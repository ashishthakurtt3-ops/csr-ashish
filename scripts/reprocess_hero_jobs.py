import os, sys
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models.company import Company
from modules.admin_panel.models.job import Job
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor
from modules.crawler_engine.verification_service import VerificationService
from django.utils import timezone

print("=== REPAIRING HERO MOTOCORP TERRITORY MANAGER JOBS ===")
hero_comp = Company.objects.filter(company_name__icontains='Hero').first()
print(f"Company: {hero_comp.company_name} ({hero_comp.company_id})")

jobs = Job.objects.filter(company=hero_comp, job_title__icontains='TERRITORY MANAGER-SALES')
print(f"Found {jobs.count()} matching jobs:")

for j in jobs:
    print(f"\nProcessing Job {j.job_row_id}: {j.job_title} | App URL: {j.application_url}")
    if not j.application_url:
        print("  Skipping: No application URL")
        continue

    # Use the application's supported crawler extraction pipeline (UniversalJobDetailExtractor)
    extracted = UniversalJobDetailExtractor.extract_from_url(j.application_url)
    print(f"  Extraction status: {extracted['detail_fetch_status']}")
    print(f"  Extracted title: {extracted['job_title']}")
    print(f"  Extracted date: {extracted['posted_date']}")
    print(f"  Extracted location: {extracted['location']} (City: {extracted['city']}, State: {extracted['state']}, Country: {extracted['country']}, Pincode: {extracted['pincode']})")
    print(f"  Extracted function: {extracted['function']}")
    print(f"  Extracted pay band: {extracted['pay_band']}")
    print(f"  Extracted role purpose len: {len(extracted['role_purpose'] or '')}")
    print(f"  Extracted responsibilities len: {len(extracted['responsibilities'] or '')}")
    print(f"  Extracted day in the life len: {len(extracted['day_in_the_life'] or '')}")
    print(f"  Extracted qualifications len: {len(extracted['qualifications'] or '')}")
    print(f"  Extracted education: {extracted['education']}")
    print(f"  Extracted experience: {extracted['experience']}")
    print(f"  Extracted technical skills len: {len(extracted['technical_skills'] or '')}")
    print(f"  Extracted behavioural skills len: {len(extracted['behavioural_skills'] or '')}")
    print(f"  Extracted employer info len: {len(extracted['employer_info'] or '')}")
    print(f"  Extracted structured details: {list(extracted['structured_details'].keys())}")

    # Persist directly into the database row
    if extracted['job_title']:
        j.job_title = extracted['job_title']
    if extracted['external_job_id']:
        j.external_job_id = extracted['external_job_id']
    if extracted['posted_date']:
        j.posted_date = extracted['posted_date']
    if extracted['location']:
        j.location = extracted['location']
        j.city = extracted['city']
        j.state = extracted['state']
        j.country = extracted['country'] or 'India'
    if extracted['function']:
        j.function = extracted['function']
        j.department = extracted['function']  # India BU
    if extracted['pay_band']:
        j.pay_band = extracted['pay_band']
    if extracted['role_purpose']:
        j.role_purpose = extracted['role_purpose']
    if extracted['responsibilities']:
        j.responsibilities = extracted['responsibilities']
    if extracted['day_in_the_life']:
        j.day_in_the_life = extracted['day_in_the_life']
    if extracted['qualifications']:
        j.qualifications = extracted['qualifications']
    if extracted['education']:
        j.education = extracted['education']
    if extracted['experience']:
        j.experience = extracted['experience']
    if extracted['technical_skills']:
        j.technical_skills = extracted['technical_skills']
    if extracted['behavioural_skills']:
        j.behavioural_skills = extracted['behavioural_skills']
    if extracted['skills']:
        j.skills = extracted['skills']
    if extracted['employer_info']:
        j.employer_info = extracted['employer_info']
    if extracted['job_description']:
        j.job_description = extracted['job_description']
    if extracted['structured_details']:
        j.structured_details = extracted['structured_details']

    j.detail_fetched = extracted['detail_fetched']
    j.detail_fetch_status = extracted['detail_fetch_status']
    j.detail_fetched_at = timezone.now().isoformat()
    j.last_checked_date = timezone.now().isoformat()
    j.ats_platform = 'SAP SuccessFactors'
    j.evidence_text = extracted['evidence_text']
    j.save()

    # Re-verify record with VerificationService
    VerificationService.publish_record(j, actor="SourceIntegrityPipeline")
    print(f"  Saved & Published Job {j.job_row_id}! Verification Status: {j.verification_status}")

print("\n--- Testing API Serializer on Job 6570 ---")
from modules.website.views.job_api_views import serialize_job_item
j6570 = Job.objects.get(job_row_id=6570)
api_res = serialize_job_item(j6570)
fields_to_check = [
    'job_title', 'external_job_id', 'posted_date', 'location', 'city', 'state', 'country',
    'function', 'department', 'pay_band', 'salary', 'role_purpose', 'responsibilities',
    'day_in_the_life', 'qualifications', 'education', 'experience', 'technical_skills',
    'behavioural_skills', 'skills', 'employer_info', 'detail_fetched', 'detail_fetch_status'
]
for f in fields_to_check:
    val = api_res.get(f)
    print(f"  API [{f}]: {str(val)[:80] if val is not None else 'None'}")
