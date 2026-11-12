import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.admin_panel.models import Company

comp = Company.objects.filter(company_name__icontains='Tata Motors').first()
if not comp:
    print("Tata Motors not in DB, using mock Company")
    comp = Company(company_id='COMP_TEST', company_name='Tata Motors Limited', website_url='https://www.tatamotors.com')

logs = []
# Test deep hop from tatamotors.com/careers/openings
url = "https://www.tatamotors.com/careers/openings/"
html, text, status = BatchDiscoveryService.fetch_page_content(url)
deep = BatchDiscoveryService.find_deep_openings_link(html, url)
print("Current find_deep_openings_link result:", deep)

