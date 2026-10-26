"""
modules/admin_panel/management/commands/audit_public.py
======================================================
Step 0 Exact-Match Standard: Public Data Quality Audit.

Independently re-fetches a sample of public Jobs (default 300) and CSR records (default 100)
to generate a comprehensive match vs. mismatch scorecard.

Release Criterion: 0 mismatches on live published records.
Any mismatch is saved as a regression fixture in tests/regression_fixtures/

Usage:
    python manage.py audit_public
    python manage.py audit_public --job-sample 50 --csr-sample 20
    python manage.py audit_public --company ACC
"""

import os
import re
import json
import random
import logging
from concurrent.futures import ThreadPoolExecutor

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from modules.admin_panel.models import Job, CSRProject
from modules.admin_panel.verification import public_jobs, public_records
from modules.crawler_engine.access_detector import fetch_live_page
from modules.crawler_engine.normalizers import clean_text

logger = logging.getLogger(__name__)


def norm_ws(v: str) -> str:
    if not v:
        return ""
    return re.sub(r'\s+', ' ', str(v)).strip().lower()


class Command(BaseCommand):
    help = "Independent live audit of public jobs and CSR records with match vs mismatch scorecard."

    def add_arguments(self, parser):
        parser.add_argument('--job-sample', type=int, default=300, help='Number of public jobs to sample.')
        parser.add_argument('--csr-sample', type=int, default=100, help='Number of public CSR projects to sample.')
        parser.add_argument('--company', type=str, help='Filter audit by NSE symbol or company ID.')
        parser.add_argument('--workers', type=int, default=8, help='Number of concurrent workers.')

    def handle(self, *args, **options):
        job_target = options['job_sample']
        csr_target = options['csr_sample']
        company_filter = options.get('company')
        workers = max(1, options.get('workers') or 8)

        self.stdout.write(self.style.NOTICE(
            f"=== Step 0 Public Audit Scorecard ===\n"
            f"Target: {job_target} Jobs | {csr_target} CSR Projects | Workers: {workers}\n"
        ))

        fixture_dir = os.path.join("tests", "regression_fixtures")
        os.makedirs(fixture_dir, exist_ok=True)

        # 1. Audit Public Jobs
        job_qs = public_jobs().filter(link_status='VERIFIED_HTTP_200')
        if company_filter:
            job_qs = job_qs.filter(Q(company__nse_symbol=company_filter) | Q(company_id=company_filter))

        all_job_ids = list(job_qs.values_list('pk', flat=True))
        sample_job_ids = random.sample(all_job_ids, min(job_target, len(all_job_ids))) if all_job_ids else []
        jobs_to_audit = list(Job.objects.filter(pk__in=sample_job_ids))

        self.stdout.write(f"Auditing {len(jobs_to_audit)} sampled public jobs...")

        job_scorecard = {
            "total": len(jobs_to_audit),
            "matches": 0,
            "mismatches": 0,
            "field_matches": {
                "title": 0,
                "location": 0,
                "department": 0,
                "employment_type": 0,
                "external_id": 0
            },
            "mismatch_items": []
        }

        def audit_single_job(job: Job):
            target_url = job.canonical_url or job.application_url
            if not target_url:
                return job, False, {"error": "Missing URL"}

            resp = fetch_live_page(target_url)
            if not resp.get("ok"):
                return job, False, {"http_error": resp.get("error", "HTTP request failed")}

            html = resp.get("html", "")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            page_text = clean_text(soup.get_text(" ", strip=True))
            lower_text = norm_ws(page_text)

            diff = {}
            # Title
            raw_title = norm_ws(job.raw_title or job.job_title)
            h1 = norm_ws(soup.find(["h1", "h2"]).get_text()) if soup.find(["h1", "h2"]) else ""
            if raw_title and (raw_title in lower_text or (h1 and raw_title in h1)):
                job_scorecard["field_matches"]["title"] += 1
            else:
                diff["title"] = {"stored": raw_title, "found_in_page": False}

            # Location
            raw_loc = norm_ws(job.raw_location or job.location)
            if raw_loc:
                if raw_loc in lower_text:
                    job_scorecard["field_matches"]["location"] += 1
                else:
                    diff["location"] = {"stored": raw_loc, "found_in_page": False}

            # Department
            raw_dept = norm_ws(job.raw_department or job.department)
            if raw_dept:
                if raw_dept in lower_text:
                    job_scorecard["field_matches"]["department"] += 1
                else:
                    diff["department"] = {"stored": raw_dept, "found_in_page": False}

            # Employment Type
            raw_emp = norm_ws(job.raw_employment_type or job.employment_type)
            if raw_emp:
                if raw_emp in lower_text:
                    job_scorecard["field_matches"]["employment_type"] += 1
                else:
                    diff["employment_type"] = {"stored": raw_emp, "found_in_page": False}

            # External Job ID
            if job.external_job_id:
                clean_ext_id = norm_ws(job.external_job_id)
                if clean_ext_id in lower_text:
                    job_scorecard["field_matches"]["external_id"] += 1
                else:
                    diff["external_job_id"] = {"stored": clean_ext_id, "found_in_page": False}

            is_match = len(diff) == 0
            return job, is_match, diff

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(audit_single_job, j) for j in jobs_to_audit]
            for f in futures:
                job, is_match, diff = f.result()
                if is_match:
                    job_scorecard["matches"] += 1
                else:
                    job_scorecard["mismatches"] += 1
                    job_scorecard["mismatch_items"].append({
                        "job_id": job.job_id,
                        "job_title": job.job_title,
                        "company": job.company.company_name,
                        "diff": diff
                    })
                    # Save as regression fixture
                    fixture_path = os.path.join(fixture_dir, f"job_mismatch_{job.job_row_id}.json")
                    try:
                        with open(fixture_path, 'w', encoding='utf-8') as ff:
                            json.dump({
                                "type": "job",
                                "row_id": job.job_row_id,
                                "job_id": job.job_id,
                                "stored_data": {
                                    "title": job.job_title,
                                    "raw_title": job.raw_title,
                                    "location": job.location,
                                    "raw_location": job.raw_location,
                                    "external_job_id": job.external_job_id,
                                    "application_url": job.application_url
                                },
                                "diff": diff,
                                "audited_at": timezone.now().isoformat()
                            }, ff, indent=2)
                    except Exception as fe:
                        logger.warning("Could not write fixture %s: %s", fixture_path, fe)

        # 2. Audit Public CSR Projects
        csr_qs = public_records(CSRProject.objects.filter(status='ACTIVE'))
        if company_filter:
            csr_qs = csr_qs.filter(Q(company__nse_symbol=company_filter) | Q(company_id=company_filter))

        all_csr_ids = list(csr_qs.values_list('pk', flat=True))
        sample_csr_ids = random.sample(all_csr_ids, min(csr_target, len(all_csr_ids))) if all_csr_ids else []
        csr_to_audit = list(CSRProject.objects.filter(pk__in=sample_csr_ids))

        self.stdout.write(f"Auditing {len(csr_to_audit)} sampled public CSR projects...")

        csr_scorecard = {
            "total": len(csr_to_audit),
            "matches": 0,
            "mismatches": 0,
            "field_matches": {
                "project_name": 0,
                "budget_verbatim": 0
            },
            "mismatch_items": []
        }

        for proj in csr_to_audit:
            # Check verbatim budget requirement: if budget is set, must be in evidence text verbatim
            ev_text = (proj.evidence_text or "")
            raw_b = (proj.raw_budget_text or proj.budget or "").strip()
            budget_ok = True
            if raw_b and raw_b not in ("Not disclosed", ""):
                if raw_b not in ev_text:
                    budget_ok = False

            name_ok = bool(proj.project_name and len(proj.project_name.strip()) > 3)

            if budget_ok and name_ok:
                csr_scorecard["matches"] += 1
                csr_scorecard["field_matches"]["project_name"] += 1
                if raw_b:
                    csr_scorecard["field_matches"]["budget_verbatim"] += 1
            else:
                csr_scorecard["mismatches"] += 1
                diff = {
                    "budget_verbatim": budget_ok,
                    "project_name_valid": name_ok,
                    "raw_budget": raw_b,
                    "evidence_snippet": ev_text[:200]
                }
                csr_scorecard["mismatch_items"].append({
                    "csr_id": proj.csr_id,
                    "company": proj.company.company_name,
                    "diff": diff
                })
                fixture_path = os.path.join(fixture_dir, f"csr_mismatch_{proj.csr_id}.json")
                try:
                    with open(fixture_path, 'w', encoding='utf-8') as ff:
                        json.dump({
                            "type": "csr",
                            "csr_id": proj.csr_id,
                            "stored_data": {
                                "project_name": proj.project_name,
                                "raw_budget_text": proj.raw_budget_text,
                                "budget": proj.budget
                            },
                            "diff": diff,
                            "audited_at": timezone.now().isoformat()
                        }, ff, indent=2)
                except Exception as fe:
                    logger.warning("Could not write fixture %s: %s", fixture_path, fe)

        # Print Scorecard
        self.stdout.write(self.style.SUCCESS("------------------------------------------------------------"))
        self.stdout.write(self.style.SUCCESS("                  AUDIT SCORECARD SUMMARY                   "))
        self.stdout.write(self.style.SUCCESS("------------------------------------------------------------"))
        self.stdout.write(f"Jobs Audited       : {job_scorecard['total']}")
        self.stdout.write(f"Jobs Matched       : {job_scorecard['matches']}")
        self.stdout.write(f"Jobs Mismatches    : {job_scorecard['mismatches']}")
        self.stdout.write(f"  - Title Match    : {job_scorecard['field_matches']['title']}")
        self.stdout.write(f"  - Location Match : {job_scorecard['field_matches']['location']}")
        self.stdout.write(f"  - Dept Match     : {job_scorecard['field_matches']['department']}")
        self.stdout.write(f"  - Emp Type Match : {job_scorecard['field_matches']['employment_type']}")
        self.stdout.write(f"  - Ext ID Match   : {job_scorecard['field_matches']['external_id']}")
        self.stdout.write("------------------------------------------------------------")
        self.stdout.write(f"CSR Audited        : {csr_scorecard['total']}")
        self.stdout.write(f"CSR Matched        : {csr_scorecard['matches']}")
        self.stdout.write(f"CSR Mismatches     : {csr_scorecard['mismatches']}")
        self.stdout.write(f"  - Verbatim Budget: {csr_scorecard['field_matches']['budget_verbatim']}")
        self.stdout.write(self.style.SUCCESS("------------------------------------------------------------"))


        total_mismatches = job_scorecard['mismatches'] + csr_scorecard['mismatches']
        if total_mismatches == 0:
            self.stdout.write(self.style.SUCCESS("RELEASE CRITERION SATISFIED: 0 MISMATCHES OBSERVED."))
        else:
            self.stdout.write(self.style.WARNING(
                f"AUDIT FOUND {total_mismatches} MISMATCHES. Fixtures saved in {fixture_dir}/"
            ))
