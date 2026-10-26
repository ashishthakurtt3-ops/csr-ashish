"""Targeted audit2 - counts and OPEN rows only, ASCII safe"""
import datetime
from django.utils import timezone
from modules.admin_panel.models import CSROpportunity, CSRProject, Job
from django.db.models import Count

print("=== STATUS COUNTS ===")
for status, cnt in CSROpportunity.objects.values_list('status').annotate(c=Count('opp_id')).order_by('status'):
    print("  status=%-30r  count=%d" % (status, cnt))
print("  CSRProject total = %d" % CSRProject.objects.count())
print("  Job ACTIVE       = %d" % Job.objects.filter(status='ACTIVE').count())
print("  Job REMOVED      = %d" % Job.objects.filter(status='REMOVED').count())

print("\n=== OPEN CSROpportunity (id, type, deadline, first_seen) ===")
for o in CSROpportunity.objects.filter(status='OPEN').order_by('opp_id').values(
        'opp_id','opportunity_type','submission_deadline','first_seen_at','portal_url'):
    t = str(o['opportunity_type'] or '').encode('ascii','replace').decode()
    p = str(o['portal_url'] or '').encode('ascii','replace').decode()[:80]
    print("  id=%-6d type=%-30s deadline=%s first=%s" % (
        o['opp_id'], t[:28], o['submission_deadline'], o['first_seen_at']))
    print("    portal=%s" % p)

cutoff = datetime.datetime(2026, 10, 19, 11, 30, 0, tzinfo=datetime.timezone.utc)
print("\n=== NEW CSROpportunity rows first_seen >= 2026-10-19 11:30 UTC ===")
new_opps = CSROpportunity.objects.filter(first_seen_at__gte=cutoff)
print("  Count: %d" % new_opps.count())
by_status = new_opps.values('status').annotate(c=Count('opp_id'))
for row in by_status:
    print("    status=%-20s count=%d" % (row['status'], row['c']))

print("\nTIMESTAMP: %s" % timezone.now().isoformat())
