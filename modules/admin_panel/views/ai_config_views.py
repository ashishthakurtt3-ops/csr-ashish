"""
modules/admin_panel/views/ai_config_views.py
=============================================
Dedicated Admin Panel views and API endpoints for managing AI Models & API Configuration.
Provides:
- Dashboard interface for AI provider configuration cards
- Centralized model & provider selection controls
- Real-time server-side API key & model connectivity testing
- Free-tier cost protection enforcement
- Masked secret management and audit logging
"""

import re
import json
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.contrib import messages

from modules.admin_panel.models import AIProviderConfig, AISystemSettings, AIConfigurationAuditLog
from modules.admin_panel.services.ai_config_service import (
    bootstrap_default_configs,
    get_active_ai_config,
    save_provider_config,
    update_system_settings,
    test_provider_live,
    is_model_free_tier,
    is_provider_paid_tier,
    refresh_provider_models,
    get_crawler_usage_metrics,
    FREE_TIER_MODELS_CATALOG,
    DEFAULT_PROVIDERS_METADATA,
    create_or_update_custom_provider,
    delete_provider,
)
from modules.admin_panel.utils.ai_crypto import mask_api_key, is_masked_placeholder

logger = logging.getLogger(__name__)


def is_authorized_admin(user) -> bool:
    """Verifies that the user has administrative or staff access privileges."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if hasattr(user, 'is_admin_or_staff') and user.is_admin_or_staff():
        return True
    if hasattr(user, 'role') and user.role in ['ADMIN', 'SUPERADMIN', 'STAFF']:
        return True
    return False


def get_client_ip(request) -> str:
    """Extracts client IP address from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@login_required
@ensure_csrf_cookie
def ai_config_index_view(request):
    """
    Renders the central AI Models & API Configuration view in the admin portal.
    """
    if not is_authorized_admin(request.user):
        messages.error(request, "Access denied. Administrative permissions are required to configure AI providers.")
        return redirect('admin_portal:dashboard')

    # Ensure baseline configs exist
    bootstrap_default_configs()

    settings_obj = AISystemSettings.get_solo()
    providers_qs = AIProviderConfig.objects.all().order_by('provider')

    # Prepare provider card view models
    providers_list = []
    configured_count = 0
    healthy_count = 0

    for p in providers_qs:
        has_key = bool(p.encrypted_api_key)
        if has_key:
            configured_count += 1
        if p.status == AIProviderConfig.STATUS_ACTIVE:
            healthy_count += 1

        # Categories for multi-tab UI filtering
        prov_id = p.provider.lower().strip()
        cat_list = ['all']
        if has_key or prov_id in ('ollama', 'local'):
            cat_list.append('configured')
        if prov_id in ('gemini', 'openrouter', 'groq', 'ollama', 'local'):
            cat_list.append('free')
        if prov_id in ('openai', 'anthropic', 'gemini', 'grok'):
            cat_list.append('cloud')
        if prov_id in ('groq', 'ollama', 'mistral', 'deepseek', 'local'):
            cat_list.append('open')
        if prov_id not in ('gemini', 'openrouter', 'grok', 'groq', 'ollama', 'openai', 'anthropic', 'mistral', 'deepseek') or prov_id == 'custom':
            cat_list.append('custom')

        # Distinctive brand subtitles for premium UI/UX
        subtitles = {
            'gemini': 'Google DeepMind • Official Primary Engine',
            'grok': 'xAI • Cosmic Reasoning & Automated Failover',
            'openrouter': 'OpenRouter • Multi-Model Free Router',
            'groq': 'Groq LPU™ • Ultra-Fast Free Developer Tier',
            'openai': 'OpenAI • ChatGPT & STEM Reasoning',
            'anthropic': 'Anthropic • Claude 3.5 Sonnet & Haiku',
            'deepseek': 'DeepSeek • DeepSeek-V3 & R1 Full Reasoning',
            'mistral': 'Mistral AI • Efficient European Open Weights',
            'ollama': 'Ollama Local • 100% Free Self-Hosted',
            'custom': 'Custom Endpoint • OpenAI Compatible REST',
        }

        brand_colors = {
            'gemini': '#2563EB',
            'grok': '#0B2545',
            'openrouter': '#0D9488',
            'groq': '#EA580C',
            'openai': '#16A34A',
            'anthropic': '#7C3AED',
            'deepseek': '#2563EB',
            'mistral': '#EA580C',
            'ollama': '#374151',
            'custom': '#4F46E5',
        }

        color = brand_colors.get(prov_id, '#2563EB')
        key_last4 = p.key_last4 if has_key else ''
        is_paid = is_provider_paid_tier(p.provider, p.selected_model)
        is_primary = (p.provider == settings_obj.primary_provider)
        is_fallback = (p.provider == settings_obj.fallback_provider and settings_obj.fallback_enabled)
        role = "primary" if is_primary else ("failover" if is_fallback else "not_used")

        providers_list.append({
            'provider': p.provider,
            'display_name': p.display_name,
            'subtitle': subtitles.get(prov_id, 'OpenAI-Compatible AI Gateway'),
            'is_enabled': p.is_enabled,
            'base_url': p.base_url,
            'selected_model': p.selected_model,
            'custom_model': p.custom_model,
            'effective_model': p.effective_model,
            'available_models': p.available_models or [],
            'has_api_key': has_key,
            'key_last4': key_last4,
            'api_key_masked': p.api_key_masked if has_key else "Not configured",
            'status': p.status,
            'last_tested_at': p.last_tested_at,
            'last_test_result': p.last_test_result,
            'last_test_message': p.last_test_message,
            'last_test_latency_ms': p.last_test_latency_ms,
            'is_primary': is_primary,
            'is_fallback': is_fallback,
            'role': role,
            'allow_paid_calls': p.allow_paid_calls,
            'version': p.version,
            'is_paid_tier': is_paid,
            'is_core': prov_id in ('gemini', 'openrouter', 'grok'),
            'color': color,
            'categories': cat_list,
            'categories_str': ' '.join(cat_list),
        })

    # Strict user-specified priority order: 1st Gemini, 2nd Grok, 3rd OpenRouter, then the rest
    PRIORITY_ORDER = {
        'gemini': 0,
        'grok': 1,
        'openrouter': 2,
        'groq': 3,
        'openai': 4,
        'anthropic': 5,
        'deepseek': 6,
        'mistral': 7,
        'ollama': 8,
        'custom': 9,
    }
    providers_list.sort(key=lambda x: PRIORITY_ORDER.get(x['provider'].lower().strip(), 99))

    # Check for paid providers active in routing without allow_paid_calls authorization (Requirement 7)
    paid_role_warnings = []
    if settings_obj.primary_provider:
        prim_cfg = AIProviderConfig.objects.filter(provider=settings_obj.primary_provider).first()
        if prim_cfg and is_provider_paid_tier(prim_cfg.provider, prim_cfg.selected_model) and not prim_cfg.allow_paid_calls:
            paid_role_warnings.append(
                f"Paid Provider Notice: Primary provider '{prim_cfg.display_name}' is a paid-tier provider without 'Allow Paid Calls' authorization enabled. Automated crawler pipeline will enforce zero-cost protection."
            )

    if settings_obj.fallback_enabled and settings_obj.fallback_provider:
        fall_cfg = AIProviderConfig.objects.filter(provider=settings_obj.fallback_provider).first()
        if fall_cfg and is_provider_paid_tier(fall_cfg.provider, fall_cfg.selected_model) and not fall_cfg.allow_paid_calls:
            paid_role_warnings.append(
                f"Paid Provider Notice: Failover provider '{fall_cfg.display_name}' is a paid-tier provider without 'Allow Paid Calls' authorization enabled. Automated crawler pipeline will enforce zero-cost protection."
            )

    # Real crawler cache metrics (Requirement 8)
    usage_metrics = get_crawler_usage_metrics()

    # Recent sanitized audit records (no secrets)
    recent_audits = AIConfigurationAuditLog.objects.order_by('-timestamp')[:10]

    providers_data = [
        {
            'provider': p['provider'],
            'displayName': p['display_name'],
            'subtitle': p['subtitle'],
            'baseUrl': p['base_url'],
            'selectedModel': p['selected_model'],
            'effectiveModel': p['effective_model'],
            'availableModels': p['available_models'],
            'hasApiKey': p['has_api_key'],
            'keyLast4': p['key_last4'],
            'apiKeyMasked': p['api_key_masked'],
            'status': p['status'],
            'lastTestResult': p['last_test_result'],
            'lastTestMessage': p['last_test_message'],
            'lastTestLatencyMs': p['last_test_latency_ms'] or 0,
            'isPrimary': p['is_primary'],
            'isFallback': p['is_fallback'],
            'role': p['role'],
            'allowPaidCalls': p['allow_paid_calls'],
            'version': p['version'],
            'isPaidTier': p['is_paid_tier'],
            'color': p['color'],
        }
        for p in providers_list
    ]

    context = {
        'settings': settings_obj,
        'settings_version': settings_obj.version,
        'providers': providers_list,
        'providers_data': providers_data,
        'free_tier_catalog_json': json.dumps(FREE_TIER_MODELS_CATALOG),
        'recent_audits': recent_audits,
        'total_providers': len(providers_list),
        'configured_count': configured_count,
        'healthy_count': healthy_count,
        'paid_role_warnings': paid_role_warnings,
        'usage_metrics': usage_metrics,
    }
    return render(request, 'admin/ai_config/index.html', context)


@login_required
@require_http_methods(["POST"])
def ai_config_save_settings_api(request):
    """
    POST API to atomically save global AI system settings.
    Validates Free-Tier cost protection, optimistic concurrency (409), and bounds constraints.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    try:
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            payload = request.POST.dict()

        success, message, status_code = update_system_settings(
            data=payload,
            user=request.user,
            ip_address=get_client_ip(request)
        )

        return JsonResponse({'success': success, 'message': message}, status=status_code)

    except Exception as e:
        logger.exception("Error saving AI system settings: %s", e)
        return JsonResponse({'success': False, 'error': f"Internal error: {str(e)}"}, status=500)


@login_required
@require_http_methods(["POST"])
def ai_config_save_provider_api(request, provider):
    """
    POST API to update a single provider's configuration card.
    Securely encrypts API key if supplied. Ignores empty or mask placeholders to avoid key wiping.
    Enforces optimistic concurrency (409) and paid provider role authorization guards.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    prov_code = (provider or "").lower().strip()
    try:
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            payload = request.POST.dict()

        # Sanitize key input: if key starts with mask characters or is whitespace, do not overwrite
        key_input = str(payload.get('api_key', '')).strip()
        if is_masked_placeholder(key_input):
            payload.pop('api_key', None)

        success, message, status_code = save_provider_config(
            provider=prov_code,
            data=payload,
            user=request.user,
            ip_address=get_client_ip(request)
        )

        cfg_obj = AIProviderConfig.objects.filter(provider=prov_code).first()
        settings_obj = AISystemSettings.get_solo()
        role = "primary" if (cfg_obj and cfg_obj.provider == settings_obj.primary_provider) else (
            "failover" if (cfg_obj and cfg_obj.provider == settings_obj.fallback_provider and settings_obj.fallback_enabled) else "not_used"
        )

        return JsonResponse({
            'success': success,
            'message': message,
            'provider': prov_code,
            'version': cfg_obj.version if cfg_obj else 1,
            'settings_version': settings_obj.version,
            'role': role,
            'allow_paid_calls': cfg_obj.allow_paid_calls if cfg_obj else False,
            'has_api_key': bool(cfg_obj.encrypted_api_key) if cfg_obj else False,
            'masked_key': cfg_obj.api_key_masked if cfg_obj else '',
            'key_last4': cfg_obj.key_last4 if cfg_obj else '',
            'effective_model': cfg_obj.effective_model if cfg_obj else '',
            'status': cfg_obj.status if cfg_obj else 'UNCONFIGURED',
        }, status=status_code)

    except Exception as e:
        logger.exception("Error saving provider %s: %s", prov_code, e)
        return JsonResponse({'success': False, 'error': f"Internal error: {str(e)}"}, status=500)


@login_required
@require_http_methods(["POST"])
def ai_config_test_provider_api(request, provider):
    """
    POST API to execute a live, server-side authentication and minimal inference probe.
    Does NOT crawl websites, scrape pages, or mutate production company intelligence.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    prov_code = (provider or "").lower().strip()
    try:
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            payload = request.POST.dict()

        api_key_override = payload.get('api_key', '').strip()
        # If the user passed mask placeholder, ignore override and use the saved encrypted key
        if not api_key_override or api_key_override.startswith('••••'):
            api_key_override = None

        model_override = payload.get('model', '').strip() or None
        base_url_override = payload.get('base_url', '').strip() or None

        test_result = test_provider_live(
            provider=prov_code,
            api_key_override=api_key_override,
            model_override=model_override,
            base_url_override=base_url_override,
            user=request.user,
            ip_address=get_client_ip(request)
        )

        return JsonResponse(test_result)

    except Exception as e:
        logger.exception("Error testing provider %s: %s", prov_code, e)
        return JsonResponse({
            'success': False,
            'status': 'PROVIDER_ERROR',
            'message': f"Unexpected server test exception: {str(e)}",
            'latency_ms': 0,
            'provider': prov_code,
            'model': '',
        }, status=500)


@login_required
@require_http_methods(["POST"])
def ai_config_refresh_models_api(request, provider):
    """
    POST API to refresh the available model catalog for a specific provider.
    Rate-limited to once every 10 seconds per provider.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    prov_code = (provider or "").lower().strip()
    try:
        success, message, models_list, status_code = refresh_provider_models(
            provider=prov_code,
            user=request.user,
            ip_address=get_client_ip(request)
        )
        return JsonResponse({
            'success': success,
            'message': message,
            'provider': prov_code,
            'models': models_list
        }, status=status_code)
    except Exception as e:
        logger.exception("Error refreshing models for %s: %s", prov_code, e)
        return JsonResponse({'success': False, 'error': f"Internal error: {str(e)}"}, status=500)


@login_required
@require_http_methods(["GET"])
def ai_config_audit_logs_api(request):
    """
    GET API returning recent sanitized audit logs with pagination support.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'error': 'Forbidden'}), content_type='application/json')

    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    page_size = 10
    total_count = AIConfigurationAuditLog.objects.count()
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages

    start_idx = (page - 1) * page_size
    logs_qs = AIConfigurationAuditLog.objects.order_by('-timestamp')[start_idx:start_idx + page_size]
    data = []
    for log in logs_qs:
        data.append({
            'id': log.id,
            'action': log.get_action_display(),
            'provider': log.provider or 'All',
            'model': log.model_name or '-',
            'status': log.status,
            'latency_ms': log.latency_ms,
            'message': log.message,
            'user': log.performed_by.username if log.performed_by else 'System',
            'created_at': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        })

    return JsonResponse({
        'success': True,
        'logs': data,
        'page': page,
        'total_pages': total_pages,
        'total_count': total_count,
        'has_prev': page > 1,
        'has_next': page < total_pages
    })


@login_required
@require_http_methods(["POST"])
def ai_config_create_provider_api(request):
    """
    POST API to dynamically register a new AI provider / model endpoint.
    Supports any custom OpenAI-compatible endpoint, local model runner, or cloud API.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    try:
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            payload = request.POST.dict()

        provider_id = payload.get('provider', '').strip()
        display_name = payload.get('display_name', '').strip()
        base_url = payload.get('base_url', '').strip()
        default_model = payload.get('default_model', '').strip()
        api_key = payload.get('api_key', '').strip()
        raw_models = payload.get('available_models', [])

        available_models = []
        if isinstance(raw_models, str):
            # Comma-separated or newline-separated
            for m in re.split(r'[,;\n]', raw_models):
                clean_m = m.strip()
                if clean_m:
                    available_models.append({"id": clean_m, "name": clean_m, "is_free_tier": False})
        elif isinstance(raw_models, list):
            available_models = raw_models

        success, message, cfg_obj = create_or_update_custom_provider(
            provider_id=provider_id,
            display_name=display_name,
            base_url=base_url,
            default_model=default_model,
            available_models=available_models,
            api_key=api_key,
            user=request.user,
            ip_address=get_client_ip(request)
        )

        status_code = 200 if success else 400
        return JsonResponse({
            'success': success,
            'message': message,
            'provider': cfg_obj.provider if cfg_obj else provider_id,
            'display_name': cfg_obj.display_name if cfg_obj else display_name,
        }, status=status_code)

    except Exception as e:
        logger.exception("Error creating custom provider: %s", e)
        return JsonResponse({'success': False, 'error': f"Internal error: {str(e)}"}, status=500)


@login_required
@require_http_methods(["POST"])
def ai_config_delete_provider_api(request, provider):
    """
    POST API to safely remove a custom or non-core AI provider configuration.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    try:
        success, message = delete_provider(
            provider_id=provider,
            user=request.user,
            ip_address=get_client_ip(request)
        )
        status_code = 200 if success else 400
        return JsonResponse({'success': success, 'message': message}, status=status_code)

    except Exception as e:
        logger.exception("Error deleting provider %s: %s", provider, e)
        return JsonResponse({'success': False, 'error': f"Internal error: {str(e)}"}, status=500)




# ==============================================================================
# ENTERPRISE CONTROL CENTER APIS: DIAGNOSTICS, TELEMETRY, ROUTING & CATALOG
# ==============================================================================

from modules.admin_panel.services.ai_config_service import (
    search_companies,
    run_company_diagnostic,
    test_routing_and_failover,
    test_all_providers_batch,
    get_model_catalog_list,
)
from modules.admin_panel.services.ai_telemetry_service import telemetry_store


@login_required
@require_http_methods(["GET"])
def ai_config_company_search_api(request):
    """
    GET API to search real company records from MySQL for company-specific AI diagnostics.
    Query parameter: ?q=<search_string>&limit=15
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    q = request.GET.get('q', '').strip()
    limit = min(50, max(1, int(request.GET.get('limit', 15))))
    results = search_companies(query=q, limit=limit)
    return JsonResponse({'success': True, 'count': len(results), 'companies': results})


@login_required
@require_http_methods(["POST"])
def ai_config_company_diagnostic_api(request):
    """
    POST API to execute a bounded, live, read-only AI diagnostic on a specific company.
    Payload: {"company_id": "...", "task": "...", "provider": "...", "model": "..."}
    Guarantees zero database modifications to jobs, CSR projects, or company records.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    try:
        try:
            payload = json.loads(request.body.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            payload = request.POST.dict()

        company_id = payload.get('company_id', '').strip()
        task = payload.get('task', 'homepage_classification').strip()
        provider = payload.get('provider', None)
        model = payload.get('model', None)

        if not company_id:
            return JsonResponse({'success': False, 'error': 'Parameter company_id is required'}, status=400)

        result = run_company_diagnostic(
            company_id=company_id,
            task=task,
            provider_override=provider,
            model_override=model,
            user=request.user,
            ip_address=get_client_ip(request)
        )
        status_code = 200 if result.get('success') else 400
        return JsonResponse(result, status=status_code)

    except Exception as e:
        logger.exception("Error executing company AI diagnostic: %s", e)
        return JsonResponse({'success': False, 'error': f"Internal error: {str(e)}"}, status=500)


@login_required
@require_http_methods(["GET"])
def ai_config_company_history_api(request, company_id=None):
    """
    GET API to retrieve historical AI diagnostic invocations for a company.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    target_id = (company_id or request.GET.get('company_id', '')).strip()
    limit = min(100, max(1, int(request.GET.get('limit', 20))))
    history = telemetry_store.get_company_history(company_id=target_id, limit=limit)
    return JsonResponse({'success': True, 'company_id': target_id, 'count': len(history), 'history': history})


@login_required
@require_http_methods(["POST"])
def ai_config_test_routing_api(request):
    """
    POST API to simulate primary provider failure and verify failover routing to fallback.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    try:
        result = test_routing_and_failover(user=request.user, ip_address=get_client_ip(request))
        return JsonResponse(result, status=200 if result.get('success') else 400)
    except Exception as e:
        logger.exception("Error testing AI routing and failover: %s", e)
        return JsonResponse({'success': False, 'error': f"Internal error: {str(e)}"}, status=500)


@login_required
@require_http_methods(["POST"])
def ai_config_test_all_api(request):
    """
    POST API to sequentially test all configured AI providers with bounded health checks.
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    try:
        results = test_all_providers_batch(user=request.user, ip_address=get_client_ip(request))
        return JsonResponse({'success': True, 'count': len(results), 'results': results})
    except Exception as e:
        logger.exception("Error testing all AI providers: %s", e)
        return JsonResponse({'success': False, 'error': f"Internal error: {str(e)}"}, status=500)


@login_required
@require_http_methods(["GET"])
def ai_config_usage_summary_api(request):
    """
    GET API to retrieve aggregated AI token usage, costs, and request distributions.
    Parameters: ?days=30&provider=all&model=all&company_id=&task=all
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    days = int(request.GET.get('days', 30))
    provider = request.GET.get('provider', 'all')
    model = request.GET.get('model', 'all')
    company_id = request.GET.get('company_id', '')
    task = request.GET.get('task', 'all')

    summary = telemetry_store.get_summary(
        days=days,
        provider=provider,
        model=model,
        company_id=company_id if company_id else None,
        task=task
    )
    return JsonResponse({'success': True, 'summary': summary})


@login_required
@require_http_methods(["GET"])
def ai_config_usage_events_api(request):
    """
    GET API to retrieve paginated, filterable raw AI invocation events.
    Parameters: ?limit=25&offset=0&provider=all&company_id=&task=all&status=all
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    limit = min(100, max(1, int(request.GET.get('limit', 25))))
    offset = max(0, int(request.GET.get('offset', 0)))
    provider = request.GET.get('provider', 'all')
    company_id = request.GET.get('company_id', '')
    task = request.GET.get('task', 'all')
    status = request.GET.get('status', 'all')

    events, total = telemetry_store.get_events(
        limit=limit,
        offset=offset,
        provider=provider,
        company_id=company_id if company_id else None,
        task=task,
        status=status
    )
    return JsonResponse({
        'success': True,
        'count': len(events),
        'total': total,
        'limit': limit,
        'offset': offset,
        'events': events
    })


@login_required
@require_http_methods(["GET"])
def ai_config_model_catalog_api(request):
    """
    GET API to retrieve full model catalog across providers with capability and pricing information.
    Parameter: ?provider=all
    """
    if not is_authorized_admin(request.user):
        return HttpResponseForbidden(json.dumps({'success': False, 'error': 'Forbidden: Administrator permissions required'}), content_type='application/json')

    provider = request.GET.get('provider', 'all')
    catalog = get_model_catalog_list(provider_filter=provider)
    return JsonResponse({'success': True, 'count': len(catalog), 'catalog': catalog})
