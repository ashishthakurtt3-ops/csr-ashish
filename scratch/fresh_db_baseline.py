import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection
from django.db.models import Count
from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, AIProviderConfig, AISystemSettings, AIConfigurationAuditLog

print("=== LIVE MYSQL DATABASE INVENTORY BASELINE ===")
print(f"Company ({Company._meta.db_table}): {Company.objects.count()} total")
print(f"Job ({Job._meta.db_table}): {Job.objects.count()} total")

job_statuses = Job.objects.values('status').annotate(cnt=Count('job_id')).order_by('-cnt')
print("  Job status distribution:")
for js in job_statuses:
    print(f"    - {js['status']}: {js['cnt']}")

job_verif = Job.objects.values('verification_status').annotate(cnt=Count('job_id')).order_by('-cnt')
print("  Job verification_status distribution:")
for jv in job_verif:
    print(f"    - {jv['verification_status']}: {jv['cnt']}")

print(f"\nCSRProject ({CSRProject._meta.db_table}): {CSRProject.objects.count()} total")
csr_statuses = CSRProject.objects.values('status').annotate(cnt=Count('csr_id')).order_by('-cnt')
print("  CSR status distribution:")
for cs in csr_statuses:
    print(f"    - {cs['status']}: {cs['cnt']}")

csr_verif = CSRProject.objects.values('verification_status').annotate(cnt=Count('csr_id')).order_by('-cnt')
print("  CSR verification_status distribution:")
for cv in csr_verif:
    print(f"    - {cv['verification_status']}: {cv['cnt']}")

print(f"\nCSROpportunity ({CSROpportunity._meta.db_table}): {CSROpportunity.objects.count()} total")
opp_statuses = CSROpportunity.objects.values('status').annotate(cnt=Count('opp_id')).order_by('-cnt')
print("  CSR Opportunity status distribution:")
for os_stat in opp_statuses:
    print(f"    - {os_stat['status']}: {os_stat['cnt']}")

print(f"\nAIProviderConfig ({AIProviderConfig._meta.db_table}): {AIProviderConfig.objects.count()} total")
print(f"AIConfigurationAuditLog ({AIConfigurationAuditLog._meta.db_table}): {AIConfigurationAuditLog.objects.count()} total")

with connection.cursor() as cursor:
    cursor.execute("SHOW TABLES")
    tables = [r[0] for r in cursor.fetchall()]

print(f"\nAll Database Tables ({len(tables)}):")
for t in sorted(tables):
    print(f"  - {t}")
