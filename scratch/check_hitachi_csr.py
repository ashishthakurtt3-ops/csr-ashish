import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from bs4 import BeautifulSoup
import urllib.parse

# Let's check hitachi energy india sustainability / CSR pages
urls = [
    "https://www.hitachienergy.com/in/en/sustainability",
    "https://www.hitachienergy.com/in/en/sustainability/ecospace",
    "https://www.hitachienergy.com/in/en/about-us/integrity/corporate-social-responsibility",
    "https://www.hitachienergy.com/in/en/about-us"
]

for u in urls:
    h, t, s = BatchDiscoveryService.fetch_page_content(u)
    print(f"{u} -> status: {s}, len: {len(t)}")
    if h:
        soup = BeautifulSoup(h, 'html.parser')
        for a in soup.find_all('a', href=True):
            txt = a.get_text(' ', strip=True).lower()
            href = a['href'].lower()
            if any(k in txt or k in href for k in ['csr', 'social-responsibility', 'sustainability-report', 'policy']):
                print(f"   Found link: {txt} -> {urllib.parse.urljoin(u, a['href'])}")

