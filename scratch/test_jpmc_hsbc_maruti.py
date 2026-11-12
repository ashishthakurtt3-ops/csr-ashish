import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import ssl
import urllib.request
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

test_list = [
    ("JPMorgan Chase", "https://www.jpmorganchase.com"),
    ("HSBC", "https://www.hsbc.com"),
    ("Maruti Suzuki India", "https://www.marutisuzuki.com"),
    ("SAP", "https://www.sap.com")
]

for name, url in test_list:
    print(f"\n==========================================", flush=True)
    print(f"TESTING: {name} ({url})", flush=True)
    print(f"==========================================", flush=True)
    res = BatchDiscoveryService.process_single_company({"company_name": name, "website_url": url}, {"extract_jobs": True, "extract_csr": True})
    print(f"Careers URL resolved: {res.get('careers_url')}", flush=True)
    print(f"CSR URL resolved: {res.get('csr_url')}", flush=True)
    print(f"Jobs Discovered: {res.get('jobs_discovered')}", flush=True)
    print(f"CSR Discovered: {res.get('csr_discovered')}", flush=True)
    for j in res.get('jobs', [])[:4]:
        title = j.get('job_title')
        link = j.get('application_url')
        print(f"  * Job: {title}", flush=True)
        print(f"    Apply: {link}", flush=True)
        # Test HTTP code
        try:
            req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
            ctx = ssl._create_unverified_context()
            resp = urllib.request.urlopen(req, context=ctx, timeout=8)
            print(f"    --> HTTP Check: {resp.status} OK (Final URL: {resp.geturl()})", flush=True)
        except Exception as e:
            print(f"    --> HTTP Check: FAILED ({e})", flush=True)

    for c in res.get('csr', [])[:3]:
        print(f"  * CSR: {c.get('project_name')}", flush=True)
        print(f"    Link: {c.get('source_url')}", flush=True)

