import os, sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
import django
from django.db.models import Count, Q

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, Company
from modules.website.views.job_api_views import serialize_job_item
import requests

# Let's find jobs with diverse ATS platforms
candidates = [
    # 1. Greenhouse / Razorpay
    Job.objects.filter(application_url__icontains='greenhouse.io').first(),
    # 2. Lever / Paytm
    Job.objects.filter(application_url__icontains='lever.co').first(),
    # 3. SuccessFactors / Mahindra
    Job.objects.filter(application_url__icontains='jobs.mahindracareers.com').first(),
    # 4. SmartRecruiters
    Job.objects.filter(application_url__icontains='smartrecruiters.com').first(),
    # 5. Generic / Corporate Careers
    Job.objects.filter(application_url__icontains='tatamotors.com').first() or Job.objects.filter(application_url__startswith='http').exclude(application_url__icontains='greenhouse').exclude(application_url__icontains='lever').exclude(application_url__icontains='mahindra').first(),
]

candidates = [c for c in candidates if c is not None]

print(f"Inspecting {len(candidates)} jobs:")
for idx, job in enumerate(candidates, 1):
    print(f"\n==========================================")
    print(f"JOB #{idx}: ID={job.job_row_id} | {job.job_title} @ {job.company.company_name}")
    print(f"ATS: {job.ats_platform} | URL: {job.application_url}")
    
    # a. Live fetch
    live_content = ""
    try:
        r = requests.get(job.application_url, timeout=6, headers={'User-Agent': 'Mozilla/5.0'})
        live_content = r.text if r.status_code == 200 else f"HTTP {r.status_code}"
        has_resp = any(k in live_content.lower() for k in ['responsibilit', 'what you will do', 'duties'])
        has_edu = any(k in live_content.lower() for k in ['qualification', 'education', 'degree', 'bachelor'])
        has_skills = any(k in live_content.lower() for k in ['skills', 'proficien', 'experience with'])
        has_benefits = any(k in live_content.lower() for k in ['benefits', 'perks', 'insurance'])
        print(f"a. Official Page ({r.status_code}): length={len(live_content)} | Has Resp: {has_resp} | Has Edu: {has_edu} | Has Skills: {has_skills} | Has Benefits: {has_benefits}")
    except Exception as e:
        print(f"a. Official Page: Fetch failed ({e})")

    # b. Database
    print(f"b. Database fields:")
    print(f"   job_description len: {len(job.job_description or '')}")
    print(f"   responsibilities: {job.responsibilities[:80] if job.responsibilities else 'EMPTY'}")
    print(f"   education: {job.education[:80] if job.education else 'EMPTY'}")
    print(f"   qualifications: {job.qualifications[:80] if job.qualifications else 'EMPTY'}")
    print(f"   skills: {job.skills[:80] if job.skills else 'EMPTY'}")
    print(f"   benefits: {job.benefits[:80] if job.benefits else 'EMPTY'}")
    print(f"   work_mode: {job.work_mode}")
    print(f"   external_job_id: {job.external_job_id}")

    # c. API
    serialized = serialize_job_item(job)
    print(f"c. API output keys present with values:")
    api_fields = {k: bool(v) for k, v in serialized.items() if k in ['job_description', 'responsibilities', 'qualifications', 'education', 'skills', 'benefits', 'work_mode', 'salary']}
    print(f"   {api_fields}")

    # d. Breakdown of where data is lost
    print(f"d. Loss Diagnosis:")
    if not job.job_description or len(job.job_description) < 100:
        print("   -> LOST AT SCRAPING STAGE: Job detail was never crawled or detail page fetch was missed.")
    elif not job.responsibilities or not job.education or not job.skills:
        print("   -> LOST AT EXTRACTION/STORAGE STAGE: Page/description was scraped, but sections (responsibilities, education, skills) were not parsed into dedicated structured fields in DB.")
    else:
        print("   -> PRESERVED in DB.")
