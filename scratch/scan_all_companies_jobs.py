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
from modules.admin_panel.models import Job, Company
from django.db.models import Count




print("=== Scanning Active Jobs by Company & URL Host/Path ===")
companies_with_jobs = Job.objects.filter(status='ACTIVE').exclude(verification_status='REJECTED').values('company_id').annotate(cnt=Count('job_row_id')).order_by('-cnt')


for item in companies_with_jobs:
    cid = item['company_id']
    cnt = item['cnt']
    cname = Company.objects.filter(company_id=cid).values_list('company_name', flat=True).first() or 'Unknown'
    jobs = Job.objects.filter(company_id=cid, status='ACTIVE').exclude(verification_status='REJECTED')
    sample_urls = set()
    sample_titles = []
    for j in jobs[:8]:
        sample_urls.add((j.application_url or j.source_url or '')[:65])
        sample_titles.append(j.job_title[:45])
    print(f"\n[{cid}] {cname} (Total Active: {cnt})")
    print(f"   URLs: {list(sample_urls)[:3]}")
    print(f"   Titles: {sample_titles[:4]}")
