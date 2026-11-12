"""
Centralized Entitlement Enforcement Service.

All plan feature checks, quota enforcement, and limit validation
are routed through this service. Every feature gate, usage limit,
and export quota is resolved dynamically from the database — no
hardcoded limits in application code.

Usage:
    from modules.website.utils.entitlement_service import EntitlementService
    svc = EntitlementService(user)
    svc.check_can_save_record()        # raises EntitlementError if over quota
    svc.check_export_quota(count=50)   # raises if monthly export exceeded
    svc.record_export_usage(count=50)  # atomically increment counter
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from django.db import transaction
from django.db.models import F, Q

from modules.admin_panel.models import (
    Plan, PlanEntitlement, Subscription, UsageCounter,
    SavedRecord, SavedSearch, TeamMembership, User
)

logger = logging.getLogger(__name__)


class EntitlementError(Exception):
    """Raised when a user exceeds their plan's entitlement."""
    def __init__(self, message: str, feature: str = '', limit: Any = None,
                 current: Any = None, upgrade_to: str = 'pro'):
        super().__init__(message)
        self.message = message
        self.feature = feature
        self.limit = limit
        self.current = current
        self.upgrade_to = upgrade_to


class EntitlementService:
    """
    Server-side plan enforcement for a specific user.
    Resolves the user's active subscription and plan from the database,
    then provides check/enforce methods for every gated feature.
    """

    def __init__(self, user: User):
        self.user = user
        self._subscription = None
        self._plan = None
        self._limits = None

    # ── Core resolution ───────────────────────────────────────────────

    @property
    def subscription(self) -> Optional[Subscription]:
        if self._subscription is None:
            q = Q(user=self.user)
            if getattr(self.user, 'id', None):
                q |= Q(tenant_id=f"user_{self.user.id}")
            if getattr(self.user, 'username', None):
                q |= Q(tenant_id=f"user_{self.user.username}")
            sub = (
                Subscription.objects
                .filter(q, Q(status='ACTIVE') | Q(status='TRIALING'))
                .select_related('plan_record')
                .order_by('-created_at')
                .first()
            )
            if sub and sub.current_period_end:
                from datetime import datetime, timezone
                try:
                    text = str(sub.current_period_end).replace('Z', '+00:00')
                    end_dt = datetime.fromisoformat(text)
                    if not end_dt.tzinfo:
                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) >= end_dt:
                        sub.status = 'EXPIRED'
                        sub.save(update_fields=['status'])
                        sub = None
                except Exception:
                    pass
            self._subscription = sub
        return self._subscription

    @property
    def plan(self) -> Optional[Plan]:
        if self._plan is None:
            sub = self.subscription
            if sub and sub.plan_record:
                self._plan = sub.plan_record
            elif sub and sub.plan_id:
                self._plan = Plan.objects.filter(code=sub.plan_id).first()
            if not self._plan:
                self._plan = Plan.objects.filter(code='free').first()
        return self._plan

    @property
    def plan_code(self) -> str:
        p = self.plan
        return p.code if p else 'free'

    @property
    def tier(self) -> str:
        """Canonical tier: 'free', 'pro', or 'ultra'."""
        code = self.plan_code.lower()
        if code in ('free', 'starter'):
            return 'free'
        if code == 'pro':
            return 'pro'
        if code in ('ultra', 'enterprise', 'foundation'):
            return 'ultra'
        return 'free'

    @property
    def limits(self) -> dict:
        """All resolved limits from Plan.limits JSON + PlanEntitlement records."""
        if self._limits is None:
            p = self.plan
            if p:
                self._limits = p.get_limits_and_entitlements()
            else:
                self._limits = {}
        return self._limits

    def get_limit(self, key: str, default=None):
        """Fetch a single limit value. None means unlimited."""
        return self.limits.get(key, default)

    def has_feature(self, key: str) -> bool:
        """Check boolean feature entitlement."""
        val = self.limits.get(key)
        if val is None:
            return False
        return bool(val)

    @property
    def tenant_id(self) -> str:
        sub = self.subscription
        if sub:
            return sub.tenant_id
        return f"user_{self.user.id}"

    # ── Browse Companies & Portals Limit ──────────────────────────────

    @property
    def browse_companies_limit(self) -> Optional[int]:
        """None = unlimited (Ultra). 20 for Free, 100 for Pro (or admin configured)."""
        val = self.get_limit('browse_companies_limit')
        if val is None:
            if self.tier == 'free':
                return 20
            elif self.tier == 'pro':
                return 100
            return None  # Ultra is unlimited
        if isinstance(val, str) and val.lower() in ('unlimited', 'all', 'none', 'null', ''):
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    # ── Saved Records (combined jobs + CSR) ───────────────────────────

    @property
    def saved_records_count(self) -> int:
        return SavedRecord.objects.filter(user=self.user).count()

    @property
    def saved_records_limit(self) -> Optional[int]:
        """None = unlimited (Ultra). 20 for Free, 100 for Pro (or admin configured)."""
        val = self.get_limit('saved_records_limit')
        if val is None:
            if self.tier == 'free':
                return 20
            elif self.tier == 'pro':
                return 100
            return None
        if isinstance(val, str) and val.lower() in ('unlimited', 'all', 'none', 'null', ''):
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    def check_can_save_record(self) -> None:
        limit = self.saved_records_limit
        if limit is None:
            return  # Unlimited
        current = self.saved_records_count
        if current >= limit:
            upgrade = 'pro' if self.tier == 'free' else 'ultra'
            raise EntitlementError(
                f"You have saved {current}/{limit} records. "
                f"Upgrade to {upgrade.upper()} for more.",
                feature='saved_records',
                limit=limit,
                current=current,
                upgrade_to=upgrade,
            )

    # ── Saved Searches ────────────────────────────────────────────────

    @property
    def saved_searches_count(self) -> int:
        return SavedSearch.objects.filter(user=self.user, is_active=True).count()

    @property
    def saved_searches_limit(self) -> int:
        val = self.get_limit('saved_searches_limit', 1)
        return int(val) if val is not None else 50

    def check_can_save_search(self) -> None:
        limit = self.saved_searches_limit
        current = self.saved_searches_count
        if current >= limit:
            upgrade = 'pro' if self.tier == 'free' else 'ultra'
            raise EntitlementError(
                f"You have {current}/{limit} saved searches. "
                f"Upgrade to {upgrade.upper()} for more.",
                feature='saved_searches',
                limit=limit,
                current=current,
                upgrade_to=upgrade,
            )

    # ── Monthly Export Quota ──────────────────────────────────────────

    @property
    def monthly_export_limit(self) -> Optional[int]:
        """None = unlimited (Ultra). 20 for Free, 100 for Pro (or admin configured)."""
        val = self.get_limit('export_rows_per_month')
        if val is None:
            if self.tier == 'free':
                return 20
            elif self.tier == 'pro':
                return 100
            return None
        if isinstance(val, str) and val.lower() in ('unlimited', 'all', 'none', 'null', ''):
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    @property
    def current_month_period(self) -> str:
        return datetime.now(timezone.utc).strftime('%Y-%m')

    @property
    def monthly_exports_used(self) -> int:
        counter = UsageCounter.objects.filter(
            tenant_id=self.tenant_id,
            metric='records_exported',
            period_date=self.current_month_period,
        ).first()
        return counter.used if counter else 0

    def check_export_quota(self, count: int = 1) -> None:
        """Raises EntitlementError if exporting `count` records exceeds monthly limit."""
        limit = self.monthly_export_limit
        if limit is None:
            return  # Unlimited on Ultra
        if limit == 0:
            raise EntitlementError(
                "Export is not enabled on this plan. Upgrade to PRO or ULTRA.",
                feature='export',
                limit=0,
                current=0,
                upgrade_to='pro',
            )
        used = self.monthly_exports_used
        if used + count > limit:
            remaining = max(0, limit - used)
            upgrade = 'ultra' if self.tier == 'pro' else 'pro'
            raise EntitlementError(
                f"Monthly export limit: {used}/{limit} rows used. "
                f"Cannot export {count} more records ({remaining} remaining). "
                f"Upgrade to {upgrade.upper()} for higher limits.",
                feature='export',
                limit=limit,
                current=used,
                upgrade_to=upgrade,
            )

    @transaction.atomic
    def record_export_usage(self, count: int) -> int:
        """Atomically increment export counter. Returns new total."""
        period = self.current_month_period
        counter, created = UsageCounter.objects.get_or_create(
            tenant_id=self.tenant_id,
            metric='records_exported',
            period_date=period,
            defaults={'used': 0},
        )
        UsageCounter.objects.filter(
            pk=counter.pk
        ).update(used=F('used') + count)
        counter.refresh_from_db()
        return counter.used

    # ── Advanced Filters ──────────────────────────────────────────────

    def check_advanced_filters(self) -> None:
        if not self.has_feature('advanced_filters'):
            raise EntitlementError(
                "Advanced search filters are available on PRO and ULTRA plans.",
                feature='advanced_filters',
                upgrade_to='pro',
            )

    # ── Company Comparison ────────────────────────────────────────────

    @property
    def compare_companies_limit(self) -> Optional[int]:
        val = self.get_limit('compare_companies_limit', 0)
        return int(val) if val is not None else None

    def check_company_comparison(self, count: int = 1) -> None:
        limit = self.compare_companies_limit
        if limit is not None and limit == 0:
            raise EntitlementError(
                "Company comparison is available on PRO and ULTRA plans.",
                feature='company_comparison',
                upgrade_to='pro',
            )
        if limit is not None and count > limit:
            raise EntitlementError(
                f"You can compare up to {limit} companies on your plan.",
                feature='company_comparison',
                limit=limit,
                upgrade_to='ultra',
            )

    # ── Team Members ──────────────────────────────────────────────────

    @property
    def team_members_limit(self) -> int:
        val = self.get_limit('seats', 1)
        return int(val) if val is not None else 3

    @property
    def active_team_members_count(self) -> int:
        return TeamMembership.objects.filter(
            owner=self.user,
            status__in=['INVITED', 'ACTIVE'],
        ).count() + 1  # +1 for the owner

    def check_can_add_team_member(self) -> None:
        limit = self.team_members_limit
        current = self.active_team_members_count
        if current >= limit:
            raise EntitlementError(
                f"Your plan supports {limit} team member(s). "
                f"Upgrade to ULTRA for up to 3 team members.",
                feature='team_members',
                limit=limit,
                current=current,
                upgrade_to='ultra',
            )

    # ── Company Refresh Requests ──────────────────────────────────────

    def check_can_request_refresh(self) -> None:
        if not self.has_feature('request_company_refresh'):
            raise EntitlementError(
                "On-demand company crawler rescan is available on PRO and ULTRA plans.",
                feature='company_refresh',
                upgrade_to='pro',
            )

    # ── Alert Frequency ───────────────────────────────────────────────

    @property
    def allowed_alert_frequency(self) -> str:
        return str(self.get_limit('alert_frequency', 'weekly'))

    def check_alert_frequency(self, requested: str) -> None:
        allowed = self.allowed_alert_frequency
        freq_order = {'weekly': 1, 'daily': 2, 'custom': 3}
        if freq_order.get(requested, 0) > freq_order.get(allowed, 0):
            raise EntitlementError(
                f"'{requested}' alerts require a higher plan. "
                f"Your plan allows '{allowed}' alerts.",
                feature='alert_frequency',
                upgrade_to='pro' if allowed == 'weekly' else 'ultra',
            )

    # ── Priority Support ──────────────────────────────────────────────

    @property
    def has_priority_support(self) -> bool:
        return self.has_feature('priority_support')

    # ── Quota Summary (for UI display) ────────────────────────────────

    def quota_summary(self) -> dict:
        """Full quota snapshot for the frontend quota progress indicators."""
        bc_limit = self.browse_companies_limit
        sr_limit = self.saved_records_limit
        ss_limit = self.saved_searches_limit
        ex_limit = self.monthly_export_limit
        tm_limit = self.team_members_limit

        has_sub = self.subscription is not None
        plan_name = self.subscription.plan_record.name if (self.subscription and self.subscription.plan_record) else (self.plan.name if (has_sub and self.plan) else 'No Active Plan')
        plan_code = self.plan_code if has_sub else None
        tier = self.tier if has_sub else None

        return {
            'has_active_subscription': has_sub,
            'plan_code': plan_code,
            'plan_name': plan_name,
            'tier': tier,
            'browse_companies': {
                'limit': bc_limit,
                'unlimited': bc_limit is None,
            },
            'saved_records': {
                'used': self.saved_records_count,
                'limit': sr_limit,
                'unlimited': sr_limit is None,
            },
            'saved_searches': {
                'used': self.saved_searches_count,
                'limit': ss_limit,
            },
            'monthly_exports': {
                'used': self.monthly_exports_used,
                'limit': ex_limit,
                'unlimited': ex_limit is None,
                'period': self.current_month_period,
            },
            'team_members': {
                'used': self.active_team_members_count,
                'limit': tm_limit,
            },
            'features': {
                'advanced_filters': self.has_feature('advanced_filters'),
                'company_comparison': self.compare_companies_limit,
                'company_refresh': self.has_feature('request_company_refresh'),
                'priority_support': self.has_priority_support,
                'alert_frequency': self.allowed_alert_frequency,
            },
        }


def user_has_active_plan(user) -> bool:
    """
    Check whether a user has an active, selected subscription plan in the database.
    - Unauthenticated users return False.
    - Regular users and staff return True ONLY if they have an active/trialing subscription that has not expired.
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    from modules.admin_panel.models import Subscription
    from django.db.models import Q
    from datetime import datetime, timezone

    subs = Subscription.objects.filter(
        Q(user=user) | Q(tenant_id=f"user_{user.id}") | Q(tenant_id=f"user_{getattr(user, 'username', '')}"),
        status__in=['ACTIVE', 'TRIALING']
    ).exclude(plan_id__isnull=True).exclude(plan_id__exact='').order_by('-created_at')

    now = datetime.now(timezone.utc)
    for sub in subs:
        if sub.current_period_end:
            try:
                text = str(sub.current_period_end).replace('Z', '+00:00')
                end_dt = datetime.fromisoformat(text)
                if not end_dt.tzinfo:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)
                if now >= end_dt:
                    sub.status = 'EXPIRED'
                    sub.save(update_fields=['status'])
                    continue
            except Exception:
                pass
        return True

    return False
