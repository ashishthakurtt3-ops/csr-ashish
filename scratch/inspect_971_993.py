import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import CSRProject

for pid in [971, 993]:
    p = CSRProject.objects.get(csr_id=pid)
    print(f"=== PROJECT {pid} ===")
    print("Project Name:", p.project_name)
    print("Company:", p.company.company_name, f"({p.company_id})")
    print("Budget:", p.budget)
    print("Source URL:", p.source_url)
    print("Locator:", p.evidence_locator)
    print("Evidence text:", repr(p.evidence_text[:300]))
    print("Source domain:", p.source_domain)
    print("Source type:", p.source_type)
    print("Retrieved at:", p.retrieved_at)
    print("Discovered date:", p.discovered_date)
    print("Verification status:", p.verification_status)
    print()
