#!/usr/bin/env python
"""
Targeted enrichment for the remaining 46 active candidate jobs with direct detail URLs.
"""

import os
import sys
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Job
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor
from modules.crawler_engine.verification_service import VerificationService
from django.utils import timezone

def run():
    qs = Job.objects.filter(detail_fetch_status='NOT_FETCHED', status='ACTIVE')
    print(f"Targeting {qs.count()} remaining active jobs...")

    enriched = 0
    failed = 0

    for job in qs:
        url = job.application_url
        print(f"Fetching Job {job.job_row_id}: {job.company.company_name[:20]} - {job.job_title[:25]}...")
        res = UniversalJobDetailExtractor.extract_from_url(url)
        status = res.get('detail_fetch_status')

        if status == 'FETCHED':
            updated_fields = []
            if res.get('job_description'):
                job.job_description = res['job_description']
                updated_fields.append('job_description')
            if res.get('responsibilities'):
                job.responsibilities = res['responsibilities']
                updated_fields.append('responsibilities')
            if res.get('qualifications'):
                job.qualifications = res['qualifications']
                updated_fields.append('qualifications')
            if res.get('education'):
                job.education = res['education']
                updated_fields.append('education')
            if res.get('experience'):
                job.experience = res['experience']
                updated_fields.append('experience')
            if res.get('technical_skills'):
                job.technical_skills = res['technical_skills']
                updated_fields.append('technical_skills')
            if res.get('behavioural_skills'):
                job.behavioural_skills = res['behavioural_skills']
                updated_fields.append('behavioural_skills')
            if res.get('structured_details'):
                job.structured_details = res['structured_details']
                updated_fields.append('structured_details')
            if res.get('role_purpose'):
                job.role_purpose = res['role_purpose']
                updated_fields.append('role_purpose')
            if res.get('function'):
                job.function = res['function']
                updated_fields.append('function')
            if res.get('department'):
                job.department = res['department']
                updated_fields.append('department')
            if res.get('posted_date'):
                job.posted_date = res['posted_date']
                updated_fields.append('posted_date')

            job.detail_fetched = True
            job.detail_fetch_status = 'FETCHED'
            now_iso = timezone.now().isoformat()
            job.detail_fetched_at = now_iso
            job.last_checked_date = now_iso
            if not job.retrieved_at:
                job.retrieved_at = timezone.now()
            if not job.evidence_text:
                job.evidence_text = f"{job.job_title} at {job.company.company_name} {job.location or ''} {job.job_description or ''}"
            job.save()

            if job.verification_status != 'PUBLISHED':
                VerificationService.publish_record(job, actor="DetailBackfillService")

            enriched += 1
            print(f"  -> ENRICHED ({len(updated_fields)} fields: {', '.join(updated_fields[:3])})")
        else:
            Job.objects.filter(job_row_id=job.job_row_id).update(
                detail_fetch_status='EXTRACTION_FAILED',
                last_checked_date=timezone.now().isoformat()
            )
            failed += 1
            print(f"  -> {status or 'EXTRACTION_FAILED'}")

    print(f"\nCompleted: {enriched} enriched, {failed} unresolved/failed.")

if __name__ == '__main__':
    run()
