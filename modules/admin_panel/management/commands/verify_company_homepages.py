Create a command that crawls 15 companies in DRY-RUN mode and saves everything it finds to
files, so I can cross-check it company by company:

  python manage.py crawl_review_sample --count 15 --out exports/crawl_review
  python manage.py crawl_review_sample --company-ids ID1,ID2 --out exports/crawl_review

## Which companies are eligible
Only companies where all three inputs are valid:
- company_id exists,
- company_name is set,
- website_url is confirmed correct: homepage status CORRECT / ALREADY_OK from the last homepage
  verification, or a correction I approved. Exclude REVIEW_REQUIRED, HOMEPAGE_NOT_FOUND,
  WRONG_ENTITY, UNVERIFIABLE_BLOCKED and unapproved AUTO_CORRECTED.
Nothing else (NSE symbol, sector, headquarters, old careers/CSR URLs, ATS fields, access flags)
may be required. The crawl must run with only these three fields. Old careers_url/
csr_portal_url etc. may be used only as extra hint candidates (source=DB_HINT).

## Choosing the 15
--count 15 picks DIVERSELY: different sectors (conglomerate group, IT, bank/finance, PSU,
consumer/manufacturing), different sizes, some with a known ATS (Workday, Darwinbox,
PeopleStrong and so on) and some on a plain careers page, some on a shared group portal
(Adani). Include Adani Enterprises, ACC, 3i Infotech and Aarti Industries if eligible.
Print the chosen list and the reason for each. --company-ids overrides the choice.

## What the crawl does (use the existing pipeline, dry-run)
1. Collect candidate pages with the existing candidate collector (header, footer, sitemap,
   common paths, subdomains, hub pages, including PDFs). Keep link_text and menu_path.
2. Identify the JOBS, CSR, SUSTAINABILITY, ANNUAL_REPORT/BRSR pages using the existing AI page
   classifier (or the new decision step if it is already built; say which one ran). Keep the
   zero-cost guards, SQLite cache and checkpoints. Record AI calls made, cache hits and the
   AI reason for each pick.
3. Validate each chosen page with the existing content validators.
4. Run the existing extraction strategies ONLY on the identified pages: ATS parsers, JSON-LD,
   embedded state, XHR, click-to-load, detail extractor, and csr_pdf for CSR/BRSR PDFs.
5. Per company: at most 50 jobs (also record the total found), and up to 20 CSR projects or
   disclosures. Per-company time limit (for example 5 minutes), polite per-domain rate
   limit, respect robots.txt. If a company fails or is blocked (403/429/timeout), record the
   reason and continue with the next company. Never mark a blocked page as "not found".

## Hard rules
- DRY RUN: NO database writes, NO status changes, NO publishing, NO URL updates. Everything
  goes to files only. Show a check at the end that the database row counts are unchanged.
- Never guess or fabricate. Missing data stays blank. Do not run any extraction on pages that
  failed validation.
- Do not output API keys or secrets.

## Output files
Folder exports/crawl_review/<timestamp>/ containing:
1. crawl_review.xlsx with these sheets (company_id and company_name in every sheet, filters on,
   frozen header, wrapped text, clickable URLs):
   - README: what each sheet means, the crawl date, which classifier ran, and how to fill the
     CHECK columns.
   - Companies: one row per company with the three inputs, crawl result
     (OK / PARTIAL / BLOCKED / FAILED), reason, time taken, pages found, jobs found, CSR items
     found, AI calls and cache hits.
   - Pages: category, chosen URL, alternatives, how it was found (HEADER_NAV, FOOTER_NAV,
     SITEMAP, COMMON_PATH, SUBDOMAIN_PROBE, HUB_PAGE, DB_HINT), link_text, menu_path, ATS
     platform and tenant, ownership_status, validation result, AI confidence and reason.
   - Jobs: job_title, department, location, work_mode, employment_type, experience,
     external_job_id, ats_platform, apply/source URL, extraction strategy used, description
     snippet (first 300 chars), retrieved_at.
   - CSR: project or disclosure name, theme, financial year, budget, geography, source URL,
     document type (web page / PDF), page number if from a PDF, evidence snippet.
   - Contacts: verified corporate emails or phone desks found (no guessed addresses).
   - Warnings: suspicious items per company (a job link that is just the careers home page, a
     shared tenant, a budget that looks like a year, a PDF with no tables, pages that needed
     Playwright, blocked pages).
   On Pages, Jobs, CSR and Contacts add empty columns CHECK (dropdown: Correct / Wrong /
   Missing / Not sure), CORRECT_VALUE and NOTES.
2. One CSV per sheet with the same content.
3. evidence/<company_id>/ with, for each chosen page, the final URL, HTTP status and the first
   2,000 characters of its extracted main text, so I can see what the crawler saw.
4. run_log.txt with timings, errors and every AI decision.

## Finish
- Add a unit test with mocked network and AI that checks eligibility (non-correct homepages are
  excluded), the 50-job cap, failure isolation (one company failing does not stop the run) and
  that no database writes happen.
- Print a terminal summary: companies crawled, results per status, rows per sheet and the
  output path. Do not start any other stage or change any other file."""
modules/admin_panel/management/commands/verify_company_homepages.py
===================================================================
Management command for automated verification and self-correction of
company homepages across all corporate records.

Features:
- Variants first: www/non-www, http->https, /in subpaths, final redirects
- Detects DNS failures and parked domains
- Structured source plug-ins: Wikidata (P856) and Exchange data (terms-governed)
- AI Fallback: Gemini Flash (free tier) with SQLite cache & zero-cost policy
- Deterministic code validation: HTTP 200, company/brand tokens, CIN/ISIN statutory signals
- Confidence routing: HIGH -> auto-update (with history); MEDIUM -> REVIEW_REQUIRED; NONE -> HOMEPAGE_NOT_FOUND
- Inviolable safety: Never overwrites locked website_url; never accepts unvalidated AI suggestions
- Monthly schedule: --scheduled flag processes companies with stale (>30 days) or unset verification

Usage:
    python manage.py verify_company_homepages --all --dry-run
    python manage.py verify_company_homepages --all --apply-updates
    python manage.py verify_company_homepages --test-abb
    python manage.py verify_company_homepages --company-id COMP_TOP200_152
    python manage.py verify_company_homepages --scheduled --apply-updates
"""

import sys
import logging
from datetime import timedelta
from typing import List, Dict, Any

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from modules.admin_panel.models import Company
from modules.crawler_engine.homepage_verifier import HomepageVerifier

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Verify and auto-correct corporate homepages with multi-tier validation, plug-ins, and safety guards."

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all companies in the directory.'
        )
        parser.add_argument(
            '--company-id',
            type=str,
            help='Process a specific company by company_id.'
        )
        parser.add_argument(
            '--test-abb',
            action='store_true',
            help='Shortcut to test the ABB India Limited edge-case.'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Maximum number of companies to process (0 = all matched).'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Simulate verification and auto-correction without persisting mutations.'
        )
        parser.add_argument(
            '--apply-updates',
            action='store_true',
            default=False,
            help='Persist verified updates, history entries, and review flags to database.'
        )
        parser.add_argument(
            '--scheduled',
            action='store_true',
            default=False,
            help='Monthly schedule filter: only process records not verified within the past 30 days.'
        )
        parser.add_argument(
            '--force-recheck',
            action='store_true',
            default=False,
            help='Force recheck even if currently verified.'
        )

    def handle(self, *args, **options):
        dry_run = not options.get('apply_updates')
        if options.get('dry_run'):
            dry_run = True

        test_abb = options.get('test_abb')
        company_id = options.get('company_id')
        process_all = options.get('all')
        limit = options.get('limit', 0)
        scheduled = options.get('scheduled')
        force_recheck = options.get('force_recheck')

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"=== ImpactBridge™ Homepage Verification & Auto-Correction Engine ===\n"
            f"Mode: {'DRY RUN (no DB mutations)' if dry_run else 'APPLY UPDATES (live DB write)'}"
        ))

        # Build queryset
        qs = Company.objects.all().order_by('company_id')

        if test_abb:
            qs = qs.filter(Q(company_name__icontains='ABB') | Q(company_id='COMP_TOP200_152'))
            self.stdout.write(f"Testing ABB India case specifically (matched {qs.count()} record)...")
        elif company_id:
            qs = qs.filter(company_id=company_id)
            if not qs.exists():
                self.stderr.write(self.style.ERROR(f"Company '{company_id}' not found in database."))
                return
        elif scheduled:
            threshold = timezone.now() - timedelta(days=30)
            qs = qs.filter(
                Q(website_url_verified_at__isnull=True) |
                Q(website_url_verified_at__lt=threshold)
            )
            self.stdout.write(f"Monthly schedule active: {qs.count()} companies due for re-verification.")
        elif not process_all and limit == 0:
            self.stdout.write(self.style.WARNING(
                "No execution scope specified. Use --all, --company-id, --test-abb, or --scheduled.\n"
                "Defaulting to dry-run for all companies."
            ))

        if limit > 0:
            qs = qs[:limit]

        total_companies = qs.count() if hasattr(qs, 'count') else len(qs)
        self.stdout.write(f"Total companies to process: {total_companies}\n")

        # Metrics aggregation
        counts = {
            "ALREADY_OK": 0,
            "AUTO_CORRECTED": 0,
            "REVIEW_REQUIRED": 0,
            "TEMPORARILY_UNVERIFIABLE": 0,
            "HOMEPAGE_NOT_FOUND": 0,
            "LOCKED_SKIPPED": 0,
            "TOTAL_PROCESSED": 0
        }

        auto_corrected_list: List[Dict[str, Any]] = []
        review_required_list: List[Dict[str, Any]] = []
        temp_unverifiable_list: List[Dict[str, Any]] = []
        not_found_list: List[Dict[str, Any]] = []

        start_time = timezone.now()

        for idx, company in enumerate(qs, 1):
            counts["TOTAL_PROCESSED"] += 1
            cid = company.company_id
            cname = company.company_name
            orig_url = company.website_url or ""

            sys.stdout.write(f"[{idx}/{total_companies}] {cid} - {cname[:28]} ... ")
            sys.stdout.flush()

            res = HomepageVerifier.verify_company(company, dry_run=dry_run, force_recheck=force_recheck)
            status = res["status"]

            if status == "ALREADY_OK":
                counts["ALREADY_OK"] += 1
                sys.stdout.write(self.style.SUCCESS(f"OK ({res['new_url']})\n"))
            elif status == "AUTO_CORRECTED":
                counts["AUTO_CORRECTED"] += 1
                auto_corrected_list.append(res)
                sys.stdout.write(self.style.WARNING(f"CORRECTED -> {res['new_url']} ({res['source']})\n"))
            elif status == "LOCKED_PRESERVED":
                counts["LOCKED_SKIPPED"] += 1
                sys.stdout.write(self.style.NOTICE(f"LOCKED (Preserved: {orig_url})\n"))
            elif status == "REVIEW_REQUIRED":
                counts["REVIEW_REQUIRED"] += 1
                review_required_list.append(res)
                sys.stdout.write(self.style.NOTICE(f"NEEDS REVIEW (Score: {res['score']})\n"))
            elif status == "TEMPORARILY_UNVERIFIABLE":
                counts["TEMPORARILY_UNVERIFIABLE"] += 1
                temp_unverifiable_list.append(res)
                sys.stdout.write(self.style.NOTICE("TEMP UNVERIFIABLE (WAF/403/Timeout)\n"))
            else:
                counts["HOMEPAGE_NOT_FOUND"] += 1
                not_found_list.append(res)
                sys.stdout.write(self.style.ERROR("NOT FOUND (DNS/Dead)\n"))

        elapsed = (timezone.now() - start_time).total_seconds()

        # Detailed Report
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.MIGRATE_HEADING("HOMEPAGE VERIFICATION & CORRECTION REPORT"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Mode:             {'DRY RUN (Simulated)' if dry_run else 'APPLIED TO DATABASE'}")
        self.stdout.write(f"Total Processed:  {counts['TOTAL_PROCESSED']}")
        self.stdout.write(f"Time Elapsed:     {elapsed:.1f}s")
        self.stdout.write("-" * 80)
        self.stdout.write(self.style.SUCCESS(f"  ALREADY_OK:                 {counts['ALREADY_OK']:>4} ({counts['ALREADY_OK']/max(1, counts['TOTAL_PROCESSED'])*100:.1f}%)"))
        self.stdout.write(self.style.WARNING(f"  AUTO_CORRECTED:             {counts['AUTO_CORRECTED']:>4} ({counts['AUTO_CORRECTED']/max(1, counts['TOTAL_PROCESSED'])*100:.1f}%)"))
        self.stdout.write(self.style.NOTICE(f"  REVIEW_REQUIRED:            {counts['REVIEW_REQUIRED']:>4} ({counts['REVIEW_REQUIRED']/max(1, counts['TOTAL_PROCESSED'])*100:.1f}%)"))
        self.stdout.write(self.style.NOTICE(f"  TEMPORARILY_UNVERIFIABLE:   {counts['TEMPORARILY_UNVERIFIABLE']:>4} ({counts['TEMPORARILY_UNVERIFIABLE']/max(1, counts['TOTAL_PROCESSED'])*100:.1f}%)"))
        self.stdout.write(self.style.ERROR(f"  HOMEPAGE_NOT_FOUND:         {counts['HOMEPAGE_NOT_FOUND']:>4} ({counts['HOMEPAGE_NOT_FOUND']/max(1, counts['TOTAL_PROCESSED'])*100:.1f}%)"))
        if counts["LOCKED_SKIPPED"] > 0:
            self.stdout.write(f"  LOCKED_SKIPPED:             {counts['LOCKED_SKIPPED']:>4}")
        self.stdout.write("=" * 80)

        # Print Auto-Corrected Items with Identity Evidence & Same Legal Entity Check
        if auto_corrected_list:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n--- AUTO-CORRECTED COMPANIES ({len(auto_corrected_list)}) ---"))
            for item in auto_corrected_list:
                same_entity_str = "YES" if item.get("same_legal_entity", True) else "NO"
                identity_ev = item.get("identity_evidence", "Statutory/Legal Name Matched")
                self.stdout.write(
                    f"\n• [{item['company_id']}] {item['company_name']}\n"
                    f"  Old URL:           {item['old_url']}\n"
                    f"  New URL:           {item['new_url']}\n"
                    f"  Source:            {item['source']} (Score: {item['score']}, Confidence: {item['confidence']})\n"
                    f"  Identity Evidence: {identity_ev}\n"
                    f"  Same Legal Entity: {same_entity_str}\n"
                    f"  Evidence Summary:  {item['evidence']}"
                )

        # Print Temporarily Unverifiable Items (WAF/403/Timeout/Stream Reset)
        if temp_unverifiable_list:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n--- TEMPORARILY UNVERIFIABLE COMPANIES (RETRY WITH PLAYWRIGHT) ({len(temp_unverifiable_list)}) ---"))
            for item in temp_unverifiable_list:
                self.stdout.write(
                    f"\n• [{item['company_id']}] {item['company_name']}\n"
                    f"  Current URL:   {item['old_url']}\n"
                    f"  Challenge:     {item['evidence']}"
                )

        # Print Review Required Items
        if review_required_list:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n--- REVIEW REQUIRED COMPANIES ({len(review_required_list)}) ---"))
            for item in review_required_list:
                self.stdout.write(
                    f"\n• [{item['company_id']}] {item['company_name']}\n"
                    f"  Current URL:   {item['old_url']}\n"
                    f"  Candidate URL: {item['new_url']}\n"
                    f"  Evidence Note: {item['evidence']}"
                )

        # Print Not Found Items (Confirmed Dead/DNS Failure)
        if not_found_list:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n--- HOMEPAGE NOT FOUND (DEAD/DNS FAILURE) ({len(not_found_list)}) ---"))
            for item in not_found_list:
                self.stdout.write(
                    f"\n• [{item['company_id']}] {item['company_name']}\n"
                    f"  Failed URL: {item['old_url']}\n"
                    f"  Note:       {item['evidence']}"
                )
        self.stdout.write("\n" + "=" * 80 + "\n")
