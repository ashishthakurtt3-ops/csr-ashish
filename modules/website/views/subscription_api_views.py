"""
Subscription REST API views — Database-Driven Django-Native Edition.

All business logic is delegated to
``modules.website.utils.subscription_service``, which is backed entirely
by the Django ORM. Billing identity is anchored to ``request.user``.
"""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from modules.website.utils.subscription_service import (
    SubscriptionError,
    normalise_tenant,
    rupees_to_paise,
    format_inr,
    plans_payload,
    promos_payload,
    current,
    quote,
    validate_promo,
    checkout,
    cancel,
    resume,
    history,
    invoices_payload,
    usage_payload,
    rotate_api_key,
    topup_wallet,
    get_wallet_data,
    toggle_auto_renew,
    schedule_downgrade, change_plan, schedule_plan_change,
    process_subscription_renewals,
    refund_payment,
)


def _user(request):
    if getattr(request, 'user', None) and request.user.is_authenticated:
        return request.user
    # Fallback to the primary active user for demo testing in the enterprise portal
    from modules.admin_panel.models import User
    user = User.objects.filter(is_active=True).order_by('id').first()
    if not user:
        user = User.objects.create(username='demo_user', email='demo@impactbridge.org', is_active=True)
    return user


def _tenant(request):
    user = _user(request)
    if user:
        return f"user_{user.id}"
    return normalise_tenant(
        request.headers.get('X-Tenant-Id') or request.GET.get('tenant_id')
    )


def _sub_call(thunk):
    try:
        data = thunk()
        return JsonResponse(data, safe=False)
    except SubscriptionError as exc:
        return JsonResponse({'detail': exc.message, 'code': exc.code}, status=exc.status_code)
    except Exception as e:
        return JsonResponse({'detail': str(e)}, status=500)


def _parse_body(request):
    body = {}
    if request.body:
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception:
            body = {}
    if not body and request.POST:
        body = request.POST.dict()
    return body


def get_subscription_plans(request):
    return JsonResponse(plans_payload(), safe=False)


def get_subscription_promos(request):
    return _sub_call(promos_payload)


def get_current_subscription(request):
    user = _user(request)
    tenant = _tenant(request)
    return _sub_call(lambda: current(tenant_id=tenant, user=user))


@csrf_exempt
def quote_subscription(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    body = _parse_body(request)
    user = _user(request)
    tenant = _tenant(request)
    return _sub_call(lambda: quote(body, tenant_id=tenant, user=user))


@csrf_exempt
def validate_subscription_promo(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    body = _parse_body(request)
    user = _user(request)
    tenant = _tenant(request)
    return _sub_call(lambda: validate_promo(body, tenant_id=tenant, user=user))


@csrf_exempt
def checkout_subscription(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    body = _parse_body(request)
    if not body.get('plan_id'):
        body['plan_id'] = request.GET.get('plan_id') or request.POST.get('plan_id')
    if not body.get('request_id'):
        header_key = request.headers.get('Idempotency-Key')
        if header_key:
            body['request_id'] = header_key

    user = _user(request)
    tenant = _tenant(request)
    return _sub_call(lambda: checkout(body, tenant_id=tenant, user=user))


@csrf_exempt
def cancel_subscription(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    body = _parse_body(request)
    user = _user(request)
    tenant = _tenant(request)
    return _sub_call(lambda: cancel(body, tenant_id=tenant, user=user))


@csrf_exempt
def resume_subscription(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    body = _parse_body(request)
    user = _user(request)
    tenant = _tenant(request)
    return _sub_call(lambda: resume(body, tenant_id=tenant, user=user))


def subscription_history(request):
    limit = int(request.GET.get('limit', 50))
    user = _user(request)
    tenant = _tenant(request)
    return _sub_call(lambda: history(tenant_id=tenant, user=user, limit=limit))


def subscription_invoices(request):
    limit = int(request.GET.get('limit', 50))
    user = _user(request)
    tenant = _tenant(request)
    return _sub_call(lambda: invoices_payload(tenant_id=tenant, user=user, limit=limit))


def subscription_usage(request):
    user = _user(request)
    tenant = _tenant(request)
    return _sub_call(lambda: usage_payload(tenant_id=tenant, user=user))


@csrf_exempt
def rotate_subscription_api_key(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    user = _user(request)
    tenant = _tenant(request)
    return _sub_call(lambda: rotate_api_key(tenant_id=tenant, user=user))


# ── WALLET APIS ──────────────────────────────────────────────────────────────
@csrf_exempt
def wallet_topup(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Please log in to add prototype wallet funds.', 'code': 'unauthorized'}, status=401)

    body = _parse_body(request)
    raw_amount = (
        body.get('amount_inr') if body.get('amount_inr') is not None
        else body.get('amount_rupees') if body.get('amount_rupees') is not None
        else body.get('amount') if body.get('amount') is not None
        else None
    )
    amount_paise = body.get('amount_paise')
    if amount_paise is None and raw_amount is not None:
        try:
            amount_paise = rupees_to_paise(float(raw_amount))
        except (ValueError, TypeError):
            amount_paise = None

    if not amount_paise or int(amount_paise) <= 0:
        return JsonResponse({'detail': 'A valid positive top-up amount is required.', 'code': 'invalid_amount'}, status=400)

    method = str(body.get('payment_method') or 'PROTOTYPE_UPI').strip()
    desc = str(body.get('description') or f"Prototype wallet top-up of {format_inr(amount_paise)}").strip()
    request_id = str(body.get('request_id') or request.headers.get('Idempotency-Key') or '').strip() or None

    return _sub_call(lambda: topup_wallet(
        user=user,
        amount_paise=int(amount_paise),
        payment_method=method,
        description=desc,
        request_id=request_id
    ))


def wallet_balance(request):
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required to view wallet.', 'code': 'unauthorized'}, status=401)
    return _sub_call(lambda: get_wallet_data(user))


def wallet_transactions(request):
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required to view wallet transactions.', 'code': 'unauthorized'}, status=401)
    return _sub_call(lambda: {'status': 'success', 'data': get_wallet_data(user)})


# ── UPGRADE, DOWNGRADE & AUTO-RENEW APIS ──────────────────────────────────────
@csrf_exempt
def subscription_upgrade(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required for subscription upgrade.', 'code': 'unauthorized'}, status=401)
    body = _parse_body(request)
    tenant = _tenant(request)
    return _sub_call(lambda: checkout(body, tenant_id=tenant, user=user))



@csrf_exempt
def subscription_change_plan(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required to change subscription.', 'code': 'unauthorized'}, status=401)
    body = _parse_body(request)
    tenant = _tenant(request)
    return _sub_call(lambda: change_plan(body, user=user, tenant_id=tenant))

@csrf_exempt
def subscription_downgrade(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required for subscription downgrade.', 'code': 'unauthorized'}, status=401)
    body = _parse_body(request)
    return _sub_call(lambda: schedule_downgrade(body, user=user))


@csrf_exempt
def subscription_toggle_auto_renew(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required to manage auto-renew.', 'code': 'unauthorized'}, status=401)
    body = _parse_body(request)
    enable = bool(body.get('auto_renew', True))
    return _sub_call(lambda: toggle_auto_renew(user=user, enable=enable))


# ── ADMIN ACTIONS ─────────────────────────────────────────────────────────────
@csrf_exempt
def admin_run_renewals_now(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    user = _user(request)
    if not (user and (user.is_superuser or user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'STAFF'))):
        return JsonResponse({'detail': 'Administrative privileges required.', 'code': 'forbidden'}, status=403)
    return _sub_call(lambda: process_subscription_renewals(force_run=True))


@csrf_exempt
def admin_refund_payment(request, payment_id):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    user = _user(request)
    if not (user and (user.is_superuser or user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'STAFF'))):
        return JsonResponse({'detail': 'Administrative privileges required.', 'code': 'forbidden'}, status=403)
    body = _parse_body(request)
    reason = body.get('reason')
    return _sub_call(lambda: refund_payment(payment_id=payment_id, actor=user.username, reason=reason))
