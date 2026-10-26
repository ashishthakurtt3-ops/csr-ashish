import os, sys, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.utils import timezone
from django.db.models import Count, Q
from modules.admin_panel.models import CSROpportunity, CSRProject, Job, Company, CompanyCrawlSummary

print("=" * 80)
print("1. CSROpportunity STATUS BREAKDOWN")
print("=" * 80)
for row in CSROpportunity.objects.values('status').annotate(cnt=Count('opp_id')).order_by('-cnt'):
    print(f"  status: {row['status']:<25} count: {row['cnt']}")

print(f"  TOTAL CSROpportunities: {CSROpportunity.objects.count()}")

print("\n" + "=" * 80)
print("2. CSRProject COUNT")
print("=" * 80)
print(f"  TOTAL CSRProjects: {CSRProject.objects.count()}")

print("\n" + "=" * 80)
print("3. Job STATUS BREAKDOWN")
print("=" * 80)
for row in Job.objects.values('status').annotate(cnt=Count('job_id')).order_by('-cnt'):
    print(f"  status: {row['status']:<25} count: {row['cnt']}")
print(f"  TOTAL Jobs: {Job.objects.count()}")

print("\n" + "=" * 80)
print("4. ALL OPEN CSROpportunities (Detailed)")
print("=" * 80)
open_opps = CSROpportunity.objects.filter(status='OPEN').order_by('opp_id')
print(f"Total OPEN: {open_opps.count()}")
for o in open_opps:
    print(f"ID: {o.opp_id} | Co: {o.company.company_name if o.company else 'None'}")
    print(f"  Title: {o.title}")
    print(f"  Type: {o.opportunity_type}")
    print(f"  Deadline: {o.submission_deadline}")
    print(f"  Portal URL: {o.portal_url}")
    print(f"  Source URL: {o.source_url}")
    print(f"  First seen: {o.first_seen_at} | Last seen: {o.last_seen_at}")
    print(f"  Evidence: {repr(o.evidence_text[:100]) if o.evidence_text else 'None'}")
    print("-" * 40)

print("\n" + "=" * 80)
print("5. RECENT CRAWLS in CompanyCrawlSummary (Last 20)")
print("=" * 80)
for s in CompanyCrawlSummary.objects.order_by('-crawl_started_at')[:20]:
    print(f"Started: {s.crawl_started_at} | Co: {s.company.company_name if s.company else 'None':<25} | Status: {s.crawl_status:<10} | Disc: {s.jobs_discovered} | Pub: {s.jobs_published} | Exp: {s.jobs_expired}")

print("\n" + "=" * 80)
print("6. CSROpportunity CREATION CHRONOLOGY")
print("=" * 80)
# Group by date or inspect min/max
print(f"Earliest first_seen_at: {CSROpportunity.objects.order_by('first_seen_at').values_list('first_seen_at', flat=True).first()}")
print(f"Latest first_seen_at:   {CSROpportunity.objects.order_by('-first_seen_at').values_list('first_seen_at', flat=True).first()}")

