import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ['FORCE_SQLITE'] = '1'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject
from modules.crawler_engine.crawler import process_company

# Test with Aarti Industries or Adani Ports or Razorpay or Mahindra
comp = Company.objects.filter(company_name__icontains='Aarti Industries').first()
if not comp:
    comp = Company.objects.first()

print(f"Testing crawl for: {comp.company_name} ({comp.company_id})")
print(f"Website: {comp.website_url}")
print(f"Careers: {comp.careers_url}")
print(f"CSR: {comp.csr_portal_url}")

process_company(comp)

comp.refresh_from_db()
print(f"\nAfter crawl:")
print(f"Crawl status: {comp.crawl_status}")
print(f"Jobs count: {comp.jobs.count()}")
print(f"Published jobs: {comp.jobs.filter(verification_status='PUBLISHED').count()}")
print(f"CSR projects: {comp.csr_projects.count()}")
print(f"Published CSR: {comp.csr_projects.filter(verification_status='PUBLISHED').count()}")
