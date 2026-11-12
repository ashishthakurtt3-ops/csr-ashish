import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company

companies = (
    Company.objects
    .filter(company_id__startswith='COMP_TOP200_')
    .order_by('company_id')[:50]
)

zero_jobs = []
zero_csr = []

print(f"{'Company Name':<45} | {'Jobs':<5} | {'CSR':<5}")
print("-" * 60)
for c in companies:
    j_count = c.jobs.count()
    cs_count = c.csr_projects.count()
    print(f"{c.company_name[:44]:<45} | {j_count:<5} | {cs_count:<5}")
    if j_count == 0:
        zero_jobs.append(c)
    if cs_count == 0:
        zero_csr.append(c)

print("-" * 60)
print(f"Total companies with 0 jobs: {len(zero_jobs)}")
print(f"Total companies with 0 CSR: {len(zero_csr)}")

