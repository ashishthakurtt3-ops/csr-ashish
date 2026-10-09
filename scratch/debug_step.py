import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
import requests, time
from modules.crawler_engine.parsers.ats import ATSParser, OracleTaleoAdapter
from modules.admin_panel.models import Company

c = Company.objects.get(company_id='COMP_TOP200_017')
print('Getting careers page...', flush=True)
resp = requests.get('https://careers.adani.com/', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)

parser = ATSParser(c, 'https://careers.adani.com/', resp.url, resp.text)
links = parser.find_ats_links()
print(f'Found {len(links)} ATS links', flush=True)
sorted_links = sorted(links, key=lambda x: 0 if 'cx_1' in x.lower() else 1)
print(f'First link: {sorted_links[0]}', flush=True)

adapter = OracleTaleoAdapter()
print(f'Testing adapter matches: {adapter.matches(sorted_links[0])}', flush=True)
t0 = time.time()
jobs = adapter.extract_jobs(sorted_links[0], c)
print(f'Extracted {len(jobs)} jobs in {time.time()-t0:.2f}s', flush=True)
