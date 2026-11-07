import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject

print("=== CHECKING ALL COMPANIES IN DATABASE ===")
for comp in Company.objects.all().order_by('company_name'):
    jobs = list(Job.objects.filter(company_id=comp.company_id))
    csrs = list(CSRProject.objects.filter(company_id=comp.company_id))
    if len(jobs) > 0 or len(csrs) > 0:
        print(f"\nCompany: {comp.company_name} (ID: {comp.company_id}) | Jobs: {len(jobs)} | CSR: {len(csrs)}")
        for j in jobs[:3]:
            print(f"   Job: {j.job_title} | ExtID: {j.external_job_id} | URL: {j.application_url}")
        for c in csrs[:2]:
            print(f"   CSR: {c.title} | URL: {c.source_url}")
