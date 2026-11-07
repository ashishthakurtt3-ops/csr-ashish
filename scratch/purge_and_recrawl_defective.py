import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Job, Company, CSRProject
from modules.crawler_engine.discovery_helpers import (
    is_valid_job_title, is_valid_csr_project,
    derive_deep_job_url, resolve_authentic_csr_url
)
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

print("--- STEP 1: AUDITING AND PURGING INVALID JOBS FROM DB ---")
total_jobs_before = Job.objects.count()
invalid_job_ids = []

for j in Job.objects.all():
    if not is_valid_job_title(j.job_title):
        invalid_job_ids.append(j.job_row_id)

print(f"Found {len(invalid_job_ids)} invalid jobs out of {total_jobs_before}")
if invalid_job_ids:
    deleted_jobs_count = Job.objects.filter(job_row_id__in=invalid_job_ids).delete()[0]
    print(f"Deleted {deleted_jobs_count} invalid jobs from database.")

print("--- STEP 2: AUDITING AND PURGING INVALID CSR FROM DB ---")
total_csr_before = CSRProject.objects.count()
invalid_csr_ids = []

for c in CSRProject.objects.all():
    if not is_valid_csr_project(c.project_name):
        invalid_csr_ids.append(c.csr_id)

print(f"Found {len(invalid_csr_ids)} invalid CSR projects out of {total_csr_before}")
if invalid_csr_ids:
    deleted_csr_count = CSRProject.objects.filter(csr_id__in=invalid_csr_ids).delete()[0]
    print(f"Deleted {deleted_csr_count} invalid CSR projects from database.")

print("--- STEP 3: CLEANING URLS IN REMAINING JOBS ---")
updated_urls_count = 0
for j in Job.objects.all():
    original_url = j.application_url or ''
    # Clean out text fragments and hash anchors
    if '#:~:text=' in original_url or '#job-' in original_url:
        clean_url = original_url.split('#:~:text=')[0].split('#job-')[0].rstrip('/')
        if clean_url:
            j.application_url = clean_url
            j.canonical_url = clean_url
            j.save(update_fields=['application_url', 'canonical_url'])
            updated_urls_count += 1

print(f"Cleaned {updated_urls_count} application URLs with text fragment or hash artifacts.")

print("\nDB Clean Complete. Current Job Count:", Job.objects.count(), "| Current CSR Count:", CSRProject.objects.count())
