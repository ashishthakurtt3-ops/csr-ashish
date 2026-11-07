import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from modules.admin_panel.models import Job, Company, CSRProject

fields = [f.name for f in Job._meta.get_fields()]
print('Job fields:', fields)

print('Total Jobs in DB:', Job.objects.count())

for j in Job.objects.all()[:25]:
    url = getattr(j, 'apply_url', None)
    print(f"Company: {j.company.company_name[:20]:20} | Title: {j.job_title[:30]:30} | Apply: {url} | Status: {j.status}")
