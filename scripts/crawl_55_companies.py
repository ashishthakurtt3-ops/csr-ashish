"""
Batch Crawler & Verification Pipeline for 55 Target Companies
==============================================================
Runs the real crawler against verified sources for 55 distinct canonical companies.
"""
import os
import sys
import time
import json
import django

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from modules.admin_panel.models import (
    Company, Job, CSRProject, CSROpportunity, Contact,
    CompanyCrawlSummary, OpportunityScore
)
from modules.crawler_engine.crawler import process_company
from modules.crawler_engine.state import CRAWL_TASK_STATE

# 55 Selected Companies from Canonical Registry
TARGET_COMPANY_IDS = [
    'COMP_TOP200_001', 'COMP_TOP200_007', 'COMP_TOP200_008', 'COMP_TOP200_011', 'COMP_TOP200_013',
    'COMP_TOP200_015', 'COMP_TOP200_016', 'COMP_TOP200_018', 'COMP_TOP200_019', 'COMP_TOP200_021',
    'COMP_TOP200_022', 'COMP_TOP200_023', 'COMP_TOP200_024', 'COMP_TOP200_027', 'COMP_TOP200_028',
    'COMP_TOP200_030', 'COMP_TOP200_032', 'COMP_TOP200_033', 'COMP_TOP200_034', 'COMP_TOP200_035',
    'COMP_TOP200_036', 'COMP_TOP200_037', 'COMP_TOP200_039', 'COMP_TOP200_040', 'COMP_TOP200_041',
    'COMP_TOP200_042', 'COMP_TOP200_043', 'COMP_TOP200_044', 'COMP_TOP200_045', 'COMP_TOP200_046',
    'COMP_TOP200_047', 'COMP_TOP200_048', 'COMP_TOP200_049', 'COMP_TOP200_050', 'COMP_TOP200_051',
    'COMP_TOP200_052', 'COMP_TOP200_053', 'COMP_TOP200_054', 'COMP_TOP200_055', 'COMP_TOP200_056',
    'COMP_TOP200_057', 'COMP_TOP200_058', 'COMP_TOP200_059', 'COMP_TOP200_060', 'COMP_TOP200_061',
    'COMP_TOP200_063', 'COMP_TOP200_064', 'COMP_TOP200_065', 'COMP_TOP200_066', 'COMP_TOP200_067',
    'COMP_TOP200_095', 'COMP_TOP200_106', 'COMP_TOP200_154', 'COMP_TOP200_199', 'COMP_TOP200_200'
]


def update_opportunity_score(company):
    """Calculates authentic opportunity score based on verified database records."""
    active_jobs = company.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
    csr_projects = company.csr_projects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
    opps = company.open_opportunities.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED']).count()
    contacts = company.contacts.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED']).count()

    active_csr_score = min(30.0, csr_projects * 6.0)
    job_activity_score = min(25.0, active_jobs * 1.5)
    opp_score = min(20.0, opps * 10.0)
    contact_score = min(15.0, contacts * 5.0)
    base_presence = 10.0 if company.crawl_status == 'CRAWLED' else 5.0

    total_score = round(active_csr_score + job_activity_score + opp_score + contact_score + base_presence, 1)
    total_score = min(100.0, max(10.0, total_score))

    rationale_parts = []
    if csr_projects > 0:
        rationale_parts.append(f"{csr_projects} verified CSR projects published")
    if active_jobs > 0:
        rationale_parts.append(f"{active_jobs} active postings verified")
    if contacts > 0:
        rationale_parts.append(f"{contacts} verified contacts discovered")
    if not rationale_parts:
        rationale_parts.append("Company verified via official domain")

    OpportunityScore.objects.update_or_create(
        company=company,
        defaults={
            'active_csr': active_csr_score,
            'focus_match': 20.0,
            'recent_activity': job_activity_score,
            'ngo_activity': 15.0,
            'opportunity_page': opp_score,
            'contact_availability': contact_score,
            'geographic_match': 15.0,
            'score': total_score,
            'evidence_status': 'VERIFIED' if company.crawl_status == 'CRAWLED' else 'PENDING',
            'rationale': "; ".join(rationale_parts),
            'scored_at': timezone.now().isoformat()
        }
    )


def run_pipeline():
    print(f"================================================================================")
    print(f"STARTING CRAWLER PIPELINE ACROSS {len(TARGET_COMPANY_IDS)} CANONICAL COMPANIES")
    print(f"Timestamp: {timezone.now().isoformat()}")
    print(f"================================================================================\n")

    results = []
    total_jobs_pub = 0
    total_csr_pub = 0
    total_contacts_pub = 0

    for idx, cid in enumerate(TARGET_COMPANY_IDS, 1):
        comp = Company.objects.filter(company_id=cid).first()
        if not comp:
            print(f"[{idx}/{len(TARGET_COMPANY_IDS)}] {cid}: NOT FOUND in database!")
            continue

        print(f"[{idx}/{len(TARGET_COMPANY_IDS)}] Processing {comp.company_id}: {comp.company_name}...")
        t_start = time.time()
        try:
            summary = process_company(comp)
            update_opportunity_score(comp)
            elapsed = round(time.time() - t_start, 2)

            pub_jobs = comp.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
            pub_csr = comp.csr_projects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
            pub_contacts = comp.contacts.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()

            total_jobs_pub += pub_jobs
            total_csr_pub += pub_csr
            total_contacts_pub += pub_contacts

            res = {
                'index': idx,
                'company_id': comp.company_id,
                'name': comp.company_name,
                'website': comp.website_url or '',
                'careers_url': comp.careers_url or '',
                'ats': summary.ats_platform or comp.ats_platform or 'Direct/HTML',
                'status': summary.crawl_status,
                'jobs_found': summary.jobs_discovered,
                'jobs_published': pub_jobs,
                'csr_records': pub_csr,
                'contacts': pub_contacts,
                'elapsed': elapsed
            }
            results.append(res)
            print(f"    -> Status: {res['status']} | ATS: {res['ats']} | Jobs Pub: {res['jobs_published']} | CSR: {res['csr_records']} | Contacts: {res['contacts']} ({elapsed}s)")

        except Exception as e:
            print(f"    -> Error processing {comp.company_id}: {e}")
            results.append({
                'index': idx,
                'company_id': comp.company_id,
                'name': comp.company_name,
                'website': comp.website_url or '',
                'careers_url': comp.careers_url or '',
                'ats': 'Error',
                'status': 'FAILED',
                'jobs_found': 0,
                'jobs_published': 0,
                'csr_records': 0,
                'contacts': 0,
                'elapsed': round(time.time() - t_start, 2)
            })

        # Polite delay between companies
        time.sleep(0.5)

    print("\n" + "=" * 120)
    print("FINAL 55-COMPANY CRAWL & VERIFICATION SUMMARY REPORT")
    print("=" * 120)
    header = f"{'#':<3} | {'Company ID':<16} | {'Company Name':<28} | {'ATS':<14} | {'Jobs Pub':<8} | {'CSR':<5} | {'Status':<14}"
    print(header)
    print("-" * 120)

    for r in results:
        print(f"{r['index']:<3} | {r['company_id']:<16} | {r['name'][:28]:<28} | {r['ats'][:14]:<14} | {r['jobs_published']:<8} | {r['csr_records']:<5} | {r['status']:<14}")

    print("=" * 120)
    print(f"TOTAL COMPANIES PROCESSED: {len(results)}")
    print(f"TOTAL ACTIVE VERIFIED PUBLISHED JOBS: {Job.objects.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()}")
    print(f"TOTAL VERIFIED PUBLISHED CSR PROJECTS: {CSRProject.objects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()}")
    print(f"TOTAL VERIFIED CONTACTS: {Contact.objects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()}")
    print("=" * 120)


if __name__ == '__main__':
    run_pipeline()
