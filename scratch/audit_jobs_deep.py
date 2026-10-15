import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, Company
from django.db.models import Count

print("=== JOB STATUS DISTRIBUTION ===")
for row in Job.objects.values('status', 'verification_status').annotate(cnt=Count('job_row_id')).order_by('-cnt'):
    print(f"status={row['status']} | verification_status={row['verification_status']} | count={row['cnt']}")

print("\n=== COMPANIES WITH ACTIVE BUT NON-PUBLISHED JOBS ===")
active_nonpub = Job.objects.filter(status='ACTIVE').exclude(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
print(f"Total active non-published: {active_nonpub.count()}")

print("\n=== COMPANIES WITH PUBLISHED BUT NON-ACTIVE JOBS ===")
pub_nonactive = Job.objects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).exclude(status='ACTIVE')
print(f"Total published non-active: {pub_nonactive.count()}")
for row in pub_nonactive.values('company_id', 'company__company_name', 'status').annotate(cnt=Count('job_row_id')):
    print(f"{row['company_id']} | {row['company__company_name']} | status={row['status']} | count={row['cnt']}")

print("\n=== CHECKING ALL 200 COMPANIES: TOTAL JOBS VS ACTIVE PUBLISHED ===")
comps_with_jobs_not_published = []
for c in Company.objects.all().order_by('company_id'):
    total_j = c.jobs.count()
    active_pub = c.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
    if total_j > 0 and active_pub == 0:
        comps_with_jobs_not_published.append((c.company_id, c.company_name, total_j, [j.verification_status for j in c.jobs.all()[:3]]))

print(f"Companies with jobs in DB but 0 active published: {len(comps_with_jobs_not_published)}")
for cid, cname, tj, sample_st in comps_with_jobs_not_published[:10]:
    print(f"  {cid} | {cname} | total_jobs={tj} | sample_statuses={sample_st}")
