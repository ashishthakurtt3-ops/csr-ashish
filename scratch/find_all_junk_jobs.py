import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job

# Let's inspect all active jobs for suspicious titles
active_jobs = Job.objects.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
print(f"Total active jobs in DB: {active_jobs.count()}")

suspicious_keywords = [
    'how to apply', 'discover more', 'faqs & support', 'faq', 'frequently asked',
    'review accommodation', 'upload resume', 'next >>', 'previous <<',
    'cookie', 'privacy notice', 'terms of use', 'accessibility statement',
    'join our talent', 'talent community', 'talent network', 'learn more about',
    'explore helpful tips', 'life at', 'read more', 'click here'
]

junk_jobs = []
for j in active_jobs:
    t = (j.job_title or '').lower().strip()
    if any(k in t for k in suspicious_keywords) or len(t) < 3:
        junk_jobs.append((j.job_id, j.company.company_id, j.company.company_name, j.job_title, j.application_url))

print(f"Total active jobs matching suspicious/junk navigation: {len(junk_jobs)}")
for jj in junk_jobs:
    print(f"  [{jj[0]}] ({jj[1]} - {jj[2]}): \"{jj[3]}\"")
    print(f"     app_url: {jj[4]}")
