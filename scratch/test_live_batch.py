import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
sys.stdout.reconfigure(encoding='utf-8')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company, Job, CompanyCrawlSummary
from modules.crawler_engine.crawler import process_company

test_comps = [
    'COMP_0',           # Razorpay (Greenhouse ATS)
    'COMP_TOP200_001',   # Reliance Industries Limited
    'COMP_TOP200_010',   # Infosys Limited
    'COMP_TOP200_038',   # Wipro Limited
    'COMP_TOP200_007',   # Larsen & Toubro Limited
]

print("=== RUNNING TEST BATCH ON 5 DIVERSE CORPORATIONS ===")
for cid in test_comps:
    try:
        c = Company.objects.get(company_id=cid)
        print(f"\nProcessing {c.company_id}: {c.company_name} | {c.careers_url}")
        process_company(c)
        c.refresh_from_db()
        summary = CompanyCrawlSummary.objects.filter(company=c).order_by('-summary_id').first()
        job_cnt = c.jobs.count()
        active_cnt = c.jobs.filter(status='ACTIVE').count()
        print(f" -> Status: {c.crawl_status} | ATS: {c.ats_platform or 'Direct/HTML'} | Jobs in DB: {job_cnt} (Active: {active_cnt}) | Summary Disc: {summary.jobs_discovered if summary else 0}")
    except Exception as e:
        print(f"Error on {cid}: {e}")
