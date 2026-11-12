import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

test_comps = [
    'Tata Consultancy Services Limited',
    'Hitachi Energy India Limited',
    'Wipro Limited',
    'Infosys Limited'
]

for name in test_comps:
    c = Company.objects.filter(company_name=name).first()
    if c:
        print(f"\n==========================================")
        print(f"Testing Grounded Discovery for {c.company_name} ({c.company_id})")
        print(f"Careers URL: {c.careers_url}")
        print(f"CSR URL: {c.csr_url}")
        task = {
            'company_name': c.company_name,
            'website_url': c.website_url,
            'careers_url': c.careers_url,
            'csr_url': c.csr_url,
            'sector': c.sector
        }
        res = BatchDiscoveryService.process_single_company(task, {'extract_jobs': True, 'extract_csr': True})
        print(f"Result:")
        print(f"  Jobs Discovered: {res.get('jobs_discovered')} | Imported: {res.get('jobs_imported')}")
        print(f"  CSR Discovered: {res.get('csr_discovered')} | Imported: {res.get('csr_imported')}")
        print("  Sample Jobs:")
        for j in res.get('jobs', [])[:3]:
            print(f"    - {j.get('job_title')} | URL: {j.get('application_url')}")
        print("  Sample CSR:")
        for cs in res.get('csr_projects', [])[:3]:
            print(f"    - {cs.get('project_name')} | URL: {cs.get('source_url')}")
        print("  Recent Logs:")
        for l in res.get('logs', [])[-4:]:
            print(f"    {l}")

