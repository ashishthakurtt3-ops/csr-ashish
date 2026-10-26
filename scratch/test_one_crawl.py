import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company
from modules.crawler_engine.crawler import process_company

c = Company.objects.get(company_id='COMP_TOP200_001')
print(f"Testing crawler on: {c.company_name} ({c.website_url}, {c.careers_url})")
t0 = time.time()
try:
    summary = process_company(c)
    print(f"Crawl completed in {round(time.time() - t0, 2)}s! Status: {summary.crawl_status}, Jobs disc: {summary.jobs_discovered}")
except Exception as e:
    print(f"Crawl error: {e}")
