import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from modules.crawler_engine.crawler import safe_get

sites = ['CX_1', 'CX_1001', 'CX_2001', 'CX_2005', 'CX_2009', 'CX_2011', 'CX_2015', 'CX_2021', 'CX_2023', 'CX_2025', 'CX_2027', 'CX_2029', 'CX_2033', 'CX_3003']
total_jobs = 0

for site in sites:
    url = f"https://eibd.fa.em2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber={site}"
    resp = safe_get(url)
    if resp and resp.ok:
        data = json.loads(resp.text)
        items = data.get('items', [])
        count = len(items)
        total_jobs += count
        if count > 0:
            print(f"Site {site}: {count} jobs found! Sample: {items[0].get('Title')} ({items[0].get('PrimaryLocation')})")
        else:
            print(f"Site {site}: 0 jobs")
    else:
        print(f"Site {site}: HTTP {resp.status_code if resp else 'None'}")

print(f"\nTotal Oracle jobs discovered across Adani sites: {total_jobs}")
