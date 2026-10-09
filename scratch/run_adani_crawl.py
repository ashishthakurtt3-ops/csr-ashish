import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
import time
from modules.admin_panel.models import Company, Job
from modules.crawler_engine.crawler import process_company

c = Company.objects.get(company_id='COMP_TOP200_017')
print(f"Starting crawl for {c.company_name} ({c.company_id})...", flush=True)
t0 = time.time()
process_company(c)
c.refresh_from_db()
print(f"Done in {time.time()-t0:.2f}s!", flush=True)
print(f"Status: {c.crawl_status}, ATS: {c.ats_platform}", flush=True)
jobs = Job.objects.filter(company=c)
print(f"Jobs in DB for Adani: {jobs.count()}", flush=True)
for j in jobs[:5]:
    print(f"  - {j.job_title} | {j.location} | {j.verification_status} | {j.ats_platform}", flush=True)
