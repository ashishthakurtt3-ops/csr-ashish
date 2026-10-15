"""
Comprehensive database reconciliation and audit script.
Investigates the history, origin, and exact status of:
- Total records (5,493)
- The previous 3,856 'active' figure vs current 964
- Legacy seed records (e.g. REQ-*)
- Extraction failure breakdown
- Quarantined / rejected records
- Company coverage
"""
import os, sys, django
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings
from modules.admin_panel.models import Job, Company
from django.db.models import Count, Q

print("=" * 80)
print("SECTION 1: DATABASE CONFIGURATION & ENVIRONMENT VERIFICATION")
print("=" * 80)
print("Django Settings Module:", os.environ.get('DJANGO_SETTINGS_MODULE'))
print("Database Engine:", settings.DATABASES['default']['ENGINE'])
print("Database Name:", settings.DATABASES['default']['NAME'])
print("Total Records in Job table:", Job.objects.count())
print("Total Companies in Company table:", Company.objects.count())

print("\n" + "=" * 80)
print("SECTION 2: RECONCILING THE 3,856 PREVIOUS 'ACTIVE' vs 964 CURRENT ACTIVE")
print("=" * 80)

# How were jobs created? Look at job_id patterns
id_prefixes = defaultdict(int)
for j in Job.objects.values('job_id'):
    jid = j['job_id'] or ''
    if jid.startswith('REQ-'):
        prefix = 'REQ-* (Legacy Seed)'
    elif jid.startswith('JOB_COMP_TOP200_'):
        prefix = 'JOB_COMP_TOP200_* (Crawler/Spider)'
    elif jid.startswith('JOB_'):
        prefix = 'JOB_* (Other Crawler)'
    else:
        prefix = 'Other / None'
    id_prefixes[prefix] += 1

print("\n--- JOB ID PATTERNS (TOTAL DATA POOL) ---")
for p, count in sorted(id_prefixes.items(), key=lambda x: -x[1]):
    print(f"  {p:45}: {count}")

# Now examine how those ID patterns break down by status
print("\n--- ID PATTERNS BY STATUS ---")
for prefix_label, condition in [
    ("REQ-* (Legacy Seed)", Q(job_id__startswith='REQ-')),
    ("JOB_COMP_TOP200_* (Real Crawler)", Q(job_id__startswith='JOB_COMP_TOP200_')),
    ("Other", ~Q(job_id__startswith='REQ-') & ~Q(job_id__startswith='JOB_COMP_TOP200_'))
]:
    print(f"\n  Pattern: {prefix_label}")
    sub = Job.objects.filter(condition)
    for r in sub.values('status', 'verification_status', 'detail_fetch_status').annotate(c=Count('pk')).order_by('-c'):
        print(f"    status={r['status']:10} | verif={r['verification_status']:18} | fetch={r['detail_fetch_status']:18} | count={r['c']}")

# Let's inspect the 3,856 number origin
# 3,856 was 1,712 fetched + 2,144 extraction failures
print("\n--- EXAMINING PREVIOUS 3,856 'ACTIVE' COUNT ---")
# If we count all jobs that used to have status='ACTIVE' or were previously counted without verification filtering:
real_crawler_jobs = Job.objects.filter(job_id__startswith='JOB_COMP_TOP200_')
print(f"Total Real Crawler Jobs (JOB_COMP_TOP200_*): {real_crawler_jobs.count()}")
print(f"  Active: {real_crawler_jobs.filter(status='ACTIVE').count()}")
print(f"  Inactive: {real_crawler_jobs.filter(status='INACTIVE').count()}")
print(f"  Expired: {real_crawler_jobs.filter(status='EXPIRED').count()}")

legacy_seed_jobs = Job.objects.filter(job_id__startswith='REQ-')
print(f"Total Legacy Seed Jobs (REQ-*): {legacy_seed_jobs.count()}")
print(f"  Active: {legacy_seed_jobs.filter(status='ACTIVE').count()}")
print(f"  Inactive: {legacy_seed_jobs.filter(status='INACTIVE').count()}")
print(f"  Expired: {legacy_seed_jobs.filter(status='EXPIRED').count()}")

# Why were 2,129 jobs set to INACTIVE with EXTRACTION_FAILED?
print("\n--- WHY ARE 2,129 JOBS INACTIVE with EXTRACTION_FAILED? ---")
inactive_ef = Job.objects.filter(status='INACTIVE', detail_fetch_status='EXTRACTION_FAILED')
print(f"Total Inactive EXTRACTION_FAILED: {inactive_ef.count()}")
for r in inactive_ef.values('verification_status', 'verification_reason').annotate(c=Count('pk')).order_by('-c')[:15]:
    reason = (r['verification_reason'] or 'No reason specified')[:60]
    print(f"  verif={r['verification_status']:20} | count={r['c']:5} | reason={reason}")

# Sample titles of inactive EXTRACTION_FAILED
print("\n--- SAMPLE TITLES OF INACTIVE EXTRACTION_FAILED (First 20) ---")
for t in inactive_ef.values('job_title', 'company__company_name').distinct()[:20]:
    print(f"  Title: {t['job_title'][:40]:40} | Company: {t['company__company_name'][:30]}")

print("\n" + "=" * 80)
print("SECTION 3: EXACT COUNTS BEFORE AND AFTER RECONCILIATION")
print("=" * 80)
total_records = Job.objects.count()
canonical_companies = Company.objects.count()
active_jobs = Job.objects.filter(status='ACTIVE').count()
published_eligible = Job.objects.filter(status='ACTIVE', verification_status='PUBLISHED').count()
legacy_seeds_quarantined = Job.objects.filter(job_id__startswith='REQ-').count()
rejected_records = Job.objects.filter(verification_status='REJECTED').count()
quarantined_records = Job.objects.filter(verification_status='QUARANTINED').count()
inactive_records = Job.objects.filter(status='INACTIVE').count()
expired_records = Job.objects.filter(status='EXPIRED').count()
fetched_records = Job.objects.filter(detail_fetch_status='FETCHED').count()
active_fetched = Job.objects.filter(status='ACTIVE', detail_fetch_status='FETCHED').count()
extraction_failures_total = Job.objects.filter(detail_fetch_status='EXTRACTION_FAILED').count()
active_extraction_failures = Job.objects.filter(status='ACTIVE', detail_fetch_status='EXTRACTION_FAILED').count()
awaiting_verification = Job.objects.filter(verification_status__in=['EXTRACTED', 'VALIDATED', 'SOURCE_CONFIRMED']).count()

print(f"1. Total database records:              {total_records}")
print(f"2. Canonical companies:                 {canonical_companies}")
print(f"3. Active jobs:                         {active_jobs}")
print(f"4. Published eligible jobs:             {published_eligible}")
print(f"5. Legacy seed records quarantined:     {legacy_seeds_quarantined}")
print(f"6. Rejected records (UI defects/links): {rejected_records}")
print(f"7. Quarantined records:                 {quarantined_records}")
print(f"8. Inactive records:                    {inactive_records}")
print(f"9. Expired records:                     {expired_records}")
print(f"10. Successfully fetched detail pages:  {fetched_records} (Active: {active_fetched})")
print(f"11. Extraction failures:                {extraction_failures_total} (Active: {active_extraction_failures})")
print(f"12. Records awaiting verification:      {awaiting_verification}")

print("\n" + "=" * 80)
print("SECTION 4: ACTIVE JOBS BY COMPANY & ATS BREAKDOWN")
print("=" * 80)
companies_with_active = Company.objects.filter(jobs__status='ACTIVE').annotate(active_c=Count('jobs', filter=Q(jobs__status='ACTIVE'))).distinct()
print(f"Distinct companies with ACTIVE jobs: {companies_with_active.count()} / 200")
for c in companies_with_active.order_by('-active_c')[:25]:
    print(f"  {c.company_id}: {c.company_name[:35]:35} | Active Jobs: {c.active_c}")
