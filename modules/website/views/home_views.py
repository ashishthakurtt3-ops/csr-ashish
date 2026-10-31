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
    from modules.admin_panel.snapshot_service import get_current_stats_snapshot
    data, is_stale, audit_run_id, data_as_of = get_current_stats_snapshot()

    context = {
        'total_companies': data.get('total_companies', 0),
        'verified_companies': data.get('verified_companies', 0),
        'csr_projects': data.get('csr_projects', 0),
        'jobs_tracked': data.get('jobs_tracked', 0),
        'active_opportunities': data.get('active_opportunities', 0),
        'last_live_fetch': data.get('last_live_fetch', 'Recently'),
        'data_as_of': data_as_of,
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
    """Platform statistics and counters endpoint - served via precomputed authoritative snapshot."""
    from modules.admin_panel.snapshot_service import get_current_stats_snapshot
    if request.GET.get('refresh'):
        cache.delete('stats_snapshot_cache')
    data, is_stale, audit_run_id, data_as_of = get_current_stats_snapshot()
    return JsonResponse(data)


def coverage_report_api(request):
    """Returns coverage statistics and status for all processed companies via precomputed snapshot."""
    from modules.admin_panel.snapshot_service import get_current_coverage_snapshot
    rows, is_stale, audit_run_id, data_as_of = get_current_coverage_snapshot()
    response = JsonResponse(rows, safe=False)
    if data_as_of:
        response['X-Data-As-Of'] = str(data_as_of)
    if audit_run_id:
        response['X-Audit-Run-Id'] = str(audit_run_id)
    return response




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

