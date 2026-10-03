"""
Subscription REST API views — Django-native edition.

All business logic is delegated to
``modules.website.utils.subscription_service``, which is backed entirely
by the Django ORM.  The old ``app.subscription`` (PyMySQL) dependency has
been removed.
"""
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from modules.website.utils.subscription_service import (
    SubscriptionError,
    normalise_tenant,
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
)


def _tenant(request):
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


def get_subscription_plans(request):
    return JsonResponse(plans_payload(), safe=False)


def get_subscription_promos(request):
    return _sub_call(promos_payload)


def get_current_subscription(request):
    return _sub_call(lambda: current(_tenant(request)))


@csrf_exempt
def quote_subscription(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = {}
    return _sub_call(lambda: quote(body, _tenant(request)))


@csrf_exempt
def validate_subscription_promo(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = {}
    return _sub_call(lambda: validate_promo(body, _tenant(request)))


@csrf_exempt
def checkout_subscription(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = {}
    if not body.get('request_id'):
        header_key = request.headers.get('Idempotency-Key')
        if header_key:
            body['request_id'] = header_key
    return _sub_call(lambda: checkout(body, _tenant(request)))


@csrf_exempt
def cancel_subscription(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = {}
    return _sub_call(lambda: cancel(body, _tenant(request)))


@csrf_exempt
def resume_subscription(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        body = {}
    return _sub_call(lambda: resume(body, _tenant(request)))


def subscription_history(request):
    limit = int(request.GET.get('limit', 50))
    return _sub_call(lambda: history(_tenant(request), limit))


def subscription_invoices(request):
    limit = int(request.GET.get('limit', 50))
    return _sub_call(lambda: invoices_payload(_tenant(request), limit))


def subscription_usage(request):
    return _sub_call(lambda: usage_payload(_tenant(request)))


@csrf_exempt
def rotate_subscription_api_key(request):
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    return _sub_call(lambda: rotate_api_key(_tenant(request)))
