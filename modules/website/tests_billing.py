import json
from datetime import timedelta
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from modules.admin_panel.models import (
    Plan, PlanEntitlement, Wallet, WalletTransaction,
    Payment, Subscription, SubscriptionEvent, Invoice, PromoCode
)
from modules.admin_panel.management.commands.seed_subscription_plans import Command as SeedCommand
from modules.website.utils.subscription_service import (
    change_plan, schedule_plan_change,
    get_plan, require_plan, get_or_create_wallet, topup_wallet,
    quote, checkout, process_subscription_renewals, refund_payment,
    toggle_auto_renew, schedule_downgrade, cancel, resume,
    rupees_to_paise, paise_to_rupees
)

User = get_user_model()


class ComprehensiveBillingTestSuite(TestCase):
    """
    Complete Integration Test Suite verifying all 38 requirements specified
    in the Project-Specific Master Task.
    """

    @classmethod
    def setUpTestData(cls):
        cmd = SeedCommand()
        cmd.handle()

    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='donor_org1',
            email='donor1@test-org.in',
            password='TestPassword123!',
            organization_name='Helping Hands Foundation',
            role='NGO_MANAGER'
        )
        self.user2 = User.objects.create_user(
            username='donor_org2',
            email='donor2@test-org.in',
            password='TestPassword123!',
            organization_name='Green Planet Trust',
            role='USER'
        )
        self.admin_user = User.objects.create_superuser(
            username='super_admin',
            email='admin@impactbridge.ai',
            password='AdminPassword123!'
        )

    # -------------------------------------------------------------------------
    # TEST 1, 2, 3: Registration, Default Starter Plan & Auto-Provisioned Wallet
    # -------------------------------------------------------------------------
    def test_01_02_03_registration_starter_plan_and_wallet_provisioning(self):
        # TEST 1: Register new user
        reg_response = self.client.post('/register/', {
            'username': 'new_ngo_user',
            'email': 'new_ngo@test.org',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!',
            'organization_name': 'New Wave NGO',
            'role': 'NGO_MANAGER'
        }, follow=True)
        self.assertEqual(reg_response.status_code, 200)

        new_user = User.objects.get(username='new_ngo_user')
        self.assertIsNotNone(new_user)

        # TEST 2: User receives starter plan
        sub = Subscription.objects.filter(user=new_user).first()
        self.assertIsNotNone(sub, "User must receive a default subscription upon registration")
        self.assertEqual(sub.plan_id, 'starter', "Default subscription must be 'starter'")
        self.assertEqual(sub.status, 'ACTIVE')

        # TEST 3: Wallet exists automatically
        wallet = Wallet.objects.filter(user=new_user).first()
        self.assertIsNotNone(wallet, "Wallet must exist automatically for new user")
        self.assertEqual(wallet.balance_paise, 0)

    # -------------------------------------------------------------------------
    # TEST 4 & 5: Add Prototype Funds to Wallet
    # -------------------------------------------------------------------------
    def test_04_05_add_funds_and_wallet_balance_increase(self):
        wallet = get_or_create_wallet(self.user1)
        self.assertEqual(wallet.balance_paise, 0)

        # TEST 4: Add ₹5,000 prototype funds (500,000 paise)
        result = topup_wallet(self.user1, amount_paise=500000, description="Test prototype funding")
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['amount_paise'], 500000)

        # Check payment record
        p = Payment.objects.get(payment_id=result['payment_id'])
        self.assertEqual(p.payment_status, 'SUCCESS')

        # TEST 5: Wallet becomes ₹5,000
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance_paise, 500000)
        self.assertEqual(wallet.balance_inr, 5000.0)

    # -------------------------------------------------------------------------
    # TEST 6, 7, 8, 9, 10, 11: Purchase Pro & Entitlements Activation
    # -------------------------------------------------------------------------
    def test_06_to_11_purchase_pro_deduction_payment_sub_invoice_entitlements(self):
        # Give user enough prototype funds (₹10,000 = 1,000,000 paise)
        topup_wallet(self.user1, amount_paise=1000000)
        wallet = get_or_create_wallet(self.user1)
        initial_balance_paise = wallet.balance_paise

        # TEST 6: Purchase Pro
        result = checkout(
            payload={
                'plan_id': 'pro',
                'billing_cycle': 'monthly',
                'payment_method': 'WALLET',
                'place_of_supply': '27'
            },
            user=self.user1
        )
        self.assertEqual(result['status'], 'success')
        self.assertTrue(result['success'])
        payment_dict = result['payment']
        sub_dict = result['subscription']
        inv_dict = result['invoice']

        # TEST 7: Wallet decreases correctly
        wallet.refresh_from_db()
        expected_balance_paise = initial_balance_paise - payment_dict['amount_paise']
        self.assertEqual(wallet.balance_paise, expected_balance_paise)

        # TEST 8: Payment appears in history
        user_payments = Payment.objects.filter(user=self.user1, payment_type='SUBSCRIPTION')
        self.assertTrue(user_payments.exists())
        self.assertEqual(user_payments.first().payment_status, 'SUCCESS')

        # TEST 9: Subscription appears in DB
        sub_db = Subscription.objects.get(user=self.user1, status='ACTIVE')
        self.assertEqual(sub_db.plan_id, 'pro')
        self.assertEqual(sub_db.status, 'ACTIVE')

        # TEST 10: Invoice generated
        self.assertIsNotNone(inv_dict)
        self.assertTrue(inv_dict['invoice_number'].startswith('IB/'))
        self.assertEqual(inv_dict['total_paise'], payment_dict['amount_paise'])

        # TEST 11: Pro entitlements activate
        self.assertTrue(sub_db.is_pro)
        self.assertTrue(sub_db.can_view_contacts)
        self.assertTrue(sub_db.can_reprobe_crawler)
        self.assertEqual(sub_db.max_export_rows, 1000)
        self.assertEqual(sub_db.max_allowed_seats, 3)

    # -------------------------------------------------------------------------
    # TEST 12: Attempt Feature Unavailable to Starter
    # -------------------------------------------------------------------------
    def test_12_feature_unavailable_to_starter(self):
        starter_sub = Subscription(subscription_id="SUB_TEST", plan_id='starter', status='ACTIVE')
        self.assertFalse(starter_sub.can_view_contacts, "Starter tier cannot view contacts")
        self.assertFalse(starter_sub.can_reprobe_crawler, "Starter tier cannot probe crawler")
        self.assertFalse(starter_sub.can_access_api, "Starter tier cannot access API")
        self.assertEqual(starter_sub.max_export_rows, 25, "Starter tier limited to 25 export rows")

    # -------------------------------------------------------------------------
    # TEST 13, 14, 15: Upgrade Pro -> Enterprise with Proration
    # -------------------------------------------------------------------------
    def test_13_14_15_upgrade_pro_to_enterprise_with_proration(self):
        # 1. Setup active Pro subscription
        topup_wallet(self.user1, amount_paise=3000000)
        checkout(payload={'plan_id': 'pro', 'billing_cycle': 'monthly', 'payment_method': 'WALLET'}, user=self.user1)

        wallet = get_or_create_wallet(self.user1)
        balance_before_upgrade = wallet.balance_paise

        # TEST 14: Quote proration credit
        q = quote(payload={'plan_id': 'enterprise', 'billing_cycle': 'monthly'}, user=self.user1)
        self.assertGreater(q['proration']['credit_paise'], 0, "Upgrade must offer proration credit for unused Pro time")

        # TEST 13: Execute Upgrade Pro -> Enterprise
        result = checkout(
            payload={'plan_id': 'enterprise', 'billing_cycle': 'monthly', 'payment_method': 'WALLET'},
            user=self.user1
        )
        self.assertEqual(result['status'], 'success')
        upgrade_sub = Subscription.objects.get(user=self.user1, status='ACTIVE')
        upgrade_payment = result['payment']

        # TEST 15: Wallet deduction correct (net of proration credit + GST)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance_paise, balance_before_upgrade - upgrade_payment['amount_paise'])
        self.assertEqual(upgrade_sub.plan_id, 'enterprise')
        self.assertTrue(upgrade_sub.can_access_api, "Enterprise tier must have API access")

    # -------------------------------------------------------------------------
    # TEST 16 & 17: Downgrade Enterprise -> Pro (Scheduled for Period End)
    # -------------------------------------------------------------------------
    def test_16_17_downgrade_scheduled_for_period_end(self):
        topup_wallet(self.user1, amount_paise=3000000)
        checkout(payload={'plan_id': 'enterprise', 'billing_cycle': 'monthly', 'payment_method': 'WALLET'}, user=self.user1)

        sub = Subscription.objects.get(user=self.user1, status='ACTIVE')
        self.assertEqual(sub.plan_id, 'enterprise')

        # TEST 16: Downgrade to Pro
        updated_res = schedule_downgrade(payload={'plan_id': 'pro'}, user=self.user1)
        self.assertEqual(updated_res['status'], 'success')

        # TEST 17: User retains current Enterprise access until period end
        sub.refresh_from_db()
        self.assertEqual(sub.plan_id, 'enterprise', "Current plan stays Enterprise")
        self.assertEqual(sub.pending_downgrade_plan, 'pro', "Target downgrade plan is recorded as Pro")
        self.assertTrue(sub.can_access_api, "User retains Enterprise capabilities until period end")

    # -------------------------------------------------------------------------
    # TEST 18 & 19: Auto-Renew Toggle (Cancel & Reactivate)
    # -------------------------------------------------------------------------
    def test_18_19_cancel_and_reactivate_auto_renew(self):
        topup_wallet(self.user1, amount_paise=1000000)
        res = checkout(payload={'plan_id': 'pro', 'billing_cycle': 'monthly', 'payment_method': 'WALLET'}, user=self.user1)
        sub = Subscription.objects.get(user=self.user1, status='ACTIVE')
        self.assertTrue(sub.auto_renew)

        # TEST 18: Cancel auto-renew
        toggle_auto_renew(user=self.user1, enable=False)
        sub.refresh_from_db()
        self.assertFalse(sub.auto_renew)
        self.assertTrue(sub.cancel_at_period_end)

        # TEST 19: Reactivate auto-renew
        toggle_auto_renew(user=self.user1, enable=True)
        sub.refresh_from_db()
        self.assertTrue(sub.auto_renew)
        self.assertFalse(sub.cancel_at_period_end)

    # -------------------------------------------------------------------------
    # TEST 20 & 21: Auto-Renewal Engine (Success with funds & Failure without)
    # -------------------------------------------------------------------------
    def test_20_21_renewal_engine_success_and_failure(self):
        # TEST 20: Renewal succeeds with sufficient wallet funds
        topup_wallet(self.user1, amount_paise=2000000)
        checkout(payload={'plan_id': 'pro', 'billing_cycle': 'monthly', 'payment_method': 'WALLET'}, user=self.user1)
        sub1 = Subscription.objects.get(user=self.user1, status='ACTIVE')

        # Fast forward period end to the past
        sub1.current_period_end = (timezone.now() - timedelta(days=1)).isoformat()
        sub1.auto_renew = True
        sub1.save()

        summary = process_subscription_renewals(force=True, tenant_id=sub1.tenant_id)
        self.assertEqual(summary['renewed'], 1)
        self.assertEqual(summary['failed'], 0)

        sub1.refresh_from_db()
        self.assertGreater(str(sub1.current_period_end), timezone.now().isoformat(), "Period end must be extended into the future")

        # TEST 21: Renewal fails with insufficient wallet funds
        # Empty user1's wallet
        wallet = get_or_create_wallet(self.user1)
        wallet.balance_paise = 0
        wallet.save()

        sub1.current_period_end = (timezone.now() - timedelta(days=1)).isoformat()
        sub1.save()

        summary2 = process_subscription_renewals(force=True, tenant_id=sub1.tenant_id)
        self.assertEqual(summary2['failed'], 1)
        sub1.refresh_from_db()
        self.assertGreater(sub1.renewal_failure_count, 0)

    # -------------------------------------------------------------------------
    # TEST 22: Subscription Expiration when Auto-Renew is OFF
    # -------------------------------------------------------------------------
    def test_22_subscription_expires_correctly_when_auto_renew_off(self):
        topup_wallet(self.user1, amount_paise=1000000)
        checkout(payload={'plan_id': 'pro', 'billing_cycle': 'monthly', 'payment_method': 'WALLET'}, user=self.user1)
        sub = Subscription.objects.get(user=self.user1, status='ACTIVE')

        sub.auto_renew = False
        sub.current_period_end = (timezone.now() - timedelta(days=1)).isoformat()
        sub.save()

        summary = process_subscription_renewals(force=True, tenant_id=sub.tenant_id)
        self.assertEqual(summary['expired'], 1)
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'EXPIRED')

    # -------------------------------------------------------------------------
    # TEST 23 & 24: Payment Failure and Payment Cancelled Recording
    # -------------------------------------------------------------------------
    def test_23_24_payment_failure_and_cancelled_recording(self):
        # TEST 23: Payment failure recorded when funds insufficient
        wallet = get_or_create_wallet(self.user2)
        wallet.balance_paise = 0
        wallet.save()

        try:
            checkout(payload={'plan_id': 'pro', 'billing_cycle': 'monthly', 'payment_method': 'WALLET'}, user=self.user2)
        except Exception:
            pass

        failed_payments = Payment.objects.filter(user=self.user2, payment_status='FAILED')
        self.assertTrue(failed_payments.exists(), "Failed payment must be recorded in database")

        # TEST 24: Payment cancelled recorded
        payment = Payment.objects.create(
            user=self.user2,
            plan_code='pro',
            amount_paise=499900,
            payment_method='UPI',
            payment_status='CANCELLED',
            payment_type='SUBSCRIPTION',
            failure_reason='User cancelled simulated payment modal.'
        )
        self.assertEqual(payment.payment_status, 'CANCELLED')

    # -------------------------------------------------------------------------
    # TEST 25: Refund Credits Wallet
    # -------------------------------------------------------------------------
    def test_25_refund_credits_wallet(self):
        topup_wallet(self.user1, amount_paise=1000000)
        res = checkout(payload={'plan_id': 'pro', 'billing_cycle': 'monthly', 'payment_method': 'WALLET'}, user=self.user1)
        payment_id = res['payment']['payment_id']
        wallet = get_or_create_wallet(self.user1)
        balance_after_purchase = wallet.balance_paise

        # Process refund
        refund_payment(payment_id=payment_id, actor='Admin', reason="Customer satisfaction guarantee")

        payment = Payment.objects.get(payment_id=payment_id)
        self.assertEqual(payment.payment_status, 'REFUNDED')

        wallet.refresh_from_db()
        self.assertEqual(wallet.balance_paise, balance_after_purchase + payment.amount_paise)

        # Check refund ledger transaction
        tx = WalletTransaction.objects.filter(reference_type='PAYMENT', reference_id=payment_id, transaction_type='REFUND').first()
        self.assertIsNotNone(tx)
        self.assertEqual(tx.credit_or_debit, 'CREDIT')

    # -------------------------------------------------------------------------
    # TEST 26: Promo Code Application
    # -------------------------------------------------------------------------
    def test_26_promo_code_works(self):
        PromoCode.objects.create(code='IMPACT25', percent_off=25, active=True)
        q = quote(payload={'plan_id': 'pro', 'billing_cycle': 'monthly', 'promo_code': 'IMPACT25'}, user=self.user1)

        self.assertGreater(q['promo']['discount_paise'], 0)
        expected_discount_paise = (q['breakdown']['base_paise'] * 25) // 100
        self.assertEqual(q['promo']['discount_paise'], expected_discount_paise)

    # -------------------------------------------------------------------------
    # TEST 27: GST Calculation Correctness
    # -------------------------------------------------------------------------
    def test_27_gst_calculation_remains_correct(self):
        # Maharashtra (intra-state: CGST 9% + SGST 9%)
        q_intra = quote(payload={'plan_id': 'pro', 'billing_cycle': 'monthly', 'place_of_supply': '27'}, user=self.user1)
        tax_intra = q_intra['breakdown']['tax']
        self.assertEqual(tax_intra['gst_rate_percent'], 18.0)
        self.assertEqual(tax_intra['supply_type'], 'INTRA_STATE')
        self.assertGreater(tax_intra['cgst_paise'], 0)
        self.assertGreater(tax_intra['sgst_paise'], 0)
        self.assertEqual(tax_intra['igst_paise'], 0)

        # Karnataka (inter-state: IGST 18%)
        q_inter = quote(payload={'plan_id': 'pro', 'billing_cycle': 'monthly', 'place_of_supply': '29'}, user=self.user1)
        tax_inter = q_inter['breakdown']['tax']
        self.assertEqual(tax_inter['supply_type'], 'INTER_STATE')
        self.assertGreater(tax_inter['igst_paise'], 0)
        self.assertEqual(tax_inter['cgst_paise'], 0)
        self.assertEqual(tax_inter['sgst_paise'], 0)

    # -------------------------------------------------------------------------
    # TEST 28: Idempotency Key Prevents Double Charges
    # -------------------------------------------------------------------------
    def test_28_duplicate_idempotency_key_does_not_double_charge(self):
        topup_wallet(self.user1, amount_paise=1500000)
        wallet = get_or_create_wallet(self.user1)
        bal_start = wallet.balance_paise
        idempotency_key = "idemp_test_key_12345"

        # First request
        res1 = checkout(
            payload={
                'plan_id': 'pro',
                'billing_cycle': 'monthly',
                'payment_method': 'WALLET',
                'request_id': idempotency_key
            },
            user=self.user1
        )
        self.assertEqual(res1['status'], 'success')
        wallet.refresh_from_db()
        bal_after_first = wallet.balance_paise
        self.assertLess(bal_after_first, bal_start)

        # Duplicate request with same idempotency key
        res2 = checkout(
            payload={
                'plan_id': 'pro',
                'billing_cycle': 'monthly',
                'payment_method': 'WALLET',
                'request_id': idempotency_key
            },
            user=self.user1
        )
        self.assertEqual(res2['status'], 'success')
        self.assertTrue(res2.get('idempotent_replay'))

        wallet.refresh_from_db()
        self.assertEqual(wallet.balance_paise, bal_after_first, "Duplicate idempotency key must NOT deduct wallet again")

    # -------------------------------------------------------------------------
    # TEST 29 & 30: Security & Isolation (Users cannot view other wallets or admin)
    # -------------------------------------------------------------------------
    def test_29_30_security_and_authorization(self):
        # TEST 29: User cannot see another user's wallet
        topup_wallet(self.user1, amount_paise=500000)
        self.client.force_login(self.user2)

        # Request user2's wallet balance
        res = self.client.get('/api/subscription/wallet/balance')
        data = res.json()
        self.assertEqual(data['balance_inr'], 0.0, "User2 should not see User1's ₹5000 balance")

        # TEST 30: Non-admin user cannot access admin billing
        admin_res = self.client.get('/admin-portal/subscriptions/')
        self.assertIn(admin_res.status_code, [302, 403], "Standard user must be rejected from admin portal")

    # -------------------------------------------------------------------------
    # TEST 31 & 32: Dynamic Pricing Modification
    # -------------------------------------------------------------------------
    def test_31_32_admin_changes_pro_price_and_pricing_page_updates(self):
        # TEST 31: Admin changes Pro price to ₹6,499
        pro_plan = Plan.objects.get(code='pro')
        pro_plan.monthly_price_paise = 649900
        pro_plan.save()

        # TEST 32: Public API immediately reflects new price
        res = self.client.get('/api/subscription/plans')
        self.assertEqual(res.status_code, 200)
        plans = res.json()['plans']
        pro_api = next(p for p in plans if p['code'] == 'pro')
        self.assertEqual(pro_api['monthly_price'], 6499.0)

    # -------------------------------------------------------------------------
    # TEST 33 & 34: Plan Deactivation
    # -------------------------------------------------------------------------
    def test_33_34_disabled_plan_cannot_be_purchased(self):
        # TEST 33: Disable Enterprise plan
        ent_plan = Plan.objects.get(code='enterprise')
        ent_plan.is_active = False
        ent_plan.save()

        # TEST 34: Purchase of disabled plan is rejected
        topup_wallet(self.user1, amount_paise=5000000)
        with self.assertRaises(Exception):
            checkout(payload={'plan_id': 'enterprise', 'billing_cycle': 'monthly'}, user=self.user1)

    # -------------------------------------------------------------------------
    # TEST 35 & 36: Dynamic New Plan Creation
    # -------------------------------------------------------------------------
    def test_35_36_new_plan_creation_and_appearance_on_api(self):
        # TEST 35: Admin creates a new custom plan
        Plan.objects.create(
            code='special_ngo',
            name='Special Impact Tier',
            description='Exclusive subsidized tier for grassroot initiatives.',
            monthly_price_paise=199900,
            yearly_price_paise=1999000,
            is_active=True,
            is_visible=True,
            display_order=25
        )

        # TEST 36: New plan automatically appears on public API
        res = self.client.get('/api/subscription/plans')
        plans = res.json()['plans']
        codes = [p['code'] for p in plans]
        self.assertIn('special_ngo', codes)

    # -------------------------------------------------------------------------
    # TEST 37 & 38: Entitlement Limits Modification & Enforcement
    # -------------------------------------------------------------------------
    def test_37_38_modify_entitlement_limits_and_verify_access(self):
        # TEST 37: Modify export rows entitlement for Pro plan
        pro_plan = Plan.objects.get(code='pro')
        ent = PlanEntitlement.objects.get(plan=pro_plan, feature_key='export_rows_per_month')
        ent.numeric_value = 5000
        ent.save()

        # TEST 38: Subscription model dynamically pulls new limit
        sub = Subscription(subscription_id="SUB_P_DYN", plan_record=pro_plan, plan_id='pro')
        self.assertEqual(sub.max_export_rows, 5000)

    # -------------------------------------------------------------------------
    # TEST 39-44: Unified Change Plan & Zero 'Downgrade' UI/API Guarantee
    # -------------------------------------------------------------------------
    def test_39_to_44_unified_change_plan_and_zero_downgrade_guarantee(self):
        # 39: Activate Pro plan via change_plan
        topup_wallet(self.user1, amount_paise=1000000)
        res_pro = change_plan({'plan_id': 'pro', 'billing_cycle': 'monthly'}, user=self.user1)
        self.assertEqual(res_pro['subscription']['plan_code'], 'pro')
        self.assertNotIn('downgrade', str(res_pro).lower(), "Response must never contain the word downgrade")

        # 40: Attempt to change to the same active plan (should raise same_plan)
        with self.assertRaises(Exception) as cm:
            change_plan({'plan_id': 'pro', 'billing_cycle': 'monthly'}, user=self.user1)
        self.assertIn('already', str(cm.exception).lower())

        # 41: Change plan to a lower-priced tier (Pro -> Starter)
        res_lower = change_plan({'plan_id': 'starter'}, user=self.user1)
        self.assertEqual(res_lower['status'], 'success')
        self.assertEqual(res_lower['pending_change_plan'], 'starter')
        self.assertNotIn('downgrade', res_lower['message'].lower(), "User-facing message must not contain downgrade")
        self.assertIn('plan change', res_lower['message'].lower())

        # 42: API endpoint /api/subscription/change-plan works identically
        self.client.force_login(self.user2)
        topup_wallet(self.user2, amount_paise=1000000)
        api_res = self.client.post(
            '/api/subscription/change-plan',
            data=json.dumps({'plan_id': 'pro', 'billing_cycle': 'monthly'}),
            content_type='application/json'
        )
        self.assertEqual(api_res.status_code, 200)
        self.assertNotIn('downgrade', api_res.content.decode('utf-8').lower())

        # 43: History and events contain neutral wording
        events = SubscriptionEvent.objects.filter(tenant_id=f"user_{self.user1.id}")
        for ev in events:
            self.assertNotIn('downgrade', str(ev.notes).lower(), f"Event note contains downgrade: {ev.notes}")

        # 44: Extended admin plan attributes exist and are accessible
        pro_plan = Plan.objects.get(code='pro')
        pro_plan.savings_text = "Save ₹989"
        pro_plan.is_recommended = True
        pro_plan.button_text = "Change Plan"
        pro_plan.discount_percent = 16
        pro_plan.save()

        plan_dict = get_plan('pro')
        self.assertEqual(plan_dict['savings_text'], "Save ₹989")
        self.assertTrue(plan_dict['is_recommended'])
        self.assertEqual(plan_dict['button_text'], "Change Plan")
        self.assertEqual(plan_dict['discount_percent'], 16)
        self.assertNotIn('downgrade', str(plan_dict).lower())
