import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from modules.admin_panel.models import CSRProject

projects = CSRProject.objects.all().order_by('csr_id')
print(f"Total CSR Projects in DB: {projects.count()}")

flagged = []
for p in projects:
    name_lower = (p.project_name or '').lower().strip()
    if any(s in name_lower for s in ['stakeholder', 'purpose of engagement', 'engagement mechanisms', 'frequency', 'our teams']):
        flagged.append(p)

print(f"Flagged non-project records: {len(flagged)}")
for f in flagged:
    print(f"  [ID {f.csr_id}] {f.company.company_name}: '{f.project_name}' | Source: {f.source_url}")
