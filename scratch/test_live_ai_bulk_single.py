import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import urllib.request
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

test_companies = [
    {'company_name': 'Hitachi Energy India Limited', 'website_url': 'https://www.hitachienergy.com'},
    {'company_name': 'Tata Motors', 'website_url': 'https://www.tatamotors.com'},
    {'company_name': 'Reliance Industries Limited', 'website_url': 'https://www.ril.com'}
]

for tc in test_companies:
    print(f"\n=======================================================", flush=True)
    print(f"TESTING LIVE BULK DISCOVERY FOR: {tc['company_name']}", flush=True)
    print(f"=======================================================", flush=True)
    res = BatchDiscoveryService.process_single_company(tc, {'extract_jobs': True, 'extract_csr': True})
    print(f"Status: {res.get('status')}", flush=True)
    print(f"Jobs Discovered: {res.get('jobs_discovered')}, Imported: {res.get('jobs_imported')}", flush=True)
    print(f"CSR Discovered: {res.get('csr_discovered')}, Imported: {res.get('csr_imported')}", flush=True)
    
    jobs = res.get('jobs', [])
    print(f"\nSample Jobs Extracted ({len(jobs)} total jobs discovered):", flush=True)
    for j in jobs[:4]:
        title = j.get('job_title')
        link = j.get('application_url')
        print(f"  * Title: {title}", flush=True)
        print(f"    Link : {link}", flush=True)
        try:
            req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            resp = urllib.request.urlopen(req, timeout=10)
            print(f"    --> HTTP Live Check: {resp.status} OK (Final URL: {resp.geturl()})", flush=True)
        except Exception as e:
            print(f"    --> HTTP Live Check: FAILED ({e})", flush=True)

    csr = res.get('csr', [])
    print(f"\nSample CSR Extracted ({len(csr)} total CSR discovered):", flush=True)
    for c in csr[:3]:
        name = c.get('project_name')
        link = c.get('source_url')
        print(f"  * Project: {name}", flush=True)
        print(f"    Link   : {link}", flush=True)
        try:
            req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            resp = urllib.request.urlopen(req, timeout=10)
            print(f"    --> HTTP Live Check: {resp.status} OK (Final URL: {resp.geturl()})", flush=True)
        except Exception as e:
            print(f"    --> HTTP Live Check: FAILED ({e})", flush=True)
