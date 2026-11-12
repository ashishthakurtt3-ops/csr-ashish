import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import sys
from pathlib import Path
project_dir = Path('.').resolve()
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.admin_panel.models import Company

companies_manifest = [
    {
        'company_name': 'Microsoft',
        'homepage_url': 'https://www.microsoft.com/',
        'careers_url': 'https://careers.microsoft.com/',
        'csr_url': 'https://www.microsoft.com/en-us/corporate-responsibility'
    },
    {
        'company_name': 'Google',
        'homepage_url': 'https://www.google.com/',
        'careers_url': 'https://www.google.com/about/careers/applications/',
        'csr_url': 'https://sustainability.google/'
    },
    {
        'company_name': 'Amazon',
        'homepage_url': 'https://www.amazon.com/',
        'careers_url': 'https://www.amazon.jobs/',
        'csr_url': 'https://sustainability.aboutamazon.com/'
    },
    {
        'company_name': 'IBM',
        'homepage_url': 'https://www.ibm.com/',
        'careers_url': 'https://www.ibm.com/careers',
        'csr_url': 'https://www.ibm.com/impact'
    },
    {
        'company_name': 'Adobe',
        'homepage_url': 'https://www.adobe.com/',
        'careers_url': 'https://careers.adobe.com/',
        'csr_url': 'https://www.adobe.com/corporate-responsibility.html'
    },
    {
        'company_name': 'Infosys',
        'homepage_url': 'https://www.infosys.com/',
        'careers_url': 'https://www.infosys.com/careers/',
        'csr_url': 'https://www.infosys.com/sustainability/'
    },
    {
        'company_name': 'Wipro',
        'homepage_url': 'https://www.wipro.com/',
        'careers_url': 'https://careers.wipro.com/',
        'csr_url': 'https://www.wipro.com/sustainability/'
    },
    {
        'company_name': 'Tata Consultancy Services (TCS)',
        'homepage_url': 'https://www.tcs.com/',
        'careers_url': 'https://www.tcs.com/careers',
        'csr_url': 'https://www.tcs.com/who-we-are/sustainability'
    },
    {
        'company_name': 'Hindustan Unilever',
        'homepage_url': 'https://www.hul.co.in/',
        'careers_url': 'https://www.hul.co.in/careers/',
        'csr_url': 'https://www.hul.co.in/planet-and-society/'
    },
    {
        'company_name': 'Mahindra & Mahindra',
        'homepage_url': 'https://www.mahindra.com/',
        'careers_url': 'https://www.mahindra.com/careers',
        'csr_url': 'https://www.mahindra.com/sustainability'
    }
]

print(f"Starting bulk execution of {len(companies_manifest)} companies...", flush=True)

summary = []
for idx, c in enumerate(companies_manifest, 1):
    c_name = c['company_name']
    print(f"\n[{idx}/10] Processing '{c_name}'...", flush=True)
    try:
        res = BatchDiscoveryService.process_single_company(c)
        st = res.get('status')
        j_disc = res.get('jobs_discovered', 0)
        j_imp = res.get('jobs_imported', 0)
        c_disc = res.get('csr_discovered', 0)
        c_imp = res.get('csr_imported', 0)
        print(f"  Status: {st} | Jobs: {j_imp}/{j_disc} | CSR: {c_imp}/{c_disc}", flush=True)
        summary.append({
            'name': c_name,
            'status': st,
            'jobs': j_imp,
            'csr': c_imp
        })
    except Exception as e:
        print(f"  ERROR: {e}", flush=True)
        summary.append({
            'name': c_name,
            'status': 'error',
            'error': str(e)
        })

print("\n=== FINAL DISCOVERY SUMMARY ===", flush=True)
for s in summary:
    print(f"  {s['name']}: Status={s.get('status')} | Jobs={s.get('jobs')} | CSR={s.get('csr')}", flush=True)

