import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.crawler_engine.crawler import safe_get
import urllib.parse

resp = safe_get('https://www.adani.com/opportunity/')
print('Status:', resp.status_code, 'Final URL:', resp.url, 'Length:', len(resp.text))
print(resp.text[:1200])

# Check API endpoint for Oracle CE
api_url = "https://eibd.fa.em2.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true"
api_resp = safe_get(api_url)
print('Oracle Rest API status:', api_resp.status_code if api_resp else None)
if api_resp and api_resp.ok:
    print('Oracle Rest API response:', api_resp.text)

