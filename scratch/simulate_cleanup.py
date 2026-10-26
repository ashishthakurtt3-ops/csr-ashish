import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job

# Non-job URL markers (where jobs never reside)
NON_CAREER_URL_SUBSTRINGS = [
    'cgglobal.com/cgglobal_backend/api/products',
    'cms.aadharhousing.com/api/v1/investor-relations',
    'cms.aadharhousing.com/customer-relations',
    'nmdc.co.in/cms-admin/api/home/ourprojects',
    'darpan.nmdc.co.in',
    'cms-api.bajajfinserv.in',
    'canarabank.bank.in/pages/',
    'economictimes.indiatimes.com',
    'pressreader.com',
    'uploads/gcpl_fe_brandwagon',
    'tcs.com/what-we-do/',
    'tcs.com/contact-us/',
    'tcs.com/who-we-are/events/',
    'digitate.com',
    'jile.io',
    'tcsion.com',
    'tvsmotor.com/about-us/',
    'torrentpharma.com/ourproducts/',
    'remember.techmahindra.com',
    'salesiq.zohopublic.in',
    'ongcindia.com/documents/',
    'careers.motherson.com/en/locations',
    'careers.motherson.com/en/144330138',
    'careers.motherson.com/en/121689704',
    'careers.motherson.com/en/98944374',
]

# Non-job exact/pattern titles
NON_JOB_TITLES = {
    'diversity and inclusion',
    'our products',
    'reconnect with us',
    'analyst relations',
    'media contacts',
    'request for services',
    'gobally present, regionally supported',
    'discover your team',
    'search for open positions by country',
    'become part of our family.',
    'building a better bharat, together.',
    'investor meet & presentation',
    'annual reports',
    'grievance redressal officer details',
    'list of authorized collection and recovery agents',
    'unauthorized individuals/entities disclaimer',
    'customer awareness literature',
    'regional centralized customer service centre',
    'kmp for determining materiality',
    'information and reports including compliance reports',
    'contact for investor grievances',
    'vigil mechanism/ whistle blower policy',
    'investor education & protection fund',
    'disclosure under reg 62 of lodr',
    'disclosure under reg 46 of lodr',
    'cg power and industrial solutions ltd.',
    'current openings – global',
    'current openings - global',
    'customer portal - darpan',
    'steel plant at nagarnar',
    'kumaraswamy iron ore mine',
    'diamond mining project, panna',
    'donimalai iron ore mines, donimalai',
    'bailadila iron ore mine, kirandul complex',
    'bailadila iron ore mine, bacheli complex',
    'we are not able to verify your identity',
    'year of incorporation verification failed',
    'year of birth verification failed',
    'verify using another option',
}

to_deactivate = []
active_jobs = Job.objects.filter(status='ACTIVE').exclude(verification_status='REJECTED')

for j in active_jobs:
    url = (j.application_url or '').lower()
    src = (j.source_url or '').lower()
    title = (j.job_title or '').strip()
    title_lower = title.lower()

    bad_reason = None
    for sub in NON_CAREER_URL_SUBSTRINGS:
        if sub in url or sub in src:
            bad_reason = f"Bad URL substring: {sub}"
            break

    if not bad_reason:
        if title_lower in NON_JOB_TITLES:
            bad_reason = f"Bad title exact: {title}"
        elif title_lower.startswith('kisan credit card') or title_lower.startswith('produce loan') or title_lower.startswith('canara consumption') or title_lower.startswith('scheme for financing') or title_lower.startswith('scheme of financing'):
            bad_reason = f"Bank loan product: {title}"
        elif title_lower.startswith('i have read, understood, and hereby accept'):
            bad_reason = f"Terms acceptance text: {title}"
        elif title_lower.startswith('written test') or title_lower.startswith('list of mca students shortlisted'):
            bad_reason = f"Exam archive: {title}"

    if bad_reason:
        to_deactivate.append((j, bad_reason))

print(f"Total active jobs evaluated: {active_jobs.count()}")
print(f"Total records to deactivate: {len(to_deactivate)}")

by_comp = {}
for j, r in to_deactivate:
    by_comp[j.company_id] = by_comp.get(j.company_id, 0) + 1

for cid, count in sorted(by_comp.items(), key=lambda x: -x[1])[:20]:
    print(f"   {cid}: {count} records")
