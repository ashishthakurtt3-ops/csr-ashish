import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, Company
from django.db.models import Count

comps_with_active = Company.objects.annotate(active_count=Count('jobs')).filter(active_count__gt=0).order_by('-active_count')

print("AUDIT OF ACTIVE JOBS ACROSS ALL COMPANIES:")
fake_comps = []
for c in comps_with_active:
    jobs = c.jobs.filter(status='ACTIVE')
    if not jobs.exists():
        continue
    sample_urls = [j.application_url or j.source_url or '' for j in jobs[:5]]
    sample_titles = [j.job_title for j in jobs[:5]]
    
    # Check if all or most sample URLs are CMS or non-careers
    is_cms_leak = any('/sites/web/ui/idcs' in u for u in sample_urls) or \
                  (c.company_id == 'COMP_TOP200_085' and any('ihcltata.com/ihcltata' in u or 'suppliers' in u or 'utsav.gov' in u for u in sample_urls)) or \
                  (c.company_id == 'COMP_TOP200_010' and any('tennis' in u or 'ithf' in u or 'atp' in u for u in sample_urls))
                  
    if is_cms_leak:
        fake_comps.append((c.company_id, c.company_name, jobs.count()))
        print(f"\n[FLAGGED CMS / MARKETING LEAK] {c.company_name} ({c.company_id}) - {jobs.count()} active jobs")
        for t, u in zip(sample_titles, sample_urls):
            print(f"    Title: {t[:40]} | URL: {u[:65]}")

print(f"\nTotal Companies flagged with full CMS / Marketing crawl leaks: {len(fake_comps)}")
