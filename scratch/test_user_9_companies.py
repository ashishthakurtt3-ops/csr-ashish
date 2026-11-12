import os
import sys
import django
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import urllib.request
import urllib.error
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

test_manifest = [
    {"company_name": "HCLTech", "website_url": "https://www.hcltech.com"},
    {"company_name": "Samsung Electronics", "website_url": "https://www.samsung.com"},
    {"company_name": "Pfizer", "website_url": "https://www.pfizer.com"},
    {"company_name": "JPMorgan Chase", "website_url": "https://www.jpmorganchase.com"},
    {"company_name": "Tata Motors", "website_url": "https://www.tatamotors.com"},
    {"company_name": "HSBC", "website_url": "https://www.hsbc.com"},
    {"company_name": "Maruti Suzuki India", "website_url": "https://www.marutisuzuki.com"},
    {"company_name": "SAP", "website_url": "https://www.sap.com"},
    {"company_name": "Tata Steel", "website_url": "https://www.tatasteel.com"},
]

results = []

for item in test_manifest:
    name = item["company_name"]
    url = item["website_url"]
    print(f"\n==================================================================", flush=True)
    print(f"PROCESSING: {name} ({url})", flush=True)
    print(f"==================================================================", flush=True)
    
    try:
        res = BatchDiscoveryService.process_single_company(
            {"company_name": name, "website_url": url},
            {"extract_jobs": True, "extract_csr": True}
        )
    except Exception as e:
        print(f"CRASH: {e}", flush=True)
        continue

    jobs = res.get('jobs', [])
    csr = res.get('csr', [])
    logs = res.get('logs', [])
    
    print(f"Careers URL resolved: {res.get('careers_url')}", flush=True)
    print(f"CSR URL resolved: {res.get('csr_url')}", flush=True)
    print(f"Jobs Discovered: {len(jobs)}", flush=True)
    print(f"CSR Discovered: {len(csr)}", flush=True)
    
    job_details = []
    for j in jobs:
        title = j.get('job_title', '')
        link = j.get('application_url', '')
        quote = j.get('verbatim_source_quote', '')
        
        # Test link
        http_code = "ERR"
        final_url = ""
        try:
            req = urllib.request.Request(link, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            resp = urllib.request.urlopen(req, timeout=10)
            http_code = resp.status
            final_url = resp.geturl()
        except urllib.error.HTTPError as he:
            http_code = he.code
            final_url = he.url
        except Exception as ex:
            http_code = str(ex)[:35]

        job_info = {
            "title": title,
            "link": link,
            "http_code": http_code,
            "final_url": final_url,
            "quote": quote[:80]
        }
        job_details.append(job_info)
        print(f"  * Job: {title}", flush=True)
        print(f"    Link: {link} [HTTP: {http_code}]", flush=True)
        print(f"    Quote: {quote[:80]}", flush=True)

    results.append({
        "company": name,
        "careers_url": res.get('careers_url'),
        "csr_url": res.get('csr_url'),
        "jobs_count": len(jobs),
        "csr_count": len(csr),
        "jobs": job_details,
        "logs": logs
    })

with open("scratch/test_user_9_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nWROTE RESULTS TO scratch/test_user_9_results.json", flush=True)

