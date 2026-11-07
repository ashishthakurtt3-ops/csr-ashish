import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from modules.admin_panel.models import CSRProject
from modules.crawler_engine.discovery_helpers import is_valid_csr_project

print("Total CSR projects in DB:", CSRProject.objects.count())

invalid_csr = []
for c in CSRProject.objects.all():
    if not is_valid_csr_project(c.project_name):
        invalid_csr.append((c.company.company_name, c.project_name, c.source_url))

print(f"Total invalid CSR projects in DB: {len(invalid_csr)}")
for comp, name, url in invalid_csr[:25]:
    print(f"  [{comp[:20]}] '{name}' -> {url}")

print("\nSample CSR projects in DB:")
for c in CSRProject.objects.all()[:15]:
    print(f"  [{c.company.company_name[:20]}] '{c.project_name}' -> {c.source_url}")

