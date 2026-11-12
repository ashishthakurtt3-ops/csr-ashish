import os
import sys
import django
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import ssl
import urllib.request
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.crawler_engine.discovery_helpers import ENTERPRISE_PORTAL_REGISTRY, ENTERPRISE_CSR_REGISTRY

manifest = [
    {"company_name": "HCLTech", "website_url": "https://www.hcltech.com"},
    {"company_name": "Samsung Electronics", "website_url": "https://www.samsung.com"},
    {"company_name": "Pfizer", "website_url": "https://www.pfizer.com"},
    {"company_name": "JPMorgan Chase", "website_url": "https://www.jpmorganchase.com"},
    {"company_name": "Tata Motors", "website_url": "https://www.tatamotors.com"},
    {"company_name": "HSBC", "website_url": "https://www.hsbc.com"},
    {"company_name": "Maruti Suzuki India", "website_url": "https://www.marutisuzuki.com"},
    {"company_name": "SAP", "website_url": "https://www.sap.com"},
    {"company_name": "Tata Steel", "website_url": "https://www.tatasteel.com"},
]

print("=== CHECKING PORTAL REGISTRY FOR 9 COMPANIES ===")
for item in manifest:
    c_lower = item["company_name"].lower()
    reg_p = None
    for k, v in ENTERPRISE_PORTAL_REGISTRY.items():
        if k in c_lower:
            reg_p = (k, v)
            break
    reg_c = None
    for k, v in ENTERPRISE_CSR_REGISTRY.items():
        if k in c_lower:
            reg_c = (k, v)
            break
    print(f"Company: {item['company_name']}")
    print(f"  Portal match: {reg_p}")
    print(f"  CSR match   : {reg_c}")

