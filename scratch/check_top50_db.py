import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.models import Company, Job, CSRProject

top50_ids = [f"COMP_TOP200_{i:03d}" for i in range(1, 51)]
comps = Company.objects.filter(company_id__in=top50_ids).order_by('company_id')

print(f"Found {comps.count()} top-50 companies in DB:")
total_jobs = 0
total_csr = 0
for c in comps:
    j_cnt = c.jobs.count()
    c_cnt = c.csr_projects.count()
    total_jobs += j_cnt
    total_csr += c_cnt
    if j_cnt > 0 or c_cnt > 0:
        print(f"  {c.company_id}: {c.company_name} | Jobs: {j_cnt} | CSR: {c_cnt}")

print(f"TOTAL Top-50 Jobs in DB: {total_jobs}, CSR in DB: {total_csr}")

