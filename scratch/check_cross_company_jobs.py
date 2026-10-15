import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models.company import Company
from modules.admin_panel.models.job import Job
from urllib.parse import urlparse

mismatches = []
all_jobs = Job.objects.select_related('company').all()
print(f"Total jobs: {all_jobs.count()}")

# Group jobs by company and check their domains against company website
for j in all_jobs:
    comp = j.company
    c_web = comp.website_url or ''
    c_car = comp.careers_url or ''
    c_domain = urlparse(c_web).netloc.lower().replace('www.', '')
    
    app_url = j.application_url or ''
    app_domain = urlparse(app_url).netloc.lower().replace('www.', '')
    
    # If app_domain contains 'adani' and company is not an Adani entity
    if 'adani' in app_domain and 'adani' not in comp.company_name.lower():
        mismatches.append((comp.company_id, comp.company_name, j.job_id, j.job_title, app_url))

print(f"Total non-Adani jobs pointing to adani/oraclecloud: {len(mismatches)}")
comp_counts = {}
for m in mismatches:
    comp_counts[m[1]] = comp_counts.get(m[1], 0) + 1

for cname, cnt in comp_counts.items():
    print(f" - {cname}: {cnt} jobs pointing to Adani")
