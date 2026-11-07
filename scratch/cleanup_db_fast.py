import os, sys, django
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from modules.admin_panel.models import Company, Job, CSRProject
from modules.crawler_engine.discovery_helpers import (
    is_valid_job_title, is_valid_csr_project, is_static_asset_url,
    derive_deep_job_url, resolve_authentic_csr_url,
    ENTERPRISE_PORTAL_REGISTRY, ENTERPRISE_CSR_REGISTRY
)

print('=== 1. AUDITING & REPAIRING COMPANY CAREERS & CSR URLs ===')
repaired_companies = 0
with transaction.atomic():
    for comp in Company.objects.all():
        updated = False
        c_lower = comp.company_name.lower()
        
        # Check if careers_url is an asset or invalid
        if not comp.careers_url or is_static_asset_url(comp.careers_url):
            for k, portal in ENTERPRISE_PORTAL_REGISTRY.items():
                if k in c_lower:
                    comp.careers_url = portal
                    updated = True
                    break
        
        # Check if csr_portal_url is an asset or invalid
        if not comp.csr_portal_url or is_static_asset_url(comp.csr_portal_url):
            for k, portal in ENTERPRISE_CSR_REGISTRY.items():
                if k in c_lower:
                    comp.csr_portal_url = portal
                    updated = True
                    break
                    
        if updated:
            comp.save(update_fields=['careers_url', 'csr_portal_url'])
            repaired_companies += 1

print(f'Repaired base URLs for {repaired_companies} companies.')

print('\n=== 2. PURGING JUNK JOBS FROM DATABASE ===')
initial_jobs = Job.objects.count()
junk_job_ids = []
for j in Job.objects.only('job_row_id', 'job_title'):
    if not is_valid_job_title(j.job_title):
        junk_job_ids.append(j.job_row_id)

print(f'Found {len(junk_job_ids)} junk non-role records out of {initial_jobs} total.')
if junk_job_ids:
    deleted_count, _ = Job.objects.filter(job_row_id__in=junk_job_ids).delete()
    print(f'Deleted {deleted_count} junk job records.')
print(f'Remaining legitimate jobs: {Job.objects.count()}')

print('\n=== 3. PURGING JUNK CSR PROJECTS FROM DATABASE ===')
initial_csr = CSRProject.objects.count()
junk_csr_ids = []
for c in CSRProject.objects.only('csr_id', 'project_name'):
    if not is_valid_csr_project(c.project_name):
        junk_csr_ids.append(c.csr_id)

print(f'Found {len(junk_csr_ids)} junk CSR records out of {initial_csr} total.')
if junk_csr_ids:
    deleted_csr, _ = CSRProject.objects.filter(csr_id__in=junk_csr_ids).delete()
    print(f'Deleted {deleted_csr} junk CSR records.')
print(f'Remaining legitimate CSR projects: {CSRProject.objects.count()}')

print('\n=== 4. REPAIRING ALL REMAINING JOB APPLICATION URLs ===')
jobs_to_update = []
for j in Job.objects.select_related('company').all():
    old_url = j.application_url
    new_url = derive_deep_job_url(
        careers_url=j.company.careers_url,
        comp_name=j.company.company_name,
        job_title=j.job_title,
        existing_url=old_url
    )
    if new_url != old_url or j.canonical_url != new_url:
        j.application_url = new_url
        j.canonical_url = new_url
        j.source_url = j.company.careers_url or new_url
        jobs_to_update.append(j)

if jobs_to_update:
    Job.objects.bulk_update(jobs_to_update, ['application_url', 'canonical_url', 'source_url'], batch_size=500)
print(f'Repaired application URLs for {len(jobs_to_update)} jobs.')

print('\n=== 5. REPAIRING ALL REMAINING CSR PROJECT URLs ===')
csr_to_update = []
for c in CSRProject.objects.select_related('company').all():
    old_url = c.source_url
    new_url = resolve_authentic_csr_url(
        csr_url=c.company.csr_portal_url or old_url,
        comp_name=c.company.company_name,
        project_name=c.project_name
    )
    if new_url != old_url or c.canonical_url != new_url:
        c.source_url = new_url
        c.canonical_url = new_url
        csr_to_update.append(c)

if csr_to_update:
    CSRProject.objects.bulk_update(csr_to_update, ['source_url', 'canonical_url'], batch_size=500)
print(f'Repaired URLs for {len(csr_to_update)} CSR projects.')
print('ALL DATABASE INTEGRITY REPAIRS COMPLETED SUCCESSFULLY!')

