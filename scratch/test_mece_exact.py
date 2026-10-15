import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import Q
from modules.admin_panel.models import Job

base_qs = Job.objects.filter(
    status='ACTIVE'
).exclude(
    verification_status__in=['STALE', 'REJECTED', 'FETCH_FAILED', 'INVALID_SOURCE', 'BLOCKED', 'LEGACY_UNVERIFIED']
).filter(
    Q(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']) | Q(link_status='PUBLISHED')
)

UNCATEGORIZED_JOB_Q = (
    Q(department__isnull=True) | Q(department='') |
    Q(department__iexact='uncategorized') | Q(department__iexact='unspecified') |
    Q(department__iexact='none') | Q(department__iexact='null')
)

TECH_Q = ~UNCATEGORIZED_JOB_Q & (
    Q(department__icontains='technology') | Q(department__icontains='tech') |
    Q(department__icontains='software') | Q(department__icontains='data') |
    Q(department__icontains='analytics') | Q(department__icontains='product') |
    Q(department__icontains='design') | Q(department__icontains='paytm labs') |
    Q(department__iexact='IT') | Q(function__icontains='information technology')
)

ENGINEERING_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & (
    Q(department__icontains='engineering') | Q(department__icontains='manufacturing') |
    Q(department__icontains='automation') | Q(department__icontains='maintenance') |
    Q(department__icontains='plant') | Q(department__icontains='process') |
    Q(function__icontains='engineering')
)

FINANCE_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & (
    Q(department__icontains='finance') | Q(department__icontains='banking') |
    Q(department__icontains='accounts') | Q(department__icontains='treasury') |
    Q(department__icontains='audit') | Q(department__icontains='tax') |
    Q(function__icontains='finance')
)

OPERATIONS_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & (
    Q(department__icontains='operation') | Q(department__icontains='supply') |
    Q(department__icontains='logistics') | Q(department__icontains='procurement') |
    Q(department__icontains='purchase') | Q(department__icontains='support') |
    Q(function__icontains='supply chain')
)

SALES_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & ~OPERATIONS_Q & (
    Q(department__icontains='sales') | Q(department__icontains='marketing') |
    Q(department__icontains='commercial') | Q(department__icontains='brand') |
    Q(function__icontains='sales') | Q(function__icontains='marketing')
)

HR_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & ~OPERATIONS_Q & ~SALES_Q & (
    Q(department__icontains='hr') | Q(department__icontains='human resources') |
    Q(department__icontains='people') | Q(department__icontains='talent') |
    Q(function__icontains='human resources')
)

CSR_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & ~OPERATIONS_Q & ~SALES_Q & ~HR_Q & (
    Q(department__icontains='csr') | Q(department__icontains='sustainability') |
    Q(department__icontains='esg') | Q(department__icontains='community') |
    Q(function__icontains='sustainability')
)

HEALTHCARE_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & ~OPERATIONS_Q & ~SALES_Q & ~HR_Q & ~CSR_Q & (
    Q(department__icontains='health') | Q(department__icontains='pharma') |
    Q(department__icontains='medical') | Q(department__icontains='clinical') |
    Q(function__icontains='healthcare')
)

LEGAL_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & ~OPERATIONS_Q & ~SALES_Q & ~HR_Q & ~CSR_Q & ~HEALTHCARE_Q & (
    Q(department__icontains='legal') | Q(department__icontains='compliance') |
    Q(department__icontains='regulatory') | Q(department__icontains='secretarial') |
    Q(department__icontains='governance') | Q(function__icontains='legal')
)

ALL_STANDARD_JOB_CATEGORIES_Q = (
    TECH_Q | ENGINEERING_Q | FINANCE_Q | OPERATIONS_Q | SALES_Q | HR_Q | CSR_Q | HEALTHCARE_Q | LEGAL_Q
)

OTHERS_JOB_Q = ~UNCATEGORIZED_JOB_Q & ~ALL_STANDARD_JOB_CATEGORIES_Q

categories = {
    'tech': base_qs.filter(TECH_Q),
    'engineering': base_qs.filter(ENGINEERING_Q),
    'finance': base_qs.filter(FINANCE_Q),
    'operations': base_qs.filter(OPERATIONS_Q),
    'sales': base_qs.filter(SALES_Q),
    'hr': base_qs.filter(HR_Q),
    'csr': base_qs.filter(CSR_Q),
    'healthcare': base_qs.filter(HEALTHCARE_Q),
    'legal': base_qs.filter(LEGAL_Q),
    'others': base_qs.filter(OTHERS_JOB_Q),
    'uncategorized': base_qs.filter(UNCATEGORIZED_JOB_Q),
}

cat_ids = {name: set(qs.values_list('job_row_id', flat=True)) for name, qs in categories.items()}
total_eligible_ids = set(base_qs.values_list('job_row_id', flat=True))

print("=== CATEGORY VERIFICATION ===")
for name, ids in cat_ids.items():
    print(f"{name:15}: {len(ids)}")

sum_counts = sum(len(ids) for ids in cat_ids.values())
print(f"Total eligible : {len(total_eligible_ids)}")
print(f"Sum of parts   : {sum_counts}")
print(f"Discrepancy    : {sum_counts - len(total_eligible_ids)}")

# Check pairwise overlap
overlap_found = False
cat_names = list(cat_ids.keys())
for i in range(len(cat_names)):
    for j in range(i + 1, len(cat_names)):
        c1, c2 = cat_names[i], cat_names[j]
        intersection = cat_ids[c1].intersection(cat_ids[c2])
        if intersection:
            print(f"OVERLAP: {c1} & {c2} -> {len(intersection)} records!")
            overlap_found = True

if not overlap_found:
    print("ALL CATEGORIES ARE 100% MUTUALLY EXCLUSIVE! ZERO OVERLAP.")

# Check union matches total
union_all = set()
for ids in cat_ids.values():
    union_all.update(ids)
print(f"Union equals total: {union_all == total_eligible_ids}")
