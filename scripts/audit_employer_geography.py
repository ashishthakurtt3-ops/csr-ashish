"""
Audit employer identity, legal entity association, and geography across all 964 active published jobs.
Checks:
- Country breakdown (India vs International)
- Employer entity / subsidiary name
- Work mode (Remote / Hybrid / On-site / Not mentioned)
- Location granularity (city, state, country)
"""
import os, sys, django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, Company
from django.db.models import Count, Q

print("=" * 80)
print("SECTION 6: AUDITING EMPLOYER IDENTITY & INTERNATIONAL ASSOCIATIONS")
print("=" * 80)

active_jobs = Job.objects.filter(status='ACTIVE', verification_status='PUBLISHED').select_related('company')

# 1. Geographic distribution of all active published jobs
print("\n--- COUNTRY BREAKDOWN ---")
for r in active_jobs.values('country').annotate(c=Count('pk')).order_by('-c'):
    print(f"  {r['country'] or 'Unspecified/None':25}: {r['c']}")

# 2. International jobs inspection
intl_jobs = active_jobs.exclude(Q(country__iexact='India') | Q(country__iexact='IN') | Q(country__isnull=True) | Q(country=''))
print(f"\nTotal International Postings: {intl_jobs.count()}")

print("\n--- INTERNATIONAL JOBS BY COMPANY ---")
for r in intl_jobs.values('company__company_id', 'company__company_name', 'country').annotate(c=Count('pk')).order_by('-c'):
    print(f"  {r['company__company_id']} | {r['company__company_name'][:30]:30} | Country: {r['country']:15} | Count: {r['c']}")

# Inspect Hindustan Unilever international jobs:
hul_intl = intl_jobs.filter(company__company_id='COMP_TOP200_009')
print(f"\n--- HINDUSTAN UNILEVER LIMITED (COMP_TOP200_009) INTERNATIONAL JOBS ({hul_intl.count()}) ---")
for j in hul_intl[:10]:
    print(f"  Job ID: {j.job_id} | Title: {j.job_title[:35]:35} | Loc: {j.location} | Country: {j.country}")
    print(f"    Source URL: {j.source_url}")
    print(f"    App URL:    {j.application_url}")

# Inspect Dr. Reddy's international jobs:
drl_intl = intl_jobs.filter(company__company_id='COMP_TOP200_106')
print(f"\n--- DR. REDDY'S LABORATORIES (COMP_TOP200_106) INTERNATIONAL JOBS ({drl_intl.count()}) ---")
for j in drl_intl[:10]:
    print(f"  Job ID: {j.job_id} | Title: {j.job_title[:35]:35} | Loc: {j.location} | Country: {j.country}")
    print(f"    Source URL: {j.source_url}")
    print(f"    App URL:    {j.application_url}")

# 3. Work mode breakdown
print("\n--- WORK MODE BREAKDOWN ---")
for r in active_jobs.values('work_mode').annotate(c=Count('pk')).order_by('-c'):
    print(f"  {r['work_mode'] or 'Not mentioned by source':25}: {r['c']}")

# 4. Salary breakdown
print("\n--- SALARY / PAY BAND BREAKDOWN ---")
with_salary = active_jobs.exclude(Q(salary__isnull=True) | Q(salary=''))
print(f"Jobs with salary: {with_salary.count()}")
with_pay_band = active_jobs.exclude(Q(pay_band__isnull=True) | Q(pay_band=''))
print(f"Jobs with pay_band: {with_pay_band.count()}")
for pb in with_pay_band.values('company__company_name', 'pay_band').distinct():
    print(f"  {pb['company__company_name'][:30]}: {pb['pay_band']}")
