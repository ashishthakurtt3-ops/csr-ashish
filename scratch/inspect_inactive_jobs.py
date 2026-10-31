import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from collections import Counter
from modules.admin_panel.models import Job

# 1. Inspect INACTIVE / REJECTED (3,123 jobs)
inactive_jobs = Job.objects.filter(status='INACTIVE')
print(f"Total INACTIVE jobs: {inactive_jobs.count()}")
print("Verification reason sample for INACTIVE:")
for r, c in Counter(inactive_jobs.values_list('verification_reason', flat=True)).most_common(10):
    print(f"  '{r}': {c}")

print("\nLink check reason sample for INACTIVE:")
for r, c in Counter(inactive_jobs.values_list('link_check_reason', flat=True)).most_common(10):
    print(f"  '{r}': {c}")

print("\nSample 15 INACTIVE job titles, companies, and URLs:")
for j in inactive_jobs.select_related('company')[:15]:
    print(f"  [{j.job_row_id}] {j.company.company_name}: '{j.job_title[:50]}' | url: {j.application_url or j.source_url} | reason: {j.verification_reason}")
