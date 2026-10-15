import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, Company
from django.db.models import Count

oracle_jobs = Job.objects.filter(source_url__icontains='oraclecloud.com')
print(f'Total oracle jobs in DB: {oracle_jobs.count()}')

for item in oracle_jobs.values('company_id', 'company__company_name', 'status', 'verification_status').annotate(cnt=Count('job_row_id')):
    print(f"{item['company_id']} | {item['company__company_name']} | {item['status']} | {item['verification_status']} | count={item['cnt']}")

# Let's inspect external_job_id overlap between COMP_TOP200_017, 039, 082, 169
cids = ['COMP_TOP200_017', 'COMP_TOP200_039', 'COMP_TOP200_082', 'COMP_TOP200_169']
for cid in cids:
    ext_ids = list(Job.objects.filter(company_id=cid, status='ACTIVE').values_list('external_job_id', flat=True))
    print(f"{cid} active ext_ids ({len(ext_ids)}): {ext_ids[:5]}...")

# Let's inspect ACC jobs (COMP_TOP200_169)
for j in Job.objects.filter(company_id='COMP_TOP200_169', status='ACTIVE'):
    text = f"{j.job_title} {j.job_description or ''} {j.employer_info or ''}".lower()
    has_acc = 'acc' in text
    has_adani = 'adani' in text
    print(f"ACC Job {j.job_row_id} ({j.external_job_id}) '{j.job_title}': has_acc={has_acc}, has_adani={has_adani}")

print("---")
# Let's inspect Ambuja jobs (COMP_TOP200_082)
for j in Job.objects.filter(company_id='COMP_TOP200_082', status='ACTIVE')[:5]:
    text = f"{j.job_title} {j.job_description or ''} {j.employer_info or ''}".lower()
    has_ambuja = 'ambuja' in text
    has_adani = 'adani' in text
    print(f"Ambuja Job {j.job_row_id} ({j.external_job_id}) '{j.job_title}': has_ambuja={has_ambuja}, has_adani={has_adani}")

