import time

from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.db.models import Count, Q
from django.utils import timezone
from modules.admin_panel.models import (
    Company, Job, CSROpportunity, CSRProject, NGOCollaboration,
    Contact, Prospect, PageRecord, CompanyCrawlSummary
)

# Process start reference used to report uptime on the health page.
from modules.admin_panel.verification import (
    PUBLIC_VERIFICATION_STATUSES, public_jobs, public_job_q, NOT_AVAILABLE_TEXT, LOGIN_REQUIRED_TEXT, LINK_OK,
)

STARTED_AT = timezone.now()

# Social-impact role detection, shared across jobs list and stats
IMPACT_ROLE_FILTER = (
    Q(job_title__icontains='CSR') | Q(job_title__icontains='ESG') |
    Q(job_title__icontains='Sustainability') | Q(job_title__icontains='Community') |
    Q(job_title__icontains='Foundation') | Q(job_title__icontains='Social') |
    Q(job_title__icontains='Environmental Impact') | Q(job_title__icontains='Impact') |
    Q(department__icontains='CSR') | Q(department__icontains='Social') |
    Q(department__icontains='Sustainab') | Q(function__icontains='Impact') |
    Q(function__icontains='Sustainability')
)


def index_view(request):
    """Serve the primary ImpactBridge Dynamic Web Portal with server-rendered telemetry."""
    # Collect real-time telemetry for the initial page load dashboard
    total_companies = Company.objects.count()
    verified_companies = Company.objects.filter(Q(verification_status='VERIFIED') | Q(link_quality__in=['VERIFIED_DEEP_LINK', 'VERIFIED_HOMEPAGE'])).count()
    
    from modules.admin_panel.verification import public_records
    csr_projects_count = public_records(CSRProject.objects.filter(status='ACTIVE')).count()
    jobs_tracked = public_jobs(Job.objects.all()).count()
    active_opportunities = CSROpportunity.objects.filter(
        verification_status__in=list(PUBLIC_VERIFICATION_STATUSES), 
        status='OPEN'
    ).count()

    latest_summary = CompanyCrawlSummary.objects.order_by('-crawl_started_at').first()
    if latest_summary and latest_summary.crawl_started_at:
        last_fetch_display = latest_summary.crawl_started_at.strftime('%d %b %Y, %H:%M')
    else:
        latest_page = PageRecord.objects.order_by('-page_id').first()
        last_fetch_display = (latest_page.last_crawled if latest_page and latest_page.last_crawled else NOT_AVAILABLE_TEXT)

    context = {
        'total_companies': total_companies,
        'verified_companies': verified_companies,
        'csr_projects': csr_projects_count,
        'jobs_tracked': jobs_tracked,
        'active_opportunities': active_opportunities,
        'last_live_fetch': last_fetch_display,
    }
    return render(request, 'website/index.html', context)


def _wants_json(request):
    """Serve JSON to API clients and HTML to browsers.

    Precedence: explicit `?format=` override, then the `Accept` header. Only
    clients that explicitly advertise `text/html` (browsers) get the styled
    page; everything else — curl, the Django test client, API consumers —
    keeps the original JSON contract.
    """
    requested = request.GET.get('format', '').lower()
    if requested in ('json', 'html'):
        return requested == 'json'
    return 'text/html' not in request.META.get('HTTP_ACCEPT', '')


def _collect_health():
    """Run the health probes and return a dict describing system state."""
    checks = []

    # --- Database connectivity + latency -------------------------------
    db_started = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        latency_ms = round((time.perf_counter() - db_started) * 1000, 2)
        db_name = connection.settings_dict.get('NAME') or 'unknown'
        checks.append({
            'name': 'Database',
            'status': 'ok',
            'detail': f'MySQL · {db_name}',
            'meta': f'{latency_ms} ms',
        })
    except Exception as exc:  # pragma: no cover - only on DB outage
        checks.append({
            'name': 'Database',
            'status': 'error',
            'detail': 'Connection failed',
            'meta': str(exc)[:120],
        })

    # --- Row counts (proves the ORM is actually reading live data) -----
    counts = []
    if checks[0]['status'] == 'ok':
        for label, model in (
            ('Companies', Company),
            ('Jobs', Job),
            ('CSR Projects', CSRProject),
            ('NGO Collaborations', NGOCollaboration),
            ('CSR Opportunities', CSROpportunity),
        ):
            try:
                counts.append({'label': label, 'value': model.objects.count()})
            except Exception:  # pragma: no cover
                counts.append({'label': label, 'value': None})

    degraded = any(c['status'] != 'ok' for c in checks)
    uptime = int((timezone.now() - STARTED_AT).total_seconds())

    return {
        'status': 'degraded' if degraded else 'ok',
        'platform': 'ImpactBridge CSR & Job Intelligence OS',
        'version': '2.5.0',
        'engine': 'Django Production',
        'checks': checks,
        'counts': counts,
        'uptime_seconds': uptime,
        'timestamp': timezone.now().isoformat(),
    }


def health_view(request):
    """System health check endpoint (HTML for browsers, JSON for API clients)."""
    payload = _collect_health()

    if _wants_json(request):
        # Preserve the original flat contract for existing API consumers.
        return JsonResponse({
            'status': payload['status'],
            'platform': payload['platform'],
            'version': payload['version'],
            'engine': payload['engine'],
        })

    response = render(request, 'website/health.html', payload)
    if payload['status'] != 'ok':
        response.status_code = 503
    return response


from django.core.cache import cache


def stats_view(request):
    """Platform statistics and counters endpoint - strictly authoritative source records."""
    cached_stats = cache.get('home_stats_cache_v1')
    if cached_stats and not request.GET.get('refresh'):
        return JsonResponse(cached_stats)

    total_companies = Company.objects.count()
    verified_companies = Company.objects.filter(Q(verification_status='VERIFIED') | Q(link_quality__in=['VERIFIED_DEEP_LINK', 'VERIFIED_HOMEPAGE'])).count()
    verified_websites = Company.objects.filter(website_url__isnull=False).exclude(website_url='').count()
    crawled_companies = Company.objects.filter(crawl_status='CRAWLED').count()
    login_required_companies = Company.objects.filter(
        Q(jobs_access='LOGIN_REQUIRED') | Q(csr_access='LOGIN_REQUIRED') | Q(contacts_access='LOGIN_REQUIRED')
    ).count()
    jobs_login_required_companies = Company.objects.filter(jobs_access='LOGIN_REQUIRED').count()
    csr_login_required_companies = Company.objects.filter(csr_access='LOGIN_REQUIRED').count()
    
    # Strictly published & verified records only
    from modules.admin_panel.verification import public_records
    csr_projects_count = public_records(CSRProject.objects.filter(status='ACTIVE')).count()
    ngo_collabs = NGOCollaboration.objects.count()
    jobs_base_qs = public_jobs(Job.objects.all())
    jobs_tracked = jobs_base_qs.count()
    impact_jobs = jobs_base_qs.filter(IMPACT_ROLE_FILTER).count()
    companies_hiring = jobs_base_qs.values('company_id').distinct().count()
    verified_job_links = jobs_tracked
    live_verified_deep_links = Company.objects.filter(link_quality='VERIFIED_DEEP_LINK').count()
    contacts_extracted = Contact.objects.filter(verification_status__in=list(PUBLIC_VERIFICATION_STATUSES)).count()
    active_opportunities = CSROpportunity.objects.filter(verification_status__in=list(PUBLIC_VERIFICATION_STATUSES), status='OPEN').count()
    prospects_count = Prospect.objects.count()

    # Telemetry and recency
    latest_summary = CompanyCrawlSummary.objects.order_by('-crawl_started_at').first()
    if latest_summary and latest_summary.crawl_started_at:
        last_fetch_display = latest_summary.crawl_started_at.strftime('%d %b %Y, %H:%M')
    else:
        latest_page = PageRecord.objects.order_by('-page_id').first()
        last_fetch_display = (latest_page.last_crawled if latest_page and latest_page.last_crawled else NOT_AVAILABLE_TEXT)

    # Statutory CSR expenditure vs. Operational Sustainability Outlay
    # Project 971 (Mahindra) recorded INR 16 million (₹1.60 Cr) invested on Waste Disposal/Treatment.
    # Under Indian Companies Act 2013 (Section 135 & Schedule VII), internal industrial waste
    # disposal/treatment is an operational environmental compliance outlay under EPA/HW rules,
    # not statutory Section 135 CSR expenditure.
    # Therefore, aggregate statutory CSR expenditure is explicitly unavailable from public web scrape
    # and returned as None (null) rather than substituting zero.
    total_csr_budget_cr = None
    sustainability_outlay_cr = None
    sustainability_outlay_details = None

    stats = {
        'total_companies': total_companies,
        'verified_companies': verified_companies,
        'verified_websites': verified_websites,
        'crawled_companies': crawled_companies,
        'login_required_companies': login_required_companies,
        'jobs_login_required_companies': jobs_login_required_companies,
        'csr_login_required_companies': csr_login_required_companies,
        'csr_projects': csr_projects_count,
        'ngo_collaborations': ngo_collabs,
        'jobs_tracked': jobs_tracked,
        'impact_jobs': impact_jobs,
        'companies_hiring': companies_hiring,
        'verified_job_links': verified_job_links,
        'live_verified_deep_links': live_verified_deep_links,
        'contacts_extracted': contacts_extracted,
        'active_opportunities': active_opportunities,
        'opportunities': active_opportunities,
        'prospects_count': prospects_count,
        'total_csr_budget_cr': total_csr_budget_cr,
        'statutory_csr_budget_cr': None,
        'csr_expenditure_status': 'Not disclosed in web crawl (Filed via MCA-21 annual reports)',
        'sustainability_outlay_cr': sustainability_outlay_cr,
        'sustainability_outlay_details': sustainability_outlay_details,
        'last_live_fetch': last_fetch_display,
        'crawl_status': 'LIVE'
    }

    # Direct Job Link Quality Metrics
    total_active_jobs = jobs_base_qs.count()
    direct_jobs_count = jobs_base_qs.filter(link_quality='DIRECT').count()
    fallback_jobs_count = jobs_base_qs.filter(link_quality='LISTING_FALLBACK').count()
    stats['direct_jobs_count'] = direct_jobs_count
    stats['fallback_jobs_count'] = fallback_jobs_count
    stats['direct_link_percentage'] = round((direct_jobs_count / total_active_jobs) * 100, 2) if total_active_jobs > 0 else 0.0

    cache.set('home_stats_cache_v1', stats, 60)
    return JsonResponse(stats)


def coverage_report_api(request):
    """Returns coverage statistics and status for all processed companies."""
    scope = request.GET.get('scope', 'all')
    companies = Company.objects.all().order_by('company_id')
    rows = []
    for c in companies:
        summary = CompanyCrawlSummary.objects.filter(company=c).first()
        active_jobs_qs = public_jobs(c.jobs.all())
        pub_jobs = active_jobs_qs.count()
        direct_jobs = active_jobs_qs.filter(link_quality='DIRECT').count()
        c_direct_pct = round((direct_jobs / pub_jobs) * 100, 2) if pub_jobs > 0 else 0.0
        pub_csr = c.csr_projects.filter(verification_status__in=list(PUBLIC_VERIFICATION_STATUSES), status='ACTIVE').count()
        status = summary.crawl_status if summary else (c.crawl_status or 'PENDING')
        ats = summary.ats_platform if (summary and summary.ats_platform) else (c.ats_platform or 'Direct/HTML')
        found = summary.jobs_discovered if summary else pub_jobs
        if summary and summary.crawl_finished_at:
            last_v = summary.crawl_finished_at.strftime('%Y-%m-%d %H:%M') if hasattr(summary.crawl_finished_at, 'strftime') else str(summary.crawl_finished_at)[:16]
        elif c.last_crawled:
            last_v = c.last_crawled.strftime('%Y-%m-%d %H:%M') if hasattr(c.last_crawled, 'strftime') else str(c.last_crawled)[:16]
        else:
            last_v = NOT_AVAILABLE_TEXT

        reasons = []
        if c.jobs_access == 'LOGIN_REQUIRED':
            reasons.append(f'Jobs: {LOGIN_REQUIRED_TEXT}')
        elif pub_jobs == 0:
            if status == 'PENDING':
                reasons.append('Jobs: Crawl pending')
            elif status == 'NO_CAREER_URL':
                reasons.append('Jobs: Official careers URL not discoverable')
            elif status == 'BLOCKED':
                reasons.append('Jobs: Blocked by bot firewall (HTTP 403)')
            elif status == 'FAILED':
                reasons.append('Jobs: Connection timeout / unreachable')
            elif status == 'REDIRECT_BLOCKED':
                reasons.append('Jobs: Disallowed redirect loop')
            elif status == 'CRAWLED':
                reasons.append('Jobs: Verified checked; 0 active public openings')
            else:
                reasons.append('Jobs: Verification pending')

        if c.csr_access == 'LOGIN_REQUIRED':
            reasons.append(f'CSR: {LOGIN_REQUIRED_TEXT}')
        elif pub_csr == 0:
            if status == 'CRAWLED':
                reasons.append('CSR: Verified checked; Schedule VII in annual PDF')
            elif status in ['BLOCKED', 'FAILED', 'REDIRECT_BLOCKED']:
                reasons.append(f'CSR: Source unreachable ({status})')
            else:
                reasons.append('CSR: Scan pending')

        explanation = ' | '.join(reasons) if reasons else 'Fully Verified & Published'
        rows.append({
            'company_id': c.company_id,
            'name': c.company_name,
            'nse_symbol': c.nse_symbol or '',
            'website': c.website_url or 'N/A',
            'careers_url': c.careers_url or 'N/A',
            'ats': ats,
            'jobs_found': found,
            'jobs_published': pub_jobs,
            'direct_link_percentage': c_direct_pct,
            'csr_records': pub_csr,
            'crawl_status': status,
            'last_verified': last_v,
            'explanation': explanation
        })
    return JsonResponse(rows, safe=False)


def search_view(request):
    """Quick autocomplete / search endpoint for companies."""
    q = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 50))

    if not q:
        return JsonResponse([], safe=False)

    qs = Company.objects.filter(
        Q(company_name__icontains=q) |
        Q(nse_symbol__icontains=q) |
        Q(sector__icontains=q)
    ).order_by('company_name')[:limit]

    results = []
    for c in qs:
        results.append({
            'company_id': c.company_id,
            'company_name': c.company_name,
            'nse_symbol': c.nse_symbol,
            'website_url': c.website_url,
            'sector': c.sector,
            'crawl_status': c.crawl_status,
        })

    return JsonResponse(results, safe=False)

