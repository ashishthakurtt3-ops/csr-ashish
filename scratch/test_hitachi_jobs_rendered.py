import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.crawler_engine.hybrid_ai_service import HybridAIExtractionService
from modules.crawler_engine.discovery_helpers import is_valid_job_title

dash_url = "https://www.hitachienergy.com/in/en/careers/open-jobs"
r_html, r_text, r_status = BatchDiscoveryService.fetch_rendered_page(dash_url)

jobs = HybridAIExtractionService.extract_unstructured_jobs(
    company_id="COMP_TOP200_050",
    company_name="Hitachi Energy India Limited",
    raw_content=r_text[:12000],
    careers_url=dash_url,
    timeout=20
)
print("Extracted jobs count:", len(jobs) if jobs else 0)
if jobs:
    for j in jobs[:8]:
        print("Job:", j.get('job_title'), "| Valid:", is_valid_job_title(j.get('job_title')))

