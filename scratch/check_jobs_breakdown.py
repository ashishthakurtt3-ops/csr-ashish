import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models.company import Company
from modules.admin_panel.models.job import Job
from collections import Counter

c_sample = Company.objects.get(company_id='COMP_TOP200_160') # 3i Infotech
print(f"Company: {c_sample.company_name} ({c_sample.company_id})")
print(f"Website: {c_sample.website_url}")
print(f"Careers URL: {c_sample.careers_url}")

sample_jobs = Job.objects.filter(company=c_sample)
print(f"Jobs count: {sample_jobs.count()}")
for j in sample_jobs[:5]:
    print(f"  Job {j.job_id}: {j.job_title}")
    print(f"    Location: {j.location}, Country: {j.country}")
    print(f"    App URL: {j.application_url}")
    print(f"    Source URL: {j.source_url}")
    print(f"    Status: {j.status}, Verification: {j.verification_status}")
    print(f"    Link Status: {j.link_status}")

# Check breakdown across all 180 zero-active companies
zero_comp_ids = [c.company_id for c in Company.objects.all() if Job.objects.filter(company=c, status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count() == 0]
jobs_zero = Job.objects.filter(company_id__in=zero_comp_ids)

status_counter = Counter(jobs_zero.values_list('status', flat=True))
verif_counter = Counter(jobs_zero.values_list('verification_status', flat=True))
country_counter = Counter(jobs_zero.values_list('country', flat=True))

print("\n--- 180 Companies Job Stats ---")
print("Total jobs in these 180 companies:", jobs_zero.count())
print("Status breakdown:", status_counter)
print("Verification breakdown:", verif_counter)
print("Country breakdown:", country_counter.most_common(10))
