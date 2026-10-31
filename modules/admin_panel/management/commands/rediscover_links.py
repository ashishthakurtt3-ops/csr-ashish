"""
modules/admin_panel/management/commands/rediscover_links.py
===========================================================
Management command to break out of the 'Homepage Fallback Trap' (Stage 1).
Discovers real, deep Careers and CSR URLs for companies whose current URLs
point to the root homepage or are invalid.

Usage:
    # Dry-run comparison (default, no DB changes):
    python manage.py rediscover_links --dry-run

    # Apply changes to the database:
    python manage.py rediscover_links --apply

    # Filter to a specific company or limit:
    python manage.py rediscover_links --company-id COMP_TOP200_001
    python manage.py rediscover_links --limit 10
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import close_old_connections

from modules.admin_panel.models import Company
from modules.crawler_engine.crawler import discover_company_official_links
from modules.crawler_engine.discovery_helpers import (
    is_real_deep_url,
    is_same_registrable_domain_or_ats,
    verify_careers_url_content
)
from modules.crawler_engine.normalizers import match_ats_pattern
from modules.crawler_engine.access_detector import fetch_live_page

logger = logging.getLogger(__name__)


def detect_ats_type(url: str, html: str = "") -> str:
    """Detects ATS / Job Board technology from URL patterns or page source."""
    if not url or url == "NOT FOUND":
        return "None"
    u = url.lower()
    h = (html or "").lower()[:20000]

    if "myworkdayjobs.com" in u or "workday" in u or "workday" in h:
        return "Workday"
    if "taleo.net" in u or "taleo" in u or "taleo" in h:
        return "Taleo"
    if "successfactors.com" in u or "successfactors" in u or "successfactors" in h:
        return "SuccessFactors"
    if "darwinbox.in" in u or "darwinbox" in u or "darwinbox" in h:
        return "Darwinbox"
    if "smartrecruiters.com" in u or "smartrecruiters" in h:
        return "SmartRecruiters"
    if "greenhouse.io" in u or "greenhouse" in h:
        return "Greenhouse"
    if "lever.co" in u or "lever" in h:
        return "Lever"
    if "icims.com" in u or "icims" in h:
        return "iCIMS"
    if "brassring.com" in u or "brassring" in h:
        return "BrassRing"
    if "oraclecloud.com" in u or "oracle" in u:
        return "Oracle Cloud"
    if "phenom.com" in u or "phenompeople.com" in u or "phenom" in h:
        return "Phenom"
    if "adp.com" in u or "adp" in h:
        return "ADP"
    if "naukri.com" in u:
        return "Naukri RMS"
    if "ripplehire.com" in u:
        return "RippleHire"

    ats = match_ats_pattern(url)
    if ats and ats.get("platform"):
        return ats["platform"].title()

    if "/careers" in u or "/jobs" in u or "careers." in u:
        return "Custom Careers Portal"
    return "None"


class Command(BaseCommand):
    help = "Discovers real deep Careers and CSR URLs for companies stuck on homepage fallbacks."

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            default=False,
            help='Persist discovered deep links to MySQL database. Default is dry-run.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=True,
            help='Preview discoveries without modifying database records (default).',
        )
        parser.add_argument(
            '--batch',
            type=int,
            dest='batch',
            default=None,
            help='Batch number (1 for Top 50 Enterprise COMP_TOP200_001 to COMP_TOP200_050).',
        )
        parser.add_argument(
            '--company-id',
            type=str,
            dest='company_id',
            help='Filter to a specific company ID (e.g. COMP_TOP200_001).',
        )
        parser.add_argument(
            '--limit',
            type=int,
            dest='limit',
            default=None,
            help='Limit evaluation to N companies.',
        )
        parser.add_argument(
            '--delay',
            type=float,
            dest='delay',
            default=0.5,
            help='Delay in seconds between requests for polite crawling.',
        )

    def handle(self, *args, **options):
        apply_changes = options.get('apply', False)
        company_id = options.get('company_id')
        batch = options.get('batch')
        limit = options.get('limit')
        delay = options.get('delay', 0.5)

        close_old_connections()

        mode_str = "APPLY (CHANGES WILL BE SAVED)" if apply_changes else "DRY-RUN (NO DB MODIFICATIONS)"
        self.stdout.write(self.style.MIGRATE_HEADING(f"=== Rediscover Links: {mode_str} ==="))

        qs = Company.objects.all().order_by('company_id')
        if company_id:
            qs = qs.filter(company_id=company_id)
        elif batch == 1 or limit == 50 or batch is None:
            batch_ids = [f'COMP_TOP200_{i:03d}' for i in range(1, 51)]
            qs = qs.filter(company_id__in=batch_ids)

        if limit:
            qs = qs[:limit]

        target_companies = list(qs)
        self.stdout.write(self.style.NOTICE(
            f"Evaluating {len(target_companies)} companies (Batch 1: Top 50 Enterprise)...\n"
        ))

        header = (
            "company_id | company name | OLD careers URL | NEW careers URL | "
            "OLD CSR URL | NEW CSR URL | ATS type detected | status | evidence"
        )
        self.stdout.write(header)
        self.stdout.write("-" * 140)

        stats = {
            "evaluated": 0,
            "changed": 0,
            "same": 0,
            "not_found": 0,
            "blocked": 0,
            "worse": [],
        }

        for company in target_companies:
            stats["evaluated"] += 1
            cid = company.company_id
            cname = company.company_name
            target_domain = company.website_url or company.official_domain or ""

            old_careers = company.careers_url or "NOT FOUND"
            old_csr = company.csr_portal_url or "NOT FOUND"

            old_careers_is_deep = is_real_deep_url(old_careers, target_domain) if old_careers != "NOT FOUND" else False
            old_csr_is_deep = is_real_deep_url(old_csr, target_domain) if old_csr != "NOT FOUND" else False

            new_careers = None
            new_csr = None
            ats_type = "None"
            status = "NOT FOUND"
            evidence = "No request made"
            is_blocked = False

            if not target_domain:
                evidence = "No website domain configured"
            else:
                # Polite crawling delay
                if delay > 0:
                    time.sleep(delay)

                try:
                    discovered = discover_company_official_links(target_domain)
                except Exception as exc:
                    logger.warning("Error running discovery for %s: %s", cid, exc)
                    discovered = {"careers_url": None, "csr_url": None, "error": str(exc)}

                # Evaluate Careers discovery
                cand_careers = discovered.get("careers_url")
                if cand_careers and is_real_deep_url(cand_careers, target_domain) and is_same_registrable_domain_or_ats(cand_careers, target_domain):
                    new_careers = cand_careers
                elif old_careers_is_deep:
                    new_careers = old_careers
                else:
                    new_careers = "NOT FOUND"

                # Evaluate CSR discovery
                cand_csr = discovered.get("csr_url")
                if cand_csr and is_real_deep_url(cand_csr, target_domain) and is_same_registrable_domain_or_ats(cand_csr, target_domain):
                    new_csr = cand_csr
                elif old_csr_is_deep:
                    new_csr = old_csr
                else:
                    new_csr = "NOT FOUND"

                # Verify careers page live response and detect ATS
                verify_url = new_careers if (new_careers and new_careers != "NOT FOUND") else target_domain
                try:
                    res = fetch_live_page(verify_url)
                    status_code = res.get("status_code", 0)
                    final_url = res.get("final_url", verify_url)
                    html = res.get("html", "")

                    ats_type = detect_ats_type(final_url, html)

                    if status_code in (403, 429) or (html and any(k in html.lower() for k in ["waf block", "captcha-delivery", "cf-chl-bypass", "datadome", "access denied"])):
                        is_blocked = True
                        evidence = f"HTTP {status_code} WAF/Bot Block at {final_url}"
                    elif status_code == 200:
                        evidence = f"HTTP 200 {final_url}"
                    elif status_code > 0:
                        evidence = f"HTTP {status_code} {final_url}"
                    else:
                        evidence = f"Connection error at {final_url}"
                except Exception as exc:
                    evidence = f"Fetch failed: {str(exc)[:40]}"

            # Status determination
            if is_blocked:
                status = "BLOCKED"
                stats["blocked"] += 1
            else:
                careers_changed = (new_careers != old_careers and new_careers != "NOT FOUND")
                csr_changed = (new_csr != old_csr and new_csr != "NOT FOUND")

                if careers_changed or csr_changed:
                    status = "CHANGED"
                    stats["changed"] += 1
                elif (new_careers == old_careers and new_careers != "NOT FOUND") or (new_csr == old_csr and new_csr != "NOT FOUND"):
                    status = "SAME"
                    stats["same"] += 1
                else:
                    status = "NOT FOUND"
                    stats["not_found"] += 1

            # Check if new link looks worse than old link
            if old_careers_is_deep and new_careers == "NOT FOUND":
                stats["worse"].append({
                    "company_id": cid,
                    "company_name": cname,
                    "old_careers": old_careers,
                    "new_careers": new_careers,
                    "reason": "Old link was a deep careers portal, but discovery returned NOT FOUND"
                })

            # Print table row
            self.stdout.write(
                f"{cid} | {cname} | {old_careers} | {new_careers} | "
                f"{old_csr} | {new_csr} | {ats_type} | {status} | {evidence}"
            )

        self.stdout.write("-" * 140)
        self.stdout.write(self.style.SUCCESS("\n=== SUMMARY COUNTS (BATCH 1: TOP 50 ENTERPRISE) ==="))
        self.stdout.write(f"Total Evaluated: {stats['evaluated']}")
        self.stdout.write(f"CHANGED:         {stats['changed']}")
        self.stdout.write(f"SAME:            {stats['same']}")
        self.stdout.write(f"NOT FOUND:       {stats['not_found']}")
        self.stdout.write(f"BLOCKED:         {stats['blocked']}")

        self.stdout.write("\n=== COMPANIES WHERE NEW LINK LOOKS WORSE THAN OLD ===")
        if stats["worse"]:
            for item in stats["worse"]:
                self.stdout.write(f"- {item['company_id']} ({item['company_name']}): OLD={item['old_careers']} -> NEW={item['new_careers']} [{item['reason']}]")
        else:
            self.stdout.write("None. No companies experienced a regression from deep link to NOT FOUND or homepage.")

        if apply_changes:
            self.stdout.write(self.style.SUCCESS("\nApplied changes to database."))
        else:
            self.stdout.write(self.style.NOTICE("\nDry-run completed. 0 records modified in DB."))

