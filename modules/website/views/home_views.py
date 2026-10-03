import time

from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from django.db.models import Count, Q
from django.utils import timezone
from modules.admin_panel.models import (
    Company, Job, CSROpportunity, CSRProject, NGOCollaboration,
    Contact, Prospect, PageRecord
)

# Process start reference used to report uptime on the health page.
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
    """Serve the primary ImpactBridge Dynamic Web Portal."""
    return render(request, 'website/index.html')


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


def stats_view(request):
    """Platform statistics and counters endpoint."""
    total_companies = Company.objects.count()
    verified_websites = Company.objects.filter(website_url__isnull=False).exclude(website_url='').count()
    crawled_companies = Company.objects.filter(crawl_status='CRAWLED').count()
    csr_projects_count = CSRProject.objects.count()
    ngo_collabs = NGOCollaboration.objects.count()
    jobs_tracked = Job.objects.count()
    impact_jobs = Job.objects.filter(IMPACT_ROLE_FILTER).count()
    companies_hiring = Job.objects.values('company_id').distinct().count()
    verified_job_links = Job.objects.filter(link_status='VERIFIED_HTTP_200').count()
    live_verified_deep_links = Company.objects.filter(link_quality='VERIFIED_DEEP_LINK').count()
    contacts_extracted = Contact.objects.count()
    active_opportunities = CSROpportunity.objects.filter(status='OPEN').count()
    prospects_count = Prospect.objects.count()

    import re
    total_csr_budget_cr = 0.0
    for b in CSRProject.objects.values_list('budget', flat=True):
        if not b:
            continue
        m = re.search(r'([\d\.]+)', str(b))
        if m:
            val = float(m.group(1))
            if 'lakh' in str(b).lower():
                total_csr_budget_cr += val / 100.0
            else:
                total_csr_budget_cr += val
    total_csr_budget_cr = round(total_csr_budget_cr, 1)

    stats = {
        'total_companies': total_companies,
        'verified_websites': verified_websites,
        'crawled_companies': crawled_companies,
        'csr_projects': csr_projects_count,
        'ngo_collaborations': ngo_collabs,
        'jobs_tracked': jobs_tracked,
        'impact_jobs': impact_jobs,
        'companies_hiring': companies_hiring,
        'verified_job_links': verified_job_links,
        'live_verified_deep_links': live_verified_deep_links,
        'contacts_extracted': contacts_extracted,
        'active_opportunities': active_opportunities,
        'prospects_count': prospects_count,
        'total_csr_budget_cr': total_csr_budget_cr
    }
    return JsonResponse(stats)


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
