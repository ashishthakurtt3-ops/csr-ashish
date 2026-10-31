import os
import sys
import django
from collections import Counter

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from modules.admin_panel.models import Job, Company, CSRProject, CSROpportunity
from modules.admin_panel.verification import public_jobs, is_defective_job_record
from modules.admin_panel.snapshot_service import get_current_stats_snapshot, get_current_job_summary_snapshot

def analyze_7a_reconcile():
    print("=" * 60)
    print("STEP 7a: INDEPENDENT RECONCILE (RAW SQL vs SNAPSHOT)")
    print("=" * 60)
    
    # Snapshot value
    stats, is_stale, run_id, as_of = get_current_stats_snapshot()
    snap_jobs = stats.get('jobs_tracked')
    
    # ORM public_jobs count
    orm_count = public_jobs(Job.objects.all()).count()
    
    # Independent raw SQL count
    # Let's count jobs matching active, non-defective, non-REQ, verified status
    raw_sql = """
        SELECT COUNT(*)
        FROM admin_panel_job
        WHERE status = 'ACTIVE'
          AND is_defective = 0
          AND job_id NOT LIKE 'REQ%%'
          AND verification_status NOT IN ('REJECTED', 'QUARANTINED', 'LEGACY_UNVERIFIED', 'NEEDS_REVIEW')
          AND status NOT IN ('NEEDS_REVIEW', 'INACTIVE', 'REMOVED', 'EXPIRED')
    """
    with connection.cursor() as cursor:
        cursor.execute(raw_sql)
        raw_count = cursor.fetchone()[0]
        
    print(f"Snapshot jobs_tracked : {snap_jobs}")
    print(f"ORM public_jobs()     : {orm_count}")
    print(f"Raw SQL count         : {raw_count}")
    print(f"Difference (Raw - Snap): {raw_count - snap_jobs}")
    return snap_jobs, orm_count, raw_count

def analyze_7b_hidden_jobs():
    print("\n" + "=" * 60)
    print("STEP 7b: HIDDEN JOBS REVIEW")
    print("=" * 60)
    
    total_jobs = Job.objects.count()
    pub_jobs = public_jobs(Job.objects.all())
    pub_count = pub_jobs.count()
    pub_pks = set(pub_jobs.values_list('job_row_id', flat=True))
    
    hidden_qs = Job.objects.exclude(job_row_id__in=pub_pks)
    hidden_count = hidden_qs.count()
    
    print(f"Total jobs in DB: {total_jobs}")
    print(f"Public jobs shown: {pub_count}")
    print(f"Hidden jobs: {hidden_count}")
    
    # Breakdown by reasons:
    # 1. status != 'ACTIVE'
    # 2. is_defective == True
    # 3. job_id.startswith('REQ')
    # 4. verification_status in ('LEGACY_UNVERIFIED', 'REJECTED', 'QUARANTINED', 'NEEDS_REVIEW')
    
    reasons = {
        'inactive_status': [],
        'defective_flag': [],
        'req_prefix': [],
        'unverified_status': [],
        'multiple_reasons': []
    }
    
    # Let's categorize each hidden job into primary reason
    for job in hidden_qs:
        flags = []
        if job.status != 'ACTIVE':
            flags.append(f"status={job.status}")
        if job.is_defective:
            flags.append("is_defective=True")
        if job.job_id and job.job_id.startswith('REQ'):
            flags.append("job_id=REQ*")
        if job.verification_status in ['LEGACY_UNVERIFIED', 'REJECTED', 'QUARANTINED', 'NEEDS_REVIEW']:
            flags.append(f"verif={job.verification_status}")
            
        if len(flags) == 0:
            flags.append("other_filter")
        
        # Categorize
        if job.is_defective and not (job.job_id and job.job_id.startswith('REQ')) and job.status == 'ACTIVE' and job.verification_status not in ['LEGACY_UNVERIFIED', 'REJECTED', 'QUARANTINED', 'NEEDS_REVIEW']:
            reasons['defective_flag'].append(job)
        elif job.job_id and job.job_id.startswith('REQ') and not job.is_defective:
            reasons['req_prefix'].append(job)
        elif job.status != 'ACTIVE' and not job.is_defective and not (job.job_id and job.job_id.startswith('REQ')):
            reasons['inactive_status'].append(job)
        elif job.verification_status in ['LEGACY_UNVERIFIED', 'REJECTED', 'QUARANTINED', 'NEEDS_REVIEW'] and not job.is_defective and not (job.job_id and job.job_id.startswith('REQ')) and job.status == 'ACTIVE':
            reasons['unverified_status'].append(job)
        else:
            reasons['multiple_reasons'].append(job)
            
    print("\nCategorized Breakdown:")
    for cat, jobs in reasons.items():
        print(f"\n--- {cat}: Count = {len(jobs)} ---")
        for j in jobs[:10]:
            print(f"  [{j.job_id}] status={j.status}, verif={j.verification_status}, defect={j.is_defective} | '{j.job_title}'")

    # Also exact reason overlap analysis
    print("\nOverlap counts:")
    with connection.cursor() as c:
        c.execute("SELECT is_defective, COUNT(*) FROM admin_panel_job GROUP BY is_defective")
        print("is_defective:", c.fetchall())
        c.execute("SELECT status, COUNT(*) FROM admin_panel_job GROUP BY status")
        print("status:", c.fetchall())
        c.execute("SELECT verification_status, COUNT(*) FROM admin_panel_job GROUP BY verification_status")
        print("verification_status:", c.fetchall())
        c.execute("SELECT count(*) FROM admin_panel_job WHERE job_id LIKE 'REQ%'")
        print("job_id LIKE 'REQ%':", c.fetchall())

def analyze_7c_suspicious_zeros():
    print("\n" + "=" * 60)
    print("STEP 7c: SUSPICIOUS ZEROS INVESTIGATION")
    print("=" * 60)
    
    with connection.cursor() as c:
        # 1. Verified Companies = 0
        print("\n1. Companies Verification Status & Link Quality:")
        c.execute("SELECT verification_status, COUNT(*) FROM admin_panel_company GROUP BY verification_status")
        print("  Company.verification_status:", c.fetchall())
        c.execute("SELECT link_quality, COUNT(*) FROM admin_panel_company GROUP BY link_quality")
        print("  Company.link_quality:", c.fetchall())
        c.execute("SELECT website_url_status, COUNT(*) FROM admin_panel_company GROUP BY website_url_status")
        print("  Company.website_url_status:", c.fetchall())
        
        # 2. Active Opportunities = 0 (1,160 rows exist)
        print("\n2. CSR Opportunities:")
        c.execute("SELECT status, verification_status, COUNT(*) FROM admin_panel_csropportunity GROUP BY status, verification_status")
        print("  CSROpportunity (status, verification_status):", c.fetchall())
        c.execute("SELECT COUNT(*) FROM admin_panel_csropportunity")
        print("  Total CSROpportunity rows:", c.fetchall())
        
        # 3. Remote = 0, Hybrid = 0, ~113 no work mode
        print("\n3. Work Modes across Jobs:")
        c.execute("SELECT work_mode, COUNT(*) FROM admin_panel_job GROUP BY work_mode")
        print("  All jobs work_mode:", c.fetchall())
        
        # In public jobs
        pub_pks = list(public_jobs(Job.objects.all()).values_list('job_row_id', flat=True))
        c.execute(f"SELECT work_mode, COUNT(*) FROM admin_panel_job WHERE job_row_id IN ({','.join(map(str, pub_pks))}) GROUP BY work_mode")
        print("  Public jobs work_mode:", c.fetchall())
        
        # Check job titles or descriptions for remote/hybrid mentions
        c.execute("SELECT COUNT(*) FROM admin_panel_job WHERE LOWER(job_title) LIKE '%remote%' OR LOWER(job_title) LIKE '%hybrid%' OR LOWER(job_title) LIKE '%work from home%'")
        print("  Jobs with remote/hybrid in title:", c.fetchall())
        c.execute("SELECT job_row_id, job_title, work_mode FROM admin_panel_job WHERE LOWER(job_title) LIKE '%remote%' OR LOWER(job_title) LIKE '%hybrid%' LIMIT 10")
        print("  Sample remote/hybrid in title:", c.fetchall())
        
        # Check jobs with empty/null work_mode
        c.execute(f"SELECT COUNT(*) FROM admin_panel_job WHERE job_row_id IN ({','.join(map(str, pub_pks))}) AND (work_mode IS NULL OR work_mode = '' OR work_mode = 'UNKNOWN')")
        print("  Public jobs with empty/null/UNKNOWN work mode:", c.fetchall())
        c.execute(f"SELECT job_row_id, job_title, location, work_mode FROM admin_panel_job WHERE job_row_id IN ({','.join(map(str, pub_pks))}) AND (work_mode IS NULL OR work_mode = '' OR work_mode = 'UNKNOWN') LIMIT 10")
        print("  Sample public jobs with no work mode:", c.fetchall())

if __name__ == '__main__':
    analyze_7a_reconcile()
    analyze_7b_hidden_jobs()
    analyze_7c_suspicious_zeros()
