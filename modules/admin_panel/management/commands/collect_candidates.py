"""
modules/admin_panel/management/commands/collect_candidates.py
=============================================================
Runs rules-based candidate link collection (Stage 1) against real corporate websites.

Usage:
    python manage.py collect_candidates --company-id COMP_TOP200_169
    python manage.py collect_candidates --company "ACC Limited" --dry-run
    python manage.py collect_candidates --url https://www.adanienterprises.com --dry-run
    python manage.py collect_candidates --company-id COMP_TOP200_017 --show-dropped
"""
from __future__ import annotations

import sys
from typing import List, Dict, Any, Optional
from django.core.management.base import BaseCommand
from django.db.models import Q

from modules.admin_panel.models.company import Company
from modules.crawler_engine.candidate_collector import CandidateCollector
from modules.crawler_engine import ai_classifier_config as cfg


def _safe_text(val: Any) -> str:
    """Sanitizes text for console stdout encoding (avoids cp1252 charmap crashes)."""
    if val is None:
        return ""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        return str(val).encode(encoding, errors="replace").decode(encoding)
    except Exception:
        return str(val).encode("ascii", errors="replace").decode("ascii")


class Command(BaseCommand):
    help = "Run rules-based candidate link collector on company websites and print numbered candidate list."

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=str, help="Company ID (e.g. COMP_TOP200_169)")
        parser.add_argument("--company", type=str, help="Company name or symbol (e.g. ACC, Adani)")
        parser.add_argument("--url", type=str, help="Direct homepage URL to test (overrides company record)")
        parser.add_argument("--limit", type=int, default=getattr(cfg, "CANDIDATE_MAX_CAP", 50), help="Max candidate limit")
        parser.add_argument("--dry-run", action="store_true", default=True, help="Run without database writes (default: True)")
        parser.add_argument("--show-dropped", action="store_true", help="Print dropped candidates if cap was reached")
        parser.add_argument("--no-playwright", action="store_true", help="Disable Playwright headless fallback")
        parser.add_argument("--no-probes", action="store_true", help="Disable common path and subdomain probes")

    def handle(self, *args, **options):
        company_id = options.get("company_id")
        company_query = options.get("company")
        direct_url = options.get("url")
        limit = options.get("limit") or 50
        show_dropped = options.get("show_dropped", False)
        allow_playwright = not options.get("no_playwright", False)
        enable_probes = not options.get("no_probes", False)

        target_companies: List[Dict[str, Any]] = []

        if direct_url:
            target_companies.append({
                "company_id": "CUSTOM_URL",
                "company_name": "Direct URL Target",
                "symbol": None,
                "website_url": direct_url,
                "extra_allowed_domains": [],
            })
        elif company_id or company_query:
            q = Q()
            if company_id:
                q |= Q(company_id=company_id)
            if company_query:
                q |= Q(company_name__icontains=company_query) | Q(nse_symbol__iexact=company_query)

            comps = Company.objects.filter(q)
            if not comps.exists():
                self.stderr.write(self.style.ERROR(f"No company found matching id='{company_id}' or query='{company_query}'."))
                return

            for c in comps:
                target_companies.append({
                    "company_id": c.company_id,
                    "company_name": c.company_name,
                    "symbol": c.nse_symbol,
                    "website_url": c.website_url,
                    "extra_allowed_domains": [c.official_domain] if c.official_domain else [],
                })
        else:
            self.stdout.write(self.style.WARNING("No --company-id or --url specified. Selecting first 5 companies with website_url."))
            comps = Company.objects.filter(website_url__isnull=False).exclude(website_url="")[:5]
            for c in comps:
                target_companies.append({
                    "company_id": c.company_id,
                    "company_name": c.company_name,
                    "symbol": c.nse_symbol,
                    "website_url": c.website_url,
                    "extra_allowed_domains": [c.official_domain] if c.official_domain else [],
                })

        collector = CandidateCollector(
            allow_playwright=allow_playwright,
            probe_sitemaps=enable_probes,
            probe_subdomains=enable_probes,
            probe_common_paths=enable_probes,
            probe_live=enable_probes,
            max_cap=limit,
        )

        for target in target_companies:
            self._process_single_company(collector, target, limit, show_dropped)

    def _process_single_company(
        self,
        collector: CandidateCollector,
        target: Dict[str, Any],
        limit: int,
        show_dropped: bool
    ):
        name = target["company_name"]
        cid = target["company_id"]
        url = target["website_url"]
        symbol = target["symbol"]

        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS(f"Target Company: {name} [{cid}]"))
        self.stdout.write(f"Homepage URL: {url} | Symbol: {symbol or 'N/A'}")
        self.stdout.write("-" * 80)

        if not url:
            self.stdout.write(self.style.WARNING("No website_url available. Skipping."))
            return

        candidates = collector.collect_candidates(
            homepage_url=url,
            company_symbol=symbol,
            extra_allowed_domains=target.get("extra_allowed_domains"),
            max_candidates=limit,
        )

        self.stdout.write(f"Total Valid Candidates Retained: {len(candidates)} (Cap: {limit})")
        self.stdout.write("-" * 80)

        careers_found: List[str] = []
        csr_found: List[str] = []
        ats_found: List[str] = []
        pdf_found: List[str] = []

        for cand in candidates:
            cid_num = cand["id"]
            c_url = cand["url"]
            text = cand.get("link_text") or ""
            menu = cand.get("menu_path") or ""
            source = cand.get("source") or ""
            ats = cand.get("ats_match", False)
            plat = cand.get("ats_platform") or ""
            req_verif = cand.get("requires_owner_verification", False)
            ext_linked = cand.get("external_linked", False)

            # Classify signals for summary
            low_comb = f"{c_url} {text} {menu}".lower()
            if any(k in low_comb for k in ("career", "job", "join us", "work with us", "opening", "vacancy")):
                careers_found.append(c_url)
            if any(k in low_comb for k in ("csr", "foundation", "sustainab", "esg", "social impact", "annual report", "brsr")):
                csr_found.append(c_url)
            if ats:
                ats_found.append(f"{c_url} ({plat})")
            if c_url.lower().endswith(".pdf"):
                pdf_found.append(c_url)

            flags = []
            if ats:
                flags.append(f"ATS:{plat}")
            if req_verif:
                flags.append("OWNER_UNRESOLVED")
            if ext_linked:
                flags.append("EXT_NAV")
            if c_url.lower().endswith(".pdf"):
                flags.append("PDF")

            flag_str = f" [{', '.join(flags)}]" if flags else ""

            safe_text = _safe_text(text)
            safe_menu = _safe_text(menu)

            self.stdout.write(
                f"[{cid_num:02d}] {c_url}{flag_str}\n"
                f"     link_text: {safe_text!r}\n"
                f"     menu_path: {safe_menu!r}\n"
                f"     source:    {source}"
            )

        # Dropped candidates
        if collector.dropped_candidates and show_dropped:
            self.stdout.write("\n" + "." * 80)
            self.stdout.write(self.style.WARNING(f"Dropped Candidates ({len(collector.dropped_candidates)} items exceeded cap):"))
            for d in collector.dropped_candidates[:15]:
                self.stdout.write(f"  - {d['url']} (priority: {d.get('priority')}, source: {d.get('source')})")
            if len(collector.dropped_candidates) > 15:
                self.stdout.write(f"  ... and {len(collector.dropped_candidates) - 15} more dropped candidates.")

        # Summary Analysis for this company
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.MIGRATE_HEADING(f"DISCOVERY SUMMARY: {name}"))
        self.stdout.write(
            f"  * Careers/Jobs Links:       {'YES' if careers_found else 'NO'} ({len(careers_found)} found)"
        )
        if careers_found:
            self.stdout.write(f"    Sample: {careers_found[0]}")

        self.stdout.write(
            f"  * CSR/Sustainability Links: {'YES' if csr_found else 'NO'} ({len(csr_found)} found)"
        )
        if csr_found:
            self.stdout.write(f"    Sample: {csr_found[0]}")

        self.stdout.write(
            f"  * ATS Links Detected:       {'YES' if ats_found else 'NO'} ({len(ats_found)} found)"
        )
        if ats_found:
            self.stdout.write(f"    Sample: {ats_found[0]}")

        self.stdout.write(
            f"  * PDF Documents Retained:   {'YES' if pdf_found else 'NO'} ({len(pdf_found)} found)"
        )
        if pdf_found:
            self.stdout.write(f"    Sample: {pdf_found[0]}")

        self.stdout.write("=" * 80 + "\n")
