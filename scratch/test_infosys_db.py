import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject

for comp in Company.objects.filter(company_name__icontains='infosys'):
    print(f"Infosys: {comp.company_name} (ID: {comp.company_id})")
    for j in Job.objects.filter(company=comp)[:5]:
        print(f"  Job: {j.job_title} | URL: {j.application_url}")
    for c in CSRProject.objects.filter(company=comp)[:5]:
        print(f"  CSR: {c.project_name} | URL: {c.source_url}")
