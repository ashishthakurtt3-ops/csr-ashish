import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject

companies = (
    Company.objects
    .filter(company_id__startswith='COMP_TOP200_')
    .order_by('company_id')[:50]
)

fake_job_count = 0
fake_csr_count = 0
dead_link_patterns = ['/candidate/?', 'candidate.tcsapps.com', 'ibegin.tcs.com', 'TCS/IND/', 'WIP-IND-', 'INFY-REQ-', '#:~:text=']

print(f"Scanning top {companies.count()} companies in MySQL...")

companies_needing_fix = []

for c in companies:
    jobs = list(c.jobs.all())
    csrs = list(c.csr_projects.all())
    
    bad_jobs = []
    for j in jobs:
        # Check if URL has dead link patterns or if evidence indicates hallucination
        is_bad = False
        if any(p in (j.application_url or '') for p in dead_link_patterns):
            is_bad = True
        if 'Enterprise hiring track' in (j.evidence_text or ''):
            is_bad = True
        if 'Senior Sustainability Officer' in (j.job_title or ''):
            is_bad = True
        if is_bad:
            bad_jobs.append(j)
            
    bad_csrs = []
    for cs in csrs:
        is_bad = False
        title = cs.project_name or ''
        if any(h in title for h in ['Environmental Stewardship & Clean Energy Mission', 'Skill Development & Livelihood Mission', 'Foundation - Primary Healthcare & Community Welfare', 'Foundation - Education & Community Upliftment']):
            is_bad = True
        if 'Flagship corporate social responsibility initiative under Section 135 Schedule V' in (cs.evidence_text or ''):
            is_bad = True
        if is_bad:
            bad_csrs.append(cs)
            
    if bad_jobs or bad_csrs:
        companies_needing_fix.append((c, len(bad_jobs), len(jobs), len(bad_csrs), len(csrs)))

print(f"Companies with hallucinated/defective records: {len(companies_needing_fix)} out of 50")
for c, bj_cnt, j_cnt, bc_cnt, c_cnt in companies_needing_fix:
    print(f"- {c.company_name} ({c.company_id}): {bj_cnt}/{j_cnt} bad jobs, {bc_cnt}/{c_cnt} bad CSR")

