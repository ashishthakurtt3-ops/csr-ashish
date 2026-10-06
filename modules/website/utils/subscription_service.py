"""
Subscription / billing service — Database-Driven Django-ORM Edition.

All pricing, plans, features, limits, wallets, payments, and billing lifecycles
are backed directly by MySQL through the Django ORM.
Hardcoded pricing constants have been removed as the source of truth.
"""
from __future__ import annotations

import calendar
import hashlib
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.db import transaction
from django.utils import timezone as dtz

from modules.admin_panel.models import (
    Plan, PlanEntitlement, Wallet, WalletTransaction, Payment,
    PromoCode, Subscription, SubscriptionEvent, Invoice, UsageCounter, User
)

# ── Money / currency constants ──────────────────────────────────────────────
CURRENCY = 'INR'
GST_RATE_BPS = 1800          # 18.00 %  (1 % = 100 bps)
SUPPLIER_STATE_CODE = str(os.environ.get('SUPPLIER_STATE_CODE', '27')).strip().upper()
DEFAULT_TENANT_ID = 'tenant_default'
TRIAL_DAYS = int(os.environ.get('SUBSCRIPTION_TRIAL_DAYS', '14'))

PAYMENT_METHODS = ('WALLET', 'UPI', 'Card', 'NetBanking', 'Corporate PO', 'NEFT')
BILLING_CYCLES = ('monthly', 'yearly')

_STATUS_ACTIVE = 'ACTIVE'
_STATUS_TRIALING = 'TRIALING'
_STATUS_CANCELED = 'CANCELED'
_STATUS_EXPIRED = 'EXPIRED'

_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$')
_GSTIN_RE = re.compile(r'^\d{2}[A-Z]{5}\d{4}[A-Z]\d[A-Z]\d$')

STATE_CODES: Dict[str, str] = {
    '01': 'Jammu & Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab',
    '04': 'Chandigarh', '05': 'Uttarakhand', '06': 'Haryana', '07': 'Delhi',
    '08': 'Rajasthan', '09': 'Uttar Pradesh', '10': 'Bihar', '11': 'Sikkim',
    '12': 'Arunachal Pradesh', '13': 'Nagaland', '14': 'Manipur',
    '15': 'Mizoram', '16': 'Tripura', '17': 'Meghalaya', '18': 'Assam',
    '19': 'West Bengal', '20': 'Jharkhand', '21': 'Odisha',
    '22': 'Chhattisgarh', '23': 'Madhya Pradesh', '24': 'Gujarat',
    '27': 'Maharashtra', '29': 'Karnataka', '30': 'Goa', '32': 'Kerala',
    '33': 'Tamil Nadu', '34': 'Puducherry', '36': 'Telangana',
    '37': 'Andhra Pradesh',
}

PLAN_ALIASES: Dict[str, str] = {
    'free': 'starter',
    'community_free': 'starter',
    'ultra': 'enterprise',
    'api': 'foundation',
    'institutional': 'foundation',
}


class SubscriptionError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = 'invalid_request'):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


# ── Money helpers ────────────────────────────────────────────────────────────
def rupees_to_paise(value: Any) -> int:
    if value is None or value == '':
        return 0
    dec = Decimal(str(value)) * Decimal(100)
    return int(dec.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def paise_to_rupees(paise: Any) -> float:
    return round(int(paise or 0) / 100.0, 2)


def format_inr(paise: Any) -> str:
    sign = '-' if int(paise or 0) < 0 else ''
    whole, frac = divmod(abs(int(paise or 0)), 100)
    s = str(whole)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts: List[str] = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ','.join(parts + [tail])
    return f'{sign}₹{s}.{frac:02d}'


def pct_of(amount_paise: int, percent: Any) -> int:
    dec = (Decimal(int(amount_paise)) * Decimal(str(percent))) / Decimal(100)
    return int(dec.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).replace('Z', '+00:00')
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _add_months(dt: datetime, months: int) -> datetime:
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def period_end(start: datetime, cycle: str) -> datetime:
    return _add_months(start, 12 if cycle == 'yearly' else 1)


# ── Database-Driven Plan Resolution ──────────────────────────────────────────
def _plan_model_to_dict(plan: Plan) -> Dict[str, Any]:
    monthly_paise = int(plan.monthly_price_paise or 0)
    yearly_paise = int(plan.yearly_price_paise or 0)
    full_year_paise = monthly_paise * 12
    savings_paise = max(0, full_year_paise - yearly_paise)
    savings_pct = round((savings_paise / full_year_paise) * 100, 1) if full_year_paise else 0.0

    limits_dict = plan.get_limits_and_entitlements()
    features_list = list(plan.features or [])
    highlight_list = list(plan.highlight_features or [])

    renewal_paise = getattr(plan, 'renewal_price_paise', None)
    if renewal_paise is None:
        renewal_paise = monthly_paise
    wallet_deduct_paise = getattr(plan, 'wallet_deduction_paise', None)
    if wallet_deduct_paise is None:
        wallet_deduct_paise = monthly_paise

    return {
        'id': plan.code,
        'code': plan.code,
        'name': plan.name,
        'slug': plan.slug,
        'badge': plan.badge or ('Free Forever' if monthly_paise == 0 else ''),
        'description': plan.description or '',
        'cta_text': getattr(plan, 'button_text', None) or plan.cta_text or ('Start Free' if monthly_paise == 0 else f'Switch to {plan.name}'),
        'button_text': getattr(plan, 'button_text', None) or ('Start Free' if monthly_paise == 0 else 'Change Plan'),
        'button_visible': bool(getattr(plan, 'button_visible', True)),
        'button_order': int(getattr(plan, 'button_order', 1) or 1),
        'billing_note': plan.billing_note or ('No credit card required' if monthly_paise == 0 else 'Billed monthly or annually (+18% GST)'),
        'is_recommended': bool(getattr(plan, 'is_recommended', False)),
        'discount_percent': int(getattr(plan, 'discount_percent', 0) or 0),
        'savings_text': getattr(plan, 'savings_text', None) or (f'Save {format_inr(savings_paise)}' if savings_paise else ''),
        'renewal_price_paise': renewal_paise,
        'renewal_price': paise_to_rupees(renewal_paise),
        'renewal_price_display': format_inr(renewal_paise),
        'wallet_deduction_paise': wallet_deduct_paise,
        'wallet_deduction': paise_to_rupees(wallet_deduct_paise),
        'wallet_deduction_display': format_inr(wallet_deduct_paise),
        'card_description': getattr(plan, 'card_description', None) or plan.description or '',
        'additional_info': getattr(plan, 'additional_info', None) or '',
        'terms': getattr(plan, 'terms', None) or '',
        'notes': getattr(plan, 'notes', None) or '',
        'price_monthly_paise': monthly_paise,
        'price_yearly_paise': yearly_paise,
        'monthly_price_paise': monthly_paise,
        'yearly_price_paise': yearly_paise,
        'price_monthly': paise_to_rupees(monthly_paise),
        'price_yearly': paise_to_rupees(yearly_paise),
        'monthly_price': paise_to_rupees(monthly_paise),
        'yearly_price': paise_to_rupees(yearly_paise),
        'price_monthly_display': format_inr(monthly_paise),
        'price_yearly_display': format_inr(yearly_paise),
        'currency': '₹',
        'is_active': bool(plan.is_active),
        'savings_yearly_paise': savings_paise,
        'savings_yearly_display': format_inr(savings_paise),
        'savings_percent': savings_pct,
        'savings_label': f'Save {format_inr(savings_paise)} / year ({savings_pct}% off)' if savings_paise else None,
        'is_free': monthly_paise == 0,
        'is_popular': bool(plan.is_popular),
        'is_contact_sales': bool(plan.is_contact_sales),
        'display_order': plan.display_order,
        'trial_days': plan.trial_days,
        'allow_upgrade': bool(plan.allow_upgrade),
        'allow_plan_change': bool(plan.allow_downgrade),
        'allow_cancel': bool(plan.allow_cancel),
        'auto_renew_default': bool(plan.auto_renew_default),
        'features': features_list,
        'highlight_features': highlight_list,
        'limits': limits_dict,
    }


def get_plan(plan_id: Any) -> Optional[Dict[str, Any]]:
    key = str(plan_id or '').strip().lower()
    canonical_key = PLAN_ALIASES.get(key, key)
    try:
        plan_obj = Plan.objects.filter(code=canonical_key).first()
        if not plan_obj:
            plan_obj = Plan.objects.filter(code=key).first()
        if plan_obj:
            return _plan_model_to_dict(plan_obj)
    except Exception:
        pass
    return None


def require_plan(plan_id: Any) -> Dict[str, Any]:
    plan = get_plan(plan_id)
    if not plan:
        valid_plans = [p.code for p in Plan.objects.filter(is_active=True).order_by('display_order')]
        raise SubscriptionError(
            f"Unknown plan '{plan_id}'. Valid plans: {', '.join(valid_plans)}.",
            404, 'unknown_plan'
        )
    if not plan.get('is_active', True):
        raise SubscriptionError(f"Plan '{plan_id}' is inactive and cannot be purchased.", 400, 'plan_inactive')
    return plan


def get_all_active_plans() -> List[Dict[str, Any]]:
    try:
        qs = Plan.objects.filter(is_active=True).order_by('display_order', 'monthly_price_paise')
        if qs.exists():
            return [_plan_model_to_dict(p) for p in qs]
    except Exception:
        pass
    starter = get_plan('starter')
    return [starter] if starter else []


def base_price_paise(plan: Dict[str, Any], cycle: str) -> int:
    return int(plan['price_yearly_paise'] if cycle == 'yearly' else plan['price_monthly_paise'])


# ── Normalisation helpers ────────────────────────────────────────────────────
def normalise_tenant(value: Any) -> str:
    tenant = str(value or DEFAULT_TENANT_ID).strip()
    tenant = re.sub(r'[^A-Za-z0-9_\-]', '', tenant)[:64]
    return tenant or DEFAULT_TENANT_ID


def normalise_email(value: Any) -> str:
    email = str(value or '').strip().lower()
    if not _EMAIL_RE.match(email):
        raise SubscriptionError('A valid contact email address is required.', 422, 'invalid_email')
    return email


def normalise_org(value: Any) -> str:
    org = ' '.join(str(value or '').split())
    if len(org) < 2:
        raise SubscriptionError('Organization / non-profit name is required.', 422, 'invalid_organization')
    if len(org) > 200:
        raise SubscriptionError('Organization name must be 200 characters or fewer.', 422, 'invalid_organization')
    return org


def normalise_cycle(value: Any) -> str:
    cycle = str(value or 'monthly').strip().lower()
    if cycle not in BILLING_CYCLES:
        raise SubscriptionError(
            f"billing_cycle must be one of: {', '.join(BILLING_CYCLES)}.", 422, 'invalid_billing_cycle')
    return cycle


def normalise_payment_method(value: Any) -> str:
    method = ' '.join(str(value or 'WALLET').split())
    if method not in PAYMENT_METHODS:
        raise SubscriptionError(
            f"payment_method must be one of: {', '.join(PAYMENT_METHODS)}.", 422, 'invalid_payment_method')
    return method


def normalise_gstin(value: Any) -> Optional[str]:
    gstin = str(value or '').strip().upper()
    if not gstin:
        return None
    if not _GSTIN_RE.match(gstin):
        raise SubscriptionError('GSTIN must be a valid 15-character Indian GST number.', 422, 'invalid_gstin')
    return gstin


def normalise_state(value: Any) -> str:
    code = str(value or '').strip().upper()
    if not code:
        return SUPPLIER_STATE_CODE
    if code in STATE_CODES or (len(code) == 2 and code.isdigit()):
        return code
    raise SubscriptionError(
        'place_of_supply must be a 2-digit GST state code (e.g. 29 for Karnataka).',
        422, 'invalid_place_of_supply')


def normalise_promo_code(value: Any) -> Optional[str]:
    code = str(value or '').strip().upper().replace(' ', '')
    if not code:
        return None
    if not re.match(r'^[A-Z0-9\-_]{3,40}$', code):
        raise SubscriptionError(
            'Promo code may only contain letters, digits, hyphens and underscores.',
            422, 'invalid_promo_code')
    return code


# ── GST engine ────────────────────────────────────────────────────────────────
def compute_tax(taxable_paise: int, place_of_supply: Optional[str]) -> Dict[str, Any]:
    supply = (place_of_supply or SUPPLIER_STATE_CODE).strip().upper()
    inter_state = supply != SUPPLIER_STATE_CODE
    total_gst = pct_of(taxable_paise, GST_RATE_BPS / 100)
    if inter_state:
        cgst = sgst = 0
        igst = total_gst
    else:
        igst = 0
        cgst = total_gst // 2
        sgst = total_gst - cgst
    return {
        'place_of_supply': supply,
        'place_of_supply_name': STATE_CODES.get(supply, 'Other Territory'),
        'supplier_state_code': SUPPLIER_STATE_CODE,
        'supplier_state_name': STATE_CODES.get(SUPPLIER_STATE_CODE, 'Other Territory'),
        'supply_type': 'INTER_STATE' if inter_state else 'INTRA_STATE',
        'gst_rate_percent': round(GST_RATE_BPS / 100, 2),
        'igst_paise': igst, 'cgst_paise': cgst, 'sgst_paise': sgst,
        'total_tax_paise': total_gst,
        'igst_display': format_inr(igst), 'cgst_display': format_inr(cgst),
        'sgst_display': format_inr(sgst), 'total_tax_display': format_inr(total_gst),
    }


# ── Promo engine (uses Django ORM) ───────────────────────────────────────────
def _promo_model_to_dict(p: PromoCode) -> Dict[str, Any]:
    try:
        plans = json.loads(p.applicable_plans) if p.applicable_plans else None
    except Exception:
        plans = None
    return {
        'code': p.code, 'percent_off': int(p.percent_off or 0),
        'max_redemptions': p.max_redemptions,
        'times_redeemed': int(p.times_redeemed or 0),
        'valid_from': p.valid_from, 'valid_until': p.valid_until,
        'applicable_plans': plans,
        'description': p.description, 'active': bool(p.active),
    }


def evaluate_promo(code: Optional[str], plan_id: str, base_paise: int) -> Dict[str, Any]:
    if not code:
        return {'valid': False, 'code': None, 'percent_off': 0, 'message': None, 'applied': False}
    try:
        p = PromoCode.objects.get(code=code)
    except PromoCode.DoesNotExist:
        return {'valid': False, 'code': code, 'percent_off': 0,
                'message': f'Promo code {code} is not recognised.', 'applied': False}

    promo = _promo_model_to_dict(p)
    now_dt = datetime.now(timezone.utc)

    if not promo['active']:
        return {'valid': False, 'code': code, 'percent_off': 0,
                'message': f'Promo code {code} is no longer active.', 'applied': False}

    start = _parse_iso(promo['valid_from'])
    if start and now_dt < start:
        return {'valid': False, 'code': code, 'percent_off': 0,
                'message': f'Promo code {code} is not yet active.', 'applied': False}

    end = _parse_iso(promo['valid_until'])
    if end and now_dt > end:
        return {'valid': False, 'code': code, 'percent_off': 0,
                'message': f'Promo code {code} expired on {end.date().isoformat()}.', 'applied': False}

    cap = promo['max_redemptions']
    if cap is not None and promo['times_redeemed'] >= int(cap):
        return {'valid': False, 'code': code, 'percent_off': 0,
                'message': f'Promo code {code} has reached its redemption limit.', 'applied': False}

    allowed = promo['applicable_plans']
    if allowed:
        canonical_plan = PLAN_ALIASES.get(plan_id, plan_id)
        if plan_id not in allowed and canonical_plan not in allowed:
            return {'valid': False, 'code': code, 'percent_off': 0,
                    'message': f"Promo code {code} is only valid on: {', '.join(allowed)}.", 'applied': False}

    discount = pct_of(base_paise, promo['percent_off'])
    return {
        'valid': True, 'applied': True, 'code': code,
        'percent_off': promo['percent_off'],
        'discount_paise': discount, 'discount_display': format_inr(discount),
        'description': promo['description'],
        'message': f"{promo['percent_off']}% discount applied ({code}) — you save {format_inr(discount)}.",
    }


# ── User and Tenant Resolution ───────────────────────────────────────────────
def resolve_user_and_tenant(user=None, tenant_id: Optional[str] = None) -> Tuple[Optional[User], str]:
    if user and getattr(user, 'is_authenticated', False):
        existing_sub = Subscription.objects.filter(user=user).first()
        if existing_sub:
            return user, existing_sub.tenant_id
        # Fallback to check if a subscription exists for username or default if admin
        if user.is_superuser or user.role == 'ADMIN':
            default_sub = Subscription.objects.filter(tenant_id=DEFAULT_TENANT_ID).first()
            if default_sub:
                if not default_sub.user:
                    default_sub.user = user
                    default_sub.save(update_fields=['user'])
                return user, DEFAULT_TENANT_ID
        return user, f"user_{user.id}"
    tenant = normalise_tenant(tenant_id)
    return None, tenant


# ── Wallet Service (Prototype Atomic Operations) ─────────────────────────────
def get_or_create_wallet(user: User) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(user=user, defaults={'balance_paise': 0})
    return wallet


def get_wallet_data(user: User) -> Dict[str, Any]:
    wallet = get_or_create_wallet(user)
    recent_txns = list(
        WalletTransaction.objects.filter(user=user).order_by('-created_at')[:20].values(
            'transaction_id', 'transaction_type', 'credit_or_debit',
            'amount_paise', 'balance_before_paise', 'balance_after_paise',
            'reference_type', 'reference_id', 'description', 'status', 'created_at'
        )
    )
    for t in recent_txns:
        t['amount_display'] = format_inr(t['amount_paise'])
        t['balance_after_display'] = format_inr(t['balance_after_paise'])
        t['amount_rupees'] = paise_to_rupees(t['amount_paise'])
        t['balance_after_rupees'] = paise_to_rupees(t['balance_after_paise'])

    return {
        'balance_paise': wallet.balance_paise,
        'balance_rupees': wallet.balance_rupees,
        'balance_inr': wallet.balance_rupees,
        'balance_display': format_inr(wallet.balance_paise),
        'currency': wallet.currency,
        'is_active': wallet.is_active,
        'recent_transactions': recent_txns,
    }


def topup_wallet(user: User, amount_paise: int, payment_method: str = 'WALLET_TOPUP',
                 description: Optional[str] = None, request_id: Optional[str] = None) -> Dict[str, Any]:
    if amount_paise <= 0:
        raise SubscriptionError('Top-up amount must be greater than zero.', 400, 'invalid_amount')

    # Idempotency check
    if request_id:
        existing_payment = Payment.objects.filter(idempotency_key=request_id, payment_status='SUCCESS').first()
        if existing_payment:
            wallet = get_or_create_wallet(user)
            return {
                'status': 'success',
                'idempotent_replay': True,
                'payment_id': existing_payment.payment_id,
                'amount_paise': existing_payment.amount_paise,
                'amount_display': format_inr(existing_payment.amount_paise),
                'balance_paise': wallet.balance_paise,
                'balance_display': format_inr(wallet.balance_paise),
                'message': f"Top-up of {format_inr(existing_payment.amount_paise)} already applied.",
            }

    with transaction.atomic():
        # Row-lock wallet
        wallet = Wallet.objects.select_for_update().get_or_create(user=user, defaults={'balance_paise': 0})[0]
        bal_before = wallet.balance_paise
        bal_after = bal_before + amount_paise
        wallet.balance_paise = bal_after
        wallet.save(update_fields=['balance_paise', 'updated_at'])

        pay_id = f"PAY_TOPUP_{uuid.uuid4().hex[:12].upper()}"
        payment = Payment.objects.create(
            payment_id=pay_id,
            user=user,
            amount_paise=amount_paise,
            currency=CURRENCY,
            payment_method=payment_method,
            payment_status='SUCCESS',
            payment_type='TOPUP',
            transaction_reference=f"TXN_TOPUP_{uuid.uuid4().hex[:8].upper()}",
            idempotency_key=request_id,
            is_prototype=True,
            metadata={'balance_before': bal_before, 'balance_after': bal_after},
            completed_at=dtz.now(),
        )

        txn_id = f"WTXN_{uuid.uuid4().hex[:12].upper()}"
        WalletTransaction.objects.create(
            transaction_id=txn_id,
            wallet=wallet,
            user=user,
            transaction_type='WALLET_TOPUP',
            credit_or_debit='CREDIT',
            amount_paise=amount_paise,
            balance_before_paise=bal_before,
            balance_after_paise=bal_after,
            reference_type='PAYMENT',
            reference_id=pay_id,
            description=description or f"Prototype Wallet Top-Up of {format_inr(amount_paise)}",
            status='SUCCESS',
        )

        SubscriptionEvent.objects.create(
            subscription_id=None,
            tenant_id=f"user_{user.id}",
            event_type='WALLET_TOPUP',
            amount_paise=amount_paise,
            notes=f"Added {format_inr(amount_paise)} prototype funds. New balance: {format_inr(bal_after)}",
            actor=user.username,
            created_at=_now(),
        )

    return {
        'status': 'success',
        'success': True,
        'payment_id': pay_id,
        'transaction_id': txn_id,
        'amount_paise': amount_paise,
        'amount_display': format_inr(amount_paise),
        'balance_before_display': format_inr(bal_before),
        'balance_display': format_inr(bal_after),
        'balance_rupees': paise_to_rupees(bal_after),
        'balance_inr': paise_to_rupees(bal_after),
        'message': f"Successfully credited {format_inr(amount_paise)} to your prototype wallet!",
    }


def refund_payment(payment_id: str, actor: str = 'Admin', reason: Optional[str] = None) -> Dict[str, Any]:
    with transaction.atomic():
        try:
            payment = Payment.objects.select_for_update().get(payment_id=payment_id)
        except Payment.DoesNotExist:
            raise SubscriptionError(f"Payment '{payment_id}' not found.", 404, 'payment_not_found')

        if payment.payment_status == 'REFUNDED':
            raise SubscriptionError('This payment has already been refunded.', 400, 'already_refunded')
        if payment.payment_status != 'SUCCESS':
            raise SubscriptionError(f"Cannot refund payment with status '{payment.payment_status}'.", 400, 'invalid_status')

        user = payment.user
        amount = payment.amount_paise
        if not user or amount <= 0:
            payment.payment_status = 'REFUNDED'
            payment.failure_reason = reason or 'Refunded without wallet credit'
            payment.save(update_fields=['payment_status', 'failure_reason'])
            return {'status': 'success', 'message': f'Payment {payment_id} marked as refunded.'}

        wallet = Wallet.objects.select_for_update().get_or_create(user=user, defaults={'balance_paise': 0})[0]
        bal_before = wallet.balance_paise
        bal_after = bal_before + amount
        wallet.balance_paise = bal_after
        wallet.save(update_fields=['balance_paise', 'updated_at'])

        payment.payment_status = 'REFUNDED'
        payment.failure_reason = reason or 'Refunded to prototype wallet'
        payment.save(update_fields=['payment_status', 'failure_reason'])

        txn_id = f"WTXN_{uuid.uuid4().hex[:12].upper()}"
        WalletTransaction.objects.create(
            transaction_id=txn_id,
            wallet=wallet,
            user=user,
            transaction_type='REFUND',
            credit_or_debit='CREDIT',
            amount_paise=amount,
            balance_before_paise=bal_before,
            balance_after_paise=bal_after,
            reference_type='PAYMENT',
            reference_id=payment.payment_id,
            description=f"Refund for payment {payment.payment_id}: {reason or 'Administrative refund'}",
            status='SUCCESS',
        )

        # Update invoice status if linked
        Invoice.objects.filter(payment=payment).update(status='REFUNDED')

        SubscriptionEvent.objects.create(
            subscription_id=payment.subscription.subscription_id if payment.subscription else None,
            tenant_id=f"user_{user.id}",
            event_type='REFUND',
            amount_paise=amount,
            notes=f"Refunded {format_inr(amount)} to wallet. Reason: {reason or 'Admin action'}",
            actor=actor,
            created_at=_now(),
        )

    return {
        'status': 'success',
        'success': True,
        'payment_id': payment_id,
        'amount_paise': amount,
        'amount_display': format_inr(amount),
        'new_balance_display': format_inr(bal_after),
        'message': f"Payment {payment_id} refunded successfully. {format_inr(amount)} credited back to wallet.",
    }


# ── Subscription ORM helpers ─────────────────────────────────────────────────
def _sub_to_dict(s: Subscription) -> Dict[str, Any]:
    plan_dict = s.plan.get_limits_and_entitlements() if s.plan else {}
    return {
        'subscription_id': s.subscription_id,
        'tenant_id': s.tenant_id,
        'user_id': s.user_id,
        'plan_id': s.plan_id or s.plan_tier,
        'plan_code': s.plan_tier,
        'status': s.status,
        'billing_cycle': s.billing_cycle,
        'organization_name': s.organization_name,
        'contact_email': s.contact_email,
        'activated_at': s.activated_at,
        'current_period_start': s.current_period_start,
        'current_period_end': s.current_period_end,
        'cancel_at_period_end': int(s.cancel_at_period_end or 0),
        'canceled_at': s.canceled_at,
        'cancel_reason': s.cancel_reason,
        'auto_renew': bool(s.auto_renew),
        'pending_change_plan': s.pending_downgrade_plan,
        'pending_change_cycle': s.pending_downgrade_cycle,
        'pending_change_date': s.pending_downgrade_date,
        'promo_code': s.promo_code,
        'promo_percent': int(s.promo_percent or 0),
        'base_amount_paise': int(s.base_amount_paise or 0),
        'discount_paise': int(s.discount_paise or 0),
        'taxable_paise': int(s.taxable_paise or 0),
        'cgst_paise': int(s.cgst_paise or 0),
        'sgst_paise': int(s.sgst_paise or 0),
        'igst_paise': int(s.igst_paise or 0),
        'total_paise': int(s.total_paise or 0),
        'currency': s.currency or CURRENCY,
        'payment_method': s.payment_method,
        'transaction_id': s.transaction_id,
        'gstin': s.gstin,
        'place_of_supply': s.place_of_supply,
        'supply_type': s.supply_type,
        'seats': int(s.seats or 1),
        'daily_match_quota': s.daily_match_quota,
        'api_key_hash': s.api_key_hash,
        'api_key_prefix': s.api_key_prefix,
        'api_key_last4': s.api_key_last4,
        'request_id': s.request_id,
        'created_at': s.created_at,
        'updated_at': s.updated_at,
    }


def empty_subscription(tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None) -> Dict[str, Any]:
    starter = get_plan('starter') or {
        'id': 'starter', 'name': 'Community Starter', 'badge': 'Free Forever',
        'is_free': True, 'features': [], 'highlight_features': [],
        'limits': {'seats': 1, 'daily_matches': 5, 'api_access': False, 'live_reprobe': False, 'view_contacts': False, 'audit_packs': False}
    }
    ts = _now()
    org_name = user.organization_name if user and user.organization_name else 'Unregistered Organisation'
    email = user.email if user and user.email else None
    return {
        'subscription_id': f'SUB_FREE_{tenant_id}'.upper()[:48],
        'tenant_id': tenant_id,
        'user_id': user.id if user else None,
        'plan_id': 'starter',
        'plan_code': 'starter',
        'plan_name': starter['name'],
        'tier': 'starter',
        'status': _STATUS_ACTIVE,
        'billing_cycle': 'free',
        'organization_name': org_name,
        'contact_email': email,
        'activated_at': ts, 'current_period_start': ts, 'current_period_end': None,
        'cancel_at_period_end': 0, 'canceled_at': None, 'cancel_reason': None,
        'auto_renew': False,
        'pending_change_plan': None, 'pending_change_cycle': None, 'pending_change_date': None,
        'promo_code': None, 'promo_percent': 0,
        'base_amount_paise': 0, 'discount_paise': 0, 'taxable_paise': 0,
        'cgst_paise': 0, 'sgst_paise': 0, 'igst_paise': 0, 'total_paise': 0,
        'currency': CURRENCY, 'payment_method': None, 'transaction_id': None,
        'gstin': None, 'place_of_supply': SUPPLIER_STATE_CODE, 'supply_type': 'INTRA_STATE',
        'seats': starter['limits'].get('seats') or 1,
        'daily_match_quota': starter['limits'].get('daily_matches'),
        'api_key_hash': None, 'api_key_prefix': None, 'api_key_last4': None,
        'request_id': None, 'created_at': ts, 'updated_at': ts,
    }


def _refresh_status(row: Dict[str, Any]) -> Dict[str, Any]:
    """Auto-expire or apply scheduled downgrade if billing period lapsed."""
    pid = str(row.get('plan_id') or '').lower()
    if pid in ('starter', 'free') or not row.get('current_period_end'):
        return row
    end = _parse_iso(row.get('current_period_end'))
    if not end or datetime.now(timezone.utc) < end:
        return row

    # Period has lapsed
    tenant = row['tenant_id']
    pending_down = row.get('pending_downgrade_plan')
    auto_renew = bool(row.get('auto_renew'))

    if pending_down:
        # Apply scheduled downgrade
        down_plan = get_plan(pending_down) or get_plan('starter')
        Subscription.objects.filter(tenant_id=tenant).update(
            plan_id=down_plan['id'],
            plan_record=Plan.objects.filter(code=down_plan['id']).first(),
            pending_downgrade_plan=None,
            pending_downgrade_cycle=None,
            pending_downgrade_date=None,
            updated_at=_now(),
        )
        SubscriptionEvent.objects.create(
            subscription_id=row['subscription_id'],
            tenant_id=tenant,
            event_type='DOWNGRADE_APPLIED',
            from_plan=row.get('plan_id'), to_plan=down_plan['id'],
            amount_paise=0,
            notes=f"Scheduled plan change to {down_plan['name']} applied at period end.",
            actor='System', created_at=_now(),
        )
        updated = dict(row)
        updated['plan_id'] = down_plan['id']
        updated['pending_downgrade_plan'] = None
        return updated

    if not auto_renew and row.get('status') != _STATUS_EXPIRED:
        Subscription.objects.filter(tenant_id=tenant).update(
            status=_STATUS_EXPIRED, updated_at=_now()
        )
        SubscriptionEvent.objects.create(
            subscription_id=row['subscription_id'],
            tenant_id=tenant,
            event_type='SUBSCRIPTION_EXPIRED',
            from_plan=row.get('plan_id'), to_plan='starter',
            amount_paise=0,
            notes=f"Billing period ended on {row.get('current_period_end')}.",
            actor='System', created_at=_now(),
        )
        expired = dict(row)
        expired['status'] = _STATUS_EXPIRED
        return expired

    return row


def _load(tenant_id: str, user: Optional[User] = None) -> Dict[str, Any]:
    qs = Subscription.objects.all()
    if user and getattr(user, 'is_authenticated', False):
        s = qs.filter(user=user).first()
        if s:
            return _refresh_status(_sub_to_dict(s))
    s = qs.filter(tenant_id=tenant_id).first()
    if s:
        if user and not s.user:
            s.user = user
            s.save(update_fields=['user'])
        return _refresh_status(_sub_to_dict(s))
    return empty_subscription(tenant_id, user)


def _entitlement(row: Dict[str, Any]) -> Dict[str, Any]:
    if row.get('status') in (_STATUS_EXPIRED, _STATUS_CANCELED):
        return get_plan('starter')
    return get_plan(row.get('plan_id')) or get_plan('starter')


def effective_plan_id(row: Dict[str, Any]) -> str:
    return _entitlement(row)['id']


def serialize(row: Dict[str, Any]) -> Dict[str, Any]:
    plan = get_plan(row.get('plan_id')) or get_plan('starter')
    out = dict(row)
    out['plan_name'] = plan['name']
    out['tier'] = plan['id']
    out['plan_badge'] = plan['badge']
    out['is_free'] = plan['is_free']
    out['limits'] = plan['limits']
    out['features'] = plan['features']
    out['highlight_features'] = plan['highlight_features']
    out['currency_symbol'] = '₹'
    out['cancel_at_period_end'] = int(row.get('cancel_at_period_end') or 0)
    out['auto_renew'] = bool(row.get('auto_renew'))
    for field in ('base_amount', 'discount', 'taxable', 'cgst', 'sgst', 'igst', 'total'):
        out[f'{field}_display'] = format_inr(row.get(f'{field}_paise'))
    out['total_amount'] = paise_to_rupees(row.get('total_paise'))
    out['has_api_key'] = bool(row.get('api_key_hash'))
    end = _parse_iso(row.get('current_period_end'))
    now_dt = datetime.now(timezone.utc)
    out['days_remaining'] = max(0, (end - now_dt).days) if end else None
    out['is_active'] = row.get('status') in (_STATUS_ACTIVE, _STATUS_TRIALING)
    out['renews_on'] = row.get('current_period_end')
    return out


# ── Usage metering ───────────────────────────────────────────────────────────
def _get_usage(tenant_id: str, metric: str, period_date: Optional[str] = None) -> int:
    today = period_date or datetime.now(timezone.utc).date().isoformat()
    try:
        uc = UsageCounter.objects.filter(tenant_id=tenant_id, metric=metric, period_date=today).first()
        return uc.used if uc else 0
    except Exception:
        return 0


def _bump_usage(tenant_id: str, metric: str, amount: int = 1) -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        uc, _ = UsageCounter.objects.get_or_create(
            tenant_id=tenant_id, metric=metric, period_date=today,
            defaults={'used': 0}
        )
        uc.used += amount
        uc.save(update_fields=['used'])
        return uc.used
    except Exception:
        return 1


def quota_snapshot(row: Dict[str, Any]) -> Dict[str, Any]:
    plan = get_plan(row.get('plan_id')) or get_plan('starter')
    limit = plan['limits'].get('daily_matches')
    tenant = row.get('tenant_id') or DEFAULT_TENANT_ID
    used = _get_usage(tenant, 'ngo_matches')
    remaining = None if limit is None else max(0, int(limit) - used)
    today = datetime.now(timezone.utc).date()
    return {
        'metric': 'ngo_matches', 'period_date': today.isoformat(),
        'limit': limit, 'unlimited': limit is None, 'used': used,
        'remaining': remaining,
        'percent_used': round((used / limit) * 100, 1) if limit else 0.0,
        'reset_at': (today + timedelta(days=1)).isoformat(),
    }


# ── Pricing & Proration helpers ──────────────────────────────────────────────
def _zero_credit() -> Dict[str, Any]:
    return {'credit_paise': 0, 'credit_display': format_inr(0),
            'remaining_days': 0, 'total_days': 0, 'applies': False}


def _proration_credit(row: Dict[str, Any], now_dt: datetime) -> Dict[str, Any]:
    pid = str(row.get('plan_id') or '').lower()
    if not row or pid in ('starter', 'free'):
        return _zero_credit()
    if row.get('status') not in (_STATUS_ACTIVE, _STATUS_TRIALING):
        return _zero_credit()
    start = _parse_iso(row.get('current_period_start'))
    end = _parse_iso(row.get('current_period_end'))
    paid = int(row.get('taxable_paise') or 0)
    if not start or not end or end <= start or paid <= 0 or now_dt >= end:
        return _zero_credit()
    total_seconds = (end - start).total_seconds()
    remaining_seconds = (end - now_dt).total_seconds()
    fraction = max(0.0, min(1.0, remaining_seconds / total_seconds))
    credit = int(round(paid * fraction))
    return {
        'credit_paise': credit, 'credit_display': format_inr(credit),
        'remaining_days': max(0, (end - now_dt).days),
        'total_days': max(1, round(total_seconds / 86400)),
        'applies': credit > 0,
    }


def _breakdown(plan: Dict[str, Any], cycle: str, promo: Dict[str, Any],
               state_code: str, credit: Dict[str, Any]) -> Dict[str, Any]:
    base = base_price_paise(plan, cycle)
    discount = int(promo.get('discount_paise') or 0) if promo.get('applied') else 0
    credit_amount = int(credit.get('credit_paise') or 0) if credit.get('applies') else 0
    taxable = max(0, base - discount - credit_amount)
    tax = compute_tax(taxable, state_code)
    total = taxable + tax['total_tax_paise']

    lines: List[Dict[str, Any]] = [
        {'label': f"{plan['name']} — {cycle.title()} subscription",
         'amount_paise': base, 'amount_display': format_inr(base), 'kind': 'charge'},
    ]
    if discount:
        lines.append({'label': f"Promo {promo['code']} ({promo['percent_off']}% off)",
                      'amount_paise': -discount, 'amount_display': f'-{format_inr(discount)}',
                      'kind': 'discount'})
    if credit_amount:
        lines.append({'label': f"Unused-time credit ({credit['remaining_days']} of {credit['total_days']} days)",
                      'amount_paise': -credit_amount,
                      'amount_display': f'-{format_inr(credit_amount)}', 'kind': 'credit'})
    lines.append({'label': 'Taxable value', 'amount_paise': taxable,
                  'amount_display': format_inr(taxable), 'kind': 'subtotal'})
    if tax['igst_paise']:
        lines.append({'label': f"IGST @ {tax['gst_rate_percent']}%",
                      'amount_paise': tax['igst_paise'], 'amount_display': tax['igst_display'], 'kind': 'tax'})
    else:
        lines.append({'label': f"CGST @ {round(tax['gst_rate_percent'] / 2, 2)}%",
                      'amount_paise': tax['cgst_paise'], 'amount_display': tax['cgst_display'], 'kind': 'tax'})
        lines.append({'label': f"SGST @ {round(tax['gst_rate_percent'] / 2, 2)}%",
                      'amount_paise': tax['sgst_paise'], 'amount_display': tax['sgst_display'], 'kind': 'tax'})

    return {
        'plan_id': plan['id'], 'plan_name': plan['name'], 'billing_cycle': cycle,
        'base_amount_paise': base, 'base_amount_display': format_inr(base),
        'base_paise': base,
        'discount_paise': discount, 'discount_display': format_inr(discount),
        'credit_paise': credit_amount, 'credit_display': format_inr(credit_amount),
        'taxable_paise': taxable, 'taxable_display': format_inr(taxable),
        'tax': tax, 'total_paise': total, 'total_display': format_inr(total),
        'currency': CURRENCY, 'lines': lines,
    }


def _change_type(current_plan_id: str, target_plan_id: str) -> str:
    curr = PLAN_ALIASES.get(str(current_plan_id or '').lower(), str(current_plan_id or '').lower())
    target = PLAN_ALIASES.get(str(target_plan_id or '').lower(), str(target_plan_id or '').lower())
    if not curr or curr in ('starter', 'free'):
        return 'SUBSCRIPTION'
    if curr == target:
        return 'RENEWAL'
    order_map = {'starter': 1, 'free': 1, 'pro': 2, 'enterprise': 3, 'ultra': 3, 'foundation': 4, 'api': 4}
    return 'UPGRADE' if order_map.get(target, 0) > order_map.get(curr, 0) else 'DOWNGRADE'


def _new_api_key(plan_id: str) -> Tuple[str, str, str, str]:
    raw = f'ib_{plan_id}_{secrets.token_hex(20)}'
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return raw, digest, raw[:12], raw[-4:]


# ── Invoice helpers ──────────────────────────────────────────────────────────
def _invoice_number(issued_at: str, invoice_id: int) -> str:
    dt = _parse_iso(issued_at) or datetime.now(timezone.utc)
    fy_start = dt.year if dt.month >= 4 else dt.year - 1
    return f'IB/{fy_start}-{str(fy_start + 1)[-2:]}/{int(invoice_id):06d}'


def _create_invoice(tenant_id: str, subscription_id: str, description: str,
                    tax: Dict[str, Any], taxable_paise: int, total_paise: int,
                    gstin: Optional[str], line_items: List[Dict[str, Any]],
                    status: str = 'PAID', user: Optional[User] = None,
                    payment: Optional[Payment] = None, plan_id: Optional[str] = None,
                    cycle: Optional[str] = None) -> Dict[str, Any]:
    issued_at = _now()
    inv = Invoice.objects.create(
        invoice_no=None,
        user=user,
        subscription_id=subscription_id,
        plan_id=plan_id,
        payment=payment,
        tenant_id=tenant_id,
        billing_cycle=cycle,
        issued_at=issued_at,
        description=description,
        taxable_paise=int(taxable_paise),
        cgst_paise=int(tax['cgst_paise']),
        sgst_paise=int(tax['sgst_paise']),
        igst_paise=int(tax['igst_paise']),
        total_paise=int(total_paise),
        currency=CURRENCY,
        gstin=gstin,
        place_of_supply=tax['place_of_supply'],
        status=status,
        line_items=json.dumps(line_items) if line_items else None,
    )
    invoice_no = _invoice_number(issued_at, inv.invoice_id)
    inv.invoice_no = invoice_no
    inv.save(update_fields=['invoice_no'])
    return {
        'invoice_id': inv.invoice_id, 'invoice_no': invoice_no, 'invoice_number': invoice_no,
        'issued_at': issued_at, 'status': status,
        'total_paise': total_paise, 'total_display': format_inr(total_paise),
    }


def _list_invoices(tenant_id: str, user: Optional[User] = None, limit: int = 50) -> List[Dict[str, Any]]:
    qs = Invoice.objects.all()
    if user and getattr(user, 'is_authenticated', False):
        qs = qs.filter(user=user)
    else:
        qs = qs.filter(tenant_id=tenant_id)
    qs = qs.order_by('-invoice_id')[:min(limit, 500)]

    result = []
    for inv in qs:
        d = {
            'invoice_id': inv.invoice_id, 'invoice_no': inv.invoice_no,
            'subscription_id': inv.subscription_id, 'tenant_id': inv.tenant_id,
            'plan_id': inv.plan_id,
            'issued_at': inv.issued_at, 'description': inv.description,
            'taxable_paise': int(inv.taxable_paise or 0),
            'cgst_paise': int(inv.cgst_paise or 0),
            'sgst_paise': int(inv.sgst_paise or 0),
            'igst_paise': int(inv.igst_paise or 0),
            'total_paise': int(inv.total_paise or 0),
            'currency': inv.currency, 'gstin': inv.gstin,
            'place_of_supply': inv.place_of_supply, 'status': inv.status,
            'payment_id': inv.payment.payment_id if inv.payment else None,
            'line_items': json.loads(inv.line_items) if inv.line_items else [],
        }
        for field in ('taxable', 'cgst', 'sgst', 'igst', 'total'):
            d[f'{field}_display'] = format_inr(d.get(f'{field}_paise'))
            d[f'{field}_rupees'] = paise_to_rupees(d.get(f'{field}_paise'))
        result.append(d)
    return result


# ── Public APIs ──────────────────────────────────────────────────────────────
def plans_payload() -> Dict[str, Any]:
    catalog = get_all_active_plans()
    return {
        'status': 'success', 'currency': 'INR', 'currency_symbol': '₹',
        'gst_rate_percent': round(GST_RATE_BPS / 100, 2),
        'supplier_state_code': SUPPLIER_STATE_CODE,
        'billing_cycles': list(BILLING_CYCLES), 'payment_methods': list(PAYMENT_METHODS),
        'trial_days': TRIAL_DAYS, 'plans': catalog,
        'state_codes': [{'code': c, 'name': n} for c, n in sorted(STATE_CODES.items())],
    }


def promos_payload() -> Dict[str, Any]:
    now_dt = datetime.now(timezone.utc)
    redeemable = []
    for p in PromoCode.objects.all().order_by('code'):
        promo = _promo_model_to_dict(p)
        if not promo['active']:
            continue
        start = _parse_iso(promo['valid_from'])
        end = _parse_iso(promo['valid_until'])
        if start and now_dt < start:
            continue
        if end and now_dt > end:
            continue
        cap = promo['max_redemptions']
        if cap is not None and promo['times_redeemed'] >= int(cap):
            continue
        redeemable.append({
            'code': promo['code'], 'percent_off': promo['percent_off'],
            'description': promo['description'],
            'applicable_plans': promo['applicable_plans'],
            'valid_until': promo['valid_until'], 'redeemable': True,
        })
    return {'status': 'success', 'count': len(redeemable), 'promos': redeemable}


def current(tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None) -> Dict[str, Any]:
    user_obj, resolved_tenant = resolve_user_and_tenant(user, tenant_id)
    row = _load(resolved_tenant, user_obj)
    sub = serialize(row)
    quota = quota_snapshot(row)
    plan = get_plan(sub.get('plan_id')) or get_plan('starter')
    events = list(
        SubscriptionEvent.objects.filter(tenant_id=resolved_tenant).order_by('-event_id')[:5].values(
            'event_id', 'event_type', 'from_plan', 'to_plan',
            'amount_paise', 'notes', 'actor', 'created_at'
        )
    )
    wallet_data = get_wallet_data(user_obj) if user_obj else None

    return {
        'status': 'success', 'tenant_id': resolved_tenant,
        'user_id': user_obj.id if user_obj else None,
        'subscription': sub, 'plan_details': plan,
        'quota': quota, 'recent_events': events,
        'wallet': wallet_data,
        'has_api_key': bool(sub.get('has_api_key')),
    }


def quote(payload: Dict[str, Any], tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None) -> Dict[str, Any]:
    user_obj, resolved_tenant = resolve_user_and_tenant(user, tenant_id)
    plan = require_plan(payload.get('plan_id'))
    cycle = normalise_cycle(payload.get('billing_cycle'))
    state_code = normalise_state(payload.get('place_of_supply'))
    promo_code = normalise_promo_code(payload.get('promo_code'))
    now_dt = datetime.now(timezone.utc)

    current_row = _load(resolved_tenant, user_obj)
    current_plan_id = effective_plan_id(current_row)
    credit = (_proration_credit(current_row, now_dt)
              if current_plan_id != plan['id'] and current_plan_id not in ('starter', 'free')
              else _zero_credit())
    promo = evaluate_promo(promo_code, plan['id'], base_price_paise(plan, cycle))
    bd = _breakdown(plan, cycle, promo, state_code, credit)
    quota = quota_snapshot(current_row)

    wallet_balance_paise = 0
    if user_obj:
        wallet = get_or_create_wallet(user_obj)
        wallet_balance_paise = wallet.balance_paise

    sufficient_wallet = wallet_balance_paise >= bd['total_paise']

    return {
        'status': 'success', 'quoted_at': now_dt.isoformat(), 'tenant_id': resolved_tenant,
        'current_plan_id': current_plan_id,
        'change_type': _change_type(current_plan_id, plan['id']),
        'requires_payment': bd['total_paise'] > 0,
        'plan': plan,
        'promo': promo, 'proration': credit, 'breakdown': bd, 'current_quota': quota,
        'wallet': {
            'balance_paise': wallet_balance_paise,
            'balance_display': format_inr(wallet_balance_paise),
            'sufficient_balance': sufficient_wallet,
            'shortfall_paise': max(0, bd['total_paise'] - wallet_balance_paise),
            'shortfall_display': format_inr(max(0, bd['total_paise'] - wallet_balance_paise)),
        },
        'summary': {
            'plan_id': plan['id'], 'plan_name': plan['name'], 'billing_cycle': cycle,
            'line_items': bd['lines'],
            'base_amount_display': bd['base_amount_display'],
            'discount_display': bd['discount_display'],
            'credit_display': bd['credit_display'],
            'taxable_display': bd['taxable_display'],
            'igst_display': bd['tax']['igst_display'],
            'cgst_display': bd['tax']['cgst_display'],
            'sgst_display': bd['tax']['sgst_display'],
            'total_tax_display': bd['tax']['total_tax_display'],
            'total_display': bd['total_display'],
            'total_paise': bd['total_paise'],
            'gst_rate_percent': bd['tax']['gst_rate_percent'],
            'supply_type': bd['tax']['supply_type'],
            'place_of_supply': bd['tax']['place_of_supply'],
            'place_of_supply_name': bd['tax']['place_of_supply_name'],
        },
    }


def validate_promo(payload: Dict[str, Any], tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None) -> Dict[str, Any]:
    plan = require_plan(payload.get('plan_id'))
    cycle = normalise_cycle(payload.get('billing_cycle'))
    code = normalise_promo_code(payload.get('promo_code'))
    result = evaluate_promo(code, plan['id'], base_price_paise(plan, cycle))
    return {'status': 'success', 'promo': result}


def checkout(payload: Dict[str, Any], tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None) -> Dict[str, Any]:
    user_obj, resolved_tenant = resolve_user_and_tenant(user, tenant_id)
    plan = require_plan(payload.get('plan_id'))
    cycle = normalise_cycle(payload.get('billing_cycle'))
    payment_method = str(payload.get('payment_method') or 'WALLET').strip().upper()
    if payment_method not in PAYMENT_METHODS:
        payment_method = 'WALLET'

    raw_org = payload.get('organization_name') or (user_obj.organization_name if user_obj and user_obj.organization_name else None) or 'ImpactBridge Enterprise Subscriber'
    raw_email = payload.get('contact_email') or (user_obj.email if user_obj and user_obj.email else None) or 'subscriber@impactbridge.org'
    org = normalise_org(raw_org)
    email = normalise_email(raw_email)
    state_code = normalise_state(payload.get('place_of_supply'))
    gstin = normalise_gstin(payload.get('gstin'))
    promo_code = normalise_promo_code(payload.get('promo_code'))
    request_id = str(payload.get('request_id') or '').strip()[:128] or None
    want_trial = bool(payload.get('start_trial')) and not plan['is_free']
    now_dt = datetime.now(timezone.utc)

    # Idempotency check: if request_id was processed within 24h, return previous transaction
    if request_id:
        prior_payment = Payment.objects.filter(idempotency_key=request_id, payment_status='SUCCESS').first()
        if prior_payment:
            replay_row = _load(resolved_tenant, user_obj)
            prior_invoices = _list_invoices(resolved_tenant, user_obj, 1)
            return {
                'status': 'success', 'idempotent_replay': True, 'change_type': 'REPLAY',
                'message': f"Request {request_id} already applied. Replayed current subscription state.",
                'subscription': serialize(replay_row),
                'invoice': prior_invoices[0] if prior_invoices else None,
                'payment': {
                    'payment_id': prior_payment.payment_id,
                    'amount_paise': prior_payment.amount_paise,
                    'amount_display': format_inr(prior_payment.amount_paise),
                    'status': prior_payment.payment_status,
                },
                'quote': None, 'quota': quota_snapshot(replay_row), 'api_key': None,
            }

    current_row = _load(resolved_tenant, user_obj)
    from_plan = effective_plan_id(current_row)
    credit = (_proration_credit(current_row, now_dt)
              if (from_plan != plan['id'] and from_plan not in ('starter', 'free')) else _zero_credit())
    promo = evaluate_promo(promo_code, plan['id'], base_price_paise(plan, cycle))
    bd = _breakdown(plan, cycle, promo, state_code, credit)

    if want_trial:
        period_start_dt = now_dt
        period_end_dt = now_dt + timedelta(days=plan.get('trial_days', TRIAL_DAYS) or TRIAL_DAYS)
        status = _STATUS_TRIALING
        charged_paise = 0
    elif plan['is_free']:
        period_start_dt = now_dt
        period_end_dt = None
        status = _STATUS_ACTIVE
        charged_paise = 0
    else:
        period_start_dt = now_dt
        period_end_dt = period_end(now_dt, cycle)
        status = _STATUS_ACTIVE
        charged_paise = bd['total_paise']

    change = _change_type(from_plan, plan['id'])

    # ATOMIC PAYMENT & SUBSCRIPTION UPDATE
    if charged_paise > 0 and payment_method == 'WALLET':
        if not user_obj:
            raise SubscriptionError('Please log in to your account to pay with wallet funds.', 401, 'unauthorized')
        pre_wallet = get_or_create_wallet(user_obj)
        if pre_wallet.balance_paise < charged_paise:
            fail_id = f"PAY_{uuid.uuid4().hex[:12].upper()}"
            Payment.objects.create(
                payment_id=fail_id,
                user=user_obj,
                plan_code=plan['id'],
                amount_paise=charged_paise,
                currency=CURRENCY,
                payment_method='WALLET',
                payment_status='FAILED',
                payment_type=change,
                failure_reason=f"Insufficient balance. Required: {format_inr(charged_paise)}, Available: {format_inr(pre_wallet.balance_paise)}",
                idempotency_key=request_id,
                is_prototype=True,
            )
            raise SubscriptionError(
                f"Insufficient wallet balance. Required: {format_inr(charged_paise)}, Current Balance: {format_inr(pre_wallet.balance_paise)}. Please top up your wallet.",
                400, 'insufficient_wallet_balance'
            )

    with transaction.atomic():
        payment = None
        wallet = None

        if charged_paise > 0:
            if payment_method == 'WALLET':
                wallet = Wallet.objects.select_for_update().get_or_create(user=user_obj, defaults={'balance_paise': 0})[0]
                if wallet.balance_paise < charged_paise:
                    fail_id = f"PAY_{uuid.uuid4().hex[:12].upper()}"
                    Payment.objects.create(
                        payment_id=fail_id,
                        user=user_obj,
                        plan_code=plan['id'],
                        amount_paise=charged_paise,
                        currency=CURRENCY,
                        payment_method='WALLET',
                        payment_status='FAILED',
                        payment_type=change,
                        failure_reason=f"Insufficient balance. Required: {format_inr(charged_paise)}, Available: {format_inr(wallet.balance_paise)}",
                        idempotency_key=request_id,
                        is_prototype=True,
                    )
                    raise SubscriptionError(
                        f"Insufficient wallet balance. Required: {format_inr(charged_paise)}, Current Balance: {format_inr(wallet.balance_paise)}. Please top up your wallet.",
                        400, 'insufficient_wallet_balance'
                    )

                # Deduct wallet atomically
                bal_before = wallet.balance_paise
                bal_after = bal_before - charged_paise
                wallet.balance_paise = bal_after
                wallet.save(update_fields=['balance_paise', 'updated_at'])

                pay_id = f"PAY_{uuid.uuid4().hex[:12].upper()}"
                payment = Payment.objects.create(
                    payment_id=pay_id,
                    user=user_obj,
                    plan_code=plan['id'],
                    amount_paise=charged_paise,
                    currency=CURRENCY,
                    payment_method='WALLET',
                    payment_status='SUCCESS',
                    payment_type=change,
                    transaction_reference=f"TXN_W_{uuid.uuid4().hex[:8].upper()}",
                    idempotency_key=request_id,
                    is_prototype=True,
                    metadata={'balance_before': bal_before, 'balance_after': bal_after, 'plan': plan['id']},
                    completed_at=dtz.now(),
                )

                wtxn_id = f"WTXN_{uuid.uuid4().hex[:12].upper()}"
                WalletTransaction.objects.create(
                    transaction_id=wtxn_id,
                    wallet=wallet,
                    user=user_obj,
                    transaction_type='SUBSCRIPTION_PAYMENT' if change != 'UPGRADE' else 'UPGRADE_PAYMENT',
                    credit_or_debit='DEBIT',
                    amount_paise=charged_paise,
                    balance_before_paise=bal_before,
                    balance_after_paise=bal_after,
                    reference_type='PAYMENT',
                    reference_id=pay_id,
                    description=f"{plan['name']} {cycle.title()} activation",
                    status='SUCCESS',
                )
            else:
                # Other prototype payment methods (UPI, Card, NetBanking, etc.)
                pay_id = f"PAY_{uuid.uuid4().hex[:12].upper()}"
                payment = Payment.objects.create(
                    payment_id=pay_id,
                    user=user_obj,
                    plan_code=plan['id'],
                    amount_paise=charged_paise,
                    currency=CURRENCY,
                    payment_method=payment_method,
                    payment_status='SUCCESS',
                    payment_type=change,
                    transaction_reference=f"TXN_PROTO_{uuid.uuid4().hex[:8].upper()}",
                    idempotency_key=request_id,
                    is_prototype=True,
                    metadata={'method': payment_method, 'plan': plan['id']},
                    completed_at=dtz.now(),
                )

        # Generate / retain API key if entitled
        existing_sub = Subscription.objects.filter(tenant_id=resolved_tenant).first()
        api_key_plain = None
        api_key_hash = existing_sub.api_key_hash if existing_sub else None
        api_key_prefix = existing_sub.api_key_prefix if existing_sub else None
        api_key_last4 = existing_sub.api_key_last4 if existing_sub else None

        if plan['limits'].get('api_access') and not api_key_hash:
            api_key_plain, api_key_hash, api_key_prefix, api_key_last4 = _new_api_key(plan['id'])

        sub_id = existing_sub.subscription_id if existing_sub else f"SUB_{uuid.uuid4().hex[:12].upper()}"
        plan_record = Plan.objects.filter(code=plan['id']).first()

        sub_obj, _ = Subscription.objects.update_or_create(
            tenant_id=resolved_tenant,
            defaults={
                'subscription_id': sub_id,
                'user': user_obj,
                'plan_record': plan_record,
                'plan_id': plan['id'],
                'status': status,
                'billing_cycle': cycle,
                'organization_name': org,
                'contact_email': email,
                'activated_at': now_dt.isoformat(),
                'current_period_start': period_start_dt.isoformat(),
                'current_period_end': period_end_dt.isoformat() if period_end_dt else None,
                'cancel_at_period_end': False,
                'canceled_at': None,
                'cancel_reason': None,
                'auto_renew': bool(plan.get('auto_renew_default', True)),
                'pending_downgrade_plan': None,
                'pending_downgrade_cycle': None,
                'pending_downgrade_date': None,
                'renewal_failure_count': 0,
                'promo_code': promo.get('code') if promo.get('applied') else None,
                'promo_percent': int(promo.get('percent_off') or 0) if promo.get('applied') else 0,
                'base_amount_paise': bd['base_amount_paise'],
                'discount_paise': bd['discount_paise'],
                'taxable_paise': 0 if want_trial else bd['taxable_paise'],
                'cgst_paise': 0 if want_trial else bd['tax']['cgst_paise'],
                'sgst_paise': 0 if want_trial else bd['tax']['sgst_paise'],
                'igst_paise': 0 if want_trial else bd['tax']['igst_paise'],
                'total_paise': charged_paise,
                'currency': CURRENCY,
                'payment_method': payment_method if charged_paise > 0 else None,
                'transaction_id': payment.payment_id if payment else None,
                'gstin': gstin,
                'place_of_supply': bd['tax']['place_of_supply'],
                'supply_type': bd['tax']['supply_type'],
                'seats': plan['limits'].get('seats') or 1,
                'daily_match_quota': plan['limits'].get('daily_matches'),
                'api_key_hash': api_key_hash,
                'api_key_prefix': api_key_prefix,
                'api_key_last4': api_key_last4,
                'request_id': request_id,
                'created_at': existing_sub.created_at if existing_sub else now_dt.isoformat(),
                'updated_at': now_dt.isoformat(),
            }
        )

        if payment:
            payment.subscription = sub_obj
            payment.save(update_fields=['subscription'])

        # Create Invoice
        invoice = None
        if charged_paise > 0:
            invoice = _create_invoice(
                resolved_tenant, sub_id,
                f"{plan['name']} — {cycle.title()} subscription",
                bd['tax'], bd['taxable_paise'], charged_paise, gstin, bd['lines'],
                status='PAID', user=user_obj, payment=payment, plan_id=plan['id'], cycle=cycle
            )

        # Audit SubscriptionEvent
        SubscriptionEvent.objects.create(
            subscription_id=sub_id, tenant_id=resolved_tenant, event_type=change,
            from_plan=from_plan, to_plan=plan['id'], amount_paise=charged_paise,
            notes=f"{plan['name']} ({cycle.upper()}); paid {format_inr(charged_paise)} via {payment_method}",
            actor=user_obj.username if user_obj else 'Subscriber', created_at=now_dt.isoformat(),
        )

        # Increment promo code redemptions
        if promo.get('applied') and charged_paise > 0:
            PromoCode.objects.filter(code=promo['code']).update(times_redeemed=models_f_plus_1('times_redeemed'))

    result_row = _load(resolved_tenant, user_obj)
    quota = quota_snapshot(result_row)
    wallet_data = get_wallet_data(user_obj) if user_obj else None

    msg = (f"{plan['name']} trial activated for {plan.get('trial_days', TRIAL_DAYS)} days." if want_trial
           else f"{plan['name']} activated — {format_inr(charged_paise)} paid via {payment_method}." if charged_paise > 0
           else f"{plan['name']} activated on the free tier.")

    return {
        'status': 'success', 'success': True, 'idempotent_replay': False, 'change_type': change,
        'message': msg,
        'subscription': serialize(result_row),
        'invoice': invoice,
        'payment': {
            'payment_id': payment.payment_id if payment else None,
            'amount_paise': charged_paise,
            'amount_display': format_inr(charged_paise),
            'method': payment_method,
            'status': 'SUCCESS',
            'is_prototype': True,
        } if payment else None,
        'wallet': wallet_data,
        'quote': {'breakdown': bd, 'promo': promo, 'proration': credit},
        'quota': quota, 'api_key': api_key_plain,
        'api_key_note': 'Store this API key now — it is shown only once.' if api_key_plain else None,
    }


def models_f_plus_1(field: str):
    from django.db.models import F
    return F(field) + 1


def cancel(payload: Dict[str, Any], tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None) -> Dict[str, Any]:
    user_obj, resolved_tenant = resolve_user_and_tenant(user, tenant_id)
    immediate = bool(payload.get('immediate'))
    reason = ' '.join(str(payload.get('reason') or '').split())[:300] or None
    now_dt = datetime.now(timezone.utc)

    row = _load(resolved_tenant, user_obj)
    if not row or str(row.get('plan_id') or '').lower() in ('starter', 'free'):
        raise SubscriptionError('There is no paid subscription to cancel.', 409, 'no_paid_subscription')
    if row.get('status') == _STATUS_CANCELED:
        raise SubscriptionError('This subscription is already cancelled.', 409, 'already_canceled')

    if immediate:
        starter_plan = Plan.objects.filter(code='starter').first()
        Subscription.objects.filter(tenant_id=resolved_tenant).update(
            status=_STATUS_CANCELED, plan_id='starter', plan_record=starter_plan,
            cancel_at_period_end=False, auto_renew=False,
            canceled_at=now_dt.isoformat(), cancel_reason=reason,
            current_period_end=now_dt.isoformat(), updated_at=now_dt.isoformat(),
        )
        SubscriptionEvent.objects.create(
            subscription_id=row['subscription_id'], tenant_id=resolved_tenant,
            event_type='CANCEL_IMMEDIATE', from_plan=row.get('plan_id'), to_plan='starter',
            amount_paise=0, notes=reason or 'Cancelled immediately by subscriber.',
            actor=user_obj.username if user_obj else 'Subscriber', created_at=now_dt.isoformat(),
        )
        message = 'Subscription cancelled immediately. Your entitlements have reverted to the free tier.'
    else:
        Subscription.objects.filter(tenant_id=resolved_tenant).update(
            cancel_at_period_end=True, auto_renew=False,
            canceled_at=now_dt.isoformat(), cancel_reason=reason, updated_at=now_dt.isoformat(),
        )
        SubscriptionEvent.objects.create(
            subscription_id=row['subscription_id'], tenant_id=resolved_tenant,
            event_type='CANCEL_AT_PERIOD_END', from_plan=row.get('plan_id'), to_plan=row.get('plan_id'),
            amount_paise=0, notes=reason or 'Auto-renew cancelled; scheduled to expire at period end.',
            actor=user_obj.username if user_obj else 'Subscriber', created_at=now_dt.isoformat(),
        )
        message = (f"Auto-renewal cancelled. Your plan remains active until {str(row.get('current_period_end'))[:10]}. "
                   'No further charges will occur.')

    updated = serialize(_load(resolved_tenant, user_obj))
    return {'status': 'success', 'message': message, 'subscription': updated}


def resume(payload: Dict[str, Any], tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None) -> Dict[str, Any]:
    user_obj, resolved_tenant = resolve_user_and_tenant(user, tenant_id)
    now_dt = datetime.now(timezone.utc)
    row = _load(resolved_tenant, user_obj)
    if not row or str(row.get('plan_id') or '').lower() in ('starter', 'free'):
        raise SubscriptionError('No paid subscription is available to reactivate.', 409, 'no_paid_subscription')

    Subscription.objects.filter(tenant_id=resolved_tenant).update(
        cancel_at_period_end=False, auto_renew=True, canceled_at=None,
        cancel_reason=None, updated_at=now_dt.isoformat(),
    )
    SubscriptionEvent.objects.create(
        subscription_id=row['subscription_id'], tenant_id=resolved_tenant,
        event_type='CANCEL_REVERSED', from_plan=row.get('plan_id'), to_plan=row.get('plan_id'),
        amount_paise=0, notes='Auto-renewal reactivated by subscriber.',
        actor=user_obj.username if user_obj else 'Subscriber', created_at=now_dt.isoformat(),
    )
    updated = serialize(_load(resolved_tenant, user_obj))
    return {'status': 'success', 'message': 'Auto-renewal reactivated. Your subscription will renew automatically.', 'subscription': updated}


def toggle_auto_renew(user: User, enable: bool) -> Dict[str, Any]:
    sub = Subscription.objects.filter(user=user).first()
    if not sub:
        raise SubscriptionError('No subscription found for your user account.', 404, 'no_subscription')
    sub.auto_renew = enable
    if not enable:
        sub.cancel_at_period_end = True
    else:
        sub.cancel_at_period_end = False
    sub.save(update_fields=['auto_renew', 'cancel_at_period_end', 'updated_at'])

    SubscriptionEvent.objects.create(
        subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
        event_type='AUTO_RENEW_ENABLED' if enable else 'AUTO_RENEW_DISABLED',
        from_plan=sub.plan_id, to_plan=sub.plan_id, amount_paise=0,
        notes=f"Auto-renew set to {'ON' if enable else 'OFF'} by user.",
        actor=user.username, created_at=_now(),
    )
    return {
        'status': 'success',
        'auto_renew': sub.auto_renew,
        'message': f"Auto-renewal is now {'ENABLED' if enable else 'DISABLED'}.",
    }


def schedule_downgrade(payload: Dict[str, Any], user: User) -> Dict[str, Any]:
    target_plan_id = payload.get('plan_id')
    target_plan = require_plan(target_plan_id)
    sub = Subscription.objects.filter(user=user).first()
    if not sub:
        raise SubscriptionError('No active subscription found.', 404, 'no_subscription')

    if target_plan['id'] == sub.plan_id:
        raise SubscriptionError('You are already on this plan.', 400, 'same_plan')

    now_dt = datetime.now(timezone.utc)
    sub.pending_downgrade_plan = target_plan['id']
    sub.pending_downgrade_cycle = payload.get('billing_cycle', sub.billing_cycle)
    sub.pending_downgrade_date = sub.current_period_end
    sub.save(update_fields=['pending_downgrade_plan', 'pending_downgrade_cycle', 'pending_downgrade_date', 'updated_at'])

    SubscriptionEvent.objects.create(
        subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
        event_type='DOWNGRADE_SCHEDULED', from_plan=sub.plan_id, to_plan=target_plan['id'],
        amount_paise=0, notes=f"Plan change to {target_plan['name']} scheduled for {sub.current_period_end}.",
        actor=user.username, created_at=now_dt.isoformat(),
    )

    return {
        'status': 'success',
        'message': f"Plan change to {target_plan['name']} scheduled for {str(sub.current_period_end)[:10]}. You will retain your current access until then.",
        'pending_change_plan': target_plan['id'],
        'effective_date': sub.current_period_end,
    }

schedule_plan_change = schedule_downgrade


def change_plan(payload: Dict[str, Any], user: User, tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, Any]:
    """Unified plan change workflow for higher-priced, lower-priced, or free plan changes."""
    target_plan_id = payload.get('plan_id')
    target_plan = require_plan(target_plan_id)
    user_obj, resolved_tenant = resolve_user_and_tenant(user, tenant_id)
    current_row = _load(resolved_tenant, user_obj)
    curr_plan_id = effective_plan_id(current_row)

    if curr_plan_id == target_plan['id']:
        raise SubscriptionError('You are already on this plan.', 400, 'same_plan')

    curr_plan = get_plan(curr_plan_id) or get_plan('starter')
    cycle = normalise_cycle(payload.get('billing_cycle') or current_row.get('billing_cycle') or 'monthly')
    target_price = base_price_paise(target_plan, cycle)
    curr_price = base_price_paise(curr_plan, cycle) if curr_plan else 0

    if target_price > curr_price and not target_plan.get('is_free'):
        # Higher-priced transition (Immediate activation with proration)
        return checkout(payload, tenant_id=resolved_tenant, user=user)
    else:
        # Lower-priced or Free transition (Active until current period ends)
        return schedule_downgrade(payload, user=user)


def history(tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None, limit: int = 50) -> Dict[str, Any]:
    user_obj, resolved_tenant = resolve_user_and_tenant(user, tenant_id)
    qs = SubscriptionEvent.objects.all()
    if user_obj:
        qs = qs.filter(tenant_id=resolved_tenant)
    else:
        qs = qs.filter(tenant_id=resolved_tenant)
    events = list(
        qs.order_by('-event_id')[:min(limit, 500)].values(
            'event_id', 'event_type', 'from_plan', 'to_plan',
            'amount_paise', 'notes', 'actor', 'created_at',
        )
    )
    for e in events:
        e['amount_display'] = format_inr(e['amount_paise'])
        e['amount_rupees'] = paise_to_rupees(e['amount_paise'])
    return {'status': 'success', 'tenant_id': resolved_tenant, 'count': len(events), 'events': events}


def invoices_payload(tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None, limit: int = 50) -> Dict[str, Any]:
    user_obj, resolved_tenant = resolve_user_and_tenant(user, tenant_id)
    docs = _list_invoices(resolved_tenant, user_obj, limit)
    return {'status': 'success', 'tenant_id': resolved_tenant, 'count': len(docs), 'invoices': docs}


def usage_payload(tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None) -> Dict[str, Any]:
    user_obj, resolved_tenant = resolve_user_and_tenant(user, tenant_id)
    row = _load(resolved_tenant, user_obj)
    quota = quota_snapshot(row)
    return {'status': 'success', 'tenant_id': resolved_tenant, 'quota': quota}


def rotate_api_key(tenant_id: str = DEFAULT_TENANT_ID, user: Optional[User] = None) -> Dict[str, Any]:
    user_obj, resolved_tenant = resolve_user_and_tenant(user, tenant_id)
    row = _load(resolved_tenant, user_obj)
    plan = _entitlement(row)
    if not plan['limits'].get('api_access'):
        raise SubscriptionError(
            f"API access is not included in the {plan['name']} plan. "
            'Upgrade to Corporate Enterprise or Foundation Master.', 403, 'api_access_not_included')
    plain, digest, prefix, last4 = _new_api_key(plan['id'])
    now_dt = datetime.now(timezone.utc)
    Subscription.objects.filter(tenant_id=resolved_tenant).update(
        api_key_hash=digest, api_key_prefix=prefix,
        api_key_last4=last4, updated_at=now_dt.isoformat(),
    )
    SubscriptionEvent.objects.create(
        subscription_id=row.get('subscription_id'), tenant_id=resolved_tenant,
        event_type='API_KEY_ROTATED', from_plan=plan['id'], to_plan=plan['id'],
        amount_paise=0,
        notes=f"Previous key revoked; new prefix {prefix} issued.",
        actor=user_obj.username if user_obj else 'Subscriber', created_at=now_dt.isoformat(),
    )
    quota = quota_snapshot(row)
    return {
        'status': 'success', 'api_key': plain,
        'api_key_prefix': prefix, 'api_key_last4': last4,
        'message': 'A new API key was issued. The previous key is now invalid.',
        'quota': quota,
    }


# ── RENEWAL ENGINE (Automated / Admin Run) ────────────────────────────────────
def process_subscription_renewals(force: bool = False, force_run: bool = False, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    force_run = force or force_run
    now_dt = datetime.now(timezone.utc)
    qs = Subscription.objects.filter(status=_STATUS_ACTIVE)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    processed = 0
    renewed = 0
    failed = 0
    expired = 0
    details = []

    for sub in qs:
        # Check if due for renewal
        pid = str(sub.plan_id or '').lower()
        if pid in ('starter', 'free') or not sub.current_period_end:
            continue

        end_dt = _parse_iso(sub.current_period_end)
        is_due = force_run or (end_dt and now_dt >= end_dt)

        if not is_due:
            continue

        processed += 1

        # Check for scheduled downgrade
        if sub.pending_downgrade_plan:
            down_plan = get_plan(sub.pending_downgrade_plan) or get_plan('starter')
            sub.plan_id = down_plan['id']
            sub.plan_record = Plan.objects.filter(code=down_plan['id']).first()
            sub.pending_downgrade_plan = None
            sub.pending_downgrade_cycle = None
            sub.pending_downgrade_date = None
            sub.current_period_start = now_dt.isoformat()
            sub.current_period_end = period_end(now_dt, sub.billing_cycle or 'monthly').isoformat() if not down_plan['is_free'] else None
            sub.save()
            SubscriptionEvent.objects.create(
                subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
                event_type='DOWNGRADE_APPLIED', from_plan=sub.plan_id, to_plan=down_plan['id'],
                amount_paise=0, notes=f"Applied scheduled plan change to {down_plan['name']}",
                actor='RenewalEngine', created_at=now_dt.isoformat(),
            )
            details.append({'subscription_id': sub.subscription_id, 'result': 'downgraded', 'plan': down_plan['id']})
            continue

        # Check if auto_renew is OFF
        if not sub.auto_renew:
            starter_plan = Plan.objects.filter(code='starter').first()
            sub.status = _STATUS_EXPIRED
            sub.plan_record = starter_plan
            sub.plan_id = 'starter'
            sub.save(update_fields=['status', 'plan_record', 'plan_id', 'updated_at'])
            SubscriptionEvent.objects.create(
                subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
                event_type='EXPIRED', from_plan=pid, to_plan='starter',
                amount_paise=0, notes='Auto-renewal was off; subscription expired at period end.',
                actor='RenewalEngine', created_at=now_dt.isoformat(),
            )
            expired += 1
            details.append({'subscription_id': sub.subscription_id, 'result': 'expired', 'reason': 'auto_renew_off'})
            continue

        # Auto-renewal is ON: attempt wallet payment
        plan_dict = get_plan(sub.plan_id)
        if not plan_dict or plan_dict['is_free']:
            continue

        cycle = sub.billing_cycle or 'monthly'
        bd = _breakdown(plan_dict, cycle, {'applied': False}, sub.place_of_supply or SUPPLIER_STATE_CODE, _zero_credit())
        amount_needed = bd['total_paise']

        user = sub.user
        if not user:
            # Cannot charge wallet without user
            sub.renewal_failure_count += 1
            sub.last_renewal_attempt = now_dt.isoformat()
            sub.save(update_fields=['renewal_failure_count', 'last_renewal_attempt'])
            failed += 1
            details.append({'subscription_id': sub.subscription_id, 'result': 'failed', 'reason': 'no_user_account'})
            continue

        with transaction.atomic():
            wallet = Wallet.objects.select_for_update().get_or_create(user=user, defaults={'balance_paise': 0})[0]
            if wallet.balance_paise >= amount_needed:
                # Success: Deduct wallet
                bal_before = wallet.balance_paise
                bal_after = bal_before - amount_needed
                wallet.balance_paise = bal_after
                wallet.save(update_fields=['balance_paise', 'updated_at'])

                # Create Payment
                pay_id = f"PAY_REN_{uuid.uuid4().hex[:12].upper()}"
                payment = Payment.objects.create(
                    payment_id=pay_id,
                    user=user,
                    subscription=sub,
                    plan_code=sub.plan_id,
                    amount_paise=amount_needed,
                    currency=CURRENCY,
                    payment_method='WALLET',
                    payment_status='SUCCESS',
                    payment_type='RENEWAL',
                    transaction_reference=f"TXN_REN_{uuid.uuid4().hex[:8].upper()}",
                    is_prototype=True,
                    metadata={'renewal_cycle': cycle, 'period_extended': True},
                    completed_at=dtz.now(),
                )

                # Record WalletTransaction
                wtxn_id = f"WTXN_{uuid.uuid4().hex[:12].upper()}"
                WalletTransaction.objects.create(
                    transaction_id=wtxn_id,
                    wallet=wallet,
                    user=user,
                    transaction_type='SUBSCRIPTION_RENEWAL',
                    credit_or_debit='DEBIT',
                    amount_paise=amount_needed,
                    balance_before_paise=bal_before,
                    balance_after_paise=bal_after,
                    reference_type='PAYMENT',
                    reference_id=pay_id,
                    description=f"Auto-renewal payment for {plan_dict['name']} ({cycle})",
                    status='SUCCESS',
                )

                # Extend subscription period
                new_start = end_dt if end_dt else now_dt
                new_end = period_end(new_start, cycle)
                sub.current_period_start = new_start.isoformat()
                sub.current_period_end = new_end.isoformat()
                sub.renewal_failure_count = 0
                sub.last_renewal_attempt = now_dt.isoformat()
                sub.save(update_fields=['current_period_start', 'current_period_end', 'renewal_failure_count', 'last_renewal_attempt', 'updated_at'])

                # Create Invoice
                _create_invoice(
                    sub.tenant_id, sub.subscription_id,
                    f"{plan_dict['name']} — {cycle.title()} renewal",
                    bd['tax'], bd['taxable_paise'], amount_needed, sub.gstin, bd['lines'],
                    status='PAID', user=user, payment=payment, plan_id=sub.plan_id, cycle=cycle
                )

                # SubscriptionEvent
                SubscriptionEvent.objects.create(
                    subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
                    event_type='RENEWAL_SUCCESS', from_plan=sub.plan_id, to_plan=sub.plan_id,
                    amount_paise=amount_needed,
                    notes=f"Auto-renewed for {cycle} period ending {new_end.date().isoformat()}. Charged {format_inr(amount_needed)} to wallet.",
                    actor='RenewalEngine', created_at=now_dt.isoformat(),
                )

                renewed += 1
                details.append({'subscription_id': sub.subscription_id, 'result': 'renewed', 'amount_paise': amount_needed})
            else:
                # Failed: Insufficient funds in wallet
                sub.renewal_failure_count += 1
                sub.last_renewal_attempt = now_dt.isoformat()

                pay_id = f"PAY_FAIL_{uuid.uuid4().hex[:12].upper()}"
                Payment.objects.create(
                    payment_id=pay_id,
                    user=user,
                    subscription=sub,
                    plan_code=sub.plan_id,
                    amount_paise=amount_needed,
                    currency=CURRENCY,
                    payment_method='WALLET',
                    payment_status='FAILED',
                    payment_type='RENEWAL',
                    failure_reason=f"Insufficient wallet balance. Required: {format_inr(amount_needed)}, Available: {format_inr(wallet.balance_paise)}",
                    is_prototype=True,
                )

                SubscriptionEvent.objects.create(
                    subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
                    event_type='RENEWAL_FAILED', from_plan=sub.plan_id, to_plan=sub.plan_id,
                    amount_paise=0,
                    notes=f"Renewal failed: insufficient wallet balance ({format_inr(wallet.balance_paise)} available, {format_inr(amount_needed)} required).",
                    actor='RenewalEngine', created_at=now_dt.isoformat(),
                )

                if sub.renewal_failure_count >= 3:
                    # Grace period expired: downgrade to starter
                    starter_plan = Plan.objects.filter(code='starter').first()
                    sub.status = _STATUS_EXPIRED
                    sub.plan_record = starter_plan
                    sub.plan_id = 'starter'
                    SubscriptionEvent.objects.create(
                        subscription_id=sub.subscription_id, tenant_id=sub.tenant_id,
                        event_type='EXPIRED', from_plan=pid, to_plan='starter',
                        amount_paise=0, notes="Expired after 3 failed renewal attempts.",
                        actor='RenewalEngine', created_at=now_dt.isoformat(),
                    )
                    expired += 1

                sub.save(update_fields=['status', 'plan_record', 'plan_id', 'renewal_failure_count', 'last_renewal_attempt', 'updated_at'])
                failed += 1
                details.append({'subscription_id': sub.subscription_id, 'result': 'failed', 'reason': 'insufficient_wallet_balance'})

    return {
        'status': 'success',
        'processed': processed,
        'renewed': renewed,
        'failed': failed,
        'expired': expired,
        'executed_at': now_dt.isoformat(),
        'details': details,
    }
