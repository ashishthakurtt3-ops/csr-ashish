import os
import sys
import json
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject
from curl_cffi import requests as cffi_requests
from modules.admin_panel.services.batch_discovery_service import BROWSER_HEADERS

top50 = Company.objects.filter(company_id__startswith='COMP_TOP200_').order_by('company_id')[:50]

print(f"Auditing links across {top50.count()} companies...")

bad_job_links = []
bad_csr_links = []
tested_urls = {}

def check_url(url):
    if not url:
        return 0, "Empty URL"
    if url in tested_urls:
        return tested_urls[url]
    
    # Check for hallucinated pattern signatures
    if any(h in url.lower() for h in ['ibegin.tcs.com/ibegin/jobs/tcs/', 'careers.wipro.com/careers-home/jobs/wip-']):
        tested_urls[url] = (404, "Hallucinated Pattern")
        return 404, "Hallucinated Pattern"
        
    try:
        r = cffi_requests.get(url, impersonate="chrome124", headers=BROWSER_HEADERS, timeout=8, allow_redirects=True)
        tested_urls[url] = (r.status_code, "OK" if r.status_code < 400 else "HTTP Error")
        return tested_urls[url]
    except Exception as e:
        tested_urls[url] = (0, str(e)[:50])
        return 0, str(e)[:50]

total_jobs_checked = 0
total_csr_checked = 0

for c in top50:
    for j in c.jobs.all()[:3]:
        total_jobs_checked += 1
        app_url = j.application_url
        if not app_url:
            bad_job_links.append((c.company_name, j.job_title, "MISSING_URL"))
            continue
        status, msg = check_url(app_url)
        if status >= 400 or status == 0:
            bad_job_links.append((c.company_name, j.job_title, app_url, status, msg))
            
    for p in c.csr_projects.all()[:2]:
        total_csr_checked += 1
        src_url = p.source_url
        if not src_url:
            bad_csr_links.append((c.company_name, p.project_name, "MISSING_URL"))
            continue
        status, msg = check_url(src_url)
        if status >= 400 or status == 0:
            bad_csr_links.append((c.company_name, p.project_name, src_url, status, msg))

print("\n=== AUDIT RESULTS ===")
print(f"Total Jobs Checked: {total_jobs_checked}")
print(f"Bad Job Links Count: {len(bad_job_links)}")
for item in bad_job_links:
    print("  BAD JOB:", item)

print(f"\nTotal CSR Checked: {total_csr_checked}")
print(f"Bad CSR Links Count: {len(bad_csr_links)}")
for item in bad_csr_links:
    print("  BAD CSR:", item)
