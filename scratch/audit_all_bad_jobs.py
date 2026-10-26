import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job
from django.db.models import Count

print("Auditing Active Jobs across database...")

# Check non-career URL patterns
bad_url_keywords = [
    '/what-we-do/',
    '/industries/',
    '/services/',
    '/products-platforms/',
    '/events/',
    '/contact-us/',
    '/who-we-are/',
    '/investor-relations/',
    '/customer-relations/',
    '/api/products',
    '/ourproducts/',
    '/about-us/',
    '/visitor/v3/',
    'digitate.com',
    'jile.io',
    'tcsion.com',
    'remember.techmahindra.com',
    '/diversity-inclusion',
    '/diversity-and-inclusion',
    '/locations',
    '#:'
]

suspect_jobs = []
for job in Job.objects.filter(status='ACTIVE').exclude(verification_status='REJECTED'):
    url = (job.application_url or '').lower()
    src = (job.source_url or '').lower()
    title = (job.job_title or '').strip()
    
    is_bad = False
    reason = ""
    for kw in bad_url_keywords:
        if kw in url or kw in src:
            is_bad = True
            reason = f"Bad URL pattern: {kw}"
            break
            
    if not is_bad:
        # Check titles
        title_lower = title.lower()
        if title_lower in [
            'diversity and inclusion', 'our products', 'reconnect with us',
            'analyst relations', 'media contacts', 'request for services',
            'gobally present, regionally supported', 'discover your team',
            'search for open positions by country', 'become part of our family.',
            'building a better bharat, together.', 'investor meet & presentation',
            'annual reports', 'grievance redressal officer details',
            'list of authorized collection and recovery agents',
            'unauthorized individuals/entities disclaimer', 'customer awareness literature',
            'regional centralized customer service centre', 'kmp for determining materiality',
            'information and reports including compliance reports', 'contact for investor grievances',
            'vigil mechanism/ whistle blower policy', 'investor education & protection fund',
            'disclosure under reg 62 of lodr', 'disclosure under reg 46 of lodr',
            'cg power and industrial solutions ltd.', 'home', 'jobs at ultratech'
        ]:
            is_bad = True
            reason = f"Bad Title: {title}"
            
    if is_bad:
        suspect_jobs.append((job, reason))

print(f"Total suspect active jobs found: {len(suspect_jobs)}")
by_company = {}
for j, r in suspect_jobs:
    by_company[j.company_id] = by_company.get(j.company_id, 0) + 1

by_company_samples = {}
for j, r in suspect_jobs:
    if j.company_id not in by_company_samples:
        by_company_samples[j.company_id] = []
    if len(by_company_samples[j.company_id]) < 5:
        by_company_samples[j.company_id].append((j.job_title, j.application_url or ''))

for cid, count in sorted(by_company.items(), key=lambda x: -x[1])[:15]:
    print(f"\n--- Company {cid} ({count} suspect jobs) ---")
    for title, url in by_company_samples[cid]:
        print(f"   * '{title}' -> {url[:70]}")

