import os
import sys
import json
import csv
import re
from urllib.parse import urlparse, parse_qs
from collections import defaultdict
from datetime import datetime

import django

sys.path.insert(0, ".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db.models import Count, Q, Sum, F
from django.utils import timezone
from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, Contact, NGOCollaboration, CompanyCrawlSummary, PageRecord
from modules.admin_panel.verification import public_jobs, PUBLIC_VERIFICATION_STATUSES
from modules.website.views.job_api_views import apply_job_safety_filters

def strip_url(url):
    if not url:
        return ""
    u = str(url).strip()
    u = u.split("#")[0]
    u = u.split("?")[0]
    return u.rstrip("/").lower()

print("Gathering Baseline Measurements...")

# 1. Companies careers mapping
companies = {c.company_id: c for c in Company.objects.all()}
careers_map = {}
csr_map = {}
for cid, comp in companies.items():
    if comp.careers_url:
        careers_map[cid] = strip_url(comp.careers_url)
    if comp.csr_url:
        csr_map[cid] = strip_url(comp.csr_url)

# 2. Job Link Audit
all_jobs = list(Job.objects.select_related("company").all())
active_jobs = [j for j in all_jobs if j.status == 'ACTIVE']

url_counts_per_company = defaultdict(lambda: defaultdict(int))
for j in active_jobs:
    cid = j.company.company_id if j.company else "UNKNOWN"
    s_url = strip_url(j.application_url or j.source_url)
    if s_url:
        url_counts_per_company[cid][s_url] += 1

job_issues_by_company = defaultdict(lambda: {
    "total_active": 0,
    "matches_careers": 0,
    "shared_url": 0,
    "has_text_fragment": 0,
    "listing_like_total": 0,
    "direct_looking": 0
})

jobs_with_text_fragment = 0
jobs_matching_careers = 0
jobs_shared = 0
total_listing_like_jobs = 0
total_direct_looking_jobs = 0

for j in active_jobs:
    cid = j.company.company_id if j.company else "UNKNOWN"
    stats = job_issues_by_company[cid]
    stats["total_active"] += 1
    
    raw_url = j.application_url or j.source_url or ""
    s_url = strip_url(raw_url)
    c_careers = careers_map.get(cid, "")
    
    matches_c = bool(s_url and c_careers and s_url == c_careers)
    is_shared = bool(s_url and url_counts_per_company[cid][s_url] > 1)
    has_frag = "#:~:text=" in raw_url
    
    if matches_c:
        stats["matches_careers"] += 1
        jobs_matching_careers += 1
    if is_shared:
        stats["shared_url"] += 1
        jobs_shared += 1
    if has_frag:
        stats["has_text_fragment"] += 1
        jobs_with_text_fragment += 1
        
    if matches_c or is_shared or has_frag:
        stats["listing_like_total"] += 1
        total_listing_like_jobs += 1
    else:
        stats["direct_looking"] += 1
        total_direct_looking_jobs += 1

# Worst 25 companies for jobs
worst_25_job_companies = sorted(
    job_issues_by_company.items(),
    key=lambda x: (x[1]["listing_like_total"], -x[1]["direct_looking"]),
    reverse=True
)[:25]

# 3. CSR Projects & Opportunities Link Audit
all_csr_projects = list(CSRProject.objects.select_related("company").all())
csr_url_counts = defaultdict(lambda: defaultdict(int))
for p in all_csr_projects:
    cid = p.company.company_id if p.company else "UNKNOWN"
    s_url = strip_url(p.source_url)
    if s_url:
        csr_url_counts[cid][s_url] += 1

csr_matching_url = 0
csr_shared_url = 0
csr_text_frag = 0
csr_listing_like = 0
for p in all_csr_projects:
    cid = p.company.company_id if p.company else "UNKNOWN"
    raw_url = p.source_url or ""
    s_url = strip_url(raw_url)
    c_csr = csr_map.get(cid, "")
    matches_c = bool(s_url and c_csr and s_url == c_csr)
    is_shared = bool(s_url and csr_url_counts[cid][s_url] > 1)
    has_frag = "#:~:text=" in raw_url
    if matches_c: csr_matching_url += 1
    if is_shared: csr_shared_url += 1
    if has_frag: csr_text_frag += 1
    if matches_c or is_shared or has_frag: csr_listing_like += 1

all_opportunities = list(CSROpportunity.objects.select_related("company").all())
opp_url_counts = defaultdict(lambda: defaultdict(int))
for o in all_opportunities:
    cid = o.company.company_id if o.company else "UNKNOWN"
    s_url = strip_url(o.portal_url or o.source_url)
    if s_url:
        opp_url_counts[cid][s_url] += 1

opp_matching_url = 0
opp_shared_url = 0
opp_text_frag = 0
opp_listing_like = 0
for o in all_opportunities:
    cid = o.company.company_id if o.company else "UNKNOWN"
    raw_url = o.portal_url or o.source_url or ""
    s_url = strip_url(raw_url)
    c_csr = csr_map.get(cid, "")
    matches_c = bool(s_url and c_csr and s_url == c_csr)
    is_shared = bool(s_url and opp_url_counts[cid][s_url] > 1)
    has_frag = "#:~:text=" in raw_url
    if matches_c: opp_matching_url += 1
    if is_shared: opp_shared_url += 1
    if has_frag: opp_text_frag += 1
    if matches_c or is_shared or has_frag: opp_listing_like += 1

# 4. Defaults & Value Extraction Analysis
# Check how many jobs have default-looking values:
# e.g. employment_type == 'Full-time' without evidence in description/title
# work_mode == 'On-site' without evidence
# city / department defaults
job_total = len(all_jobs)
emp_type_counts = defaultdict(int)
work_mode_counts = defaultdict(int)
city_null_count = 0
dept_null_count = 0
status_counts = defaultdict(int)

for j in all_jobs:
    emp = (j.employment_type or "").strip()
    wm = (j.work_mode or "").strip()
    c = (j.city or "").strip()
    d = (j.department or "").strip()
    emp_type_counts[emp or "NULL/Blank"] += 1
    work_mode_counts[wm or "NULL/Blank"] += 1
    if not c or c.lower() in ('none', 'null', 'unknown'):
        city_null_count += 1
    if not d or d.lower() in ('none', 'null', 'unknown', 'uncategorized', 'unspecified'):
        dept_null_count += 1
    status_counts[j.status or "NULL"] += 1

# 5. CSR Budget Analysis
csr_total = len(all_csr_projects)
budget_null_zero = 0
budget_parsed_vals = []
unparseable_budgets = 0
absurd_budgets = 0 # > 500 Crore for a single project

BUDGET_RE = re.compile(r'(?:INR|Rs\.?|₹)?\s*([\d,]+(?:\.\d+)?)\s*(crore|cr\.?|lakh|million|billion)?', re.IGNORECASE)

def parse_budget_val(b_str):
    if not b_str:
        return None
    s = str(b_str).strip()
    if s.lower() in ('null', 'none', 'unknown', '0', '0.0', 'na', 'not disclosed', ''):
        return 0.0
    m = BUDGET_RE.search(s)
    if not m:
        return -1 # unparseable
    try:
        val = float(m.group(1).replace(',', ''))
        unit = (m.group(2) or '').lower()
        if 'crore' in unit or 'cr' in unit:
            return val * 10000000
        elif 'lakh' in unit:
            return val * 100000
        elif 'million' in unit:
            return val * 1000000
        elif 'billion' in unit:
            return val * 1000000000
        else:
            return val
    except:
        return -1

company_csr_sums = defaultdict(float)
for p in all_csr_projects:
    b = p.budget
    if not b or b.strip() in ('', '0', '0.0', 'None', 'null'):
        budget_null_zero += 1
    else:
        v = parse_budget_val(b)
        if v == -1:
            unparseable_budgets += 1
        elif v == 0.0:
            budget_null_zero += 1
        else:
            budget_parsed_vals.append((p.csr_id, p.project_name, b, v))
            cid = p.company.company_id if p.company else "UNKNOWN"
            company_csr_sums[cid] += v
            if v > 5000000000: # > 500 Cr
                absurd_budgets += 1

# Opportunity analysis: deadlines and application mechanisms
opp_total = len(all_opportunities)
opp_no_deadline = 0
opp_no_apply_mech = 0
for o in all_opportunities:
    d = (o.submission_deadline or "").strip()
    if not d or d.lower() in ('null', 'none', 'open', 'unknown', 'na', ''):
        opp_no_deadline += 1
    p = (o.portal_url or "").strip()
    req = (o.requirements or "").strip()
    if (not p or p == "#" or "javascript" in p) and not ("@" in req or "http" in req or "portal" in req.lower()):
        opp_no_apply_mech += 1

# 6. Duplicates, Empty required fields, Invalid URLs, Old retrieved_at
dup_fingerprints_jobs = Job.objects.values("fingerprint").annotate(cnt=Count("job_row_id")).filter(cnt__gt=1).count()
empty_title_jobs = Job.objects.filter(Q(job_title__isnull=True) | Q(job_title="")).count()
invalid_app_urls = Job.objects.filter(~Q(application_url__startswith="http"), application_url__isnull=False).exclude(application_url="").count()

cutoff_30d = timezone.now() - timezone.timedelta(days=30)
active_old_retrieved = Job.objects.filter(status="ACTIVE", retrieved_at__lt=cutoff_30d).count()
active_null_retrieved = Job.objects.filter(status="ACTIVE", retrieved_at__isnull=True).count()

# 7. /stats vs Actual Table counts
total_companies_table = Company.objects.count()
total_jobs_table = Job.objects.count()
active_jobs_table = Job.objects.filter(status="ACTIVE").count()
public_jobs_qs = apply_job_safety_filters(public_jobs(Job.objects.all()))
public_jobs_count = public_jobs_qs.count()

total_csr_table = CSRProject.objects.count()
public_csr_count = CSRProject.objects.filter(verification_status__in=list(PUBLIC_VERIFICATION_STATUSES)).count()

total_opps_table = CSROpportunity.objects.count()
public_opps_count = CSROpportunity.objects.filter(verification_status__in=list(PUBLIC_VERIFICATION_STATUSES), status='OPEN').count()

output_data = {
    "total_companies": total_companies_table,
    "all_jobs": job_total,
    "active_jobs": len(active_jobs),
    "total_direct_looking_jobs": total_direct_looking_jobs,
    "total_listing_like_jobs": total_listing_like_jobs,
    "jobs_matching_careers": jobs_matching_careers,
    "jobs_shared": jobs_shared,
    "jobs_with_text_fragment": jobs_with_text_fragment,
    "worst_25_job_companies": [(cid, companies[cid].company_name if cid in companies else cid, stats) for cid, stats in worst_25_job_companies],
    "csr_total": csr_total,
    "csr_matching_url": csr_matching_url,
    "csr_shared_url": csr_shared_url,
    "csr_text_frag": csr_text_frag,
    "csr_listing_like": csr_listing_like,
    "opp_total": opp_total,
    "opp_matching_url": opp_matching_url,
    "opp_shared_url": opp_shared_url,
    "opp_text_frag": opp_text_frag,
    "opp_listing_like": opp_listing_like,
    "emp_type_counts": dict(emp_type_counts),
    "work_mode_counts": dict(work_mode_counts),
    "city_null_count": city_null_count,
    "dept_null_count": dept_null_count,
    "status_counts": dict(status_counts),
    "csr_budget_null_zero": budget_null_zero,
    "csr_unparseable_budgets": unparseable_budgets,
    "csr_absurd_budgets": absurd_budgets,
    "company_csr_sums_gt_500cr": [(cid, companies[cid].company_name if cid in companies else cid, s/10000000) for cid, s in company_csr_sums.items() if s > 5000000000],
    "opp_no_deadline": opp_no_deadline,
    "opp_no_apply_mech": opp_no_apply_mech,
    "dup_fingerprints_jobs": dup_fingerprints_jobs,
    "empty_title_jobs": empty_title_jobs,
    "invalid_app_urls": invalid_app_urls,
    "active_old_retrieved": active_old_retrieved,
    "active_null_retrieved": active_null_retrieved,
    "stats_comparison": {
        "total_companies_table": total_companies_table,
        "total_jobs_table": total_jobs_table,
        "active_jobs_table": active_jobs_table,
        "public_jobs_visible": public_jobs_count,
        "total_csr_table": total_csr_table,
        "public_csr_visible": public_csr_count,
        "total_opps_table": total_opps_table,
        "public_opps_visible": public_opps_count,
    }
}

with open("scratch/baseline_data.json", "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2)

print("Baseline data saved successfully to scratch/baseline_data.json!")
