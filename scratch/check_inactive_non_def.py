import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Job

inactive_non_def = Job.objects.filter(status='INACTIVE', is_defective=False)
print(f"INACTIVE with is_defective=False: {inactive_non_def.count()}")

# Sample 30 of them
for j in inactive_non_def.select_related('company')[:30]:
    print(f"[{j.job_row_id}] {j.company.company_name}: '{j.job_title}' | URL: {j.application_url or j.source_url} | Reason: {j.verification_reason}")
