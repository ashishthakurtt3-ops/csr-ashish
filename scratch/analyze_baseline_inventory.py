import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from collections import Counter
from modules.admin_panel.models import Job, CSRProject, CSROpportunity

def analyze_model(model, pk_name):
    total = model.objects.count()
    pks = list(model.objects.values_list(pk_name, flat=True).order_by(pk_name))
    min_pk = pks[0] if pks else None
    max_pk = pks[-1] if pks else None
    
    # Status distributions
    stat_counter = Counter(model.objects.values_list('status', flat=True))
    ver_counter = Counter(model.objects.values_list('verification_status', flat=True))
    
    print(f"\n=== {model.__name__} ===")
    print(f"Total Rows: {total}")
    print(f"Primary Key: {pk_name} (min: {min_pk}, max: {max_pk})")
    print(f"Status breakdown: {dict(stat_counter)}")
    print(f"Verification status breakdown: {dict(ver_counter)}")
    
    if hasattr(model, 'is_defective'):
        def_counter = Counter(model.objects.values_list('is_defective', flat=True))
        print(f"is_defective breakdown: {dict(def_counter)}")
    if hasattr(model, 'link_quality'):
        lq_counter = Counter(model.objects.values_list('link_quality', flat=True))
        print(f"link_quality breakdown: {dict(lq_counter)}")

analyze_model(Job, 'job_row_id')
analyze_model(CSRProject, 'csr_id')
analyze_model(CSROpportunity, 'opp_id')
