import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models.company import Company
from urllib.parse import urlparse

suspicious_comps = []
for c in Company.objects.all():
    w = c.website_url or ''
    car = c.careers_url or ''
    if not car:
        continue
    w_dom = urlparse(w).netloc.lower().replace('www.', '')
    car_dom = urlparse(car).netloc.lower().replace('www.', '')
    
    # Common cross-entity checks
    # Check if car_dom has another company name
    other_keywords = ['adani', 'tata', 'reliance', 'birla', 'infosys', 'wipro', 'hcl', 'techmahindra']
    for kw in other_keywords:
        if kw in car_dom and kw not in c.company_name.lower() and kw not in w_dom:
            suspicious_comps.append((c.company_id, c.company_name, w, car))

print("Suspicious cross-entity company careers_urls:")
for sc in suspicious_comps:
    print(sc)
