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


def index_view(request, default_tab='companies'):
    """Serve the primary ImpactBridge Dynamic Web Portal with server-rendered telemetry and auth state."""
    from modules.admin_panel.snapshot_service import get_current_stats_snapshot
    from modules.admin_panel.models import Subscription, GuestPreviewSettings
    from modules.website.utils.subscription_service import get_or_create_wallet

    data, is_stale, audit_run_id, data_as_of = get_current_stats_snapshot()
    preview_cfg = GuestPreviewSettings.get_settings()

    try:
        banner_headline_rendered = preview_cfg.banner_headline.format(
            count=preview_cfg.preview_limit,
            companies=data.get('total_companies', 201),
            jobs=data.get('jobs_tracked', 2619),
            csr=data.get('csr_projects', 1600)
        )
    except Exception:
        banner_headline_rendered = preview_cfg.banner_headline

    try:
        bottom_title_rendered = preview_cfg.bottom_banner_title.format(
            count=preview_cfg.preview_limit,
            total=data.get('total_companies', 201)
        )
    except Exception:
        bottom_title_rendered = preview_cfg.bottom_banner_title

    user_sub = None
    user_wallet = None
    wallet_balance_inr = "0.00"
    plan_tier = "FREE"
    plan_tier_label = "No Active Plan"
    is_sub_active = False
    sub_status = "NONE"

    has_active_plan = False
    if request.user.is_authenticated:
        # Query latest subscription regardless of status (read-only)
        user_sub = Subscription.objects.filter(user=request.user).order_by('-created_at').first()
        if not user_sub:
            user_sub = Subscription.objects.filter(tenant_id=f"user_{request.user.id}").order_by('-created_at').first()

        from modules.website.utils.entitlement_service import user_has_active_plan
        has_active_plan = user_has_active_plan(request.user)

        if user_sub:
            sub_status = (user_sub.status or 'INACTIVE').upper()
            is_sub_active = sub_status in ('ACTIVE', 'TRIALING')
            plan_tier = (user_sub.plan_id or 'free').upper()
            if is_sub_active:
                plan_tier_label = f"{plan_tier} Active"
            elif sub_status == 'EXPIRED':
                plan_tier_label = f"{plan_tier} Expired"
            elif sub_status in ('CANCELED', 'CANCELLED'):
                plan_tier_label = f"{plan_tier} Cancelled"
            else:
                plan_tier_label = f"{plan_tier} ({sub_status})"
        elif request.user.is_staff or request.user.is_superuser:
            sub_status = "ACTIVE"
            is_sub_active = True
            plan_tier = "ADMIN"
            plan_tier_label = "Admin Access"
        else:
            sub_status = "NONE"
            plan_tier = "FREE"
            plan_tier_label = "No Active Plan"

        user_wallet = get_or_create_wallet(request.user)
        if user_wallet:
            wallet_balance_inr = f"{user_wallet.balance_paise / 100:,.2f}"

    plan_required = bool(request.user.is_authenticated and not has_active_plan)
    is_preview_mode = not has_active_plan

    tab_param = request.GET.get('tab')
    if tab_param in ('companies', 'jobs', 'csr', 'matching', 'prospects', 'pricing'):
        default_tab = tab_param
    elif request.GET.get('plan_required') or (plan_required and not request.GET.get('tab')):
        default_tab = 'pricing'

    context = {
        'total_companies': data.get('total_companies', 0),
        'verified_companies': data.get('verified_companies', 0),
        'csr_projects': data.get('csr_projects', 0),
        'jobs_tracked': data.get('jobs_tracked', 0),
        'active_opportunities': data.get('active_opportunities', 0),
        'last_live_fetch': data.get('last_live_fetch', 'Recently'),
        'data_as_of': data_as_of,
        'user_subscription': user_sub,
        'user_wallet': user_wallet,
        'wallet_balance_inr': wallet_balance_inr,
        'plan_tier': plan_tier,
        'plan_tier_label': plan_tier_label,
        'is_sub_active': is_sub_active,
        'sub_status': sub_status,
        'default_tab': default_tab,
        'is_preview_mode': is_preview_mode,
        'has_active_plan': has_active_plan,
        'plan_required': plan_required,
        'preview_settings': preview_cfg,
        'banner_headline_rendered': banner_headline_rendered,
        'bottom_title_rendered': bottom_title_rendered,
    }
    return render(request, 'website/index.html', context)


def pricing_view(request):
    """Direct route for subscription pricing tab."""
    return index_view(request, default_tab='pricing')


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

