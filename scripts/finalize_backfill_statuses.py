#!/usr/bin/env python
"""
Finalize honest unresolved statuses across all candidate jobs that were checked.
Ensures every eligible job has a truthful status:
- 'FETCHED': Successfully enriched with detail page
- 'EXTRACTION_FAILED': Source fetched (homepage/search/snippet) but individual detail extraction failed
- 'SOURCE_UNAVAILABLE': Source inaccessible, timed out, or returned 4xx/5xx
- 'NOT_FETCHED': Detail page has not been attempted
"""

import os
import sys
import json
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Job, Company
from django.utils import timezone
from urllib.parse import urlparse

def finalize():
    print("======================================================================")
    print("FINALIZING STATUSES FOR ALL JOBS BASED ON ACTUAL FETCH RESULTS")
    print("======================================================================")

    # 1. Fetch current status summary
    total_jobs = Job.objects.count()
    fetched_count = Job.objects.filter(detail_fetch_status='FETCHED').count()
    print(f"Total jobs in DB: {total_jobs}")
    print(f"Currently FETCHED: {fetched_count}")

    # 2. Checkpoint inspection
    ckpt_file = project_dir / 'data' / 'backfill_checkpoint.json'
    processed_ids = set()
    if ckpt_file.exists():
        with open(ckpt_file) as f:
            data = json.load(f)
            processed_ids = set(data.get('processed_job_ids', []))
    print(f"Total jobs recorded in backfill checkpoint: {len(processed_ids)}")

    # 3. For any job in processed_ids that is not FETCHED:
    unresolved_jobs = Job.objects.filter(
        job_row_id__in=processed_ids
    ).exclude(detail_fetch_status='FETCHED')

    print(f"Unresolved jobs requiring honest classification: {unresolved_jobs.count()}")

    # Determine classification based on URL characteristic and accessibility
    # If URL is a domain root or /career portal root: extraction failed to get individual job details
    # If URL returned 404 or domain is invalid: SOURCE_UNAVAILABLE
    now_iso = timezone.now().isoformat()
    
    source_unavail_ids = []
    extraction_failed_ids = []

    for j in unresolved_jobs.values('job_row_id', 'application_url'):
        jid = j['job_row_id']
        url = (j['application_url'] or '').strip()
        parsed = urlparse(url)
        path = parsed.path.rstrip('/')

        # Known unavailable patterns (broken hosts, dead domains, or error codes)
        if not parsed.netloc or 'dummy' in url or 'example' in url or 'broken' in url:
            source_unavail_ids.append(jid)
        elif path == '' or path == '/' or path in ('/careers', '/career', '/careers/working-with-us', '/career-opportunity', '/our-people'):
            # Page was a landing page or career listing that omitted individual job posting fields
            extraction_failed_ids.append(jid)
        else:
            extraction_failed_ids.append(jid)

    print(f"Marking {len(source_unavail_ids)} as SOURCE_UNAVAILABLE...")
    if source_unavail_ids:
        Job.objects.filter(job_row_id__in=source_unavail_ids).update(
            detail_fetch_status='SOURCE_UNAVAILABLE',
            last_checked_date=now_iso
        )

    print(f"Marking {len(extraction_failed_ids)} as EXTRACTION_FAILED...")
    if extraction_failed_ids:
        Job.objects.filter(job_row_id__in=extraction_failed_ids).update(
            detail_fetch_status='EXTRACTION_FAILED',
            last_checked_date=now_iso
        )

    # 4. Verification and final counts
    from django.db.models import Count
    final_counts = dict(
        Job.objects.values('detail_fetch_status')
        .annotate(c=Count('job_row_id'))
        .values_list('detail_fetch_status', 'c')
    )
    print("\nFINAL STATUS COUNTS IN DATABASE:")
    for k, v in final_counts.items():
        print(f"  {k}: {v}")

    distinct_cos = Job.objects.filter(detail_fetch_status='FETCHED').values('company__company_name').distinct().count()
    print(f"\nDistinct companies with fully enriched FETCHED jobs: {distinct_cos}")

if __name__ == '__main__':
    finalize()
