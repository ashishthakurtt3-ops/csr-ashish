import os, sys
sys.path.insert(0, os.getcwd())
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models.job import Job
from modules.admin_panel.verification import public_jobs
from modules.website.views.job_api_views import apply_job_safety_filters
from collections import Counter

pub = public_jobs(Job.objects.all())
safe = apply_job_safety_filters(pub)
pub_ids = set(pub.values_list('job_id', flat=True))
safe_ids = set(safe.values_list('job_id', flat=True))
hidden_ids = pub_ids - safe_ids
print(f"Total hidden by apply_job_safety_filters: {len(hidden_ids)}")

hidden_jobs = list(Job.objects.filter(job_id__in=hidden_ids).select_related('company'))
comp_counter = Counter(j.company.company_name if j.company else 'Unknown' for j in hidden_jobs)
print("\nHidden jobs by company:")
for comp, cnt in comp_counter.most_common(15):
    print(f"  {comp}: {cnt}")

print("\nSample 25 hidden job titles, URLs and reasons:")
for j in hidden_jobs[:25]:
    print(f"  [{j.company.company_name if j.company else ''}] Title: '{j.job_title}' | URL: {j.application_url}")

