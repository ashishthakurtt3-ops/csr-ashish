import os, sys, json
import django

from pathlib import Path
project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models.company import Company
from modules.admin_panel.models.job import Job

print("=== INSPECTING HERO MOTOCORP ===")
companies = Company.objects.filter(company_name__icontains='Hero')
for c in companies:
    print(f"Company ID: {c.company_id}, Name: {c.company_name}, Careers URL: {getattr(c, 'careers_url', None)}, ATS: {getattr(c, 'ats_platform', None)}")
    c_jobs = Job.objects.filter(company=c)
    print(f"Total jobs for {c.company_name}: {c_jobs.count()}")
    for j in c_jobs:
        print(f"  Job {j.job_row_id} | Title: {j.job_title} | Location: {j.location} | Ext ID: {j.external_job_id} | Detail Fetched: {j.detail_fetched}")
        print(f"    App URL: {j.application_url}")

print("\n=== SEARCHING ALL JOBS FOR 'TERRITORY' ===")
t_jobs = Job.objects.filter(job_title__icontains='Territory')
print(f"Total Territory jobs: {t_jobs.count()}")
for j in t_jobs:
    print(f"Job {j.job_row_id} | Co: {j.company.company_name} | Title: {j.job_title} | Loc: {j.location} | Date: {j.posted_date} | Fetched: {j.detail_fetched}")
    print(f"  URL: {j.application_url}")
    print(f"  Desc len: {len(j.job_description or '')} | Resp len: {len(j.responsibilities or '')} | Qual len: {len(j.qualifications or '')}")
    if j.company and 'hero' in j.company.company_name.lower():
        print(f"  FULL HERO JOB DETAILS:")
        for field in j._meta.fields:
            val = getattr(j, field.name)
            if val:
                print(f"    {field.name}: {str(val)[:200]}")
