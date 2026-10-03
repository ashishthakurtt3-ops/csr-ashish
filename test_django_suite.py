import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from modules.admin_panel.models import (
    User, Company, Job, CSRProject, CSROpportunity,
    Contact, OpportunityScore, PageRecord, Document
)

def run_tests():
    print("=" * 70)
    print(" IMPACTBRIDGE DJANGO MIGRATION COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    passed = 0
    failed = 0

    def assert_true(cond, name, details=""):
        nonlocal passed, failed
        if cond:
            print(f" [PASS] {name} {details}")
            passed += 1
        else:
            print(f" [FAIL] {name} {details}")
            failed += 1

    # 1. Database Model Integrity
    print("\n--- 1. DATABASE MODEL & DATA INTEGRITY ---")
    comp_cnt = Company.objects.count()
    assert_true(comp_cnt >= 200, f"Companies Count", f"(Found: {comp_cnt})")
    
    job_cnt = Job.objects.count()
    assert_true(job_cnt >= 1800, f"Jobs Count", f"(Found: {job_cnt})")
    
    csr_cnt = CSRProject.objects.count()
    assert_true(csr_cnt >= 500, f"CSR Projects Count", f"(Found: {csr_cnt})")
    
    opp_cnt = CSROpportunity.objects.count()
    assert_true(opp_cnt >= 130, f"CSR Opportunities Count", f"(Found: {opp_cnt})")
    
    con_cnt = Contact.objects.count()
    assert_true(con_cnt >= 400, f"Contacts Count", f"(Found: {con_cnt})")
    
    score_cnt = OpportunityScore.objects.count()
    assert_true(score_cnt >= 200, f"Opportunity Scores Count", f"(Found: {score_cnt})")
    
    page_cnt = PageRecord.objects.count()
    assert_true(page_cnt >= 800, f"Page Crawl Records Count", f"(Found: {page_cnt})")
    
    admin_user = User.objects.filter(username='admin').first()
    assert_true(admin_user is not None and admin_user.is_superuser, "Admin Superuser Exists", f"(Role: {admin_user.role if admin_user else None})")

    # 2. Public Portal & API Endpoints
    print("\n--- 2. PUBLIC PORTAL & REST APIS ---")
    client = Client()

    res = client.get('/')
    assert_true(res.status_code == 200, "GET / (Homepage)", f"Status: {res.status_code}")

    res = client.get('/health')
    assert_true(res.status_code == 200 and res.json().get('status') == 'ok', "GET /health", f"Status: {res.status_code}")

    res = client.get('/stats')
    assert_true(res.status_code == 200 and res.json().get('total_companies') >= 200, "GET /stats", f"Total Companies in JSON: {res.json().get('total_companies')}")

    res = client.get('/search?q=Tata')
    s_results = res.json() if isinstance(res.json(), list) else res.json().get('results', [])
    assert_true(res.status_code == 200 and len(s_results) > 0, "GET /search?q=Tata", f"Results: {len(s_results)}")

    res = client.get('/companies?page=1&page_size=12')
    data = res.json()
    assert_true(res.status_code == 200 and data.get('total') == 200 and len(data.get('items', [])) == 12, "GET /companies pagination envelope", f"Total: {data.get('total')}, Page size: {len(data.get('items', []))}")

    first_comp = Company.objects.first()
    if first_comp:
        res = client.get(f'/companies/{first_comp.company_id}')
        assert_true(res.status_code == 200, f"GET /companies/{first_comp.company_id}", f"Company: {res.json().get('company_name')}")

    res = client.get('/jobs?page=1&page_size=12')
    jdata = res.json()
    assert_true(res.status_code == 200 and jdata.get('total') >= 1800, "GET /jobs pagination envelope", f"Total: {jdata.get('total')}")

    res = client.get('/jobs/summary')
    assert_true(res.status_code == 200, "GET /jobs/summary", f"Total roles summarized: {res.json().get('total_roles')}")

    res = client.get('/csr/projects?page=1&page_size=12')
    pdata = res.json()
    assert_true(res.status_code == 200 and pdata.get('total') >= 500, "GET /csr/projects", f"Total: {pdata.get('total')}")

    res = client.get('/csr/opportunities')
    assert_true(res.status_code == 200, "GET /csr/opportunities", f"Count: {len(res.json()) if isinstance(res.json(), list) else res.json().get('total')}")

    res = client.get('/ngo/matches?sector=Education')
    assert_true(res.status_code == 200, "GET /ngo/matches", f"Matches: {len(res.json()) if isinstance(res.json(), list) else len(res.json().get('matches', []))}")

    res = client.get('/prospects')
    prosp_len = len(res.json()) if isinstance(res.json(), list) else res.json().get('total', 0)
    assert_true(res.status_code == 200, "GET /prospects", f"Total prospects: {prosp_len}")

    res = client.get('/api/crawler/logs?page=1')
    assert_true(res.status_code == 200, "GET /api/crawler/logs", f"Total crawled: {res.json().get('total')}")

    res = client.get('/api/subscription/plans')
    assert_true(res.status_code == 200, "GET /api/subscription/plans", f"Status: {res.status_code}")

    # 3. Authentication & Protected User Flows
    print("\n--- 3. AUTHENTICATION & USER PORTAL ---")
    res = client.get('/login/')
    assert_true(res.status_code == 200, "GET /login/", f"Status: {res.status_code}")

    res = client.get('/register/')
    assert_true(res.status_code == 200, "GET /register/", f"Status: {res.status_code}")

    login_success = client.login(username='ngo_manager', password='Manager@12345')
    assert_true(login_success, "Client Login as 'ngo_manager'")

    res = client.get('/profile/')
    assert_true(res.status_code == 200, "GET /profile/ (authenticated)", f"Status: {res.status_code}")

    res = client.get('/documents/upload/')
    assert_true(res.status_code == 200, "GET /documents/upload/ (authenticated)", f"Status: {res.status_code}")

    client.logout()

    # 4. Admin Portal Architecture & Navigation
    print("\n--- 4. CUSTOM ENTERPRISE ADMIN CONSOLE ---")
    res = client.get('/admin-portal/')
    assert_true(res.status_code in (302, 403), "GET /admin-portal/ (unauthenticated redirects)", f"Status: {res.status_code}")

    res = client.get('/admin-portal/login/')
    assert_true(res.status_code == 200, "GET /admin-portal/login/", f"Status: {res.status_code}")

    admin_login = client.login(username='admin', password='Admin@12345')
    assert_true(admin_login, "Admin Login as 'admin' Superuser")

    res = client.get('/admin-portal/')
    assert_true(res.status_code == 200, "GET /admin-portal/ (Dashboard)", f"Status: {res.status_code}")

    res = client.get('/admin-portal/users/')
    assert_true(res.status_code == 200, "GET /admin-portal/users/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/users/create/')
    assert_true(res.status_code == 200, "GET /admin-portal/users/create/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/companies/')
    assert_true(res.status_code == 200, "GET /admin-portal/companies/", f"Status: {res.status_code}")

    if first_comp:
        res = client.get(f'/admin-portal/companies/{first_comp.company_id}/')
        assert_true(res.status_code == 200, f"GET /admin-portal/companies/{first_comp.company_id}/", f"Status: {res.status_code}")

        res = client.get(f'/admin-portal/companies/{first_comp.company_id}/edit/')
        assert_true(res.status_code == 200, f"GET /admin-portal/companies/{first_comp.company_id}/edit/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/jobs/')
    assert_true(res.status_code == 200, "GET /admin-portal/jobs/", f"Status: {res.status_code}")

    first_job = Job.objects.first()
    if first_job:
        res = client.get(f'/admin-portal/jobs/{first_job.job_row_id}/edit/')
        assert_true(res.status_code == 200, f"GET /admin-portal/jobs/{first_job.job_row_id}/edit/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/opportunities/')
    assert_true(res.status_code == 200, "GET /admin-portal/opportunities/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/opportunities/projects/')
    assert_true(res.status_code == 200, "GET /admin-portal/opportunities/projects/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/documents/')
    assert_true(res.status_code == 200, "GET /admin-portal/documents/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/documents/upload/')
    assert_true(res.status_code == 200, "GET /admin-portal/documents/upload/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/subscriptions/')
    assert_true(res.status_code == 200, "GET /admin-portal/subscriptions/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/subscriptions/invoices/')
    assert_true(res.status_code == 200, "GET /admin-portal/subscriptions/invoices/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/subscriptions/promos/')
    assert_true(res.status_code == 200, "GET /admin-portal/subscriptions/promos/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/verification/queue/')
    assert_true(res.status_code == 200, "GET /admin-portal/verification/queue/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/verification/audit-trail/')
    assert_true(res.status_code == 200, "GET /admin-portal/verification/audit-trail/", f"Status: {res.status_code}")

    res = client.get('/admin-portal/verification/crawler-status/')
    assert_true(res.status_code == 200, "GET /admin-portal/verification/crawler-status/", f"Status: {res.status_code}")

    print("\n" + "=" * 70)
    print(f" TEST RESULTS SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=" * 70)
    
    return failed == 0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
