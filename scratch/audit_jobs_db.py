import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.models import Job, Company
from django.db.models import Count

print("=== TOTAL JOBS IN DATABASE ===")
total = Job.objects.count()
print(f"Total Jobs: {total}")

print("\n=== JOBS BY COMPANY ===")
by_comp = Job.objects.values('company__company_id', 'company__company_name').annotate(cnt=Count('job_row_id')).order_by('-cnt')
for row in by_comp:
    print(f"{row['company__company_id']}: {row['company__company_name']} -> {row['cnt']} jobs")

print("\n=== JOBS BY VERIFICATION STATUS ===")
for row in Job.objects.values('verification_status').annotate(cnt=Count('job_row_id')):
    print(f"{row['verification_status']}: {row['cnt']}")

print("\n=== JOBS BY STATUS ===")
for row in Job.objects.values('status').annotate(cnt=Count('job_row_id')):
    print(f"{row['status']}: {row['cnt']}")

print("\n=== EVIDENCE AUDIT ===")
missing_source = Job.objects.filter(source_url__isnull=True).count()
missing_evidence = Job.objects.filter(evidence_text__isnull=True).count()
print(f"Missing source_url: {missing_source}")
print(f"Missing evidence_text: {missing_evidence}")

test_jobs = Job.objects.filter(job_title__icontains='test').exclude(job_title__icontains='quality').exclude(job_title__icontains='software').exclude(job_title__icontains='automation')
print(f"Potential test job records: {test_jobs.count()}")
for tj in test_jobs:
    print(f" - {tj.job_id}: {tj.job_title} | {tj.company.company_name}")
