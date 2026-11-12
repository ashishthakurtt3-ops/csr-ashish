import os
import sys
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject
from modules.crawler_engine.discovery_helpers import ENTERPRISE_PORTAL_REGISTRY

print("=== STARTING PURGE OF SYNTHETIC & HALLUCINATED RECORDS ===")

# 1. Purge bad jobs
bad_job_count = 0
fixed_job_urls = 0

for j in Job.objects.all():
    title = j.job_title or ''
    ev = j.evidence_text or ''
    app_url = j.application_url or ''
    
    is_fake = False
    if 'Enterprise hiring track' in ev:
        is_fake = True
    elif any(bad in app_url for bad in ['ibegin.tcs.com', 'TCS/IND/', 'WIP-IND-', 'INFY-REQ-']):
        is_fake = True
    elif any(bad_title in title for bad_title in [
        'Senior Sustainability Officer', 'Management Executive', 'CSR & ESG Lead', 'Operations & Strategy Manager'
    ]):
        is_fake = True
        
    if is_fake:
        bad_job_count += 1
        j.delete()
    else:
        # If genuine job has text fragment or login wall, fix it
        new_url = re.sub(r'#:~:text=.*$', '', app_url, flags=re.IGNORECASE).rstrip('&?')
        if any(bad in new_url.lower() for bad in ['/candidate/?', 'candidate.tcsapps.com', 'signin', 'auth/login']):
            comp_key = (j.company.company_name or '').lower()
            new_url = ENTERPRISE_PORTAL_REGISTRY.get(comp_key) or j.company.careers_url or j.company.website_url
        if new_url != app_url:
            j.application_url = new_url
            j.canonical_url = new_url
            j.save(update_fields=['application_url', 'canonical_url'])
            fixed_job_urls += 1

print(f"Purged {bad_job_count} hallucinated/dead jobs.")
print(f"Fixed {fixed_job_urls} job application URLs.")

# 2. Purge bad CSR projects
bad_csr_count = 0
fixed_csr_urls = 0

for c in CSRProject.objects.all():
    name = c.project_name or ''
    ev = c.evidence_text or ''
    src_url = c.source_url or ''
    
    is_fake = False
    if any(h in name for h in [
        'Environmental Stewardship & Clean Energy Mission',
        'Skill Development & Livelihood Mission',
        'Foundation - Primary Healthcare & Community Welfare',
        'Foundation - Education & Community Upliftment'
    ]):
        is_fake = True
    elif 'Flagship corporate social responsibility initiative under Section 135 Schedule V' in ev:
        is_fake = True
        
    if is_fake:
        bad_csr_count += 1
        c.delete()
    else:
        new_src = re.sub(r'#:~:text=.*$', '', src_url, flags=re.IGNORECASE).rstrip('&?')
        if new_src != src_url:
            c.source_url = new_src
            c.canonical_url = new_src
            c.save(update_fields=['source_url', 'canonical_url'])
            fixed_csr_urls += 1

print(f"Purged {bad_csr_count} hallucinated/templated CSR projects.")
print(f"Fixed {fixed_csr_urls} CSR URLs.")
print("=== PURGE COMPLETE ===")

