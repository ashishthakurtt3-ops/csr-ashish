import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from modules.admin_panel.models import Job, Company

companies_with_jobs = Company.objects.filter(jobs__isnull=False).distinct()
print(f'Companies with any jobs in DB: {companies_with_jobs.count()}')

india_keywords = [
    'india', 'mumbai', 'bengaluru', 'bangalore', 'delhi', 'gurugram', 'gurgaon', 'noida',
    'kolkata', 'chennai', 'hyderabad', 'pune', 'ahmedabad', 'khamgaon', 'haldia', 'haridwar',
    'sumerpur', 'chiplun', 'dharwad', 'mysore', 'mysuru', 'hosur', 'pondicherry', 'puducherry',
    'gujarat', 'maharashtra', 'karnataka', 'tamil nadu', 'telangana', 'west bengal', 'haryana',
    'uttar pradesh', 'rajasthan', 'odisha', 'jharkhand', 'kerala', 'punjab', 'andhra pradesh',
    'madhya pradesh', 'assam', 'bihar', 'chhattisgarh', 'goa', 'uttarakhand', 'himachal pradesh',
    'vadodara', 'surat', 'nagpur', 'indore', 'bhopal', 'visakhapatnam', 'patna', 'kochi', 'coimbatore'
]

for c in companies_with_jobs.order_by('company_id'):
    jobs = Job.objects.filter(company=c, status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).exclude(verification_status='LEGACY_UNVERIFIED')
    if not jobs.exists():
        continue
    overseas = []
    india = []
    for j in jobs:
        loc = (j.location or '').lower()
        if any(k in loc for k in india_keywords):
            india.append(j)
        else:
            overseas.append(j)
    if overseas:
        print(f"{c.company_id}: {c.company_name:<35} | Total Active: {jobs.count():4d} | India: {len(india):4d} | Overseas/Other: {len(overseas):4d}")
        for sample in overseas[:2]:
            print(f"     Sample: '{sample.job_title}' at '{sample.location}' ({sample.application_url})")
