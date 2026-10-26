import os
import sys
import django
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, CSRProject, CSROpportunity, Company

def audit_jobs():
    print("=" * 80)
    print("AUDITING ACTIVE PUBLISHED JOBS")
    print("=" * 80)
    
    active_published_jobs = Job.objects.filter(
        status='ACTIVE',
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
    )
    print(f"Total Active Published Jobs: {active_published_jobs.count()}")

    # 1. Check title false positives (pagination buttons, UI elements)
    button_patterns = [
        'upload resume', 'next >>', 'next >', '<< previous', 'previous', 'last >>', 'last',
        'know more', 'click here', 'apply now', 'search jobs', 'view all', 'view details',
        'review accommodations for disability', 'cookie settings', 'read more', 'back to top'
    ]
    
    suspect_jobs = []
    for j in active_published_jobs:
        title_lower = (j.job_title or '').strip().lower()
        if any(bp == title_lower or bp in title_lower for bp in button_patterns):
            suspect_jobs.append(j)
            print(f"[BUTTON/UI DEFECT] {j.company.company_name} | ID:{j.job_id} | Title: '{j.job_title}' | Loc: '{j.location}' | URL: {j.application_url}")

    print(f"\nTotal Button/UI Defect Jobs: {len(suspect_jobs)}")

    # 2. Check overseas jobs for Indian companies
    # HUL is prime example, check if other Indian companies have overseas jobs
    overseas_keywords = [
        'usa', 'united states', 'netherlands', 'rotterdam', 'vietnam', 'philippines', 'thailand',
        'germany', 'poland', 'myanmar', 'sri lanka', 'singapore', 'indonesia', 'jakarta', 'morocco',
        'malaysia', 'south africa', 'turkey', 'umraniye', 'london', 'uk', 'united kingdom',
        'hoboken', 'jefferson city', 'jonesboro', 'independence', 'raeford', 'heilbronn', 'taguig',
        'cavite', 'warsaw', 'auerbach', 'buxtehude', 'hammond', 'chicago'
    ]
    
    overseas_by_company = defaultdict(list)
    for j in active_published_jobs:
        loc_lower = (j.location or '').strip().lower()
        title_lower = (j.job_title or '').strip().lower()
        is_overseas = any(k in loc_lower for k in overseas_keywords)
        # Check if company is Indian listed
        if is_overseas:
            overseas_by_company[j.company.company_name].append(j)

    print("\nOVERSEAS JOBS ATTRIBUTED TO INDIAN COMPANIES:")
    for comp_name, j_list in overseas_by_company.items():
        print(f"  {comp_name}: {len(j_list)} overseas jobs")
        for j in j_list[:3]:
            print(f"     - ID:{j.job_id} | Title: {j.job_title} | Loc: {j.location}")

def audit_csr_projects():
    print("\n" + "=" * 80)
    print("AUDITING CSR PROJECTS")
    print("=" * 80)
    
    published_csr = CSRProject.objects.filter(
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
    )
    print(f"Total Published CSR Projects: {published_csr.count()}")

    header_patterns = [
        'stakeholder value created', 'purpose of engagement', 'frequency',
        'engagement mechanisms', 'our teams', 'board of directors', 'table of contents',
        'disclaimer', 'contact us', 'privacy policy', 'terms of use', 'overview'
    ]
    
    defect_csr = []
    for p in published_csr:
        p_name_lower = (p.project_name or '').strip().lower()
        if any(hp == p_name_lower or hp in p_name_lower for hp in header_patterns):
            defect_csr.append(p)
            print(f"[CSR HEADER DEFECT] {p.company.company_name} | ID:{p.csr_id} | Name: '{p.project_name}' | Focus: '{p.category}'")

    print(f"\nTotal Scraped Table/Navigation CSR Defects: {len(defect_csr)}")

def audit_opportunities():
    print("\n" + "=" * 80)
    print("AUDITING CSR OPPORTUNITIES")
    print("=" * 80)
    
    open_opps = CSROpportunity.objects.filter(
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED'],
        status='OPEN'
    )
    print(f"Total Open CSROpportunities: {open_opps.count()}")

    commercial_patterns = [
        'helicopter', 'tender', 'supplier registration', 'vendor registration',
        'sap ariba', 'procurement', 'disposal of', 'sale of scrap', 'marking videos',
        'homebuilder', 'commercial tender', 'contractor registration'
    ]

    defect_opps = []
    for o in open_opps:
        t_lower = (o.title or '').strip().lower()
        desc_lower = (o.requirements or '').strip().lower()
        is_commercial = any(cp in t_lower or cp in desc_lower for cp in commercial_patterns)
        print(f"Opp ID:{o.opp_id} | Co: {o.company.company_name if o.company else 'None'} | Title: '{o.title}' | Type: {o.opportunity_type} | Deadline: {o.submission_deadline}")
        if is_commercial:
            defect_opps.append(o)
            print(f"   --> [COMMERCIAL/NON-CSR DEFECT] Matched commercial pattern!")

    print(f"\nTotal Commercial Non-CSR Opportunity Defects: {len(defect_opps)}")

if __name__ == '__main__':
    audit_jobs()
    audit_csr_projects()
    audit_opportunities()
