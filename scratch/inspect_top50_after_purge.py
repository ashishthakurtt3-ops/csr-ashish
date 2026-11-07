import os, sys, json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject

companies = Company.objects.filter(company_id__startswith='COMP_TOP200_').order_by('company_id')[:50]

empty_companies = []
print(f"Checking top {len(companies)} companies...")

for c in companies:
    jobs = list(c.jobs.all())
    csrs = list(c.csr_projects.all())
    j_count = len(jobs)
    c_count = len(csrs)
    if j_count == 0 or c_count == 0:
        empty_companies.append((c.company_id, c.company_name, j_count, c_count))

print(f"Companies with 0 jobs or 0 CSR: {len(empty_companies)}")
for cid, name, jc, cc in empty_companies:
    print(f"  {cid}: {name[:30]:30} -> Jobs: {jc}, CSR: {cc}")

