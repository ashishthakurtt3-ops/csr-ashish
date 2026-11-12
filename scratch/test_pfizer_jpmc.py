import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

for name, url in [("Pfizer", "https://www.pfizer.com"), ("JPMorgan Chase", "https://www.jpmorganchase.com")]:
    print(f"\n==========================================")
    print(f"TESTING: {name}")
    print(f"==========================================")
    res = BatchDiscoveryService.process_single_company({"company_name": name, "website_url": url}, {"extract_jobs": True, "extract_csr": False})
    print(f"Careers URL resolved: {res.get('careers_url')}")
    print(f"Jobs Discovered: {res.get('jobs_discovered')}")
    for j in res.get('jobs', []):
        print(f"  * Title: {j.get('job_title')}")
        print(f"    Apply: {j.get('application_url')}")
        print(f"    Quote: {j.get('verbatim_source_quote')[:100]}")

