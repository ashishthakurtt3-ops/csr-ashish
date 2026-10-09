import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.models import Company

ats_signatures = {
    'Greenhouse': ['greenhouse.io'],
    'Lever': ['lever.co'],
    'Workday': ['myworkdayjobs.com'],
    'SmartRecruiters': ['smartrecruiters.com'],
    'Ashby': ['ashbyhq.com'],
    'SuccessFactors': ['successfactors.com', 'successfactors.eu', 'sf.com'],
    'Oracle/Taleo': ['taleo.net', 'oraclecloud.com', 'sites/cx_'],
    'Darwinbox': ['darwinbox.in'],
    'Eightfold': ['eightfold.ai'],
    'iCIMS': ['icims.com'],
}

detected = {}
for c in Company.objects.all():
    url = (c.careers_url or '') + ' ' + (c.website_url or '')
    matched = None
    for ats, sigs in ats_signatures.items():
        if any(sig in url.lower() for sig in sigs):
            matched = ats
            break
    if matched:
        detected[c.company_id] = (c.company_name, matched, c.careers_url)

print(f"Total companies with direct ATS URL: {len(detected)}")
for cid, (name, ats, curl) in list(detected.items())[:20]:
    print(f"  {cid}: {name[:25]:<25} | ATS: {ats:<15} | {curl}")
