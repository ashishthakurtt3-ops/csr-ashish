import json
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from modules.admin_panel.models import (
    Plan, PlanEntitlement, Subscription, UsageCounter,
    SavedRecord, SavedSearch, TeamMembership, CompanyRefreshRequest,
    Company, Job, CSRProject
)
from modules.website.utils.entitlement_service import EntitlementService, EntitlementError

User = get_user_model()


class ThreeTierSubscriptionTests(TestCase):
    """
    Comprehensive test suite verifying the FREE, PRO, and ULTRA subscription system.
    """

    def setUp(self):
        self.client = Client()

        # Ensure canonical plans exist
        self.free_plan = Plan.objects.filter(code='free').first()
        self.pro_plan = Plan.objects.filter(code='pro').first()
        self.ultra_plan = Plan.objects.filter(code='ultra').first()

        # Create test users
        self.free_user = User.objects.create_user(
            username='test_free_user',
            email='free@test.org',
            password='Password123!',
            is_staff=False,
            is_superuser=False
        )
        self.pro_user = User.objects.create_user(
            username='test_pro_user',
            email='pro@test.org',
            password='Password123!',
            is_staff=False,
            is_superuser=False
        )
        self.ultra_user = User.objects.create_user(
            username='test_ultra_user',
            email='ultra@test.org',
            password='Password123!',
            is_staff=False,
            is_superuser=False
        )
        self.admin_user = User.objects.create_user(
            username='test_admin_user',
            email='admin@test.org',
            password='Password123!',
            is_staff=True,
            is_superuser=True
        )

        # Attach subscriptions
        Subscription.objects.create(
            subscription_id='sub_test_free',
            user=self.free_user,
            tenant_id=f"user_{self.free_user.id}",
            plan_id='free',
            plan_record=self.free_plan,
            status='ACTIVE'
        )
        Subscription.objects.create(
            subscription_id='sub_test_pro',
            user=self.pro_user,
            tenant_id=f"user_{self.pro_user.id}",
            plan_id='pro',
            plan_record=self.pro_plan,
            status='ACTIVE'
        )
        Subscription.objects.create(
            subscription_id='sub_test_ultra',
            user=self.ultra_user,
            tenant_id=f"user_{self.ultra_user.id}",
            plan_id='ultra',
            plan_record=self.ultra_plan,
            status='ACTIVE'
        )

        # Create sample company & job & csr project
        self.company = Company.objects.create(
            company_id='COMP_TEST_001',
            company_name='Test Technologies Ltd',
            sector='Information Technology'
        )
        self.job = Job.objects.create(
            job_id='JOB_TEST_001',
            company=self.company,
            job_title='Sustainability Lead',
            department='ESG',
            status='ACTIVE'
        )
        self.csr_project = CSRProject.objects.create(
            csr_id='CSR_TEST_001',
            company=self.company,
            title='Rural Solar Clean Energy Project',
            category='Renewable Energy',
            status='ACTIVE'
        )

    # ── 1. Plan Catalog & Entitlements Tests ─────────────────────────
    def test_three_plans_catalog(self):
        """Verify that exactly 3 plans are active and visible."""
        active_plans = Plan.objects.filter(is_active=True, is_visible=True).order_by('display_order')
        codes = [p.code for p in active_plans]
        self.assertEqual(codes, ['free', 'pro', 'ultra'])
        self.assertEqual(self.free_plan.monthly_price_paise, 0)
        self.assertTrue(self.pro_plan.is_recommended)

    def test_entitlements_populated(self):
        """Verify that each active plan has exactly 16 dynamic comparison entitlements."""
        for plan in [self.free_plan, self.pro_plan, self.ultra_plan]:
            ents = PlanEntitlement.objects.filter(plan=plan)
            self.assertEqual(ents.count(), 16, f"Plan {plan.code} should have 16 entitlements")

    # ── 2. Saved Records Quota & Quota-Freeing Tests ─────────────────
    def test_free_user_saved_records_limit(self):
        """Free user can save up to 10 records. The 11th must be blocked."""
        svc = EntitlementService(self.free_user)
        self.assertEqual(svc.saved_records_limit, 10)

        # Create 10 dummy jobs and save them
        for i in range(10):
            j = Job.objects.create(
                job_id=f"JOB_FREE_{i}",
                company=self.company,
                job_title=f"Role {i}"
            )
            SavedRecord.objects.create(user=self.free_user, item_type='JOB', job=j)

        self.assertEqual(svc.saved_records_count, 10)

        # Attempting to save an 11th must raise EntitlementError
        with self.assertRaises(EntitlementError) as ctx:
            svc.check_can_save_record()
        self.assertIn("10/10 records", str(ctx.exception))

        # Deleting a record must immediately free up quota
        SavedRecord.objects.filter(user=self.free_user).first().delete()
        self.assertEqual(svc.saved_records_count, 9)
        # Now check_can_save_record should pass without error
        svc.check_can_save_record()

    def test_ultra_user_unlimited_saved_records(self):
        """Ultra user has unlimited saved records."""
        svc = EntitlementService(self.ultra_user)
        self.assertIsNone(svc.saved_records_limit)
        # Should never raise regardless of count
        svc.check_can_save_record()

    # ── 3. Saved Searches Quota Tests ────────────────────────────────
    def test_saved_searches_limits(self):
        """Free: 1, Pro: 10, Ultra: 50."""
        svc_free = EntitlementService(self.free_user)
        self.assertEqual(svc_free.saved_searches_limit, 1)

        svc_pro = EntitlementService(self.pro_user)
        self.assertEqual(svc_pro.saved_searches_limit, 10)

        svc_ultra = EntitlementService(self.ultra_user)
        self.assertEqual(svc_ultra.saved_searches_limit, 50)

    # ── 4. Monthly Export Quota Tests ────────────────────────────────
    def test_free_user_export_blocked(self):
        """Free user has 0 export allowance; check_export_quota must raise."""
        svc = EntitlementService(self.free_user)
        self.assertEqual(svc.monthly_export_limit, 0)
        with self.assertRaises(EntitlementError) as ctx:
            svc.check_export_quota(count=1)
        self.assertIn("Export is not available on the FREE plan", str(ctx.exception))

    def test_pro_user_export_quota_and_usage_tracking(self):
        """Pro user can export up to 200 rows per month with atomic counter tracking."""
        svc = EntitlementService(self.pro_user)
        self.assertEqual(svc.monthly_export_limit, 200)

        # First export 50 rows
        svc.check_export_quota(count=50)
        new_total = svc.record_export_usage(count=50)
        self.assertEqual(new_total, 50)
        self.assertEqual(svc.monthly_exports_used, 50)

        # Second export 100 rows
        svc.check_export_quota(count=100)
        new_total = svc.record_export_usage(count=100)
        self.assertEqual(new_total, 150)

        # Attempting to export 60 more (150 + 60 = 210 > 200) must raise EntitlementError
        with self.assertRaises(EntitlementError) as ctx:
            svc.check_export_quota(count=60)
        self.assertIn("150/200 used", str(ctx.exception))

    # ── 5. Team Members Quota Tests (Ultra Tier) ─────────────────────
    def test_team_members_limit(self):
        """Free & Pro allow 1 account member. Ultra allows up to 3 team members."""
        svc_free = EntitlementService(self.free_user)
        self.assertEqual(svc_free.team_members_limit, 1)
        with self.assertRaises(EntitlementError):
            svc_free.check_can_add_team_member()

        svc_ultra = EntitlementService(self.ultra_user)
        self.assertEqual(svc_ultra.team_members_limit, 3)
        # Ultra owner counts as 1. Adding member 2:
        svc_ultra.check_can_add_team_member()
        TeamMembership.objects.create(owner=self.ultra_user, invited_email='m1@test.org', status='ACTIVE')
        self.assertEqual(svc_ultra.active_team_members_count, 2)

        # Adding member 3:
        svc_ultra.check_can_add_team_member()
        TeamMembership.objects.create(owner=self.ultra_user, invited_email='m2@test.org', status='ACTIVE')
        self.assertEqual(svc_ultra.active_team_members_count, 3)

        # Adding a 4th member must be blocked:
        with self.assertRaises(EntitlementError) as ctx:
            svc_ultra.check_can_add_team_member()
        self.assertIn("Your plan supports 3 team member(s)", str(ctx.exception))

    # ── 6. Customer Downgrade Prevention Tests ────────────────────────
    def test_customer_downgrade_blocked_on_backend(self):
        """Direct call to /api/subscription/downgrade by non-admin must return 403."""
        self.client.force_login(self.pro_user)
        res = self.client.post(
            reverse('subscription_downgrade'),
            data=json.dumps({'plan_id': 'free'}),
            content_type='application/json'
        )
        self.assertEqual(res.status_code, 403)
        data = res.json()
        self.assertEqual(data.get('code'), 'downgrade_blocked')

    # ── 7. Dynamic Plan Comparison API Tests ─────────────────────────
    def test_dynamic_comparison_api(self):
        """GET /api/subscription/comparison returns 3 plans and 16 features from MySQL."""
        res = self.client.get(reverse('subscription_comparison'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['plans']), 3)
        self.assertEqual(len(data['features']), 16)

        # Verify free plan export is 0 and ultra is 2000
        export_row = next((f for f in data['features'] if f['feature_key'] == 'export_rows_per_month'), None)
        self.assertIsNotNone(export_row)
        self.assertEqual(export_row['values']['free']['value'], 0)
        self.assertEqual(export_row['values']['pro']['value'], 200)
        self.assertEqual(export_row['values']['ultra']['value'], 2000)

    # ── 8. User Quota Summary API Tests ──────────────────────────────
    def test_user_quota_api(self):
        """GET /api/user/quotas returns accurate real-time usage snapshot."""
        self.client.force_login(self.pro_user)
        res = self.client.get(reverse('user_quotas'))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data['status'], 'success')
        q = data['quota']
        self.assertEqual(q['tier'], 'pro')
        self.assertEqual(q['saved_records']['limit'], 100)
        self.assertEqual(q['monthly_exports']['limit'], 200)

    # ── 9. Preservation & Non-Destructive Invariance ──────────────────
    def test_legacy_plans_preserved(self):
        """Legacy plans starter, enterprise, foundation still exist in database."""
        for code in ['starter', 'enterprise', 'foundation']:
            plan = Plan.objects.filter(code=code).first()
            self.assertIsNotNone(plan, f"Legacy plan '{code}' must not be deleted!")
            self.assertFalse(plan.is_active)
            self.assertFalse(plan.is_visible)

