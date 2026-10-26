import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job

for cid in ['COMP_TOP200_057', 'COMP_TOP200_042', 'COMP_TOP200_192']:
    jobs = list(Job.objects.filter(company_id=cid, status='ACTIVE')[:15])
    print(f"\n=== {cid} ===")
    for j in jobs:
        print(f" - {j.job_title} | URL: {j.application_url[:75] if j.application_url else 'None'}")
