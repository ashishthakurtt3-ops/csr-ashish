import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)")
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings
from django.test import RequestFactory
from django.db import transaction
from modules.admin_panel.models import User, Plan, Subscription, Wallet, WalletTransaction, Payment, SavedRecord
from modules.website.utils.subscription_service import (
    process_subscription_renewals, topup_wallet, checkout, SubscriptionError,
    get_plan, _breakdown, SUPPLIER_STATE_CODE, _zero_credit
)
from modules.website.utils.entitlement_service import EntitlementService, EntitlementError
from modules.website.views.subscription_api_views import (
    _user, saved_records_api, wallet_balance, team_members_api
)

def run_tests():
    print("=" * 70)
    print("STARTING PRODUCTION-READINESS TEST SUITE")
    print("=" * 70)

    # -------------------------------------------------------------
    # TEST 1: PROTOTYPE PAYMENT MODE GUARD
    # -------------------------------------------------------------
    print("\n[TEST 1] Prototype Payment Mode Guard in Production...")
    test_user, _ = User.objects.get_or_create(username='audit_proto_guard_user', defaults={'email': 'proto@test.com', 'is_active': True})
    
    # Simulate production mode (ALLOW_PROTOTYPE_PAYMENTS = False)
    orig_proto_setting = getattr(settings, 'ALLOW_PROTOTYPE_PAYMENTS', True)
    try:
        settings.ALLOW_PROTOTYPE_PAYMENTS = False
        
        # Test 1a: Wallet topup must be rejected in production
        try:
            topup_wallet(test_user, 10000)
            assert False, "FAILED: topup_wallet should have been rejected when ALLOW_PROTOTYPE_PAYMENTS=False"
        except SubscriptionError as e:
            assert e.code == 'prototype_payments_disabled', f"Unexpected error code: {e.code}"
            print("  [PASS] Wallet top-up blocked when ALLOW_PROTOTYPE_PAYMENTS=False")

        # Test 1b: Direct non-wallet checkout must be rejected in production
        try:
            checkout({'plan_id': 'pro', 'billing_cycle': 'monthly', 'payment_method': 'UPI'}, user=test_user)
            assert False, "FAILED: Direct non-wallet checkout should have been rejected in production"
        except SubscriptionError as e:
            assert e.code == 'prototype_payments_disabled', f"Unexpected error code: {e.code}"
            print("  [PASS] Direct simulated checkout blocked when ALLOW_PROTOTYPE_PAYMENTS=False")

    finally:
        settings.ALLOW_PROTOTYPE_PAYMENTS = orig_proto_setting

    # -------------------------------------------------------------
    # TEST 2: RENEWAL LIFECYCLE (SUCCESS, INSUFFICIENT BALANCE, RETRY, EXPIRY)
    # -------------------------------------------------------------
    print("\n[TEST 2] Subscription Renewal Lifecycle...")
    pro_plan = Plan.objects.filter(code='pro', is_active=True).first()
    free_plan = Plan.objects.filter(code='free', is_active=True).first()
    assert pro_plan and free_plan, "Required plans 'pro' and 'free' must exist"

    renew_user, _ = User.objects.get_or_create(username='audit_renewal_user', defaults={'email': 'renew@test.com', 'is_active': True})
    tenant_id = f"user_{renew_user.id}"
    
    # Calculate exact total required (base + 18% GST)
    plan_dict = get_plan('pro')
    bd = _breakdown(plan_dict, 'monthly', {'applied': False}, SUPPLIER_STATE_CODE, _zero_credit())
    amount_needed = bd['total_paise']

    # Set up wallet with exact funds for 1 renewal
    wallet, _ = Wallet.objects.get_or_create(user=renew_user, defaults={'balance_paise': 0})
    wallet.balance_paise = amount_needed
    wallet.save()

    now_dt = datetime.now(timezone.utc)
    sub_id = f"SUB_AUDIT_{uuid.uuid4().hex[:8].upper()}"
    Subscription.objects.filter(tenant_id=tenant_id).delete()
    sub, _ = Subscription.objects.update_or_create(
        tenant_id=tenant_id,
        defaults={
            'subscription_id': sub_id,
            'user': renew_user,
            'plan_record': pro_plan,
            'plan_id': 'pro',
            'status': 'active',
            'billing_cycle': 'monthly',
            'current_period_start': (now_dt - timedelta(days=30)).isoformat(),
            'current_period_end': (now_dt - timedelta(minutes=5)).isoformat(), # Past due
            'auto_renew': True,
            'renewal_failure_count': 0,
        }
    )

    # 2a: Test successful renewal
    res = process_subscription_renewals(force_run=False, tenant_id=tenant_id)
    assert res['renewed'] == 1, f"Expected renewed=1, got {res}"
    sub.refresh_from_db()
    wallet.refresh_from_db()
    assert wallet.balance_paise == 0, f"Expected wallet balance 0, got {wallet.balance_paise}"
    new_end = datetime.fromisoformat(sub.current_period_end)
    assert new_end > now_dt, f"Expected new_end in future, got {new_end}"
    assert sub.renewal_failure_count == 0
    print(f"  [PASS] Renewal success: period extended to {new_end.date()}, charged {amount_needed} paise ({res['renewed']} renewed)")

    # 2b: Duplicate renewal prevention (current_period_end is in the future)
    res_dup = process_subscription_renewals(force_run=False, tenant_id=tenant_id)
    assert res_dup['processed'] == 0, f"Expected 0 processed (future date), got {res_dup}"
    print("  [PASS] Duplicate renewal prevented: skipped subscription with future period end")

    # 2c: Insufficient balance failure
    # Force period end into past again without refilling wallet
    sub.current_period_end = (now_dt - timedelta(minutes=5)).isoformat()
    sub.save()

    res_fail1 = process_subscription_renewals(force_run=False, tenant_id=tenant_id)
    assert res_fail1['failed'] == 1, f"Expected failed=1, got {res_fail1}"
    sub.refresh_from_db()
    assert sub.renewal_failure_count == 1, f"Expected failure count 1, got {sub.renewal_failure_count}"
    assert sub.status == 'active'
    print("  [PASS] Renewal failure 1 recorded: renewal_failure_count=1, subscription still active (grace period)")

    # 2d: Retry failure 2
    res_fail2 = process_subscription_renewals(force_run=False, tenant_id=tenant_id)
    assert res_fail2['failed'] == 1
    sub.refresh_from_db()
    assert sub.renewal_failure_count == 2
    print("  [PASS] Renewal failure 2 recorded: renewal_failure_count=2")

    # 2e: Max retries failure 3 -> Transition to EXPIRED on FREE plan
    res_fail3 = process_subscription_renewals(force_run=False, tenant_id=tenant_id)
    assert res_fail3['failed'] == 1
    assert res_fail3['expired'] == 1, f"Expected expired=1, got {res_fail3}"
    sub.refresh_from_db()
    assert sub.status.lower() == 'expired', f"Expected status expired, got {sub.status}"
    assert sub.plan_id == 'free', f"Expected plan_id 'free', got {sub.plan_id}"
    assert sub.plan_record.code == 'free', f"Expected plan_record 'free', got {sub.plan_record.code}"
    print("  [PASS] Renewal failure 3: subscription marked 'expired' and smoothly transitioned to 'free' plan")

    # -------------------------------------------------------------
    # TEST 3: ACCESS RESTRICTIONS AFTER EXPIRY
    # -------------------------------------------------------------
    print("\n[TEST 3] Access Restrictions After Expiry...")
    es = EntitlementService(renew_user)
    quota = es.quota_summary()
    assert quota['tier'] == 'free', f"Expected tier 'free' after expiry, got {quota['tier']}"
    assert quota['monthly_exports']['limit'] == 0, "Export quota must be 0 for expired user"
    assert quota['saved_records']['limit'] == 10, "Saved records limit must be 10 for expired user"

    try:
        es.check_export_quota(count=5)
        assert False, "Expected EntitlementError on export for expired user"
    except EntitlementError as e:
        assert e.feature == 'export'

    try:
        es.check_advanced_filters()
        assert False, "Expected EntitlementError on advanced filters for expired user"
    except EntitlementError as e:
        assert e.feature == 'advanced_filters'
    print("  [PASS] Entitlement restrictions strictly enforced for expired subscription")

    # -------------------------------------------------------------
    # TEST 4: CUSTOMER DATA ISOLATION & BACKEND AUTHORIZATION
    # -------------------------------------------------------------
    print("\n[TEST 4] Customer Data Isolation & Authorization...")
    factory = RequestFactory()

    # 4a: Unauthenticated access with ALLOW_DEMO_AUTH_FALLBACK=False must return None
    orig_demo_setting = getattr(settings, 'ALLOW_DEMO_AUTH_FALLBACK', True)
    try:
        settings.ALLOW_DEMO_AUTH_FALLBACK = False
        anon_request = factory.get('/api/subscription/wallet/balance/')
        anon_request.user = django.contrib.auth.models.AnonymousUser()
        user_res = _user(anon_request)
        assert user_res is None, f"Expected None for unauthenticated user in production, got {user_res}"
        print("  [PASS] _user(request) returns None for unauthenticated visitor when ALLOW_DEMO_AUTH_FALLBACK=False")

        # 4b: Endpoints return 401 when unauthenticated
        wb_resp = wallet_balance(anon_request)
        assert wb_resp.status_code == 401, f"Expected 401 for wallet_balance, got {wb_resp.status_code}"
        
        sr_resp = saved_records_api(anon_request)
        assert sr_resp.status_code == 401, f"Expected 401 for saved_records_api, got {sr_resp.status_code}"

        tm_resp = team_members_api(anon_request)
        assert tm_resp.status_code == 401, f"Expected 401 for team_members_api, got {tm_resp.status_code}"
        print("  [PASS] Unauthenticated API requests receive HTTP 401 Unauthorized")
    finally:
        settings.ALLOW_DEMO_AUTH_FALLBACK = orig_demo_setting

    # 4c: Isolation between User A and User B
    from modules.admin_panel.models import SavedSearch
    user_a, _ = User.objects.get_or_create(username='audit_user_a', defaults={'email': 'a@test.com', 'is_active': True})
    user_b, _ = User.objects.get_or_create(username='audit_user_b', defaults={'email': 'b@test.com', 'is_active': True})

    SavedSearch.objects.filter(user__in=[user_a, user_b]).delete()
    s_a = SavedSearch.objects.create(user=user_a, name='User A Secret Search', search_type='JOB', query_params={'q': 'csr'})
    s_b = SavedSearch.objects.create(user=user_b, name='User B Secret Search', search_type='JOB', query_params={'q': 'finance'})

    from modules.website.views.subscription_api_views import saved_searches_api
    req_a = factory.get('/api/subscription/saved-searches/')
    req_a.user = user_a
    resp_a = saved_searches_api(req_a)
    import json
    data_a = json.loads(resp_a.content)
    names_a = [s['name'] for s in data_a.get('searches', [])]
    assert 'User A Secret Search' in names_a and 'User B Secret Search' not in names_a, f"User A leaked User B data: {names_a}"
    print("  [PASS] Customer data isolation verified: User A cannot see User B saved searches")

    # Clean up test accounts
    SavedSearch.objects.filter(user__in=[user_a, user_b]).delete()
    Subscription.objects.filter(user__in=[test_user, renew_user, user_a, user_b]).delete()
    WalletTransaction.objects.filter(user__in=[test_user, renew_user, user_a, user_b]).delete()
    Payment.objects.filter(user__in=[test_user, renew_user, user_a, user_b]).delete()
    Wallet.objects.filter(user__in=[test_user, renew_user, user_a, user_b]).delete()
    User.objects.filter(username__in=['audit_proto_guard_user', 'audit_renewal_user', 'audit_user_a', 'audit_user_b']).delete()

    print("\n" + "=" * 70)
    print("ALL PRODUCTION-READINESS TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)

if __name__ == '__main__':
    run_tests()
