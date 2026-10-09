import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
import requests
from modules.crawler_engine.parsers.ats import ATSParser
from modules.admin_panel.models import Company

c = Company.objects.get(company_id='COMP_TOP200_017')
resp = requests.get('https://careers.adani.com/', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)

parser = ATSParser(c, 'https://careers.adani.com/', resp.url, resp.text)
links = parser.find_ats_links()
print('ATS links found from careers.adani.com:', links)
jobs = parser.extract_jobs()
print('Jobs extracted:', len(jobs))
