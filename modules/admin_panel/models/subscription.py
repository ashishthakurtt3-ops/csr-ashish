from django.db import models
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP


class Plan(models.Model):
    """Database-driven subscription plan model."""
    code = models.CharField(max_length=40, primary_key=True)  # starter, pro, enterprise, foundation
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    badge = models.CharField(max_length=60, blank=True, null=True)
    cta_text = models.CharField(max_length=60, default='Select Plan')
    billing_note = models.CharField(max_length=120, blank=True, null=True)

    monthly_price_paise = models.BigIntegerField(default=0)
    yearly_price_paise = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=8, default='INR')

    is_active = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)
    is_contact_sales = models.BooleanField(default=False)

    display_order = models.IntegerField(default=0)
    trial_days = models.IntegerField(default=0)

    allow_upgrade = models.BooleanField(default=True)
    allow_downgrade = models.BooleanField(default=True)
    allow_cancel = models.BooleanField(default=True)
    auto_renew_default = models.BooleanField(default=True)

    features = models.JSONField(default=list, blank=True)
    highlight_features = models.JSONField(default=list, blank=True)
    limits = models.JSONField(default=dict, blank=True)

    # Extended Admin Plan Configuration Attributes
    is_recommended = models.BooleanField(default=False)
    discount_percent = models.IntegerField(default=0)
    savings_text = models.CharField(max_length=120, blank=True, null=True)
    renewal_price_paise = models.BigIntegerField(null=True, blank=True)
    wallet_deduction_paise = models.BigIntegerField(null=True, blank=True)
    card_description = models.TextField(blank=True, null=True)
    additional_info = models.TextField(blank=True, null=True)
    button_text = models.CharField(max_length=60, default='Change Plan', blank=True, null=True)
    button_visible = models.BooleanField(default=True)
    button_order = models.IntegerField(default=1)
    terms = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subscription_plans'
        ordering = ['display_order', 'monthly_price_paise']

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def price_monthly(self) -> float:
        return round(self.monthly_price_paise / 100.0, 2)

    @property
    def price_yearly(self) -> float:
        return round(self.yearly_price_paise / 100.0, 2)

    @property
    def is_free(self) -> bool:
        return self.monthly_price_paise == 0

    @property
    def savings_yearly_paise(self) -> int:
        full_year = self.monthly_price_paise * 12
        return max(0, full_year - self.yearly_price_paise)

    @property
    def price_renewal(self) -> float:
        if self.renewal_price_paise is not None:
            return round(self.renewal_price_paise / 100.0, 2)
        return self.price_monthly

    @property
    def price_wallet_deduction(self) -> float:
        if self.wallet_deduction_paise is not None:
            return round(self.wallet_deduction_paise / 100.0, 2)
        return self.price_monthly

    @property
    def savings_percent(self) -> float:
        full_year = self.monthly_price_paise * 12
        if full_year > 0:
            return round((self.savings_yearly_paise / full_year) * 100, 1)
        return 0.0

    def get_limits_and_entitlements(self) -> dict:
        """Consolidated dictionary of limits and entitlements from both JSON and related PlanEntitlement records."""
        result = dict(self.limits or {})
        try:
            for ent in self.entitlements.all():
                result[ent.feature_key] = ent.resolved_value
        except Exception:
            pass
        return result


class PlanEntitlement(models.Model):
    """Structured plan entitlement (boolean, numeric limit, unlimited, or text)."""
    TYPE_BOOLEAN = 'BOOLEAN'
    TYPE_NUMERIC = 'NUMERIC'
    TYPE_UNLIMITED = 'UNLIMITED'
    TYPE_TEXT = 'TEXT'

    TYPE_CHOICES = (
        (TYPE_BOOLEAN, 'Boolean (Yes/No)'),
        (TYPE_NUMERIC, 'Numeric Limit'),
        (TYPE_UNLIMITED, 'Unlimited'),
        (TYPE_TEXT, 'Text Value'),
    )

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='entitlements')
    feature_key = models.CharField(max_length=64)
    display_name = models.CharField(max_length=120)
    feature_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_BOOLEAN)
    boolean_value = models.BooleanField(default=False)
    numeric_value = models.IntegerField(null=True, blank=True)
    text_value = models.TextField(null=True, blank=True)
    is_unlimited = models.BooleanField(default=False)

    class Meta:
        db_table = 'subscription_plan_entitlements'
        unique_together = ('plan', 'feature_key')

    def __str__(self):
        return f"{self.plan.code} : {self.feature_key} = {self.resolved_value}"

    @property
    def resolved_value(self):
        if self.feature_type == self.TYPE_UNLIMITED or self.is_unlimited:
            return None
        if self.feature_type == self.TYPE_BOOLEAN:
            return self.boolean_value
        if self.feature_type == self.TYPE_NUMERIC:
            return self.numeric_value
        return self.text_value


class Wallet(models.Model):
    """Prototype in-app wallet for subscription and billing operations."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance_paise = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=8, default='INR')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wallets'

    def __str__(self):
        return f"Wallet({self.user.username}): ₹{self.balance_rupees:.2f}"

    @property
    def balance_rupees(self) -> float:
        return round(self.balance_paise / 100.0, 2)

    @property
    def balance_inr(self) -> float:
        return self.balance_rupees


class WalletTransaction(models.Model):
    """Immutable ledger of all wallet credits and debits."""
    TYPE_TOPUP = 'WALLET_TOPUP'
    TYPE_SUBSCRIPTION = 'SUBSCRIPTION_PAYMENT'
    TYPE_RENEWAL = 'SUBSCRIPTION_RENEWAL'
    TYPE_UPGRADE = 'UPGRADE_PAYMENT'
    TYPE_REFUND = 'REFUND'
    TYPE_ADMIN_CREDIT = 'ADMIN_CREDIT'
    TYPE_ADMIN_DEBIT = 'ADMIN_DEBIT'
    TYPE_PROMO_CREDIT = 'PROMOTIONAL_CREDIT'
    TYPE_DOWNGRADE = 'DOWNGRADE_ADJUSTMENT'

    TYPE_CHOICES = (
        (TYPE_TOPUP, 'Wallet Top-Up'),
        (TYPE_SUBSCRIPTION, 'Subscription Payment'),
        (TYPE_RENEWAL, 'Subscription Renewal'),
        (TYPE_UPGRADE, 'Plan Upgrade'),
        (TYPE_REFUND, 'Refund to Wallet'),
        (TYPE_ADMIN_CREDIT, 'Admin Credit'),
        (TYPE_ADMIN_DEBIT, 'Admin Debit'),
        (TYPE_PROMO_CREDIT, 'Promotional Credit'),
        (TYPE_DOWNGRADE, 'Plan Change Adjustment'),
    )

    DIRECTION_CREDIT = 'CREDIT'
    DIRECTION_DEBIT = 'DEBIT'
    DIRECTION_CHOICES = (
        (DIRECTION_CREDIT, 'Credit (+)'),
        (DIRECTION_DEBIT, 'Debit (-)'),
    )

    transaction_id = models.CharField(max_length=64, primary_key=True)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet_transactions')
    transaction_type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    credit_or_debit = models.CharField(max_length=8, choices=DIRECTION_CHOICES)
    amount_paise = models.BigIntegerField(default=0)
    balance_before_paise = models.BigIntegerField(default=0)
    balance_after_paise = models.BigIntegerField(default=0)
    reference_type = models.CharField(max_length=40, blank=True, null=True)
    reference_id = models.CharField(max_length=64, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=24, default='SUCCESS')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wallet_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} [{self.credit_or_debit}] ₹{self.amount_rupees:.2f}"

    @property
    def amount_rupees(self) -> float:
        return round(self.amount_paise / 100.0, 2)


class Payment(models.Model):
    """Database model for all prototype payments."""
    STATUS_PENDING = 'PENDING'
    STATUS_SUCCESS = 'SUCCESS'
    STATUS_FAILED = 'FAILED'
    STATUS_CANCELLED = 'CANCELLED'
    STATUS_REFUNDED = 'REFUNDED'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCESS, 'Success'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_REFUNDED, 'Refunded'),
    )

    TYPE_TOPUP = 'TOPUP'
    TYPE_SUBSCRIPTION = 'SUBSCRIPTION'
    TYPE_UPGRADE = 'UPGRADE'
    TYPE_RENEWAL = 'RENEWAL'
    TYPE_DOWNGRADE = 'DOWNGRADE_ADJUSTMENT'
    TYPE_REFUND = 'REFUND'

    TYPE_CHOICES = (
        (TYPE_TOPUP, 'Wallet Top-up'),
        (TYPE_SUBSCRIPTION, 'New Subscription'),
        (TYPE_UPGRADE, 'Subscription Upgrade'),
        (TYPE_RENEWAL, 'Subscription Renewal'),
        (TYPE_DOWNGRADE, 'Plan Change Adjustment'),
        (TYPE_REFUND, 'Refund'),
    )

    payment_id = models.CharField(max_length=64, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    subscription = models.ForeignKey('Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    plan_code = models.CharField(max_length=40, blank=True, null=True)
    amount_paise = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=8, default='INR')
    payment_method = models.CharField(max_length=40, default='WALLET')
    payment_status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_type = models.CharField(max_length=40, choices=TYPE_CHOICES)
    transaction_reference = models.CharField(max_length=64, blank=True, null=True)
    idempotency_key = models.CharField(max_length=128, blank=True, null=True, db_index=True)
    is_prototype = models.BooleanField(default=True)
    failure_reason = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.payment_id} ({self.payment_type}) - ₹{self.amount_rupees:.2f} [{self.payment_status}]"

    @property
    def amount_rupees(self) -> float:
        return round(self.amount_paise / 100.0, 2)

    @property
    def amount_inr(self) -> float:
        return self.amount_rupees

    @property
    def is_successful(self) -> bool:
        return self.payment_status == self.STATUS_SUCCESS

    @property
    def plan_record(self):
        """Resolves the linked Plan model instance."""
        if self.plan_code:
            p = Plan.objects.filter(code=self.plan_code).first()
            if p:
                return p
        if self.subscription and getattr(self.subscription, 'plan', None):
            return self.subscription.plan
        return None

    @property
    def plan_name_display(self) -> str:
        """Formatted human-readable plan name or purpose."""
        if self.plan_record:
            return self.plan_record.name
        if self.plan_code:
            return self.plan_code.replace('_', ' ').title()
        if self.payment_type == self.TYPE_TOPUP:
            return "Wallet Top-Up"
        return "Standard Service"

    @property
    def billing_cycle_display(self) -> str:
        """Billing frequency for subscriptions or one-time."""
        if self.subscription and self.subscription.billing_cycle:
            cycle = self.subscription.billing_cycle.lower()
            if 'year' in cycle or 'annual' in cycle:
                return "Annual (Yearly)"
            if 'month' in cycle:
                return "Monthly"
            return self.subscription.billing_cycle.title()
        if self.metadata and isinstance(self.metadata, dict) and self.metadata.get('billing_cycle'):
            return str(self.metadata['billing_cycle']).title()
        if self.payment_type == self.TYPE_TOPUP:
            return "One-Time Credit"
        return "One-Time Payment"

    @property
    def processing_duration_display(self) -> str:
        """Timing duration between creation and completion."""
        if self.created_at and self.completed_at:
            delta = self.completed_at - self.created_at
            total_seconds = delta.total_seconds()
            if total_seconds < 1:
                ms = int(total_seconds * 1000)
                return f"{max(ms, 0)} ms (Instant)"
            elif total_seconds < 60:
                return f"{total_seconds:.2f} seconds"
            else:
                mins = int(total_seconds // 60)
                secs = int(total_seconds % 60)
                return f"{mins}m {secs}s"
        return "Instant (< 1s)"

    @property
    def invoice_record(self):
        """Linked Invoice if generated."""
        return self.invoices.first()

    @property
    def wallet_transaction(self):
        """Linked WalletTransaction ledger entry."""
        return WalletTransaction.objects.filter(
            models.Q(reference_id=self.payment_id) |
            models.Q(transaction_id=self.transaction_reference)
        ).first()


class PromoCode(models.Model):
    code = models.CharField(max_length=40, primary_key=True)
    percent_off = models.IntegerField(default=0)
    max_redemptions = models.IntegerField(null=True, blank=True)
    times_redeemed = models.IntegerField(default=0)
    valid_from = models.TextField(blank=True, null=True)
    valid_until = models.TextField(blank=True, null=True)
    applicable_plans = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = 'promo_codes'

    def __str__(self):
        return f"{self.code} ({self.percent_off}% off)"


class Subscription(models.Model):
    subscription_id = models.CharField(max_length=48, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')
    tenant_id = models.CharField(max_length=64, unique=True)
    plan_id = models.CharField(max_length=40, blank=True, null=True)
    plan_record = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions', db_column='plan_fk')
    status = models.CharField(max_length=24, blank=True, null=True)
    billing_cycle = models.CharField(max_length=16, blank=True, null=True)
    organization_name = models.CharField(max_length=255, blank=True, null=True)
    contact_email = models.CharField(max_length=190, blank=True, null=True)
    activated_at = models.TextField(blank=True, null=True)
    current_period_start = models.TextField(blank=True, null=True)
    current_period_end = models.TextField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.TextField(blank=True, null=True)
    cancel_reason = models.TextField(blank=True, null=True)
    auto_renew = models.BooleanField(default=True)
    pending_downgrade_plan = models.CharField(max_length=40, blank=True, null=True)
    pending_downgrade_cycle = models.CharField(max_length=16, blank=True, null=True)
    pending_downgrade_date = models.TextField(blank=True, null=True)
    renewal_failure_count = models.IntegerField(default=0)
    last_renewal_attempt = models.TextField(blank=True, null=True)

    promo_code = models.CharField(max_length=40, blank=True, null=True)
    promo_percent = models.IntegerField(default=0)
    base_amount_paise = models.BigIntegerField(default=0)
    discount_paise = models.BigIntegerField(default=0)
    taxable_paise = models.BigIntegerField(default=0)
    cgst_paise = models.BigIntegerField(default=0)
    sgst_paise = models.BigIntegerField(default=0)
    igst_paise = models.BigIntegerField(default=0)
    total_paise = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=8, default='INR')
    payment_method = models.CharField(max_length=40, blank=True, null=True)
    transaction_id = models.CharField(max_length=64, blank=True, null=True)
    gstin = models.CharField(max_length=20, blank=True, null=True)
    place_of_supply = models.CharField(max_length=8, blank=True, null=True)
    supply_type = models.CharField(max_length=20, blank=True, null=True)
    seats = models.IntegerField(default=1)
    daily_match_quota = models.IntegerField(null=True, blank=True)
    api_key_hash = models.CharField(max_length=128, blank=True, null=True)
    api_key_prefix = models.CharField(max_length=24, blank=True, null=True)
    api_key_last4 = models.CharField(max_length=8, blank=True, null=True)
    request_id = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.TextField(blank=True, null=True)
    updated_at = models.TextField(blank=True, null=True)

    PLAN_FREE = 'starter'
    PLAN_PRO = 'pro'
    PLAN_ENTERPRISE = 'enterprise'
    PLAN_FOUNDATION = 'foundation'

    TIER_CHOICES = (
        (PLAN_FREE, 'Community Starter'),
        (PLAN_PRO, 'Impact Pro'),
        (PLAN_ENTERPRISE, 'Corporate Enterprise'),
        (PLAN_FOUNDATION, 'Foundation Master'),
    )

    class Meta:
        db_table = 'subscriptions'

    def __str__(self):
        return f"{self.organization_name or self.tenant_id} [{self.plan_id}]"

    @property
    def pending_change_plan(self):
        return self.pending_downgrade_plan

    @property
    def pending_change_cycle(self):
        return self.pending_downgrade_cycle

    @property
    def pending_change_date(self):
        return self.pending_downgrade_date

    @property
    def id(self):
        return self.subscription_id

    @property
    def plan(self):
        if self.plan_record:
            return self.plan_record
        if self.plan_id:
            try:
                return Plan.objects.filter(code=self.plan_tier).first() or Plan.objects.filter(code=self.plan_id).first()
            except Exception:
                return None
        return None

    @property
    def plan_tier(self) -> str:
        """Normalized canonical tier code: 'starter', 'pro', 'enterprise', 'foundation'."""
        pid = str(self.plan_id or '').strip().lower()
        if pid in ('free', 'starter'):
            return 'starter'
        if pid in ('pro',):
            return 'pro'
        if pid in ('enterprise', 'ultra'):
            return 'enterprise'
        if pid in ('foundation', 'api'):
            return 'foundation'
        return 'starter'

    @property
    def is_free(self) -> bool:
        return self.plan_tier == 'starter'

    @property
    def is_pro(self) -> bool:
        return self.plan_tier == 'pro'

    @property
    def is_enterprise(self) -> bool:
        return self.plan_tier in ('enterprise', 'foundation')

    @property
    def is_ultra(self) -> bool:
        return self.plan_tier in ('enterprise', 'foundation')

    def has_entitlement(self, key: str, default: bool = False) -> bool:
        """Dynamic database-driven entitlement check."""
        if self.plan:
            limits = self.plan.get_limits_and_entitlements()
            if key in limits:
                return bool(limits[key])
        return default

    def get_limit(self, key: str, default=None):
        """Dynamic database-driven limit lookup."""
        if self.plan:
            limits = self.plan.get_limits_and_entitlements()
            if key in limits:
                return limits[key]
        return default

    @property
    def can_view_contacts(self) -> bool:
        """True for Pro, Enterprise, and Foundation subscribers."""
        if self.plan:
            return bool(self.has_entitlement('view_contacts', self.plan_tier != 'starter'))
        return self.plan_tier != 'starter'

    @property
    def can_reprobe_crawler(self) -> bool:
        """True for subscribers who can trigger live re-crawling."""
        if self.plan:
            return bool(self.has_entitlement('live_reprobe', self.plan_tier != 'starter'))
        return self.plan_tier != 'starter'

    @property
    def can_access_api(self) -> bool:
        """True for Enterprise and Foundation institutional API consumers."""
        if self.plan:
            return bool(self.has_entitlement('api_access', self.plan_tier in ('enterprise', 'foundation')))
        return self.plan_tier in ('enterprise', 'foundation')

    @property
    def can_access_audit_packs(self) -> bool:
        """Statutory Section 135 & Schedule VII audit evidence packs."""
        if self.plan:
            return bool(self.has_entitlement('audit_packs', self.plan_tier in ('enterprise', 'foundation')))
        return self.plan_tier in ('enterprise', 'foundation')

    @property
    def max_export_rows(self) -> int | None:
        """Export limits: 25 rows for Starter, 1000 for Pro, unlimited for Enterprise/Foundation."""
        if self.plan:
            return self.get_limit('export_rows_per_month', 25 if self.plan_tier == 'starter' else (1000 if self.plan_tier == 'pro' else None))
        if self.plan_tier == 'starter':
            return 25
        if self.plan_tier == 'pro':
            return 1000
        return None  # Unlimited

    @property
    def max_allowed_seats(self) -> int:
        if self.plan:
            return int(self.get_limit('seats', 1 if self.plan_tier == 'starter' else (3 if self.plan_tier == 'pro' else 15)))
        if self.plan_tier == 'starter':
            return 1
        if self.plan_tier == 'pro':
            return 3
        return 15


class SubscriptionEvent(models.Model):
    event_id = models.AutoField(primary_key=True)
    subscription_id = models.CharField(max_length=48, blank=True, null=True)
    tenant_id = models.CharField(max_length=64, blank=True, null=True)
    event_type = models.CharField(max_length=40, blank=True, null=True)
    from_plan = models.CharField(max_length=40, blank=True, null=True)
    to_plan = models.CharField(max_length=40, blank=True, null=True)
    amount_paise = models.BigIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    actor = models.CharField(max_length=80, blank=True, null=True)
    created_at = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'subscription_events'
        ordering = ['-event_id']

    def __str__(self):
        return f"Event {self.event_type} for {self.tenant_id}"


class Invoice(models.Model):
    invoice_id = models.AutoField(primary_key=True)
    invoice_no = models.CharField(max_length=40, blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    subscription_id = models.CharField(max_length=48, blank=True, null=True)
    plan_id = models.CharField(max_length=40, blank=True, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    tenant_id = models.CharField(max_length=64, blank=True, null=True)
    billing_cycle = models.CharField(max_length=16, blank=True, null=True)
    period_start = models.TextField(blank=True, null=True)
    period_end = models.TextField(blank=True, null=True)
    issued_at = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    taxable_paise = models.BigIntegerField(default=0)
    cgst_paise = models.BigIntegerField(default=0)
    sgst_paise = models.BigIntegerField(default=0)
    igst_paise = models.BigIntegerField(default=0)
    total_paise = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=8, default='INR')
    gstin = models.CharField(max_length=20, blank=True, null=True)
    place_of_supply = models.CharField(max_length=8, blank=True, null=True)
    status = models.CharField(max_length=24, default='PAID')
    line_items = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'invoices'
        ordering = ['-invoice_id']

    def __str__(self):
        return f"Invoice {self.invoice_no} ({self.status})"

    @property
    def total_rupees(self) -> float:
        return round(self.total_paise / 100.0, 2)

    @property
    def taxable_rupees(self) -> float:
        return round(self.taxable_paise / 100.0, 2)

    @property
    def cgst_rupees(self) -> float:
        return round(self.cgst_paise / 100.0, 2)

    @property
    def sgst_rupees(self) -> float:
        return round(self.sgst_paise / 100.0, 2)

    @property
    def igst_rupees(self) -> float:
        return round(self.igst_paise / 100.0, 2)


class UsageCounter(models.Model):
    tenant_id = models.CharField(max_length=64)
    metric = models.CharField(max_length=40)
    period_date = models.CharField(max_length=10)
    used = models.IntegerField(default=0)

    class Meta:
        db_table = 'usage_counters'
        unique_together = ('tenant_id', 'metric', 'period_date')

    def __str__(self):
        return f"{self.tenant_id}:{self.metric}:{self.period_date} = {self.used}"
