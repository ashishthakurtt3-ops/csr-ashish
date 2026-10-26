import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import sys
sys.stdout.reconfigure(encoding='utf-8')
from modules.admin_panel.models import Job

jobs = list(Job.objects.filter(status='ACTIVE').exclude(verification_status='REJECTED'))
print(f"Total active jobs remaining: {len(jobs)}")

# Let's inspect titles that have suspect tokens
suspects = []
for j in jobs:
    t = (j.job_title or '').strip()
    u = (j.application_url or '').lower()
    t_low = t.lower()
    
    reasons = []
    if t.isupper() and len(t.split()) <= 4 and any(k in t for k in ['SEE ALL', 'VIEW ALL', 'ALL JOBS', 'JOIN US']):
        reasons.append('Button label')
    if any(k in t_low for k in [
        'caste certificate', 'certificate format', 'medical rules', 'audio-visual',
        'navigation menu', 'live your passion', 'why choose us', 'diverse teams are',
        'learning is your launchpad', 'industrial business', 'namma metro', 'dicgc',
        'save your card', 'premier banker program', 'registered with', 'about pidilite',
        'brands', 'phase-i:result', 'results-', 'part-vi-result', 'gate 2023 score',
        'recruitment notices', 'find your work family', 'disclaimer', 'privacy policy'
    ]):
        reasons.append('Boilerplate phrase')
    if any(k in u for k in [
        'mazagondock.in/writereaddata', 'cardhq.com', 'paycraftsol.in', 'dicgc.org.in',
        'niit.com', 'pminternship', 'pidilite.com/careers/young-talent', 'pidilite.com/careers/diversity',
        'pidilite.com/consumer-brands', 'industrial-adhesives.pidilite.com', 'ongcindia.com/web/eng/sitemap',
        'ongcindia.com/web/eng/career/audio-visual', 'ongcindia.com/web/eng/career/recruitment-policy',
        'ongcindia.com/web/eng/career/why-work-with-ongc', 'ongcindia.com/web/eng/detail?assetclasspk'
    ]):
        reasons.append('Non-career URL')
        
    if reasons:
        suspects.append((j, reasons))

print(f"Total suspects found in check: {len(suspects)}")
for j, r in suspects[:25]:
    print(f" - [{j.company_id}] {j.job_title} | {r} | URL: {j.application_url[:70] if j.application_url else 'None'}")
