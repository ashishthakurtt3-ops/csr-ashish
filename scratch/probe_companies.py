import os
import sys
import re
import requests
from bs4 import BeautifulSoup
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ['FORCE_SQLITE'] = '1'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Company

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

ats_patterns = [
    ('Greenhouse', re.compile(r'greenhouse\.io/[a-zA-Z0-9_\-]+', re.I)),
    ('Lever', re.compile(r'lever\.co/[a-zA-Z0-9_\-]+', re.I)),
    ('SmartRecruiters', re.compile(r'smartrecruiters\.com/[a-zA-Z0-9_\-]+', re.I)),
    ('Workday', re.compile(r'myworkdayjobs\.com/[a-zA-Z0-9_\-]+', re.I)),
    ('Ashby', re.compile(r'ashbyhq\.com/[a-zA-Z0-9_\-]+', re.I)),
    ('SuccessFactors', re.compile(r'successfactors\.(?:com|eu)/[a-zA-Z0-9_\-]+', re.I)),
    ('OracleCloud', re.compile(r'oraclecloud\.com/[a-zA-Z0-9_\-/]+', re.I)),
    ('Darwinbox', re.compile(r'darwinbox\.in/[a-zA-Z0-9_\-/]+', re.I)),
]

companies = list(Company.objects.all().order_by('company_id'))[:60]
print(f"Testing first {len(companies)} companies...")

results = []

for c in companies:
    target = c.careers_url or c.website_url
    if not target:
        continue
    try:
        r = requests.get(target, headers=HEADERS, timeout=6, allow_redirects=True)
        if not r.ok:
            results.append((c.company_id, c.company_name, target, f"HTTP {r.status_code}", None))
            continue
        text = r.text
        detected = []
        for name, pat in ats_patterns:
            m = pat.search(text)
            if m:
                detected.append(f"{name}: {m.group(0)}")
        if 'application/ld+json' in text and 'JobPosting' in text:
            detected.append('JSON-LD JobPosting')
        
        status_msg = f"HTTP {r.status_code} ({len(text)} bytes)"
        results.append((c.company_id, c.company_name, r.url, status_msg, detected))
    except Exception as e:
        results.append((c.company_id, c.company_name, target, f"Error: {str(e)[:40]}", None))

print("\n--- Summary ---")
with_jobs_source = [r for r in results if r[4]]
print(f"Companies with detected job sources: {len(with_jobs_source)}")
for r in with_jobs_source:
    print(f"  {r[0]} | {r[1]} | {r[4]}")
