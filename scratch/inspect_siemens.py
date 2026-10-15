import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job

siemens = Company.objects.filter(nse_symbol='SIEMENS').first() or Company.objects.filter(company_name__icontains='siemens').first()
print('Siemens company:', siemens.company_id, siemens.company_name)
print('Website:', siemens.website_url)
print('Careers:', siemens.careers_url)

s_jobs = Job.objects.filter(company=siemens)
print(f'Total Siemens jobs in DB: {s_jobs.count()}')
for j in s_jobs:
    print(f'[{j.job_id}] "{j.job_title}"')
    print(f'  status: {j.status} | verif: {j.verification_status} | loc: {j.location}')
    print(f'  app_url: {j.application_url}')
    print(f'  src_url: {j.source_url}')
