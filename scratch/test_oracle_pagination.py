import os, sys, json, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from modules.crawler_engine.crawler import safe_get

oracle_host = 'https://eibd.fa.em2.oraclecloud.com'
site_number = 'CX_1'
offset = 0
all_jobs = []

while True:
    url = f"{oracle_host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber={site_number}&expand=requisitionList&offset={offset}&limit=25"
    resp = safe_get(url)
    if not resp or not resp.ok:
        break
    data = json.loads(resp.text)
    items = data.get('items', [])
    if not items:
        break
    req_list = items[0].get('requisitionList', [])
    if not req_list:
        break
    for req in req_list:
        all_jobs.append({
            'title': req.get('Title'),
            'location': req.get('PrimaryLocation'),
            'req_id': req.get('Id'),
            'posted_date': req.get('PostedDate')
        })
    print(f"Fetched offset {offset}: got {len(req_list)} jobs (total so far: {len(all_jobs)})")
    offset += 25
    if offset >= 100:  # test 4 pages = 100 jobs
        break

print(f"\nDiscovered {len(all_jobs)} authentic jobs from Adani Oracle Cloud!")
if all_jobs:
    for j in all_jobs[:5]:
        print(f" - {j['title']} | {j['location']} (ID: {j['req_id']})")
