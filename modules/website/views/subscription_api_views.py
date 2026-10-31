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
    from django.conf import settings
    if getattr(settings, 'ALLOW_DEMO_AUTH_FALLBACK', False):
        from modules.admin_panel.models import User
        return User.objects.filter(is_active=True).order_by('id').first()
    return None


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
    """Customer-facing downgrade is BLOCKED. Only admin/staff can downgrade."""
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required.', 'code': 'unauthorized'}, status=401)
    # Only admin/staff can execute downgrades
    if not (user.is_superuser or user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'STAFF')):
        return JsonResponse({
            'detail': 'Plan downgrades are not available from the customer portal. '
                      'Please contact support if you need to change your plan.',
            'code': 'downgrade_blocked'
        }, status=403)
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


# ── SAVED RECORDS API ─────────────────────────────────────────────────────────
from modules.website.utils.entitlement_service import EntitlementService, EntitlementError
from modules.admin_panel.models import SavedRecord, SavedSearch, TeamMembership, CompanyRefreshRequest


@csrf_exempt
def saved_records_api(request):
    """GET: list saved records. POST: save a record. DELETE: unsave a record."""
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required.', 'code': 'unauthorized'}, status=401)

    svc = EntitlementService(user)

    if request.method == 'GET':
        records = SavedRecord.objects.filter(user=user).select_related('job', 'csr_project')
        data = []
        for r in records:
            data.append({
                'id': r.id,
                'item_type': r.item_type,
                'title': r.title,
                'company_name': r.company_name,
                'notes': r.notes,
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'job_id': r.job_id,
                'csr_project_id': r.csr_project_id,
            })
        quota = svc.saved_records_limit
        return JsonResponse({
            'status': 'success',
            'count': len(data),
            'limit': quota,
            'unlimited': quota is None,
            'records': data,
        })

    elif request.method == 'POST':
        body = _parse_body(request)
        item_type = body.get('item_type', 'JOB').upper()
        item_id = body.get('item_id')
        notes = body.get('notes', '')

        if not item_id:
            return JsonResponse({'detail': 'item_id is required.', 'code': 'invalid'}, status=400)

        try:
            svc.check_can_save_record()
        except EntitlementError as e:
            return JsonResponse({
                'detail': e.message,
                'code': 'quota_exceeded',
                'feature': e.feature,
                'limit': e.limit,
                'current': e.current,
                'upgrade_to': e.upgrade_to,
            }, status=403)

        from modules.admin_panel.models import Job, CSRProject
        kwargs = {'user': user, 'item_type': item_type, 'notes': notes}
        if item_type == 'JOB':
            j_obj = Job.objects.filter(pk=item_id).first() or Job.objects.filter(job_id=str(item_id)).first()
            if not j_obj:
                return JsonResponse({'detail': 'Job opening not found.', 'code': 'not_found'}, status=404)
            kwargs['job'] = j_obj
        elif item_type == 'CSR_PROJECT':
            c_obj = CSRProject.objects.filter(pk=item_id).first() or CSRProject.objects.filter(csr_id=str(item_id)).first()
            if not c_obj:
                return JsonResponse({'detail': 'CSR project not found.', 'code': 'not_found'}, status=404)
            kwargs['csr_project'] = c_obj

        # Prevent duplicate saves
        existing = SavedRecord.objects.filter(
            user=user, item_type=item_type,
            **({'job': kwargs.get('job')} if item_type == 'JOB' else {'csr_project': kwargs.get('csr_project')})
        ).first()
        if existing:
            return JsonResponse({'status': 'success', 'message': 'Already saved.', 'id': existing.id})

        record = SavedRecord.objects.create(**kwargs)
        return JsonResponse({
            'status': 'success',
            'message': 'Record saved.',
            'id': record.id,
            'count': svc.saved_records_count,
            'limit': svc.saved_records_limit,
        }, status=201)

    elif request.method == 'DELETE':
        body = _parse_body(request)
        record_id = body.get('id') or body.get('record_id')
        if not record_id:
            return JsonResponse({'detail': 'Record id is required.', 'code': 'invalid'}, status=400)
        deleted, _ = SavedRecord.objects.filter(user=user, id=int(record_id)).delete()
        return JsonResponse({
            'status': 'success',
            'deleted': deleted > 0,
            'count': svc.saved_records_count,
            'limit': svc.saved_records_limit,
        })

    return JsonResponse({'detail': 'Method not allowed'}, status=405)


# ── SAVED SEARCHES API ────────────────────────────────────────────────────────
@csrf_exempt
def saved_searches_api(request):
    """GET: list saved searches. POST: save a search. DELETE: remove a search."""
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required.', 'code': 'unauthorized'}, status=401)

    svc = EntitlementService(user)

    if request.method == 'GET':
        searches = SavedSearch.objects.filter(user=user, is_active=True)
        data = []
        for s in searches:
            data.append({
                'id': s.id,
                'name': s.name,
                'search_type': s.search_type,
                'query_params': s.query_params,
                'alert_frequency': s.alert_frequency,
                'created_at': s.created_at.isoformat() if s.created_at else None,
            })
        return JsonResponse({
            'status': 'success',
            'count': len(data),
            'limit': svc.saved_searches_limit,
            'searches': data,
        })

    elif request.method == 'POST':
        body = _parse_body(request)
        name = body.get('name', '').strip()
        if not name:
            return JsonResponse({'detail': 'Search name is required.', 'code': 'invalid'}, status=400)

        try:
            svc.check_can_save_search()
        except EntitlementError as e:
            return JsonResponse({
                'detail': e.message,
                'code': 'quota_exceeded',
                'feature': e.feature,
                'limit': e.limit,
                'current': e.current,
                'upgrade_to': e.upgrade_to,
            }, status=403)

        alert_freq = body.get('alert_frequency', svc.allowed_alert_frequency)
        try:
            svc.check_alert_frequency(alert_freq)
        except EntitlementError as e:
            alert_freq = svc.allowed_alert_frequency

        search = SavedSearch.objects.create(
            user=user,
            name=name,
            search_type=body.get('search_type', 'JOBS'),
            query_params=body.get('query_params', {}),
            alert_frequency=alert_freq,
        )
        return JsonResponse({
            'status': 'success',
            'message': 'Search saved.',
            'id': search.id,
            'count': svc.saved_searches_count,
            'limit': svc.saved_searches_limit,
        }, status=201)

    elif request.method == 'DELETE':
        body = _parse_body(request)
        search_id = body.get('id') or body.get('search_id')
        if not search_id:
            return JsonResponse({'detail': 'Search id is required.', 'code': 'invalid'}, status=400)
        deleted, _ = SavedSearch.objects.filter(user=user, id=int(search_id)).delete()
        return JsonResponse({
            'status': 'success',
            'deleted': deleted > 0,
            'count': svc.saved_searches_count,
            'limit': svc.saved_searches_limit,
        })

    return JsonResponse({'detail': 'Method not allowed'}, status=405)


# ── TEAM MEMBERS API ──────────────────────────────────────────────────────────
@csrf_exempt
def team_members_api(request):
    """GET: list team. POST: invite member. DELETE: revoke member."""
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required.', 'code': 'unauthorized'}, status=401)

    svc = EntitlementService(user)

    if request.method == 'GET':
        members = TeamMembership.objects.filter(owner=user).exclude(status='REVOKED')
        data = [{
            'id': m.id,
            'invited_email': m.invited_email,
            'role': m.role,
            'status': m.status,
            'created_at': m.created_at.isoformat() if m.created_at else None,
        } for m in members]
        return JsonResponse({
            'status': 'success',
            'count': svc.active_team_members_count,
            'limit': svc.team_members_limit,
            'members': data,
        })

    elif request.method == 'POST':
        body = _parse_body(request)
        email = body.get('email', '').strip().lower()
        if not email or '@' not in email:
            return JsonResponse({'detail': 'Valid email is required.', 'code': 'invalid'}, status=400)

        try:
            svc.check_can_add_team_member()
        except EntitlementError as e:
            return JsonResponse({
                'detail': e.message,
                'code': 'quota_exceeded',
                'feature': e.feature,
                'limit': e.limit,
                'current': e.current,
                'upgrade_to': e.upgrade_to,
            }, status=403)

        import secrets
        member, created = TeamMembership.objects.get_or_create(
            owner=user,
            invited_email=email,
            defaults={
                'role': body.get('role', 'MEMBER'),
                'status': 'INVITED',
                'invitation_token': secrets.token_hex(32),
            }
        )
        if not created and member.status == 'REVOKED':
            member.status = 'INVITED'
            member.invitation_token = secrets.token_hex(32)
            member.save()
            created = True

        return JsonResponse({
            'status': 'success',
            'message': 'Invitation sent.' if created else 'Already invited.',
            'id': member.id,
        }, status=201 if created else 200)

    elif request.method == 'DELETE':
        body = _parse_body(request)
        member_id = body.get('id') or body.get('member_id')
        if not member_id:
            return JsonResponse({'detail': 'Member id is required.', 'code': 'invalid'}, status=400)
        updated = TeamMembership.objects.filter(
            owner=user, id=int(member_id)
        ).update(status='REVOKED')
        return JsonResponse({
            'status': 'success',
            'revoked': updated > 0,
            'count': svc.active_team_members_count,
        })

    return JsonResponse({'detail': 'Method not allowed'}, status=405)


# ── COMPANY REFRESH REQUEST API ───────────────────────────────────────────────
@csrf_exempt
def company_refresh_api(request):
    """POST: request a company data refresh (Ultra only)."""
    if request.method != 'POST':
        return JsonResponse({'detail': 'Method not allowed'}, status=405)
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required.', 'code': 'unauthorized'}, status=401)

    svc = EntitlementService(user)
    try:
        svc.check_can_request_refresh()
    except EntitlementError as e:
        return JsonResponse({
            'detail': e.message,
            'code': 'feature_locked',
            'feature': e.feature,
            'upgrade_to': e.upgrade_to,
        }, status=403)

    body = _parse_body(request)
    company_id = body.get('company_id')
    if not company_id:
        return JsonResponse({'detail': 'company_id is required.', 'code': 'invalid'}, status=400)

    from modules.admin_panel.models import Company
    company = Company.objects.filter(company_id=company_id).first()
    if not company:
        return JsonResponse({'detail': 'Company not found.', 'code': 'not_found'}, status=404)

    req = CompanyRefreshRequest.objects.create(
        user=user,
        company=company,
        reason=body.get('reason', ''),
    )
    return JsonResponse({
        'status': 'success',
        'message': f'Refresh request submitted for {company.company_name}.',
        'request_id': req.id,
    }, status=201)


# ── SUBSCRIPTION COMPARISON TABLE API ─────────────────────────────────────────
def subscription_comparison_api(request):
    """GET: dynamic plan comparison matrix from database entitlements."""
    from modules.admin_panel.models import Plan, PlanEntitlement

    active_plans = Plan.objects.filter(
        is_active=True, is_visible=True
    ).order_by('display_order')

    plans_list = []
    for p in active_plans:
        plans_list.append({
            'code': p.code,
            'name': p.name,
            'badge': p.badge,
            'is_recommended': p.is_recommended,
            'monthly_price_paise': p.monthly_price_paise,
            'yearly_price_paise': p.yearly_price_paise,
        })

    # Build comparison rows from PlanEntitlement records
    # Get all unique feature_keys across active plans
    feature_keys = list(
        PlanEntitlement.objects.filter(plan__in=active_plans)
        .values_list('feature_key', flat=True)
        .distinct()
        .order_by('pk')
    )

    # Deduplicate while preserving order
    seen = set()
    ordered_keys = []
    for k in feature_keys:
        if k not in seen:
            seen.add(k)
            ordered_keys.append(k)

    rows = []
    for key in ordered_keys:
        row = {'feature_key': key, 'display_name': '', 'values': {}}
        for plan in active_plans:
            ent = PlanEntitlement.objects.filter(plan=plan, feature_key=key).first()
            if ent:
                row['display_name'] = ent.display_name
                if ent.is_unlimited:
                    row['values'][plan.code] = {'type': 'unlimited', 'display': 'Unlimited'}
                elif ent.feature_type == 'BOOLEAN':
                    row['values'][plan.code] = {
                        'type': 'boolean',
                        'value': ent.boolean_value,
                        'display': 'Yes' if ent.boolean_value else 'No',
                    }
                elif ent.feature_type == 'NUMERIC':
                    display = str(ent.numeric_value) if ent.numeric_value else '0'
                    row['values'][plan.code] = {
                        'type': 'numeric',
                        'value': ent.numeric_value,
                        'display': display,
                    }
                elif ent.feature_type == 'TEXT':
                    row['values'][plan.code] = {
                        'type': 'text',
                        'value': ent.text_value,
                        'display': ent.text_value or '',
                    }
            else:
                row['values'][plan.code] = {'type': 'boolean', 'value': False, 'display': 'No'}
        rows.append(row)

    return JsonResponse({
        'status': 'success',
        'plans': plans_list,
        'features': rows,
    })


# ── USER QUOTA SUMMARY API ───────────────────────────────────────────────────
def user_quota_api(request):
    """GET: returns the authenticated user's current quota usage and limits."""
    user = _user(request)
    if not user:
        return JsonResponse({'detail': 'Authentication required.', 'code': 'unauthorized'}, status=401)
    svc = EntitlementService(user)
    return JsonResponse({
        'status': 'success',
        'quota': svc.quota_summary(),
    })
