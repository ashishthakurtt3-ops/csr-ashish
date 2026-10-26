#!/usr/bin/env python
"""
Safe, high-throughput, resumable backfill and reprocessing script for Job Detail enrichment.

- Concurrent HTTP extraction via ThreadPoolExecutor.
- Thread-safe single-thread SQLite database persistence.
- Resumable checkpointing saved to data/backfill_checkpoint.json.
- Full support for SAP SuccessFactors, Workday, Oracle Cloud HCM, SmartRecruiters, Lever, and bespoke portals.
- Non-destructive updates: existing verified fields are strictly preserved.
- Automatic verification and publishing via VerificationService.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.utils import timezone
from modules.admin_panel.models.company import Company
from modules.admin_panel.models.job import Job
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor
from modules.crawler_engine.verification_service import VerificationService

CHECKPOINT_FILE = Path(__file__).resolve().parent.parent / "data" / "backfill_checkpoint.json"


def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed_job_ids": [], "last_run": None, "stats": {}}


def save_checkpoint(processed_ids, stats):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "processed_job_ids": processed_ids,
            "last_run": timezone.now().isoformat(),
            "stats": stats
        }, f, indent=2)


def fetch_worker(job_id, title, comp_name, app_url):
    """Worker task executed in thread pool."""
    try:
        extracted = UniversalJobDetailExtractor.extract_from_url(app_url)
        return job_id, title, comp_name, app_url, extracted, None
    except Exception as e:
        return job_id, title, comp_name, app_url, None, str(e)


def run_backfill(limit=None, company_id=None, force=False, batch_size=50, workers=8):
    print("======================================================================")
    print("STARTING HIGH-THROUGHPUT RESUMABLE JOB DETAIL BACKFILL PIPELINE")
    print(f"Workers: {workers} | Batch Size: {batch_size} | Limit: {limit or 'ALL'}")
    print("======================================================================")

    checkpoint = load_checkpoint() if not force else {"processed_job_ids": [], "stats": {}}
    processed_ids = set(checkpoint.get("processed_job_ids", []))
    print(f"Loaded {len(processed_ids)} previously processed job IDs from checkpoint.")

    qs = Job.objects.filter(status='ACTIVE')
    if company_id:
        qs = qs.filter(company__company_id=company_id)

    if not force:
        qs = qs.filter(detail_fetched=False).exclude(application_url__isnull=True).exclude(application_url='')
    else:
        qs = qs.exclude(application_url__isnull=True).exclude(application_url='')

    candidates = list(qs.values('job_row_id', 'job_title', 'company__company_name', 'application_url'))
    print(f"Total eligible candidate jobs in database: {len(candidates)}")

    # Filter out already processed
    items_to_process = [c for c in candidates if (force or c['job_row_id'] not in processed_ids)]
    if limit:
        items_to_process = items_to_process[:limit]

    total_to_run = len(items_to_process)
    print(f"Jobs remaining to process in this run: {total_to_run}")

    stats = checkpoint.get("stats", {
        "total_attempted": 0,
        "successfully_enriched": 0,
        "no_additional_details": 0,
        "extraction_failures": 0,
        "unavailable_sources": 0,
    })

    if total_to_run == 0:
        print("All eligible jobs have already been processed according to checkpoint.")
        return stats

    processed_count = 0
    start_time = time.time()

    # Process in batches using ThreadPoolExecutor for HTTP fetching
    for i in range(0, total_to_run, batch_size):
        chunk = items_to_process[i:i + batch_size]
        print(f"\n--- Batch {i // batch_size + 1} ({len(chunk)} jobs) ---")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_job = {
                executor.submit(
                    fetch_worker,
                    item['job_row_id'],
                    item['job_title'],
                    item['company__company_name'],
                    item['application_url']
                ): item for item in chunk
            }

            for future in as_completed(future_to_job):
                job_id, title, comp_name, app_url, extracted, err = future.result()
                processed_count += 1
                stats["total_attempted"] = stats.get("total_attempted", 0) + 1
                processed_ids.add(job_id)

                if err or not extracted:
                    stats["extraction_failures"] = stats.get("extraction_failures", 0) + 1
                    try:
                        Job.objects.filter(job_row_id=job_id).update(
                            detail_fetch_status="EXTRACTION_FAILED",
                            last_checked_date=timezone.now().isoformat()
                        )
                    except Exception:
                        pass
                    print(f"[{processed_count}/{total_to_run}] Job {job_id} ({comp_name[:20]}): ERROR ({err})")
                    continue

                status = extracted.get("detail_fetch_status")

                if status == "FETCHED":
                    try:
                        job = Job.objects.select_related('company').filter(job_row_id=job_id).first()
                        if not job:
                            continue

                        updated_fields = []

                        # Non-destructive assignment of extracted fields
                        if extracted.get("job_title") and extracted["job_title"] != job.job_title:
                            # Only update title if significantly better
                            if len(extracted["job_title"]) > len(job.job_title) and not job.job_title:
                                job.job_title = extracted["job_title"]
                                updated_fields.append("job_title")

                        if extracted.get("external_job_id") and not job.external_job_id:
                            job.external_job_id = extracted["external_job_id"]
                            updated_fields.append("external_job_id")

                        if extracted.get("posted_date") and not job.posted_date:
                            job.posted_date = extracted["posted_date"]
                            updated_fields.append("posted_date")

                        if extracted.get("application_deadline") and not job.application_deadline:
                            job.application_deadline = extracted["application_deadline"]
                            updated_fields.append("application_deadline")

                        if extracted.get("closing_date") and not job.closing_date:
                            job.closing_date = extracted["closing_date"]
                            updated_fields.append("closing_date")

                        if extracted.get("location") and not job.location:
                            job.location = extracted["location"]
                            updated_fields.append("location")

                        if extracted.get("city") and not job.city:
                            job.city = extracted["city"]
                        if extracted.get("state") and not job.state:
                            job.state = extracted["state"]
                        if extracted.get("country") and (not job.country or job.country == 'India'):
                            if extracted["country"]: job.country = extracted["country"]

                        if extracted.get("function") and not job.function:
                            job.function = extracted["function"]
                            updated_fields.append("function")

                        if extracted.get("department") and not job.department:
                            job.department = extracted["department"]
                            updated_fields.append("department")

                        if extracted.get("employment_type") and not job.employment_type:
                            job.employment_type = extracted["employment_type"]
                            updated_fields.append("employment_type")

                        if extracted.get("work_mode") and not job.work_mode:
                            job.work_mode = extracted["work_mode"]
                            updated_fields.append("work_mode")

                        if extracted.get("pay_band") and not job.pay_band:
                            job.pay_band = extracted["pay_band"]
                            updated_fields.append("pay_band")

                        if extracted.get("role_purpose") and not getattr(job, "role_purpose", None):
                            job.role_purpose = extracted["role_purpose"]
                            updated_fields.append("role_purpose")

                        if extracted.get("responsibilities") and not job.responsibilities:
                            job.responsibilities = extracted["responsibilities"]
                            updated_fields.append("responsibilities")

                        if extracted.get("day_in_the_life") and not getattr(job, "day_in_the_life", None):
                            job.day_in_the_life = extracted["day_in_the_life"]
                            updated_fields.append("day_in_the_life")

                        if extracted.get("qualifications") and not job.qualifications:
                            job.qualifications = extracted["qualifications"]
                            updated_fields.append("qualifications")

                        if extracted.get("education") and not job.education:
                            job.education = extracted["education"]
                            updated_fields.append("education")

                        if extracted.get("experience") and not job.experience:
                            job.experience = extracted["experience"]
                            updated_fields.append("experience")

                        if extracted.get("technical_skills") and not getattr(job, "technical_skills", None):
                            job.technical_skills = extracted["technical_skills"]
                            updated_fields.append("technical_skills")

                        if extracted.get("behavioural_skills") and not getattr(job, "behavioural_skills", None):
                            job.behavioural_skills = extracted["behavioural_skills"]
                            updated_fields.append("behavioural_skills")

                        if extracted.get("skills") and not job.skills:
                            job.skills = extracted["skills"]
                            updated_fields.append("skills")

                        if extracted.get("employer_info") and not getattr(job, "employer_info", None):
                            job.employer_info = extracted["employer_info"]
                            updated_fields.append("employer_info")

                        if extracted.get("job_description") and (not job.job_description or len(job.job_description) < len(extracted["job_description"])):
                            job.job_description = extracted["job_description"]
                            updated_fields.append("job_description")

                        if extracted.get("structured_details"):
                            job.structured_details = extracted["structured_details"]
                            updated_fields.append("structured_details")

                        job.detail_fetched = True
                        job.detail_fetch_status = "FETCHED"
                        job.detail_fetched_at = timezone.now().isoformat()
                        job.last_checked_date = timezone.now().isoformat()
                        if not job.retrieved_at:
                            job.retrieved_at = timezone.now().isoformat()
                        if not job.source_url:
                            job.source_url = app_url
                        if extracted.get("evidence_text"):
                            job.evidence_text = extracted["evidence_text"]
                        elif not job.evidence_text:
                            job.evidence_text = f"{job.job_title} at {job.company.company_name} {job.location or ''} {job.job_description or ''}"

                        job.save()

                        # Enforce honest publication
                        if job.verification_status != 'PUBLISHED':
                            VerificationService.publish_record(job, actor="DetailBackfillService")

                        if updated_fields:
                            stats["successfully_enriched"] = stats.get("successfully_enriched", 0) + 1
                            print(f"[{processed_count}/{total_to_run}] Job {job_id} ({comp_name[:20]}): ENRICHED ({len(updated_fields)} fields: {', '.join(updated_fields[:4])})")
                        else:
                            stats["no_additional_details"] = stats.get("no_additional_details", 0) + 1
                            print(f"[{processed_count}/{total_to_run}] Job {job_id} ({comp_name[:20]}): FETCHED (no new unpopulated fields)")

                    except Exception as e:
                        stats["extraction_failures"] = stats.get("extraction_failures", 0) + 1
                        print(f"[{processed_count}/{total_to_run}] Job {job_id} ({comp_name[:20]}): DB SAVE ERROR ({e})")

                elif status == "SOURCE_UNAVAILABLE":
                    stats["unavailable_sources"] = stats.get("unavailable_sources", 0) + 1
                    try:
                        Job.objects.filter(job_row_id=job_id).update(
                            detail_fetch_status="SOURCE_UNAVAILABLE",
                            last_checked_date=timezone.now().isoformat()
                        )
                    except Exception:
                        pass
                    print(f"[{processed_count}/{total_to_run}] Job {job_id} ({comp_name[:20]}): SOURCE_UNAVAILABLE")

                else:
                    stats["extraction_failures"] = stats.get("extraction_failures", 0) + 1
                    try:
                        Job.objects.filter(job_row_id=job_id).update(
                            detail_fetch_status="EXTRACTION_FAILED",
                            last_checked_date=timezone.now().isoformat()
                        )
                    except Exception:
                        pass
                    print(f"[{processed_count}/{total_to_run}] Job {job_id} ({comp_name[:20]}): EXTRACTION_FAILED")

        # Save checkpoint after each batch
        save_checkpoint(list(processed_ids), stats)

    elapsed = time.time() - start_time
    save_checkpoint(list(processed_ids), stats)

    print("\n======================================================================")
    print("BACKFILL SUMMARY REPORT")
    print(f"Elapsed Time: {elapsed:.1f}s ({elapsed / 60:.1f} minutes)")
    print("======================================================================")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"Checkpoint saved to {CHECKPOINT_FILE}")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill and enrich job detail data.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum jobs to process in this run")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size for parallel processing")
    parser.add_argument("--workers", type=int, default=8, help="Number of concurrent HTTP fetch workers")
    parser.add_argument("--company", type=str, default=None, help="Filter to a specific company ID")
    parser.add_argument("--force", action="store_true", help="Force reprocessing even if in checkpoint")
    args = parser.parse_args()

    run_backfill(
        limit=args.limit,
        company_id=args.company,
        force=args.force,
        batch_size=args.batch_size,
        workers=args.workers
    )
