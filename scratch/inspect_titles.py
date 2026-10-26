import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company
from modules.admin_panel.verification import public_jobs

cids = ['COMP_TOP200_119', 'COMP_TOP200_085', 'COMP_TOP200_010', 'COMP_TOP200_042', 'COMP_TOP200_064', 'COMP_TOP200_073']
for cid in cids:
    c = Company.objects.get(company_id=cid)
    pj = list(public_jobs(c.jobs.all()))
    print(f"\n=== {c.company_name} ({len(pj)} public jobs) ===")
    for j in pj[:10]:
        print(f"  [{j.job_id}] {j.job_title} | Dept: {j.department} | URL: {j.application_url[:60] if j.application_url else 'None'}")
