import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from collections import Counter
from modules.admin_panel.models import Job

inactive_jobs = Job.objects.filter(status='INACTIVE')

# Check distribution of companies among INACTIVE
comp_counter = Counter(inactive_jobs.values_list('company__company_name', flat=True))
print("Companies with INACTIVE jobs:")
for c, cnt in comp_counter.most_common(20):
    print(f"  {c}: {cnt}")

# Check INACTIVE jobs that are NOT Yes Bank, NOT UltraTech, NOT Infosys marketing
other_inactive = inactive_jobs.exclude(
    verification_reason__icontains='YES Bank'
).exclude(
    verification_reason__icontains='UltraTech'
).exclude(
    verification_reason__icontains='Infosys'
)
print(f"\nOther INACTIVE jobs count: {other_inactive.count()}")
print("Reasons for other INACTIVE jobs:")
for r, cnt in Counter(other_inactive.values_list('verification_reason', flat=True)).most_common(15):
    print(f"  '{r}': {cnt}")

print("\nSample 20 other INACTIVE jobs:")
for j in other_inactive.select_related('company')[:20]:
    cname = j.company.company_name if j.company else "No Company"
    print(f"  [{j.job_row_id}] {cname}: '{j.job_title}' | URL: {j.application_url or j.source_url} | is_defective: {j.is_defective}")
