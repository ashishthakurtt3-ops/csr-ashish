from urllib.parse import urlparse
from django.db.models import Count, Q
from modules.admin_panel.models import Company, Job

print("--- AUDITING JOB-TO-COMPANY ASSOCIATIONS ---")

active_jobs = Job.objects.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).select_related('company')
print(f"Total active published jobs to check: {active_jobs.count()}")

discrepancies = []
by_company = {}

for j in active_jobs:
    cid = j.company_id
    cname = j.company.company_name
    src_url = j.source_url or ''
    app_url = j.application_url or ''
    domain = urlparse(app_url or src_url).netloc.lower()
    
    by_company.setdefault(cid, {'name': cname, 'jobs': 0, 'domains': set(), 'titles_sample': []})
    by_company[cid]['jobs'] += 1
    by_company[cid]['domains'].add(domain)
    if len(by_company[cid]['titles_sample']) < 3:
        by_company[cid]['titles_sample'].append(j.job_title)

print("\n--- Summary by Company ---")
for cid, info in sorted(by_company.items(), key=lambda x: -x[1]['jobs']):
    print(f"{cid} | {info['name']}: {info['jobs']} jobs, domains={list(info['domains'])[:3]}")

# Let's inspect the 20 companies and their domains:
# Do any domains cross between companies?
print("\n--- Checking Domain Overlaps ---")
domain_to_companies = {}
for cid, info in by_company.items():
    for d in info['domains']:
        domain_to_companies.setdefault(d, []).append((cid, info['name']))

for d, comps in domain_to_companies.items():
    if len(comps) > 1:
        print(f"Domain '{d}' shared by: {comps}")
