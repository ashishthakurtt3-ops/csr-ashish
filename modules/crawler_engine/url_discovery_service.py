"""
modules/crawler_engine/url_discovery_service.py
===============================================
Milestone 2: Multi-Source URL Discovery Engine (Requirement R3).

Coordinates URL discovery across:
1. Robots.txt directives & declared sitemaps (RFC 9309 compliant)
2. Multi-format XML & .xml.gz sitemap parsing (recursive traversal)
3. Homepage & Website Navigation (Header, Footer, Mega-Menus, Breadcrumbs, JSON-LD)
4. Resource-bounded headless Playwright fallback for SPA / dynamic navigation
5. Associated external domains (Subdomains, ATS platforms, Corporate foundations)
6. Canonical deduplication, junk filtering, and source priority ranking

Interface Contract:
- Ingests: normalize_and_validate_company(name, url) from normalizers.py
- Exports: discover_company_urls(company_name, base_url, options) -> List[DiscoveredUrlCandidate]
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

try:
    import requests
except ImportError:
    requests = None

from .access_detector import DEFAULT_HEADERS
from .candidate_collector import CandidateCollector
from .discovery_helpers import (
    ALLOWED_ATS_HOSTS,
    APPROVED_FOUNDATION_DOMAINS,
    is_allowed_domain_or_ats,
)
from .normalizers import (
    clean_text,
    is_junk_url,
    match_ats_pattern,
    load_ats_patterns,
    normalize_and_validate_company,
    normalize_canonical_url,
)
from .robots_handler import RobotsHandler
from .sitemap_parser import SitemapParser

logger = logging.getLogger(__name__)


class DiscoverySource(str, Enum):
    ROBOTS_TXT = "ROBOTS_TXT"
    SITEMAP = "SITEMAP"
    HEADER_NAV = "HEADER_NAV"
    FOOTER_NAV = "FOOTER_NAV"
    BODY_CONTENT = "BODY_CONTENT"
    SUBDOMAIN = "SUBDOMAIN"
    ATS_PLATFORM = "ATS_PLATFORM"
    FOUNDATION = "FOUNDATION"


SOURCE_PRIORITY: Dict[str, int] = {
    DiscoverySource.HEADER_NAV.value: 100,
    DiscoverySource.ATS_PLATFORM.value: 95,
    DiscoverySource.FOUNDATION.value: 90,
    DiscoverySource.FOOTER_NAV.value: 80,
    DiscoverySource.SITEMAP.value: 70,
    DiscoverySource.SUBDOMAIN.value: 60,
    DiscoverySource.ROBOTS_TXT.value: 50,
    DiscoverySource.BODY_CONTENT.value: 40,
}


@dataclass
class DiscoveredUrlCandidate:
    """Strongly-typed contract object for discovered URL candidates (M2 -> M3)."""
    url: str
    discovery_source: str
    referring_url: str = ""
    anchor_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if isinstance(self.discovery_source, DiscoverySource):
            self.discovery_source = self.discovery_source.value
        elif isinstance(self.discovery_source, str):
            self.discovery_source = self.discovery_source.upper().strip()
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Serializes candidate to dictionary."""
        return {
            "url": self.url,
            "discovery_source": self.discovery_source,
            "referring_url": self.referring_url,
            "anchor_text": self.anchor_text,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DiscoveredUrlCandidate:
        """Constructs DiscoveredUrlCandidate from dictionary."""
        return cls(
            url=data.get("url", ""),
            discovery_source=data.get("discovery_source", DiscoverySource.BODY_CONTENT.value),
            referring_url=data.get("referring_url", ""),
            anchor_text=data.get("anchor_text", ""),
            metadata=data.get("metadata") or {},
        )


def fetch_raw_page(url: str, timeout: int = 10) -> Tuple[int, str]:
    """
    Fetches raw HTTP page content with Chrome JA3 impersonation cascade.
    Returns (status_code, body_text).
    """
    if cffi_requests is not None:
        try:
            resp = cffi_requests.get(
                url,
                impersonate="chrome124",
                headers=DEFAULT_HEADERS,
                timeout=timeout,
                allow_redirects=True,
            )
            return resp.status_code, resp.text or ""
        except Exception as e:
            logger.debug("curl_cffi fetch error for %s: %s", url, e)

    if requests is not None:
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
            return resp.status_code, resp.text or ""
        except Exception as e:
            logger.debug("requests fetch error for %s: %s", url, e)

    return 0, ""


class URLDiscoveryEngine:
    """Multi-source URL discovery engine extracting DOM, breadcrumb, JSON-LD, and SPA candidates."""

    def __init__(self, playwright_threshold: int = 15):
        self.playwright_threshold = playwright_threshold
        self.ats_patterns = load_ats_patterns()

    def extract_dom_candidates(self, base_url: str, html: str) -> List[DiscoveredUrlCandidate]:
        """Extracts candidates from DOM anchors, breadcrumbs, and JSON-LD microdata."""
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        candidates: List[DiscoveredUrlCandidate] = []
        seen_urls: Set[str] = set()

        base_parsed = urlparse(base_url)
        base_domain = base_parsed.netloc.lower()

        # 1. Parse DOM anchor tags
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue

            full_url = urljoin(base_url, href)
            clean_url = full_url.split('#')[0].rstrip('/')
            if not clean_url or clean_url in seen_urls:
                continue

            text = clean_text(a.get_text(" ", strip=True)) or ""
            title_attr = clean_text(a.get("title", "")) or ""
            aria_label = clean_text(a.get("aria-label", "")) or ""
            img = a.find("img")
            img_alt = clean_text(img.get("alt", "")) if img else ""
            link_label = text or title_attr or aria_label or img_alt or ""

            # Check breadcrumb structure
            is_breadcrumb = bool(
                a.find_parent(attrs={"aria-label": re.compile(r"breadcrumb", re.I)}) or
                a.find_parent(class_=re.compile(r"breadcrumb", re.I)) or
                a.find_parent(attrs={"itemtype": re.compile(r"BreadcrumbList", re.I)})
            )

            # Check header / nav / dropdown / mega-menu / ARIA roles
            in_header = bool(
                a.find_parent(["header", "nav"]) or
                self._has_nav_class(a, ("menu", "header", "navbar", "nav", "dropdown", "megamenu", "mega-menu", "flyout", "sub-menu", "submenu")) or
                a.find_parent(attrs={"role": re.compile(r"menu(bar|item)?", re.I)}) or
                a.find_parent(attrs={"aria-haspopup": "true"})
            )

            # Check footer
            in_footer = bool(
                a.find_parent("footer") or
                self._has_nav_class(a, ("footer", "bottom", "colophon", "site-info"))
            )

            p = urlparse(full_url)
            host = (p.netloc or "").lower()
            ats_match = match_ats_pattern(full_url, self.ats_patterns)

            # Determine discovery source tag
            if ats_match or any(host == h or host.endswith("." + h) for h in ALLOWED_ATS_HOSTS):
                source_tag = DiscoverySource.ATS_PLATFORM.value
            elif host in APPROVED_FOUNDATION_DOMAINS or any(f in host for f in ("foundation", "trust")):
                source_tag = DiscoverySource.FOUNDATION.value
            elif in_header or is_breadcrumb:
                source_tag = DiscoverySource.HEADER_NAV.value
            elif in_footer:
                source_tag = DiscoverySource.FOOTER_NAV.value
            else:
                source_tag = DiscoverySource.BODY_CONTENT.value

            metadata: Dict[str, Any] = {
                "in_header": in_header,
                "in_footer": in_footer,
            }
            if is_breadcrumb:
                metadata["breadcrumb"] = True

            seen_urls.add(clean_url)
            candidates.append(DiscoveredUrlCandidate(
                url=full_url,
                discovery_source=source_tag,
                referring_url=base_url,
                anchor_text=link_label[:120],
                metadata=metadata,
            ))

        # 2. Extract structured JSON-LD links
        jsonld_cands = self._extract_jsonld_candidates(base_url, soup)
        for jc in jsonld_cands:
            c_clean = jc.url.split('#')[0].rstrip('/')
            if c_clean and c_clean not in seen_urls:
                seen_urls.add(c_clean)
                candidates.append(jc)

        return candidates

    def _has_nav_class(self, tag: Any, keywords: Tuple[str, ...]) -> bool:
        """Walks up tag ancestors checking for navigation class keywords."""
        curr = tag
        depth = 0
        while curr and depth < 4:
            classes = curr.get("class", [])
            class_str = " ".join(classes).lower() if isinstance(classes, list) else str(classes).lower()
            if any(k in class_str for k in keywords):
                return True
            curr = curr.parent
            depth += 1
        return False

    def _extract_jsonld_candidates(self, base_url: str, soup: BeautifulSoup) -> List[DiscoveredUrlCandidate]:
        """Extracts candidate URLs from application/ld+json microdata."""
        extracted: List[DiscoveredUrlCandidate] = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw_text = script.string or script.get_text()
                if not raw_text or not raw_text.strip():
                    continue
                data = json.loads(raw_text)
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    type_ = str(item.get("@type", "")).lower()

                    # BreadcrumbList
                    if "breadcrumblist" in type_:
                        elem_list = item.get("itemListElement", [])
                        for elem in elem_list:
                            if isinstance(elem, dict):
                                cand_url = elem.get("item") or elem.get("id") or elem.get("url")
                                name = elem.get("name") or "Breadcrumb Item"
                                if cand_url and isinstance(cand_url, str):
                                    full = urljoin(base_url, cand_url)
                                    extracted.append(DiscoveredUrlCandidate(
                                        url=full,
                                        discovery_source=DiscoverySource.HEADER_NAV.value,
                                        referring_url=base_url,
                                        anchor_text=str(name)[:120],
                                        metadata={"breadcrumb": True, "json_ld": True},
                                    ))

                    # Organization / Corporation (sameAs)
                    elif any(t in type_ for t in ("organization", "corporation", "company")):
                        same_as = item.get("sameAs", [])
                        if isinstance(same_as, str):
                            same_as = [same_as]
                        for s_url in same_as:
                            if isinstance(s_url, str) and s_url.startswith(("http://", "https://")):
                                host = urlparse(s_url).netloc.lower()
                                if host in APPROVED_FOUNDATION_DOMAINS or any(f in host for f in ("foundation", "trust")):
                                    extracted.append(DiscoveredUrlCandidate(
                                        url=s_url,
                                        discovery_source=DiscoverySource.FOUNDATION.value,
                                        referring_url=base_url,
                                        anchor_text=str(item.get("name", "Corporate Foundation")),
                                        metadata={"json_ld": True, "type": "sameAs"},
                                    ))
                                elif match_ats_pattern(s_url, self.ats_patterns):
                                    extracted.append(DiscoveredUrlCandidate(
                                        url=s_url,
                                        discovery_source=DiscoverySource.ATS_PLATFORM.value,
                                        referring_url=base_url,
                                        anchor_text="ATS Careers Portal",
                                        metadata={"json_ld": True, "type": "sameAs"},
                                    ))

                    # JobPosting
                    elif "jobposting" in type_:
                        job_url = item.get("url") or item.get("directApply")
                        title = item.get("title", "Job Posting")
                        if job_url and isinstance(job_url, str):
                            full = urljoin(base_url, job_url)
                            ats_match = match_ats_pattern(full, self.ats_patterns)
                            source = DiscoverySource.ATS_PLATFORM.value if ats_match else DiscoverySource.BODY_CONTENT.value
                            extracted.append(DiscoveredUrlCandidate(
                                url=full,
                                discovery_source=source,
                                referring_url=base_url,
                                anchor_text=str(title)[:120],
                                metadata={"json_ld": True, "type": "JobPosting"},
                            ))
            except Exception:
                continue

        return extracted

    def crawl_homepage(
        self,
        base_url: str,
        html: str,
        allow_playwright: bool = True,
    ) -> List[DiscoveredUrlCandidate]:
        """
        Extracts DOM candidates and evaluates whether headless Playwright fallback is necessary.
        """
        candidates = self.extract_dom_candidates(base_url, html)

        # Evaluate triggering conditions
        link_count = len(candidates)
        header_link_count = sum(1 for c in candidates if c.discovery_source == DiscoverySource.HEADER_NAV.value)

        is_spa = False
        if html:
            soup = BeautifulSoup(html, "lxml")
            is_spa = bool(soup.find(id=re.compile(r"^(root|app|__next)$")) or soup.find(["app-root", "router-outlet"]))

        should_trigger = allow_playwright and (
            link_count < 5 or
            (is_spa and link_count < self.playwright_threshold) or
            (header_link_count == 0 and link_count < self.playwright_threshold)
        )

        if should_trigger:
            pw_candidates = self._execute_playwright_discovery(base_url)
            if pw_candidates:
                return pw_candidates

        return candidates

    def _execute_playwright_discovery(self, url: str) -> List[DiscoveredUrlCandidate]:
        """Executes bounded Playwright Chromium instance to render dynamic navigation."""
        try:
            collector = CandidateCollector(allow_playwright=True)
            pw_html = collector._fetch_with_playwright(url)
            if pw_html:
                return self.extract_dom_candidates(url, pw_html)
        except Exception as e:
            logger.debug("Playwright discovery error for %s: %s", url, e)
        return []

    def deduplicate_and_rank(self, candidates: List[DiscoveredUrlCandidate]) -> List[DiscoveredUrlCandidate]:
        """
        Deduplicates candidates by canonical normalized URL, preserving the candidate
        with the highest priority discovery source. Sorts output by priority descending.
        """
        best_candidates: Dict[str, DiscoveredUrlCandidate] = {}

        for c in candidates:
            norm = normalize_canonical_url(c.url, base_url=c.referring_url or c.url)
            if not norm:
                continue

            c_copy = DiscoveredUrlCandidate(
                url=norm,
                discovery_source=c.discovery_source,
                referring_url=c.referring_url,
                anchor_text=c.anchor_text,
                metadata=dict(c.metadata),
            )

            current_score = SOURCE_PRIORITY.get(c_copy.discovery_source, 0)
            if norm not in best_candidates:
                best_candidates[norm] = c_copy
            else:
                existing_score = SOURCE_PRIORITY.get(best_candidates[norm].discovery_source, 0)
                if current_score > existing_score:
                    best_candidates[norm] = c_copy
                else:
                    # Merge metadata
                    best_candidates[norm].metadata.update(c_copy.metadata)

        result = list(best_candidates.values())
        result.sort(key=lambda x: SOURCE_PRIORITY.get(x.discovery_source, 0), reverse=True)
        return result


def discover_company_urls(
    company_name: str,
    base_url: str,
    options: Optional[Dict[str, Any]] = None,
) -> List[DiscoveredUrlCandidate]:
    """
    Milestone 2 -> Milestone 3 Master Discovery Interface.
    Orchestrates:
    1. Input normalization and validation via M1 contract.
    2. Robots.txt directives & sitemap declarations (RFC 9309 compliant).
    3. Multi-format XML & .xml.gz sitemap parsing.
    4. Homepage navigation, mega-menus, breadcrumbs, JSON-LD microdata.
    5. Subdomain and common-path probing with CandidateCollector.
    6. Associated external domain and ATS platform mapping.
    7. Canonical deduplication and priority merge.
    Returns deduplicated list of DiscoveredUrlCandidate objects.
    """
    options = options or {}
    candidates: List[DiscoveredUrlCandidate] = []
    seen_urls: Set[str] = set()

    # 1. Normalize and validate inputs via M1 contract
    is_valid, norm_base_url, domain, err = normalize_and_validate_company(company_name, base_url)
    if not is_valid:
        logger.info("Validation rejected company '%s' with URL '%s': %s", company_name, base_url, err)
        return []

    # 2. Robots.txt
    robots_url = RobotsHandler._build_robots_url(norm_base_url)
    status_code, robots_content = fetch_raw_page(robots_url, timeout=options.get("timeout", 10))

    robots = RobotsHandler.from_content(
        content=robots_content,
        base_url=norm_base_url,
        status_code=status_code,
        allow_on_403=options.get("allow_on_403", False),
    )
    sitemaps_to_crawl = list(robots.get_sitemaps())

    # 3. Sitemaps
    sitemap_parser = SitemapParser(
        max_depth=options.get("max_sitemap_depth", 3),
        max_urls=options.get("max_sitemap_urls", 500),
        timeout=options.get("timeout", 10),
    )
    if not sitemaps_to_crawl:
        sitemaps_to_crawl.append(urljoin(norm_base_url, "/sitemap.xml"))

    for sm_url in sitemaps_to_crawl:
        sm_status, sm_content = fetch_raw_page(sm_url, timeout=options.get("timeout", 10))
        if sm_status == 200 and sm_content:
            sm_entries = sitemap_parser.parse_content(sm_content, sitemap_url=sm_url)
            for item in sm_entries:
                u = item.get("url") or item.get("loc")
                if not u:
                    continue
                norm_u = normalize_canonical_url(u, base_url=sm_url)
                if not norm_u:
                    continue
                is_junk, _ = is_junk_url(norm_u)
                if is_junk:
                    continue
                if norm_u not in seen_urls:
                    seen_urls.add(norm_u)
                    candidates.append(DiscoveredUrlCandidate(
                        url=norm_u,
                        discovery_source=DiscoverySource.SITEMAP.value,
                        referring_url=sm_url,
                        anchor_text="",
                        metadata=dict(item),
                    ))

    # 4. DOM & Navigation Discovery via URLDiscoveryEngine
    engine = URLDiscoveryEngine(playwright_threshold=options.get("playwright_threshold", 15))
    page_status, page_html = fetch_raw_page(norm_base_url, timeout=options.get("timeout", 10))

    if page_html:
        dom_cands = engine.crawl_homepage(
            norm_base_url,
            page_html,
            allow_playwright=options.get("allow_playwright", True),
        )
        for dc in dom_cands:
            norm_u = normalize_canonical_url(dc.url, base_url=norm_base_url)
            if not norm_u:
                continue
            is_junk, _ = is_junk_url(norm_u, dc.anchor_text)
            if is_junk:
                continue
            candidates.append(dc)

    # 5. External Domain, Subdomain & Common Path Discovery via CandidateCollector
    collector = CandidateCollector(
        allow_playwright=False,  # Already evaluated in step 4
        probe_sitemaps=False,    # Handled in step 3
        probe_subdomains=options.get("probe_subdomains", True),
        probe_common_paths=options.get("probe_common_paths", True),
        timeout=options.get("timeout", 10),
    )
    raw_collector_cands = collector.collect_candidates(
        homepage_url=norm_base_url,
        company_symbol=company_name,
        html_override=page_html,
        max_candidates=options.get("max_candidates", 100),
    )

    for rc in raw_collector_cands:
        u = rc.get("url")
        if not u:
            continue
        norm_u = normalize_canonical_url(u, base_url=norm_base_url)
        if not norm_u:
            continue

        source_val = rc.get("source", DiscoverySource.BODY_CONTENT.value)
        if rc.get("ats_match"):
            source_val = DiscoverySource.ATS_PLATFORM.value
        elif rc.get("external_linked") and any(k in norm_u.lower() for k in ("foundation", "trust")):
            source_val = DiscoverySource.FOUNDATION.value

        candidates.append(DiscoveredUrlCandidate(
            url=norm_u,
            discovery_source=source_val,
            referring_url=norm_base_url,
            anchor_text=rc.get("link_text", ""),
            metadata={
                "menu_path": rc.get("menu_path"),
                "ats_platform": rc.get("ats_platform"),
                "ownership_status": rc.get("ownership_status"),
                "requires_owner_verification": rc.get("requires_owner_verification", False),
                "discovered_at": datetime.now(timezone.utc).isoformat(),
            },
        ))

    # 6. Deduplicate, Rank, and Return
    deduped = engine.deduplicate_and_rank(candidates)
    return deduped
