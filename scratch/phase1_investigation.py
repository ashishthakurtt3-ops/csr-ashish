import os
import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
import django
from django.db.models import Count, Q
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, Company
from django.db import connection

print("=== 1. JOB FIELDS & TYPES ===")
fields = [(f.name, f.get_internal_type()) for f in Job._meta.get_fields() if hasattr(f, 'get_internal_type')]
for name, ftype in sorted(fields):
    print(f"{name}: {ftype}")

print("\n=== 2. FIELD POPULATION STATS ===")
total = Job.objects.count()
print(f"Total jobs: {total}")
for f in ['job_description', 'responsibilities', 'qualifications', 'education', 'skills', 
          'experience', 'benefits', 'salary', 'work_mode', 'employment_type', 
          'posted_date', 'application_deadline', 'external_job_id', 'canonical_url']:
    has_val = Job.objects.filter(~Q(**{f: None}) & ~Q(**{f: ''})).count()
    pct = (has_val / total) * 100 if total else 0
    print(f"{f}: {has_val} / {total} ({pct:.1f}%)")

print("\n=== 3. DUPLICATE ANALYSIS ===")
# 3.1 by (company_id, application_url)
dups_url = (Job.objects.exclude(application_url__isnull=True).exclude(application_url='')
            .values('company_id', 'application_url')
            .annotate(cnt=Count('job_row_id'))
            .filter(cnt__gt=1)
            .order_by('-cnt'))
print(f"Duplicate groups by (company_id, application_url): {dups_url.count()}")
total_dup_url_rows = sum(d['cnt'] for d in dups_url)
print(f"Total rows involved in (company_id, application_url) duplicates: {total_dup_url_rows}")
for d in list(dups_url)[:5]:
    c = Company.objects.get(pk=d['company_id'])
    print(f"  Company {c.company_name} ({d['company_id']}), cnt={d['cnt']}, url={d['application_url'][:80]}")

# 3.2 by (company_id, job_title, location)
dups_title_loc = (Job.objects.values('company_id', 'job_title', 'location')
                  .annotate(cnt=Count('job_row_id'))
                  .filter(cnt__gt=1)
                  .order_by('-cnt'))
print(f"\nDuplicate groups by (company_id, job_title, location): {dups_title_loc.count()}")
total_dup_title_loc_rows = sum(d['cnt'] for d in dups_title_loc)
print(f"Total rows involved in (company_id, job_title, location) duplicates: {total_dup_title_loc_rows}")
for d in list(dups_title_loc)[:5]:
    c = Company.objects.get(pk=d['company_id'])
    print(f"  Company {c.company_name}, cnt={d['cnt']}, title={d['job_title'][:40]}, loc={d['location']}")

# 3.3 by (company_id, external_job_id)
dups_ext = (Job.objects.exclude(external_job_id__isnull=True).exclude(external_job_id='')
            .values('company_id', 'external_job_id')
            .annotate(cnt=Count('job_row_id'))
            .filter(cnt__gt=1)
            .order_by('-cnt'))
print(f"\nDuplicate groups by (company_id, external_job_id): {dups_ext.count()}")
for d in list(dups_ext)[:5]:
    c = Company.objects.get(pk=d['company_id'])
    print(f"  Company {c.company_name}, cnt={d['cnt']}, ext_id={d['external_job_id']}")

print("\n=== 4. ATS PLATFORMS PRESENT ===")
for row in Job.objects.values('ats_platform').annotate(cnt=Count('job_row_id')).order_by('-cnt'):
    print(f"  {row['ats_platform']}: {row['cnt']}")

print("\n=== 5. PICK 5 REAL JOBS ACROSS DIFFERENT ATS PLATFORMS ===")
sample_jobs = []
for ats in ['SuccessFactors', 'Workday', 'Taleo', 'Greenhouse', 'Lever', 'SmartRecruiters', 'Oracle Cloud', None]:
    if ats:
        j = Job.objects.filter(ats_platform__icontains=ats, application_url__startswith='http').first()
    else:
        j = Job.objects.filter(ats_platform__isnull=True, application_url__startswith='http').first()
    if j:
        sample_jobs.append(j)
    if len(sample_jobs) >= 6:
        break

for j in sample_jobs:
    print(f"\nJob ID: {j.job_row_id} | Company: {j.company.company_name} | ATS: {j.ats_platform}")
    print(f"Title: {j.job_title} | Location: {j.location}")
    print(f"Apply URL: {j.application_url}")
    print(f"Description length: {len(j.job_description or '')}")
    print(f"Responsibilities present: {bool(j.responsibilities)}")
    print(f"Qualifications present: {bool(j.qualifications)}")
    print(f"Education present: {bool(j.education)}")
    print(f"Skills present: {bool(j.skills)}")
    print(f"Benefits present: {bool(j.benefits)}")
    print(f"Detail fetched: {j.detail_fetched} | Status: {j.detail_fetch_status}")
