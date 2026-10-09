import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.crawler_engine.crawler import safe_get
from bs4 import BeautifulSoup

resp = safe_get('https://careers.adani.com/')
print('Status:', resp.status_code, 'Final URL:', resp.url, 'Length:', len(resp.text))
soup = BeautifulSoup(resp.text, 'lxml')
print('Title:', soup.title.text if soup.title else None)

for a in soup.find_all('a', href=True):
    href = a['href']
    if any(k in href.lower() for k in ['job', 'career', 'opportunity', 'search', 'portal', 'successfactors', 'oracle', 'workday']):
        print('A link:', a.get_text(strip=True)[:40], '-->', href)

for iframe in soup.find_all('iframe', src=True):
    print('Iframe:', iframe['src'])
