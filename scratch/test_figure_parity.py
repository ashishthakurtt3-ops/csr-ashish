import os
import sys
import json
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from modules.website.views.job_api_views import jobs_list_api
from modules.website.views.company_api_views import companies_list_api
from modules.website.views.opportunity_api_views import csr_projects_api
from modules.admin_panel.snapshot_service import get_current_stats_snapshot

def test_parity():
    rf = RequestFactory()
    snap, _, _, _ = get_current_stats_snapshot()

    # /jobs
    req = rf.get('/jobs?page=1&page_size=12')
    resp = jobs_list_api(req)
    data = json.loads(resp.content)
    jobs_total = data['total']

    # /companies
    req = rf.get('/companies?page=1&page_size=12')
    resp = companies_list_api(req)
    data = json.loads(resp.content)
    companies_total = data['total']

    # /csr/projects
    req = rf.get('/csr/projects?page=1&page_size=12')
    resp = csr_projects_api(req)
    data = json.loads(resp.content)
    csr_total = data['total']

    print(f"Jobs: Snapshot={snap['jobs_tracked']}, API={jobs_total}, Match={snap['jobs_tracked'] == jobs_total}")
    print(f"Companies: Snapshot={snap['total_companies']}, API={companies_total}, Match={snap['total_companies'] == companies_total}")
    print(f"CSR Projects: Snapshot={snap['csr_projects']}, API={csr_total}, Match={snap['csr_projects'] == csr_total}")
    assert snap['jobs_tracked'] == jobs_total
    assert snap['total_companies'] == companies_total
    assert snap['csr_projects'] == csr_total
    print("ALL PARITY CHECKS PASSED!")

if __name__ == '__main__':
    test_parity()
