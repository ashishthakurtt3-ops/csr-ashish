import os
import sys
import json

sys.path.insert(0, r"d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)")
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.conf import settings
settings.ALLOW_PROTOTYPE_PAYMENTS = True
settings.ALLOW_DEMO_AUTH_FALLBACK = True
from django.test import Client
from django.db import transaction
from modules.admin_panel.models import (
    User, Plan, Subscription, Wallet, WalletTransaction, Payment,
    Invoice, UsageCounter, SavedRecord, SavedSearch, TeamMembership,
    CompanyRefreshRequest, Company, Job, CSRProject
)
from modules.website.utils.subscription_service import (
    topup_wallet, checkout, cancel, resume, process_subscription_renewals
)

print("=" * 70)
print("E2E VERIFICATION: CUSTOMER LIFECYCLE, WALLET, PURCHASE & WORKFLOWS")
print("=" * 70)

client = Client()

# ── 1. Create Dedicated Test Customer ─────────────────────────────────────────
print("\n[1] Creating dedicated test customer account...")
test_user, created = User.objects.get_or_create(
    username="e2e_subscriber",
    defaults={"email": "e2e_sub@impactbridge.org", "role": "USER", "is_active": True}
)
test_user.set_password("SecurePassword123!")
test_user.save()

# Ensure customer starts on FREE plan
free_plan = Plan.objects.get(code='free')
pro_plan = Plan.objects.get(code='pro')
ultra_plan = Plan.objects.get(code='ultra')

sub, _ = Subscription.objects.update_or_create(
    user=test_user,
    defaults={
        "subscription_id": f"sub_e2e_{test_user.id}",
        "tenant_id": f"user_{test_user.id}",
        "plan_id": "free",
        "plan_record": free_plan,
        "status": "ACTIVE",
        "billing_cycle": "monthly",
        "auto_renew": False,
    }
)
client.force_login(test_user)
print(f"  Customer '{test_user.username}' initialized on tier '{sub.plan_id}'.")

# ── 2. Test FREE Tier Quotas & Enforcement ───────────────────────────────────
print("\n[2] Testing FREE tier limits & feature gates:")

# 2a. Saved records limit (10)
print("  - Testing saved records limit (10)...")
comp = Company.objects.first()
job = Job.objects.first()

# Clear existing test records
SavedRecord.objects.filter(user=test_user).delete()

# Cleanly save exactly 10 distinct records via API
for i in range(10):
    dummy_job = Job.objects.create(job_id=f"JOB_E2E_DISTINCT_{i}", company=comp, job_title=f"Role {i}")
    res = client.post('/api/user/saved-records', json.dumps({
        'item_type': 'JOB',
        'item_id': dummy_job.pk,
        'notes': f"Saved item {i}"
    }), content_type='application/json')
    assert res.status_code == 201

res_11th = client.post('/api/user/saved-records', json.dumps({
    'item_type': 'JOB',
    'item_id': job.pk,
}), content_type='application/json')
print(f"    11th save attempt -> HTTP {res_11th.status_code} ({res_11th.json().get('detail')})")
assert res_11th.status_code == 403, f"Expected 403, got {res_11th.status_code}"
assert res_11th.json().get('code') == 'quota_exceeded'

# Freeing quota by deleting 1
first_rec = SavedRecord.objects.filter(user=test_user).first()
res_del = client.delete('/api/user/saved-records', json.dumps({'id': first_rec.id}), content_type='application/json')
print(f"    Deleted 1 record -> Remaining: {res_del.json().get('count')}")
assert res_del.json().get('count') == 9

# 2b. Saved search limit (1)
print("  - Testing saved search limit (1)...")
SavedSearch.objects.filter(user=test_user).delete()
res_s1 = client.post('/api/user/saved-searches', json.dumps({'name': 'Search 1', 'query_params': {'q': 'ESG'}}), content_type='application/json')
assert res_s1.status_code == 201

res_s2 = client.post('/api/user/saved-searches', json.dumps({'name': 'Search 2', 'query_params': {'q': 'CSR'}}), content_type='application/json')
print(f"    2nd search save attempt -> HTTP {res_s2.status_code} ({res_s2.json().get('detail')})")
assert res_s2.status_code == 403
assert res_s2.json().get('code') == 'quota_exceeded'

# 2c. CSV export gate (0 exports on Free)
print("  - Testing CSV export gate on FREE plan...")
res_exp = client.get('/api/jobs?export=csv')
print(f"    Free user CSV export -> HTTP {res_exp.status_code} ({res_exp.json().get('error')})")
assert res_exp.status_code == 403, "Free user CSV export must be blocked with 403"

# 2d. Customer downgrade rejection
print("  - Testing customer downgrade rejection...")
res_down = client.post('/api/subscription/downgrade', json.dumps({'plan_id': 'free'}), content_type='application/json')
print(f"    Downgrade call -> HTTP {res_down.status_code} ({res_down.json().get('detail')})")
assert res_down.status_code == 403
assert res_down.json().get('code') == 'downgrade_blocked'

# ── 3. Wallet Top-Up (Prototype Mode) ─────────────────────────────────────────
print("\n[3] Testing wallet recharge (Safe Prototype Mode)...")
res_topup = client.post('/api/wallet/topup', json.dumps({
    'amount': 5000,  # Rs. 5,000
    'payment_method': 'PROTOTYPE_UPI',
    'description': 'Safe E2E Test Wallet Top-Up'
}), content_type='application/json')
print(f"  Wallet top-up -> HTTP {res_topup.status_code}")
topup_data = res_topup.json()
print(f"  New balance: Rs. {topup_data.get('balance_rupees', topup_data.get('wallet', {}).get('balance_rupees'))}")
assert res_topup.status_code == 200

# ── 4. Subscription Purchase & Upgrade to PRO ─────────────────────────────────
print("\n[4] Testing subscription purchase / upgrade to PRO:")
res_checkout = client.post('/api/subscription/upgrade', json.dumps({
    'plan_id': 'pro',
    'billing_cycle': 'monthly',
    'payment_method': 'WALLET'
}), content_type='application/json')
print(f"  Upgrade to PRO -> HTTP {res_checkout.status_code}")
checkout_data = res_checkout.json()
print(f"  Checkout status: {checkout_data.get('status')}, Payment ID: {checkout_data.get('payment_id')}")
assert res_checkout.status_code == 200
assert checkout_data.get('status') == 'success'

# Verify subscription updated to PRO
sub.refresh_from_db()
print(f"  Active plan in DB: {sub.plan_id} (name: {sub.plan.name})")
assert sub.plan_id == 'pro'

# Verify PRO entitlements now active
from modules.website.utils.entitlement_service import EntitlementService
svc = EntitlementService(test_user)
print(f"  New saved records limit: {svc.saved_records_limit}")
print(f"  New monthly export limit: {svc.monthly_export_limit}")
assert svc.saved_records_limit == 100
assert svc.monthly_export_limit == 200

# ── 5. Test PRO CSV Export & Quota Tracking ───────────────────────────────────
print("\n[5] Testing PRO CSV export & atomic quota usage:")
res_pro_exp = client.get('/api/jobs?export=csv&limit=50')
print(f"  PRO CSV export -> HTTP {res_pro_exp.status_code}, Content-Type: {res_pro_exp.get('Content-Type')}")
assert res_pro_exp.status_code == 200
assert 'text/csv' in res_pro_exp.get('Content-Type')
print(f"  Export quota used this month: {svc.monthly_exports_used} / 200")
assert svc.monthly_exports_used > 0, "Export usage must be recorded in UsageCounter"

# ── 6. Upgrade to ULTRA & Test Team / Refresh Features ────────────────────────
print("\n[6] Testing upgrade to ULTRA (Teams & Org):")
# Top up additional balance for Ultra
client.post('/api/wallet/topup', json.dumps({'amount': 10000, 'payment_method': 'WALLET'}), content_type='application/json')
res_ultra = client.post('/api/subscription/upgrade', json.dumps({
    'plan_id': 'ultra',
    'billing_cycle': 'monthly',
    'payment_method': 'WALLET'
}), content_type='application/json')
print(f"  Upgrade to ULTRA -> HTTP {res_ultra.status_code}")
assert res_ultra.status_code == 200

sub.refresh_from_db()
print(f"  Active plan in DB: {sub.plan_id} (name: {sub.plan.name})")
assert sub.plan_id == 'ultra'

svc = EntitlementService(test_user)
print(f"  Ultra saved records limit: {svc.saved_records_limit} (Unlimited)")
print(f"  Ultra export limit: {svc.monthly_export_limit}")
print(f"  Ultra team seats limit: {svc.team_members_limit}")
assert svc.saved_records_limit is None
assert svc.monthly_export_limit == 2000
assert svc.team_members_limit == 3

# Test team invitations (max 3 including owner)
print("  - Testing team seats (max 3)...")
TeamMembership.objects.filter(owner=test_user).delete()
res_m1 = client.post('/api/user/team', json.dumps({'email': 'analyst1@team.org', 'role': 'ANALYST'}), content_type='application/json')
assert res_m1.status_code == 201

res_m2 = client.post('/api/user/team', json.dumps({'email': 'analyst2@team.org', 'role': 'MEMBER'}), content_type='application/json')
assert res_m2.status_code == 201

# Attempting 4th member
res_m3 = client.post('/api/user/team', json.dumps({'email': 'analyst3@team.org', 'role': 'MEMBER'}), content_type='application/json')
print(f"    4th team member attempt -> HTTP {res_m3.status_code} ({res_m3.json().get('detail')})")
assert res_m3.status_code == 403
assert res_m3.json().get('code') == 'quota_exceeded'

# Test company data refresh request
print("  - Testing on-demand company refresh request...")
res_ref = client.post('/api/user/company-refresh', json.dumps({
    'company_id': comp.company_id,
    'reason': 'Annual ESG audit filing refresh request'
}), content_type='application/json')
print(f"    Company refresh request -> HTTP {res_ref.status_code} ({res_ref.json().get('message')})")
assert res_ref.status_code == 201

# ── 7. Subscription Cancellation & Resume Lifecycle ───────────────────────────
print("\n[7] Testing cancellation & resume lifecycle:")
res_cancel = client.post('/api/subscription/cancel', json.dumps({
    'reason': 'Testing cancellation workflow'
}), content_type='application/json')
print(f"  Cancel at period end -> HTTP {res_cancel.status_code}")
sub.refresh_from_db()
print(f"  cancel_at_period_end: {sub.cancel_at_period_end}")
assert sub.cancel_at_period_end is True

res_resume = client.post('/api/subscription/resume', content_type='application/json')
print(f"  Resume subscription -> HTTP {res_resume.status_code}")
sub.refresh_from_db()
print(f"  cancel_at_period_end after resume: {sub.cancel_at_period_end}")
assert sub.cancel_at_period_end is False

# ── 8. Subscription Renewal Workflow ──────────────────────────────────────────
print("\n[8] Testing renewal workflow (process_subscription_renewals)...")
renewal_summary = process_subscription_renewals(force_run=True)
print(f"  Renewal run summary: {renewal_summary}")
assert isinstance(renewal_summary, dict)

# ── 9. Verify Migrated Customer Integrity ─────────────────────────────────────
print("\n[9] Verifying migrated customer subscriptions & ledger integrity:")
# User 2 (ngo_manager): migrated from starter -> free
user2 = User.objects.filter(id=2).first()
if user2:
    sub2 = Subscription.objects.filter(user=user2).first()
    print(f"  User 2 ({user2.username}): plan={sub2.plan_id}, status={sub2.status}")
    assert sub2.plan_id == 'free'
    assert sub2.status == 'ACTIVE'

# User 1 (admin): migrated from foundation -> ultra
user1 = User.objects.filter(id=1).first()
if user1:
    sub1 = Subscription.objects.filter(user=user1).first()
    print(f"  User 1 ({user1.username}): plan={sub1.plan_id}, status={sub1.status}")
    assert sub1.plan_id == 'ultra'
    assert sub1.status == 'ACTIVE'
    # Wallet balance preserved
    w1 = Wallet.objects.filter(user=user1).first()
    print(f"  User 1 Wallet Balance: Rs. {w1.balance_rupees} (preserved!)")
    assert w1.balance_paise == 499210

# Total Payments & Invoices check
print(f"  Total historical payments in database: {Payment.objects.count()}")
print(f"  Total historical invoices in database: {Invoice.objects.count()}")
print(f"  Total wallet transactions in database: {WalletTransaction.objects.count()}")
assert Payment.objects.count() >= 9
assert Invoice.objects.count() >= 7

print("\n" + "=" * 70)
print("ALL E2E LIFECYCLE & INTEGRITY CHECKS COMPLETED SUCCESSFULLY!")
print("=" * 70)
