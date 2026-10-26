"""Phase 1 audit - run as manage.py shell < this_file or python manage.py runscript"""
import datetime
from django.utils import timezone
from modules.admin_panel.models import CSROpportunity, CSRProject, Job
from modules.crawler_engine.models import CompanyCrawlSummary
from django.db.models import Count

SEP = "=" * 70

print(SEP)
print("STATUS COUNTS")
print(SEP)
for status, cnt in CSROpportunity.objects.values_list('status').annotate(c=Count('opp_id')).order_by('status'):
    print(f"  CSROpportunity status={repr(status):30s} count={cnt}")
print(f"  CSRProject total       = {CSRProject.objects.count()}")
active_j = Job.objects.filter(status='ACTIVE').count()
removed_j = Job.objects.filter(status='REMOVED').count()
print(f"  Job ACTIVE             = {active_j}")
print(f"  Job REMOVED            = {removed_j}")
print(f"  Job total              = {Job.objects.count()}")

print()
print(SEP)
print("ALL OPEN CSROpportunity rows")
print(SEP)
for o in CSROpportunity.objects.filter(status='OPEN').order_by('opp_id').values(
        'opp_id','title','submission_deadline','portal_url','source_url','opportunity_type','first_seen_at'):
    print(f"  id={o['opp_id']} type={o['opportunity_type']}  deadline={o['submission_deadline']}")
    print(f"    title={str(o['title'])[:80]}")
    print(f"    portal={o['portal_url']}")
    print(f"    source={o['source_url']}")
    print(f"    first_seen={o['first_seen_at']}")

print()
cutoff = datetime.datetime(2026, 10, 19, 6, 0, 0, tzinfo=datetime.timezone.utc)
print(SEP)
print("CRAWL HISTORY since 2026-10-19 06:00 UTC (all entries)")
print(SEP)
qs = CompanyCrawlSummary.objects.filter(crawl_started_at__gte=cutoff).order_by('crawl_started_at')
print(f"  Total crawl summaries since cutoff: {qs.count()}")
for s in qs.values('company__company_name','crawl_started_at','crawl_status','jobs_discovered','jobs_published','jobs_expired'):
    ts = s['crawl_started_at'].strftime('%H:%M:%S')
    print(f"  {ts}  {str(s['company__company_name'])[:28]:28s}  {s['crawl_status']:12s}  disc={s['jobs_discovered']:4}  pub={s['jobs_published']:4}  exp={s['jobs_expired']}")

print()
print(SEP)
print("NEW CSROpportunity rows first_seen >= cutoff")
print(SEP)
new_opps = CSROpportunity.objects.filter(first_seen_at__gte=cutoff)
print(f"  Count: {new_opps.count()}")
for o in new_opps.order_by('first_seen_at').values('opp_id','status','title','first_seen_at'):
    print(f"  id={o['opp_id']} status={str(o['status'])[:20]:20s} first={o['first_seen_at']} title={str(o['title'])[:55]}")

print()
print(f"TIMESTAMP: {timezone.now().isoformat()}")
