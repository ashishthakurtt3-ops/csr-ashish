import os
import sys
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection
from modules.admin_panel.verification import public_jobs
from modules.admin_panel.models import Job

with connection.cursor() as c:
    # 1. Total jobs
    c.execute("SELECT COUNT(*) FROM admin_panel_job")
    total = c.fetchone()[0]

    # 2. Raw SQL count without public_jobs() or is_defective
    # Ground truth: status is ACTIVE, verification_status in PUBLISHED, SOURCE_CONFIRMED,
    # and title does not match defect navigation patterns, and job_id not REQ%
    c.execute("""
        SELECT COUNT(*) FROM admin_panel_job
        WHERE status = 'ACTIVE'
          AND verification_status IN ('PUBLISHED', 'SOURCE_CONFIRMED')
          AND job_id NOT LIKE 'REQ%'
    """)
    raw_active_verified = c.fetchone()[0]

    # Let's see what the 21 defective jobs among (status=ACTIVE, verif in (PUBLISHED, SOURCE_CONFIRMED), no REQ) are:
    c.execute("""
        SELECT job_row_id, job_title FROM admin_panel_job
        WHERE status = 'ACTIVE'
          AND verification_status IN ('PUBLISHED', 'SOURCE_CONFIRMED')
          AND job_id NOT LIKE 'REQ%'
          AND is_defective = 1
    """)
    defective_among_active = c.fetchall()
    print(f"Total jobs: {total}")
    print(f"Raw active + verified: {raw_active_verified}")
    print(f"Defective among active verified ({len(defective_among_active)}):")
    for r in defective_among_active:
        print(f"  ID {r[0]}: {r[1]}")

    # Raw SQL without is_defective that directly excludes defect tokens:
    # Notice all 21 are '%Calculator%'
    c.execute("""
        SELECT COUNT(*) FROM admin_panel_job
        WHERE status = 'ACTIVE'
          AND verification_status IN ('PUBLISHED', 'SOURCE_CONFIRMED')
          AND job_id NOT LIKE 'REQ%'
          AND job_title NOT LIKE '%Calculator%'
          AND job_title NOT LIKE '%How to apply%'
          AND job_title NOT LIKE '%Discover more%'
          AND job_title NOT LIKE '%Upload Resume%'
          AND job_title NOT LIKE '%Submit Resume%'
          AND job_title NOT LIKE '%Next >>%'
          AND job_title NOT LIKE '%Previous <<%'
          AND job_title NOT LIKE '%Click here%'
          AND job_title NOT LIKE '%Apply now%'
          AND job_title NOT LIKE '%View details%'
          AND job_title NOT LIKE '%Read more%'
          AND job_title NOT LIKE '%Learn more%'
          AND job_title NOT LIKE '%FAQs%'
    """)
    raw_cleaned = c.fetchone()[0]
    print(f"Raw independent SQL (no is_defective, purely SQL filtered): {raw_cleaned}")
    print(f"public_jobs() count: {public_jobs(Job.objects.all()).count()}")
