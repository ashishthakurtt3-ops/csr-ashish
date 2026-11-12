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

test_companies = [
    ('HCLTech', 'https://www.hcltech.com'),
    ('JPMorgan Chase', 'https://www.jpmorganchase.com'),
    ('Tata Steel', 'https://www.tatasteel.com'),
    ('Pfizer', 'https://www.pfizer.com'),
    ('Samsung Electronics', 'https://www.samsung.com'),
    ('Tata Motors', 'https://careers.tatamotors.com/go/View-All-Opportunities/3505801/'),
    ('SAP', 'https://jobs.sap.com/'),
    ('Maruti Suzuki India', 'https://maruti.app.param.ai/jobs/'),
    ('HSBC', 'https://mycareer.hsbc.com/en_GB/external'),
]

for name, url in test_companies:
    print('=' * 60)
    print(f'TESTING: {name} ({url})')
    c = Company(company_name=name, website_url=url)
    logs = []
    reg_url = ENTERPRISE_PORTAL_REGISTRY.get(name.lower()) or url
    jobs = BatchDiscoveryService.discover_all_real_jobs(c, reg_url, '', '', 'Technology', logs)
    print(f'RESULT: {len(jobs)} jobs found')
    for l in logs:
        print('  LOG:', l)
    if jobs:
        print(f'  First Job: {jobs[0]["job_title"]}')
        print(f'  Apply URL: {jobs[0]["application_url"]}')
        print(f'  Location:  {jobs[0]["location"]}')
        print(f'  Req ID:    {jobs[0].get("requisition_id")}')
