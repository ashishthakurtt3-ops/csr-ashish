import os
import re
import csv
import io
import time
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple, Set

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from modules.admin_panel.models import Company
from modules.crawler_engine.homepage_verifier import (
    fetch_candidate_page,
    clean_tokens_for_company,
    is_wrong_entity_or_parent,
    WikidataPlugin,
    FetchResult,
)


def get_registrable_domain(url: str) -> str:
    """
    Extracts the registrable domain (e.g. adani.com, tataconsultancy.co.in)
    from a URL, normalizing port, scheme, and subdomains.
    """
    if not url:
        return ""
    try:
        raw = url.strip().lower()
        if not raw.startswith("http://") and not raw.startswith("https://"):
            raw = "https://" + raw
        p = urllib.parse.urlparse(raw)
        host = p.netloc.split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        parts = host.split(".")
        if len(parts) <= 2:
            return host
        two_level_tlds = {
            "co.in", "net.in", "org.in", "gen.in", "firm.in", "ind.in",
            "bank.in", "gov.in", "ac.in", "edu.in", "res.in",
            "co.uk", "org.uk", "me.uk", "ltd.uk", "plc.uk",
            "com.au", "net.au", "org.au", "edu.au",
            "co.za", "com.sg", "com.my", "co.nz", "com.br"
        }
        last_two = ".".join(parts[-2:])
        if last_two in two_level_tlds and len(parts) >= 3:
            return ".".join(parts[-3:])
        return ".".join(parts[-2:])
    except Exception:
        return ""


class Command(BaseCommand):
    help = (
        "Dataset cross-checking for automatic homepage verification: "
        "cross-checks against official exchange & Wikidata datasets, collects "
        "independent source votes, checks identity proof on-site, and accepts "
        "urls only with multi-source domain consensus and statutory proof."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="Simulate verification without database modifications (default: True).",
        )
        parser.add_argument(
            "--apply-updates",
            action="store_true",
            default=False,
            help="Apply accepted and locked URLs to the database.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Limit number of companies to check (0 = all 201 companies).",
        )
        parser.add_argument(
            "--company-id",
            type=str,
            help="Check a single company by company_id.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default="exports/homepage_crosscheck.csv",
            help="Destination output CSV path (default: exports/homepage_crosscheck.csv).",
        )

    def handle(self, *args, **options):
        dry_run = not options.get("apply_updates")
        limit = options.get("limit", 0)
        target_company_id = options.get("company_id")
        out_path = options.get("out", "exports/homepage_crosscheck.csv")
        if not os.path.isabs(out_path):
            out_path = os.path.abspath(out_path)

        self.stdout.write(self.style.NOTICE("\n=== Automatic Homepage Verification & Dataset Cross-Check ==="))
        self.stdout.write(f"Mode: {'DRY RUN (No database mutations)' if dry_run else 'APPLY UPDATES (Mutating DB)'}")

        # ----------------------------------------------------------------------
        # Step 1: Load and Cache NSE EQUITY_L.csv and NSDL ISIN list
        # ----------------------------------------------------------------------
        nse_data, nse_source_info = self._load_or_cache_nse_equity_list()
        nsdl_data = self._load_or_cache_nsdl_list()

        # Cross-check 201 companies against exchange datasets
        qs = Company.objects.all().order_by("company_id")
        if target_company_id:
            qs = qs.filter(company_id=target_company_id)
        if limit > 0:
            qs = qs[:limit]

        companies = list(qs)
        self.stdout.write(f"Loaded {len(companies)} company records from database.")

        dataset_mismatches = []
        unmatched_companies = []

        for c in companies:
            c_isin = (c.isin or "").strip()
            c_name = (c.company_name or "").strip()

            nse_match = None
            if c_isin and c_isin in nse_data["by_isin"]:
                nse_match = nse_data["by_isin"][c_isin]
                nse_name = nse_match["name"]
                # Name divergence check
                if not self._is_name_substantially_equal(c_name, nse_name):
                    dataset_mismatches.append({
                        "company_id": c.company_id,
                        "type": "NAME_MISMATCH_WITH_NSE",
                        "db_val": c_name,
                        "exchange_val": nse_name,
                        "isin": c_isin,
                        "symbol": nse_match["symbol"]
                    })
            elif c_name.lower() in nse_data["by_name"]:
                nse_match = nse_data["by_name"][c_name.lower()]
                nse_isin = nse_match["isin"]
                if c_isin and nse_isin != c_isin:
                    dataset_mismatches.append({
                        "company_id": c.company_id,
                        "type": "ISIN_MISMATCH_WITH_NSE",
                        "db_val": c_isin,
                        "exchange_val": nse_isin,
                        "company_name": c_name,
                        "symbol": nse_match["symbol"]
                    })
            else:
                unmatched_companies.append({
                    "company_id": c.company_id,
                    "company_name": c_name,
                    "isin": c_isin
                })

        self.stdout.write(f"Exchange Match Summary:")
        self.stdout.write(f"  - Matched on NSE: {len(companies) - len(unmatched_companies)}/{len(companies)}")
        self.stdout.write(f"  - Unmatched on NSE: {len(unmatched_companies)}")
        for u in unmatched_companies:
            self.stdout.write(self.style.WARNING(f"    * Unmatched: [{u['company_id']}] {u['company_name']} (ISIN: {u['isin'] or 'None'})"))
        self.stdout.write(f"  - Name/ISIN Mismatches with Exchange: {len(dataset_mismatches)}")
        for m in dataset_mismatches[:5]:
            self.stdout.write(f"    * {m['company_id']} ({m['type']}): DB '{m['db_val']}' vs NSE '{m['exchange_val']}'")

        # ----------------------------------------------------------------------
        # Step 2 to 5: Candidate Collection, Identity Evidence, & Decision
        # ----------------------------------------------------------------------
        wikidata_plugin = WikidataPlugin()
        results = []
        decision_counts = {
            "ACCEPTED": 0,
            "UNRESOLVED": 0,
            "WRONG_ENTITY": 0
        }

        self.stdout.write(self.style.NOTICE("\nProcessing companies with multi-source candidate collection & identity verification..."))

        for idx, comp in enumerate(companies, 1):
            comp_id = comp.company_id
            comp_name = comp.company_name
            website_url = comp.website_url or ""
            isin = comp.isin or ""
            cin = comp.cin or ""

            # Sources map: source_name -> URL
            source_candidates: Dict[str, str] = {}

            # Source 1: Current website_url
            if website_url:
                source_candidates["CURRENT_DB"] = website_url.strip()

            # Source 2: Wikidata (property P856)
            try:
                wd_urls = wikidata_plugin.lookup(comp)
                for w_idx, w_url in enumerate(wd_urls, 1):
                    tag = "WIKIDATA" if w_idx == 1 else f"WIKIDATA_{w_idx}"
                    source_candidates[tag] = w_url.strip()
            except Exception as e:
                pass

            # Source 3: Annual Report URL printed domain
            if comp.annual_report_url and comp.annual_report_url.strip():
                try:
                    ar_parsed = urllib.parse.urlparse(comp.annual_report_url.strip())
                    if ar_parsed.netloc:
                        ar_cand = f"{ar_parsed.scheme or 'https'}://{ar_parsed.netloc}"
                        source_candidates["ANNUAL_REPORT"] = ar_cand
                except Exception:
                    pass

            # Count votes per registrable domain
            domain_votes: Dict[str, List[Tuple[str, str]]] = {}
            for src, u in source_candidates.items():
                r_dom = get_registrable_domain(u)
                if r_dom:
                    if r_dom not in domain_votes:
                        domain_votes[r_dom] = []
                    domain_votes[r_dom].append((src, u))

            # Fetch candidate pages and inspect on-site evidence
            candidate_proofs: Dict[str, Dict[str, Any]] = {}
            # Unique URLs to fetch
            urls_to_test = list(dict.fromkeys(source_candidates.values()))

            for u in urls_to_test:
                proof = self._fetch_and_check_identity(u, comp)
                candidate_proofs[u] = proof

            # Decision Evaluation per Rule 4:
            # (a) At least two sources agree on the same registrable domain AND
            # (b) The site shows the ISIN, CIN or full legal name.
            # If the old URL works and names the company, keep it.
            # If the site names a parent, subsidiary or sister company, mark WRONG_ENTITY.

            decision = "UNRESOLVED"
            chosen_url = ""
            reasons = []
            evidence_found_str = ""

            # Check if any candidate triggered WRONG_ENTITY
            wrong_entity_flag = False
            wrong_entity_details = ""
            for u in urls_to_test:
                p = candidate_proofs[u]
                if p.get("is_wrong_entity"):
                    wrong_entity_flag = True
                    wrong_entity_details = p.get("wrong_entity_reason", "Names parent or sister company")
                    break

            if wrong_entity_flag:
                decision = "WRONG_ENTITY"
                reasons.append(wrong_entity_details)
                evidence_found_str = f"Wrong Entity: {wrong_entity_details}"
            else:
                # Find domains with at least 2 votes
                valid_consensuses = []
                for r_dom, votes in domain_votes.items():
                    if len(votes) >= 2:
                        valid_consensuses.append((r_dom, votes))

                if not valid_consensuses:
                    if len(domain_votes) <= 1 and urls_to_test:
                        reasons.append("sources disagree: insufficient multi-source agreement (< 2 sources)")
                    else:
                        reasons.append("sources disagree: conflicting source candidate domains")

                # Check if any consensus candidate has identity proof
                accepted_candidate = None
                for r_dom, votes in valid_consensuses:
                    for src, cand_u in votes:
                        proof = candidate_proofs.get(cand_u, {})
                        if proof.get("has_identity_proof"):
                            accepted_candidate = (cand_u, r_dom, votes, proof)
                            break
                    if accepted_candidate:
                        break

                if accepted_candidate:
                    cand_u, r_dom, votes, proof = accepted_candidate
                    # Prefer current DB URL if it works, belongs to consensus domain, and names company
                    if website_url and get_registrable_domain(website_url) == r_dom:
                        curr_proof = candidate_proofs.get(website_url, {})
                        if curr_proof.get("status_code") == 200 and curr_proof.get("has_identity_proof"):
                            chosen_url = curr_proof.get("final_url") or website_url
                            evidence_found_str = curr_proof.get("evidence_summary", "")
                        else:
                            chosen_url = proof.get("final_url") or cand_u
                            evidence_found_str = proof.get("evidence_summary", "")
                    else:
                        chosen_url = proof.get("final_url") or cand_u
                        evidence_found_str = proof.get("evidence_summary", "")

                    decision = "ACCEPTED"
                    src_list = [v[0] for v in votes]
                    reasons.append(f"Domain consensus '{r_dom}' by {', '.join(src_list)} with identity proof")
                else:
                    blocked_any = any(candidate_proofs[u].get("is_blocked") for u in urls_to_test)
                    if blocked_any:
                        reasons.append("blocked")
                    if valid_consensuses:
                        if not blocked_any:
                            reasons.append("no identity proof")
                    else:
                        # sources already disagree, check if also no identity proof
                        if not any(candidate_proofs[u].get("has_identity_proof") for u in urls_to_test) and not blocked_any:
                            reasons.append("no identity proof")

            decision_counts[decision] += 1

            # Format source candidate strings
            curr_src_str = source_candidates.get("CURRENT_DB", "")
            wd_src_str = ", ".join([u for s, u in source_candidates.items() if "WIKIDATA" in s])
            ar_src_str = source_candidates.get("ANNUAL_REPORT", "")

            row_data = {
                "company_id": comp_id,
                "company_name": comp_name,
                "isin": isin,
                "cin": cin,
                "current_db_url": curr_src_str,
                "wikidata_url": wd_src_str,
                "annual_report_url": ar_src_str,
                "chosen_url": chosen_url if decision == "ACCEPTED" else "",
                "decision": decision,
                "decision_reasons": "; ".join(reasons),
                "evidence_found": evidence_found_str,
            }
            results.append(row_data)

            if idx % 20 == 0 or idx == len(companies):
                self.stdout.write(f"Processed {idx}/{len(companies)} companies... (Accepted: {decision_counts['ACCEPTED']}, Unresolved: {decision_counts['UNRESOLVED']}, Wrong Entity: {decision_counts['WRONG_ENTITY']})")

            # Apply updates if explicitly requested
            if not dry_run and decision == "ACCEPTED" and chosen_url:
                if not comp.website_url_locked:
                    if comp.website_url != chosen_url:
                        history = list(comp.website_url_history or [])
                        history.append({
                            "previous_url": comp.website_url,
                            "changed_at": timezone.now().isoformat(),
                            "source": "DATASET_CROSSCHECK",
                            "evidence": evidence_found_str
                        })
                        comp.website_url_history = history
                        comp.website_url = chosen_url
                    comp.website_url_locked = True
                    comp.website_url_status = "CORRECT"
                    comp.website_url_verified_at = timezone.now()
                    comp.website_url_review_notes = f"Accepted via dataset cross-check: {evidence_found_str}"
                    comp.save(update_fields=[
                        "website_url", "website_url_history", "website_url_locked",
                        "website_url_status", "website_url_verified_at", "website_url_review_notes"
                    ])

        # ----------------------------------------------------------------------
        # Step 6: Write exports/homepage_crosscheck.csv & Print Terminal Summary
        # ----------------------------------------------------------------------
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        csv_headers = [
            "company_id",
            "company_name",
            "isin",
            "cin",
            "current_db_url",
            "wikidata_url",
            "annual_report_url",
            "chosen_url",
            "decision",
            "decision_reasons",
            "evidence_found",
        ]
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=csv_headers)
            writer.writeheader()
            for r in results:
                writer.writerow(r)

        self.stdout.write(self.style.SUCCESS("\n" + "=" * 70))
        self.stdout.write(self.style.SUCCESS("Dataset Cross-Checking Summary"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(f"Total Companies Evaluated: {len(companies)}")
        self.stdout.write(self.style.SUCCESS(f"  - ACCEPTED     : {decision_counts['ACCEPTED']}"))
        self.stdout.write(self.style.WARNING(f"  - UNRESOLVED   : {decision_counts['UNRESOLVED']}"))
        self.stdout.write(self.style.ERROR(f"  - WRONG_ENTITY : {decision_counts['WRONG_ENTITY']}"))
        self.stdout.write("-" * 70)
        self.stdout.write(f"Cross-check Report Saved to: {out_path}")
        self.stdout.write(self.style.SUCCESS("=" * 70 + "\n"))

    # --------------------------------------------------------------------------
    # Helper: Load and Cache NSE EQUITY_L.csv
    # --------------------------------------------------------------------------
    def _load_or_cache_nse_equity_list(self) -> Tuple[Dict[str, Dict[str, Any]], str]:
        cache_dir = os.path.join(settings.BASE_DIR, "data", "exchange_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cached_file = os.path.join(cache_dir, "EQUITY_L.csv")

        content = ""
        info_str = "cache"

        # Check if cache is fresh (< 7 days)
        need_fetch = True
        if os.path.exists(cached_file):
            mtime = os.path.getmtime(cached_file)
            if (time.time() - mtime) < (7 * 86400):
                need_fetch = False
                try:
                    with open(cached_file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    info_str = f"local_cache ({cached_file})"
                except Exception:
                    need_fetch = True

        if need_fetch or not content:
            url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw_data = resp.read()
                    content = raw_data.decode("utf-8", errors="replace")
                with open(cached_file, "w", encoding="utf-8", errors="replace") as f:
                    f.write(content)
                info_str = f"live_fetch ({url})"
            except Exception as e:
                # If fetch fails, try fallback to cached file if exists
                if os.path.exists(cached_file):
                    with open(cached_file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    info_str = f"fallback_cache ({cached_file})"
                else:
                    self.stdout.write(self.style.ERROR(f"Failed to fetch NSE list: {e}"))
                    content = ""

        by_isin = {}
        by_name = {}

        if content:
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                isin = (row.get(" ISIN NUMBER") or row.get("ISIN NUMBER") or "").strip()
                name = (row.get("NAME OF COMPANY") or "").strip()
                symbol = (row.get("SYMBOL") or "").strip()
                if isin:
                    by_isin[isin] = {"name": name, "symbol": symbol}
                if name:
                    by_name[name.lower()] = {"isin": isin, "symbol": symbol}

        return {"by_isin": by_isin, "by_name": by_name}, info_str

    # --------------------------------------------------------------------------
    # Helper: Load and Cache NSDL List if available
    # --------------------------------------------------------------------------
    def _load_or_cache_nsdl_list(self) -> Dict[str, Any]:
        cache_dir = os.path.join(settings.BASE_DIR, "data", "exchange_cache")
        cached_file = os.path.join(cache_dir, "nsdl_isin.csv")
        by_isin = {}
        if os.path.exists(cached_file):
            try:
                with open(cached_file, "r", encoding="utf-8", errors="replace") as f:
                    reader = csv.DictReader(f)
                    for r in reader:
                        isin = (r.get("ISIN") or "").strip()
                        name = (r.get("COMPANY_NAME") or "").strip()
                        if isin:
                            by_isin[isin] = name
            except Exception:
                pass
        return {"by_isin": by_isin}

    # --------------------------------------------------------------------------
    # Helper: Compare Company Names (Normalizing Suffixes)
    # --------------------------------------------------------------------------
    def _is_name_substantially_equal(self, name1: str, name2: str) -> bool:
        if not name1 or not name2:
            return False
        n1 = re.sub(r"[^a-zA-Z0-9\s]", " ", name1.lower())
        n2 = re.sub(r"[^a-zA-Z0-9\s]", " ", name2.lower())
        stopwords = {"limited", "ltd", "private", "pvt", "corp", "corporation", "inc", "incorporated", "llc", "plc"}
        w1 = [w for w in n1.split() if w not in stopwords]
        w2 = [w for w in n2.split() if w not in stopwords]
        return " ".join(w1) == " ".join(w2)

    # --------------------------------------------------------------------------
    # Helper: Fetch Candidate and Check Identity Evidence
    # --------------------------------------------------------------------------
    def _fetch_and_check_identity(self, url: str, company: Company) -> Dict[str, Any]:
        """
        Fetches candidate page (using curl_cffi or Playwright if blocked),
        evaluates wrong-entity guards, and checks for on-site identity:
        ISIN, CIN, or full legal name.
        """
        fetch_res: FetchResult = fetch_candidate_page(url, timeout=12)

        # Fallback to Playwright if blocked (403, 429, 503, bot challenge)
        html = fetch_res.html or ""
        status_code = fetch_res.status_code
        final_url = fetch_res.final_url or url
        is_blocked = False

        challenge_markers = (
            "cf-browser-verification", "cf-mitigated", "challenge-platform",
            "just a moment...", "turnstile", "recaptcha", "hcaptcha",
            "ddos-guard", "incapsula", "access denied", "attention required! | cloudflare",
            "security check to access", "robot or human", "verify you are human",
        )
        lower_html = html.lower()
        has_challenge = any(m in lower_html for m in challenge_markers)
        is_suspicious_short = (status_code == 200 and len(html.strip()) < 350 and any(w in lower_html for w in ("blocked", "forbidden", "denied", "captcha", "security check")))

        if status_code in (403, 429, 503) or (status_code == 200 and (has_challenge or is_suspicious_short)) or (not html and status_code != 200):
            is_blocked = True
            pw_html, pw_url = self._fetch_with_playwright(url)
            if pw_html:
                pw_lower = pw_html.lower()
                pw_has_challenge = any(m in pw_lower for m in challenge_markers)
                if not pw_has_challenge and len(pw_html.strip()) > 350:
                    html = pw_html
                    final_url = pw_url or final_url
                    status_code = 200
                    is_blocked = False

        # Rule 5: Never mark a blocked page as wrong
        if is_blocked or status_code in (403, 429, 503):
            return {
                "status_code": status_code,
                "final_url": final_url,
                "is_blocked": True,
                "is_wrong_entity": False,
                "wrong_entity_reason": "",
                "has_identity_proof": False,
                "evidence_summary": "Blocked by security checkpoint / challenge",
            }

        # Wrong entity guard
        wrong_entity, wrong_reason = is_wrong_entity_or_parent(final_url, html, company)
        if wrong_entity:
            return {
                "status_code": status_code,
                "final_url": final_url,
                "is_blocked": False,
                "is_wrong_entity": True,
                "wrong_entity_reason": wrong_reason,
                "has_identity_proof": False,
                "evidence_summary": f"WRONG_ENTITY: {wrong_reason}",
            }

        # Check identity signals on site:
        # 1. ISIN on site
        isin = (company.isin or "").strip()
        isin_found = bool(isin and len(isin) >= 10 and isin in html)

        # 2. CIN on site
        cin = (company.cin or "").strip()
        cin_found = bool(cin and len(cin) >= 15 and cin in html)

        # 3. Full Legal Name / Authentic Name on site
        comp_name = company.company_name.strip()
        legal_name = (company.legal_name or "").strip()
        name_clean = re.sub(r"\s+", " ", comp_name.lower())
        norm_html = re.sub(r"\s+", " ", html.lower())

        # Exact match or normalized match
        name_found = False
        if name_clean in norm_html:
            name_found = True
        elif legal_name and re.sub(r"\s+", " ", legal_name.lower()) in norm_html:
            name_found = True
        else:
            # Check without corporate suffixes
            stripped_name = re.sub(r"\b(limited|ltd|pvt|private|inc|corp)\b", "", name_clean).strip()
            if len(stripped_name) >= 4 and stripped_name in norm_html:
                name_found = True

        evidence_items = []
        if isin_found:
            evidence_items.append(f"ISIN found ({isin})")
        if cin_found:
            evidence_items.append(f"CIN found ({cin})")
        if name_found:
            evidence_items.append(f"Legal Name found ('{comp_name}')")

        has_identity_proof = bool(isin_found or cin_found or name_found)

        return {
            "status_code": status_code,
            "final_url": final_url,
            "is_blocked": is_blocked,
            "is_wrong_entity": False,
            "has_identity_proof": has_identity_proof,
            "isin_found": isin_found,
            "cin_found": cin_found,
            "name_found": name_found,
            "evidence_summary": "; ".join(evidence_items) if evidence_items else "No identity proof on site",
        }

    # --------------------------------------------------------------------------
    # Helper: Playwright Fetch for Blocked Sites
    # --------------------------------------------------------------------------
    def _fetch_with_playwright(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ))
                page.goto(url, timeout=15000, wait_until="domcontentloaded")
                html = page.content()
                final_url = page.url
                browser.close()
                return html, final_url
        except Exception:
            return None, None
