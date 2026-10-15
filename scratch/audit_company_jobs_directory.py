import json
from collections import Counter
from django.db.models import Count, Q
from modules.admin_panel.models import Company, Job

print("--- AUDITING ALL COMPANIES AND JOBS ---")
total_companies = Company.objects.count()
print(f"Total companies in database: {total_companies}")

# Overall job stats
total_jobs = Job.objects.count()
print(f"Total jobs in database: {total_jobs}")

status_counts = Counter(Job.objects.values_list('status', flat=True))
print("Job status breakdown:", dict(status_counts))

verif_counts = Counter(Job.objects.values_list('verification_status', flat=True))
print("Job verification_status breakdown:", dict(verif_counts))

# Eligible jobs according to current policy:
# status='ACTIVE', verification_status in ['PUBLISHED', 'SOURCE_CONFIRMED'], not starting with 'REQ-', not in UI_NAV_DEFECT_PATTERNS
eligible_jobs_qs = Job.objects.filter(
    status='ACTIVE',
    verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
).exclude(job_id__startswith='REQ-').exclude(verification_status__in=['LEGACY_UNVERIFIED', 'REJECTED', 'QUARANTINED'])

print(f"Eligible active verified jobs total: {eligible_jobs_qs.count()}")

# Check which companies have jobs
company_job_counts = Job.objects.values('company_id', 'company__company_name').annotate(
    total=Count('job_row_id'),
    active=Count('job_row_id', filter=Q(status='ACTIVE')),
    published=Count('job_row_id', filter=Q(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])),
    legacy=Count('job_row_id', filter=Q(verification_status='LEGACY_UNVERIFIED')),
    rejected=Count('job_row_id', filter=Q(verification_status='REJECTED'))
).order_by('-published', '-total')

print(f"Companies with at least one job record: {len(company_job_counts)}")
print("\nTop 30 companies with jobs:")
for c in company_job_counts[:30]:
    print(f"  {c['company_id']} | {c['company__company_name']}: Total={c['total']}, Active={c['active']}, Published={c['published']}, Legacy={c['legacy']}, Rejected={c['rejected']}")

# How many companies have published jobs?
comps_with_published = [c for c in company_job_counts if c['published'] > 0]
print(f"\nCompanies with published jobs count: {len(comps_with_published)}")
for c in comps_with_published:
    print(f"  -> {c['company_id']} | {c['company__company_name']}: {c['published']} published jobs")

# Companies with crawl_status
crawl_statuses = Counter(Company.objects.values_list('crawl_status', flat=True))
print("\nCompany crawl_status breakdown:", dict(crawl_statuses))

# Check foreign key nulls or anomalies
orphaned_jobs = Job.objects.filter(company__isnull=True).count()
print(f"Orphaned jobs (no company): {orphaned_jobs}")

# Check company IDs in Job vs Company
job_cids = set(Job.objects.values_list('company_id', flat=True).distinct())
company_cids = set(Company.objects.values_list('company_id', flat=True).distinct())
unknown_cids = job_cids - company_cids
print(f"Job company_ids not matching any Company: {unknown_cids}")
