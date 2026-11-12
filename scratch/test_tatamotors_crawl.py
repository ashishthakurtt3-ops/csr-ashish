import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.admin_panel.models import Company

c = Company.objects.filter(company_name__icontains='Tata Motors').first()
print(f"Testing {c.company_name}...")
res = BatchDiscoveryService.process_single_company({
    'company_name': c.company_name,
    'website_url': 'https://www.tatamotors.com',
    'careers_url': 'https://www.tatamotors.com/careers',
    'csr_url': 'https://www.tatamotors.com/corporate-responsibility'
})
print("Result jobs count:", res.get('jobs_discovered'))
for j in res.get('jobs', [])[:5]:
    print("  Job:", j.get('job_title'), "->", j.get('application_url'))
print("Result CSR count:", res.get('csr_discovered'))
for p in res.get('csr', [])[:5]:
    print("  CSR:", p.get('project_name'), "->", p.get('source_url'))

