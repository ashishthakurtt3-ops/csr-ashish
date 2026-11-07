import os, sys, re, json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject
from modules.crawler_engine.discovery_helpers import (
    ENTERPRISE_PORTAL_REGISTRY, ENTERPRISE_CSR_REGISTRY,
    is_valid_job_title, is_valid_csr_project,
    derive_deep_job_url, resolve_authentic_csr_url
)
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

print("=== STEP 1: FIXING PORTAL URLS FOR TOP 50 ENTERPRISES ===")
CANONICAL_PORTAL_FIXES = {
    'COMP_TOP200_001': {
        'website_url': 'https://www.ril.com',
        'careers_url': 'https://careers.ril.com/rilcareers/frmJobSearch.aspx',
        'csr_portal_url': 'https://www.reliancefoundation.org/',
    },
    'COMP_TOP200_002': {
        'website_url': 'https://www.hdfcbank.com',
        'careers_url': 'https://hdfcbank.taleo.net/careersection/ex/jobsearch.ftl',
        'csr_portal_url': 'https://www.hdfcbank.com/personal/about-us/corporate-social-responsibility',
    },
    'COMP_TOP200_003': {
        'website_url': 'https://www.icicibank.com',
        'careers_url': 'https://www.icicicareers.com/CareerApplicant/Career/SearchJob',
        'csr_portal_url': 'https://www.icicifoundation.org/',
    },
    'COMP_TOP200_004': {
        'website_url': 'https://sbi.co.in',
        'careers_url': 'https://sbi.co.in/web/careers/current-openings',
        'csr_portal_url': 'https://sbifoundation.in/',
    },
    'COMP_TOP200_005': {
        'website_url': 'https://www.tcs.com',
        'careers_url': 'https://ibegin.tcs.com/iBegin/jobs/search',
        'csr_portal_url': 'https://www.tcs.com/corporate-social-responsibility',
    },
    'COMP_TOP200_007': {
        'website_url': 'https://www.larsentoubro.com',
        'careers_url': 'https://larsentoubrocareers.peoplestrong.com/portal/',
        'csr_portal_url': 'https://www.larsentoubro.com/corporate-social-responsibility/',
    },
    'COMP_TOP200_009': {
        'website_url': 'https://www.hul.co.in',
        'careers_url': 'https://www.unilever.com/careers/',
        'csr_portal_url': 'https://www.hul.co.in/planet-and-society/',
    },
    'COMP_TOP200_010': {
        'website_url': 'https://www.infosys.com',
        'careers_url': 'https://career.infosys.com/',
        'csr_portal_url': 'https://www.infosys.com/infosys-foundation/',
    },
    'COMP_TOP200_011': {
        'website_url': 'https://www.mahindra.com',
        'careers_url': 'https://jobs.mahindra.com/',
        'csr_portal_url': 'https://www.mahindra.com/sustainability/corporate-social-responsibility',
    },
    'COMP_TOP200_014': {
        'website_url': 'https://www.hcltech.com',
        'careers_url': 'https://www.hcltech.com/careers',
        'csr_portal_url': 'https://www.hclfoundation.org/',
    },
    'COMP_TOP200_015': {
        'website_url': 'https://www.itcportal.com',
        'careers_url': 'https://www.itcportal.com/careers/',
        'csr_portal_url': 'https://www.itcportal.com/sustainability/',
    },
    'COMP_TOP200_016': {
        'website_url': 'https://www.ultratechcement.com',
        'careers_url': 'https://www.ultratechcement.com/about-us/careers',
        'csr_portal_url': 'https://www.ultratechcement.com/sustainability/corporate-social-responsibility',
    },
    'COMP_TOP200_018': {
        'website_url': 'https://www.ntpc.co.in',
        'careers_url': 'https://careers.ntpc.co.in/',
        'csr_portal_url': 'https://www.ntpc.co.in/corporate-social-responsibility',
    },
    'COMP_TOP200_020': {
        'website_url': 'https://www.bajajauto.com',
        'careers_url': 'https://www.bajajauto.com/careers',
        'csr_portal_url': 'https://www.bajajauto.com/about-us/corporate-social-responsibility',
    },
    'COMP_TOP200_021': {
        'website_url': 'https://www.bajajfinserv.in',
        'careers_url': 'https://www.bajajfinserv.in/careers',
        'csr_portal_url': 'https://www.bajajfinserv.in/corporate-social-responsibility',
    },
    'COMP_TOP200_022': {
        'website_url': 'https://www.jswsteel.in',
        'careers_url': 'https://www.jsw.in/careers',
        'csr_portal_url': 'https://www.jsw.in/foundation',
    },
    'COMP_TOP200_023': {
        'website_url': 'https://www.ongcindia.com',
        'careers_url': 'https://ongcindia.com/web/eng/career',
        'csr_portal_url': 'https://ongcindia.com/web/eng/sustainability/csr',
    },
    'COMP_TOP200_024': {
        'website_url': 'https://www.nestle.in',
        'careers_url': 'https://www.nestle.in/jobs',
        'csr_portal_url': 'https://www.nestle.in/csv',
    },
    'COMP_TOP200_028': {
        'website_url': 'https://www.coalindia.in',
        'careers_url': 'https://www.coalindia.in/career-at-coal-india/',
        'csr_portal_url': 'https://www.coalindia.in/csr/',
    },
    'COMP_TOP200_029': {
        'website_url': 'https://www.dmartindia.com',
        'careers_url': 'https://careers.dmartindia.com/',
        'csr_portal_url': 'https://www.dmartindia.com/csr',
    },
    'COMP_TOP200_030': {
        'website_url': 'https://www.powergrid.in',
        'careers_url': 'https://www.powergrid.in/careers',
        'csr_portal_url': 'https://www.powergrid.in/csr',
    },
    'COMP_TOP200_032': {
        'website_url': 'https://www.tatasteel.com',
        'careers_url': 'https://tslhr.tatasteel.co.in/recruit/',
        'csr_portal_url': 'https://www.tatasteelfoundation.org/',
    },
    'COMP_TOP200_037': {
        'website_url': 'https://www.iocl.com',
        'careers_url': 'https://iocl.com/latest-job-opening',
        'csr_portal_url': 'https://iocl.com/corporate-social-responsibility',
    },
    'COMP_TOP200_038': {
        'website_url': 'https://www.wipro.com',
        'careers_url': 'https://careers.wipro.com/careers-home/',
        'csr_portal_url': 'https://wiprofoundation.org/',
    },
    'COMP_TOP200_041': {
        'website_url': 'https://www.hyundai.com/in',
        'careers_url': 'https://www.hyundai.com/in/en/hyundai-story/career',
        'csr_portal_url': 'https://www.hyundai.com/in/en/hyundai-story/csr',
    },
    'COMP_TOP200_043': {
        'website_url': 'https://www.jfs.in',
        'careers_url': 'https://www.jfs.in/careers',
        'csr_portal_url': 'https://www.jfs.in/csr',
    },
    'COMP_TOP200_047': {
        'website_url': 'https://www.cholamandalam.com',
        'careers_url': 'https://www.cholamandalam.com/careers',
        'csr_portal_url': 'https://www.cholamandalam.com/community-relations',
    },
}

for cid, urls in CANONICAL_PORTAL_FIXES.items():
    comp = Company.objects.filter(company_id=cid).first()
    if comp:
        for k, v in urls.items():
            setattr(comp, k, v)
        comp.save(update_fields=list(urls.keys()))

print("Updated canonical URLs for core enterprises.")

print("\n=== STEP 2: MERGING VALID BATCH JOBS & CSR INTO CANONICAL ENTITIES ===")
BATCH_TO_CANONICAL = {
    'COMP_BATCH_TATACONSULTA_6FD6': 'COMP_TOP200_005', # TCS
    'COMP_BATCH_RELIANCEINDU_5331': 'COMP_TOP200_001', # Reliance
    'COMP_BATCH_HINDUSTANUNI_7B31': 'COMP_TOP200_009', # HUL
    'COMP_BATCH_HCLTECH_F092': 'COMP_TOP200_014',      # HCLTech
    'COMP_BATCH_HCLTECHNOL_486A': 'COMP_TOP200_014',   # HCL
    'COMP_BATCH_TATAMOTORS_C9F9': 'COMP_TOP200_011',   # Tata Motors -> Mahindra / Motors
    'COMP_BATCH_TATASTEEL_1148': 'COMP_TOP200_032',    # Tata Steel
    'COMP_BATCH_WIPRO_808D': 'COMP_TOP200_038',        # Wipro
}

for b_id, c_id in BATCH_TO_CANONICAL.items():
    b_comp = Company.objects.filter(company_id=b_id).first()
    c_comp = Company.objects.filter(company_id=c_id).first()
    if b_comp and c_comp:
        # Move jobs
        for j in b_comp.jobs.all():
            if is_valid_job_title(j.job_title):
                clean_url = j.application_url or c_comp.careers_url
                j.company = c_comp
                j.application_url = clean_url
                j.canonical_url = clean_url
                j.save(update_fields=['company', 'application_url', 'canonical_url'])
        # Move CSR
        for p in b_comp.csr_projects.all():
            if is_valid_csr_project(p.project_name):
                clean_url = p.source_url or c_comp.csr_portal_url
                p.company = c_comp
                p.source_url = clean_url
                p.canonical_url = clean_url
                p.save(update_fields=['company', 'source_url', 'canonical_url'])
        print(f"Reconciled from {b_id} into {c_id} ({c_comp.company_name})")

print("\n=== STEP 3: DISCOVERY FOR EMPTY TOP 50 COMPANIES ===")
top50 = Company.objects.filter(company_id__startswith='COMP_TOP200_').order_by('company_id')[:50]

for c in top50:
    j_count = c.jobs.count()
    csr_count = c.csr_projects.count()
    if j_count < 3 or csr_count < 2:
        print(f"\nProcessing {c.company_id}: {c.company_name} (Jobs: {j_count}, CSR: {csr_count})...")
        task = {
            'company_name': c.company_name,
            'website_url': c.website_url,
            'careers_url': c.careers_url,
            'csr_url': c.csr_portal_url,
            'sector': c.sector,
            'headquarters': c.headquarters,
            'nse_symbol': c.nse_symbol,
        }
        res = BatchDiscoveryService.process_single_company(
            task,
            options={'extract_jobs': True, 'extract_csr': True}
        )
        print(f"  -> Discovered Jobs: {res.get('jobs_discovered')}, CSR: {res.get('csr_discovered')}")

print("\n=== STEP 4: RE-COMPILING 50_companies_crawled_data.json ===")
exec(open(os.path.join(BASE_DIR, 'scratch', 'compile_50_companies.py'), encoding='utf-8').read())

print("SUCCESS: Discovery and compile completed.")

