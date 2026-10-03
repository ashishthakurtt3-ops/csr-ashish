"""
Subscription / billing service — Django-ORM edition.

This module is a complete, self-contained replacement for the legacy
``app.subscription`` module.  All data is read from / written to the
Django ORM (MySQL, the project's primary database), so no raw PyMySQL
connection is opened.

Public surface used by ``subscription_api_views.py``:
    plans_payload()
    promos_payload()
    current(tenant_id)
    quote(payload, tenant_id)
    validate_promo(payload, tenant_id)
    checkout(payload, tenant_id)
    cancel(payload, tenant_id)
    resume(payload, tenant_id)
    history(tenant_id, limit)
    invoices_payload(tenant_id, limit)
    usage_payload(tenant_id)
    rotate_api_key(tenant_id)
    normalise_tenant(value)
    SubscriptionError
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

# ── Django ORM imports (safe to use anywhere settings are configured) ──────
from modules.admin_panel.models import (
    PromoCode, Subscription, SubscriptionEvent, Invoice,
)

# ── Money / currency constants ──────────────────────────────────────────────
CURRENCY = 'INR'
GST_RATE_BPS = 1800          # 18.00 %  (1 % = 100 bps)
SUPPLIER_STATE_CODE = str(os.environ.get('SUPPLIER_STATE_CODE', '29')).strip().upper()
DEFAULT_TENANT_ID = 'tenant_default'
TRIAL_DAYS = int(os.environ.get('SUBSCRIPTION_TRIAL_DAYS', '14'))

PAYMENT_METHODS = ('UPI', 'Card', 'NetBanking', 'Corporate PO', 'NEFT')
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


# ── Exception ───────────────────────────────────────────────────────────────
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


# ── Plan catalogue ────────────────────────────────────────────────────────────
_RAW_PLANS: List[Dict[str, Any]] = [
    {
        'id': 'starter', 'name': 'Community Starter', 'badge': 'Free Forever',
        'is_popular': False, 'price_monthly': 0, 'price_yearly': 0,
        'billing_note': 'No credit card required',
        'description': 'Essential CSR intelligence for grassroots non-profits.',
        'features': [
            'Full Top 200 Listed Companies Registry',
            'Verified Official Corporate & CSR Portal URLs',
            '5 Donor Matchmaker Queries / Day',
            'Daily Web Crawl Provenance Logs',
            'CSV Exports (up to 50 records / month)',
            'Community Email Support',
        ],
        'highlight_features': ['5 Matches/Day', '200 Companies', 'Standard Exports'],
        'cta_text': 'Start Free',
        'limits': {'daily_matches': 5, 'api_access': False, 'live_reprobe': False,
                   'seats': 1, 'export_rows_per_month': 50},
    },
    {
        'id': 'pro', 'name': 'Impact Pro', 'badge': 'Most Popular',
        'is_popular': True, 'price_monthly': 4999, 'price_yearly': 47990,
        'billing_note': 'Billed monthly or annually (+18% GST)',
        'description': 'Advanced discovery & intelligence suite for active NGOs.',
        'features': [
            'Everything in Starter, plus:',
            'Unlimited Donor Matchmaker Queries',
            'Live Website Re-Check & On-Demand Web Scraping',
            'Real-Time Corporate Open RFPs & Grant Deadline Radar',
            '1-Click Tailored CSR Pitch & Outreach Email Generator',
            'Live Social Impact Job Board & Verified Recruiter Links',
            'Outreach Pipeline CRM with Custom Tags & Export',
            'Unlimited Master Dataset Exports (CSV & JSON)',
            'Priority Email & Chat Support',
        ],
        'highlight_features': ['Unlimited Matchmaker', 'Live Scrape On-Demand',
                               'Open RFPs Radar', 'Outreach CRM'],
        'cta_text': 'Upgrade to Impact Pro',
        'limits': {'daily_matches': None, 'api_access': False, 'live_reprobe': True,
                   'seats': 3, 'export_rows_per_month': None},
    },
    {
        'id': 'enterprise', 'name': 'Enterprise CSR', 'badge': 'Enterprise',
        'is_popular': False, 'price_monthly': 19999, 'price_yearly': 189990,
        'billing_note': 'Billed monthly or annually (+18% GST)',
        'description': 'High-volume intelligence for large foundations.',
        'features': [
            'Everything in Pro, plus:',
            '10 Dedicated Team Seats & Multi-User Collaboration',
            'Statutory Section 135 & Schedule VII Audit Reports',
            'Real-Time Slack & Microsoft Teams Webhook Alerts',
            'Priority High-Speed Web Scraping Probes (Hourly Sync)',
            'Custom Corporate Domain & Subsidiary Tracking',
            'Auditor-Ready Evidence Packs with Raw Provenance',
            'Dedicated CSR Account Strategist & 99.9% SLA',
        ],
        'highlight_features': ['10 Team Seats', 'Section 135 Audit Reports',
                               'Slack / Teams Webhooks', 'Hourly Crawl Priority'],
        'cta_text': 'Upgrade to Enterprise',
        'limits': {'daily_matches': None, 'api_access': True, 'live_reprobe': True,
                   'seats': 10, 'export_rows_per_month': None},
    },
    {
        'id': 'api', 'name': 'Institutional Data Feed & API', 'badge': 'Developer Feed',
        'is_popular': False, 'price_monthly': 49999, 'price_yearly': 479990,
        'billing_note': 'Billed monthly or annually (+18% GST)',
        'description': 'Programmatic access for research institutions & fintech.',
        'features': [
            'Everything in Enterprise, plus:',
            'Dedicated REST API with Key Management',
            'Batch Export Up to 10,000 Records per Call',
            'Custom Data Ingestion Hooks (webhooks)',
            'Premium SLA with 24/7 Support',
        ],
        'highlight_features': ['REST API Access', '10K Batch Exports', 'Webhooks', '24/7 SLA'],
        'cta_text': 'Contact Sales',
        'limits': {'daily_matches': None, 'api_access': True, 'live_reprobe': True,
                   'seats': 25, 'export_rows_per_month': None},
    },
]


def _build_catalog() -> List[Dict[str, Any]]:
    catalog = []
    for raw in _RAW_PLANS:
        monthly = rupees_to_paise(raw['price_monthly'])
        yearly = rupees_to_paise(raw['price_yearly'])
        full_year = monthly * 12
        savings = max(0, full_year - yearly)
        savings_percent = round((savings / full_year) * 100, 1) if full_year else 0.0
        plan = dict(raw)
        plan['price_monthly_paise'] = monthly
        plan['price_yearly_paise'] = yearly
        plan['price_monthly_display'] = format_inr(monthly)
        plan['price_yearly_display'] = format_inr(yearly)
        plan['currency'] = '₹'
        plan['savings_yearly_paise'] = savings
        plan['savings_yearly_display'] = format_inr(savings)
        plan['savings_percent'] = savings_percent
        plan['savings_label'] = (
            f'Save {format_inr(savings)} / year ({savings_percent}% off)'
            if savings else None
        )
        plan['is_free'] = monthly == 0
        plan['is_contact_sales'] = raw['id'] == 'api'
        catalog.append(plan)
    return catalog


PLANS_CATALOG: List[Dict[str, Any]] = _build_catalog()
PLANS_BY_ID: Dict[str, Dict[str, Any]] = {p['id']: p for p in PLANS_CATALOG}


def get_plan(plan_id: Any) -> Optional[Dict[str, Any]]:
    return PLANS_BY_ID.get(str(plan_id or '').strip().lower())


def require_plan(plan_id: Any) -> Dict[str, Any]:
    plan = get_plan(plan_id)
    if not plan:
        raise SubscriptionError(
            f"Unknown plan '{plan_id}'. Valid plans: {', '.join(PLANS_BY_ID)}.",
            404, 'unknown_plan')
    return plan


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
    method = ' '.join(str(value or 'UPI').split())
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


_PROMO_SEED = [
    {'code': 'IMPACT2026', 'percent_off': 25, 'max_redemptions': 100,
     'valid_from': '2026-01-01T00:00:00+00:00', 'valid_until': '2026-12-31T23:59:59+00:00',
     'applicable_plans': ['pro', 'enterprise'], 'description': 'Impact 2026 launch promo'},
    {'code': 'NGO10', 'percent_off': 10, 'max_redemptions': 500,
     'valid_from': '2026-01-01T00:00:00+00:00', 'valid_until': None,
     'applicable_plans': None, 'description': 'NGO partner discount'},
    {'code': 'CSR2026', 'percent_off': 20, 'max_redemptions': 300,
     'valid_from': '2026-01-01T00:00:00+00:00', 'valid_until': '2026-12-31T23:59:59+00:00',
     'applicable_plans': ['pro', 'enterprise', 'api'], 'description': 'CSR director programme discount'},
    {'code': 'PARTNER20', 'percent_off': 20, 'max_redemptions': 500,
     'valid_from': '2026-01-01T00:00:00+00:00', 'valid_until': None,
     'applicable_plans': ['pro', 'enterprise', 'api'], 'description': 'Partner referral discount'},
    {'code': 'ENTERPRISE15', 'percent_off': 15, 'max_redemptions': 200,
     'valid_from': '2026-01-01T00:00:00+00:00', 'valid_until': None,
     'applicable_plans': ['enterprise', 'api'], 'description': 'Enterprise volume discount'},
]


def _seed_promos() -> int:
    inserted = 0
    for seed in _PROMO_SEED:
        _, created = PromoCode.objects.get_or_create(
            code=seed['code'],
            defaults={
                'percent_off': seed['percent_off'],
                'max_redemptions': seed['max_redemptions'],
                'times_redeemed': 0,
                'valid_from': seed['valid_from'],
                'valid_until': seed['valid_until'],
                'applicable_plans': json.dumps(seed['applicable_plans']) if seed['applicable_plans'] else None,
                'description': seed['description'],
                'active': True,
            }
        )
        if created:
            inserted += 1
    return inserted


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
    if allowed and plan_id not in allowed:
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


# ── Subscription ORM helpers ─────────────────────────────────────────────────
def _sub_to_dict(s: Subscription) -> Dict[str, Any]:
    return {
        'subscription_id': s.subscription_id,
        'tenant_id': s.tenant_id,
        'plan_id': s.plan_id,
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


def empty_subscription(tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, Any]:
    starter = PLANS_BY_ID['starter']
    ts = _now()
    return {
        'subscription_id': f'SUB_FREE_{tenant_id}'.upper()[:48],
        'tenant_id': tenant_id,
        'plan_id': 'starter',
        'plan_name': starter['name'],
        'tier': 'starter',
        'status': _STATUS_ACTIVE,
        'billing_cycle': 'free',
        'organization_name': 'Unregistered Organisation',
        'contact_email': None,
        'activated_at': ts, 'current_period_start': ts, 'current_period_end': None,
        'cancel_at_period_end': 0, 'canceled_at': None, 'cancel_reason': None,
        'promo_code': None, 'promo_percent': 0,
        'base_amount_paise': 0, 'discount_paise': 0, 'taxable_paise': 0,
        'cgst_paise': 0, 'sgst_paise': 0, 'igst_paise': 0, 'total_paise': 0,
        'currency': CURRENCY, 'payment_method': None, 'transaction_id': None,
        'gstin': None, 'place_of_supply': SUPPLIER_STATE_CODE, 'supply_type': 'INTRA_STATE',
        'seats': starter['limits']['seats'] or 1,
        'daily_match_quota': starter['limits']['daily_matches'],
        'api_key_hash': None, 'api_key_prefix': None, 'api_key_last4': None,
        'request_id': None, 'created_at': ts, 'updated_at': ts,
    }


def _refresh_status(row: Dict[str, Any]) -> Dict[str, Any]:
    """Auto-expire a paid subscription whose billing period has lapsed."""
    if row.get('plan_id') == 'starter' or not row.get('current_period_end'):
        return row
    if row.get('status') == _STATUS_EXPIRED:
        return row
    end = _parse_iso(row.get('current_period_end'))
    if not end or datetime.now(timezone.utc) < end:
        return row
    # Mark expired in DB
    try:
        Subscription.objects.filter(tenant_id=row['tenant_id']).update(
            status=_STATUS_EXPIRED, updated_at=_now()
        )
        SubscriptionEvent.objects.create(
            subscription_id=row['subscription_id'],
            tenant_id=row['tenant_id'],
            event_type='SUBSCRIPTION_EXPIRED',
            from_plan=row.get('plan_id'), to_plan='starter',
            amount_paise=0,
            notes=f"Billing period ended on {row.get('current_period_end')}.",
            actor='System', created_at=_now(),
        )
    except Exception:
        pass
    expired = dict(row)
    expired['status'] = _STATUS_EXPIRED
    expired['plan_id'] = 'starter'
    return expired


def _load(tenant_id: str) -> Dict[str, Any]:
    try:
        s = Subscription.objects.get(tenant_id=tenant_id)
        row = _sub_to_dict(s)
        return _refresh_status(row)
    except Subscription.DoesNotExist:
        return empty_subscription(tenant_id)


def _entitlement(row: Dict[str, Any]) -> Dict[str, Any]:
    if row.get('status') in (_STATUS_EXPIRED, _STATUS_CANCELED):
        return PLANS_BY_ID['starter']
    return get_plan(row.get('plan_id')) or PLANS_BY_ID['starter']


def effective_plan_id(row: Dict[str, Any]) -> str:
    return _entitlement(row)['id']


def serialize(row: Dict[str, Any]) -> Dict[str, Any]:
    plan = get_plan(row.get('plan_id')) or PLANS_BY_ID['starter']
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


# ── Usage metering (simple DB table via Django ORM) ──────────────────────────
# We use a minimal usage_counters pattern.  If the model doesn't exist yet
# (table not migrated), usage checks degrade gracefully to 0.
def _get_usage(tenant_id: str, metric: str, period_date: Optional[str] = None) -> int:
    from django.utils import timezone as dtz
    today = period_date or datetime.now(timezone.utc).date().isoformat()
    try:
        from django.db import connection
        with connection.cursor() as cur:
            cur.execute(
                'SELECT used FROM usage_counters WHERE tenant_id=%s AND metric=%s AND period_date=%s',
                [tenant_id, metric, today]
            )
            row = cur.fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def _bump_usage(tenant_id: str, metric: str, amount: int = 1) -> int:
    today = datetime.now(timezone.utc).date().isoformat()
    current = _get_usage(tenant_id, metric, today)
    new_total = current + amount
    try:
        from django.db import connection
        with connection.cursor() as cur:
            if current == 0:
                cur.execute(
                    'INSERT INTO usage_counters(tenant_id, metric, period_date, used) VALUES(%s,%s,%s,%s)',
                    [tenant_id, metric, today, new_total]
                )
            else:
                cur.execute(
                    'UPDATE usage_counters SET used=%s WHERE tenant_id=%s AND metric=%s AND period_date=%s',
                    [new_total, tenant_id, metric, today]
                )
    except Exception:
        pass
    return new_total


def quota_snapshot(row: Dict[str, Any]) -> Dict[str, Any]:
    plan = get_plan(row.get('plan_id')) or PLANS_BY_ID['starter']
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


# ── Pricing helpers ────────────────────────────────────────────────────────────
def _zero_credit() -> Dict[str, Any]:
    return {'credit_paise': 0, 'credit_display': format_inr(0),
            'remaining_days': 0, 'total_days': 0, 'applies': False}


def _proration_credit(row: Dict[str, Any], now_dt: datetime) -> Dict[str, Any]:
    if not row or row.get('plan_id') in (None, 'starter'):
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
        'discount_paise': discount, 'discount_display': format_inr(discount),
        'credit_paise': credit_amount, 'credit_display': format_inr(credit_amount),
        'taxable_paise': taxable, 'taxable_display': format_inr(taxable),
        'tax': tax, 'total_paise': total, 'total_display': format_inr(total),
        'currency': CURRENCY, 'lines': lines,
    }


def _change_type(current_plan_id: str, target_plan_id: str) -> str:
    order = {p['id']: i for i, p in enumerate(PLANS_CATALOG)}
    if current_plan_id == target_plan_id:
        return 'RENEWAL'
    return 'UPGRADE' if order.get(target_plan_id, 0) > order.get(current_plan_id, 0) else 'DOWNGRADE'


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
                    status: str = 'PAID') -> Dict[str, Any]:
    issued_at = _now()
    inv = Invoice.objects.create(
        invoice_no=None,
        subscription_id=subscription_id,
        tenant_id=tenant_id,
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
    )
    invoice_no = _invoice_number(issued_at, inv.invoice_id)
    inv.invoice_no = invoice_no
    inv.save(update_fields=['invoice_no'])
    return {
        'invoice_id': inv.invoice_id, 'invoice_no': invoice_no,
        'issued_at': issued_at, 'status': status,
    }


def _list_invoices(tenant_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    qs = Invoice.objects.filter(tenant_id=tenant_id).order_by('-invoice_id')[:min(limit, 500)]
    result = []
    for inv in qs:
        d = {
            'invoice_id': inv.invoice_id, 'invoice_no': inv.invoice_no,
            'subscription_id': inv.subscription_id, 'tenant_id': inv.tenant_id,
            'issued_at': inv.issued_at, 'description': inv.description,
            'taxable_paise': int(inv.taxable_paise or 0),
            'cgst_paise': int(inv.cgst_paise or 0),
            'sgst_paise': int(inv.sgst_paise or 0),
            'igst_paise': int(inv.igst_paise or 0),
            'total_paise': int(inv.total_paise or 0),
            'currency': inv.currency, 'gstin': inv.gstin,
            'place_of_supply': inv.place_of_supply, 'status': inv.status,
            'line_items': [],
        }
        for field in ('taxable', 'cgst', 'sgst', 'igst', 'total'):
            d[f'{field}_display'] = format_inr(d.get(f'{field}_paise'))
        result.append(d)
    return result


# ── Public API ────────────────────────────────────────────────────────────────
def plans_payload() -> Dict[str, Any]:
    return {
        'status': 'success', 'currency': 'INR', 'currency_symbol': '₹',
        'gst_rate_percent': round(GST_RATE_BPS / 100, 2),
        'supplier_state_code': SUPPLIER_STATE_CODE,
        'billing_cycles': list(BILLING_CYCLES), 'payment_methods': list(PAYMENT_METHODS),
        'trial_days': TRIAL_DAYS, 'plans': PLANS_CATALOG,
        'state_codes': [{'code': c, 'name': n} for c, n in sorted(STATE_CODES.items())],
    }


def promos_payload() -> Dict[str, Any]:
    _seed_promos()
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


def current(tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, Any]:
    _seed_promos()
    tenant = normalise_tenant(tenant_id)
    row = _load(tenant)
    sub = serialize(row)
    quota = quota_snapshot(row)
    plan = get_plan(sub.get('plan_id')) or PLANS_BY_ID['starter']
    events = list(
        SubscriptionEvent.objects.filter(tenant_id=tenant).order_by('-event_id')[:5].values(
            'event_id', 'event_type', 'from_plan', 'to_plan',
            'amount_paise', 'notes', 'actor', 'created_at'
        )
    )
    return {
        'status': 'success', 'tenant_id': tenant,
        'subscription': sub, 'plan_details': plan,
        'quota': quota, 'recent_events': events,
        'has_api_key': bool(sub.get('has_api_key')),
    }


def quote(payload: Dict[str, Any], tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, Any]:
    _seed_promos()
    plan = require_plan(payload.get('plan_id'))
    cycle = normalise_cycle(payload.get('billing_cycle'))
    state_code = normalise_state(payload.get('place_of_supply'))
    promo_code = normalise_promo_code(payload.get('promo_code'))
    tenant = normalise_tenant(tenant_id)
    now_dt = datetime.now(timezone.utc)

    current_row = _load(tenant)
    current_plan_id = effective_plan_id(current_row)
    credit = (_proration_credit(current_row, now_dt)
              if current_plan_id != plan['id'] and current_plan_id != 'starter'
              else _zero_credit())
    promo = evaluate_promo(promo_code, plan['id'], base_price_paise(plan, cycle))
    bd = _breakdown(plan, cycle, promo, state_code, credit)
    quota = quota_snapshot(current_row)

    return {
        'status': 'success', 'quoted_at': now_dt.isoformat(), 'tenant_id': tenant,
        'current_plan_id': current_plan_id,
        'change_type': _change_type(current_plan_id, plan['id']),
        'requires_payment': bd['total_paise'] > 0,
        'plan': {'id': plan['id'], 'name': plan['name'], 'badge': plan['badge'],
                 'features': plan['features'], 'limits': plan['limits'],
                 'is_popular': plan['is_popular'], 'cta_text': plan['cta_text']},
        'promo': promo, 'proration': credit, 'breakdown': bd, 'current_quota': quota,
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
            'gst_rate_percent': bd['tax']['gst_rate_percent'],
            'supply_type': bd['tax']['supply_type'],
            'place_of_supply': bd['tax']['place_of_supply'],
            'place_of_supply_name': bd['tax']['place_of_supply_name'],
        },
    }


def validate_promo(payload: Dict[str, Any], tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, Any]:
    _seed_promos()
    plan = require_plan(payload.get('plan_id'))
    cycle = normalise_cycle(payload.get('billing_cycle'))
    code = normalise_promo_code(payload.get('promo_code'))
    result = evaluate_promo(code, plan['id'], base_price_paise(plan, cycle))
    return {'status': 'success', 'promo': result}


def checkout(payload: Dict[str, Any], tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, Any]:
    _seed_promos()
    tenant = normalise_tenant(tenant_id)
    plan = require_plan(payload.get('plan_id'))
    cycle = normalise_cycle(payload.get('billing_cycle'))
    org = normalise_org(payload.get('organization_name'))
    email = normalise_email(payload.get('contact_email'))
    state_code = normalise_state(payload.get('place_of_supply'))
    gstin = normalise_gstin(payload.get('gstin'))
    promo_code = normalise_promo_code(payload.get('promo_code'))
    request_id = str(payload.get('request_id') or '').strip()[:64] or None
    want_trial = bool(payload.get('start_trial')) and not plan['is_free']
    payment_method = (None if (plan['is_free'] or want_trial)
                      else normalise_payment_method(payload.get('payment_method')))
    now_dt = datetime.now(timezone.utc)

    # Idempotency check
    try:
        existing_sub = Subscription.objects.get(tenant_id=tenant)
        existing_dict = _sub_to_dict(existing_sub)
        if request_id and existing_dict.get('request_id') == request_id:
            replay_row = _load(tenant)
            prior_invoices = _list_invoices(tenant, 1)
            return {
                'status': 'success', 'idempotent_replay': True, 'change_type': 'REPLAY',
                'message': f"Replayed the existing {plan['name']} activation (request {request_id} already applied).",
                'subscription': serialize(replay_row),
                'invoice': prior_invoices[0] if prior_invoices else None,
                'quote': None, 'quota': quota_snapshot(replay_row), 'api_key': None, 'api_key_note': None,
            }
    except Subscription.DoesNotExist:
        existing_dict = None

    current_row = _load(tenant)
    from_plan = effective_plan_id(current_row)
    credit = (_proration_credit(current_row, now_dt)
              if (from_plan != plan['id'] and from_plan != 'starter') else _zero_credit())
    promo = evaluate_promo(promo_code, plan['id'], base_price_paise(plan, cycle))
    bd = _breakdown(plan, cycle, promo, state_code, credit)

    if want_trial:
        period_start_dt = now_dt
        period_end_dt = now_dt + timedelta(days=TRIAL_DAYS)
        status = _STATUS_TRIALING
        charged_paise = 0
    else:
        period_start_dt = now_dt
        period_end_dt = period_end(now_dt, cycle)
        status = _STATUS_ACTIVE
        charged_paise = bd['total_paise']

    api_key_plain = None
    api_key_hash = existing_dict.get('api_key_hash') if existing_dict else None
    api_key_prefix = existing_dict.get('api_key_prefix') if existing_dict else None
    api_key_last4 = existing_dict.get('api_key_last4') if existing_dict else None
    if plan['limits'].get('api_access') and not api_key_hash:
        api_key_plain, api_key_hash, api_key_prefix, api_key_last4 = _new_api_key(plan['id'])

    sub_id = (existing_dict.get('subscription_id') if existing_dict
              else f'SUB_{uuid.uuid4().hex[:12].upper()}')

    Subscription.objects.update_or_create(
        tenant_id=tenant,
        defaults={
            'subscription_id': sub_id,
            'plan_id': plan['id'], 'status': status, 'billing_cycle': cycle,
            'organization_name': org, 'contact_email': email,
            'activated_at': now_dt.isoformat(),
            'current_period_start': period_start_dt.isoformat(),
            'current_period_end': period_end_dt.isoformat(),
            'cancel_at_period_end': False, 'canceled_at': None, 'cancel_reason': None,
            'promo_code': promo.get('code') if promo.get('applied') else None,
            'promo_percent': int(promo.get('percent_off') or 0) if promo.get('applied') else 0,
            'base_amount_paise': bd['base_amount_paise'],
            'discount_paise': bd['discount_paise'],
            'taxable_paise': 0 if want_trial else bd['taxable_paise'],
            'cgst_paise': 0 if want_trial else bd['tax']['cgst_paise'],
            'sgst_paise': 0 if want_trial else bd['tax']['sgst_paise'],
            'igst_paise': 0 if want_trial else bd['tax']['igst_paise'],
            'total_paise': charged_paise,
            'currency': CURRENCY, 'payment_method': payment_method,
            'transaction_id': f'TXN_IB_{uuid.uuid4().hex[:12].upper()}' if charged_paise > 0 else None,
            'gstin': gstin, 'place_of_supply': bd['tax']['place_of_supply'],
            'supply_type': bd['tax']['supply_type'],
            'seats': plan['limits']['seats'] or 1,
            'daily_match_quota': plan['limits']['daily_matches'],
            'api_key_hash': api_key_hash, 'api_key_prefix': api_key_prefix,
            'api_key_last4': api_key_last4, 'request_id': request_id,
            'created_at': existing_dict.get('created_at') if existing_dict else now_dt.isoformat(),
            'updated_at': now_dt.isoformat(),
        }
    )

    invoice = None
    if charged_paise > 0:
        invoice = _create_invoice(
            tenant, sub_id,
            f"{plan['name']} — {cycle.title()} subscription",
            bd['tax'], bd['taxable_paise'], charged_paise, gstin, bd['lines']
        )

    change = _change_type(from_plan, plan['id'])
    SubscriptionEvent.objects.create(
        subscription_id=sub_id, tenant_id=tenant, event_type=change,
        from_plan=from_plan, to_plan=plan['id'], amount_paise=charged_paise,
        notes=f"{plan['name']} ({cycle.upper()}); paid {format_inr(charged_paise)}",
        actor='Subscriber', created_at=now_dt.isoformat(),
    )
    if promo.get('applied') and charged_paise > 0:
        PromoCode.objects.filter(code=promo['code']).update(
            times_redeemed=models_f_plus_1('times_redeemed')
        )

    result_row = _load(tenant)
    quota = quota_snapshot(result_row)

    msg = (f"{plan['name']} trial activated for {TRIAL_DAYS} days." if want_trial
           else f"{plan['name']} activated — {format_inr(charged_paise)} paid." if charged_paise > 0
           else f"{plan['name']} activated on the free tier.")

    return {
        'status': 'success', 'idempotent_replay': False, 'change_type': change,
        'message': msg, 'subscription': serialize(result_row), 'invoice': invoice,
        'quote': {'breakdown': bd, 'promo': promo, 'proration': credit},
        'quota': quota, 'api_key': api_key_plain,
        'api_key_note': 'Store this API key now — it is shown only once.' if api_key_plain else None,
    }


def models_f_plus_1(field: str):
    """Return an F() expression for incrementing a field by 1."""
    from django.db.models import F
    return F(field) + 1


def cancel(payload: Dict[str, Any], tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, Any]:
    tenant = normalise_tenant(tenant_id)
    immediate = bool(payload.get('immediate'))
    reason = ' '.join(str(payload.get('reason') or '').split())[:300] or None
    now_dt = datetime.now(timezone.utc)

    row = _load(tenant)
    if not row or row.get('plan_id') in (None, 'starter'):
        raise SubscriptionError('There is no paid subscription to cancel.', 409, 'no_paid_subscription')
    if row.get('status') == _STATUS_CANCELED:
        raise SubscriptionError('This subscription is already cancelled.', 409, 'already_canceled')

    if immediate:
        Subscription.objects.filter(tenant_id=tenant).update(
            status=_STATUS_CANCELED, plan_id='starter', cancel_at_period_end=False,
            canceled_at=now_dt.isoformat(), cancel_reason=reason,
            current_period_end=now_dt.isoformat(), updated_at=now_dt.isoformat(),
        )
        SubscriptionEvent.objects.create(
            subscription_id=row['subscription_id'], tenant_id=tenant,
            event_type='CANCELED_IMMEDIATE', from_plan=row.get('plan_id'), to_plan='starter',
            amount_paise=0, notes=reason or 'Cancelled immediately by subscriber.',
            actor='Subscriber', created_at=now_dt.isoformat(),
        )
        message = 'Subscription cancelled immediately. Your entitlements have reverted to the free tier.'
    else:
        Subscription.objects.filter(tenant_id=tenant).update(
            cancel_at_period_end=True, canceled_at=now_dt.isoformat(),
            cancel_reason=reason, updated_at=now_dt.isoformat(),
        )
        SubscriptionEvent.objects.create(
            subscription_id=row['subscription_id'], tenant_id=tenant,
            event_type='CANCEL_AT_PERIOD_END', from_plan=row.get('plan_id'), to_plan=row.get('plan_id'),
            amount_paise=0, notes=reason or 'Scheduled to cancel at period end.',
            actor='Subscriber', created_at=now_dt.isoformat(),
        )
        message = (f"Subscription will end on {str(row.get('current_period_end'))[:10]}. "
                   'You keep full access until then.')

    updated = serialize(_load(tenant))
    return {'status': 'success', 'message': message, 'subscription': updated}


def resume(payload: Dict[str, Any], tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, Any]:
    tenant = normalise_tenant(tenant_id)
    cycle_override = payload.get('billing_cycle')
    now_dt = datetime.now(timezone.utc)

    row = _load(tenant)
    if not row or row.get('plan_id') in (None, 'starter'):
        raise SubscriptionError('No paid subscription is available to resume.', 409, 'no_paid_subscription')

    plan = require_plan(row.get('plan_id'))
    cycle = (normalise_cycle(cycle_override) if cycle_override
             else (row.get('billing_cycle') if row.get('billing_cycle') in BILLING_CYCLES else 'monthly'))

    if row.get('cancel_at_period_end') and row.get('status') != _STATUS_CANCELED:
        Subscription.objects.filter(tenant_id=tenant).update(
            cancel_at_period_end=False, canceled_at=None, cancel_reason=None, updated_at=now_dt.isoformat(),
        )
        SubscriptionEvent.objects.create(
            subscription_id=row['subscription_id'], tenant_id=tenant,
            event_type='CANCEL_REVERSED', from_plan=row.get('plan_id'), to_plan=row.get('plan_id'),
            amount_paise=0, notes='Scheduled cancellation reversed by subscriber.',
            actor='Subscriber', created_at=now_dt.isoformat(),
        )
        updated = serialize(_load(tenant))
        message = 'Scheduled cancellation reversed. Your plan continues.'
    else:
        bd = _breakdown(plan, cycle, {'applied': False},
                        row.get('place_of_supply') or SUPPLIER_STATE_CODE, _zero_credit())
        new_end = period_end(now_dt, cycle)
        Subscription.objects.filter(tenant_id=tenant).update(
            status=_STATUS_ACTIVE, billing_cycle=cycle,
            current_period_start=now_dt.isoformat(),
            current_period_end=new_end.isoformat(),
            cancel_at_period_end=False, canceled_at=None, cancel_reason=None,
            taxable_paise=bd['taxable_paise'],
            cgst_paise=bd['tax']['cgst_paise'], sgst_paise=bd['tax']['sgst_paise'],
            igst_paise=bd['tax']['igst_paise'], total_paise=bd['total_paise'],
            transaction_id=f'TXN_IB_{uuid.uuid4().hex[:12].upper()}',
            updated_at=now_dt.isoformat(),
        )
        _create_invoice(
            tenant, row['subscription_id'],
            f"{plan['name']} — renewal ({cycle})",
            bd['tax'], bd['taxable_paise'], bd['total_paise'],
            row.get('gstin'), bd['lines']
        )
        SubscriptionEvent.objects.create(
            subscription_id=row['subscription_id'], tenant_id=tenant,
            event_type='RENEWED', from_plan=row.get('plan_id'), to_plan=plan['id'],
            amount_paise=bd['total_paise'],
            notes=f"Renewed for {cycle} period ending {new_end.date().isoformat()}.",
            actor='Subscriber', created_at=now_dt.isoformat(),
        )
        updated = serialize(_load(tenant))
        message = f"{plan['name']} renewed until {new_end.date().isoformat()}."

    return {'status': 'success', 'message': message, 'subscription': updated}


def history(tenant_id: str = DEFAULT_TENANT_ID, limit: int = 50) -> Dict[str, Any]:
    tenant = normalise_tenant(tenant_id)
    events = list(
        SubscriptionEvent.objects.filter(tenant_id=tenant).order_by('-event_id')
        [:min(limit, 500)].values(
            'event_id', 'event_type', 'from_plan', 'to_plan',
            'amount_paise', 'notes', 'actor', 'created_at',
        )
    )
    return {'status': 'success', 'tenant_id': tenant, 'count': len(events), 'events': events}


def invoices_payload(tenant_id: str = DEFAULT_TENANT_ID, limit: int = 50) -> Dict[str, Any]:
    tenant = normalise_tenant(tenant_id)
    docs = _list_invoices(tenant, limit)
    return {'status': 'success', 'tenant_id': tenant, 'count': len(docs), 'invoices': docs}


def usage_payload(tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, Any]:
    tenant = normalise_tenant(tenant_id)
    row = _load(tenant)
    quota = quota_snapshot(row)
    return {'status': 'success', 'tenant_id': tenant, 'quota': quota}


def rotate_api_key(tenant_id: str = DEFAULT_TENANT_ID) -> Dict[str, Any]:
    tenant = normalise_tenant(tenant_id)
    row = _load(tenant)
    plan = _entitlement(row)
    if not plan['limits'].get('api_access'):
        raise SubscriptionError(
            f"API access is not included in the {plan['name']} plan. "
            'Upgrade to Enterprise or the Institutional Data Feed.', 403, 'api_access_not_included')
    plain, digest, prefix, last4 = _new_api_key(plan['id'])
    now_dt = datetime.now(timezone.utc)
    Subscription.objects.filter(tenant_id=tenant).update(
        api_key_hash=digest, api_key_prefix=prefix,
        api_key_last4=last4, updated_at=now_dt.isoformat(),
    )
    SubscriptionEvent.objects.create(
        subscription_id=row.get('subscription_id'), tenant_id=tenant,
        event_type='API_KEY_ROTATED', from_plan=plan['id'], to_plan=plan['id'],
        amount_paise=0,
        notes=f"Previous key {row.get('api_key_prefix') or 'none'} revoked.",
        actor='Subscriber', created_at=now_dt.isoformat(),
    )
    quota = quota_snapshot(row)
    return {
        'status': 'success', 'api_key': plain,
        'api_key_prefix': prefix, 'api_key_last4': last4,
        'message': 'A new API key was issued. The previous key is now invalid.',
        'quota': quota,
    }
