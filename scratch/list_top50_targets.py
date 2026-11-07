import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Company

comps = Company.objects.filter(company_id__startswith='COMP_TOP200_').order_by('company_id')[:50]
for idx, c in enumerate(comps, 1):
    print(f"[{idx}] {c.company_id}: {c.company_name} | Web: {c.website_url} | Careers: {c.careers_url} | CSR: {c.csr_portal_url}")

