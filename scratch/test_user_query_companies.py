import os
import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.crawler_engine.discovery_helpers import ENTERPRISE_PORTAL_REGISTRY

target_companies = [
    ('HCLTech', 'https://www.hcltech.com'),
    ('JPMorgan Chase', 'https://www.jpmorganchase.com'),
    ('Tata Steel', 'https://www.tatasteel.com'),
]

for name, url in target_companies:
    print('=' * 60, flush=True)
    print(f'TESTING: {name}', flush=True)
    c = Company(company_name=name, website_url=url)
    logs = []
    reg_url = ENTERPRISE_PORTAL_REGISTRY.get(name.lower()) or url
    jobs = BatchDiscoveryService.discover_all_real_jobs(c, reg_url, '', '', 'Technology', logs)
    print(f'RESULT: {len(jobs)} jobs extracted for {name}', flush=True)
    for l in logs:
        print(f'  [LOG] {l}', flush=True)
    for j in jobs[:3]:
        print(f'  -> Job: {j.get("job_title")} | Location: {j.get("location")} | Apply URL: {j.get("application_url")}', flush=True)

