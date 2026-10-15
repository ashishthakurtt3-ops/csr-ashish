import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models.company import Company
from modules.admin_panel.models.job import Job
from collections import Counter
from urllib.parse import urlparse

# Get all 180 companies that currently have 0 active verified jobs
comps_all = Company.objects.all()
zero_comps = [c for c in comps_all if c.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count() == 0]
print(f"Total companies with 0 verified jobs: {len(zero_comps)}")

jobs_180 = Job.objects.filter(company__in=zero_comps)
print(f"Total jobs across these companies: {jobs_180.count()}")

# Inspect fields
has_title = jobs_180.exclude(job_title='').exclude(job_title__isnull=True).count()
has_loc = jobs_180.exclude(location='').exclude(location__isnull=True).count()
has_url = jobs_180.exclude(application_url='').exclude(application_url__isnull=True).count()
country_counts = Counter(jobs_180.values_list('country', flat=True))

print(f"Jobs with title: {has_title}")
print(f"Jobs with location: {has_loc}")
print(f"Jobs with application_url: {has_url}")
print(f"Country breakdown: {country_counts}")

# Check URL domain matching
domain_match = 0
domain_mismatch = 0
mismatches = []
for j in jobs_180:
    comp = j.company
    c_dom = urlparse(comp.website_url or '').netloc.lower().replace('www.', '')
    j_dom = urlparse(j.application_url or '').netloc.lower().replace('www.', '')
    if c_dom and j_dom and (c_dom in j_dom or j_dom in c_dom):
        domain_match += 1
    else:
        domain_mismatch += 1
        mismatches.append((comp.company_name, comp.website_url, j.application_url))

print(f"Domain matches: {domain_match}")
print(f"Domain mismatches: {domain_mismatch}")
if mismatches:
    print(f"First 10 mismatches:")
    for m in mismatches[:10]:
        print(f"  {m[0]}: comp_web={m[1]} vs job_app={m[2]}")
