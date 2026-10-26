"""
modules/crawler_engine/candidate_collector.py
=============================================
Step 1: Rules-Based Candidate Link Collection (No AI).

Collects, normalizes, deduplicates, and filters candidate links for:
- Jobs / Careers & ATS portals
- CSR / Social Impact / Foundation
- Sustainability / ESG
- Annual Reports / BRSR Filings
- NGO Partnerships & Grant RFPs

Features:
- Primary fetch using curl_cffi (Chrome TLS fingerprint from config).
- Playwright dynamic DOM fallback when few links are detected (JS-rendered menus).
- Extraction from header nav, mega-menus, footers, common paths, subdomain probes, and sitemaps.
- Domain allowance gate (official domain, subdomains, ATS domains, navigation-linked foundations).
- ATS pattern matching via config/ats_domains.json.
- Multi-tenant ATS filtering via ownership.py and shared_tenants.json.
- Unresolved shared ATS tenants flagged with requires_owner_verification=True (never lost, withheld from auto-publish).
- Junk filtering and canonical URL normalization (preserves PDFs).
- Live existence verification with soft-404 rejection and per-domain rate limiting for probes.
- Detailed dropped-candidate logging when candidate cap (~50) is reached.
- Numbered candidate output (id: 1..N).
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Set, Tuple
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from . import ai_classifier_config as cfg
from .access_detector import DEFAULT_HEADERS
from .normalizers import clean_text, normalize_canonical_url, is_junk_url, match_ats_pattern, load_ats_patterns
from .ownership import resolve_owner, WRONG_COMPANY, OWNED, UNRESOLVED

logger = logging.getLogger(__name__)

COMMON_PATHS = (
    "/careers",
    "/jobs",
    "/join-us",
    "/career",
    "/work-with-us",
    "/csr",
    "/sustainability",
    "/foundation",
    "/about/csr",
    "/investors/annual-reports",
    "/investors/annual-report",
    "/investor-relations/annual-reports",
    "/esg",
    "/social-impact",
    "/about-us/careers",
    "/about-us/csr",
    "/sustainability/csr",
    "/community",
)

COMMON_SUBDOMAINS = (
    "careers",
    "jobs",
    "csr",
    "sustainability",
    "foundation",
    "investors",
)

SOFT_404_PHRASES = (
    "page not found",
    "404 not found",
    "404 - not found",
    "error 404",
    "page does not exist",
    "the page you requested cannot be found",
    "the page you requested could not be found",
    "the page you are looking for",
    "sorry, we couldn't find",
    "oops! that page can't be found",
    "oops! that page cannot be found",
    "this page could not be found",
)


def _extract_domain(url: str) -> str:
    """Extracts lowercase domain netloc without port."""
    if not url:
        return ""
    p = urlparse(url if "://" in url else f"https://{url}")
    return (p.netloc or "").split(":")[0].lower()


def _get_base_domain(domain: str) -> str:
    """Strips leading 'www.' or common subdomain prefix to get root corporate domain."""
    d = (domain or "").lower().strip()
    if d.startswith("www."):
        d = d[4:]
    return d


def _is_subdomain_or_same(host: str, base_domain: str) -> bool:
    """Checks if host matches or is a subdomain of base_domain."""
    h = (host or "").lower()
    b = (base_domain or "").lower()
    return h == b or h.endswith(f".{b}")


class CandidateCollector:
    """
    Candidate collector for corporate intelligence.
    Extracts up to ~50 candidate URLs per company using deterministic rule pipelines.
    """

    def __init__(
        self,
        ats_config_path: Optional[Path] = None,
        timeout: int = 15,
        allow_playwright: bool = True,
        probe_sitemaps: bool = True,
        probe_subdomains: bool = True,
        probe_common_paths: bool = True,
        probe_live: bool = True,
        max_cap: Optional[int] = None,
        rate_limit_delay: Optional[float] = None,
        browser_fingerprint: Optional[str] = None,
    ):
        self.ats_patterns = load_ats_patterns(ats_config_path)
        self.timeout = timeout
        self.allow_playwright = allow_playwright
        self.probe_sitemaps = probe_sitemaps
        self.probe_subdomains = probe_subdomains
        self.probe_common_paths = probe_common_paths
        self.probe_live = probe_live
        self.max_cap = max_cap or getattr(cfg, "CANDIDATE_MAX_CAP", 50)
        self.rate_limit_delay = rate_limit_delay or getattr(cfg, "PROBE_RATE_LIMIT_DELAY", 0.2)
        self.browser_fingerprint = browser_fingerprint or getattr(cfg, "BROWSER_FINGERPRINT", "chrome124")
        self.playwright_threshold = getattr(cfg, "PLAYWRIGHT_FALLBACK_LINK_THRESHOLD", 15)
        self.dropped_candidates: List[Dict[str, Any]] = []

    def collect_candidates(
        self,
        homepage_url: str,
        company_symbol: Optional[str] = None,
        extra_allowed_domains: Optional[List[str]] = None,
        max_candidates: Optional[int] = None,
        html_override: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Main entry point for candidate collection.
        Returns a list of numbered candidate dicts: 1..N (up to max_candidates).
        """
        self.dropped_candidates = []
        effective_max = max_candidates or self.max_cap

        if not homepage_url:
            return []

        if not homepage_url.startswith(("http://", "https://")):
            homepage_url = f"https://{homepage_url}"

        base_domain = _get_base_domain(_extract_domain(homepage_url))
        extra_allowed = set((d.lower().strip() for d in (extra_allowed_domains or []) if d))

        # 1. Fetch homepage DOM
        html, fetch_method = self._fetch_homepage_html(homepage_url, html_override=html_override)

        candidates_pool: List[Dict[str, Any]] = []
        seen_urls: Set[str] = set()

        # 2. Extract anchor links from homepage DOM
        dom_links = self._extract_dom_links(homepage_url, html, base_domain, extra_allowed)
        candidates_pool.extend(dom_links)

        # 3. Probe common paths on official domain
        if self.probe_common_paths:
            common_path_links = self._generate_common_path_links(homepage_url)
            candidates_pool.extend(common_path_links)

        # 4. Probe subdomains on official domain
        if self.probe_subdomains:
            subdomain_links = self._generate_subdomain_links(base_domain)
            candidates_pool.extend(subdomain_links)

        # 5. Extract sitemap candidates if sitemap exists
        if self.probe_sitemaps:
            sitemap_links = self._extract_sitemap_candidates(homepage_url)
            candidates_pool.extend(sitemap_links)

        # 6. Normalize, validate ATS ownership, filter junk and deduplicate
        filtered_candidates: List[Dict[str, Any]] = []

        for item in candidates_pool:
            raw_url = item.get("url")
            link_text = item.get("link_text") or ""
            norm_url = normalize_canonical_url(raw_url, base_url=homepage_url)

            if not norm_url:
                continue

            # Junk check (explicitly preserves valid PDFs)
            is_junk, junk_reason = is_junk_url(norm_url, link_text)
            if is_junk:
                continue

            parsed_norm = urlparse(norm_url)
            host = (parsed_norm.netloc or "").lower()

            # ATS pattern detection
            ats_match = match_ats_pattern(norm_url, self.ats_patterns)
            ats_platform = ats_match.get("platform") if ats_match else None
            ownership_status = None
            requires_owner_verification = False

            if ats_match:
                decision, reason = resolve_owner({"application_url": norm_url}, crawl_symbol=company_symbol)
                ownership_status = decision
                # If resolved to another company in a shared tenant -> discard from this company
                if decision == WRONG_COMPANY:
                    continue
                # If shared tenant ownership is unresolved -> keep candidate, but flag for manual review
                if decision != OWNED:
                    requires_owner_verification = True

            # Domain allowance check
            is_official = _is_subdomain_or_same(host, base_domain)
            is_extra_allowed = any(_is_subdomain_or_same(host, ed) for ed in extra_allowed)
            is_external_nav = item.get("external_linked", False)

            if not (is_official or ats_match or is_extra_allowed or is_external_nav):
                continue

            if norm_url in seen_urls:
                continue
            seen_urls.add(norm_url)

            filtered_candidates.append({
                "url": norm_url,
                "link_text": link_text,
                "menu_path": item.get("menu_path") or link_text,
                "source": item.get("source", "BODY_CONTENT"),
                "external_linked": bool(is_external_nav and not is_official),
                "ats_match": bool(ats_match),
                "ats_platform": ats_platform,
                "ownership_status": ownership_status,
                "requires_owner_verification": requires_owner_verification,
                "priority": self._calculate_candidate_priority(item, bool(ats_match)),
            })

        # 7. Sort by priority, cap at max_candidates, and log dropped items
        filtered_candidates.sort(key=lambda x: x["priority"], reverse=True)

        final_candidates = filtered_candidates[:effective_max]
        if len(filtered_candidates) > effective_max:
            self.dropped_candidates = filtered_candidates[effective_max:]
            for idx, dropped in enumerate(self.dropped_candidates, start=effective_max + 1):
                logger.info(
                    "Candidate cap reached (%d). Dropped [rank %d]: %s (source: %s, priority: %d) - Reason: Exceeded candidate cap threshold",
                    effective_max, idx, dropped["url"], dropped["source"], dropped["priority"]
                )

        # 8. Number final candidate list 1..N
        numbered_list = []
        for idx, cand in enumerate(final_candidates, start=1):
            cand_copy = dict(cand)
            cand_copy["id"] = idx
            cand_copy.pop("priority", None)
            numbered_list.append(cand_copy)

        return numbered_list

    def _fetch_homepage_html(self, url: str, html_override: Optional[str] = None) -> Tuple[str, str]:
        """Fetches page HTML with curl_cffi and falls back to Playwright if needed."""
        if html_override:
            return html_override, "OVERRIDE"

        html = ""
        try:
            resp = cffi_requests.get(
                url,
                impersonate=self.browser_fingerprint,
                headers=DEFAULT_HEADERS,
                timeout=self.timeout,
                allow_redirects=True,
            )
            html = resp.text or ""
        except Exception as e:
            logger.debug("curl_cffi fetch error for %s: %s", url, e)

        # Inspect link count to determine if Playwright re-render is necessary
        link_count = 0
        if html:
            soup = BeautifulSoup(html, "lxml")
            link_count = len(soup.find_all("a", href=True))

        if link_count < self.playwright_threshold and self.allow_playwright:
            pw_html = self._fetch_with_playwright(url)
            if pw_html:
                return pw_html, "PLAYWRIGHT"

        return html, "CURL_CFFI"

    def _fetch_with_playwright(self, url: str) -> Optional[str]:
        """Renders page in headless Playwright to capture JavaScript-generated menus."""
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent=DEFAULT_HEADERS.get("User-Agent", "Mozilla/5.0"),
                    extra_http_headers=DEFAULT_HEADERS
                )
                page.goto(url, timeout=self.timeout * 1000, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
                content = page.content()
                browser.close()
                return content
        except Exception as e:
            logger.debug("Playwright render error for %s: %s", url, e)
            return None

    def _probe_url_exists(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Executes a polite HTTP probe checking if a common-path or subdomain page exists.
        Rejects soft-404s and rate-limits per request.
        """
        if not self.probe_live:
            return True, url

        time.sleep(self.rate_limit_delay)
        try:
            resp = cffi_requests.get(
                url,
                impersonate=self.browser_fingerprint,
                headers=DEFAULT_HEADERS,
                timeout=min(self.timeout, 10),
                allow_redirects=True,
            )
            if resp.status_code not in (200, 301, 302, 307, 308):
                return False, f"HTTP_{resp.status_code}"

            final_url = str(resp.url)
            final_low = final_url.lower()

            # Reject redirects that land on explicit 404/not-found endpoints
            if any(tok in final_low for tok in ("page-not-found", "page-not-foud", "pagenotfound", "/404", "error-404", "not-found", "/notfound")):
                return False, "SOFT_404_REDIRECT_URL"

            html = resp.text or ""
            if len(html.strip()) < 80:
                return False, "EMPTY_CONTENT"

            # Check for Soft-404 signatures in title and body
            soup = BeautifulSoup(html, "lxml")
            title = (soup.title.string if soup.title and soup.title.string else "").lower()
            if any(tok in title for tok in ("404", "page not found", "page not foud", "error 404", "not found", "cannot be found", "does not exist")):
                return False, "SOFT_404_TITLE"

            body_sample = soup.get_text(" ", strip=True)[:1000].lower()
            if any(tok in body_sample for tok in SOFT_404_PHRASES):
                return False, "SOFT_404_CONTENT"

            return True, final_url
        except Exception as e:
            return False, f"PROBE_ERROR_{str(e)[:40]}"

    def _extract_dom_links(
        self,
        base_url: str,
        html: str,
        base_domain: str,
        extra_allowed: Set[str]
    ) -> List[Dict[str, Any]]:
        """Parses anchor tags preserving context, hierarchy, and menu paths."""
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        results: List[Dict[str, Any]] = []

        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue

            full_url = urljoin(base_url, href)

            text = clean_text(a.get_text(" ", strip=True)) or ""
            title_attr = clean_text(a.get("title", "")) or ""
            aria_label = clean_text(a.get("aria-label", "")) or ""
            img = a.find("img")
            img_alt = clean_text(img.get("alt", "")) if img else ""
            link_label = text or title_attr or aria_label or img_alt or ""

            in_header = bool(a.find_parent(["header", "nav"]) or self._has_class_keyword(a, ("menu", "header", "navbar", "nav")))
            in_footer = bool(a.find_parent("footer") or self._has_class_keyword(a, ("footer", "bottom")))
            source_tag = "HEADER_NAV" if in_header else ("FOOTER_NAV" if in_footer else "BODY_CONTENT")

            menu_path = self._extract_menu_path(a, link_label)

            p = urlparse(full_url)
            host = (p.netloc or "").lower()
            is_official = _is_subdomain_or_same(host, base_domain)
            is_extra = any(_is_subdomain_or_same(host, ed) for ed in extra_allowed)
            ats_match = match_ats_pattern(full_url, self.ats_patterns)

            external_linked = False
            if (in_header or in_footer) and not (is_official or is_extra or ats_match):
                if self._is_plausible_corporate_outbound(host, link_label, menu_path):
                    external_linked = True

            results.append({
                "url": full_url,
                "link_text": link_label[:120],
                "menu_path": menu_path[:150],
                "source": source_tag,
                "external_linked": external_linked,
            })

        return results

    def _extract_menu_path(self, anchor_tag: Any, link_label: str) -> str:
        """Walks up DOM parent elements to reconstruct menu path (e.g. 'About Us > Careers')."""
        path_segments: List[str] = []
        curr = anchor_tag.parent

        depth = 0
        while curr and depth < 5:
            if curr.name in ("li", "div", "nav", "section"):
                header_elem = curr.find(["h1", "h2", "h3", "h4", "h5", "h6", "span", "button", "a"])
                if header_elem and header_elem != anchor_tag:
                    txt = clean_text(header_elem.get_text(" ", strip=True))
                    if txt and len(txt) <= 40 and txt != link_label and txt not in path_segments:
                        path_segments.insert(0, txt)
            curr = curr.parent
            depth += 1

        if link_label:
            path_segments.append(link_label)

        return " > ".join(path_segments) if len(path_segments) > 1 else link_label

    def _has_class_keyword(self, tag: Any, keywords: Tuple[str, ...]) -> bool:
        """Checks if tag or its immediate parents have matching CSS class names."""
        for p in [tag, tag.parent, tag.parent.parent if tag.parent else None]:
            if not p:
                continue
            classes = p.get("class", [])
            class_str = " ".join(classes).lower() if isinstance(classes, list) else str(classes).lower()
            if any(k in class_str for k in keywords):
                return True
        return False

    def _is_plausible_corporate_outbound(self, host: str, link_label: str, menu_path: str) -> bool:
        """Checks if an outbound navigation link has plausible corporate intelligence signals (foundation, trust, csr, careers)."""
        h = (host or "").lower()
        t = f"{link_label} {menu_path}".lower()
        keywords = (
            "foundation", "trust", "charity", "csr", "social", "impact",
            "community", "sustainab", "esg", "giving", "welfare", "careers", "jobs", "recruit"
        )
        return any(k in h for k in keywords) or any(k in t for k in keywords)

    def _generate_common_path_links(self, base_url: str) -> List[Dict[str, Any]]:
        """Generates and live-probes standard corporate paths."""
        results = []
        for path in COMMON_PATHS:
            full = urljoin(base_url, path)
            label = path.strip("/").replace("-", " ").replace("/", " > ").title()

            is_live, final_or_err = self._probe_url_exists(full)
            if is_live:
                target_url = final_or_err if final_or_err.startswith("http") else full
                results.append({
                    "url": target_url,
                    "link_text": label,
                    "menu_path": label,
                    "source": "COMMON_PATH",
                    "external_linked": False,
                })
        return results

    def _generate_subdomain_links(self, base_domain: str) -> List[Dict[str, Any]]:
        """Generates and live-probes common subdomain URLs."""
        results = []
        if not base_domain:
            return results
        for sub in COMMON_SUBDOMAINS:
            sub_url = f"https://{sub}.{base_domain}"
            label = f"{sub.title()} Subdomain"

            is_live, final_or_err = self._probe_url_exists(sub_url)
            if is_live:
                target_url = final_or_err if final_or_err.startswith("http") else sub_url
                results.append({
                    "url": target_url,
                    "link_text": label,
                    "menu_path": label,
                    "source": "SUBDOMAIN_PROBE",
                    "external_linked": False,
                })
        return results

    def _extract_sitemap_candidates(self, homepage_url: str) -> List[Dict[str, Any]]:
        """Extracts candidate URLs from /sitemap.xml and sitemap index if available."""
        sitemap_url = urljoin(homepage_url, "/sitemap.xml")
        results = []
        try:
            resp = cffi_requests.get(
                sitemap_url,
                impersonate=self.browser_fingerprint,
                headers=DEFAULT_HEADERS,
                timeout=min(self.timeout, 8),
                allow_redirects=True,
            )
            if resp.status_code == 200 and resp.text:
                locs = re.findall(r'<loc>\s*(https?://[^<\s]+)\s*</loc>', resp.text, re.IGNORECASE)
                for loc in locs:
                    loc_clean = loc.strip()
                    loc_lower = loc_clean.lower()
                    if any(k in loc_lower for k in (
                        "career", "job", "join-us", "work-with-us", "csr", "sustainab", "foundation",
                        "esg", "annual-report", "brsr", "social-impact", "community"
                    )):
                        p_name = loc_clean.rstrip("/").split("/")[-1].replace("-", " ").title()
                        results.append({
                            "url": loc_clean,
                            "link_text": p_name or "Sitemap Page",
                            "menu_path": f"Sitemap > {p_name}",
                            "source": "SITEMAP",
                            "external_linked": False,
                        })
                        if len(results) >= 20:
                            break
        except Exception as e:
            logger.debug("Sitemap probe error for %s: %s", sitemap_url, e)

        return results

    def _calculate_candidate_priority(self, item: Dict[str, Any], is_ats: bool) -> int:
        """Scores candidate links with rich synonyms to prioritize high-value pages when capping at ~50."""
        score = 0
        if is_ats:
            score += 100

        source = item.get("source")
        if source == "HEADER_NAV":
            score += 80
        elif source == "SUBDOMAIN_PROBE":
            score += 70
        elif source == "COMMON_PATH":
            score += 65
        elif source == "FOOTER_NAV":
            score += 60
        elif source == "SITEMAP":
            score += 50
        else:
            score += 30

        text = (item.get("link_text") or "").lower()
        menu_path = (item.get("menu_path") or "").lower()
        url = (item.get("url") or "").lower()
        combined = f"{text} {menu_path} {url}"

        # 1. Careers / Recruitment synonyms
        if any(k in combined for k in (
            "career", "job", "join us", "work with us", "life at", "opportunities",
            "openings", "vacancies", "vacanc", "roles", "hiring", "talent",
            "employment", "people", "naukri", "rozgar"
        )):
            score += 40

        # 2. CSR / Social Impact / Foundation synonyms
        if any(k in combined for k in (
            "csr", "social impact", "foundation", "trust", "community", "community development",
            "giving", "citizenship", "society", "social responsibility", "schedule vii",
            "section 135", "samajik", "sewa", "ngo", "philanthropy"
        )):
            score += 40

        # 3. Sustainability / ESG synonyms
        if any(k in combined for k in (
            "sustainab", "esg", "environment", "climate", "net zero",
            "green", "carbon", "renewable", "brsr"
        )):
            score += 35

        # 4. Annual Reports / Statutory Disclosures synonyms
        if any(k in combined for k in (
            "annual report", "annual-report", "integrated report", "investor relations",
            "investor", "financial statements", "statutory disclosure", "disclosures"
        )):
            score += 30

        # 5. NGO Partnerships / Grant RFPs synonyms
        if any(k in combined for k in (
            "partner with us", "ngo partner", "call for proposal", "grant", "rfp",
            "eoi", "tender", "empanelment", "expression of interest"
        )):
            score += 35

        return score
