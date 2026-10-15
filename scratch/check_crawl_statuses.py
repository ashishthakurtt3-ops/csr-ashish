import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company
from django.db.models import Count

for row in Company.objects.values('crawl_status').annotate(cnt=Count('company_id')):
    print(f"crawl_status={row['crawl_status']} | count={row['cnt']}")

print("\n--- Companies by crawl_status ---")
for st in ['CRAWLED', 'FAILED', 'BLOCKED', 'REDIRECT_BLOCKED']:
    comps = Company.objects.filter(crawl_status=st)
    sample = [c.company_name for c in comps[:3]]
    print(f"{st} ({comps.count()}): {sample}...")
