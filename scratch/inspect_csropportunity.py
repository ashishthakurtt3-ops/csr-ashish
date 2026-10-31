import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import CSROpportunity

opps = CSROpportunity.objects.all()[:15]
print("=== SAMPLE CSROpportunity ROWS ===")
for o in opps:
    print(f"ID: {o.opp_id} | Comp: {o.company_id} | Title: {o.title} | Type: {o.opportunity_type} | Category: {o.category} | Status: {o.status} | Source: {o.source_url} | Portal: {o.portal_url} | Evidence: {o.evidence_text[:50] if o.evidence_text else None}")
