import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, Company

# Quarantine misattributed jobs on ACC (COMP_TOP200_169)
acc_jobs = Job.objects.filter(company_id='COMP_TOP200_169', status='ACTIVE')
print(f"Quarantining {acc_jobs.count()} misattributed Adani CX_1 jobs from ACC Limited (COMP_TOP200_169)")
acc_count = acc_jobs.update(
    status='INACTIVE',
    verification_status='QUARANTINED',
    evidence_text='Quarantined duplicate: Adani Group Oracle HCM CX_1 requisition misattributed to ACC Limited without independent employer evidence.'
)

# Quarantine misattributed jobs on Ambuja Cements (COMP_TOP200_082)
ambuja_jobs = Job.objects.filter(company_id='COMP_TOP200_082', status='ACTIVE')
print(f"Quarantining {ambuja_jobs.count()} misattributed Adani CX_1 jobs from Ambuja Cements (COMP_TOP200_082)")
ambuja_count = ambuja_jobs.update(
    status='INACTIVE',
    verification_status='QUARANTINED',
    evidence_text='Quarantined duplicate: Adani Group Oracle HCM CX_1 requisition misattributed to Ambuja Cements without independent employer evidence.'
)

# Quarantine misattributed duplicate jobs on Adani Energy Solutions (COMP_TOP200_039)
# Note: These 25 jobs are identical duplicates of Adani Enterprises (COMP_TOP200_017)
energy_jobs = Job.objects.filter(company_id='COMP_TOP200_039', status='ACTIVE')
print(f"Quarantining {energy_jobs.count()} duplicate Adani CX_1 jobs from Adani Energy Solutions (COMP_TOP200_039)")
energy_count = energy_jobs.update(
    status='INACTIVE',
    verification_status='QUARANTINED',
    evidence_text='Quarantined duplicate: Identical clone of Adani Enterprises (COMP_TOP200_017) CX_1 requisitions.'
)

print(f"Updated ACC: {acc_count}, Ambuja: {ambuja_count}, Adani Energy: {energy_count}")

# Verify Adani Enterprises still has its 25 verified active jobs
ent_jobs = Job.objects.filter(company_id='COMP_TOP200_017', status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
print(f"Adani Enterprises (COMP_TOP200_017) verified active jobs: {ent_jobs.count()}")
