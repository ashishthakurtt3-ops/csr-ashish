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

print("Auditing remaining ACTIVE jobs...")
jobs = Job.objects.filter(status='ACTIVE').exclude(verification_status='REJECTED')
print(f"Total active records: {jobs.count()}")

patterns_to_check = [
    # SBI Life leadership
    ('SBI Life Leadership / Contact', lambda j: 'sbilife.co.in/about/leadership-team' in (j.application_url or '') or (j.job_title or '').startswith('+91') or (j.job_title or '').startswith('LIBERATE') or (j.job_title or '').startswith('Mr. ')),
    # RBL Bank products
    ('RBL Bank products', lambda j: 'rbl.bank.in' in (j.application_url or '') or (j.job_title or '').endswith(' Loan') or (j.job_title or '') in ['Current Accounts', 'Credit Cards', 'Term Deposits', 'Savings Accounts']),
    # Siemens marketing
    ('Siemens marketing', lambda j: 'siemens.com' in (j.application_url or '') and (j.job_title or '') in ['Innovating the future of rail, travel & transport', 'We create technology that the world needs', 'Connecting energy systems, buildings & industries.', 'An innovator in automation and digitalization', 'WE Stand for values', 'Belonging at Siemens', 'Explore all jobs']),
    # Generic URLs
    ('SMS / WhatsApp / Mailto', lambda j: any((j.application_url or '').startswith(p) for p in ['sms:', 'tel:', 'mailto:', 'https://wa.me/'])),
    ('Careers webpage / portal header', lambda j: (j.job_title or '').lower() in ['careers webpage', 'careers page', 'explore all jobs', 'open jobs', 'current jobs', 'all jobs']),
]

for label, cond in patterns_to_check:
    matched = [j for j in jobs if cond(j)]
    print(f"\n--- {label}: {len(matched)} matched ---")
    for j in matched[:5]:
        print(f"   [{j.company_id}] '{j.job_title}' -> {j.application_url[:60] if j.application_url else 'None'}")
