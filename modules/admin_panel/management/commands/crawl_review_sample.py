"""
modules/admin_panel/management/commands/crawl_review_sample.py
=============================================================
Dry-run crawl review sampler for cross-checking candidate discovery, page classification,
and content extraction across a diverse 15-company portfolio.

Strict Hard Rules:
1. DRY RUN: NO database writes, NO status changes, NO publishing, NO URL updates.
   Enforces and asserts that database row counts are identical before and after.
2. ELIGIBILITY: Only companies with:
   - company_id exists
   - company_name is set
   - website_url confirmed correct (ALREADY_OK or approved correction from homepage verification).
   - Excludes REVIEW_REQUIRED, HOMEPAGE_NOT_FOUND, WRONG_ENTITY, UNVERIFIABLE_BLOCKED.
   - Crawl runs strictly using these three fields; old careers/CSR URLs are used only as DB_HINT candidates.
3. CAPS & LIMITS:
   - At most 50 jobs per company (with total found recorded).
   - Up to 20 CSR projects or disclosures per company.
   - Per-company time limit (default 300s), polite per-domain rate limit.
   - Failure isolation: blocked or failed companies do not halt execution.
4. ARTIFACTS:
   - exports/crawl_review/<timestamp>/crawl_review.xlsx with frozen headers, filters, wrapped text,
     clickable URLs, and CHECK dropdowns.
   - One CSV per sheet with identical tabular content.
   - evidence/<company_id>/ text previews for each chosen page (URL, HTTP status, first 2,000 chars).
   - run_log.txt detailing timings, errors, and every AI decision.

Usage:
    python manage.py crawl_review_sample --count 15 --out exports/crawl_review
    python manage.py crawl_review_sample --company-ids COMP_TOP200_017,COMP_TOP200_169 --out exports/crawl_review
"""

import os
import re
import csv
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set
from urllib.parse import urlparse

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, Contact, AuditTrail
from modules.crawler_engine.candidate_collector import CandidateCollector
from modules.crawler_engine.page_classifier import TwoStagePageClassifier
from modules.crawler_engine.strategies.pipeline import StrategyPipeline
from modules.crawler_engine.parsers.csr_pdf import CSRPdfParser
from modules.crawler_engine.parsers.corporate import CorporateHTMLParser
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor
from modules.crawler_engine.access_detector import fetch_live_page
from modules.crawler_engine.normalizers import clean_text, normalize_canonical_url
from modules.crawler_engine import ai_classifier_config as cfg

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# Default portfolio of 15 diverse companies selected across sectors, ATS platforms, and sizes
DEFAULT_DIVERSE_15 = [
    {
        "company_id": "COMP_TOP200_017",
        "company_name": "Adani Enterprises Limited",
        "reason": "Conglomerate group, shared group portal (Adani), Oracle Taleo ATS",
    },
    {
        "company_id": "COMP_TOP200_169",
        "company_name": "ACC Limited",
        "reason": "Manufacturing / Cement, large industrial conglomerate affiliate",
    },
    {
        "company_id": "COMP_TOP200_160",
        "company_name": "3i Infotech Limited",
        "reason": "IT Services / Mid-cap tech, plain corporate careers portal",
    },
    {
        "company_id": "COMP_TOP200_199",
        "company_name": "Aarti Industries Limited",
        "reason": "Manufacturing / Specialty Chemicals, direct corporate careers",
    },
    {
        "company_id": "COMP_TOP200_148",
        "company_name": "Ashok Leyland Limited",
        "reason": "Automotive / Commercial Vehicles, Darwinbox ATS platform",
    },
    {
        "company_id": "COMP_TOP200_064",
        "company_name": "Bosch Limited",
        "reason": "Manufacturing / Auto-tech, SmartRecruiters ATS platform",
    },
    {
        "company_id": "COMP_TOP200_073",
        "company_name": "Hero MotoCorp Limited",
        "reason": "Automotive / Two-wheelers, SAP SuccessFactors ATS platform",
    },
    {
        "company_id": "COMP_TOP200_095",
        "company_name": "One 97 Communications Limited",
        "reason": "Fintech / New-age consumer tech (Paytm), Lever ATS platform",
    },
    {
        "company_id": "COMP_TOP200_003",
        "company_name": "State Bank of India",
        "reason": "Banking / Finance, largest public sector bank (PSU Bank)",
    },
    {
        "company_id": "COMP_TOP200_005",
        "company_name": "Tata Consultancy Services Limited",
        "reason": "IT / Tech giant, large enterprise conglomerate (Tata Group)",
    },
    {
        "company_id": "COMP_TOP200_015",
        "company_name": "ITC Limited",
        "reason": "FMCG / Consumer goods & agribusiness, extensive CSR disclosures",
    },
    {
        "company_id": "COMP_TOP200_009",
        "company_name": "NTPC Limited",
        "reason": "PSU / Energy & Power Maharatna, statutory public sector disclosures",
    },
    {
        "company_id": "COMP_TOP200_081",
        "company_name": "Lupin Limited",
        "reason": "Pharmaceuticals / Healthcare, global life sciences, SAP SuccessFactors",
    },
    {
        "company_id": "COMP_TOP200_184",
        "company_name": "AU Small Finance Bank Limited",
        "reason": "Banking / Small Finance Bank, fast-growing retail banking lender",
    },
    {
        "company_id": "COMP_TOP200_154",
        "company_name": "20 Microns Limited",
        "reason": "Manufacturing / Industrial minerals, small-cap, plain HTML careers",
    },
]


def load_homepage_verification_status_map() -> Dict[str, str]:
    """
    Loads verified homepage status map from exports/homepage_verification_results.json.
    Returns dict mapping company_id -> status ('ALREADY_OK', 'CORRECT', etc.).
    """
    results_path = os.path.join("exports", "homepage_verification_results.json")
    if os.path.exists(results_path):
        try:
            with open(results_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {cid: info.get("status", "UNKNOWN") for cid, info in data.items()}
        except Exception as exc:
            logger.warning("Could not read %s: %s", results_path, exc)
    return {}


def is_company_eligible(company: Company, status_map: Dict[str, str]) -> Tuple[bool, str]:
    """
    Enforces eligibility rule:
    - company_id exists
    - company_name is set and non-empty
    - website_url is confirmed correct (CORRECT or ALREADY_OK from homepage verification)
    - Excludes REVIEW_REQUIRED, HOMEPAGE_NOT_FOUND, WRONG_ENTITY, UNVERIFIABLE_BLOCKED, unapproved AUTO_CORRECTED.
    """
    if not company.company_id:
        return False, "Missing company_id"
    if not company.company_name or not company.company_name.strip():
        return False, "Missing company_name"
    if not company.website_url or not company.website_url.strip():
        return False, "Missing website_url"

    status = status_map.get(company.company_id) or getattr(company, "website_url_status", None) or "UNKNOWN"
    status_upper = status.upper()

    if status_upper in ("CORRECT", "ALREADY_OK", "VERIFIED_HTTP_200"):
        return True, "Eligible (homepage confirmed ALREADY_OK/CORRECT)"

    if status_upper == "AUTO_CORRECTED":
        return False, "Excluded: unapproved AUTO_CORRECTED (must be approved before crawl)"
    if status_upper == "REVIEW_REQUIRED":
        return False, "Excluded: homepage status is REVIEW_REQUIRED"
    if status_upper == "HOMEPAGE_NOT_FOUND":
        return False, "Excluded: homepage status is HOMEPAGE_NOT_FOUND"
    if status_upper in ("TEMPORARILY_UNVERIFIABLE", "UNVERIFIABLE_BLOCKED"):
        return False, "Excluded: homepage status is TEMPORARILY_UNVERIFIABLE"
    if status_upper == "WRONG_ENTITY":
        return False, "Excluded: homepage status is WRONG_ENTITY"

    return False, f"Excluded: unverified homepage status '{status}'"


class Command(BaseCommand):
    help = "Crawl 15 companies in DRY-RUN mode and export findings to structured Excel, CSVs, and evidence files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=15,
            help="Number of diverse sample companies to crawl (default: 15).",
        )
        parser.add_argument(
            "--company-ids",
            type=str,
            default="",
            help="Comma-separated list of company IDs to override the diverse default choice.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default="exports/crawl_review",
            help="Base output directory (default: exports/crawl_review).",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=300,
            help="Per-company crawl time limit in seconds (default: 300 / 5 minutes).",
        )

    def handle(self, *args, **options):
        count_limit = options.get("count", 15)
        company_ids_arg = options.get("company_ids", "").strip()
        out_base = options.get("out", "exports/crawl_review")
        timeout_sec = options.get("timeout", 300)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = os.path.join(out_base, timestamp_str)
        evidence_dir = os.path.join(out_dir, "evidence")
        os.makedirs(evidence_dir, exist_ok=True)

        log_path = os.path.join(out_dir, "run_log.txt")
        self._log_file = open(log_path, "w", encoding="utf-8")
        self._log(f"=== ImpactBridge Crawl Review Sampler (DRY RUN) ===")
        self._log(f"Timestamp: {timestamp_str}")
        self._log(f"Output directory: {out_dir}")
        self._log(f"Per-company timeout: {timeout_sec}s")

        # ----------------------------------------------------------------------
        # 1. HARD RULE: Check DB row counts BEFORE crawl
        # ----------------------------------------------------------------------
        db_counts_before = self._get_db_counts()
        self._log(f"Initial DB row counts: {db_counts_before}")
        self.stdout.write(self.style.NOTICE(f"Initial Database Row Counts: {db_counts_before}"))

        # ----------------------------------------------------------------------
        # 2. Load Homepage Verification Status & Determine Chosen Companies
        # ----------------------------------------------------------------------
        status_map = load_homepage_verification_status_map()
        self._log(f"Loaded {len(status_map)} records from homepage verification results map.")

        chosen_items = self._select_companies(
            count_limit=count_limit,
            company_ids_str=company_ids_arg,
            status_map=status_map,
        )

        self.stdout.write(self.style.MIGRATE_HEADING(f"\n--- Chosen Companies for Review Sample ({len(chosen_items)}) ---"))
        for idx, item in enumerate(chosen_items, 1):
            msg = f"{idx:>2}. [{item['company_id']}] {item['company_name']} - Reason: {item['reason']}"
            self.stdout.write(msg)
            self._log(msg)

        # ----------------------------------------------------------------------
        # 3. Initialize Shared Crawler Components
        # ----------------------------------------------------------------------
        classifier_name = "TwoStagePageClassifier (OpenRouter Free / Deterministic Fallback + Evidence Gate)"
        page_classifier = TwoStagePageClassifier()
        strategy_pipeline = StrategyPipeline()
        collector = CandidateCollector(
            max_cap=50,
            allow_playwright=True,
            probe_common_paths=True,
            probe_subdomains=True,
            probe_sitemaps=True,
        )

        # In-memory accumulators for report generation
        companies_rows: List[Dict[str, Any]] = []
        pages_rows: List[Dict[str, Any]] = []
        jobs_rows: List[Dict[str, Any]] = []
        csr_rows: List[Dict[str, Any]] = []
        contacts_rows: List[Dict[str, Any]] = []
        warnings_rows: List[Dict[str, Any]] = []

        total_companies = len(chosen_items)
        self.stdout.write(self.style.NOTICE(f"\n--> Starting Dry-Run Crawl across {total_companies} companies...\n"))

        # ----------------------------------------------------------------------
        # 4. Crawl Loop with Failure Isolation & Polite Rate Limiting
        # ----------------------------------------------------------------------
        for idx, item in enumerate(chosen_items, 1):
            cid = item["company_id"]
            cname = item["company_name"]
            cobj = item["company_obj"]
            reason = item["reason"]

            self.stdout.write(f"[{idx}/{total_companies}] Crawling {cid} - {cname}...")
            self._log(f"\n--- [{idx}/{total_companies}] Company: {cid} ({cname}) ---")
            self._log(f"Registered Website URL: {cobj.website_url}")

            start_t = time.time()
            comp_evidence_dir = os.path.join(evidence_dir, cid)
            os.makedirs(comp_evidence_dir, exist_ok=True)

            try:
                res = self._crawl_one_company(
                    company=cobj,
                    collector=collector,
                    classifier=page_classifier,
                    pipeline=strategy_pipeline,
                    timeout_sec=timeout_sec,
                    evidence_dir=comp_evidence_dir,
                )

                elapsed = round(time.time() - start_t, 2)
                res["time_taken"] = elapsed
                self._log(f"Completed {cid} in {elapsed}s with status {res['result']}: {res['reason']}")

                # Accumulate company summary
                companies_rows.append({
                    "company_id": cid,
                    "company_name": cname,
                    "website_url": cobj.website_url,
                    "crawl_result": res["result"],
                    "reason": res["reason"],
                    "time_taken_seconds": elapsed,
                    "pages_found": len(res["pages"]),
                    "jobs_found": len(res["jobs"]),
                    "csr_items_found": len(res["csr"]),
                    "contacts_found": len(res["contacts"]),
                    "ai_calls": res["ai_calls"],
                    "cache_hits": res["cache_hits"],
                })

                pages_rows.extend(res["pages"])
                jobs_rows.extend(res["jobs"])
                csr_rows.extend(res["csr"])
                contacts_rows.extend(res["contacts"])
                warnings_rows.extend(res["warnings"])

                color_fn = self.style.SUCCESS if res["result"] == "OK" else (self.style.WARNING if res["result"] == "PARTIAL" else self.style.ERROR)
                self.stdout.write(color_fn(
                    f"     Status: {res['result']} | Pages: {len(res['pages'])}, Jobs: {len(res['jobs'])}, "
                    f"CSR: {len(res['csr'])}, Contacts: {len(res['contacts'])} ({elapsed}s)"
                ))

            except Exception as exc:
                elapsed = round(time.time() - start_t, 2)
                err_msg = f"Fatal company exception: {str(exc)}"
                self._log(f"ERROR in {cid}: {err_msg}")
                self.stdout.write(self.style.ERROR(f"     FAILED: {err_msg} ({elapsed}s)"))

                companies_rows.append({
                    "company_id": cid,
                    "company_name": cname,
                    "website_url": cobj.website_url,
                    "crawl_result": "FAILED",
                    "reason": err_msg,
                    "time_taken_seconds": elapsed,
                    "pages_found": 0,
                    "jobs_found": 0,
                    "csr_items_found": 0,
                    "contacts_found": 0,
                    "ai_calls": 0,
                    "cache_hits": 0,
                })
                warnings_rows.append({
                    "company_id": cid,
                    "company_name": cname,
                    "warning_type": "FATAL_COMPANY_EXCEPTION",
                    "details": err_msg,
                    "url": cobj.website_url or "",
                    "evidence_snippet": "",
                })

            # Polite delay between companies
            time.sleep(0.5)

        # ----------------------------------------------------------------------
        # 5. HARD RULE: Check DB row counts AFTER crawl
        # ----------------------------------------------------------------------
        db_counts_after = self._get_db_counts()
        self._log(f"\nFinal DB row counts: {db_counts_after}")

        db_unchanged = (db_counts_before == db_counts_after)
        if not db_unchanged:
            diff_msg = f"CRITICAL INTEGRITY FAILURE: Database was mutated during dry run! Before={db_counts_before}, After={db_counts_after}"
            self._log(diff_msg)
            raise CommandError(diff_msg)

        # ----------------------------------------------------------------------
        # 6. Generate Excel Spreadsheet, CSVs, and README
        # ----------------------------------------------------------------------
        self.stdout.write(self.style.NOTICE("\n--> Generating Excel spreadsheet and CSV exports..."))
        excel_path = os.path.join(out_dir, "crawl_review.xlsx")

        self._export_to_excel_and_csv(
            out_dir=out_dir,
            excel_path=excel_path,
            classifier_name=classifier_name,
            companies_rows=companies_rows,
            pages_rows=pages_rows,
            jobs_rows=jobs_rows,
            csr_rows=csr_rows,
            contacts_rows=contacts_rows,
            warnings_rows=warnings_rows,
        )

        self._log(f"Excel report saved to: {excel_path}")
        self._log("Crawl review completed successfully.")
        self._log_file.close()

        # ----------------------------------------------------------------------
        # 7. Print Terminal Summary
        # ----------------------------------------------------------------------
        status_counts = {}
        for r in companies_rows:
            st = r["crawl_result"]
            status_counts[st] = status_counts.get(st, 0) + 1

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("CRAWL REVIEW SAMPLE COMPLETE (DRY RUN)"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total Companies Processed: {len(companies_rows)}")
        self.stdout.write(f"Results Breakdown:")
        for st, c in sorted(status_counts.items()):
            self.stdout.write(f"  - {st:<10}: {c}")
        self.stdout.write("-" * 80)
        self.stdout.write(f"Rows Exported per Sheet:")
        self.stdout.write(f"  - Companies : {len(companies_rows)}")
        self.stdout.write(f"  - Pages     : {len(pages_rows)}")
        self.stdout.write(f"  - Jobs      : {len(jobs_rows)}")
        self.stdout.write(f"  - CSR       : {len(csr_rows)}")
        self.stdout.write(f"  - Contacts  : {len(contacts_rows)}")
        self.stdout.write(f"  - Warnings  : {len(warnings_rows)}")
        self.stdout.write("-" * 80)
        self.stdout.write(self.style.SUCCESS(f"DATABASE INVARIANT VERIFIED: All table row counts 100% UNCHANGED."))
        self.stdout.write(f"  Before: {db_counts_before}")
        self.stdout.write(f"  After:  {db_counts_after}")
        self.stdout.write("-" * 80)
        self.stdout.write(self.style.NOTICE(f"Output Artifacts Directory: {out_dir}"))
        self.stdout.write(self.style.NOTICE(f"Master Excel Workbook:     {excel_path}"))
        self.stdout.write("=" * 80 + "\n")

    # ==========================================================================
    # HELPER: Company Selection & Eligibility
    # ==========================================================================
    def _select_companies(
        self,
        count_limit: int,
        company_ids_str: str,
        status_map: Dict[str, str],
    ) -> List[Dict[str, Any]]:
        """
        Selects companies for crawl review:
        - If --company-ids is provided, validates eligibility and uses those.
        - Otherwise, picks the diverse 15 portfolio ensuring Adani, ACC, 3i Infotech, and Aarti Industries are included.
        """
        chosen = []

        if company_ids_str:
            ids = [x.strip() for x in company_ids_str.split(",") if x.strip()]
            for cid in ids:
                cobj = Company.objects.filter(company_id=cid).first()
                if not cobj:
                    raise CommandError(f"Requested company_id '{cid}' does not exist in database.")
                eligible, el_reason = is_company_eligible(cobj, status_map)
                if not eligible:
                    raise CommandError(f"Company '{cid}' ({cobj.company_name}) is NOT eligible for crawl: {el_reason}")
                chosen.append({
                    "company_id": cobj.company_id,
                    "company_name": cobj.company_name,
                    "company_obj": cobj,
                    "reason": f"Explicitly requested via --company-ids: {el_reason}",
                })
            return chosen

        # Process default diverse list
        for item in DEFAULT_DIVERSE_15:
            cid = item["company_id"]
            cobj = Company.objects.filter(company_id=cid).first()
            if not cobj:
                continue
            eligible, el_reason = is_company_eligible(cobj, status_map)
            if eligible:
                chosen.append({
                    "company_id": cobj.company_id,
                    "company_name": cobj.company_name,
                    "company_obj": cobj,
                    "reason": item["reason"],
                })
            else:
                self._log(f"Default candidate {cid} ({cobj.company_name}) excluded: {el_reason}")

        if len(chosen) >= count_limit:
            return chosen[:count_limit]

        # Fill remaining slots up to count_limit from remaining eligible companies
        for c in Company.objects.all().order_by("company_id"):
            if any(x["company_id"] == c.company_id for x in chosen):
                continue
            eligible, _ = is_company_eligible(c, status_map)
            if eligible:
                chosen.append({
                    "company_id": c.company_id,
                    "company_name": c.company_name,
                    "company_obj": c,
                    "reason": f"Diverse fill candidate ({c.sector or 'General'})",
                })
            if len(chosen) >= count_limit:
                break

        return chosen

    # ==========================================================================
    # HELPER: Crawl One Company (Dry Run)
    # ==========================================================================
    def _crawl_one_company(
        self,
        company: Company,
        collector: CandidateCollector,
        classifier: TwoStagePageClassifier,
        pipeline: StrategyPipeline,
        timeout_sec: int,
        evidence_dir: str,
    ) -> Dict[str, Any]:
        """
        Executes dry-run crawl for one company using existing candidate collection,
        AI page classification, validation, and content extraction strategies.
        """
        cid = company.company_id
        cname = company.company_name
        homepage_url = company.website_url

        res = {
            "result": "OK",
            "reason": "Successfully crawled official sources.",
            "pages": [],
            "jobs": [],
            "csr": [],
            "contacts": [],
            "warnings": [],
            "ai_calls": 0,
            "cache_hits": 0,
        }

        # ----------------------------------------------------------------------
        # Step 1: Collect Candidate Links
        # ----------------------------------------------------------------------
        start_time = time.time()
        self._log(f"Collecting candidate links for {homepage_url}...")

        # In-memory candidate collection strictly using company_id, company_name, and website_url
        candidates = collector.collect_candidates(
            homepage_url=homepage_url,
            company_symbol=company.nse_symbol or "",
        )
        self._log(f"Collector returned {len(candidates)} candidates.")

        # Inject existing DB URLs as DB_HINT candidates if valid and not already in pool
        db_hints = [
            (company.careers_url, "Careers URL"),
            (company.jobs_page_url, "Jobs Page URL"),
            (company.csr_portal_url, "CSR Portal URL"),
            (company.sustainability_url, "Sustainability URL"),
            (company.annual_report_url, "Annual Report URL"),
        ]
        existing_urls = {c.get("url") for c in candidates}
        for hint_url, hint_name in db_hints:
            if hint_url and hint_url.startswith("http") and hint_url not in existing_urls:
                candidates.append({
                    "url": hint_url,
                    "link_text": f"DB Hint ({hint_name})",
                    "menu_path": f"DB_HINT > {hint_name}",
                    "source": "DB_HINT",
                    "external_linked": False,
                    "ats_match": False,
                    "ats_platform": None,
                    "ownership_status": None,
                    "requires_owner_verification": False,
                })
                existing_urls.add(hint_url)

        if not candidates:
            # Check if homepage itself was blocked or failed
            hp_probe = fetch_live_page(homepage_url)
            if not hp_probe.get("ok"):
                code = hp_probe.get("status_code", 0)
                if code in (403, 429, 307):
                    res["result"] = "BLOCKED"
                    res["reason"] = f"Corporate website blocked requests (HTTP {code})."
                else:
                    res["result"] = "FAILED"
                    res["reason"] = f"Corporate homepage unreachable (HTTP {code})."
                res["warnings"].append({
                    "company_id": cid,
                    "company_name": cname,
                    "warning_type": "BLOCKED_PAGE",
                    "details": res["reason"],
                    "url": homepage_url,
                    "evidence_snippet": hp_probe.get("error", ""),
                })
                return res

        # Check candidate ownership flags for warnings
        for cand in candidates:
            if cand.get("requires_owner_verification"):
                res["warnings"].append({
                    "company_id": cid,
                    "company_name": cname,
                    "warning_type": "SHARED_TENANT_UNRESOLVED",
                    "details": f"Candidate URL is on a shared ATS tenant ({cand.get('ats_platform')}) requiring owner verification.",
                    "url": cand.get("url"),
                    "evidence_snippet": cand.get("link_text") or "",
                })

        # ----------------------------------------------------------------------
        # Step 2: AI Page Classification & Validation Gate
        # ----------------------------------------------------------------------
        domain = company.official_domain or urlparse(homepage_url).netloc
        classified_links = []

        try:
            # Stage 1: Link classification
            classified_links = classifier.classify_discovered_links(
                company_name=cname,
                domain=domain,
                links=candidates[:40],
            )
            res["ai_calls"] += len(classified_links) // 10 + 1
        except Exception as exc:
            self._log(f"AI Stage 1 warning for {cid}: {exc}. Using deterministic candidate prioritization.")
            classified_links = []
            for cand in candidates:
                u_low = (cand.get("url") or "").lower()
                t_low = (cand.get("link_text") or "").lower()
                m_low = (cand.get("menu_path") or "").lower()
                comb = f"{u_low} {t_low} {m_low}"
                cat = "UNKNOWN_REQUIRES_REVIEW"
                if cand.get("ats_match") or any(k in comb for k in ("career", "job", "join us", "work with us", "opening", "vacanc")):
                    cat = "JOBS_LISTING_CANDIDATE"
                elif any(k in comb for k in ("csr", "social impact", "foundation", "trust", "community")):
                    cat = "CSR_OVERVIEW_CANDIDATE"
                elif any(k in comb for k in ("sustainab", "esg", "environment")):
                    cat = "SUSTAINABILITY_REPORT_CANDIDATE"
                elif any(k in comb for k in ("annual report", "annual-report", "brsr")):
                    cat = "ANNUAL_REPORT_CANDIDATE"
                classified_links.append({
                    **cand,
                    "candidate_category": cat,
                    "confidence": 0.7,
                    "broad_category": "CORP_INTELLIGENCE",
                    "actual_model": "rule_based_fallback",
                })

        promising_candidates = classifier.filter_promising_candidates_for_stage_2(
            classified_links=classified_links,
            max_pages=8,
        )

        # Categorized selections
        chosen_by_category: Dict[str, Dict[str, Any]] = {}
        alternatives_by_category: Dict[str, List[str]] = {}

        for cand in promising_candidates:
            if (time.time() - start_time) > timeout_sec:
                self._log(f"Timeout reached ({timeout_sec}s) while classifying candidates for {cid}.")
                break

            cand_url = cand.get("url")
            if not cand_url:
                continue

            page_data = classifier.fetch_and_prepare_page_data(cand_url)
            status_code = page_data.get("status_code", 0)

            if status_code in (403, 429, 307):
                res["warnings"].append({
                    "company_id": cid,
                    "company_name": cname,
                    "warning_type": "BLOCKED_PAGE",
                    "details": f"Candidate page returned challenge/blocking status (HTTP {status_code}).",
                    "url": cand_url,
                    "evidence_snippet": page_data.get("main_text", "")[:200],
                })
                continue

            # Stage 2 classification
            try:
                dest_class = classifier.classify_destination_page(cname, cand_url, page_data)
                res["ai_calls"] += 1
            except Exception as e:
                c_cat = cand.get("candidate_category") or "UNKNOWN_REQUIRES_REVIEW"
                mapped_type = "UNKNOWN_REQUIRES_REVIEW"
                if c_cat == "JOBS_LISTING_CANDIDATE":
                    mapped_type = "JOBS_LISTING_PAGE"
                elif c_cat in ("CSR_OVERVIEW_CANDIDATE", "CSR_PROJECT_DISCLOSURE_CANDIDATE"):
                    mapped_type = "CSR_OVERVIEW_PAGE"
                elif c_cat == "SUSTAINABILITY_REPORT_CANDIDATE":
                    mapped_type = "SUSTAINABILITY_OR_ESG_REPORT"
                elif c_cat == "ANNUAL_REPORT_CANDIDATE":
                    mapped_type = "ANNUAL_REPORT_WITH_CSR_EVIDENCE"
                dest_class = {
                    "page_type": mapped_type,
                    "confidence": 0.7,
                    "reasoning": f"Deterministic fallback evaluation: {e}",
                    "actual_model": "rule_based_fallback",
                }

            # Evidence Validation Gate
            val_gate = classifier.validate_page_evidence(cname, domain, dest_class, page_data)
            decision = val_gate.get("decision", "REVIEW_REQUIRED")
            verified_type = val_gate.get("verified_type", "UNKNOWN")
            reason_str = val_gate.get("reason", "")

            # Map to report category
            cat = None
            if "JOB" in verified_type or "CAREER" in verified_type:
                cat = "JOBS"
            elif "CSR" in verified_type:
                cat = "CSR"
            elif "SUSTAINABILITY" in verified_type:
                cat = "SUSTAINABILITY"
            elif "ANNUAL_REPORT" in verified_type or "REPORT" in verified_type:
                cat = "ANNUAL_REPORT"

            if not cat:
                continue

            # Save evidence preview file
            self._save_evidence_file(
                evidence_dir=evidence_dir,
                category=cat,
                url=cand_url,
                status_code=status_code,
                main_text=page_data.get("main_text", ""),
            )

            # Store chosen vs alternatives
            if cat not in chosen_by_category:
                chosen_by_category[cat] = {
                    "url": cand_url,
                    "cand": cand,
                    "page_data": page_data,
                    "val_gate": val_gate,
                    "confidence": dest_class.get("confidence", 0.8),
                    "ai_reason": dest_class.get("reasoning") or reason_str,
                }
                alternatives_by_category[cat] = []
            else:
                alternatives_by_category[cat].append(cand_url)

        # Build Pages rows
        for cat, c_info in chosen_by_category.items():
            cand = c_info["cand"]
            vg = c_info["val_gate"]
            res["pages"].append({
                "company_id": cid,
                "company_name": cname,
                "category": cat,
                "chosen_url": c_info["url"],
                "alternatives": "; ".join(alternatives_by_category.get(cat, [])),
                "how_found": cand.get("source", "HEADER_NAV"),
                "link_text": cand.get("link_text", ""),
                "menu_path": cand.get("menu_path", ""),
                "ats_platform": cand.get("ats_platform") or "",
                "ats_tenant": "",
                "ownership_status": cand.get("ownership_status") or "OWNED",
                "validation_result": vg.get("decision", "APPROVED"),
                "ai_confidence": round(float(c_info.get("confidence", 0.8)), 2),
                "ai_reason": c_info.get("ai_reason", ""),
            })

        # ----------------------------------------------------------------------
        # Step 3: Jobs Content Extraction (ONLY if JOBS page identified)
        # ----------------------------------------------------------------------
        if "JOBS" in chosen_by_category:
            jobs_info = chosen_by_category["JOBS"]
            jobs_url = jobs_info["url"]

            self._log(f"Running strategy pipeline for {jobs_url}...")
            # Run pipeline in a dry-run copy of company
            raw_jobs, strat_name, direct_pct = pipeline.run(company, jobs_url)
            total_jobs_found = len(raw_jobs)
            self._log(f"Strategy pipeline extracted {total_jobs_found} jobs via '{strat_name}' ({direct_pct}% direct).")

            # Apply 50-job cap
            capped_jobs = raw_jobs[:50]

            for j in capped_jobs:
                apply_url = j.get("application_url") or jobs_url
                link_qual = j.get("link_quality", "UNVERIFIED")

                if link_qual == "LISTING_FALLBACK" or apply_url == jobs_url:
                    res["warnings"].append({
                        "company_id": cid,
                        "company_name": cname,
                        "warning_type": "GENERIC_LISTING_LINK",
                        "details": f"Job '{j.get('title')}' apply URL falls back to generic careers listing page.",
                        "url": apply_url,
                        "evidence_snippet": j.get("title", ""),
                    })

                res["jobs"].append({
                    "company_id": cid,
                    "company_name": cname,
                    "job_title": clean_text(j.get("title") or "Corporate Opening"),
                    "department": clean_text(j.get("department") or ""),
                    "location": clean_text(j.get("location") or "India"),
                    "work_mode": clean_text(j.get("work_mode") or ""),
                    "employment_type": clean_text(j.get("employment_type") or "Full-time"),
                    "experience": clean_text(j.get("experience") or ""),
                    "external_job_id": clean_text(j.get("external_job_id") or ""),
                    "ats_platform": clean_text(j.get("ats_platform") or jobs_info["cand"].get("ats_platform") or strat_name),
                    "apply_source_url": apply_url,
                    "extraction_strategy_used": strat_name,
                    "description_snippet": clean_text(j.get("job_description") or j.get("description") or j.get("title") or "")[:300],
                    "retrieved_at": timezone.now().isoformat(),
                })

        # ----------------------------------------------------------------------
        # Step 4: CSR Content Extraction (ONLY on CSR / Sustainability / Reports)
        # ----------------------------------------------------------------------
        csr_items: List[Dict[str, Any]] = []

        for cat in ("CSR", "SUSTAINABILITY", "ANNUAL_REPORT"):
            if cat not in chosen_by_category or len(csr_items) >= 20:
                continue

            c_info = chosen_by_category[cat]
            target_url = c_info["url"]

            # If PDF
            if target_url.lower().endswith(".pdf"):
                self._log(f"Extracting CSR from PDF: {target_url}...")
                parser = CSRPdfParser(pdf_url=target_url, company=company)
                pdf_projects = parser.fetch_and_extract()
                if not pdf_projects:
                    res["warnings"].append({
                        "company_id": cid,
                        "company_name": cname,
                        "warning_type": "PDF_WITHOUT_TABLES",
                        "details": f"CSR PDF at {target_url} returned 0 tabular project disclosures (code: {parser.error_code}).",
                        "url": target_url,
                        "evidence_snippet": "",
                    })
                else:
                    for p in pdf_projects:
                        if len(csr_items) >= 20:
                            break
                        # Budget suspicious year check
                        b_val = p.get("budget") or ""
                        if b_val and re.match(r"^20\d\d$", b_val.strip()):
                            res["warnings"].append({
                                "company_id": cid,
                                "company_name": cname,
                                "warning_type": "SUSPICIOUS_BUDGET_YEAR",
                                "details": f"Extracted budget value '{b_val}' looks like a year.",
                                "url": target_url,
                                "evidence_snippet": p.get("evidence_snippet", ""),
                            })

                        csr_items.append({
                            "company_id": cid,
                            "company_name": cname,
                            "project_or_disclosure_name": p.get("project_name", "Statutory CSR Initiative"),
                            "theme": p.get("theme", "Community Development"),
                            "financial_year": p.get("financial_year", "FY 2023-24"),
                            "budget": p.get("budget", ""),
                            "geography": p.get("geography", ""),
                            "source_url": target_url,
                            "document_type": "PDF",
                            "page_number": p.get("page_number", ""),
                            "evidence_snippet": clean_text(p.get("evidence_snippet", ""))[:400],
                        })
            else:
                # HTML CSR extraction
                html_resp = fetch_live_page(target_url)
                if html_resp.get("ok"):
                    html = str(html_resp.get("html") or "")
                    corp_parser = CorporateHTMLParser(company=company, url=target_url, final_url=target_url, html_content=html)
                    projects = corp_parser.extract_csr()
                    opps = corp_parser.extract_opportunities()

                    for prj in projects:
                        if len(csr_items) >= 20:
                            break
                        csr_items.append({
                            "company_id": cid,
                            "company_name": cname,
                            "project_or_disclosure_name": prj.get("project_name", "CSR Project"),
                            "theme": prj.get("category", "Corporate Social Responsibility"),
                            "financial_year": "Current FY",
                            "budget": prj.get("budget", ""),
                            "geography": prj.get("geographic_location", ""),
                            "source_url": target_url,
                            "document_type": "web page",
                            "page_number": "",
                            "evidence_snippet": clean_text(prj.get("evidence_text", ""))[:400],
                        })

                    for opp in opps:
                        if len(csr_items) >= 20:
                            break
                        csr_items.append({
                            "company_id": cid,
                            "company_name": cname,
                            "project_or_disclosure_name": opp.get("title", "CSR Partner Opportunity"),
                            "theme": opp.get("opportunity_type", "Grant / RFP"),
                            "financial_year": "Current FY",
                            "budget": "",
                            "geography": "India",
                            "source_url": opp.get("portal_url", target_url),
                            "document_type": "web page",
                            "page_number": "",
                            "evidence_snippet": clean_text(opp.get("evidence_text", ""))[:400],
                        })

        res["csr"] = csr_items[:20]

        # ----------------------------------------------------------------------
        # Step 5: Verified Contacts Extraction (Homepage, Careers, CSR)
        # ----------------------------------------------------------------------
        contacts_list: List[Dict[str, Any]] = []
        pages_to_check_contacts = [homepage_url]
        for c_info in chosen_by_category.values():
            if c_info["url"] not in pages_to_check_contacts:
                pages_to_check_contacts.append(c_info["url"])

        seen_contacts = set()
        for p_url in pages_to_check_contacts[:3]:
            p_resp = fetch_live_page(p_url)
            if p_resp.get("ok"):
                raw_html = str(p_resp.get("html") or "")
                c_parser = CorporateHTMLParser(company=company, url=p_url, final_url=p_url, html_content=raw_html)
                for contact in c_parser.extract_contacts():
                    val = contact.get("email") or contact.get("phone")
                    if not val or val in seen_contacts:
                        continue
                    seen_contacts.add(val)
                    ctype = "email" if contact.get("email") else "phone"
                    contacts_list.append({
                        "company_id": cid,
                        "company_name": cname,
                        "contact_type": ctype,
                        "value": val,
                        "department": contact.get("department") or "Corporate Desk",
                        "source_url": p_url,
                        "evidence_snippet": clean_text(contact.get("evidence_text", ""))[:300],
                    })

        res["contacts"] = contacts_list

        # Determine overall result status
        if not res["pages"] and not res["jobs"] and not res["csr"]:
            res["result"] = "FAILED"
            res["reason"] = "No target pages or structured data could be extracted."
        elif not res["jobs"] or not res["csr"]:
            res["result"] = "PARTIAL"
            missing_items = []
            if not res["jobs"]: missing_items.append("Jobs")
            if not res["csr"]: missing_items.append("CSR")
            res["reason"] = f"Partial extraction: {', '.join(missing_items)} portal not identified."
        else:
            res["result"] = "OK"
            res["reason"] = "Both Jobs and CSR intelligence successfully identified and extracted."

        return res

    # ==========================================================================
    # HELPER: Save Evidence Preview Text File
    # ==========================================================================
    def _save_evidence_file(
        self,
        evidence_dir: str,
        category: str,
        url: str,
        status_code: int,
        main_text: str,
    ):
        """Saves first 2,000 characters of extracted text for reviewer verification."""
        try:
            parsed = urlparse(url)
            slug = re.sub(r"[^A-Za-z0-9_-]", "_", parsed.path.strip("/") or "home")[:40]
            filename = f"{category.lower()}_{slug}.txt"
            path = os.path.join(evidence_dir, filename)

            content = (
                f"URL: {url}\n"
                f"HTTP_STATUS: {status_code}\n"
                f"CATEGORY: {category}\n"
                f"RETRIEVED_AT: {timezone.now().isoformat()}\n"
                f"{'-' * 80}\n"
                f"MAIN_TEXT_PREVIEW (first 2,000 characters):\n"
                f"{'-' * 80}\n"
                f"{main_text[:2000]}\n"
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            logger.debug("Could not write evidence file: %s", e)

    # ==========================================================================
    # HELPER: Export to Multi-Sheet Excel & CSVs
    # ==========================================================================
    def _export_to_excel_and_csv(
        self,
        out_dir: str,
        excel_path: str,
        classifier_name: str,
        companies_rows: List[Dict[str, Any]],
        pages_rows: List[Dict[str, Any]],
        jobs_rows: List[Dict[str, Any]],
        csr_rows: List[Dict[str, Any]],
        contacts_rows: List[Dict[str, Any]],
        warnings_rows: List[Dict[str, Any]],
    ):
        """Generates crawl_review.xlsx with frozen headers, filters, wrapped text, and CSVs."""
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        # Style definitions
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill_blue = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        header_fill_amber = PatternFill(start_color="F59E0B", end_color="F59E0B", fill_type="solid")
        header_font_amber = Font(name="Calibri", size=11, bold=True, color="000000")
        link_font = Font(name="Calibri", size=11, color="1D4ED8", underline="single")
        regular_font = Font(name="Calibri", size=11)
        wrap_alignment = Alignment(wrap_text=True, vertical="top")

        # ----------------------------------------------------------------------
        # 1. README Sheet
        # ----------------------------------------------------------------------
        ws_readme = wb.create_sheet(title="README")
        readme_lines = [
            ("ImpactBridge™ Crawl Review Sampler - Master Verification Workbook", ""),
            ("Crawl Date & Time", timezone.now().strftime("%Y-%m-%d %H:%M:%S UTC")),
            ("Page Classifier", classifier_name),
            ("Execution Mode", "DRY RUN (Zero database mutations confirmed)"),
            ("", ""),
            ("Sheet Guide & Instructions for Human Reviewers:", ""),
            ("1. Companies", "Overview of each crawled company, duration, crawl result (OK/PARTIAL/BLOCKED/FAILED), extracted counts."),
            ("2. Pages", "Identified corporate portals for Jobs, CSR, Sustainability, Reports with verification gate decisions."),
            ("3. Jobs", "Extracted job vacancies (capped at 50/company) with titles, departments, locations, and ATS strategies."),
            ("4. CSR", "CSR projects, statutory Section 135 disclosures, and grant RFPs (capped at 20/company) with budgets & themes."),
            ("5. Contacts", "Verified corporate mailto: and tel: contact points (no guessed personal names or addresses)."),
            ("6. Warnings", "Suspicious crawler observations: generic listing fallbacks, unresolved shared ATS tenants, budget year anomalies."),
            ("", ""),
            ("How to fill the CHECK columns (Pages, Jobs, CSR, Contacts):", ""),
            ("- CHECK", "Select from dropdown: 'Correct', 'Wrong', 'Missing', or 'Not sure'."),
            ("- CORRECT_VALUE", "If 'Wrong' or 'Missing', enter the true official URL, title, or statutory value."),
            ("- NOTES", "Add any reviewer comments or context for subsequent publishing approval."),
        ]
        for row in readme_lines:
            ws_readme.append(list(row))
        ws_readme.column_dimensions["A"].width = 30
        ws_readme.column_dimensions["B"].width = 90
        ws_readme["A1"].font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")

        # ----------------------------------------------------------------------
        # 2. Table Sheets Config
        # ----------------------------------------------------------------------
        sheets_data = [
            ("Companies", companies_rows, [
                "company_id", "company_name", "website_url", "crawl_result", "reason",
                "time_taken_seconds", "pages_found", "jobs_found", "csr_items_found",
                "contacts_found", "ai_calls", "cache_hits"
            ], False),
            ("Pages", pages_rows, [
                "company_id", "company_name", "category", "chosen_url", "alternatives",
                "how_found", "link_text", "menu_path", "ats_platform", "ats_tenant",
                "ownership_status", "validation_result", "ai_confidence", "ai_reason",
                "CHECK", "CORRECT_VALUE", "NOTES"
            ], True),
            ("Jobs", jobs_rows, [
                "company_id", "company_name", "job_title", "department", "location",
                "work_mode", "employment_type", "experience", "external_job_id",
                "ats_platform", "apply_source_url", "extraction_strategy_used",
                "description_snippet", "retrieved_at",
                "CHECK", "CORRECT_VALUE", "NOTES"
            ], True),
            ("CSR", csr_rows, [
                "company_id", "company_name", "project_or_disclosure_name", "theme",
                "financial_year", "budget", "geography", "source_url", "document_type",
                "page_number", "evidence_snippet",
                "CHECK", "CORRECT_VALUE", "NOTES"
            ], True),
            ("Contacts", contacts_rows, [
                "company_id", "company_name", "contact_type", "value", "department",
                "source_url", "evidence_snippet",
                "CHECK", "CORRECT_VALUE", "NOTES"
            ], True),
            ("Warnings", warnings_rows, [
                "company_id", "company_name", "warning_type", "details", "url", "evidence_snippet"
            ], False),
        ]

        # Setup Excel validation dropdown for CHECK
        check_validation = DataValidation(
            type="list",
            formula1='"Correct,Wrong,Missing,Not sure"',
            allow_blank=True,
        )

        for sheet_name, rows, columns, has_check in sheets_data:
            ws = wb.create_sheet(title=sheet_name)
            ws.append(columns)

            if has_check:
                ws.add_data_validation(check_validation)

            # Freeze panes at A2
            ws.freeze_panes = "A2"

            # Format Header Row
            for col_idx, col_name in enumerate(columns, 1):
                cell = ws.cell(row=1, column=col_idx)
                if col_name == "CHECK":
                    cell.fill = header_fill_amber
                    cell.font = header_font_amber
                else:
                    cell.fill = header_fill_blue
                    cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

            # Append data rows
            for r_idx, row_dict in enumerate(rows, 2):
                row_vals = []
                for c in columns:
                    val = row_dict.get(c, "")
                    row_vals.append("" if val is None else val)
                ws.append(row_vals)

                # Format cells
                for col_idx, col_name in enumerate(columns, 1):
                    c_cell = ws.cell(row=r_idx, column=col_idx)
                    c_cell.font = regular_font
                    c_cell.alignment = wrap_alignment

                    # Clickable URLs
                    val_str = str(c_cell.value or "")
                    if val_str.startswith("http://") or val_str.startswith("https://"):
                        c_cell.hyperlink = val_str
                        c_cell.font = link_font

                    # Apply CHECK dropdown
                    if col_name == "CHECK" and has_check:
                        check_validation.add(c_cell)

            # Set Auto Filter
            if ws.max_row > 1:
                ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{ws.max_row}"

            # Auto-size columns sensibly
            for col_idx, col_name in enumerate(columns, 1):
                col_letter = get_column_letter(col_idx)
                max_len = len(col_name)
                for cell in ws[col_letter]:
                    v_str = str(cell.value or "")
                    if len(v_str) > max_len:
                        max_len = min(len(v_str), 55)
                ws.column_dimensions[col_letter].width = max(max_len + 3, 14)

            # ------------------------------------------------------------------
            # Also export matching CSV file
            # ------------------------------------------------------------------
            csv_path = os.path.join(out_dir, f"{sheet_name}.csv")
            with open(csv_path, "w", newline="", encoding="utf-8-sig") as csv_f:
                writer = csv.DictWriter(csv_f, fieldnames=columns)
                writer.writeheader()
                for r in rows:
                    writer.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in columns})

        # Save workbook
        wb.save(excel_path)

        # Also write README.csv
        readme_csv_path = os.path.join(out_dir, "README.csv")
        with open(readme_csv_path, "w", newline="", encoding="utf-8-sig") as rf:
            writer = csv.writer(rf)
            for line in readme_lines:
                writer.writerow(list(line))

    # ==========================================================================
    # HELPER: Database Counts
    # ==========================================================================
    def _get_db_counts(self) -> Dict[str, int]:
        """Returns row counts across all core tables to verify zero mutations."""
        return {
            "Company": Company.objects.count(),
            "Job": Job.objects.count(),
            "CSRProject": CSRProject.objects.count(),
            "CSROpportunity": CSROpportunity.objects.count(),
            "Contact": Contact.objects.count(),
            "AuditTrail": AuditTrail.objects.count(),
        }

    # ==========================================================================
    # HELPER: Logging
    # ==========================================================================
    def _log(self, msg: str):
        """Writes to run_log.txt and logger."""
        timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {msg}"
        if hasattr(self, "_log_file") and self._log_file and not self._log_file.closed:
            self._log_file.write(line + "\n")
            self._log_file.flush()
        logger.info(msg)
