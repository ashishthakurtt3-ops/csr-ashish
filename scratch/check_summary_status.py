import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, CompanyCrawlSummary

summaries = CompanyCrawlSummary.objects.filter(crawl_status='CRAWLED')
print(f"CompanyCrawlSummary with crawl_status='CRAWLED': {summaries.count()}")

# Check how many Company models have a corresponding summary that is CRAWLED
c_ids = summaries.values_list('company_id', flat=True)
comps = Company.objects.filter(company_id__in=c_ids)
print(f"Companies matching CRAWLED summary: {comps.count()}")
print("Their company.crawl_status distribution:")
from django.db.models import Count
print(dict(comps.values_list('crawl_status').annotate(Count('company_id'))))
