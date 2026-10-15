"""Comprehensive audit of all job extraction states."""
import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Job, Company
from django.db.models import Count, Q

print('=' * 80)
print('COMPREHENSIVE JOB EXTRACTION AUDIT')
print('=' * 80)

# 1. Full matrix: status × detail_fetch_status
print('\n=== STATUS × DETAIL_FETCH_STATUS MATRIX ===')
for row in Job.objects.values('status', 'detail_fetch_status').annotate(c=Count('pk')).order_by('status', 'detail_fetch_status'):
    print(f"  {row['status']:12} | {row['detail_fetch_status']:20} | {row['c']}")

# 2. Full matrix: status × verification_status
print('\n=== STATUS × VERIFICATION_STATUS MATRIX ===')
for row in Job.objects.values('status', 'verification_status').annotate(c=Count('pk')).order_by('status', 'verification_status'):
    print(f"  {row['status']:12} | {row['verification_status']:20} | {row['c']}")

# 3. Active EXTRACTION_FAILED detail
print('\n=== ACTIVE EXTRACTION_FAILED JOBS (all 8) ===')
for j in Job.objects.filter(status='ACTIVE', detail_fetch_status='EXTRACTION_FAILED').select_related('company'):
    print(f"  {j.job_id} | {j.job_title[:50]:50} | {j.company.company_name[:30]:30} | ATS: {j.ats_platform or 'N/A'}")
    print(f"    source: {j.source_url}")
    print(f"    app_url: {j.application_url}")
    print(f"    ext_method: {j.extraction_method}")
    has_desc = bool(j.job_description and len(str(j.job_description).strip()) > 50)
    print(f"    has_desc: {has_desc} | dept: {j.department or 'None'} | loc: {j.location or 'None'}")
    print()

# 4. Active NOT_FETCHED breakdown by company/ATS
print('\n=== ACTIVE NOT_FETCHED BY COMPANY (Top 20) ===')
nf = Job.objects.filter(status='ACTIVE', detail_fetch_status='NOT_FETCHED')
for row in nf.values('company__company_id', 'company__company_name', 'ats_platform').annotate(c=Count('pk')).order_by('-c')[:20]:
    print(f"  {row['company__company_id']:20} | {row['company__company_name'][:30]:30} | ATS: {row['ats_platform'] or 'N/A':20} | {row['c']}")

# 5. Active FETCHED field coverage
print('\n=== ACTIVE FETCHED FIELD COVERAGE ===')
fetched = Job.objects.filter(status='ACTIVE', detail_fetch_status='FETCHED')
fc = fetched.count()
print(f"Total FETCHED active: {fc}")
has_desc = fetched.exclude(Q(job_description__isnull=True) | Q(job_description='')).count()
has_resp = fetched.exclude(Q(responsibilities__isnull=True) | Q(responsibilities='')).count()
has_quals = fetched.exclude(Q(qualifications__isnull=True) | Q(qualifications='')).count()
has_dept = fetched.exclude(Q(department__isnull=True) | Q(department='')).count()
has_exp = fetched.exclude(Q(experience__isnull=True) | Q(experience='')).count()
has_edu = fetched.exclude(Q(education__isnull=True) | Q(education='')).count()
has_skills = fetched.exclude(Q(skills__isnull=True) | Q(skills='')).count()
has_loc = fetched.exclude(Q(location__isnull=True) | Q(location='')).count()
print(f"  With description: {has_desc}")
print(f"  With responsibilities: {has_resp}")
print(f"  With qualifications: {has_quals}")
print(f"  With department: {has_dept}")
print(f"  With experience: {has_exp}")
print(f"  With education: {has_edu}")
print(f"  With skills: {has_skills}")
print(f"  With location: {has_loc}")

# 6. ALL EXTRACTION_FAILED by company (for full audit of 2176)
print('\n=== ALL EXTRACTION_FAILED (2176) BY COMPANY (Top 30) ===')
ef = Job.objects.filter(detail_fetch_status='EXTRACTION_FAILED')
for row in ef.values('company__company_id', 'company__company_name', 'status').annotate(c=Count('pk')).order_by('-c')[:30]:
    print(f"  {row['company__company_id']:20} | {row['company__company_name'][:30]:30} | {row['status']:10} | {row['c']}")

# 7. ALL EXTRACTION_FAILED by ATS
print('\n=== ALL EXTRACTION_FAILED BY ATS ===')
for row in ef.values('ats_platform').annotate(c=Count('pk')).order_by('-c'):
    print(f"  {row['ats_platform'] or 'None/Unknown':30} | {row['c']}")

# 8. Sample of INACTIVE EXTRACTION_FAILED
print('\n=== SAMPLE INACTIVE EXTRACTION_FAILED (first 15) ===')
for j in Job.objects.filter(status='INACTIVE', detail_fetch_status='EXTRACTION_FAILED').select_related('company')[:15]:
    print(f"  {j.job_id} | {j.job_title[:40]:40} | {j.company.company_name[:25]:25} | VS: {j.verification_status}")

# 9. What exactly is the original 2144 referring to?
print('\n=== COUNTS BY DETAIL_FETCH_STATUS × STATUS ===')
total_ef_active = Job.objects.filter(detail_fetch_status='EXTRACTION_FAILED', status='ACTIVE').count()
total_ef_inactive = Job.objects.filter(detail_fetch_status='EXTRACTION_FAILED', status='INACTIVE').count()
total_ef = Job.objects.filter(detail_fetch_status='EXTRACTION_FAILED').count()
print(f"  EXTRACTION_FAILED & ACTIVE: {total_ef_active}")
print(f"  EXTRACTION_FAILED & INACTIVE: {total_ef_inactive}")
print(f"  EXTRACTION_FAILED total: {total_ef}")
