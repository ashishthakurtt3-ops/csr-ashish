import os
import sys
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job

active_jobs = Job.objects.filter(status='ACTIVE')
print(f"Total active jobs: {active_jobs.count()}")

# Print all distinct titles that do NOT contain typical job title nouns:
job_nouns = [
    'manager', 'officer', 'lead', 'head', 'analyst', 'engineer', 'specialist',
    'executive', 'director', 'intern', 'trainee', 'associate', 'consultant',
    'vp', 'president', 'developer', 'operator', 'supervisor', 'technician',
    'rider', 'agent', 'advisor', 'clerk', 'assistant', 'expert', 'architect',
    'sales', 'marketing', 'finance', 'accountant', 'legal', 'chemist', 'scientist',
    'pilot', 'nurse', 'doctor', 'staff', 'faculty', 'planner', 'buyer', 'recruiter',
    'electrician', 'mechanic', 'fitter', 'welder', 'turner', 'machinist', 'attendant',
    'coordinator', 'administrator', 'worker', 'counselor', 'instructor', 'trainer',
    'programmer', 'tester', 'auditor', 'collector', 'representative', 'teller',
    'teller', 'cashier', 'driver', 'guard', 'steward', 'chef', 'cook', 'waiter',
    'traineeship', 'internship', 'fellow', 'fellowship', 'graduate', 'undergraduate',
    'apprentice', 'apprenticeship', 'professional', 'generalist', 'specialist'
]

non_job_candidates = []
for j in active_jobs:
    t = (j.job_title or '').strip()
    tl = t.lower()
    has_noun = any(jn in tl for jn in job_nouns)
    if not has_noun:
        non_job_candidates.append(j)

print(f"Active jobs lacking any recognizable job role keyword: {len(non_job_candidates)}")
sample = [(j.company.company_name, j.job_id, j.job_title, j.application_url) for j in non_job_candidates[:50]]
for cname, jid, title, url in sample:
    print(f"  [{cname[:20]}] '{title}' | URL: {url[:60] if url else 'None'}")
