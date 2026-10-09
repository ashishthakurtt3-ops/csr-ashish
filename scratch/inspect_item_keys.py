import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()

from modules.crawler_engine.crawler import safe_get

url = "https://eibd.fa.em2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber=CX_1"
resp = safe_get(url)
data = json.loads(resp.text)
item = data['items'][0]
print("Keys:", list(item.keys()))
for k, v in item.items():
    if not isinstance(v, (dict, list)):
        print(f"  {k}: {v}")
