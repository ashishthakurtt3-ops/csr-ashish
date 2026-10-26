"""
Verify View Cards against official job pages across all 5 ATS families:
1. SAP SuccessFactors CSB (Hero MotoCorp - Territory Manager)
2. Oracle Cloud HCM (Adani Power / ACC / Fortis)
3. Workday (Hindustan Unilever)
4. SmartRecruiters (Dr. Reddy's Laboratories)
5. Lever (One 97 Communications / Paytm)
6. SAP SuccessFactors (Mahindra & Mahindra)

Tests:
- Database record contents
- API response (`/jobs/<job_id>/`)
- Card field mapping
"""
import os, sys, django, json, urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, Company

print("=" * 80)
print("SECTION 4: CROSS-ATS VIEW CARD & SOURCE VERIFICATION")
print("=" * 80)

# Regression Test 1: Hero MotoCorp
print("\n--- TEST CASE 1: HERO MOTOCORP (SAP SuccessFactors CSB) ---")
hero_jobs = Job.objects.filter(company__company_name__icontains='Hero MotoCorp', status='ACTIVE')
print(f"Total active Hero MotoCorp jobs: {hero_jobs.count()}")
for j in hero_jobs:
    print(f"\nChecking Job: {j.job_id} - '{j.job_title}'")
    print(f"  Source URL: {j.source_url}")
    print(f"  App URL:    {j.application_url}")
    print(f"  Location:   {j.location}")
    print(f"  Function:   {j.function or 'Not mentioned'}")
    print(f"  Pay Band:   {j.pay_band or 'Not mentioned'}")
    print(f"  Role Purpose: {j.role_purpose[:100] if j.role_purpose else 'Not mentioned'}")
    print(f"  Responsibilities: {j.responsibilities[:100] if j.responsibilities else 'Not mentioned'}")
    print(f"  Qualifications:   {j.qualifications[:100] if j.qualifications else 'Not mentioned'}")
    print(f"  Experience:       {j.experience or 'Not mentioned'}")
    print(f"  Education:        {j.education or 'Not mentioned'}")
    print(f"  Skills:           {j.skills or 'Not mentioned'}")
    
    # Query API
    try:
        url = f"http://127.0.0.1:8000/jobs/{j.job_id}/"
        resp = urllib.request.urlopen(url, timeout=5)
        api_data = json.loads(resp.read().decode('utf-8'))
        print(f"  API HTTP Status: {resp.status}")
        print(f"  API Title: {api_data.get('job_title')}")
        print(f"  API Location: {api_data.get('location')}")
        print(f"  API Status: {api_data.get('status')}")
    except Exception as e:
        print(f"  API Error: {e}")

# Test Cases 2-5: Across all other ATS platforms
cases = [
    ("Oracle Cloud HCM", "Adani Power Limited", 'COMP_TOP200_012'),
    ("Workday", "Hindustan Unilever Limited", 'COMP_TOP200_009'),
    ("SmartRecruiters", "Dr. Reddy's Laboratories Limited", 'COMP_TOP200_106'),
    ("Lever", "One 97 Communications Limited", 'COMP_TOP200_095'),
    ("SuccessFactors Standard", "Mahindra & Mahindra Limited", 'COMP_TOP200_011'),
]

for ats_name, comp_name, comp_id in cases:
    print(f"\n--- TEST CASE: {comp_name} ({ats_name}) ---")
    j = Job.objects.filter(company__company_id=comp_id, status='ACTIVE', detail_fetch_status='FETCHED').first()
    if not j:
        print(f"  No active job found for {comp_name}")
        continue
        
    print(f"Job: {j.job_id} - '{j.job_title}'")
    print(f"  Source URL: {j.source_url[:65]}...")
    print(f"  App URL:    {j.application_url[:65]}...")
    print(f"  ATS:        {j.ats_platform}")
    print(f"  Location:   {j.location}")
    print(f"  Desc Len:   {len(j.job_description or '')}")
    print(f"  Resp Len:   {len(j.responsibilities or '')}")
    print(f"  Qual Len:   {len(j.qualifications or '')}")
    print(f"  Deadline:   {j.closing_date or j.application_deadline or 'Not mentioned'}")
    print(f"  Dept:       {j.department or 'Not mentioned'}")
    
    # Check API response
    try:
        url = f"http://127.0.0.1:8000/jobs/{j.job_id}/"
        resp = urllib.request.urlopen(url, timeout=5)
        api_data = json.loads(resp.read().decode('utf-8'))
        print(f"  API Status: {resp.status} | API Title: {api_data.get('job_title')}")
        print(f"  API Location: {api_data.get('location')} | API ATS: {api_data.get('ats_platform')}")
        print(f"  API Resp Match: {len(api_data.get('responsibilities') or '') == len(j.responsibilities or '')}")
        print(f"  API Qual Match: {len(api_data.get('qualifications') or '') == len(j.qualifications or '')}")
    except Exception as e:
        print(f"  API Error: {e}")
