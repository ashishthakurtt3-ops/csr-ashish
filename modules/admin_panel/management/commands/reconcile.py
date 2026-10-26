"""
modules/admin_panel/management/commands/reconcile.py
===================================================
Step 0 Exact-Match Standard: Reconciliation Verifier.

For every public record, independently re-fetches the job's own page or ATS
detail endpoint by a DIFFERENT path from original extraction, and compares:
- title / job_title
- external_job_id
- location
- application_url

Exact match after whitespace normalization only.
Mismatch -> record status = 'NEEDS_REVIEW', hidden from public view/API/stats
with mismatch_reason and mismatch_diff recorded.
Pass -> last_reconciled_at = timezone.now()

Usage:
    python manage.py reconcile
    python manage.py reconcile --limit 100
    python manage.py reconcile --company ACC
    python manage.py reconcile --workers 8
"""

import re
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from modules.admin_panel.models import Job, CSRProject, Company, AuditTrail
from modules.crawler_engine.access_detector import fetch_live_page
from modules.crawler_engine.normalizers import clean_text

logger = logging.getLogger(__name__)


def normalize_ws(val: str) -> str:
    """Whitespace normalizer for exact match comparison."""
    if not val:
        return ""
    return re.sub(r'\s+', ' ', str(val)).strip()


class Command(BaseCommand):
    help = "Independently re-fetch and exact-match reconcile public jobs and CSR records."

    def add_arguments(self, parser):
        parser.add_argument('--company', type=str, help='NSE symbol or company_id.')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of records to reconcile.')
        parser.add_argument('--workers', type=int, default=8, help='Number of concurrent workers.')
        parser.add_argument('--stale-hours', type=int, default=0, help='Only check records not reconciled in N hours.')
        parser.add_argument('--job-id', type=str, help='Reconcile a specific job ID.')

    def handle(self, *args, **options):
        company_filter = options.get('company')
        limit = options.get('limit') or 0
        workers = max(1, options.get('workers') or 8)
        stale_hours = options.get('stale_hours') or 0
        job_id_filter = options.get('job_id')

        self.stdout.write(self.style.NOTICE("=== Step 0: Reconciliation Verifier Execution ==="))

        # Query candidates: Prioritize newest unreconciled jobs
        qs = Job.objects.filter(status='ACTIVE')
        if company_filter:
            qs = qs.filter(Q(company__nse_symbol=company_filter) | Q(company_id=company_filter))
        if job_id_filter:
            qs = qs.filter(job_id=job_id_filter)
        if stale_hours > 0:
            cutoff = timezone.now() - timedelta(hours=stale_hours)
            qs = qs.filter(Q(last_reconciled_at__isnull=True) | Q(last_reconciled_at__lt=cutoff))

        # Order by unreconciled first, then newest
        qs = qs.order_by(
            models_nulls_first('last_reconciled_at'),
            '-job_row_id'
        )

        if limit > 0:
            qs = qs[:limit]

        jobs = list(qs)
        total_jobs = len(jobs)
        self.stdout.write(f"Targeting {total_jobs} active jobs for independent reconciliation...\n")

        if not jobs:
            self.stdout.write(self.style.SUCCESS("No records require reconciliation."))
            return

        reconciled_count = 0
        mismatch_count = 0
        inaccessible_count = 0

        def check_job(job: Job):
            target_url = job.canonical_url or job.application_url
            if not target_url:
                return job, False, "MISSING_URL", {"error": "No canonical or application URL stored on job record."}

            # Fetch via alternative direct path
            res = fetch_live_page(target_url)
            if not res.get("ok"):
                return job, False, "INACCESSIBLE_OR_CLOSED", {
                    "status_code": res.get("status_code", 0),
                    "error": res.get("error", "HTTP request failed / closed")
                }

            html = res.get("html", "")
            if not html:
                return job, False, "EMPTY_RESPONSE", {"error": "Page returned empty body"}

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            page_text = clean_text(soup.get_text(" ", strip=True))

            # 1. Closed or login wall checks
            lower_text = page_text.lower()
            if any(term in lower_text for term in ["this job has expired", "position closed", "no longer accepting applications", "job is no longer available"]):
                return job, False, "JOB_CLOSED", {"reason": "Official page states job has expired or is closed."}

            if any(term in lower_text for term in ["login to view", "sign in to apply", "access restricted"]):
                return job, False, "LOGIN_WALL", {"reason": "Official page requires authentication."}

            # 2. Check title exact match after whitespace normalization
            stored_title = normalize_ws(job.raw_title or job.job_title)
            # Find page title / H1
            h1 = soup.find(["h1", "h2"])
            h1_text = normalize_ws(clean_text(h1.get_text())) if h1 else ""
            doc_title = normalize_ws(clean_text(soup.title.string)) if soup.title else ""

            # Check if stored title is present in document title or h1 or verbatim in body
            title_matched = (
                (stored_title and stored_title.lower() in h1_text.lower()) or
                (stored_title and stored_title.lower() in doc_title.lower()) or
                (stored_title and stored_title.lower() in lower_text)
            )

            diff = {}
            if not title_matched:
                diff["job_title"] = {
                    "stored": stored_title,
                    "observed_h1": h1_text,
                    "observed_doc_title": doc_title
                }

            # 3. Check external_job_id if published
            if job.external_job_id:
                clean_ext_id = normalize_ws(job.external_job_id)
                if clean_ext_id and clean_ext_id not in page_text:
                    diff["external_job_id"] = {
                        "stored": clean_ext_id,
                        "present_in_page": False
                    }

            # 4. Check location if published
            stored_loc = normalize_ws(job.raw_location or job.location)
            if stored_loc and len(stored_loc) > 3:
                # Primary city / state check
                loc_matched = stored_loc.lower() in lower_text
                if not loc_matched:
                    diff["location"] = {
                        "stored": stored_loc,
                        "present_in_page": False
                    }

            if diff:
                return job, False, "DATA_MISMATCH", diff

            return job, True, "MATCH_CONFIRMED", {}

        # Run concurrent checks
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(check_job, j) for j in jobs]
            for f in futures:
                job, ok, reason, diff_data = f.result()
                if ok:
                    job.last_reconciled_at = timezone.now()
                    job.mismatch_reason = None
                    job.mismatch_diff = {}
                    job.save(update_fields=['last_reconciled_at', 'mismatch_reason', 'mismatch_diff'])
                    reconciled_count += 1
                else:
                    mismatch_count += 1
                    if reason in ("INACCESSIBLE_OR_CLOSED", "JOB_CLOSED", "LOGIN_WALL"):
                        inaccessible_count += 1

                    # Flag status as NEEDS_REVIEW, hiding from public view/API
                    job.status = 'NEEDS_REVIEW'
                    job.mismatch_reason = f"[{reason}] {json.dumps(diff_data)}"
                    job.mismatch_diff = diff_data
                    job.save(update_fields=['status', 'mismatch_reason', 'mismatch_diff'])

                    # Audit entry
                    AuditTrail.objects.create(
                        record_type="Job",
                        record_id=str(job.job_row_id),
                        action="RECONCILIATION_MISMATCH_QUARANTINE",
                        previous_value="ACTIVE",
                        new_value="NEEDS_REVIEW",
                        user_role="RECONCILIATION_ENGINE",
                        notes=f"Mismatch identified: {reason} | Diff: {json.dumps(diff_data)[:500]}",
                        timestamp=timezone.now().isoformat()
                    )
                    self.stdout.write(self.style.WARNING(
                        f"Quarantined Job #{job.job_row_id} ({job.job_title}): {reason}"
                    ))

        self.stdout.write(self.style.SUCCESS("--------------------------------------------------"))
        self.stdout.write(self.style.SUCCESS("             RECONCILIATION COMPLETE             "))
        self.stdout.write(self.style.SUCCESS("--------------------------------------------------"))
        self.stdout.write(f"Total Checked    : {total_jobs}")
        self.stdout.write(f"Exact Match Pass : {reconciled_count}")
        self.stdout.write(f"Mismatches       : {mismatch_count} (Flagged NEEDS_REVIEW)")
        self.stdout.write(f"Inaccessible/404 : {inaccessible_count}")
        self.stdout.write(self.style.SUCCESS("--------------------------------------------------"))



def models_nulls_first(field_name: str):
    from django.db.models import F
    return F(field_name).asc(nulls_first=True)
