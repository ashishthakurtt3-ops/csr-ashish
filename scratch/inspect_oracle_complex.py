import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from modules.crawler_engine.crawler import safe_get

url = "https://eibd.fa.em2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1"
resp = safe_get(url)
data = json.loads(resp.text)
item = data['items'][0]
for k, v in item.items():
    if isinstance(v, (dict, list)):
        print(f"Key {k} (type {type(v)}):")
        if isinstance(v, list) and len(v) > 0:
            print(f"  first elem: {v[0]}")
        elif isinstance(v, dict):
            print(f"  keys: {list(v.keys())}")
