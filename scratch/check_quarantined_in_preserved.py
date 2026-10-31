import json
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
django.setup()

from modules.admin_panel.models import Job

with open('reports/audit/jobs_audit_classification.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

fab_ids = {r['id'] for r in data['fabricated_records']}
quarantined_jobs = Job.objects.filter(verification_status='QUARANTINED')
quarantined_in_preserved = [j for j in quarantined_jobs if j.job_row_id not in fab_ids]
print('Quarantined jobs not in fabricated:', len(quarantined_in_preserved))

for j in quarantined_in_preserved[:10]:
    print(j.job_row_id, j.company.company_name, repr(j.job_title), repr(j.application_url))
