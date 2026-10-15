import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from modules.admin_panel.models import CSROpportunity

opps = CSROpportunity.objects.all().order_by('opp_id')
print(f"Total CSROpportunity records in DB: {opps.count()}")
open_opps = opps.filter(status='OPEN')
print(f"Total OPEN CSROpportunity records: {open_opps.count()}")

print("\nAll Open Opportunities detail:")
for o in open_opps:
    print(f"ID {o.opp_id}: '{o.title}' | Company: {o.company.company_name} ({o.company_id})")
    print(f"   Status: {o.status} | Verification: {o.verification_status} | Type: {o.opportunity_type}")
    print(f"   Deadline: {o.submission_deadline}")
    print(f"   Source URL: {o.source_url}")
    print(f"   Portal URL: {o.portal_url}")
    print(f"   Requirements: {str(o.requirements)[:150]}...")
    print("-" * 70)
