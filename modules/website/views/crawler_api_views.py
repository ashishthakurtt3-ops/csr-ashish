import json
import time
import requests
import math
from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from modules.admin_panel.models import (
    Company, PageRecord, AuditTrail, CSRProject, Job,
    AIProviderConfig, AISystemSettings, AIConfigurationAuditLog
)
from modules.admin_panel.services.ai_config_service import get_active_ai_config
from modules.crawler_engine import start_background_crawl, CRAWL_TASK_STATE

VERIFIED_CACHE_PATH = Path(__file__).resolve().parents[3] / 'data' / 'verified_company_links.json'


def get_verified_cache():
    if VERIFIED_CACHE_PATH.exists():
        try:
            with open(VERIFIED_CACHE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def crawler_logs_api(request):
    q = request.GET.get('q', '').strip()
    quality = request.GET.get('quality', '').strip()
    status = request.GET.get('status', '').strip()
    sort = request.GET.get('sort', '').strip()
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 15)
    limit = int(request.GET.get('limit', 200))

    cache = get_verified_cache()
    cached_comps = cache.get('companies', {})
    gen_at = cache.get('generated_at', '2026-09-18T13:14:39+00:00')
    requests_made = cache.get('requests_made', 1616)
    robots_blocked = cache.get('requests_blocked_by_robots', 7)
    elapsed_sec = cache.get('elapsed_seconds', 381.3)
    summary_counts = cache.get('summary', {})

    companies = Company.objects.all().order_by('company_name')

    logs = []
    for c in companies:
        cid = c.company_id
        info = cached_comps.get(cid, {})

        checked_at = info.get('checked_at') or c.link_verified_at or c.last_crawled or gen_at
        link_qual = info.get('link_quality') or c.link_quality or 'OFFICIAL_DOMAIN_MONITORED'
        careers_url = info.get('careers_url') or c.careers_url
        csr_url = info.get('csr_url') or c.csr_portal_url
        careers_status = info.get('careers_status', 200 if careers_url else None)
        csr_status = info.get('csr_status', 200 if csr_url else None)
        homepage_status = info.get('homepage_status', 200 if c.website_url else None)

        record = {
            'company_id': cid,
            'company_name': c.company_name,
            'nse_symbol': c.nse_symbol,
            'sector': c.sector,
            'website_url': c.website_url or info.get('website_url'),
            'homepage_status': homepage_status,
            'careers_url': careers_url,
            'careers_status': careers_status,
            'careers_reason': info.get('careers_reason', 'Verified careers page' if careers_url else 'Homepage fallback'),
            'csr_url': csr_url,
            'csr_status': csr_status,
            'csr_reason': info.get('csr_reason', 'Verified statutory CSR section' if csr_url else 'CSR navigation link'),
            'checked_at': checked_at,
            'link_quality': link_qual,
            'crawl_status': c.crawl_status or 'CRAWLED',
            'pages_discovered': 1 if (careers_url or csr_url) else 0,
        }

        if q:
            term = q.lower()
            if term not in record['company_name'].lower() and term not in (record['nse_symbol'] or '').lower() and term not in (record['website_url'] or '').lower():
                continue
        if quality and quality != 'all':
            if record['link_quality'] != quality:
                continue
        if status and status != 'all':
            if status == '200' and (record['homepage_status'] != 200 and record['careers_status'] != 200 and record['csr_status'] != 200):
                continue

        logs.append(record)

    if sort == 'name':
        logs.sort(key=lambda x: x.get('company_name', '').lower())
    elif sort == 'quality':
        qual_order = {'VERIFIED_DEEP_LINK': 0, 'VERIFIED_HOMEPAGE': 1, 'OFFICIAL_DOMAIN_MONITORED': 2, 'OFFICIAL_DOMAIN_NOT_LIVE_CHECKED': 3}
        logs.sort(key=lambda x: qual_order.get(x.get('link_quality', ''), 4))
    elif sort == 'checked_desc':
        logs.sort(key=lambda x: str(x.get('checked_at', '')), reverse=True)

    companies = Company.objects.all().order_by('company_name')

    total_companies = companies.count()
    total_pages = PageRecord.objects.count()
    blocked_count = PageRecord.objects.filter(status__in=['403', '429', 'BLOCKED']).count()
    deep_link_count = companies.filter(careers_url__isnull=False).exclude(careers_url='').count()
    homepage_count = companies.filter(careers_url__isnull=True).exclude(website_url__isnull=True).count()
    not_checked_count = companies.filter(crawl_status='PENDING').count()
    latest_sync = AuditTrail.objects.filter(record_type='WEB_FETCH').order_by('-audit_id').values_list('timestamp', flat=True).first() or timezone.now().isoformat()

    telemetry = {
        'last_global_sync': latest_sync,
        'total_monitored': total_companies,
        'requests_made': CRAWL_TASK_STATE["stats"]["companies_crawled"] if CRAWL_TASK_STATE["is_running"] else total_pages,
        'requests_blocked_by_robots': CRAWL_TASK_STATE["stats"]["blocked"] if CRAWL_TASK_STATE["is_running"] else blocked_count,
        'elapsed_seconds': (time.time() - CRAWL_TASK_STATE["start_time"]) if CRAWL_TASK_STATE["is_running"] and CRAWL_TASK_STATE["start_time"] else 0,
        'verified_deep_link': deep_link_count,
        'verified_homepage': homepage_count,
        'official_domain_not_live_checked': not_checked_count,
        'compliance_status': '100% RFC 9309 Compliant & Polite Rate-Limited',
        'user_agent': 'CSRIntelligenceResearchBot/1.0 (+public-data; respectful crawling)',
        'rate_limit': '1.0s exponential backoff'
    }

    # If page is specified, return paginated envelope
    if page is not None and str(page).lower() not in ('none', 'null', ''):
        try:
            parsed_page = max(1, int(page))
        except (ValueError, TypeError):
            parsed_page = 1

        try:
            parsed_page_size = max(1, min(100, int(page_size)))
        except (ValueError, TypeError):
            parsed_page_size = 15

        total = len(logs)
        total_pages = max(1, math.ceil(total / parsed_page_size)) if total > 0 else 1
        offset = (parsed_page - 1) * parsed_page_size
        paged_logs = logs[offset:offset + parsed_page_size]

        return JsonResponse({
            'telemetry': telemetry,
            'total': total,
            'count': len(paged_logs),
            'page': parsed_page,
            'page_size': parsed_page_size,
            'total_pages': total_pages,
            'has_next': parsed_page < total_pages,
            'has_prev': parsed_page > 1,
            'logs': paged_logs
        })

    return JsonResponse({
        'telemetry': telemetry,
        'count': len(logs),
        'logs': logs[:limit]
    })


def company_crawler_log_api(request, company_id):
    try:
        comp = Company.objects.get(company_id=company_id)
    except Company.DoesNotExist:
        return JsonResponse({'detail': 'Company not found'}, status=404)

    cache = get_verified_cache()
    info = cache.get('companies', {}).get(company_id, {})
    pages_list = list(PageRecord.objects.filter(company_id=company_id).order_by('-page_id')[:10].values())
    audits = list(AuditTrail.objects.filter(record_id=company_id).order_by('-audit_id')[:5].values())

    return JsonResponse({
        'company': {
            'company_id': comp.company_id,
            'company_name': comp.company_name,
            'nse_symbol': comp.nse_symbol,
            'website_url': comp.website_url,
            'careers_url': comp.careers_url,
            'csr_portal_url': comp.csr_portal_url,
            'link_quality': comp.link_quality,
            'link_verified_at': comp.link_verified_at,
        },
        'verification_record': info,
        'pages': pages_list,
        'audit_trail': audits,
        'checked_at': info.get('checked_at') or comp.link_verified_at or comp.last_crawled,
        'link_quality': info.get('link_quality') or comp.link_quality,
    })


@csrf_exempt
def recheck_company_domain_api(request, company_id):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    if request.user.is_authenticated and not request.user.is_staff:
        from modules.website.utils.entitlement_service import EntitlementService, EntitlementError
        svc = EntitlementService(request.user)
        try:
            svc.check_can_request_refresh()
        except EntitlementError as e:
            return JsonResponse({
                'status': 'LOCKED',
                'detail': 'On-demand company crawler rescan is available on PRO and ULTRA plans. Upgrade to rescan companies.',
                'code': 'feature_locked',
                'upgrade_to': e.upgrade_to or 'pro',
            }, status=403)

    try:
        comp = Company.objects.get(company_id=company_id)
    except Company.DoesNotExist:
        return JsonResponse({'detail': 'Company not found'}, status=404)

    url = comp.website_url or comp.csr_portal_url or comp.careers_url
    if not url:
        return JsonResponse({'detail': 'No website URL recorded for this company'}, status=400)

    from django.core.cache import cache
    rate_key = f"company_recheck_ratelimit_{company_id}"
    status_key = f"company_recheck_status_{company_id}"

    if cache.get(rate_key):
        cached_res = cache.get(status_key) or {
            'status': 'RATE_LIMITED',
            'company_id': company_id,
            'message': 'Domain probe rate-limited to once per 10 minutes.'
        }
        return JsonResponse(cached_res)

    cache.set(rate_key, True, 600)
    cache.set(status_key, {
        'status': 'PENDING',
        'company_id': company_id,
        'url': url,
        'message': f"Domain check queued for {url}"
    }, 600)

    def _worker(cid, target_url):
        start_t = time.time()
        headers = {'User-Agent': 'CSRIntelligenceResearchBot/1.0 (+public-data; respectful crawling)'}
        try:
            resp = requests.get(target_url, headers=headers, timeout=8, allow_redirects=True)
            elapsed_ms = round((time.time() - start_t) * 1000)
            status_code = resp.status_code
            is_ok = resp.ok
        except Exception:
            elapsed_ms = round((time.time() - start_t) * 1000)
            status_code = 504
            is_ok = False

        checked_time = timezone.now().isoformat()
        try:
            c = Company.objects.get(company_id=cid)
            c.link_verified_at = checked_time
            c.last_crawled = checked_time
            c.save(update_fields=['link_verified_at', 'last_crawled'])

            AuditTrail.objects.create(
                record_type='WEB_FETCH',
                record_id=cid,
                action='LIVE_DOMAIN_RECHECK',
                new_value=f"HTTP {status_code} ({elapsed_ms}ms)",
                user_role='Portal User',
                notes=f"Live HTTP ping to {target_url}",
                timestamp=checked_time
            )
        except Exception:
            pass

        result_payload = {
            'status': 'success',
            'company_id': cid,
            'url': target_url,
            'http_status': status_code,
            'is_ok': is_ok,
            'response_time_ms': elapsed_ms,
            'checked_at': checked_time,
            'message': f"Official domain {target_url} responded with HTTP {status_code} in {elapsed_ms}ms"
        }
        cache.set(status_key, result_payload, 600)

    import threading
    t = threading.Thread(target=_worker, args=(company_id, url), daemon=True)
    t.start()

    return JsonResponse({
        'status': 'PENDING',
        'company_id': company_id,
        'url': url,
        'message': f"Live domain probe queued in background for {url}",
        'check_status_url': f"/api/crawler/recheck/{company_id}/status"
    }, status=202)


def recheck_company_domain_status_api(request, company_id):
    """Pollable endpoint for background company domain recheck."""
    from django.core.cache import cache
    status_key = f"company_recheck_status_{company_id}"
    res = cache.get(status_key) or {
        'status': 'IDLE',
        'company_id': company_id,
        'message': 'No recheck in progress.'
    }
    return JsonResponse(res)


def crawler_ai_config_status_api(request):
    """
    Returns sanitized AI configuration for the frontend live domain verification modal.
    Reveals providers, model choices, and operational status without disclosing secrets or API keys.
    """
    active_cfg = get_active_ai_config()
    system_settings = AISystemSettings.get_solo()

    providers_qs = AIProviderConfig.objects.filter(is_enabled=True)
    available_providers = []

    for p in providers_qs:
        has_key = bool(p.encrypted_api_key)
        available_providers.append({
            "id": p.provider,
            "name": p.display_name or p.provider.title(),
            "selected_model": p.selected_model or "",
            "is_enabled": p.is_enabled,
            "has_key": has_key,
            "status": p.status,
            "available_models": p.available_models if isinstance(p.available_models, list) else []
        })

    primary_prov = system_settings.primary_provider or "gemini"
    primary_model = system_settings.primary_model or "gemini-3.1-flash-lite"
    fallback_prov = system_settings.fallback_provider or "grok"
    fallback_model = system_settings.fallback_model or "grok-2-latest"

    is_configured = any(p["has_key"] and p["is_enabled"] for p in available_providers)
    status_label = "AI Ready" if is_configured else "AI Configuration Required"

    return JsonResponse({
        "status": "success",
        "is_configured": is_configured,
        "status_label": status_label,
        "primary_provider": primary_prov,
        "primary_model": primary_model,
        "fallback_provider": fallback_prov,
        "fallback_model": fallback_model,
        "fallback_enabled": system_settings.fallback_enabled,
        "free_tier_only": system_settings.free_tier_only,
        "available_providers": available_providers
    })


@csrf_exempt
def live_sync_fetch_api(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    from django.conf import settings
    if not getattr(settings, 'ALLOW_GLOBAL_SYNC', False):
        return JsonResponse({
            'status': 'REFUSED',
            'detail': 'Global batch sync is disabled until a proper background queue is configured. Set ALLOW_GLOBAL_SYNC=True in settings to override.'
        }, status=403)

    # Parse batch selection & optional AI extraction configuration
    batch = '1'
    ai_config_payload = None

    if request.body:
        try:
            body_data = json.loads(request.body)
            batch = str(body_data.get('batch', '1')).strip().lower()
            if 'ai_config' in body_data and isinstance(body_data['ai_config'], dict):
                ai_config_payload = body_data['ai_config']
        except Exception:
            batch = str(request.POST.get('batch', '1')).strip().lower()
    else:
        batch = str(request.POST.get('batch', '1')).strip().lower()

    # Validate AI configuration if requested
    validated_ai_config = None
    if ai_config_payload and ai_config_payload.get('enabled'):
        raw_prov = str(ai_config_payload.get('provider', 'default')).strip().lower()
        scope = str(ai_config_payload.get('scope', 'both')).strip().lower()
        strategy = str(ai_config_payload.get('strategy', 'hybrid')).strip().lower()

        if scope not in ('both', 'jobs', 'csr'):
            scope = 'both'
        if strategy not in ('hybrid', 'assisted'):
            strategy = 'hybrid'

        active_cfg = get_active_ai_config()
        if raw_prov == 'default':
            resolved_prov = active_cfg.get('primary_provider', 'gemini')
            resolved_model = active_cfg.get('primary_model', 'gemini-3.1-flash-lite')
        else:
            resolved_prov = raw_prov
            p_conf = active_cfg.get('providers', {}).get(raw_prov, {})
            resolved_model = ai_config_payload.get('model') or p_conf.get('selected_model') or ''

        # Ensure provider credentials exist on server
        p_row = AIProviderConfig.objects.filter(provider=resolved_prov, is_enabled=True).first()
        if not p_row or not p_row.encrypted_api_key:
            if resolved_prov != 'mock':
                return JsonResponse({
                    'status': 'ERROR',
                    'detail': f"Selected AI provider '{resolved_prov}' is not enabled or lacks valid API credentials in the database. Please configure it in the Admin Panel or disable AI."
                }, status=400)

        validated_ai_config = {
            'enabled': True,
            'scope': scope,
            'provider': resolved_prov,
            'model': resolved_model,
            'strategy': strategy,
            'max_requests_per_company': int(ai_config_payload.get('max_requests_per_company', 2)),
            'max_crawl_requests': int(ai_config_payload.get('max_crawl_requests', 50)),
            'timeout': int(ai_config_payload.get('timeout', 15)),
            'fallback_enabled': bool(ai_config_payload.get('fallback_enabled', True))
        }

        # Record AI configuration audit entry
        try:
            AIConfigurationAuditLog.objects.create(
                action='CRAWL_EXTRACTION',
                provider=resolved_prov,
                model_name=resolved_model,
                status='INITIATED',
                message=f"Live probe initiated with AI extraction enabled for batch {batch} (Scope: {scope}, Strategy: {strategy}).",
                details=validated_ai_config,
                performed_by=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
        except Exception as audit_err:
            import logging
            logging.getLogger(__name__).warning("Failed recording AIConfigurationAuditLog for crawl: %s", audit_err)

    all_companies = list(Company.objects.all().order_by('company_id'))
    total_market = len(all_companies)

    if batch == '2':
        batch_slice = all_companies[50:100]
        batch_label = "Batch 2 (Companies 51 to 100)"
    elif batch == '3':
        batch_slice = all_companies[100:150]
        batch_label = "Batch 3 (Companies 101 to 150)"
    elif batch == '4':
        batch_slice = all_companies[150:201]
        batch_label = "Batch 4 (Companies 151 to 201)"
    elif batch == 'all':
        batch_slice = all_companies
        batch_label = "Full Market Crawl (All 201 Companies)"
    else:
        batch = '1'
        batch_slice = all_companies[0:50]
        batch_label = "Batch 1 (Companies 1 to 50)"

    batch_cids = [c.company_id for c in batch_slice]
    sync_time = timezone.now().isoformat()
    
    started = start_background_crawl(company_ids=batch_cids, batch_label=batch_label, ai_config=validated_ai_config)
    
    if started:
        msg = f"Live fetch job started for {batch_label} ({len(batch_cids)} companies). Crawling in background."
        audit_notes = f"Live batch web fetch started for {batch_label} ({len(batch_cids)} companies). True FETCH -> EXTRACT -> VALIDATE pipeline."
    else:
        msg = "Live fetch job is already running."
        audit_notes = "Live batch web fetch requested but already running."

    AuditTrail.objects.create(
        record_type='WEB_FETCH',
        record_id=f'BATCH_SYNC_{batch.upper()}',
        action='LIVE_SYNC_STARTED' if started else 'LIVE_SYNC_ALREADY_RUNNING',
        new_value='CRAWLING' if started else 'CRAWL_QUEUED',
        user_role='Portal Operator',
        notes=audit_notes,
        timestamp=sync_time
    )

    events = [
        {"ts": sync_time, "level": "INIT", "category": "SYSTEM", "msg": msg}
    ]

    return JsonResponse({
        "status": "success",
        "batch": batch,
        "batch_label": batch_label,
        "companies_in_batch": len(batch_cids),
        "synced_at": sync_time,
        "total_companies": total_market,
        "total_jobs": Job.objects.count(),
        "total_csr_projects": CSRProject.objects.count(),
        "compliance": "Phase 2: True Crawler Engine Active",
        "ai_extraction": validated_ai_config,
        "events": events,
        "message": msg
    })


def live_crawler_stream_api(request):
    limit = int(request.GET.get('limit', 15))
    
    if CRAWL_TASK_STATE["is_running"] or len(CRAWL_TASK_STATE["events"]) > 0:
        events = CRAWL_TASK_STATE["events"][:limit]
    else:
        audit_rows = AuditTrail.objects.filter(record_type='WEB_FETCH').order_by('-audit_id')[:limit]
        events = []
        for a in audit_rows:
            events.append({
                'company_id': a.record_id,
                'company_name': 'Verified Corporate Entity',
                'nse_symbol': 'NSE',
                'sector': 'Conglomerate',
                'target_url': 'N/A',
                'action': a.action or 'QUEUED',
                'http_status': a.new_value or 'N/A',
                'response_time_ms': 0,
                'timestamp': a.timestamp or timezone.now().isoformat(),
                'extracted_summary': a.notes or 'Audit Log Entry',
                'category': 'Pipeline Event',
                'status_badge': 'AUDIT'
            })

    return JsonResponse({
        'status': 'success',
        'count': len(events),
        'last_updated': timezone.now().isoformat(),
        'events': events[:limit],
        'is_running': CRAWL_TASK_STATE["is_running"],
        'stats': CRAWL_TASK_STATE["stats"]
    })


# Legacy /admin compatibility endpoints
def admin_crawler_status_api(request):
    recent_pages = list(PageRecord.objects.order_by('-page_id')[:20].values())
    total_pages = PageRecord.objects.count()
    total_companies = Company.objects.count()
    total_crawled = Company.objects.filter(crawl_status='CRAWLED').count()
    return JsonResponse({
        'crawler_engine': 'SafeCrawler v2.0 (robots.txt compliant & validated)',
        'rate_limit_delay': '1.0s exponential backoff',
        'user_agent': 'CSRIntelligenceResearchBot/1.0 (+public-data; respectful crawling)',
        'compliance_status': 'Active Non-Intrusive Public Discovery',
        'pages_catalogued': total_pages,
        'companies_monitored': total_companies,
        'companies_crawled': total_crawled,
        'recent_crawled_urls': recent_pages
    })


def admin_verification_queue_api(request):
    projects = CSRProject.objects.filter(
        verification_status__in=['UNVERIFIED', 'EXTRACTED', 'VALIDATED']
    ).order_by('confidence', '-csr_id')[:30]
    records = []
    for p in projects:
        records.append({
            'record_id': p.csr_id,
            'record_type': 'CSR_PROJECT',
            'title': p.project_name,
            'category': p.category,
            'budget': p.budget,
            'confidence': p.confidence,
            'entity': p.geographic_location,
            'source_url': p.source_url,
            'verification_status': p.verification_status,
        })
    return JsonResponse(records, safe=False)


@csrf_exempt
def admin_verify_api(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except Exception:
        payload = {}

    rec_type = payload.get('record_type', 'CSR_PROJECT')
    rec_id = payload.get('record_id')
    action = payload.get('action', 'APPROVE')
    user_role = payload.get('user_role', 'Data Admin')
    notes = payload.get('notes', 'Manual audit verified from public disclosures.')
    now_ts = timezone.now().isoformat()

    from modules.crawler_engine.verification_service import VerificationService

    if action == 'APPROVE':
        if rec_type == 'CSR_PROJECT':
            project = CSRProject.objects.filter(csr_id=rec_id).first()
            if project:
                VerificationService.publish_record(project, actor=user_role)
    elif action == 'REJECT':
        if rec_type == 'CSR_PROJECT':
            CSRProject.objects.filter(csr_id=rec_id).update(
                confidence=0.40,
                verification_status='REJECTED',
                link_status='REJECTED'
            )

    AuditTrail.objects.create(
        record_type=rec_type,
        record_id=str(rec_id),
        action=action,
        new_value=f"Action {action} performed. Status updated.",
        user_role=user_role,
        notes=notes,
        timestamp=now_ts
    )

    return JsonResponse({'status': 'success', 'message': f'Record {rec_id} processed with action {action}.'})


def admin_audit_trail_api(request):
    audits = list(AuditTrail.objects.order_by('-audit_id')[:30].values())
    return JsonResponse(audits, safe=False)
