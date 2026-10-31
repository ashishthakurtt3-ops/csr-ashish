import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
django.setup()

from modules.admin_panel.models import Job

active_jobs = Job.objects.filter(status='ACTIVE', is_defective=False)

non_jobs_in_active = []
for j in active_jobs:
    u = (j.application_url or '').lower()
    t = (j.job_title or '').lower()
    comp = j.company.company_name
    
    # Check if clearly a non-job
    if any(k in u for k in ['case-study', 'who-we-are/newsroom', 'about-us/corporate-office', 'consumer-brands', 'young-talent']):
        non_jobs_in_active.append((j.job_row_id, comp, j.job_title, j.application_url))

print(f'Total non-jobs found in active (1492): {len(non_jobs_in_active)}')
for nj in non_jobs_in_active:
    print(nj)
