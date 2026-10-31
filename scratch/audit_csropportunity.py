import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from collections import Counter
from modules.admin_panel.models import CSROpportunity

opps = CSROpportunity.objects.all()
total = opps.count()
print(f"Total CSROpportunity rows: {total}")

# Look at opportunity_type distribution
print("Opportunity Types:", Counter(opps.values_list('opportunity_type', flat=True)))
# Look at categories
print("Categories:", Counter(opps.values_list('category', flat=True)))

# Look at source_url patterns
sources = list(opps.values_list('source_url', flat=True))
bad_kw = ['privacy-policy', 'cookie-policy', 'terms', 'disclaimer', 'contact-us', 'login', '#:~:text=']
bad_counts = {kw: sum(1 for s in sources if s and kw in s.lower()) for kw in bad_kw}
print("Source URL suspicious patterns:", bad_counts)

# Sample 20 random rows from different companies
print("\n--- SAMPLE 20 DISTINCT CSROpportunity TITLES & SOURCES ---")
for o in opps.order_by('?')[:20]:
    print(f"[{o.opp_id}] {o.company.company_name if o.company else 'None'}: '{o.title[:70]}' -> {o.source_url[:80]}")
