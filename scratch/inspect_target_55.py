import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, CompanyCrawlSummary, CompanyCompletenessRegister
from scripts.crawl_55_companies import TARGET_COMPANY_IDS

print(f"Total target company IDs: {len(TARGET_COMPANY_IDS)}")
comps = Company.objects.filter(company_id__in=TARGET_COMPANY_IDS).order_by('company_id')
print(f"Found in DB: {comps.count()}")

print(f"\n{'#':<3} | {'ID':<16} | {'Company Name':<30} | {'Status':<10} | {'ATS':<14} | {'Jobs':<5} | {'CSR':<5} | {'Opps':<5}")
print("-" * 95)
for idx, c in enumerate(comps[:55], 1):
    summary = CompanyCrawlSummary.objects.filter(company=c).order_by('-summary_id').first()
    ats = c.ats_platform or (summary.ats_platform if summary else 'Direct') or 'Direct'
    status = (summary.crawl_status if summary else c.crawl_status)
    jobs_count = c.jobs.filter(status='ACTIVE').count()
    csr_count = c.csr_projects.count()
    opps_count = c.open_opportunities.count()
    print(f"{idx:<3} | {c.company_id:<16} | {c.company_name[:30]:<30} | {status:<10} | {ats[:14]:<14} | {jobs_count:<5} | {csr_count:<5} | {opps_count:<5}")
