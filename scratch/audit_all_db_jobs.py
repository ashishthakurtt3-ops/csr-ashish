import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from modules.admin_panel.models import Job, Company, CSRProject
from modules.crawler_engine.discovery_helpers import is_valid_job_title, is_valid_csr_project

print("Total jobs in DB:", Job.objects.count())

invalid_jobs = []
for j in Job.objects.all():
    if not is_valid_job_title(j.job_title):
        invalid_jobs.append((j.company.company_name, j.job_title, j.application_url))

print(f"Total invalid jobs in DB according to current is_valid_job_title: {len(invalid_jobs)}")
for comp, title, url in invalid_jobs[:20]:
    print(f"  [{comp[:20]}] '{title}' -> {url}")

print("\nSample valid jobs:")
for j in Job.objects.all()[:10]:
    print(f"  [{j.company.company_name[:20]}] '{j.job_title}' -> {j.application_url}")

