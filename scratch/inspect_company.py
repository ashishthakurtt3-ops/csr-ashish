import os
import sys
import django

sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject

target_names = ['Hitachi Energy', 'Tata Consultancy', 'Wipro', 'Infosys', 'Varun Beverages', 'Tata Motors', 'State Bank of India']
for name in target_names:
    for c in Company.objects.filter(company_name__icontains=name):
        print(f"\n=== {c.company_name} ({c.company_id}) ===")
        print("Careers URL:", c.careers_url)
        print("CSR URL:", c.csr_url)
        jobs = list(Job.objects.filter(company=c))
        print(f"Jobs ({len(jobs)}):")
        for j in jobs[:6]:
            print(f"  - Title: {j.job_title}\n    URL: {j.application_url}\n    Evidence: {j.evidence_text[:80] if j.evidence_text else ''}")
        csrs = list(CSRProject.objects.filter(company=c))
        print(f"CSR ({len(csrs)}):")
        for cs in csrs[:4]:
            print(f"  - Title: {cs.project_name}\n    URL: {cs.source_url}\n    Evidence: {cs.evidence_text[:80] if cs.evidence_text else ''}")
