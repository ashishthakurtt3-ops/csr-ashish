import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
django.setup()

from modules.admin_panel.models import Job

# Check all inactive jobs whose URL or title might indicate an actual job posting
inactive_jobs = Job.objects.filter(status='INACTIVE', verification_status='REJECTED').exclude(
    company__company_name__in=['Yes Bank Limited', 'Oil & Natural Gas Corporation Limited', 'CG Power and Industrial Solutions Limited']
)

genuine_inactive_jobs = []
for j in inactive_jobs:
    u = (j.application_url or '').lower()
    t = (j.job_title or '').lower()
    
    # Exclude obvious non-jobs
    if any(k in u for k in ['/pages/', 'cms.', 'contact-us', 'calculators', 'who-we-are', 'what-we-do', 'investors', 'about-us', 'suppliers', 'accessibility', 'policies']):
        continue
    if any(k in t for k in ['loan', 'deposit', 'account', 'credit card', 'championship', 'ambassador', 'feedback', 'grievance', 'disclaimer', 'branch', 'atp', 'open', 'hall of fame']):
        continue
    if any(k in u for k in ['/job/', '/jobs/', 'candidateexperience', 'oraclecloud', 'workday', 'darwinbox', 'peoplestrong', 'successfactors', 'lever.co', 'greenhouse.io', 'smartrecruiters', 'naukri.com']):
        # Check if title is a defect
        from modules.admin_panel.verification import is_defective_job_record
        if not is_defective_job_record(j.job_title, j.application_url, j.source_url):
            genuine_inactive_jobs.append((j.job_row_id, j.company.company_name, j.job_title, j.application_url))

print(f'Total candidate genuine jobs in INACTIVE: {len(genuine_inactive_jobs)}')
for c in genuine_inactive_jobs:
    print(c)
