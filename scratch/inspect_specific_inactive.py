import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
django.setup()

from modules.admin_panel.models import Job

for cname in ['Infosys Limited', 'Aadhar Housing Finance Limited', 'Tata Consultancy Services Limited', 'Canara Bank', 'RBL Bank Limited']:
    print(f'=== {cname} ===')
    for j in Job.objects.filter(company__company_name=cname, status='INACTIVE')[:8]:
        t = (j.job_title[:45] or '').encode('ascii', 'replace').decode('ascii')
        u = (j.application_url[:70] or '').encode('ascii', 'replace').decode('ascii')
        print(f'  [{j.job_row_id}] {t!r} -> {u}')
