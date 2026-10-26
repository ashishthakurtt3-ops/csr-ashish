import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job

# Let's inspect active job titles and print any that look suspicious
active_jobs = Job.objects.filter(status='ACTIVE')
print("Total active jobs:", active_jobs.count())

suspicious = []
for j in active_jobs:
    t = (j.job_title or '').strip()
    tl = t.lower()
    
    # Check if title looks like a URL or starts with http
    if tl.startswith('http') or '.com' in tl or '.co.uk' in tl:
        suspicious.append((j.company.company_name, j.job_id, t, "URL_TITLE"))
        continue
        
    # Check if title contains typical web phrases
    bad_tokens = [
        'alert', 'feedback', 'cookie', 'terms', 'privacy', 'sitemap', 'faq',
        'policy', 'compliance', 'shareholder', 'investor', 'sustainability',
        'governance', 'leadership', 'our values', 'our story', 'our history',
        'press release', 'newsroom', 'case stud', 'about us', 'contact us',
        'view all', 'view detail', 'know more', 'learn more', 'apply now',
        'upload resume', 'submit resume', 'saved job', 'ads', 'championship',
        'brand ambassador', 'download', 'calculator', 'locator'
    ]
    if any(b in tl for b in bad_tokens):
        # Exclude legitimate titles like "Sustainability Manager", "Compliance Officer", "Privacy Analyst"
        is_legit = any(role in tl for role in ['manager', 'officer', 'lead', 'head', 'analyst', 'engineer', 'specialist', 'executive', 'director', 'intern', 'trainee', 'associate', 'consultant', 'vp', 'president', 'developer'])
        if not is_legit:
            suspicious.append((j.company.company_name, j.job_id, t, "BOILERPLATE"))

print(f"Total additional suspicious titles found: {len(suspicious)}")
for cname, jid, title, reason in suspicious[:40]:
    print(f"  [{cname[:20]}] {title} ({reason})")
