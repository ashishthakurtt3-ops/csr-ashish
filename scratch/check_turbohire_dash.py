import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

r_html, r_text, r_status = BatchDiscoveryService.fetch_rendered_page('https://tatamotors.turbohire.co/dashboardv2?orgId=39ddba0d-55f7-4206-abf0-e6121e93436a&type=0')
print("Status:", r_status)
print("Text length:", len(r_text))
print("Text sample:", r_text[:1000])

from bs4 import BeautifulSoup
soup = BeautifulSoup(r_html, 'html.parser')
anchors = soup.find_all('a')
print("Total anchors:", len(anchors))
for a in anchors[:15]:
    print(a.get_text(strip=True), "->", a.get('href'))

