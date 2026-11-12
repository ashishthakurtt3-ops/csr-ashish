import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
from pathlib import Path
project_dir = Path('.').resolve()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("Django setup complete.", flush=True)

from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.admin_panel.models import Company

task = {
    'company_name': 'Titan Company Limited',
    'homepage_url': 'https://www.titancompany.in',
    'careers_url': 'https://careers.titan.in/in/en/search-results',
    'csr_url': 'https://www.titancompany.in/sustainability'
}

print("Running process_single_company...", flush=True)
res = BatchDiscoveryService.process_single_company(task)
print('STATUS:', res.get('status'), flush=True)
print('JOBS DISCOVERED:', res.get('jobs_discovered'), 'SAVED:', res.get('jobs_imported'), flush=True)
print('CSR DISCOVERED:', res.get('csr_discovered'), 'SAVED:', res.get('csr_imported'), flush=True)
print('--- LOGS ---', flush=True)
for l in res.get('logs', []):
    print(l, flush=True)

# Verify in DB
comp = Company.objects.filter(company_name__icontains='Titan').first()
if comp:
    print('DB JOBS:', comp.jobs.count(), flush=True)
    print('DB CSR:', comp.csr_projects.count(), flush=True)
