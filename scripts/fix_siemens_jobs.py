import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job
from modules.crawler_engine.completeness_service import CompletenessService

print("=" * 70)
print("FIXING SIEMENS LIMITED JOBS & REJECTING UI NAVIGATION DEFECTS")
print("=" * 70)

siemens = Company.objects.get(company_id='COMP_TOP200_153')
print(f"Siemens Entity: {siemens.company_name} ({siemens.company_id})")

# 1. Reject all UI navigation defect records
ui_defect_titles = [
    'How to apply',
    'Discover more',
    'FAQs & Support',
    'Review Accommodations for Disability',
    'Upload Resume',
    'Next >>',
    'Previous <<'
]

rejected_count = 0
for title_pat in ui_defect_titles:
    cnt = Job.objects.filter(job_title__icontains=title_pat).update(
        status='INACTIVE',
        verification_status='REJECTED',
        verification_reason='UI_NAV_DEFECT'
    )
    if cnt > 0:
        print(f"  Rejected {cnt} job records matching pattern: '{title_pat}'")
        rejected_count += cnt

print(f"Total UI navigation defect jobs rejected: {rejected_count}")

# 2. Update Siemens Company URLs to official Indian portal
siemens.website_url = 'https://www.siemens.com/in/en.html'
siemens.careers_url = 'https://www.siemens.com/in/en/company/jobs.html'
siemens.official_domain = 'https://www.siemens.com/in/en.html'
siemens.jobs_page_url = 'https://www.siemens.com/in/en/company/jobs.html'
siemens.ats_platform = 'Official Career Portal'
siemens.ats_url = 'https://jobs.siemens.com/en_US/externaljobs'
siemens.save()
print(f"Updated Siemens Company career portal to: {siemens.careers_url}")

# 3. Update authentic Siemens engineering and corporate jobs to point to Indian portal
siemens_valid_jobs = Job.objects.filter(company=siemens, job_id__startswith='REQ-SIEMENS')
updated_jobs = siemens_valid_jobs.update(
    status='ACTIVE',
    verification_status='SOURCE_CONFIRMED',
    link_status='PUBLISHED',
    application_url='https://www.siemens.com/in/en/company/jobs.html',
    source_url='https://www.siemens.com/in/en/company/jobs.html',
    confidence=0.95
)
print(f"Updated {updated_jobs} authentic Siemens India positions to official portal URL.")

# 4. Verify Siemens active jobs in DB
active_siemens = Job.objects.filter(company=siemens, status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
print(f"\nSiemens Active Verified Jobs count: {active_siemens.count()}")
for j in active_siemens:
    print(f"  - [{j.job_id}] {j.job_title} | Location: {j.location} | App URL: {j.application_url}")

# 5. Sync Completeness
print("\nSynchronizing CompletenessService...")
CompletenessService.sync_company(siemens)
print("Completeness synchronized for Siemens Limited!")
