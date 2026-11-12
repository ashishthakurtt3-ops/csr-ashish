import os
import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from datetime import datetime, timedelta, timezone
from django.contrib.auth import get_user_model
from modules.admin_panel.models import Plan, Subscription, SubscriptionEvent
from modules.website.utils.entitlement_service import user_has_active_plan, EntitlementService
from modules.website.utils.subscription_service import checkout, current, SubscriptionError

User = get_user_model()

def run_tests():
    print("==================================================")
    print("Testing 14-Day Free Trial End-to-End Implementation")
    print("==================================================")

    # Clean up or create test user
    username = "trial_test_user_14d"
    User.objects.filter(username=username).delete()
    user = User.objects.create_user(
        username=username,
        email="trial14d@example.com",
        password="TestPassword123!"
    )
    print(f"[1] Created test user: {user.username}")

    # Check 1: Initially, user has NO active plan
    assert not user_has_active_plan(user), "User should have no active plan before selecting one!"
    print("  [PASS] Initially user_has_active_plan is False")

    # Check 2: User activates Free Plan (should get 14-Day Free Trial)
    payload = {
        'plan_id': 'free',
        'billing_cycle': 'monthly',
        'payment_method': 'WALLET'
    }
    result = checkout(payload, user=user)
    print("  [PASS] checkout(plan_id='free') succeeded")

    sub = Subscription.objects.filter(user=user).order_by('-created_at').first()
    assert sub is not None, "Subscription record must exist!"
    assert sub.status == 'TRIALING', f"Expected status 'TRIALING', got '{sub.status}'"
    print(f"  [PASS] Subscription status is '{sub.status}'")

    assert sub.current_period_start is not None, "current_period_start must be set"
    assert sub.current_period_end is not None, "current_period_end must be set"
    
    end_dt = datetime.fromisoformat(sub.current_period_end.replace('Z', '+00:00'))
    start_dt = datetime.fromisoformat(sub.current_period_start.replace('Z', '+00:00'))
    duration_days = (end_dt - start_dt).days
    assert duration_days == 14, f"Expected 14 days trial duration, got {duration_days}"
    print(f"  [PASS] Free trial duration is exactly {duration_days} days")

    # Check 3: Active trial grants access
    assert user_has_active_plan(user), "user_has_active_plan should return True while trial is active!"
    print("  [PASS] user_has_active_plan(user) is True during active 14-day trial")

    # Check 4: Trying to re-activate free plan while currently trialing should be blocked
    try:
        checkout(payload, user=user)
        assert False, "Should have raised SubscriptionError for trial already active"
    except SubscriptionError as e:
        assert 'active 14-Day Free Trial' in str(e), f"Unexpected error message: {e}"
        print(f"  [PASS] Re-activating while active correctly blocked: '{e.message}'")

    # Check 5: Simulate trial expiration (current_period_end set to past)
    past_end = datetime.now(timezone.utc) - timedelta(days=1)
    sub.current_period_end = past_end.isoformat()
    sub.save(update_fields=['current_period_end'])
    print(f"[2] Simulated trial expiration: set period_end to {past_end.isoformat()}")

    # Check 6: user_has_active_plan detects expiration and returns False
    has_plan = user_has_active_plan(user)
    assert not has_plan, "user_has_active_plan must return False when trial is expired!"
    sub.refresh_from_db()
    assert sub.status == 'EXPIRED', f"Expected sub.status to be 'EXPIRED', got '{sub.status}'"
    print("  [PASS] Expired trial detected: user_has_active_plan returns False, status updated to 'EXPIRED'")

    # Check 7: Trying to re-activate free plan after expiration must be strictly blocked
    try:
        checkout(payload, user=user)
        assert False, "Should have raised SubscriptionError for expired trial"
    except SubscriptionError as e:
        assert 'expired' in str(e).lower(), f"Unexpected error message: {e}"
        print(f"  [PASS] Re-activating after expiration blocked: '{e.message}'")

    # Check 8: Upgrading to PRO from expired trial succeeds
    from modules.admin_panel.models import Wallet
    w, _ = Wallet.objects.get_or_create(user=user)
    w.balance_paise = 1000000  # Rs 10,000
    w.save()

    pro_payload = {
        'plan_id': 'pro',
        'billing_cycle': 'monthly',
        'payment_method': 'WALLET'
    }
    pro_result = checkout(pro_payload, user=user)
    sub.refresh_from_db()
    assert sub.status == 'ACTIVE', f"Expected status 'ACTIVE' for PRO, got '{sub.status}'"
    assert sub.plan_id == 'pro', f"Expected plan_id 'pro', got '{sub.plan_id}'"
    assert user_has_active_plan(user), "user_has_active_plan should return True after upgrading to PRO!"
    print("  [PASS] Upgrading to PRO from expired trial succeeded! Status is ACTIVE")

    print("\n==================================================")
    print("ALL 14-DAY FREE TRIAL TESTS PASSED SUCCESSFULLY! 🚀")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
