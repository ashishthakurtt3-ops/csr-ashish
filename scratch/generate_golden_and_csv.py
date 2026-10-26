import os
import sys
import json
import csv
from collections import defaultdict
from urllib.parse import urlparse

import django

sys.path.insert(0, ".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity

def strip_url(url):
    if not url: return ""
    u = str(url).strip().split("#")[0].split("?")[0]
    return u.rstrip("/").lower()

print("Generating baseline.csv and golden test templates...")

os.makedirs("reports", exist_ok=True)
os.makedirs("tests/golden", exist_ok=True)

# 1. Generate reports/baseline.csv
companies = {c.company_id: c for c in Company.objects.all()}
careers_map = {c.company_id: strip_url(c.careers_url) for c in companies.values() if c.careers_url}
csr_map = {c.company_id: strip_url(c.csr_url) for c in companies.values() if c.csr_url}

active_jobs = list(Job.objects.filter(status='ACTIVE').select_related("company"))

url_counts_per_company = defaultdict(lambda: defaultdict(int))
for j in active_jobs:
    cid = j.company.company_id if j.company else "UNKNOWN"
    s_url = strip_url(j.application_url or j.source_url)
    if s_url:
        url_counts_per_company[cid][s_url] += 1

csr_projects = list(CSRProject.objects.select_related("company"))
csr_url_counts = defaultdict(lambda: defaultdict(int))
for p in csr_projects:
    cid = p.company.company_id if p.company else "UNKNOWN"
    s_url = strip_url(p.source_url)
    if s_url:
        csr_url_counts[cid][s_url] += 1

csr_opps = list(CSROpportunity.objects.select_related("company"))
opp_url_counts = defaultdict(lambda: defaultdict(int))
for o in csr_opps:
    cid = o.company.company_id if o.company else "UNKNOWN"
    s_url = strip_url(o.portal_url or o.source_url)
    if s_url:
        opp_url_counts[cid][s_url] += 1

# Per company baseline stats
company_rows = []
for cid, comp in sorted(companies.items(), key=lambda x: x[1].company_name):
    c_jobs = [j for j in active_jobs if j.company and j.company.company_id == cid]
    c_csr = [p for p in csr_projects if p.company and p.company.company_id == cid]
    c_opp = [o for o in csr_opps if o.company and o.company.company_id == cid]
    
    total_jobs = len(c_jobs)
    job_direct = 0
    job_listing_like = 0
    c_careers = careers_map.get(cid, "")
    
    for j in c_jobs:
        raw_url = j.application_url or j.source_url or ""
        s_url = strip_url(raw_url)
        matches_c = bool(s_url and c_careers and s_url == c_careers)
        is_shared = bool(s_url and url_counts_per_company[cid][s_url] > 1)
        has_frag = "#:~:text=" in raw_url
        if matches_c or is_shared or has_frag:
            job_listing_like += 1
        else:
            job_direct += 1
            
    pct_direct = (job_direct / total_jobs * 100.0) if total_jobs > 0 else 0.0
    
    # CSR link stats
    total_csr = len(c_csr)
    csr_listing_like = 0
    c_csr_url = csr_map.get(cid, "")
    for p in c_csr:
        raw_url = p.source_url or ""
        s_url = strip_url(raw_url)
        matches_c = bool(s_url and c_csr_url and s_url == c_csr_url)
        is_shared = bool(s_url and csr_url_counts[cid][s_url] > 1)
        has_frag = "#:~:text=" in raw_url
        if matches_c or is_shared or has_frag:
            csr_listing_like += 1
            
    # Default counts for jobs
    full_time_count = sum(1 for j in c_jobs if j.employment_type == 'Full-time')
    onsite_count = sum(1 for j in c_jobs if j.work_mode == 'On-site')
    corp_dept_count = sum(1 for j in c_jobs if j.department in ('Corporate', 'Corporate Openings'))
    
    company_rows.append({
        "company_id": cid,
        "company_name": comp.company_name,
        "ats_platform": comp.ats_platform or comp.ats_type or "Custom/None",
        "active_jobs": total_jobs,
        "direct_jobs": job_direct,
        "listing_like_jobs": job_listing_like,
        "pct_direct_jobs": f"{pct_direct:.1f}%",
        "csr_projects_count": total_csr,
        "csr_listing_like": csr_listing_like,
        "csr_opportunities_count": len(c_opp),
        "jobs_full_time_default": full_time_count,
        "jobs_onsite_default": onsite_count,
        "jobs_corp_dept_default": corp_dept_count,
        "extraction_strategy": comp.extraction_strategy or "none"
    })

# Write reports/baseline.csv
with open("reports/baseline.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(company_rows[0].keys()))
    writer.writeheader()
    writer.writerows(company_rows)

print(f"Saved reports/baseline.csv with {len(company_rows)} company rows.")

# 2. Golden test file sampling
# Sample ~100 jobs: across Lever, Greenhouse, Workday, Darwinbox, SuccessFactors, Oracle, Custom
sampled_jobs = []
seen_job_ids = set()

# First add by detected platform / adapter
for j in active_jobs:
    plat = (j.ats_platform or (j.company.ats_platform if j.company else "") or "CUSTOM").upper()
    if len([x for x in sampled_jobs if x["ats_platform"] == plat]) < 15:
        sampled_jobs.append({
            "job_row_id": j.job_row_id,
            "company_id": j.company.company_id if j.company else "",
            "company_name": j.company.company_name if j.company else "",
            "ats_platform": plat,
            "current_title": j.job_title,
            "expected_title": j.job_title,
            "current_location": j.location,
            "expected_location": j.location,
            "current_application_url": j.application_url,
            "expected_application_url": j.canonical_url or j.application_url,
            "current_canonical_url": j.canonical_url,
            "link_quality": j.link_quality,
            "expected_link_quality": "DIRECT" if j.link_quality == "DIRECT" else "LISTING_FALLBACK",
            "current_employment_type": j.employment_type,
            "expected_employment_type": j.employment_type or "Unknown",
            "current_work_mode": j.work_mode,
            "expected_work_mode": j.work_mode or "Unknown",
            "verified_by_human": False
        })
        seen_job_ids.add(j.job_row_id)

# Fill up to 100 jobs with diverse active jobs
for j in active_jobs:
    if len(sampled_jobs) >= 100:
        break
    if j.job_row_id in seen_job_ids:
        continue
    plat = (j.ats_platform or (j.company.ats_platform if j.company else "") or "CUSTOM").upper()
    sampled_jobs.append({
        "job_row_id": j.job_row_id,
        "company_id": j.company.company_id if j.company else "",
        "company_name": j.company.company_name if j.company else "",
        "ats_platform": plat,
        "current_title": j.job_title,
        "expected_title": j.job_title,
        "current_location": j.location,
        "expected_location": j.location,
        "current_application_url": j.application_url,
        "expected_application_url": j.canonical_url or j.application_url,
        "current_canonical_url": j.canonical_url,
        "link_quality": j.link_quality,
        "expected_link_quality": "DIRECT" if j.link_quality == "DIRECT" else "LISTING_FALLBACK",
        "current_employment_type": j.employment_type,
        "expected_employment_type": j.employment_type or "Unknown",
        "current_work_mode": j.work_mode,
        "expected_work_mode": j.work_mode or "Unknown",
        "verified_by_human": False
    })
    seen_job_ids.add(j.job_row_id)

print(f"Sampled {len(sampled_jobs)} golden jobs.")
with open("tests/golden/golden_jobs.json", "w", encoding="utf-8") as f:
    json.dump(sampled_jobs, f, indent=2)

# Sample ~50 CSR projects: diverse companies
sampled_csr = []
seen_csr_cids = set()
for p in csr_projects:
    cid = p.company.company_id if p.company else ""
    if cid in seen_csr_cids and len(sampled_csr) > 30:
        continue
    seen_csr_cids.add(cid)
    sampled_csr.append({
        "csr_id": p.csr_id,
        "company_id": cid,
        "company_name": p.company.company_name if p.company else "",
        "current_project_name": p.project_name,
        "expected_project_name": p.project_name, # For manual audit
        "current_category": p.category,
        "expected_category": p.category,
        "current_budget": p.budget,
        "expected_budget": p.budget,
        "current_source_url": p.source_url,
        "expected_source_url": p.source_url,
        "verified_by_human": False
    })
    if len(sampled_csr) >= 50:
        break

print(f"Sampled {len(sampled_csr)} golden CSR projects.")
with open("tests/golden/golden_csr_projects.json", "w", encoding="utf-8") as f:
    json.dump(sampled_csr, f, indent=2)

print("Golden files created successfully!")
