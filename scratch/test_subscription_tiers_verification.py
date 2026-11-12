import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from modules.admin_panel.models import Plan, PlanEntitlement, User, Subscription, Company
from modules.website.utils.entitlement_service import EntitlementService, EntitlementError
from django.test import RequestFactory
from modules.website.views.company_api_views import companies_list_api
from modules.website.views.crawler_api_views import recheck_company_domain_api
import json

def run_tests():
    print("==================================================")
    print("SUBSCRIPTION TIERS & ADMIN CONFIG VERIFICATION")
    print("==================================================")

    # 1. Verify Plan limits in DB
    print("\n--- 1. Checking Database Plan Specs ---")
    free = Plan.objects.get(code='free')
    pro = Plan.objects.get(code='pro')
    ultra = Plan.objects.get(code='ultra')

    print(f"FREE: limits={free.limits}, trial_days={free.trial_days}")
    assert free.limits.get('browse_companies_limit') == 20, f"Expected 20, got {free.limits.get('browse_companies_limit')}"
    assert free.limits.get('saved_records_limit') == 20, f"Expected 20, got {free.limits.get('saved_records_limit')}"
    assert free.limits.get('export_rows_per_month') == 20, f"Expected 20, got {free.limits.get('export_rows_per_month')}"
    assert free.limits.get('request_company_refresh') is False
    assert free.trial_days == 14

    print(f"PRO: limits={pro.limits}, trial_days={pro.trial_days}")
    assert pro.limits.get('browse_companies_limit') == 100
    assert pro.limits.get('saved_records_limit') == 100
    assert pro.limits.get('export_rows_per_month') == 100
    assert pro.limits.get('request_company_refresh') is True
    assert pro.trial_days == 0

    print(f"ULTRA: limits={ultra.limits}, trial_days={ultra.trial_days}")
    assert ultra.limits.get('browse_companies_limit') is None
    assert ultra.limits.get('saved_records_limit') is None
    assert ultra.limits.get('export_rows_per_month') is None
    assert ultra.limits.get('request_company_refresh') is True
    assert ultra.trial_days == 0

    print(" Plan DB limits verified successfully.")

    # 2. Verify EntitlementService behavior per Tier
    print("\n--- 2. Checking EntitlementService per Tier ---")
    # Test user
    test_user, _ = User.objects.get_or_create(username='test_tier_user', defaults={'email': 'test@tier.com'})

    # Free subscription
    sub, _ = Subscription.objects.update_or_create(
        user=test_user,
        defaults={
            'subscription_id': 'sub_test_tier',
            'tenant_id': f"user_{test_user.id}",
            'plan_id': 'free',
            'plan_record': free,
            'status': 'TRIALING',
        }
    )

    svc_free = EntitlementService(test_user)
    print(f"Free user svc.browse_companies_limit = {svc_free.browse_companies_limit}")
    assert svc_free.browse_companies_limit == 20
    print(f"Free user svc.saved_records_limit = {svc_free.saved_records_limit}")
    assert svc_free.saved_records_limit == 20
    print(f"Free user svc.monthly_export_limit = {svc_free.monthly_export_limit}")
    assert svc_free.monthly_export_limit == 20
    try:
        svc_free.check_can_request_refresh()
        assert False, "Free user should NOT be able to request crawler rescan"
    except EntitlementError as e:
        print(f"Free crawler rescan blocked as expected: {e.message}")

    # Upgrade to Pro
    sub.plan_id = 'pro'
    sub.plan_record = pro
    sub.status = 'ACTIVE'
    sub.save()

    svc_pro = EntitlementService(test_user)
    print(f"Pro user svc.browse_companies_limit = {svc_pro.browse_companies_limit}")
    assert svc_pro.browse_companies_limit == 100
    print(f"Pro user svc.saved_records_limit = {svc_pro.saved_records_limit}")
    assert svc_pro.saved_records_limit == 100
    print(f"Pro user svc.monthly_export_limit = {svc_pro.monthly_export_limit}")
    assert svc_pro.monthly_export_limit == 100
    svc_pro.check_can_request_refresh()
    print("Pro crawler rescan permitted as expected.")

    # Upgrade to Ultra
    sub.plan_id = 'ultra'
    sub.plan_record = ultra
    sub.save()

    svc_ultra = EntitlementService(test_user)
    print(f"Ultra user svc.browse_companies_limit = {svc_ultra.browse_companies_limit} (Unlimited)")
    assert svc_ultra.browse_companies_limit is None
    print(f"Ultra user svc.saved_records_limit = {svc_ultra.saved_records_limit} (Unlimited)")
    assert svc_ultra.saved_records_limit is None
    print(f"Ultra user svc.monthly_export_limit = {svc_ultra.monthly_export_limit} (Unlimited)")
    assert svc_ultra.monthly_export_limit is None
    svc_ultra.check_can_request_refresh()
    print("Ultra crawler rescan permitted as expected.")

    # 3. Test Company Directory Browse API limit
    print("\n--- 3. Testing Company Directory Browse API Limit ---")
    factory = RequestFactory()

    # Free user request
    sub.plan_id = 'free'
    sub.plan_record = free
    sub.status = 'TRIALING'
    sub.save()

    req_free = factory.get('/companies/?page=1&page_size=12', HTTP_HOST='127.0.0.1')
    req_free.user = test_user
    resp_free = companies_list_api(req_free)
    data_free = json.loads(resp_free.content)

    print(f"Free user companies API response: total={data_free.get('total')}, page_size={data_free.get('page_size')}, plan_browse_limit={data_free.get('plan_browse_limit')}")
    assert data_free.get('plan_browse_limit') == 20
    assert data_free.get('total') <= 20
    assert data_free.get('total_pages') == 2

    # Pro user request
    sub.plan_id = 'pro'
    sub.plan_record = pro
    sub.status = 'ACTIVE'
    sub.save()

    req_pro = factory.get('/companies/?page=1&page_size=12', HTTP_HOST='127.0.0.1')
    req_pro.user = test_user
    resp_pro = companies_list_api(req_pro)
    data_pro = json.loads(resp_pro.content)

    print(f"Pro user companies API response: total={data_pro.get('total')}, plan_browse_limit={data_pro.get('plan_browse_limit')}")
    assert data_pro.get('plan_browse_limit') == 100

    # 4. Test Crawler Rescan Endpoint Permission Gate
    print("\n--- 4. Testing Crawler Rescan Endpoint Permission Gate ---")
    comp = Company.objects.first()
    if comp:
        # Free user POST
        sub.plan_id = 'free'
        sub.plan_record = free
        sub.save()

        req_rescan_free = factory.post(f'/api/crawler/companies/{comp.company_id}/recheck', HTTP_HOST='127.0.0.1')
        req_rescan_free.user = test_user
        resp_rescan_free = recheck_company_domain_api(req_rescan_free, comp.company_id)
        assert resp_rescan_free.status_code == 403, f"Expected 403, got {resp_rescan_free.status_code}"
        print(f"Free user rescan blocked with 403: {json.loads(resp_rescan_free.content).get('detail')}")

        # Pro user POST
        sub.plan_id = 'pro'
        sub.plan_record = pro
        sub.save()

        req_rescan_pro = factory.post(f'/api/crawler/companies/{comp.company_id}/recheck', HTTP_HOST='127.0.0.1')
        req_rescan_pro.user = test_user
        resp_rescan_pro = recheck_company_domain_api(req_rescan_pro, comp.company_id)
        assert resp_rescan_pro.status_code == 202, f"Expected 202 (Accepted), got {resp_rescan_pro.status_code}"
        print(f"Pro user rescan accepted with 202: {json.loads(resp_rescan_pro.content).get('status')}")
        print(f"Pro user rescan accepted with 200: {json.loads(resp_rescan_pro.content).get('status')}")

    # 5. Verify Admin UI template cleanliness
    print("\n--- 5. Checking Template Cleanliness ---")
    with open('templates/admin/base_admin.html', 'r', encoding='utf-8') as f:
        base_html = f.read()
    assert 'User Wallets' not in base_html, "User Wallets should not be in sidebar"
    assert 'Promo Codes' not in base_html, "Promo Codes should not be in sidebar"
    print(" base_admin.html verified clean of wallets & promo codes in sidebar.")

    with open('templates/admin/subscriptions/list.html', 'r', encoding='utf-8') as f:
        list_html = f.read()
    assert 'Run Renewals' not in list_html, "Run Renewals button should not be in list.html"
    assert 'Customer Escrow Reserve' not in list_html, "Customer Escrow Reserve should not be in list.html"
    print(" list.html verified clean of renewal button and escrow reserve.")

    with open('templates/admin/subscriptions/plan_form.html', 'r', encoding='utf-8') as f:
        form_html = f.read()
    assert 'field-limit_browse_companies' in form_html, "Browse companies limit input must be present"
    assert 'On-Demand Company Crawler Rescan (Refresh)' in form_html
    assert 'Wallet Deduction' not in form_html
    print(" plan_form.html verified with browse companies input and clean layout.")

    # Clean up test user & sub
    sub.delete()
    test_user.delete()

    print("\n==================================================")
    print("ALL TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
