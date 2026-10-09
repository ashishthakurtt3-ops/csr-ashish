import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
import requests
from modules.crawler_engine.parsers.ats import ATSParser
from modules.admin_panel.models import Company

ports = Company.objects.get(company_id='COMP_TOP200_013')
resp = requests.get('https://careers.adani.com/', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)

parser = ATSParser(ports, 'https://careers.adani.com/', resp.url, resp.text)
links = parser.find_ats_links()
print(f'Ports company name: {ports.company_name}')
print(f'Top 3 ATS links for Ports:')
for l in links[:3]:
    print(' -', l)

jobs = parser.extract_jobs()
print(f'Extracted {len(jobs)} jobs for Ports!')
if jobs:
    print('Sample job:', jobs[0].get('title'), '|', jobs[0].get('location'))
