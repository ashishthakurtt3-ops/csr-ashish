from django.db import models


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
    tenant_id = models.CharField(max_length=64, unique=True)
    plan_id = models.CharField(max_length=40, blank=True, null=True)
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

    class Meta:
        db_table = 'subscriptions'

    def __str__(self):
        return f"{self.organization_name or self.tenant_id} [{self.plan_id}]"


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
    subscription_id = models.CharField(max_length=48, blank=True, null=True)
    tenant_id = models.CharField(max_length=64, blank=True, null=True)
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
