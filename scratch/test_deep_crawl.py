import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
import urllib.parse
from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
from modules.admin_panel.services.batch_discovery_service import BROWSER_HEADERS
from modules.crawler_engine.discovery_helpers import is_static_asset_url

def find_deep_links(url, keywords):
    try:
        resp = cffi_requests.get(url, impersonate="chrome124", headers=BROWSER_HEADERS, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        results = []
        for a in soup.find_all('a', href=True):
            h = a['href'].strip()
            txt = a.get_text(' ', strip=True).lower()
            combined = f"{h.lower()} {txt}"
            if h.startswith(('#', 'javascript:', 'mailto:')) or is_static_asset_url(h):
                continue
            full = urllib.parse.urljoin(url, h)
            if is_static_asset_url(full) or full.rstrip('/') == url.rstrip('/'):
                continue
            if any(k in combined for k in keywords):
                if not any(bad in full.lower() for bad in ['login', 'privacy', 'terms', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube']):
                    results.append((full, txt))
        return results
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

print("=== Tata Motors Careers ===")
links = find_deep_links("https://www.tatamotors.com/careers/", ['opening', 'vacanc', 'opportunit', 'job', 'search', 'view all'])
for l, t in links[:10]:
    print(f"  {t} -> {l}")

print("\n=== Hitachi Energy Careers ===")
links = find_deep_links("https://www.hitachienergy.com/careers", ['opening', 'vacanc', 'opportunit', 'job', 'search', 'open-jobs'])
for l, t in links[:10]:
    print(f"  {t} -> {l}")
