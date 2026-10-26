import os
import json
import difflib
from django.core.management.base import BaseCommand
from modules.admin_panel.models import Job, CSRProject

class Command(BaseCommand):
    help = "Scores extraction accuracy and precision against golden test datasets."

    def add_arguments(self, parser):
        parser.add_argument(
            "--jobs-golden",
            default="tests/golden/golden_jobs.json",
            help="Path to golden jobs JSON file"
        )
        parser.add_argument(
            "--csr-golden",
            default="tests/golden/golden_csr_projects.json",
            help="Path to golden CSR projects JSON file"
        )
        parser.add_argument(
            "--sources-golden",
            default="tests/golden/gold_sources.csv",
            help="Path to draft/verified gold sources CSV file"
        )

    def handle(self, *args, **options):
        jobs_path = options["jobs_golden"]
        csr_path = options["csr_golden"]
        sources_path = options.get("sources_golden", "tests/golden/gold_sources.csv")

        self.stdout.write("=" * 80)
        self.stdout.write("DATA ACCURACY SCORECARD: BASELINE PRECISION MEASUREMENT")
        self.stdout.write("=" * 80)

        # 1. Score Jobs
        if os.path.exists(jobs_path):
            with open(jobs_path, "r", encoding="utf-8") as f:
                golden_jobs = json.load(f)

            total_jobs = len(golden_jobs)
            title_matches = 0
            location_valid = 0
            url_direct_valid = 0
            emp_type_truthful = 0
            work_mode_truthful = 0

            # Phase 1: Warn if any golden record is not yet human-verified.
            unverified_jobs = [gj for gj in golden_jobs if not gj.get("verified_by_human", False)]
            if unverified_jobs:
                self.stdout.write(self.style.WARNING(
                    f"  [!] UNVERIFIED: {len(unverified_jobs)}/{total_jobs} golden job records have"
                    " verified_by_human=false. Scores below are ESTIMATES, not confirmed ground-truth."
                ))

            for gj in golden_jobs:
                db_job = Job.objects.filter(job_row_id=gj["job_row_id"]).first()
                if not db_job:
                    continue

                # Title match (exact or close)
                t_db = (db_job.job_title or "").strip().lower()
                t_exp = (gj.get("expected_title") or "").strip().lower()
                ratio = difflib.SequenceMatcher(None, t_db, t_exp).ratio()
                if ratio >= 0.9:
                    title_matches += 1

                # Location valid (not generic "India" unless expected, non-empty)
                loc_db = (db_job.location or "").strip()
                if loc_db and loc_db != "India":
                    location_valid += 1
                elif loc_db == "India" and (gj.get("expected_location") == "India"):
                    location_valid += 1

                # URL precision: must be DIRECT and not equal to listing URL or have text-fragment
                url_db = db_job.application_url or ""
                if db_job.link_quality == "DIRECT" and "#:~:text=" not in url_db and url_db.startswith("http"):
                    url_direct_valid += 1

                # Employment type: truthful if NOT defaulting to Full-time blindly
                # In baseline, if it's "Full-time", is it backed by real description?
                if db_job.employment_type and db_job.employment_type != "Full-time":
                    emp_type_truthful += 1
                elif db_job.employment_type == "Full-time" and db_job.job_description and "full" in db_job.job_description.lower():
                    emp_type_truthful += 1
                elif not db_job.employment_type or db_job.employment_type.lower() in ("unknown", "none"):
                    emp_type_truthful += 1

                # Work mode: truthful if NOT defaulting to On-site blindly
                if db_job.work_mode and db_job.work_mode != "On-site":
                    work_mode_truthful += 1
                elif db_job.work_mode == "On-site" and db_job.job_description and "on-site" in db_job.job_description.lower():
                    work_mode_truthful += 1
                elif not db_job.work_mode or db_job.work_mode.lower() in ("unknown", "none"):
                    work_mode_truthful += 1

            p_title = (title_matches / total_jobs * 100) if total_jobs > 0 else 0
            p_loc = (location_valid / total_jobs * 100) if total_jobs > 0 else 0
            p_url = (url_direct_valid / total_jobs * 100) if total_jobs > 0 else 0
            p_emp = (emp_type_truthful / total_jobs * 100) if total_jobs > 0 else 0
            p_wm = (work_mode_truthful / total_jobs * 100) if total_jobs > 0 else 0

            self.stdout.write(f"\n1. JOB DATA PRECISION (Sample size: {total_jobs} golden records):")
            self.stdout.write(f"   - Title Precision:            {title_matches}/{total_jobs} ({p_title:.1f}%)")
            self.stdout.write(f"   - Location Precision:         {location_valid}/{total_jobs} ({p_loc:.1f}%)")
            self.stdout.write(f"   - Direct URL Precision:       {url_direct_valid}/{total_jobs} ({p_url:.1f}%)")
            self.stdout.write(f"   - Truthful Employment Type:   {emp_type_truthful}/{total_jobs} ({p_emp:.1f}%)")
            self.stdout.write(f"   - Truthful Work Mode:         {work_mode_truthful}/{total_jobs} ({p_wm:.1f}%)")
        else:
            self.stdout.write(self.style.WARNING(f"Golden jobs file not found at {jobs_path}"))

        # 2. Score CSR Projects
        if os.path.exists(csr_path):
            with open(csr_path, "r", encoding="utf-8") as f:
                golden_csr = json.load(f)

            total_csr = len(golden_csr)
            csr_title_matches = 0
            category_valid = 0
            budget_valid = 0
            url_clean = 0

            # Phase 1: Warn if any golden record is not yet human-verified.
            unverified_csr = [gc for gc in golden_csr if not gc.get("verified_by_human", False)]
            if unverified_csr:
                self.stdout.write(self.style.WARNING(
                    f"  [!] UNVERIFIED: {len(unverified_csr)}/{total_csr} golden CSR records have"
                    " verified_by_human=false. Scores below are ESTIMATES, not confirmed ground-truth."
                ))

            for gc in golden_csr:
                db_p = CSRProject.objects.filter(csr_id=gc["csr_id"]).first()
                if not db_p:
                    continue

                # Project name precision
                p_db = (db_p.project_name or "").strip().lower()
                p_exp = (gc.get("expected_project_name") or "").strip().lower()
                if p_db and difflib.SequenceMatcher(None, p_db, p_exp).ratio() >= 0.85:
                    csr_title_matches += 1

                # Category precision (valid statutory Schedule VII)
                cat = (db_p.category or "").strip()
                if cat and cat not in ("General", "Corporate", "Other", ""):
                    category_valid += 1

                # Budget precision: must be parseable and not absurd (>500 Cr) or statutory filing placeholder
                b = (db_p.budget or "").strip()
                if b and b != "Statutory Annual Filing":
                    # Check if numeric / parseable
                    import re
                    if re.search(r'\d', b) and not any(k in b.lower() for k in ("crore crore", "lakh lakh")):
                        budget_valid += 1

                # URL clean: no text fragments
                s_url = db_p.source_url or ""
                if s_url and "#:~:text=" not in s_url and s_url.startswith("http"):
                    url_clean += 1

            p_ctitle = (csr_title_matches / total_csr * 100) if total_csr > 0 else 0
            p_cat = (category_valid / total_csr * 100) if total_csr > 0 else 0
            p_bud = (budget_valid / total_csr * 100) if total_csr > 0 else 0
            p_curl = (url_clean / total_csr * 100) if total_csr > 0 else 0

            self.stdout.write(f"\n2. CSR PROJECT DATA PRECISION (Sample size: {total_csr} golden records):")
            self.stdout.write(f"   - Project Title Precision:    {csr_title_matches}/{total_csr} ({p_ctitle:.1f}%)")
            self.stdout.write(f"   - Schedule VII Category:      {category_valid}/{total_csr} ({p_cat:.1f}%)")
            self.stdout.write(f"   - Parseable Budget Precision: {budget_valid}/{total_csr} ({p_bud:.1f}%)")
            self.stdout.write(f"   - Clean Direct URL Precision: {url_clean}/{total_csr} ({p_curl:.1f}%)")
        else:
            self.stdout.write(self.style.WARNING(f"Golden CSR file not found at {csr_path}"))

        # 3. Score Company Sources (from gold_sources.csv)
        if os.path.exists(sources_path):
            import csv
            from modules.admin_panel.models.company import Company
            from modules.crawler_engine.normalizers import normalize_canonical_url

            with open(sources_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                all_source_rows = list(reader)

            total_sources = len(all_source_rows)
            verified_rows = [r for r in all_source_rows if (r.get("verified") or "").strip().upper() == "TRUE"]

            self.stdout.write(f"\n3. COMPANY SOURCES PRECISION (Ground-truth dataset: {sources_path}):")
            self.stdout.write(f"   - Total Defined Source Rows:  {total_sources}")
            self.stdout.write(f"   - Human Verified Rows:        {len(verified_rows)} / {total_sources}")

            if not verified_rows:
                self.stdout.write(self.style.WARNING(
                    "   [!] UNVERIFIED DRAFT: All rows currently have verified=FALSE.\n"
                    "       Per system guidelines, the evaluator evaluates accuracy ONLY against human-verified rows (verified=TRUE).\n"
                    "       Conservative policy active: Unverified candidates are routed to REVIEW_REQUIRED."
                ))
            else:
                correct_matches = 0
                for r in verified_rows:
                    cid = r.get("company_id")
                    cat = (r.get("category") or "").upper().strip()
                    exp_url = normalize_canonical_url(r.get("correct_url") or "")

                    comp = Company.objects.filter(company_id=cid).first()
                    if not comp:
                        continue

                    db_url = ""
                    if cat == "CAREERS":
                        db_url = comp.careers_url or comp.jobs_page_url or comp.ats_url or ""
                    elif cat == "CSR":
                        db_url = comp.csr_portal_url or ""
                    elif cat == "SUSTAINABILITY":
                        db_url = comp.sustainability_url or comp.esg_url or ""
                    elif cat in ("ANNUAL_REPORT", "BRSR"):
                        db_url = comp.annual_report_url or comp.brsr_url or ""

                    db_norm = normalize_canonical_url(db_url)
                    if db_norm and exp_url and (db_norm == exp_url or exp_url in db_norm or db_norm in exp_url):
                        correct_matches += 1

                p_src = (correct_matches / len(verified_rows) * 100) if verified_rows else 0
                self.stdout.write(f"   - Verified Source Accuracy:   {correct_matches}/{len(verified_rows)} ({p_src:.1f}%)")
        else:
            self.stdout.write(self.style.WARNING(f"Golden Sources file not found at {sources_path}"))

        self.stdout.write("\n" + "=" * 80)
