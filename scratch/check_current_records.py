import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ['FORCE_SQLITE'] = '1'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject, Contact

print("Total companies in DB:", Company.objects.count())

# Look at companies with careers_url and csr_portal_url
with_careers = Company.objects.filter(careers_url__isnull=False).exclude(careers_url='')
print("Companies with careers_url:", with_careers.count())

with_csr = Company.objects.filter(csr_portal_url__isnull=False).exclude(csr_portal_url='')
print("Companies with csr_portal_url:", with_csr.count())

# Check how many jobs are currently in DB and their verification_status
from collections import Counter
job_statuses = Counter(Job.objects.values_list('verification_status', flat=True))
print("Job verification_statuses:", job_statuses)

# Check companies with jobs
comps_with_jobs = Company.objects.filter(jobs__isnull=False).distinct()
print("Companies with jobs:", comps_with_jobs.count())
for c in comps_with_jobs[:10]:
    print(f"  {c.company_id}: {c.company_name} ({c.jobs.count()} jobs)")
