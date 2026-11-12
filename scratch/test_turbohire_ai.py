import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.crawler_engine.hybrid_ai_service import HybridAIExtractionService

dash_url = "https://tatamotors.turbohire.co/dashboardv2?orgId=39ddba0d-55f7-4206-abf0-e6121e93436a&type=0"
r_html, r_text, r_status = BatchDiscoveryService.fetch_rendered_page(dash_url)
print("Rendered text len:", len(r_text))

jobs = HybridAIExtractionService.extract_unstructured_jobs(
    company_id="COMP_TEST",
    company_name="Tata Motors Limited",
    raw_content=r_text[:10000],
    careers_url=dash_url,
    timeout=20
)
print("Extracted jobs count:", len(jobs) if jobs else 0)
if jobs:
    for j in jobs[:5]:
        print("Job:", j)
