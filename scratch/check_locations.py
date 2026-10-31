import os
import sys
BASE_DIR = r"d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)"
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, CSRProject
from django.db.models import Count

print("=== TOP 30 JOB LOCATIONS IN DB ===")
job_locs = Job.objects.values('location').annotate(cnt=Count('job_row_id')).order_by('-cnt')[:30]
for r in job_locs:
    print(f"  '{r['location']}': {r['cnt']}")

print("\n=== TOP 25 CSR STATES IN DB ===")
csr_states = CSRProject.objects.values('state').annotate(cnt=Count('csr_id')).order_by('-cnt')[:25]
for r in csr_states:
    print(f"  '{r['state']}': {r['cnt']}")

print("\n=== TOP 25 CSR GEOGRAPHIC_LOCATIONS IN DB ===")
csr_geos = CSRProject.objects.values('geographic_location').annotate(cnt=Count('csr_id')).order_by('-cnt')[:25]
for r in csr_geos:
    print(f"  '{r['geographic_location']}': {r['cnt']}")
