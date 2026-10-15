import os
import sys
from collections import Counter
from django.db.models import Count, Q
from modules.admin_panel.models import Company, Job

print("--- DEEP FORENSIC AUDIT OF ALL 200 COMPANIES ---")

companies = Company.objects.all().order_by('company_id')
print(f"Total companies in database: {companies.count()}")

audit_rows = []

for c in companies:
    all_jobs = c.jobs.all()
    total_jobs = all_jobs.count()
    active_jobs = all_jobs.filter(status='ACTIVE').count()
    published_jobs = all_jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
    legacy_jobs = all_jobs.filter(verification_status='LEGACY_UNVERIFIED').count()
    quarantined_jobs = all_jobs.filter(verification_status='QUARANTINED').count()
    rejected_jobs = all_jobs.filter(verification_status='REJECTED').count()
    stale_jobs = all_jobs.filter(verification_status='STALE').count()
    expired_jobs = all_jobs.filter(status='EXPIRED').count()
    pending_jobs = all_jobs.filter(verification_status__in=['DISCOVERED', 'FETCHED', 'EXTRACTED', 'UNVERIFIED']).count()
    
    # Check ATS and careers info
    careers_url = c.careers_url or ''
    ats_platform = c.ats_platform or 'Unknown'
    last_crawled = c.last_crawled or 'Never'
    crawl_status = c.crawl_status or 'PENDING'
    
    # Determine the authoritative expected coverage state:
    if published_jobs > 0:
        coverage_state = "VERIFIED_JOBS"
        display_label = f"{published_jobs} Verified Jobs"
    elif crawl_status == 'FAILED':
        coverage_state = "CRAWL_FAILED"
        display_label = "Crawl Failed"
    elif crawl_status in ('BLOCKED', 'REDIRECT_BLOCKED'):
        coverage_state = "SOURCE_BLOCKED"
        display_label = "Source Blocked / Protected"
    elif not careers_url or crawl_status == 'NO_CAREER_URL':
        coverage_state = "NO_CAREER_URL"
        display_label = "Source Unavailable"
    elif crawl_status == 'CRAWLED':
        coverage_state = "VERIFIED_ZERO"
        display_label = "0 Verified Jobs (Confirmed)"
    else:
        coverage_state = "PENDING_COVERAGE"
        display_label = "Coverage Pending"

    audit_rows.append({
        'company_id': c.company_id,
        'company_name': c.company_name,
        'nse_symbol': c.nse_symbol or '',
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'published_jobs': published_jobs,
        'legacy_jobs': legacy_jobs,
        'quarantined_jobs': quarantined_jobs,
        'rejected_jobs': rejected_jobs,
        'stale_jobs': stale_jobs,
        'expired_jobs': expired_jobs,
        'pending_jobs': pending_jobs,
        'careers_url': careers_url,
        'ats_platform': ats_platform,
        'last_crawled': last_crawled,
        'crawl_status': crawl_status,
        'coverage_state': coverage_state,
        'display_label': display_label,
    })

# Print high-level breakdown
print("\n--- COVERAGE STATE BREAKDOWN ACROSS 200 COMPANIES ---")
state_counter = Counter(r['coverage_state'] for r in audit_rows)
for st, cnt in state_counter.most_common():
    print(f"  {st}: {cnt} companies")

print("\n--- PUBLISHED JOBS AUDIT ---")
comps_with_jobs = [r for r in audit_rows if r['published_jobs'] > 0]
print(f"Companies with published jobs: {len(comps_with_jobs)}")
for r in sorted(comps_with_jobs, key=lambda x: -x['published_jobs']):
    print(f"  {r['company_id']} | {r['company_name']} ({r['nse_symbol']}): {r['published_jobs']} jobs")

# Check Adani / ACC / Ambuja duplicates
print("\n--- ADANI / ACC / AMBUJA REQUISITION OVERLAP AUDIT ---")
eibd_jobs = Job.objects.filter(source_url__icontains='eibd.fa.em2.oraclecloud.com', status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
print(f"Total active published jobs from eibd Oracle ATS: {eibd_jobs.count()}")
for j in eibd_jobs:
    print(f"  Job {j.job_row_id} | ExtID: {j.external_job_id} | Comp: {j.company_id} ({j.company.company_name}) | Title: {j.job_title} | AppURL: {j.application_url[:60]}")
