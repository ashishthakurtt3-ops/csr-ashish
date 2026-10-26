import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import Count
from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, Contact

print(f"Total Companies: {Company.objects.count()}")
print(f"Total Jobs: {Job.objects.count()} (Active: {Job.objects.filter(status='ACTIVE').count()}, Published: {Job.objects.filter(verification_status='PUBLISHED').count()})")
print(f"Total CSR Projects: {CSRProject.objects.count()}")
print(f"Total CSROpportunities: {CSROpportunity.objects.count()}")
print(f"Total Contacts: {Contact.objects.count()}")

status_counts = Company.objects.values('crawl_status').annotate(cnt=Count('company_id'))
print("\nCrawl Status Breakdown:")
for sc in status_counts:
    print(f"  {sc['crawl_status']}: {sc['cnt']}")

print("\nFirst 50 Companies summary:")
print(f"{'#':<3} | {'Company ID':<16} | {'Company Name':<30} | {'Status':<10} | {'Jobs':<5} | {'CSR':<5} | {'Opps':<5}")
print("-" * 80)
for idx, c in enumerate(Company.objects.all()[:50], 1):
    j_count = c.jobs.count()
    csr_count = c.csr_projects.count()
    opp_count = c.open_opportunities.count()
    print(f"{idx:<3} | {c.company_id:<16} | {c.company_name[:30]:<30} | {c.crawl_status:<10} | {j_count:<5} | {csr_count:<5} | {opp_count:<5}")
