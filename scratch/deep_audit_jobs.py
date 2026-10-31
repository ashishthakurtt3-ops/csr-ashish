import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from collections import Counter
from modules.admin_panel.models import Job, CSRProject, CSROpportunity

print("=== DEEP AUDIT OF JOB STATUSES ===")
for status in ['ACTIVE', 'INACTIVE', 'QUARANTINED', 'EXPIRED', 'REMOVED', 'NEEDS_REVIEW']:
    qs = Job.objects.filter(status=status)
    cnt = qs.count()
    # Check how many have is_defective=True
    def_cnt = qs.filter(is_defective=True).count()
    ver_breakdown = dict(Counter(qs.values_list('verification_status', flat=True)))
    print(f"\nStatus: {status} (Total: {cnt}, is_defective: {def_cnt})")
    print(f"  Verification statuses: {ver_breakdown}")
    # Sample 5 titles and URLs
    print("  Sample records:")
    for j in qs.select_related('company')[:5]:
        cname = j.company.company_name if j.company else "No Company"
        print(f"    [{j.job_row_id}] {cname}: '{j.job_title[:40]}' | url: {j.application_url or j.source_url} | reason: {j.verification_reason}")
