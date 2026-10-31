import os, sys, django, json, csv
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
django.setup()

from modules.admin_panel.models import Job, CSRProject, CSROpportunity
from modules.admin_panel.verification import is_defective_job_record

def get_job_classification(j):
    title = (j.job_title or '').strip()
    url = (j.application_url or '').strip()
    src = (j.source_url or '').strip()
    comp = j.company.company_name if j.company else ''
    
    # 1. Genuine exceptions in inactive/quarantined:
    # Paytm Lever jobs:
    if j.job_row_id in (6719, 6713) or ('jobs.lever.co/paytm' in url):
        return 'UNVERIFIED', 'Genuine Paytm technical engineering vacancy on Lever ATS', False
        
    # Whirlpool global jobs:
    if j.job_row_id in (10501, 10493, 10485) or ('jobs.whirlpool.com' in url and any(k in title for k in ['Gestionnaire', 'Gerente', 'Senior Finance Manager'])):
        return 'UNVERIFIED', 'Genuine Whirlpool career opening on official career portal', False
        
    # Samvardhana Motherson genuine vacancies:
    if 'Samvardhana Motherson' in comp and 'careers.motherson.com/en/job/' in url:
        return 'UNVERIFIED', 'Genuine Samvardhana Motherson international manufacturing opening', False

    # 2. Confirmed fabricated patterns:
    # A. Apollo Hospitals medical/surgical procedures & hospital branch directory
    if 'Apollo Hospitals' in comp and any(k in (url + src) for k in ['/procedures/', '/hospitals/', '/hospital/']):
        return 'CONFIRMED_FABRICATED', 'Apollo Hospitals medical/surgical procedure or hospital branch directory scraped as job vacancy', True

    # B. Yes Bank Oracle IDCS CMS article nodes
    if 'Yes Bank' in comp and ('/sites/web/ui/idcs' in url or 'yes.bank.in' in url):
        return 'CONFIRMED_FABRICATED', 'Yes Bank Oracle CMS content node scraped due to ?job_id query parameter', True

    # C. CG Power industrial product equipment catalog
    if 'CG Power' in comp and ('api/products' in url or 'cgglobal_backend' in url or title.startswith('Emotron') or title == 'Consumer Products'):
        return 'CONFIRMED_FABRICATED', 'CG Power industrial variable speed drives product catalog item', True

    # D. ONGC accessibility screen-reader software and recruitment exam results notices
    if 'Oil & Natural Gas' in comp and any(k in (url + src) for k in ['vispero', 'yourdolphin', 'freedomscientific', 'webanywhere', 'screenreader', 'satogo', 'nvda-project', 'documents/', 'web/eng/detail']):
        return 'CONFIRMED_FABRICATED', 'ONGC accessibility screen-reader link or recruitment exam result notice', True

    # E. HDFC mutual fund investment calculators
    if 'HDFC Asset' in comp and 'calculators/' in url:
        return 'CONFIRMED_FABRICATED', 'HDFC AMC mutual fund financial planning calculator', True

    # F. Executive leadership bio pages
    if any(k in url for k in ['leadership-team/mr-', 'leadership-team/ms-']):
        return 'CONFIRMED_FABRICATED', 'Executive director leadership biography page', True

    # G. Indian Hotels brands, supplier portals, and financial transparency PDFs
    if 'Indian Hotels' in comp and any(k in (url + src) for k in ['utsav.gov.in', 'nidhi.tourism.gov.in', 'saathi.qcin.org', 'IHCL-Tax-Transparency', 'suppliers', 'accessibility', 'policies', 'esg-profile', 'taj-public-service', 'ihcltata-subscription', 'gingerhotels.com', 'vivantahotels.com', 'gateway-hotels.com', 'hotelclarks.com', 'seleqtionshotels.com', 'brijhotels.com', 'atmantan.com', 'claridges.com', 'tajsats.com', 'soulinaire.com', 'qmin.co.in', 'amastaysandtrails.com', 'treeofliferesorts.com']):
        return 'CONFIRMED_FABRICATED', 'Indian Hotels brand domain, supplier portal, or tax transparency PDF', True

    # H. Defective UI navigation tokens
    if is_defective_job_record(title, url, src):
        return 'CONFIRMED_FABRICATED', f'Defective website navigation token or UI boilerplate: {title[:40]}', True

    # I. Corporate marketing, vendor widgets, non-career URLs
    if any(k in (url + src) for k in ['/what-we-do/', '/services/', '/industries/', 'case-study', 'diageoindia.com/en/careers/life-at-diageo', 'edgeverve.com', 'pminternship.mca.gov.in', 'consent/cookie_banner', 'hcmRestApi/resources/latest/recruitingCEUser', 'lloyds.in/about-us/committees', 'cms.aadharhousing.com', 'avglogistics.com/leadership', 'remember.techmahindra.com', 'salesiq.zohopublic.in']):
        return 'CONFIRMED_FABRICATED', 'Corporate marketing, vendor widget, or non-career landing page', True

    # J. Any other INACTIVE / REJECTED records that have no valid job URL
    if j.status == 'INACTIVE' or j.verification_status == 'REJECTED':
        return 'CONFIRMED_FABRICATED', f'Non-job corporate page or administrative link: {title[:40]}', True

    # 3. Genuine records:
    if j.status == 'ACTIVE':
        return 'SOURCE_VERIFIED', 'Active verified job posting on official careers portal', False
    elif j.status in ('EXPIRED', 'STALE') or j.status == 'REMOVED':
        return 'EXPIRED_OR_STALE', 'Genuine job posting that has expired or rotated off', False
    else:
        return 'UNVERIFIED', f'Genuine job posting currently marked {j.status}/{j.verification_status}', False


os.makedirs('reports/audit', exist_ok=True)
jobs_to_remove = []
jobs_to_preserve = []

for j in Job.objects.select_related('company').all():
    classification, reason, is_fabricated = get_job_classification(j)
    item = {
        'id': j.job_row_id,
        'company': j.company.company_name if j.company else '',
        'title': j.job_title,
        'status': j.status,
        'verification_status': j.verification_status,
        'url': j.application_url,
        'classification': classification,
        'reason': reason
    }
    if is_fabricated:
        jobs_to_remove.append(item)
    else:
        jobs_to_preserve.append(item)

print(f'Total Jobs Audited: {Job.objects.count()}')
print(f'Confirmed Fabricated to Remove: {len(jobs_to_remove)}')
print(f'Genuine Records to Preserve: {len(jobs_to_preserve)}')

from collections import Counter
c_pres = Counter(r['classification'] for r in jobs_to_preserve)
for k, v in c_pres.items():
    print(f'Preserved [{k}]: {v}')

# Save audit json
with open('reports/audit/jobs_audit_classification.json', 'w', encoding='utf-8') as f:
    json.dump({
        'total_jobs': Job.objects.count(),
        'confirmed_fabricated_count': len(jobs_to_remove),
        'preserved_count': len(jobs_to_preserve),
        'fabricated_records': jobs_to_remove,
    }, f, indent=2)

print('Saved reports/audit/jobs_audit_classification.json successfully.')
