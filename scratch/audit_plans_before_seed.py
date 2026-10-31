"""
Pre-seed dependency audit: inspect every foreign-key relationship,
active/historical subscriptions, payments, wallet transactions,
and entitlements per plan before making any changes.
"""
import os, sys, json, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import (
    Plan, PlanEntitlement, Subscription, Payment,
    WalletTransaction, SubscriptionEvent, Invoice, UsageCounter
)

print("=" * 70)
print("PRE-SEED DEPENDENCY AUDIT")
print("=" * 70)

# 1. All plans with metadata
print("\n--- EXISTING PLANS ---")
for p in Plan.objects.all().order_by('display_order'):
    print(f"  code={p.code!r}, name={p.name!r}, active={p.is_active}, visible={p.is_visible}, "
          f"monthly={p.monthly_price_paise}, yearly={p.yearly_price_paise}, order={p.display_order}")

# 2. Subscriptions per plan
print("\n--- SUBSCRIPTIONS PER PLAN ---")
for p in Plan.objects.all():
    # By plan_id text field
    subs_by_id = Subscription.objects.filter(plan_id=p.code)
    # By plan_record FK
    subs_by_fk = Subscription.objects.filter(plan_record=p)
    combined = Subscription.objects.filter(
        __import__('django').db.models.Q(plan_id=p.code) |
        __import__('django').db.models.Q(plan_record=p)
    ).distinct()
    print(f"  {p.code}: by plan_id={subs_by_id.count()}, by plan_record FK={subs_by_fk.count()}, combined distinct={combined.count()}")
    for s in combined:
        print(f"    sub={s.subscription_id}, user={s.user}, tenant={s.tenant_id}, "
              f"status={s.status}, plan_id={s.plan_id}, plan_fk={s.plan_record_id}")

# 3. Payments referencing each plan
print("\n--- PAYMENTS PER PLAN ---")
for p in Plan.objects.all():
    payments = Payment.objects.filter(plan_code=p.code)
    print(f"  {p.code}: {payments.count()} payments")
    for pay in payments[:5]:
        print(f"    {pay.payment_id} type={pay.payment_type} status={pay.payment_status} "
              f"amount={pay.amount_paise}")

# Check payments referencing aliases
for alias in ['free', 'ultra', 'starter']:
    payments = Payment.objects.filter(plan_code=alias)
    if payments.exists():
        print(f"  ALIAS '{alias}': {payments.count()} payments")

# 4. Subscription events
print("\n--- SUBSCRIPTION EVENTS PER PLAN ---")
for p in Plan.objects.all():
    events_from = SubscriptionEvent.objects.filter(from_plan=p.code)
    events_to = SubscriptionEvent.objects.filter(to_plan=p.code)
    print(f"  {p.code}: from_plan={events_from.count()}, to_plan={events_to.count()}")

# 5. Invoices per plan
print("\n--- INVOICES PER PLAN ---")
for p in Plan.objects.all():
    invs = Invoice.objects.filter(plan_id=p.code)
    print(f"  {p.code}: {invs.count()} invoices")

# 6. Entitlements per plan
print("\n--- ENTITLEMENTS PER PLAN ---")
for p in Plan.objects.all():
    ents = PlanEntitlement.objects.filter(plan=p)
    print(f"  {p.code}: {ents.count()} entitlements")
    for e in ents:
        print(f"    {e.feature_key}: type={e.feature_type}, bool={e.boolean_value}, "
              f"num={e.numeric_value}, text={e.text_value!r}, unlimited={e.is_unlimited}")

# 7. Usage counters
print("\n--- USAGE COUNTERS ---")
counters = UsageCounter.objects.all()
print(f"  Total usage counter records: {counters.count()}")
for c in counters[:10]:
    print(f"    tenant={c.tenant_id}, metric={c.metric}, period={c.period_date}, used={c.used}")

# 8. Check if 'free' or 'ultra' plan codes already exist
print("\n--- PLAN CODE AVAILABILITY ---")
for code in ['free', 'ultra']:
    exists = Plan.objects.filter(code=code).exists()
    print(f"  code={code!r}: {'EXISTS' if exists else 'AVAILABLE'}")

print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)

