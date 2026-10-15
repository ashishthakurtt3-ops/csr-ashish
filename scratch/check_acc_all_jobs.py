import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models.company import Company
from modules.admin_panel.models.job import Job

acc = Company.objects.get(company_id='COMP_TOP200_169')
print(f"Company: {acc.company_name} ({acc.company_id})")
for j in Job.objects.filter(company=acc):
    print(f"[{j.job_id}] {j.job_title} | status: {j.status} | verif: {j.verification_status} | app_url: {j.application_url}")
