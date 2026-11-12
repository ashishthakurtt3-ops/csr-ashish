import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.admin_panel.models import Company

c = Company.objects.get(company_id='COMP_TOP200_050') # Hitachi Energy
res = BatchDiscoveryService.process_single_company({
    'company_name': c.company_name,
    'website_url': c.website_url,
    'careers_url': c.careers_url,
    'csr_url': c.csr_portal_url
})
print("LOGS:")
for l in res.get('logs', []):
    print(" ", l)

