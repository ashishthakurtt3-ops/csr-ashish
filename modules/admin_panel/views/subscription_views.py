import json
import uuid
from datetime import datetime, timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.http import HttpResponse, JsonResponse

from modules.admin_panel.models import (
    Subscription, Invoice, PromoCode, SubscriptionEvent,
    Plan, PlanEntitlement, Wallet, WalletTransaction, Payment, User
)
from modules.website.utils.subscription_service import (
    rupees_to_paise, paise_to_rupees, format_inr,
    process_subscription_renewals, refund_payment, _now
)


def _is_admin(user):
    return user.is_superuser or user.is_staff or getattr(user, 'role', '') in ('ADMIN', 'STAFF')


@login_required
def subscription_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    plan_id = request.GET.get('plan', '').strip()
    status = request.GET.get('status', '').strip()
    search = request.GET.get('q', '').strip()
    page_num = request.GET.get('page', 1)

    qs = Subscription.objects.select_related('user', 'plan_record').all().order_by('-created_at')

    if plan_id and plan_id != 'all':
        qs = qs.filter(Q(plan_id=plan_id) | Q(plan_record__code=plan_id))
    if status and status != 'all':
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            Q(subscription_id__icontains=search) |
            Q(tenant_id__icontains=search) |
            Q(organization_name__icontains=search) |
            Q(contact_email__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search)
        )

    # Billing KPI Aggregations
    total_subscriptions = Subscription.objects.count()
    active_subscribers = Subscription.objects.filter(status='ACTIVE').exclude(plan_id='starter').count()
    free_subscribers = Subscription.objects.filter(Q(plan_id='starter') | Q(status='EXPIRED')).count()
    auto_renew_count = Subscription.objects.filter(auto_renew=True, status='ACTIVE').count()
    total_proto_revenue_paise = Payment.objects.filter(payment_status='SUCCESS', is_prototype=True).aggregate(s=Sum('amount_paise'))['s'] or 0
    total_wallets_paise = Wallet.objects.aggregate(s=Sum('balance_paise'))['s'] or 0

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_num)

    plans_list = Plan.objects.all().order_by('display_order')

    return render(request, 'admin/subscriptions/list.html', {
        'page_obj': page_obj,
        'selected_plan': plan_id,
        'selected_status': status,
        'search_query': search,
        'total_count': paginator.count,
        'plans_list': plans_list,
        'kpis': {
            'total_subscriptions': total_subscriptions,
            'active_subscribers': active_subscribers,
            'free_subscribers': free_subscribers,
            'auto_renew_count': auto_renew_count,
            'total_revenue_display': format_inr(total_proto_revenue_paise),
            'total_wallets_display': format_inr(total_wallets_paise),
        }
    })


@login_required
def subscription_detail_manage_view(request, sub_id):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    sub = get_object_or_404(Subscription.objects.select_related('user', 'plan_record'), subscription_id=sub_id)
    plans = Plan.objects.all().order_by('display_order')
    user = sub.user
    wallet = Wallet.objects.filter(user=user).first() if user else None
    payments = Payment.objects.filter(subscription=sub).order_by('-created_at')[:10]
    invoices = Invoice.objects.filter(subscription_id=sub.subscription_id).order_by('-invoice_id')[:10]
    events = SubscriptionEvent.objects.filter(tenant_id=sub.tenant_id).order_by('-event_id')[:15]

    if request.method == 'POST':
        action = request.POST.get('action')
        now_str = _now()

        if action == 'change_plan':
            new_plan_code = request.POST.get('new_plan')
            new_plan = get_object_or_404(Plan, code=new_plan_code)
            old_plan = sub.plan_id
            sub.plan_record = new_plan
            sub.plan_id = new_plan.code
            sub.save(update_fields=['plan_record', 'plan_id', 'updated_at'])

            SubscriptionEvent.objects.create(
                subscription_id=sub.subscription_id,
                tenant_id=sub.tenant_id,
                event_type='ADMIN_PLAN_CHANGE',
                from_plan=old_plan,
                to_plan=new_plan.code,
                amount_paise=0,
                notes=f"Plan manually changed to {new_plan.name} by admin {request.user.username}.",
                actor=request.user.username,
                created_at=now_str
            )
            messages.success(request, f"Subscription plan changed to {new_plan.name}.")

        elif action == 'toggle_auto_renew':
            sub.auto_renew = not sub.auto_renew
            sub.save(update_fields=['auto_renew', 'updated_at'])
            SubscriptionEvent.objects.create(
                subscription_id=sub.subscription_id,
                tenant_id=sub.tenant_id,
                event_type='AUTO_RENEW_ENABLED' if sub.auto_renew else 'AUTO_RENEW_DISABLED',
                from_plan=sub.plan_id, to_plan=sub.plan_id, amount_paise=0,
                notes=f"Auto-renewal toggled to {'ON' if sub.auto_renew else 'OFF'} by admin.",
                actor=request.user.username, created_at=now_str
            )
            messages.success(request, f"Auto-renew set to {'ON' if sub.auto_renew else 'OFF'}.")

        elif action == 'cancel_immediate':
            reason = request.POST.get('cancel_reason', 'Cancelled by administrator.')
            starter = Plan.objects.filter(code='starter').first()
            sub.status = 'CANCELED'
            sub.plan_record = starter
            sub.plan_id = 'starter'
            sub.cancel_at_period_end = False
            sub.auto_renew = False
            sub.canceled_at = now_str
            sub.cancel_reason = reason
            sub.save()

            SubscriptionEvent.objects.create(
                subscription_id=sub.subscription_id,
                tenant_id=sub.tenant_id,
                event_type='CANCEL_IMMEDIATE',
                from_plan=sub.plan_id, to_plan='starter', amount_paise=0,
                notes=f"Admin immediate cancellation: {reason}",
                actor=request.user.username, created_at=now_str
            )
            messages.success(request, "Subscription immediately cancelled and reverted to Community Starter.")

        elif action == 'reactivate':
            sub.status = 'ACTIVE'
            sub.auto_renew = True
            sub.cancel_at_period_end = False
            sub.canceled_at = None
            sub.cancel_reason = None
            sub.save()

            SubscriptionEvent.objects.create(
                subscription_id=sub.subscription_id,
                tenant_id=sub.tenant_id,
                event_type='CANCEL_REVERSED',
                from_plan=sub.plan_id, to_plan=sub.plan_id, amount_paise=0,
                notes="Subscription reactivated by administrator.",
                actor=request.user.username, created_at=now_str
            )
            messages.success(request, "Subscription successfully reactivated.")

        elif action == 'change_cycle':
            new_cycle = request.POST.get('new_cycle', 'monthly').strip().lower()
            old_cycle = sub.billing_cycle
            sub.billing_cycle = new_cycle
            sub.save(update_fields=['billing_cycle', 'updated_at'])
            SubscriptionEvent.objects.create(
                subscription_id=sub.subscription_id,
                tenant_id=sub.tenant_id,
                event_type='ADMIN_CYCLE_CHANGE',
                from_plan=sub.plan_id, to_plan=sub.plan_id, amount_paise=0,
                notes=f"Billing cycle changed from {old_cycle} to {new_cycle} by admin {request.user.username}.",
                actor=request.user.username, created_at=now_str
            )
            messages.success(request, f"Billing cycle updated to {new_cycle}.")

        elif action == 'change_renewal_date':
            new_date = request.POST.get('new_renewal_date')
            if new_date:
                old_date = str(sub.current_period_end)[:10]
                sub.current_period_end = new_date
                sub.save(update_fields=['current_period_end', 'updated_at'])
                SubscriptionEvent.objects.create(
                    subscription_id=sub.subscription_id,
                    tenant_id=sub.tenant_id,
                    event_type='ADMIN_RENEWAL_DATE_CHANGE',
                    from_plan=sub.plan_id, to_plan=sub.plan_id, amount_paise=0,
                    notes=f"Renewal date updated from {old_date} to {new_date} by admin {request.user.username}.",
                    actor=request.user.username, created_at=now_str
                )
                messages.success(request, f"Next renewal date successfully set to {new_date}.")

        elif action == 'expire':
            starter = Plan.objects.filter(code='starter').first()
            old_plan = sub.plan_id
            sub.status = 'EXPIRED'
            sub.plan_record = starter
            sub.plan_id = 'starter'
            sub.auto_renew = False
            sub.save(update_fields=['status', 'plan_record', 'plan_id', 'auto_renew', 'updated_at'])
            SubscriptionEvent.objects.create(
                subscription_id=sub.subscription_id,
                tenant_id=sub.tenant_id,
                event_type='EXPIRED',
                from_plan=old_plan, to_plan='starter', amount_paise=0,
                notes=f"Subscription manually expired by admin {request.user.username}.",
                actor=request.user.username, created_at=now_str
            )
            messages.success(request, "Subscription status changed to EXPIRED.")

        elif action == 'refund':
            last_payment = Payment.objects.filter(subscription=sub, payment_status='SUCCESS').first()
            if last_payment and last_payment.amount_paise > 0:
                try:
                    refund_payment(last_payment.payment_id, actor=request.user.username, reason="Admin subscription refund")
                    messages.success(request, f"Refund of {format_inr(last_payment.amount_paise)} processed to user wallet.")
                except Exception as ex:
                    messages.error(request, f"Refund failed: {str(ex)}")
            else:
                messages.error(request, "No refundable payment found for this subscription.")

        return redirect('admin_subscriptions:manage', sub_id=sub.subscription_id)

    return render(request, 'admin/subscriptions/manage_subscription.html', {
        'sub': sub,
        'plans': plans,
        'wallet': wallet,
        'payments': payments,
        'invoices': invoices,
        'events': events,
    })


# ── PLAN MANAGEMENT ──────────────────────────────────────────────────────────
@login_required
def plan_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    plans = Plan.objects.all().order_by('display_order', 'monthly_price_paise')
    return render(request, 'admin/subscriptions/plans_list.html', {
        'plans': plans,
        'total_plans': plans.count()
    })


@login_required
def plan_create_edit_view(request, code=None):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    plan = get_object_or_404(Plan, code=code) if code else None

    if request.method == 'POST':
        plan_code = request.POST.get('code', '').strip().lower()
        if not plan_code and plan:
            plan_code = plan.code

        name = request.POST.get('name', '').strip()
        slug = request.POST.get('slug', '').strip() or plan_code
        desc = request.POST.get('description', '').strip()
        badge = request.POST.get('badge', '').strip()
        cta_text = request.POST.get('cta_text', '').strip() or 'Select Plan'
        billing_note = request.POST.get('billing_note', '').strip()

        monthly_inr = float(request.POST.get('monthly_price_inr') or 0)
        yearly_inr = float(request.POST.get('yearly_price_inr') or 0)
        monthly_paise = rupees_to_paise(monthly_inr)
        yearly_paise = rupees_to_paise(yearly_inr)

        renewal_inr = request.POST.get('renewal_price_inr')
        renewal_paise = rupees_to_paise(float(renewal_inr)) if renewal_inr and renewal_inr.strip() else monthly_paise

        wallet_deduct_inr = request.POST.get('wallet_deduction_inr')
        wallet_deduct_paise = rupees_to_paise(float(wallet_deduct_inr)) if wallet_deduct_inr and wallet_deduct_inr.strip() else monthly_paise

        currency = request.POST.get('currency', 'INR').strip() or 'INR'
        discount_percent = int(request.POST.get('discount_percent') or 0)
        savings_text = request.POST.get('savings_text', '').strip() or None
        card_description = request.POST.get('card_description', '').strip() or None
        additional_info = request.POST.get('additional_info', '').strip() or None
        button_text = request.POST.get('button_text', '').strip() or 'Change Plan'
        button_visible = bool(request.POST.get('button_visible'))
        button_order = int(request.POST.get('button_order') or 1)
        terms = request.POST.get('terms', '').strip() or None
        notes = request.POST.get('notes', '').strip() or None

        is_active = bool(request.POST.get('is_active'))
        is_visible = bool(request.POST.get('is_visible'))
        is_popular = bool(request.POST.get('is_popular'))
        is_recommended = bool(request.POST.get('is_recommended'))
        is_contact_sales = bool(request.POST.get('is_contact_sales'))
        allow_upgrade = bool(request.POST.get('allow_upgrade'))
        allow_downgrade = bool(request.POST.get('allow_downgrade'))
        allow_cancel = bool(request.POST.get('allow_cancel'))
        auto_renew_default = bool(request.POST.get('auto_renew_default'))

        display_order = int(request.POST.get('display_order') or 0)
        trial_days = int(request.POST.get('trial_days') or 0)

        # Parse features list (newline separated)
        features_raw = request.POST.get('features', '') or request.POST.get('features_text', '')
        features_list = [f.strip() for f in features_raw.split('\n') if f.strip()]

        highlight_raw = request.POST.get('highlight_features', '')
        highlight_list = [h.strip() for h in highlight_raw.split('\n') if h.strip()]

        # Limits / entitlements
        daily_matches = request.POST.get('limit_daily_matches')
        daily_matches_val = None if daily_matches in ('', 'None', 'unlimited') else int(daily_matches)
        api_access = bool(request.POST.get('limit_api_access'))
        live_reprobe = bool(request.POST.get('limit_live_reprobe'))
        view_contacts = bool(request.POST.get('limit_view_contacts'))
        audit_packs = bool(request.POST.get('limit_audit_packs'))
        seats = int(request.POST.get('limit_seats') or 1)
        export_rows = request.POST.get('limit_export_rows')
        export_rows_val = None if export_rows in ('', 'None', 'unlimited') else int(export_rows)
        crm_limit = int(request.POST.get('limit_crm') or 10)

        jobs_raw = request.POST.get('limit_jobs')
        jobs_val = None if jobs_raw in ('', 'None', 'unlimited') else int(jobs_raw)

        api_req_raw = request.POST.get('limit_api_requests')
        api_req_val = None if api_req_raw in ('', 'None', 'unlimited') else int(api_req_raw)

        storage_val = request.POST.get('limit_storage', '').strip() or '10 GB'

        credits_raw = request.POST.get('limit_credits')
        credits_val = None if credits_raw in ('', 'None', 'unlimited') else int(credits_raw)

        search_raw = request.POST.get('limit_search')
        search_val = None if search_raw in ('', 'None', 'unlimited') else int(search_raw)

        export_limit_raw = request.POST.get('limit_export')
        export_limit_val = None if export_limit_raw in ('', 'None', 'unlimited') else int(export_limit_raw)

        limits_dict = {
            'daily_matches': daily_matches_val,
            'api_access': api_access,
            'live_reprobe': live_reprobe,
            'view_contacts': view_contacts,
            'audit_packs': audit_packs,
            'seats': seats,
            'export_rows_per_month': export_rows_val,
            'crm_limit': crm_limit,
            'jobs': jobs_val,
            'api_requests': api_req_val,
            'storage': storage_val,
            'credits': credits_val,
            'search_limit': search_val,
            'export_limit': export_limit_val,
        }

        defaults = {
            'name': name,
            'slug': slug,
            'description': desc,
            'badge': badge,
            'cta_text': cta_text,
            'billing_note': billing_note,
            'monthly_price_paise': monthly_paise,
            'yearly_price_paise': yearly_paise,
            'currency': currency,
            'renewal_price_paise': renewal_paise,
            'wallet_deduction_paise': wallet_deduct_paise,
            'discount_percent': discount_percent,
            'savings_text': savings_text,
            'card_description': card_description,
            'additional_info': additional_info,
            'button_text': button_text,
            'button_visible': button_visible,
            'button_order': button_order,
            'terms': terms,
            'notes': notes,
            'is_active': is_active,
            'is_visible': is_visible,
            'is_popular': is_popular,
            'is_recommended': is_recommended,
            'is_contact_sales': is_contact_sales,
            'display_order': display_order,
            'trial_days': trial_days,
            'allow_upgrade': allow_upgrade,
            'allow_downgrade': allow_downgrade,
            'allow_cancel': allow_cancel,
            'auto_renew_default': auto_renew_default,
            'features': features_list,
            'highlight_features': highlight_list,
            'limits': limits_dict,
        }

        plan_obj, created = Plan.objects.update_or_create(code=plan_code, defaults=defaults)

        # Update structured entitlements
        entitlements_spec = [
            ('daily_matches', 'Daily Matchmaker Queries', PlanEntitlement.TYPE_UNLIMITED if daily_matches_val is None else PlanEntitlement.TYPE_NUMERIC, daily_matches_val, daily_matches_val is None),
            ('api_access', 'REST API Access', PlanEntitlement.TYPE_BOOLEAN, api_access, False),
            ('live_reprobe', 'Live Domain Socket Probing', PlanEntitlement.TYPE_BOOLEAN, live_reprobe, False),
            ('view_contacts', 'Unmasked Corporate Direct Contacts', PlanEntitlement.TYPE_BOOLEAN, view_contacts, False),
            ('audit_packs', 'Section 135 Audit Packs', PlanEntitlement.TYPE_BOOLEAN, audit_packs, False),
            ('seats', 'Team Seats', PlanEntitlement.TYPE_NUMERIC, seats, False),
            ('export_rows_per_month', 'Monthly CSV Export Rows', PlanEntitlement.TYPE_UNLIMITED if export_rows_val is None else PlanEntitlement.TYPE_NUMERIC, export_rows_val, export_rows_val is None),
            ('crm_limit', 'Outreach CRM Pipeline Limit', PlanEntitlement.TYPE_NUMERIC, crm_limit, False),
            ('jobs', 'Jobs Limit', PlanEntitlement.TYPE_UNLIMITED if jobs_val is None else PlanEntitlement.TYPE_NUMERIC, jobs_val, jobs_val is None),
            ('api_requests', 'API Requests Limit', PlanEntitlement.TYPE_UNLIMITED if api_req_val is None else PlanEntitlement.TYPE_NUMERIC, api_req_val, api_req_val is None),
            ('credits', 'Credits Limit', PlanEntitlement.TYPE_UNLIMITED if credits_val is None else PlanEntitlement.TYPE_NUMERIC, credits_val, credits_val is None),
            ('search_limit', 'Search Queries Limit', PlanEntitlement.TYPE_UNLIMITED if search_val is None else PlanEntitlement.TYPE_NUMERIC, search_val, search_val is None),
            ('storage', 'Storage Allowance', PlanEntitlement.TYPE_TEXT, storage_val, False),
        ]

        for k, dname, etype, val, is_unlim in entitlements_spec:
            PlanEntitlement.objects.update_or_create(
                plan=plan_obj, feature_key=k,
                defaults={
                    'display_name': dname,
                    'feature_type': etype,
                    'is_unlimited': is_unlim,
                    'boolean_value': val if isinstance(val, bool) else False,
                    'numeric_value': val if isinstance(val, int) and not isinstance(val, bool) else None,
                    'text_value': val if isinstance(val, str) else None,
                }
            )

        messages.success(request, f"Plan '{plan_obj.name}' successfully {'created' if created else 'saved'}!")
        return redirect('admin_subscriptions:plans')

    features_str = '\n'.join(plan.features) if plan and plan.features else ''
    highlight_str = '\n'.join(plan.highlight_features) if plan and plan.highlight_features else ''
    limits = plan.get_limits_and_entitlements() if plan else {}

    return render(request, 'admin/subscriptions/plan_form.html', {
        'plan': plan,
        'features_str': features_str,
        'highlight_str': highlight_str,
        'limits': limits,
        'is_new': not bool(plan),
        'is_edit': bool(plan),
    })

@login_required
def plan_duplicate_view(request, code):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    original = get_object_or_404(Plan, code=code)
    new_code = f"{original.code}_copy_{uuid.uuid4().hex[:4]}"
    new_name = f"{original.name} (Copy)"
    new_slug = f"{original.slug}-copy-{uuid.uuid4().hex[:4]}"

    new_plan = Plan.objects.create(
        code=new_code,
        name=new_name,
        slug=new_slug,
        description=original.description,
        badge=original.badge,
        cta_text=original.cta_text,
        billing_note=original.billing_note,
        monthly_price_paise=original.monthly_price_paise,
        yearly_price_paise=original.yearly_price_paise,
        currency=original.currency,
        is_active=False,  # default draft
        is_visible=False,
        is_popular=False,
        is_contact_sales=original.is_contact_sales,
        display_order=original.display_order + 1,
        trial_days=original.trial_days,
        allow_upgrade=original.allow_upgrade,
        allow_downgrade=original.allow_downgrade,
        allow_cancel=original.allow_cancel,
        auto_renew_default=original.auto_renew_default,
        features=original.features,
        highlight_features=original.highlight_features,
        limits=original.limits,
        is_recommended=original.is_recommended,
        discount_percent=original.discount_percent,
        savings_text=original.savings_text,
        renewal_price_paise=original.renewal_price_paise,
        wallet_deduction_paise=original.wallet_deduction_paise,
        card_description=original.card_description,
        additional_info=original.additional_info,
        button_text=original.button_text,
        button_visible=original.button_visible,
        button_order=original.button_order,
        terms=original.terms,
        notes=original.notes,
    )

    # Copy entitlements
    for ent in original.entitlements.all():
        PlanEntitlement.objects.create(
            plan=new_plan,
            feature_key=ent.feature_key,
            display_name=ent.display_name,
            feature_type=ent.feature_type,
            boolean_value=ent.boolean_value,
            numeric_value=ent.numeric_value,
            text_value=ent.text_value,
            is_unlimited=ent.is_unlimited,
        )

    messages.success(request, f"Plan duplicated as draft: '{new_name}' ({new_code}).")
    return redirect('admin_subscriptions:plan_edit', code=new_code)


@login_required
def plan_toggle_status_view(request, code):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    plan = get_object_or_404(Plan, code=code)
    plan.is_active = not plan.is_active
    plan.save(update_fields=['is_active'])
    status_label = "Activated" if plan.is_active else "Deactivated"
    messages.success(request, f"Plan '{plan.name}' has been {status_label}.")
    return redirect('admin_subscriptions:plans')


@login_required
def plan_delete_view(request, code):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    plan = get_object_or_404(Plan, code=code)
    # Check if subscriptions are on this plan
    active_subs = Subscription.objects.filter(plan_id=plan.code).count()
    if active_subs > 0:
        messages.error(request, f"Cannot delete plan '{plan.name}' because {active_subs} subscription(s) are currently attached. Deactivate it instead.")
        return redirect('admin_subscriptions:plans')

    plan.delete()
    messages.success(request, f"Plan '{plan.name}' deleted successfully.")
    return redirect('admin_subscriptions:plans')


# ── PAYMENT MANAGEMENT (READ-ONLY FINANCIAL AUDIT) ───────────────────────────
@login_required
def payment_list_view(request):
    """
    Read-only payment ledger for administrators.
    Displays all payments, timing breakdown, customer attribution, plan details, and transaction audits.
    """
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    status_filter = request.GET.get('status', '').strip().upper()
    type_filter = request.GET.get('type', '').strip().upper()
    method_filter = request.GET.get('method', '').strip().upper()
    plan_filter = request.GET.get('plan', '').strip().lower()
    sort_filter = request.GET.get('sort', 'newest').strip().lower()
    search = request.GET.get('q', '').strip()
    page_num = request.GET.get('page', 1)

    qs = Payment.objects.select_related('user', 'subscription', 'subscription__plan_record').all()

    # Filters
    if status_filter and status_filter != 'ALL':
        qs = qs.filter(payment_status=status_filter)
    if type_filter and type_filter != 'ALL':
        qs = qs.filter(payment_type=type_filter)
    if method_filter and method_filter != 'ALL':
        qs = qs.filter(payment_method__iexact=method_filter)
    if plan_filter and plan_filter != 'all':
        qs = qs.filter(Q(plan_code__iexact=plan_filter) | Q(subscription__plan_id__iexact=plan_filter))
    if search:
        qs = qs.filter(
            Q(payment_id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(transaction_reference__icontains=search) |
            Q(plan_code__icontains=search) |
            Q(subscription__tenant_id__icontains=search) |
            Q(subscription__organization_name__icontains=search)
        )

    # Sorting
    if sort_filter == 'oldest':
        qs = qs.order_by('created_at')
    elif sort_filter == 'amount_high':
        qs = qs.order_by('-amount_paise', '-created_at')
    elif sort_filter == 'amount_low':
        qs = qs.order_by('amount_paise', '-created_at')
    else:  # newest
        qs = qs.order_by('-created_at')

    # Aggregates across the entire database for KPI cards
    totals = Payment.objects.aggregate(
        total_vol=Sum('amount_paise'),
        total_cnt=Count('payment_id'),
        success_sum=Sum('amount_paise', filter=Q(payment_status='SUCCESS')),
        success_cnt=Count('payment_id', filter=Q(payment_status='SUCCESS')),
        pending_sum=Sum('amount_paise', filter=Q(payment_status='PENDING')),
        pending_cnt=Count('payment_id', filter=Q(payment_status='PENDING')),
        failed_cnt=Count('payment_id', filter=Q(payment_status='FAILED')),
        refund_sum=Sum('amount_paise', filter=Q(payment_status='REFUNDED')),
        refund_cnt=Count('payment_id', filter=Q(payment_status='REFUNDED')),
    )

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(page_num)

    all_plans = Plan.objects.all().order_by('display_order', 'monthly_price_paise')

    return render(request, 'admin/subscriptions/payments.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'type_filter': type_filter,
        'method_filter': method_filter,
        'plan_filter': plan_filter,
        'sort_filter': sort_filter,
        'selected_status': status_filter,
        'selected_type': type_filter,
        'selected_method': method_filter,
        'selected_plan': plan_filter,
        'search_query': search,
        'total_count': paginator.count,
        'all_plans': all_plans,
        'totals': {
            'total_vol_display': format_inr(totals['total_vol'] or 0),
            'total_cnt': totals['total_cnt'] or 0,
            'success_sum_display': format_inr(totals['success_sum'] or 0),
            'success_cnt': totals['success_cnt'] or 0,
            'pending_sum_display': format_inr(totals['pending_sum'] or 0),
            'pending_cnt': totals['pending_cnt'] or 0,
            'failed_cnt': totals['failed_cnt'] or 0,
            'refund_sum_display': format_inr(totals['refund_sum'] or 0),
            'refund_cnt': totals['refund_cnt'] or 0,
        }
    })


@login_required
def payment_detail_view(request, payment_id):
    """
    Dedicated, strictly read-only audit dossier for an individual payment.
    Displays complete financial, timing, customer, and subscription plan specifications.
    """
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    payment = get_object_or_404(
        Payment.objects.select_related('user', 'subscription', 'subscription__plan_record'),
        payment_id=payment_id
    )

    # Linked objects
    user = payment.user
    subscription = payment.subscription
    plan = payment.plan_record
    invoices = payment.invoices.all().order_by('-invoice_id')
    wallet_txn = payment.wallet_transaction

    # Format raw metadata
    metadata_json = "{}"
    if payment.metadata:
        try:
            metadata_json = json.dumps(payment.metadata, indent=2, default=str)
        except Exception:
            metadata_json = str(payment.metadata)

    # Support JSON response for quick-view modal AJAX requests
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json':
        return JsonResponse({
            'payment_id': payment.payment_id,
            'amount_inr': payment.amount_inr,
            'amount_paise': payment.amount_paise,
            'currency': payment.currency,
            'payment_status': payment.payment_status,
            'payment_type': payment.payment_type,
            'payment_method': payment.payment_method,
            'transaction_reference': payment.transaction_reference or '—',
            'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if payment.created_at else '—',
            'completed_at': payment.completed_at.strftime('%Y-%m-%d %H:%M:%S UTC') if payment.completed_at else '—',
            'duration': payment.processing_duration_display,
            'user': {
                'username': user.username if user else 'Anonymous',
                'email': user.email if user else '—',
                'organization': getattr(user, 'organization_name', None) or (subscription.organization_name if subscription else None) or '—',
            },
            'plan': {
                'name': payment.plan_name_display,
                'code': payment.plan_code or (plan.code if plan else 'N/A'),
                'tier': plan.code if plan else (payment.plan_code or 'N/A'),
                'monthly_price_inr': plan.price_monthly if plan else None,
                'yearly_price_inr': plan.price_yearly if plan else None,
                'billing_cycle': payment.billing_cycle_display,
            },
            'subscription': {
                'subscription_id': subscription.subscription_id if subscription else None,
                'tenant_id': subscription.tenant_id if subscription else None,
                'status': subscription.status if subscription else None,
                'current_period_start': subscription.current_period_start if subscription else None,
                'current_period_end': subscription.current_period_end if subscription else None,
                'seats': subscription.seats if subscription else 1,
            } if subscription else None,
            'metadata': payment.metadata or {},
        })

    return render(request, 'admin/subscriptions/payment_detail.html', {
        'payment': payment,
        'user': user,
        'subscription': subscription,
        'plan': plan,
        'invoices': invoices,
        'wallet_txn': wallet_txn,
        'metadata_json': metadata_json,
    })


@login_required
def admin_payment_refund_view(request, payment_id):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    reason = request.POST.get('reason', 'Administrative refund')
    try:
        res = refund_payment(payment_id=payment_id, actor=request.user.username, reason=reason)
        messages.success(request, res['message'])
    except Exception as e:
        messages.error(request, f"Refund failed: {str(e)}")

    return redirect('admin_subscriptions:payments_list')


# ── WALLET MANAGEMENT ────────────────────────────────────────────────────────
@login_required
def wallet_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    search = request.GET.get('q', '').strip()
    page_num = request.GET.get('page', 1)

    qs = Wallet.objects.select_related('user').all().order_by('-balance_paise')
    if search:
        qs = qs.filter(
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(user__organization_name__icontains=search)
        )

    total_balance_paise = Wallet.objects.aggregate(s=Sum('balance_paise'))['s'] or 0
    total_wallets = Wallet.objects.count()

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(page_num)

    recent_txns = WalletTransaction.objects.select_related('user').all().order_by('-created_at')[:25]

    return render(request, 'admin/subscriptions/wallets.html', {
        'page_obj': page_obj,
        'search_query': search,
        'total_count': paginator.count,
        'total_balance_display': format_inr(total_balance_paise),
        'total_wallets': total_wallets,
        'recent_transactions': recent_txns,
    })


@login_required
def admin_wallet_adjust_view(request, user_id):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    target_user = get_object_or_404(User, id=user_id)
    wallet = get_object_or_404(Wallet, user=target_user)

    if request.method == 'POST':
        action_type = request.POST.get('action_type')  # CREDIT or DEBIT
        amount_inr = float(request.POST.get('amount_inr') or 0)
        amount_paise = rupees_to_paise(amount_inr)
        reason = request.POST.get('reason', 'Administrative wallet adjustment')

        if amount_paise <= 0:
            messages.error(request, "Adjustment amount must be positive.")
            return redirect('admin_subscriptions:wallets')

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(id=wallet.id)
            bal_before = wallet.balance_paise

            if action_type == 'DEBIT':
                if wallet.balance_paise < amount_paise:
                    messages.error(request, f"Cannot debit {format_inr(amount_paise)}: User only has {format_inr(wallet.balance_paise)}.")
                    return redirect('admin_subscriptions:wallets')
                bal_after = bal_before - amount_paise
                txn_type = 'ADMIN_DEBIT'
                direction = 'DEBIT'
            else:
                bal_after = bal_before + amount_paise
                txn_type = 'ADMIN_CREDIT'
                direction = 'CREDIT'

            wallet.balance_paise = bal_after
            wallet.save(update_fields=['balance_paise', 'updated_at'])

            txn_id = f"WTXN_{uuid.uuid4().hex[:12].upper()}"
            WalletTransaction.objects.create(
                transaction_id=txn_id,
                wallet=wallet,
                user=target_user,
                transaction_type=txn_type,
                credit_or_debit=direction,
                amount_paise=amount_paise,
                balance_before_paise=bal_before,
                balance_after_paise=bal_after,
                reference_type='ADMIN_MANUAL',
                reference_id=request.user.username,
                description=f"{direction} adjustment by admin {request.user.username}: {reason}",
                status='SUCCESS',
            )

            SubscriptionEvent.objects.create(
                subscription_id=None,
                tenant_id=f"user_{target_user.id}",
                event_type=f"WALLET_{direction}",
                amount_paise=amount_paise,
                notes=f"{direction} of {format_inr(amount_paise)} by admin {request.user.username}. Reason: {reason}",
                actor=request.user.username,
                created_at=_now(),
            )

        messages.success(request, f"Successfully {direction.lower()}ed {format_inr(amount_paise)} to {target_user.username}'s wallet. New balance: {format_inr(bal_after)}.")

    return redirect('admin_subscriptions:wallets')


# ── INVOICE MANAGEMENT ────────────────────────────────────────────────────────
@login_required
def invoice_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    page_num = request.GET.get('page', 1)
    search = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip().upper()

    qs = Invoice.objects.select_related('user', 'payment').all().order_by('-issued_at', '-invoice_id')
    if status_filter and status_filter != 'ALL':
        qs = qs.filter(status=status_filter)
    if search:
        qs = qs.filter(
            Q(invoice_no__icontains=search) |
            Q(tenant_id__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__email__icontains=search) |
            Q(subscription_id__icontains=search)
        )

    # Tax totals
    tax_totals = Invoice.objects.filter(status='PAID').aggregate(
        taxable_sum=Sum('taxable_paise'),
        cgst_sum=Sum('cgst_paise'),
        sgst_sum=Sum('sgst_paise'),
        igst_sum=Sum('igst_paise'),
        total_sum=Sum('total_paise'),
    )

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/subscriptions/invoices.html', {
        'page_obj': page_obj,
        'search_query': search,
        'status_filter': status_filter,
        'total_count': paginator.count,
        'tax_totals': {
            'taxable_display': format_inr(tax_totals['taxable_sum'] or 0),
            'cgst_display': format_inr(tax_totals['cgst_sum'] or 0),
            'sgst_display': format_inr(tax_totals['sgst_sum'] or 0),
            'igst_display': format_inr(tax_totals['igst_sum'] or 0),
            'total_display': format_inr(tax_totals['total_sum'] or 0),
        }
    })


@login_required
def invoice_detail_view(request, invoice_id):
    inv = get_object_or_404(Invoice.objects.select_related('user', 'payment'), invoice_id=invoice_id)
    # Check permissions: admin can view any invoice, regular user can only view own invoice
    if not _is_admin(request.user) and inv.user != request.user:
        messages.error(request, "Permission denied.")
        return redirect('website:user_profile')

    lines = json.loads(inv.line_items) if inv.line_items else []

    return render(request, 'admin/subscriptions/invoice_printable.html', {
        'inv': inv,
        'lines': lines,
        'is_admin': _is_admin(request.user),
    })


# ── PROMO CODE MANAGEMENT ────────────────────────────────────────────────────
@login_required
def promo_code_list_view(request):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        code = request.POST.get('code', '').strip().upper()

        if action == 'toggle':
            p = get_object_or_404(PromoCode, code=code)
            p.active = not p.active
            p.save(update_fields=['active'])
            messages.success(request, f"Promo code '{code}' is now {'Active' if p.active else 'Inactive'}.")
            return redirect('admin_subscriptions:promos')

        pct = int(request.POST.get('percent_off', 10))
        max_r = request.POST.get('max_redemptions')
        desc = request.POST.get('description', '').strip()
        app_plans = request.POST.getlist('applicable_plans')

        if code:
            PromoCode.objects.update_or_create(
                code=code,
                defaults={
                    'percent_off': pct,
                    'max_redemptions': int(max_r) if max_r else None,
                    'description': desc,
                    'applicable_plans': json.dumps(app_plans) if app_plans else None,
                    'active': True
                }
            )
            messages.success(request, f"Promo code '{code}' saved.")
            return redirect('admin_subscriptions:promos')

    promos = PromoCode.objects.all().order_by('code')
    plans = Plan.objects.all().order_by('display_order')
    return render(request, 'admin/subscriptions/promos.html', {
        'promos': promos,
        'plans': plans
    })


# ── RENEWALS TRIGGER ─────────────────────────────────────────────────────────
@login_required
def admin_trigger_renewals_view(request):
    if not _is_admin(request.user):
        messages.error(request, "Access restricted to administrators.")
        return redirect('admin_portal:dashboard')

    res = process_subscription_renewals(force_run=True)
    messages.success(
        request,
        f"Automated renewals executed: Processed={res['processed']}, Renewed={res['renewed']}, "
        f"Failed={res['failed']}, Expired={res['expired']}."
    )
    return redirect('admin_subscriptions:list')
