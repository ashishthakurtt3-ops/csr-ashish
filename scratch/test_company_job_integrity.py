import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()


from django.test import RequestFactory
from modules.admin_panel.models import Company, Job
from modules.website.views.job_api_views import jobs_list_api
import json

def test_company_job_integrity():
    rf = RequestFactory()
    total_companies = Company.objects.count()
    print(f"Total companies in registry: {total_companies}")
    
    mismatches = []
    jobs_checked = 0

    for comp in Company.objects.all():
        # Query jobs directly via ORM
        orm_jobs = list(comp.jobs.all())
        orm_count = len(orm_jobs)

        # Query jobs via Company Jobs API
        req = rf.get(f"/jobs?company_id={comp.company_id}&page_size=100")
        resp = jobs_list_api(req)
        api_data = json.loads(resp.content)
        api_total = api_data.get('total', 0) if isinstance(api_data, dict) else len(api_data)

        if orm_count != api_total:
            mismatches.append(f"Mismatch for {comp.company_id} ({comp.company_name}): ORM={orm_count}, API={api_total}")

        # Verify each job's company_id == company.company_id
        for j in orm_jobs:
            jobs_checked += 1
            if j.company_id != comp.company_id:
                mismatches.append(f"Job {j.job_id} company_id ({j.company_id}) != {comp.company_id}")

    print(f"Verified {jobs_checked} jobs across {total_companies} companies.")
    if mismatches:
        print("FAILURES DETECTED:")
        for m in mismatches[:10]:
            print(" -", m)
        return False
    else:
        print("INTEGRITY VERIFIED: 100% of jobs and APIs match Company primary key and counts.")
        return True

if __name__ == '__main__':
    success = test_company_job_integrity()
    if not success:
        sys.exit(1)
