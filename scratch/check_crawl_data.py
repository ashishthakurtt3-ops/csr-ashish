import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, Contact, CompanyCrawlSummary

print("CompanyCrawlSummary count:", CompanyCrawlSummary.objects.count())
summaries = CompanyCrawlSummary.objects.all()[:15]
for s in summaries:
    print(f"[{s.company_id}] {s.company.company_name if s.company else 'None'} | status={s.crawl_status} | jobs_disc={s.jobs_discovered} | ats={s.ats_platform}")

print("\nCompanies with jobs > 0:")
comps_with_jobs = Company.objects.filter(jobs__isnull=False).distinct()
print(f"Count of companies with at least 1 job: {comps_with_jobs.count()}")

print("\nCompanies with CSR > 0:")
comps_with_csr = Company.objects.filter(csr_projects__isnull=False).distinct()
print(f"Count of companies with at least 1 CSR project: {comps_with_csr.count()}")
