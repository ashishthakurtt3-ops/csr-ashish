import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from modules.admin_panel.models import Company

print("=== CANONICAL COMPANY IDENTITY AUDIT ===")
companies = list(Company.objects.all().order_by('company_id'))
print(f"Total Canonical Enterprises: {len(companies)}")

# Check for pattern of synthetic CINs
# Synthetic pattern noticed earlier: L\d{5}MH\d{4}PLC\d{6}
synthetic_like = 0
mh_cins = 0
for c in companies:
    cin = c.cin or ''
    if 'MH' in cin:
        mh_cins += 1

print(f"Companies with 'MH' in CIN: {mh_cins} / {len(companies)}")
print(f"HUL current in DB: CIN='{Company.objects.get(company_id='COMP_TOP200_009').cin}', HQ='{Company.objects.get(company_id='COMP_TOP200_009').headquarters}'")
