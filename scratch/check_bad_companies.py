import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from modules.admin_panel.models import Job, Company, CSRProject

top_comps = Company.objects.filter(company_id__in=[
    'COMP_TOP200_001', 'COMP_TOP200_002', 'COMP_TOP200_003', 'COMP_TOP200_004', 'COMP_TOP200_005'
])

for comp in top_comps:
    jobs = list(comp.jobs.all())
    print(f"\n================ {comp.company_name} ({comp.company_id}) ================")
    print(f"Website: {comp.website_url} | Careers: {comp.careers_url}")
    print(f"Total Jobs in DB: {len(jobs)}")
    for j in jobs[:6]:
        print(f"  - Title: {j.job_title} | URL: {j.application_url} | Status: {j.status} | Quality: {j.link_quality} | VerifReason: {j.verification_reason}")
    csrs = list(comp.csr_projects.all())
    print(f"Total CSR: {len(csrs)}")
    for c in csrs[:4]:
        print(f"  - CSR: {c.project_name} | URL: {getattr(c, 'source_url', None)} | Status: {c.status}")
