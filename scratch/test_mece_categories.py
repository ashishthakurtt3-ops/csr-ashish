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

total_count = base_qs.count()
print(f"Total eligible jobs: {total_count}")

# MECE Categories strictly based on source category (department)
# 1. Uncategorized: source provided NO department
uncat_q = Q(department__isnull=True) | Q(department='') | Q(department__iexact='uncategorized') | Q(department__iexact='unspecified')
uncat_qs = base_qs.filter(uncat_q)
has_dept_qs = base_qs.exclude(uncat_q)

# 2. Standard categories mapped from department
# Tech: Technology, Paytm Labs, Analytics, Product, Design
tech_dept_q = Q(department__icontains='Technology') | Q(department__icontains='Paytm Labs') | Q(department__icontains='Analytics') | Q(department__icontains='Tech') | Q(department__icontains='Software') | Q(department__icontains='IT') | Q(department__icontains='Product') | Q(department__icontains='Design')
# Sales & Marketing
sales_dept_q = Q(department__icontains='Sales') | Q(department__icontains='Marketing') | Q(department__icontains='Commercial')
# Finance
finance_dept_q = Q(department__icontains='Finance') | Q(department__icontains='Accounts') | Q(department__icontains='Treasury')
# HR
hr_dept_q = Q(department__icontains='HR') | Q(department__icontains='Human Resources') | Q(department__icontains='People') | Q(department__icontains='Talent')
# Operations & Supply Chain
ops_dept_q = Q(department__icontains='Operations') | Q(department__icontains='Support') | Q(department__icontains='Purchase') | Q(department__icontains='Supply') | Q(department__icontains='Logistics')
# Legal & Compliance
legal_dept_q = Q(department__icontains='Legal') | Q(department__icontains='Compliance') | Q(department__icontains='Regulatory')
# CSR & Sustainability
csr_dept_q = Q(department__icontains='CSR') | Q(department__icontains='Sustainability') | Q(department__icontains='ESG')
# Healthcare
health_dept_q = Q(department__icontains='Health') | Q(department__icontains='Pharma') | Q(department__icontains='Medical')
# Engineering (if in dept)
eng_dept_q = Q(department__icontains='Engineering') | Q(department__icontains='Manufacturing') | Q(department__icontains='Plant')

all_std_q = (
    tech_dept_q | sales_dept_q | finance_dept_q | hr_dept_q |
    ops_dept_q | legal_dept_q | csr_dept_q | health_dept_q | eng_dept_q
)

others_qs = has_dept_qs.exclude(all_std_q)

# Check counts
print(f"Uncategorized: {uncat_qs.count()}")
print(f"Tech: {has_dept_qs.filter(tech_dept_q).count()}")
print(f"Sales: {has_dept_qs.filter(sales_dept_q).count()}")
print(f"Finance: {has_dept_qs.filter(finance_dept_q).count()}")
print(f"HR: {has_dept_qs.filter(hr_dept_q).count()}")
print(f"Operations: {has_dept_qs.filter(ops_dept_q).count()}")
print(f"Legal: {has_dept_qs.filter(legal_dept_q).count()}")
print(f"CSR: {has_dept_qs.filter(csr_dept_q).count()}")
print(f"Healthcare: {has_dept_qs.filter(health_dept_q).count()}")
print(f"Engineering: {has_dept_qs.filter(eng_dept_q).count()}")
print(f"Others: {others_qs.count()}")

std_sum = (
    has_dept_qs.filter(tech_dept_q).count() +
    has_dept_qs.filter(sales_dept_q).count() +
    has_dept_qs.filter(finance_dept_q).count() +
    has_dept_qs.filter(hr_dept_q).count() +
    has_dept_qs.filter(ops_dept_q).count() +
    has_dept_qs.filter(legal_dept_q).count() +
    has_dept_qs.filter(csr_dept_q).count() +
    has_dept_qs.filter(health_dept_q).count() +
    has_dept_qs.filter(eng_dept_q).count()
)

print(f"Total Standard: {std_sum}")
print(f"Total Others: {others_qs.count()}")
print(f"Total Uncategorized: {uncat_qs.count()}")
print(f"Sum (Standard + Others + Uncategorized): {std_sum + others_qs.count() + uncat_qs.count()}")
print(f"Difference from 610: {std_sum + others_qs.count() + uncat_qs.count() - total_count}")
