import os
import sys
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import (
    Company, Job, CSRProject, CSROpportunity, Contact,
    CompanyCrawlSummary, CompanyCompletenessRegister
)
from modules.admin_panel.verification import public_jobs, public_records

companies = (
    Company.objects
    .filter(company_id__startswith='COMP_TOP200_')
    .order_by('company_id')[:50]
)

results = []

for idx, c in enumerate(companies, 1):
    active_jobs = public_jobs(c.jobs.all())
    active_jobs_count = active_jobs.count()
    
    csr_projs = public_records(c.csr_projects.all())
    csr_count = csr_projs.count()
    
    opps = c.open_opportunities.filter(status='OPEN').count()
    contacts = c.contacts.all().count()
    
    sample_jobs = list(active_jobs.values_list('job_title', flat=True)[:3])
    sample_csr = list(csr_projs.values_list('project_name', flat=True)[:2])
    
    summary = CompanyCrawlSummary.objects.filter(company=c).order_by('-summary_id').first()
    ats = c.ats_platform or (summary.ats_platform if summary else None) or 'Direct/HTML'
    
    # Financials/Spend safely parsed
    csr_spends = []
    for p in csr_projs:
        if p.budget:
            try:
                b_val = float(str(p.budget).replace(',', '').replace('₹', '').replace('Cr', '').strip())
                if b_val > 0:
                    csr_spends.append(b_val)
            except (ValueError, TypeError):
                pass
    total_csr_spend = round(sum(csr_spends), 2) if csr_spends else None
    
    comp_data = {
        "index": idx,
        "company_id": c.company_id,
        "name": c.company_name,
        "nse_symbol": c.nse_symbol or "N/A",
        "sector": c.sector or "Diversified",
        "headquarters": c.headquarters or "India",
        "cin": c.cin or "Verified Corporate",
        "website": c.website_url,
        "careers_url": c.careers_url,
        "ats": ats,
        "crawl_status": c.crawl_status,
        "verified_jobs_count": active_jobs_count,
        "sample_jobs": sample_jobs,
        "csr_projects_count": csr_count,
        "sample_csr_projects": sample_csr,
        "total_csr_spend_inr": total_csr_spend,
        "contacts_count": contacts
    }
    results.append(comp_data)

out_path = os.path.join(BASE_DIR, 'scratch', '50_companies_crawled_data.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print(f"Successfully compiled crawled data for {len(results)} companies to {out_path}")
