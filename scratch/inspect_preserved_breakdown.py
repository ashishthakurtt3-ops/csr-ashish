import json
from collections import Counter

with open('reports/audit/jobs_audit_classification.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('Fabricated count:', data['confirmed_fabricated_count'])
print('Preserved count:', data['preserved_count'])

# Breakdown of preserved
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
django.setup()

from modules.admin_panel.models import Job

# Let's inspect preserved statuses
preserved_ids = set(Job.objects.values_list('job_row_id', flat=True)) - {r['id'] for r in data['fabricated_records']}
print('Preserved ids count:', len(preserved_ids))

for row in Job.objects.filter(job_row_id__in=preserved_ids).values('status', 'verification_status').annotate(cnt=django.db.models.Count('job_row_id')):
    print(row)
