import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
django.setup()

from modules.admin_panel.models import Job
from django.db.models import Count

for r in Job.objects.filter(status='INACTIVE', verification_status='REJECTED').values('company__company_name').annotate(cnt=Count('job_row_id')).order_by('-cnt')[:25]:
    print(r['company__company_name'], ':', r['cnt'])
