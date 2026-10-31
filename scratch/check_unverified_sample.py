import json
from collections import Counter

with open('reports/audit/confirmed_fabricated_records_20261029_163718.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
django.setup()

from modules.admin_panel.models import Job

deleted_ids = {r['id'] for r in data['deleted_records'] if r['entity'] == 'Job'}
preserved = Job.objects.exclude(job_row_id__in=deleted_ids)

unverified = [j for j in preserved if j.status not in ('ACTIVE', 'EXPIRED', 'STALE') and j.status != 'REMOVED']
print('Unverified count:', len(unverified))
for j in unverified[:15]:
    t = (j.job_title[:40] or '').encode('ascii', 'replace').decode('ascii')
    u = (j.application_url[:65] or '').encode('ascii', 'replace').decode('ascii')
    print(f'[{j.company.company_name[:20]}] {t} -> {u}')
