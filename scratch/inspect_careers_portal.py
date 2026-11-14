import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from bs4 import BeautifulSoup
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

html, text, stat = BatchDiscoveryService.fetch_page_content('https://careers.happiestminds.com/')
print(f"Status: {stat}, length: {len(html)}")
soup = BeautifulSoup(html, 'html.parser')

print("Links on careers.happiestminds.com:")
for a in soup.find_all('a', href=True):
    href = a['href'].strip()
    txt = a.get_text(' ', strip=True)
    if any(k in href.lower() or k in txt.lower() for k in ['job', 'opening', 'search', 'apply', 'career', 'opportunity', 'position']):
        print(f"  {txt[:40]} -> {href}")

for btn in soup.find_all(['button', 'input']):
    print("  Button/Input:", btn.get('value') or btn.get('name') or btn.get_text(strip=True)[:40])

