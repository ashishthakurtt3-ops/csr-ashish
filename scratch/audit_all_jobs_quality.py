import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models.company import Company
from modules.admin_panel.models.job import Job

# Inspect all jobs in the database
total_jobs = Job.objects.count()
print(f"Total jobs in DB: {total_jobs}")

# Let's inspect by status and verification status
from django.db.models import Count
breakdown = Job.objects.values('status', 'verification_status').annotate(cnt=Count('job_row_id')).order_by('-cnt')
for b in breakdown:
    print(f"Status: {b['status']:<12} | Verif: {b['verification_status']:<20} | Count: {b['cnt']}")

# Check overseas jobs
overseas_jobs = Job.objects.exclude(country='India').exclude(country__isnull=True).exclude(country='')
print(f"Non-India jobs: {overseas_jobs.count()}")
for oj in overseas_jobs[:10]:
    print(f"  {oj.company.company_name} | {oj.job_title} | {oj.country} | {oj.status} | {oj.verification_status}")

# Check jobs with blank titles
blank_title = Job.objects.filter(job_title__isnull=True) | Job.objects.filter(job_title='')
print(f"Blank title jobs: {blank_title.count()}")

# Check jobs with blank application_url
blank_app = Job.objects.filter(application_url__isnull=True) | Job.objects.filter(application_url='')
print(f"Blank application_url jobs: {blank_app.count()}")

# Check jobs with button/UI defect titles
ui_defects = Job.objects.filter(job_title__icontains='Review Accommodations') | Job.objects.filter(job_title__icontains='Upload Resume') | Job.objects.filter(job_title__icontains='Next >>')
print(f"UI defect jobs: {ui_defects.count()}")
