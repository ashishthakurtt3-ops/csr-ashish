import os
import sys
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.db import connection
from modules.website.views.job_api_views import public_jobs, apply_job_safety_filters
from modules.website.views.company_api_views import _annotate_company_metrics
from modules.website.views.opportunity_api_views import public_records
from modules.admin_panel.models import Job, Company, CSRProject
from modules.admin_panel.models.snapshot import AuditRun

cursor = connection.cursor()

def explain_qs(name, qs):
    sql, params = qs.query.sql_with_params()
    cursor.execute(f"EXPLAIN {sql}", params)
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    print(f"\n=== EXPLAIN: {name} ===")
    for r in rows:
        d = dict(zip(columns, r))
        print(f"Table: {d.get('table')} | Type: {d.get('type')} | Key: {d.get('key')} | Rows: {d.get('rows')} | Extra: {d.get('Extra')}")

# 1. Job List
qs1 = public_jobs(Job.objects.select_related('company'))
qs1 = apply_job_safety_filters(qs1).order_by('-last_checked_date', '-job_row_id')[:12]
explain_qs("Job List Query", qs1)

# 2. CSR Project List
qs2 = public_records(CSRProject.objects.select_related('company')).exclude(
    source_url__isnull=True
).exclude(source_url='').exclude(
    evidence_text__isnull=True
).exclude(evidence_text='').order_by('-confidence', '-csr_id')[:12]
explain_qs("CSR Project List Query", qs2)

# 3. Company List (CompanyMetrics join)
qs3 = Company.objects.all()
qs3 = _annotate_company_metrics(qs3)[:12]
explain_qs("Company List with Metrics Join", qs3)

# 4. Job Category Filter Query
qs4 = public_jobs(Job.objects.filter(department__icontains='tech')).order_by('-job_row_id')[:12]
explain_qs("Job Department Query", qs4)

# 5. CSR Project State Query
qs5 = public_records(CSRProject.objects.filter(state__icontains='Maharashtra')).order_by('-confidence', '-csr_id')[:12]
explain_qs("CSR Project State Filter Query", qs5)
