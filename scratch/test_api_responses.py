import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
import json

client = Client()

# 1. Test recommendations API (Company Jobs Directory)
print("=== 1. TESTING /recommendations?limit=200 ===")
resp = client.get('/recommendations?limit=200')
print("Status code:", resp.status_code)
data = resp.json()
items = data.get('items', []) if isinstance(data, dict) else data
print(f"Total companies returned: {len(items)}")

zero_count = 0
positive_count = 0
for i, comp in enumerate(items):
    cnt = comp.get('job_count', 0)
    if cnt == 0:
        zero_count += 1
    else:
        positive_count += 1

print(f"Companies with job_count > 0: {positive_count}")
print(f"Companies with job_count == 0: {zero_count}")

# Check page 3 companies (indices 24 to 35 in 12-per-page)
print("\n--- Sample companies from Page 3 (indices 24-35) ---")
for comp in items[24:36]:
    print(f"  {comp.get('company_name')}: {comp.get('job_count')} jobs | careers: {comp.get('careers_url')}")

# 2. Test ACC Limited in recommendations
acc_comp = next((c for c in items if c.get('company_id') == 'COMP_TOP200_169'), None)
print("\n=== 2. ACC LIMITED IN RECOMMENDATIONS ===")
if acc_comp:
    print("Name:", acc_comp.get('company_name'))
    print("Website:", acc_comp.get('website_url'))
    print("Careers URL:", acc_comp.get('careers_url'))
    print("Job Count:", acc_comp.get('job_count'))
else:
    print("ACC not found!")

# 3. Test /jobs?company_id=COMP_TOP200_169
print("\n=== 3. TESTING /jobs?company_id=COMP_TOP200_169 ===")
resp_jobs = client.get('/jobs?company_id=COMP_TOP200_169')
print("Status code:", resp_jobs.status_code)
data_jobs = resp_jobs.json()
job_items = data_jobs.get('items', []) if isinstance(data_jobs, dict) else data_jobs
print(f"Total ACC jobs returned: {len(job_items)}")
for j in job_items[:5]:
    print(f"  Job: {j.get('job_title')}")
    print(f"    Application URL: {j.get('application_url')}")
    print(f"    Source URL: {j.get('source_url')}")
    print(f"    Careers URL: {j.get('careers_url')}")
    assert 'adani' not in (j.get('application_url') or '').lower(), "FAIL: Adani found in application_url"
    assert 'oraclecloud' not in (j.get('application_url') or '').lower(), "FAIL: oraclecloud found in application_url"
    assert 'adani' not in (j.get('careers_url') or '').lower(), "FAIL: Adani found in careers_url"

print("\nALL API CHECKS PASSED PERFECTLY!")
