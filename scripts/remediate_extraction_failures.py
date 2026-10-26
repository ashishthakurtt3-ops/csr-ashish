"""
Comprehensive remediation script for all active jobs needing detail extraction.

Processes:
1. Active EXTRACTION_FAILED jobs (retry extraction)
2. Active NOT_FETCHED jobs (first-time detail fetch)

Uses the existing UniversalJobDetailExtractor pipeline.
Non-destructive: never overwrites valid existing data with empty results.
Resumable via checkpoint.
"""
import os, sys, json, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.utils import timezone
from django.db.models import Q
from modules.admin_panel.models import Job
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor
from modules.crawler_engine.verification_service import VerificationService

CHECKPOINT_FILE = BASE_DIR / "data" / "remediation_checkpoint.json"
RESULTS_FILE = BASE_DIR / "data" / "remediation_results.json"

# Detail-enrichable fields in the Job model
ENRICHABLE_FIELDS = [
    'job_title', 'external_job_id', 'posted_date', 'application_deadline',
    'closing_date', 'location', 'city', 'state', 'country', 'function',
    'business_unit', 'department', 'team', 'pay_band', 'employment_type',
    'work_mode', 'role_purpose', 'responsibilities', 'day_in_the_life',
    'qualifications', 'preferred_qualifications', 'education', 'experience',
    'technical_skills', 'behavioural_skills', 'skills', 'benefits',
    'employer_info', 'job_description', 'structured_details'
]


def load_checkpoint():
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed": {}, "stats": {}}


def save_checkpoint(checkpoint):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    checkpoint["last_saved"] = timezone.now().isoformat()
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, indent=2, default=str)


def fetch_worker(job_id, app_url):
    """Thread-pool worker: fetch and extract from a single URL."""
    try:
        result = UniversalJobDetailExtractor.extract_from_url(app_url)
        return job_id, app_url, result, None
    except Exception as e:
        return job_id, app_url, None, str(e)


def apply_extracted_data(job, extracted):
    """Non-destructively apply extracted data to a Job object.
    Returns list of fields that were actually updated."""
    updated_fields = []
    
    for field in ENRICHABLE_FIELDS:
        new_val = extracted.get(field)
        if new_val is None:
            continue
        if field == 'structured_details' and not new_val:
            continue
            
        old_val = getattr(job, field, None)
        
        # For job_title, only update if current is empty or significantly shorter
        if field == 'job_title':
            if old_val and len(str(old_val).strip()) > 0:
                continue
        
        # For job_description, update if new is longer
        if field == 'job_description':
            if old_val and len(str(old_val)) >= len(str(new_val)):
                continue
        
        # For other fields, only update if currently empty
        if field not in ('job_title', 'job_description', 'structured_details'):
            if old_val and str(old_val).strip():
                continue
        
        setattr(job, field, new_val)
        updated_fields.append(field)
    
    return updated_fields


def run_remediation(workers=6, batch_size=40):
    print("=" * 80)
    print("COMPREHENSIVE JOB DETAIL REMEDIATION PIPELINE")
    print(f"Workers: {workers} | Batch Size: {batch_size}")
    print(f"Started: {timezone.now().isoformat()}")
    print("=" * 80)
    
    checkpoint = load_checkpoint()
    processed = checkpoint.get("processed", {})
    
    # Find all active jobs needing detail work
    candidates = Job.objects.filter(
        status='ACTIVE'
    ).filter(
        Q(detail_fetch_status='EXTRACTION_FAILED') |
        Q(detail_fetch_status='NOT_FETCHED')
    ).exclude(
        application_url__isnull=True
    ).exclude(
        application_url=''
    ).select_related('company').order_by('company__company_id')
    
    # Filter out already-processed (unless they failed last time and we want to retry)
    items = []
    for j in candidates:
        prev = processed.get(str(j.job_row_id))
        if prev and prev.get('outcome') in ('FETCHED', 'SOURCE_UNAVAILABLE'):
            continue  # Already successfully processed or confirmed unavailable
        items.append(j)
    
    total = len(items)
    print(f"\nEligible jobs to process: {total}")
    print(f"  Previously processed (skipping): {len(candidates) - total}")
    
    stats = {
        "total_attempted": 0,
        "successfully_enriched": 0,
        "fetched_no_new_fields": 0,
        "extraction_failed": 0,
        "source_unavailable": 0,
        "errors": 0,
        "fields_updated": {},
    }
    
    if total == 0:
        print("No eligible jobs remaining.")
        return stats
    
    start_time = time.time()
    done_count = 0
    
    for batch_start in range(0, total, batch_size):
        batch = items[batch_start:batch_start + batch_size]
        print(f"\n--- Batch {batch_start // batch_size + 1} ({len(batch)} jobs) ---")
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(fetch_worker, j.job_row_id, j.application_url): j
                for j in batch
            }
            
            for future in as_completed(futures):
                job = futures[future]
                job_row_id, app_url, extracted, err = future.result()
                done_count += 1
                stats["total_attempted"] += 1
                
                comp_name = job.company.company_name[:25]
                
                if err or not extracted:
                    stats["errors"] += 1
                    processed[str(job_row_id)] = {
                        "outcome": "ERROR",
                        "error": err,
                        "timestamp": timezone.now().isoformat()
                    }
                    Job.objects.filter(job_row_id=job_row_id).update(
                        detail_fetch_status="EXTRACTION_FAILED",
                        last_checked_date=timezone.now().isoformat()
                    )
                    print(f"[{done_count}/{total}] {job.job_id} ({comp_name}): ERROR - {err}")
                    continue
                
                status = extracted.get("detail_fetch_status", "EXTRACTION_FAILED")
                
                if status == "FETCHED":
                    # Reload fresh from DB to avoid stale data
                    fresh_job = Job.objects.select_related('company').get(job_row_id=job_row_id)
                    updated_fields = apply_extracted_data(fresh_job, extracted)
                    
                    fresh_job.detail_fetched = True
                    fresh_job.detail_fetch_status = "FETCHED"
                    fresh_job.detail_fetched_at = timezone.now().isoformat()
                    fresh_job.last_checked_date = timezone.now().isoformat()
                    
                    if extracted.get("evidence_text"):
                        fresh_job.evidence_text = extracted["evidence_text"]
                    
                    fresh_job.save()
                    
                    # Track field stats
                    for f in updated_fields:
                        stats["fields_updated"][f] = stats["fields_updated"].get(f, 0) + 1
                    
                    if updated_fields:
                        stats["successfully_enriched"] += 1
                        processed[str(job_row_id)] = {
                            "outcome": "FETCHED",
                            "fields_updated": updated_fields,
                            "timestamp": timezone.now().isoformat()
                        }
                        print(f"[{done_count}/{total}] {job.job_id} ({comp_name}): ENRICHED ({len(updated_fields)} fields: {', '.join(updated_fields[:5])})")
                    else:
                        stats["fetched_no_new_fields"] += 1
                        processed[str(job_row_id)] = {
                            "outcome": "FETCHED",
                            "fields_updated": [],
                            "timestamp": timezone.now().isoformat()
                        }
                        print(f"[{done_count}/{total}] {job.job_id} ({comp_name}): FETCHED (no new fields)")
                
                elif status == "SOURCE_UNAVAILABLE":
                    stats["source_unavailable"] += 1
                    processed[str(job_row_id)] = {
                        "outcome": "SOURCE_UNAVAILABLE",
                        "timestamp": timezone.now().isoformat()
                    }
                    Job.objects.filter(job_row_id=job_row_id).update(
                        detail_fetch_status="SOURCE_UNAVAILABLE",
                        last_checked_date=timezone.now().isoformat()
                    )
                    print(f"[{done_count}/{total}] {job.job_id} ({comp_name}): SOURCE_UNAVAILABLE")
                
                else:
                    stats["extraction_failed"] += 1
                    processed[str(job_row_id)] = {
                        "outcome": "EXTRACTION_FAILED",
                        "timestamp": timezone.now().isoformat()
                    }
                    Job.objects.filter(job_row_id=job_row_id).update(
                        detail_fetch_status="EXTRACTION_FAILED",
                        last_checked_date=timezone.now().isoformat()
                    )
                    print(f"[{done_count}/{total}] {job.job_id} ({comp_name}): EXTRACTION_FAILED")
        
        # Save checkpoint after each batch
        checkpoint["processed"] = processed
        checkpoint["stats"] = stats
        save_checkpoint(checkpoint)
        
        # Rate limit between batches
        time.sleep(0.5)
    
    elapsed = time.time() - start_time
    
    # Save final results
    checkpoint["processed"] = processed
    checkpoint["stats"] = stats
    checkpoint["completed_at"] = timezone.now().isoformat()
    checkpoint["elapsed_seconds"] = round(elapsed, 1)
    save_checkpoint(checkpoint)
    
    # Also save a clean results file
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    
    print(f"\n{'=' * 80}")
    print(f"REMEDIATION COMPLETE in {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
    print(f"{'=' * 80}")
    for k, v in stats.items():
        if k != "fields_updated":
            print(f"  {k}: {v}")
    print(f"\n  Fields updated breakdown:")
    for f, c in sorted(stats.get("fields_updated", {}).items(), key=lambda x: -x[1]):
        print(f"    {f}: {c}")
    print(f"\nCheckpoint: {CHECKPOINT_FILE}")
    print(f"Results: {RESULTS_FILE}")
    
    return stats


if __name__ == "__main__":
    run_remediation(workers=6, batch_size=40)
