import sys
from collections import Counter
from django.db.models import Count, Q
from modules.admin_panel.models import Company, Job

print("--- EXAMINING JOBS ACROSS ALL 200 COMPANIES ---")

companies = Company.objects.all().order_by('company_id')

results = []
for c in companies:
    jobs_all = c.jobs.all()
    total_cnt = jobs_all.count()
    active_cnt = jobs_all.filter(status='ACTIVE').count()
    published_cnt = jobs_all.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
    legacy_cnt = jobs_all.filter(verification_status='LEGACY_UNVERIFIED').count()
    stale_cnt = jobs_all.filter(verification_status='STALE').count()
    quarantined_cnt = jobs_all.filter(verification_status='QUARANTINED').count()
    rejected_cnt = jobs_all.filter(verification_status='REJECTED').count()
    
    # Check sample job titles or verification reasons
    sample_reasons = list(jobs_all.exclude(verification_reason__isnull=True).exclude(verification_reason='').values_list('verification_reason', flat=True)[:3])
    sample_statuses = dict(Counter(jobs_all.values_list('verification_status', flat=True)))
    
    results.append({
        'company_id': c.company_id,
        'company_name': c.company_name,
        'nse_symbol': c.nse_symbol,
        'crawl_status': c.crawl_status,
        'careers_url': c.careers_url,
        'ats_platform': c.ats_platform,
        'total_jobs': total_cnt,
        'active_jobs': active_cnt,
        'published_jobs': published_cnt,
        'legacy_jobs': legacy_cnt,
        'stale_jobs': stale_cnt,
        'quarantined_jobs': quarantined_cnt,
        'rejected_jobs': rejected_cnt,
        'sample_statuses': sample_statuses,
        'sample_reasons': sample_reasons,
    })

# Summary of companies
has_any_jobs = [r for r in results if r['total_jobs'] > 0]
has_active_jobs = [r for r in results if r['active_jobs'] > 0]
has_published_jobs = [r for r in results if r['published_jobs'] > 0]
has_legacy_only = [r for r in results if r['total_jobs'] > 0 and r['published_jobs'] == 0]

print(f"Total companies: {len(results)}")
print(f"Companies with total_jobs > 0: {len(has_any_jobs)}")
print(f"Companies with active_jobs > 0: {len(has_active_jobs)}")
print(f"Companies with published_jobs > 0: {len(has_published_jobs)}")
print(f"Companies with legacy/stale jobs but 0 published: {len(has_legacy_only)}")

print("\nCompanies with crawl_status breakdown:")
print(Counter(r['crawl_status'] for r in results))

print("\nSample of 20 companies that have total_jobs > 0 but published == 0:")
for r in has_legacy_only[:20]:
    print(f"  {r['company_id']} | {r['company_name']}: total={r['total_jobs']}, statuses={r['sample_statuses']}, crawl_status={r['crawl_status']}, url={r['careers_url']}")
