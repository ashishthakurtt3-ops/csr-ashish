import json
from django.core.management.base import BaseCommand
from django.test import Client
from django.db import transaction
from django.contrib.auth import get_user_model
from django.urls import reverse
from modules.admin_panel.models import (
    Plan, PlanEntitlement, Subscription, UsageCounter,
    SavedRecord, SavedSearch, TeamMembership, CompanyRefreshRequest,
    Company, Job, CSRProject
)
from modules.website.utils.entitlement_service import EntitlementService, EntitlementError

User = get_user_model()


class Command(BaseCommand):
    help = 'Run comprehensive live test suite for the three-tier subscription system with rollback'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Starting Three-Tier Subscription Test Suite..."))
        passed = 0
        failed = 0

        def assert_true(condition, msg):
            nonlocal passed, failed
            if condition:
                passed += 1
                self.stdout.write(self.style.SUCCESS(f"  [PASS] {msg}"))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f"  [FAIL] {msg}"))

        # Run inside atomic block with rollback to avoid database pollution
        try:
            with transaction.atomic():
                # ── 1. Plan Catalog Tests ──────────────────────────────
                active_plans = list(Plan.objects.filter(is_active=True, is_visible=True).order_by('display_order'))
                codes = [p.code for p in active_plans]
                assert_true(codes == ['free', 'pro', 'ultra'], f"Exactly 3 active plans exist: {codes}")

                free_plan = Plan.objects.get(code='free')
                pro_plan = Plan.objects.get(code='pro')
                ultra_plan = Plan.objects.get(code='ultra')

                assert_true(free_plan.monthly_price_paise == 0, f"FREE plan price is Rs 0 (got {free_plan.monthly_price_paise})")
                assert_true(pro_plan.is_recommended, "PRO plan has is_recommended=True")
                assert_true(ultra_plan.badge == 'TEAMS & ORG', f"ULTRA plan has badge 'TEAMS & ORG' (got {ultra_plan.badge})")

                # ── 2. Entitlements Verification ───────────────────────
                for p in [free_plan, pro_plan, ultra_plan]:
                    count = PlanEntitlement.objects.filter(plan=p).count()
                    assert_true(count == 16, f"Plan {p.code} has exactly 16 entitlements (got {count})")

                # Verify dynamic limits stored in database
                assert_true(free_plan.limits.get('saved_records_limit') == 10, "FREE saved_records_limit == 10")
                assert_true(free_plan.limits.get('saved_searches_limit') == 1, "FREE saved_searches_limit == 1")
                assert_true(free_plan.limits.get('export_rows_per_month') == 0, "FREE export_rows_per_month == 0")
                assert_true(free_plan.limits.get('seats') == 1, "FREE seats == 1")

                assert_true(pro_plan.limits.get('saved_records_limit') == 100, "PRO saved_records_limit == 100")
                assert_true(pro_plan.limits.get('saved_searches_limit') == 10, "PRO saved_searches_limit == 10")
                assert_true(pro_plan.limits.get('export_rows_per_month') == 200, "PRO export_rows_per_month == 200")
                assert_true(pro_plan.limits.get('compare_companies_limit') == 10, "PRO compare_companies_limit == 10")

                assert_true(ultra_plan.limits.get('saved_records_limit') is None, "ULTRA saved_records_limit is Unlimited (None)")
                assert_true(ultra_plan.limits.get('saved_searches_limit') == 50, "ULTRA saved_searches_limit == 50")
                assert_true(ultra_plan.limits.get('export_rows_per_month') == 2000, "ULTRA export_rows_per_month == 2000")
                assert_true(ultra_plan.limits.get('seats') == 3, "ULTRA seats == 3")
                assert_true(ultra_plan.limits.get('request_company_refresh') is True, "ULTRA request_company_refresh == True")

                # ── 3. Test Users & Subscription Creation ──────────────
                user_free = User.objects.create_user(username='t_free_usr', email='free@t.org', password='pwd')
                user_pro = User.objects.create_user(username='t_pro_usr', email='pro@t.org', password='pwd')
                user_ultra = User.objects.create_user(username='t_ultra_usr', email='ultra@t.org', password='pwd')

                Subscription.objects.create(subscription_id='sub_tf', user=user_free, tenant_id='ten_f', plan_id='free', plan_record=free_plan, status='ACTIVE')
                Subscription.objects.create(subscription_id='sub_tp', user=user_pro, tenant_id='ten_p', plan_id='pro', plan_record=pro_plan, status='ACTIVE')
                Subscription.objects.create(subscription_id='sub_tu', user=user_ultra, tenant_id='ten_u', plan_id='ultra', plan_record=ultra_plan, status='ACTIVE')

                # ── 4. Entitlement Service: Saved Records Quota ────────
                svc_free = EntitlementService(user_free)
                svc_pro = EntitlementService(user_pro)
                svc_ultra = EntitlementService(user_ultra)

                assert_true(svc_free.saved_records_limit == 10, "EntitlementService resolved FREE limit = 10")
                assert_true(svc_pro.saved_records_limit == 100, "EntitlementService resolved PRO limit = 100")
                assert_true(svc_ultra.saved_records_limit is None, "EntitlementService resolved ULTRA limit = None (Unlimited)")

                # Create test company and job
                comp = Company.objects.first() or Company.objects.create(company_id='C_TEST_99', company_name='Sample Co')
                job = Job.objects.first() or Job.objects.create(job_id='J_TEST_99', company=comp, job_title='Sample Job')

                # Save 10 records for free user
                for i in range(10):
                    SavedRecord.objects.create(user=user_free, item_type='JOB', job=job, notes=f"Note {i}")

                assert_true(svc_free.saved_records_count == 10, "Free user has 10 saved records")

                # 11th save must raise EntitlementError
                threw_quota_err = False
                try:
                    svc_free.check_can_save_record()
                except EntitlementError as e:
                    threw_quota_err = True
                    assert_true('10/10' in e.message, f"EntitlementError message includes '10/10': {e.message}")
                assert_true(threw_quota_err, "Free user blocked from saving 11th record")

                # Delete one record -> quota freed immediately!
                SavedRecord.objects.filter(user=user_free).first().delete()
                assert_true(svc_free.saved_records_count == 9, "Deleting record freed quota (count=9)")
                can_save_now = True
                try:
                    svc_free.check_can_save_record()
                except EntitlementError:
                    can_save_now = False
                assert_true(can_save_now, "Free user can save again after deleting an item")

                # ── 5. Entitlement Service: Monthly Export Quota ───────
                # Free user has 0 exports
                free_export_blocked = False
                try:
                    svc_free.check_export_quota(count=1)
                except EntitlementError:
                    free_export_blocked = True
                assert_true(free_export_blocked, "Free user export is strictly blocked (limit=0)")

                # Pro user has 200 exports
                assert_true(svc_pro.monthly_export_limit == 200, "Pro user monthly export limit is 200")
                svc_pro.check_export_quota(count=50)
                used1 = svc_pro.record_export_usage(count=50)
                assert_true(used1 == 50, f"Recorded 50 export rows (got {used1})")
                assert_true(svc_pro.monthly_exports_used == 50, f"UsageCounter shows 50 used (got {svc_pro.monthly_exports_used})")

                # Try exporting 160 more (50 + 160 = 210 > 200) -> must raise
                pro_over_quota = False
                try:
                    svc_pro.check_export_quota(count=160)
                except EntitlementError as e:
                    pro_over_quota = True
                    assert_true('50/200' in e.message, f"Quota error mentions '50/200': {e.message}")
                assert_true(pro_over_quota, "Pro user blocked from exceeding 200 monthly exports")

                # ── 6. Team Membership Limit (Ultra Tier) ──────────────
                assert_true(svc_free.team_members_limit == 1, "Free team seats == 1")
                assert_true(svc_ultra.team_members_limit == 3, "Ultra team seats == 3 (owner + 2 members)")

                # Ultra user adding 2 team members
                TeamMembership.objects.create(owner=user_ultra, invited_email='m1@corp.org', status='ACTIVE')
                TeamMembership.objects.create(owner=user_ultra, invited_email='m2@corp.org', status='ACTIVE')
                assert_true(svc_ultra.active_team_members_count == 3, "Ultra active team count == 3 (owner + 2)")

                ultra_team_blocked = False
                try:
                    svc_ultra.check_can_add_team_member()
                except EntitlementError:
                    ultra_team_blocked = True
                assert_true(ultra_team_blocked, "Adding 4th team member on Ultra is blocked")

                # ── 7. Client API Tests ────────────────────────────────
                client = Client()

                # Dynamic comparison API
                res = client.get('/api/subscription/comparison')
                assert_true(res.status_code == 200, f"/api/subscription/comparison returned 200 (got {res.status_code})")
                data = json.loads(res.content)
                assert_true(len(data.get('plans', [])) == 3, f"Comparison API returned 3 plans (got {len(data.get('plans', []))})")
                assert_true(len(data.get('features', [])) == 16, f"Comparison API returned 16 features (got {len(data.get('features', []))})")

                # User quota API for Pro user
                client.force_login(user_pro)
                res_q = client.get('/api/user/quotas')
                assert_true(res_q.status_code == 200, f"/api/user/quotas returned 200")
                qdata = json.loads(res_q.content).get('quota', {})
                assert_true(qdata.get('tier') == 'pro', f"Quota tier is 'pro' (got {qdata.get('tier')})")
                assert_true(qdata.get('monthly_exports', {}).get('used') == 50, f"Quota monthly exports used == 50")

                # Downgrade block: calling downgrade as regular customer returns 403
                res_down = client.post('/api/subscription/downgrade', json.dumps({'plan_id': 'free'}), content_type='application/json')
                assert_true(res_down.status_code == 403, f"Customer downgrade returned 403 Forbidden (got {res_down.status_code})")
                assert_true(json.loads(res_down.content).get('code') == 'downgrade_blocked', "Error code is 'downgrade_blocked'")

                # Legacy plans preservation check
                for leg_code in ['starter', 'enterprise', 'foundation']:
                    leg_p = Plan.objects.filter(code=leg_code).first()
                    assert_true(leg_p is not None, f"Legacy plan '{leg_code}' preserved in database")
                    assert_true(not leg_p.is_active and not leg_p.is_visible, f"Legacy plan '{leg_code}' is archived (inactive/hidden)")

                # Trigger rollback so test data doesn't persist
                transaction.set_rollback(True)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Exception during test run: {e}"))
            import traceback
            traceback.print_exc()

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Three-Tier Subscription Test Results:"))
        self.stdout.write(self.style.SUCCESS(f"  Passed: {passed}"))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f"  Failed: {failed}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"  All {passed} checks passed successfully!"))

