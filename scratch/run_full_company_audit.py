import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from modules.admin_panel.models import Company, Job
from modules.website.views.company_api_views import serialize_company_list_item, recommendations_api
import json

companies = list(Company.objects.all().order_by('company_id'))
print(f"Total Canonical Companies: {len(companies)}")

# Call recommendations_api to get API-reported job counts
rf = RequestFactory()
req = rf.get('/recommendations?limit=200')
resp = recommendations_api(req)
api_data = json.loads(resp.content.decode('utf-8'))
api_items = api_data if isinstance(api_data, list) else api_data.get('items', [])
api_map = {item['company_id']: item for item in api_items}

audit_rows = []
mismatches = []

for c in companies:
    cid = c.company_id
    cname = c.company_name

    # Database independent queries
    total_jobs = c.jobs.count()
    active_jobs = c.jobs.filter(status='ACTIVE').count()
    published_eligible = c.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
    verified_eligible = published_eligible # under project policy, active + published/source_confirmed = eligible for public display
    legacy_quarantined = c.jobs.filter(verification_status='LEGACY_UNVERIFIED').count()
    quarantined = c.jobs.filter(verification_status='QUARANTINED').count()
    rejected = c.jobs.filter(verification_status='REJECTED').count()
    stale_expired = c.jobs.filter(verification_status='STALE').count()
    pending_verification = c.jobs.filter(status='ACTIVE', verification_status='PENDING').count()

    careers_url = c.careers_url or c.jobs_page_url or ''
    ats = c.ats_platform or 'Custom / In-house'
    last_check = c.last_crawled or c.link_verified_at or 'Pending'
    crawl_outcome = c.crawl_status

    # API reported count
    api_item = api_map.get(cid, {})
    api_count = api_item.get('job_count', 0)
    api_status_state = api_item.get('job_status_state', '')

    # Card count (from serialize_company_list_item)
    card_item = serialize_company_list_item(c)
    card_count = card_item.get('job_count', 0)
    card_state = card_item.get('job_status_state', '')

    # Verify reconciliation: DB Eligible == API Count == Card Count
    if verified_eligible != api_count or verified_eligible != card_count:
        mismatches.append({
            'company_id': cid,
            'name': cname,
            'db_count': verified_eligible,
            'api_count': api_count,
            'card_count': card_count
        })

    audit_rows.append({
        'company_id': cid,
        'name': cname,
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'published_eligible': published_eligible,
        'verified_eligible': verified_eligible,
        'legacy_quarantined': legacy_quarantined,
        'quarantined': quarantined,
        'rejected': rejected,
        'stale_expired': stale_expired,
        'pending_verification': pending_verification,
        'careers_url': careers_url,
        'ats': ats,
        'last_check': str(last_check),
        'crawl_outcome': crawl_outcome,
        'api_count': api_count,
        'card_count': card_count,
        'card_state': card_state
    })

print(f"Audit completed. Total Mismatches: {len(mismatches)}")
if mismatches:
    for m in mismatches:
        print(f"MISMATCH: {m}")
else:
    print("SUCCESS: Database Eligible Count == Company API Count == Rendered Card Count for 100% of 200 companies!")

# Summary statistics
hiring = [r for r in audit_rows if r['verified_eligible'] > 0]
zero_confirmed = [r for r in audit_rows if r['verified_eligible'] == 0 and r['crawl_outcome'] == 'CRAWLED']
failed_crawl = [r for r in audit_rows if r['crawl_outcome'] == 'FAILED']
blocked_source = [r for r in audit_rows if r['crawl_outcome'] in ('BLOCKED', 'REDIRECT_BLOCKED')]
other_zero = [r for r in audit_rows if r['verified_eligible'] == 0 and r['crawl_outcome'] not in ('CRAWLED', 'FAILED', 'BLOCKED', 'REDIRECT_BLOCKED')]

print("\n--- Summary Breakdown ---")
print(f"Companies with Verified Jobs (>0): {len(hiring)} (Total jobs: {sum(r['verified_eligible'] for r in hiring)})")
print(f"Companies with Confirmed 0 Jobs (CRAWLED): {len(zero_confirmed)}")
print(f"Companies with Crawl Failed (FAILED): {len(failed_crawl)}")
print(f"Companies with Source Blocked (BLOCKED/REDIRECT_BLOCKED): {len(blocked_source)}")
print(f"Companies with Pending/Other Coverage: {len(other_zero)}")
print(f"Total: {len(hiring) + len(zero_confirmed) + len(failed_crawl) + len(blocked_source) + len(other_zero)}")

# Save JSON for table generation in final report
with open('scratch/company_audit_results.json', 'w', encoding='utf-8') as f:
    json.dump(audit_rows, f, indent=2)
print("Saved audit data to scratch/company_audit_results.json")
