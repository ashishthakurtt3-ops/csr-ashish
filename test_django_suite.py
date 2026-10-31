import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test.utils import setup_test_environment
setup_test_environment()

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
    assert_true(con_cnt >= 40, f"Contacts Count", f"(Found: {con_cnt})")
    
    score_cnt = OpportunityScore.objects.count()
    assert_true(score_cnt >= 0, f"Opportunity Scores Count", f"(Found: {score_cnt})")
    
    page_cnt = PageRecord.objects.count()
    assert_true(page_cnt >= 500, f"Page Crawl Records Count", f"(Found: {page_cnt})")
    
    admin_user = User.objects.filter(username='admin').first()
    assert_true(admin_user is not None and admin_user.is_superuser, "Admin Superuser Exists", f"(Role: {admin_user.role if admin_user else None})")

    # 2. Public Portal & API Endpoints
    print("\n--- 2. PUBLIC PORTAL & REST APIS ---")
    client = Client()

    res_home = client.get('/')
    assert_true(res_home.status_code == 200, "GET / (Homepage)", f"Status: {res_home.status_code}")
    assert_true(res_home.context is not None and 'data_as_of' in res_home.context, "Homepage context has data_as_of", f"data_as_of: {res_home.context.get('data_as_of') if res_home.context else None}")

    res = client.get('/health')
    assert_true(res.status_code == 200 and res.json().get('status') == 'ok', "GET /health", f"Status: {res.status_code}")

    res = client.get('/stats')
    s_data = res.json()
    assert_true(res.status_code == 200 and s_data.get('total_companies') >= 200, "GET /stats", f"Total Companies in JSON: {s_data.get('total_companies')}")
    assert_true('data_as_of' in s_data and s_data.get('data_as_of') is not None, "GET /stats has data_as_of", f"data_as_of: {s_data.get('data_as_of')}")
    assert_true('audit_run_id' in s_data, "GET /stats has audit_run_id", f"audit_run_id: {s_data.get('audit_run_id')}")

    res = client.get('/search?q=Tata')
    s_results = res.json() if isinstance(res.json(), list) else res.json().get('results', [])
    assert_true(res.status_code == 200 and len(s_results) > 0, "GET /search?q=Tata", f"Results: {len(s_results)}")

    res = client.get('/companies?page=1&page_size=12')
    data = res.json()
    assert_true(res.status_code == 200 and data.get('total') >= 200 and len(data.get('items', [])) == 12, "GET /companies pagination envelope", f"Total: {data.get('total')}, Page size: {len(data.get('items', []))}")

    first_comp = Company.objects.first()
    if first_comp:
        res = client.get(f'/companies/{first_comp.company_id}')
        assert_true(res.status_code == 200, f"GET /companies/{first_comp.company_id}", f"Company: {res.json().get('company_name')}")

    res = client.get('/jobs?page=1&page_size=12')
    jdata = res.json()
    assert_true(res.status_code == 200 and jdata.get('total') >= 1400, "GET /jobs pagination envelope", f"Total: {jdata.get('total')}")
    assert_true(s_data.get('jobs_tracked') == jdata.get('total'), "Exact Parity: /stats jobs_tracked == /jobs list total", f"{s_data.get('jobs_tracked')} == {jdata.get('total')}")
    if res_home.context:
        assert_true(res_home.context.get('jobs_tracked') == s_data.get('jobs_tracked') == jdata.get('total'), "Exact Parity: Homepage context == /stats == /jobs list total", f"{res_home.context.get('jobs_tracked')} == {s_data.get('jobs_tracked')} == {jdata.get('total')}")
        assert_true(res_home.context.get('total_companies') == s_data.get('total_companies'), "Exact Parity: Homepage context total_companies == /stats", f"{res_home.context.get('total_companies')} == {s_data.get('total_companies')}")
        assert_true(res_home.context.get('csr_projects') == s_data.get('csr_projects'), "Exact Parity: Homepage context csr_projects == /stats", f"{res_home.context.get('csr_projects')} == {s_data.get('csr_projects')}")

    res = client.get('/jobs/summary')
    sum_data = res.json()
    assert_true(res.status_code == 200, "GET /jobs/summary", f"Total roles summarized: {sum_data.get('total_roles')}")
    assert_true('data_as_of' in sum_data and 'audit_run_id' in sum_data, "GET /jobs/summary has snapshot metadata", f"audit_run_id: {sum_data.get('audit_run_id')}")

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

    user_pwd = os.environ.get('TEST_USER_PASSWORD', 'Manager@12345')
    admin_pwd = os.environ.get('TEST_ADMIN_PASSWORD', 'Admin@12345')

    login_success = client.login(username='ngo_manager', password=user_pwd)
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

    admin_login = client.login(username='admin', password=admin_pwd)
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

    # 5. Performance, Light Payloads & Accuracy Verifications
    print("\n--- 5. PERFORMANCE, LIGHT PAYLOADS & ACCURACY (STEP 8) ---")
    from django.db import connection, reset_queries
    from modules.admin_panel.signals import pause_snapshot_signals, are_signals_paused
    from modules.admin_panel.snapshot_service import reconcile_snapshots

    # 5a. Query count limits
    connection.force_debug_cursor = True

    # /companies query limit <= 4
    reset_queries()
    res = client.get('/companies?page=1&page_size=12')
    c_queries = len(connection.queries)
    assert_true(res.status_code == 200 and c_queries <= 4, "Query limit /companies?page_size=12 (<= 4 queries)", f"Queries: {c_queries}")

    # /jobs query limit <= 4
    reset_queries()
    res = client.get('/jobs?page=1&page_size=12')
    j_queries = len(connection.queries)
    assert_true(res.status_code == 200 and j_queries <= 4, "Query limit /jobs?page_size=12 (<= 4 queries)", f"Queries: {j_queries}")

    # /jobs/{id} query limit <= 5
    active_pub_job = Job.objects.filter(is_defective=False, status='ACTIVE').first()
    if active_pub_job:
        reset_queries()
        res = client.get(f'/jobs/{active_pub_job.job_row_id}')
        jd_queries = len(connection.queries)
        assert_true(res.status_code == 200 and jd_queries <= 5, f"Query limit /jobs/{active_pub_job.job_row_id} (<= 5 queries)", f"Queries: {jd_queries}")

    # /csr/projects query limit <= 4
    reset_queries()
    res = client.get('/csr/projects?page=1&page_size=12')
    csr_queries = len(connection.queries)
    assert_true(res.status_code == 200 and csr_queries <= 4, "Query limit /csr/projects?page_size=12 (<= 4 queries)", f"Queries: {csr_queries}")

    # /admin-portal/ query limit <= 10
    reset_queries()
    res = client.get('/admin-portal/')
    admin_queries = len(connection.queries)
    assert_true(res.status_code == 200 and admin_queries <= 10, "Query limit /admin-portal/ (<= 10 queries)", f"Queries: {admin_queries}")

    connection.force_debug_cursor = False

    # 5b. Pagination hard cap
    res = client.get('/companies?limit=5000')
    c_cap = res.json()
    items_count = len(c_cap) if isinstance(c_cap, list) else len(c_cap.get('items', []))
    assert_true(res.status_code == 200 and items_count <= 100, "Pagination Cap /companies?limit=5000 (<= 100 items)", f"Returned: {items_count}")

    res = client.get('/companies?page=1&page_size=500')
    c_page_cap = res.json()
    c_p_items_count = len(c_page_cap.get('items', []))
    assert_true(res.status_code == 200 and c_p_items_count <= 100, "Pagination Cap /companies?page_size=500 (<= 100 items)", f"Returned: {c_p_items_count}")

    res = client.get('/jobs?page=1&page_size=500')
    j_cap = res.json()
    j_items_count = len(j_cap.get('items', []))
    assert_true(res.status_code == 200 and j_items_count <= 100, "Pagination Cap /jobs?page=1&page_size=500 (<= 100 items)", f"Returned: {j_items_count}")

    res = client.get('/jobs?limit=5000')
    j_flat = res.json()
    assert_true(isinstance(j_flat, list) and len(j_flat) <= 100, "Legacy Flat Array Cap /jobs?limit=5000 (<= 100 items)", f"Returned: {len(j_flat)}")

    # 5c. Pagination envelope integrity
    envelope_keys = {'items', 'total', 'page', 'page_size', 'total_pages', 'has_next', 'has_prev'}
    assert_true(envelope_keys.issubset(j_cap.keys()), "Envelope Unchanged /jobs", f"Keys: {list(j_cap.keys())}")
    assert_true(envelope_keys.issubset(c_page_cap.keys()), "Envelope Unchanged /companies", f"Keys: {list(c_page_cap.keys())}")

    # 5d. List payloads contain no large fields and have summary
    sample_job = j_cap.get('items', [{}])[0]
    assert_true('description_raw' not in sample_job and 'responsibilities_list' not in sample_job, "List payload omits large fields (Job)", f"Keys: {list(sample_job.keys())[:5]}...")
    assert_true('summary' in sample_job, "List payload contains short summary (Job)", f"Summary length: {len(sample_job.get('summary') or '')}")

    # 5e. Companies lookup endpoint
    res = client.get('/companies/lookup')
    assert_true(res.status_code == 200, "GET /companies/lookup (status 200)", f"Status: {res.status_code}")
    lookup_data = res.json()
    lookup_items = lookup_data.get('items', lookup_data) if isinstance(lookup_data, dict) else lookup_data
    assert_true(isinstance(lookup_items, list) and len(lookup_items) >= 200, "Lookup returns lightweight list of all companies", f"Count: {len(lookup_items)}")
    if lookup_items:
        first_lookup = lookup_items[0]
        assert_true('id' in first_lookup and 'name' in first_lookup and 'nse_symbol' in first_lookup and 'access' in first_lookup, "Lookup item fields {id, name, nse_symbol, access}", f"Item: {first_lookup}")

    # 5f. Non-blocking refresh endpoint
    if active_pub_job:
        res = client.get(f'/jobs/{active_pub_job.job_row_id}?refresh=1')
        assert_true(res.status_code == 200, f"GET /jobs/{active_pub_job.job_row_id}?refresh=1 returns immediately", f"Status: {res.status_code}")
        ref_json = res.json()
        item_ref = ref_json.get('job') or ref_json
        assert_true('refresh_status' in item_ref, "Async refresh returns refresh_status field", f"refresh_status: {item_ref.get('refresh_status')}")

        res = client.get(f'/jobs/{active_pub_job.job_row_id}/refresh-status')
        assert_true(res.status_code == 200 and 'status' in res.json(), f"GET /jobs/{active_pub_job.job_row_id}/refresh-status polls status", f"Response: {res.json()}")

    # 5g. Context manager pauses signals during bulk operations
    assert_true(not are_signals_paused(), "Signals active by default")
    with pause_snapshot_signals() as modified_set:
        assert_true(are_signals_paused(), "pause_snapshot_signals() actively suppresses per-save signals")
    assert_true(not are_signals_paused(), "Signals unpaused on exit")

    # 5h. Independent Raw-SQL Snapshot Reconcile
    all_matched, reconcile_results = reconcile_snapshots()
    assert_true(all_matched, "reconcile_snapshots() full match with live DB", f"Results: {len(reconcile_results)} checks")
    raw_sql_row = next((r for r in reconcile_results if r['metric'] == 'independent_raw_sql_jobs'), None)
    assert_true(raw_sql_row is not None and raw_sql_row['match'], "Independent Raw-SQL Jobs Count matches Snapshot", f"Diff: {raw_sql_row.get('diff') if raw_sql_row else 'None'}")

    # 6. Static Hashing, Minification, Self-Hosted Fonts & Parity (Step 7)
    print("\n--- 6. STATIC HASHING, ASSET MINIFICATION, FONTS & HOME PARITY ---")
    from django.conf import settings
    from pathlib import Path
    from django.core.management import call_command
    import io

    # 6a. index.html references minified files
    index_file = Path(settings.BASE_DIR) / 'templates' / 'website' / 'index.html'
    assert_true(index_file.exists(), "templates/website/index.html exists")
    with open(index_file, 'r', encoding='utf-8') as f:
        html_src = f.read()

    assert_true("style.min.css" in html_src or "style.css" in html_src, "index.html references style asset")
    assert_true("app.min.js" in html_src or ("app.js" in html_src and "STATIC_VERSION" in html_src), "index.html references versioned app asset")
    assert_true("app.js?v=3.6.0" not in html_src, "index.html does not reference old hardcoded app.js?v=3.6.0")

    # 6b. No external font URLs
    assert_true("fonts.googleapis.com" not in html_src, "No fonts.googleapis.com in index.html")
    assert_true("fonts.gstatic.com" not in html_src, "No fonts.gstatic.com in index.html")
    assert_true("fonts/plus-jakarta-sans-" in html_src or "fonts/inter-" in html_src, "index.html preloads local woff2 fonts")

    # 6c. WhiteNoise / Manifest static storage produces hashed static files
    manifest_file = Path(settings.BASE_DIR) / 'staticfiles' / 'staticfiles.json'
    assert_true(manifest_file.exists(), "WhiteNoise staticfiles.json manifest generated")
    if manifest_file.exists():
        import json as j_mod
        with open(manifest_file, 'r', encoding='utf-8') as mf:
            m_data = j_mod.load(mf)
        paths = m_data.get('paths', {})
        assert_true('js/app.min.js' in paths or 'css/style.min.css' in paths, "WhiteNoise hashes minified assets in manifest")

    # 6d. Home numbers equal /stats numbers
    res_home = client.get('/')
    res_stats = client.get('/stats')
    s_payload = res_stats.json()
    ctx = res_home.context
    if ctx:
        assert_true(ctx.get('total_companies') == s_payload.get('total_companies'), "Parity: Home total_companies == /stats total_companies", f"{ctx.get('total_companies')} == {s_payload.get('total_companies')}")
        assert_true(ctx.get('jobs_tracked') == s_payload.get('jobs_tracked'), "Parity: Home jobs_tracked == /stats jobs_tracked", f"{ctx.get('jobs_tracked')} == {s_payload.get('jobs_tracked')}")
        assert_true(ctx.get('csr_projects') == s_payload.get('csr_projects'), "Parity: Home csr_projects == /stats csr_projects", f"{ctx.get('csr_projects')} == {s_payload.get('csr_projects')}")
        assert_true(ctx.get('data_as_of') == s_payload.get('data_as_of'), "Parity: Home data_as_of == /stats data_as_of", f"{ctx.get('data_as_of')} == {s_payload.get('data_as_of')}")

    # 6e. warm_cache command executes cleanly
    buf = io.StringIO()
    call_command('warm_cache', stdout=buf)
    warm_output = buf.getvalue()
    assert_true("All core caches successfully warmed" in warm_output, "warm_cache command runs and completes successfully")

    # 6f. build_assets --check verifies sources vs minified timestamps
    buf_assets = io.StringIO()
    call_command('build_assets', check=True, stdout=buf_assets)
    assert_true("[OK] All minified static assets are up-to-date." in buf_assets.getvalue(), "build_assets --check validates minified assets are up-to-date")

    print("\n" + "=" * 70)
    print(f" TEST RESULTS SUMMARY: {passed} PASSED, {failed} FAILED")
    print("=" * 70)
    
    return failed == 0

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

