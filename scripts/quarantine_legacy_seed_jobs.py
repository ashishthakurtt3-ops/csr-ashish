"""
Quarantine Legacy Seed Jobs & Nullify Synthetic Salary Data
===========================================================
Strict Data Integrity Enforcement:
1. Quarantines all legacy seed jobs (REQ-*) to verification_status='LEGACY_UNVERIFIED' and status='INACTIVE'.
2. Purges all fabricated synthetic salary figures (sets salary, salary_min, salary_max to NULL).
3. Ensures only genuine source-extracted jobs (JOB_*) remain in the active published pool.
"""
import os
import sys
import django

BASE_DIR = r"D:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from modules.admin_panel.models import Job, Company

def quarantine_seed_jobs():
    print("=" * 80)
    print("QUARANTINING LEGACY SYNTHETIC SEED JOBS")
    print("=" * 80)

    # 1. Inspect existing state
    total_jobs = Job.objects.count()
    req_jobs = Job.objects.filter(job_id__startswith='REQ')
    active_req_jobs = req_jobs.filter(status='ACTIVE')
    jobs_with_salary = Job.objects.filter(salary__isnull=False).exclude(salary='')

    print(f"Total jobs in DB: {total_jobs}")
    print(f"Total REQ- seed jobs: {req_jobs.count()}")
    print(f"Currently active REQ- seed jobs: {active_req_jobs.count()}")
    print(f"Jobs with synthetic salary populated: {jobs_with_salary.count()}")

    # 2. Nullify all synthetic salaries across all jobs
    cleared_salaries = jobs_with_salary.update(
        salary=None,
        salary_min=None,
        salary_max=None,
        salary_currency=None
    )
    print(f"Successfully purged synthetic salary data on {cleared_salaries} jobs.")

    # 3. Quarantine all REQ- seed jobs
    quarantined_count = req_jobs.update(
        status='INACTIVE',
        verification_status='LEGACY_UNVERIFIED',
        verification_reason='Quarantined legacy unverified synthetic seed data',
        link_status='UNVERIFIED'
    )
    print(f"Successfully quarantined {quarantined_count} REQ- seed jobs to LEGACY_UNVERIFIED / INACTIVE.")

    # 4. Audit active published pool
    active_published = Job.objects.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
    print("\n--- ACTIVE PUBLISHED POOL AFTER QUARANTINE ---")
    print(f"Total Active Published Jobs: {active_published.count()}")
    
    # Verify zero REQ- jobs remain active
    active_req_rem = Job.objects.filter(job_id__startswith='REQ', status='ACTIVE').count()
    print(f"Remaining active REQ- jobs (MUST BE 0): {active_req_rem}")
    
    # Verify zero jobs have synthetic salary
    sal_rem = Job.objects.filter(status='ACTIVE', salary__isnull=False).exclude(salary='').count()
    print(f"Remaining active jobs with salary (MUST BE 0 unless genuine source): {sal_rem}")

    # Breakdown of remaining active jobs by company
    comp_counts = {}
    for j in active_published:
        cname = j.company.company_name
        comp_counts[cname] = comp_counts.get(cname, 0) + 1

    print(f"\nCompanies with genuine active postings: {len(comp_counts)}")
    for cname, count in sorted(comp_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  - {cname}: {count} genuine active jobs")

    print("\n" + "=" * 80)
    print("QUARANTINE COMPLETED SUCCESSFULLY")
    print("=" * 80)

if __name__ == '__main__':
    quarantine_seed_jobs()
