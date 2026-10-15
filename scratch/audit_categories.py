import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db.models import Q
from modules.admin_panel.models import Job
from modules.website.views.job_api_views import (
    ALL_STANDARD_JOB_CATEGORIES_Q,
    JOB_CATEGORY_MAP,
    TECH_Q, ENGINEERING_Q, FINANCE_Q, OPERATIONS_Q, SALES_Q,
    HR_Q, CSR_Q, HEALTHCARE_Q, LEGAL_Q
)

base_qs = Job.objects.filter(
    status='ACTIVE'
).exclude(
    verification_status__in=['STALE', 'REJECTED', 'FETCH_FAILED', 'INVALID_SOURCE', 'BLOCKED', 'LEGACY_UNVERIFIED']
).filter(
    Q(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']) | Q(link_status='PUBLISHED')
)

total_eligible_ids = set(base_qs.values_list('job_row_id', flat=True))
print(f"1. Total distinct eligible job IDs: {len(total_eligible_ids)}")

# Test current category queries
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
}

uncat_q = Q(department__isnull=True) | Q(department='') | Q(department__iexact='uncategorized') | Q(department__iexact='unspecified')
others_q_current = base_qs.exclude(ALL_STANDARD_JOB_CATEGORIES_Q).exclude(uncat_q)

cat_id_map = {k: set(qs.values_list('job_row_id', flat=True)) for k, qs in categories.items()}
cat_id_map['uncategorized'] = set(base_qs.filter(uncat_q).values_list('job_row_id', flat=True))
cat_id_map['others'] = set(others_q_current.values_list('job_row_id', flat=True))

print("\n2. Distinct job IDs returned by each category filter:")
for cat_name, ids in cat_id_map.items():
    print(f"  - {cat_name}: {len(ids)}")

sum_cats = sum(len(ids) for ids in cat_id_map.values())
print(f"  Sum of all categories: {sum_cats} (vs 610 total)")

print("\n3. Overlaps with Uncategorized:")
uncat_ids = cat_id_map['uncategorized']
for cat_name, ids in cat_id_map.items():
    if cat_name != 'uncategorized':
        overlap = uncat_ids.intersection(ids)
        if overlap:
            print(f"  - Uncategorized & {cat_name} overlap count: {len(overlap)}")

print("\n4. Overlaps between standard categories:")
keys = list(categories.keys())
for i in range(len(keys)):
    for j in range(i + 1, len(keys)):
        c1, c2 = keys[i], keys[j]
        overlap = cat_id_map[c1].intersection(cat_id_map[c2])
        if overlap:
            print(f"  - {c1} & {c2} overlap count: {len(overlap)}")

print("\n5. Sample overlapping records (Tech & Uncategorized):")
tech_uncat_overlap = uncat_ids.intersection(cat_id_map['tech'])
for job in base_qs.filter(job_row_id__in=list(tech_uncat_overlap)[:10]):
    print(f"  ID {job.job_row_id}: Title='{job.job_title}', Dept='{job.department}', Function='{job.function}'")

print("\n6. Sample overlapping records between Standard Categories (e.g. Tech & Engineering):")
tech_eng_overlap = cat_id_map['tech'].intersection(cat_id_map['engineering'])
for job in base_qs.filter(job_row_id__in=list(tech_eng_overlap)[:10]):
    print(f"  ID {job.job_row_id}: Title='{job.job_title}', Dept='{job.department}', Function='{job.function}'")
