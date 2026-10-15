import os
import sys
import re
import urllib.parse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ['FORCE_SQLITE'] = '1'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Company
from modules.crawler_engine.parsers.ats import ATS_ADAPTER_REGISTRY, safe_get

companies = list(Company.objects.all().order_by('company_id'))

print(f"Scanning {len(companies)} companies for careers/ATS endpoints...")

ats_detected = []
no_ats = []

for c in companies:
    target = c.careers_url or c.website_url
    if not target:
        continue
    matched_adapter = None
    for adapter in ATS_ADAPTER_REGISTRY:
        if adapter.matches(target):
            matched_adapter = adapter.name
            break
    if matched_adapter:
        ats_detected.append((c.company_id, c.company_name, target, matched_adapter))
    else:
        no_ats.append((c.company_id, c.company_name, target))

print(f"Direct ATS matches in careers_url: {len(ats_detected)}")
for item in ats_detected[:20]:
    print(f"  {item[0]} | {item[1]} | {item[3]} | {item[2]}")
