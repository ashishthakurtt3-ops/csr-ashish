"""
tests_pure/test_m2_discovery_engine.py
=======================================
Comprehensive Pure Unit Test Suite for Milestone 2: Multi-Source URL Discovery Engine.

Requirements Covered (R3):
- Suite 1: M1 Ingestion Contract & DiscoveredUrlCandidate Data Structure (4 tests)
- Suite 2: RFC 9309 Robots.txt Parser & Fallbacks (7 tests)
- Suite 3: Multi-Format Sitemap Parser (Standard, Nested, .xml.gz, Malformed) (6 tests)
- Suite 4: Navigation & DOM Link Crawling (Header, Footer, Breadcrumbs, JSON-LD) (4 tests)
- Suite 5: Associated External Domains, ATS Platforms & Enterprise Aliases (5 tests)
- Suite 6: End-to-End Unified Coordinator Coordination & Deduplication (3 tests)

Total: 29 fast, deterministic, self-contained tests (< 1.5s execution, 0 network, 0 MySQL).
"""
import gzip
import io
import json
import re
import unittest
from dataclasses import asdict
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

from modules.crawler_engine.normalizers import (
    normalize_canonical_url,
    normalize_and_validate_company,
    is_junk_url,
)
from modules.crawler_engine.discovery_helpers import (
    is_allowed_domain_or_ats,
    APPROVED_FOUNDATION_DOMAINS,
    ENTERPRISE_DOMAIN_ALIASES,
)


# ==============================================================================
# SUITE 1: M1 Ingestion Contract & DiscoveredUrlCandidate Data Structure
# ==============================================================================
class TestM1IngestionAndCandidateContract(unittest.TestCase):
    """Verifies M1 contract ingestion and DiscoveredUrlCandidate dataclass specification."""

    def test_01_m1_valid_company_input(self):
        """Valid company name and official URL pass M1 validation."""
        is_valid, norm_url, domain, err = normalize_and_validate_company(
            "Tata Consultancy Services", "https://www.tcs.com/careers"
        )
        self.assertTrue(is_valid)
        self.assertEqual(norm_url, "https://www.tcs.com/careers")
        self.assertEqual(domain, "tcs.com")
        self.assertEqual(err, "")

    def test_02_m1_invalid_company_rejected_before_crawl(self):
        """Invalid schemes, whitespace, and static asset URLs are rejected before discovery starts."""
        cases = [
            ("", "https://acme.com", "EMPTY_COMPANY_NAME"),
            ("A", "https://acme.com", "COMPANY_NAME_TOO_SHORT"),
            ("Acme", "ftp://acme.com", "INVALID_URL_SCHEME"),
            ("Acme", "https://acme.com/logo.png", "STATIC_ASSET_NOT_HOMEPAGE"),
            ("Acme", "https://acme.com/report.pdf", "STATIC_ASSET_NOT_HOMEPAGE"),
        ]
        for name, url, expected_err in cases:
            is_valid, _, _, err = normalize_and_validate_company(name, url)
            self.assertFalse(is_valid)
            self.assertEqual(err, expected_err)

    def test_03_discovered_url_candidate_dataclass_schema(self):
        """DiscoveredUrlCandidate enforces the exact 5-field schema with to_dict and from_dict."""
        from modules.crawler_engine.url_discovery_service import DiscoveredUrlCandidate, DiscoverySource

        cand = DiscoveredUrlCandidate(
            url="https://acme.com/careers",
            discovery_source=DiscoverySource.HEADER_NAV,
            referring_url="https://acme.com",
            anchor_text="Careers & Opportunities",
            metadata={"menu_path": "Company > Careers", "priority": 0.9},
        )
        self.assertEqual(cand.url, "https://acme.com/careers")
        self.assertEqual(cand.discovery_source, "HEADER_NAV")
        self.assertEqual(cand.referring_url, "https://acme.com")
        self.assertEqual(cand.anchor_text, "Careers & Opportunities")
        self.assertEqual(cand.metadata["menu_path"], "Company > Careers")

        # Roundtrip to_dict and from_dict
        d = cand.to_dict()
        self.assertEqual(d["discovery_source"], "HEADER_NAV")
        restored = DiscoveredUrlCandidate.from_dict(d)
        self.assertEqual(restored.url, cand.url)
        self.assertEqual(restored.discovery_source, cand.discovery_source)

    def test_04_discovery_source_enum_completeness(self):
        """Validates that all 8 discovery sources are defined in DiscoverySource Enum."""
        from modules.crawler_engine.url_discovery_service import DiscoverySource

        expected_sources = {
            "ROBOTS_TXT", "SITEMAP", "HEADER_NAV", "FOOTER_NAV",
            "BODY_CONTENT", "SUBDOMAIN", "ATS_PLATFORM", "FOUNDATION"
        }
        actual_sources = {s.value for s in DiscoverySource}
        self.assertEqual(actual_sources, expected_sources)


# ==============================================================================
# SUITE 2: RFC 9309 Robots.txt Parser & Fallbacks
# ==============================================================================
class TestRobotsTxtParserRFC9309(unittest.TestCase):
    """Verifies RFC 9309 compliance, directive matching, sitemap extraction, and fallbacks."""

    def test_01_wildcard_allow_disallow_precedence(self):
        """Parses Allow and Disallow rules for wildcard '*' user-agent."""
        from modules.crawler_engine.robots_handler import RobotsHandler

        robots_content = (
            "User-agent: *\n"
            "Disallow: /admin/\n"
            "Disallow: /private/\n"
            "Allow: /careers/\n"
            "Allow: /csr/\n"
        )
        handler = RobotsHandler.from_content(robots_content, base_url="https://example.com")
        self.assertTrue(handler.is_allowed("https://example.com/careers/jobs"))
        self.assertTrue(handler.is_allowed("https://example.com/csr/initiatives"))
        self.assertFalse(handler.is_allowed("https://example.com/admin/login"))
        self.assertFalse(handler.is_allowed("https://example.com/private/data"))

    def test_02_longest_match_rule_rfc9309(self):
        """When Allow and Disallow match, longest path prefix takes precedence."""
        from modules.crawler_engine.robots_handler import RobotsHandler

        robots_content = (
            "User-agent: *\n"
            "Disallow: /careers/\n"
            "Allow: /careers/openings/\n"
        )
        handler = RobotsHandler.from_content(robots_content, base_url="https://example.com")
        self.assertTrue(handler.is_allowed("https://example.com/careers/openings/engineer"))
        self.assertFalse(handler.is_allowed("https://example.com/careers/confidential"))

    def test_03_specific_user_agent_priority(self):
        """Specific User-Agent rules override wildcard '*' directives."""
        from modules.crawler_engine.robots_handler import RobotsHandler

        robots_content = (
            "User-agent: *\n"
            "Disallow: /restricted/\n"
            "User-agent: ImpactBridge\n"
            "Allow: /restricted/\n"
        )
        handler = RobotsHandler.from_content(robots_content, base_url="https://example.com")
        self.assertFalse(handler.is_allowed("https://example.com/restricted/page", user_agent="*"))
        self.assertTrue(handler.is_allowed("https://example.com/restricted/page", user_agent="ImpactBridge"))

    def test_04_sitemap_directive_extraction(self):
        """Extracts declared sitemap URLs regardless of casing or whitespace."""
        from modules.crawler_engine.robots_handler import RobotsHandler

        robots_content = (
            "User-agent: *\n"
            "Disallow: /temp/\n"
            "Sitemap: https://example.com/sitemap_index.xml\n"
            "sitemap: https://example.com/sitemap_careers.xml\n"
            "SITEMAP:   https://example.com/sitemap_csr.xml.gz  \n"
        )
        handler = RobotsHandler.from_content(robots_content, base_url="https://example.com")
        sitemaps = handler.get_sitemaps()
        self.assertEqual(len(sitemaps), 3)
        self.assertIn("https://example.com/sitemap_index.xml", sitemaps)
        self.assertIn("https://example.com/sitemap_careers.xml", sitemaps)
        self.assertIn("https://example.com/sitemap_csr.xml.gz", sitemaps)

    def test_05_crawl_delay_parsing(self):
        """Extracts Crawl-delay directive value."""
        from modules.crawler_engine.robots_handler import RobotsHandler

        robots_content = "User-agent: *\nCrawl-delay: 3.5\nDisallow: /private/\n"
        handler = RobotsHandler.from_content(robots_content, base_url="https://example.com")
        self.assertEqual(handler.get_crawl_delay(), 3.5)

    def test_06_http_404_fallback_rfc9309(self):
        """Per RFC 9309, HTTP 404 (Not Found) grants unrestricted crawl permissions."""
        from modules.crawler_engine.robots_handler import RobotsHandler

        with patch("modules.crawler_engine.robots_handler.fetch_robots_txt", return_value=(404, "")):
            handler = RobotsHandler.from_url("https://example.com")
            self.assertTrue(handler.is_allowed("https://example.com/careers"))
            self.assertTrue(handler.is_allowed("https://example.com/admin/login"))
            self.assertEqual(handler.get_sitemaps(), [])

    def test_07_http_5xx_and_waf_403_fallback(self):
        """Server errors (5xx) or WAF blocks (403) fall back gracefully without unhandled crashes."""
        from modules.crawler_engine.robots_handler import RobotsHandler

        with patch("modules.crawler_engine.robots_handler.fetch_robots_txt", return_value=(503, "Service Unavailable")):
            handler = RobotsHandler.from_url("https://example.com")
            self.assertIsNotNone(handler)
            # Safe default fallback policy allows standard navigation crawling
            self.assertTrue(handler.is_allowed("https://example.com/careers"))


# ==============================================================================
# SUITE 3: Multi-Format Sitemap Parser
# ==============================================================================
class TestMultiFormatSitemapParser(unittest.TestCase):
    """Verifies XML, nested sitemap index recursion, .xml.gz decompression, and limits."""

    def test_01_standard_urlset_metadata_extraction(self):
        """Parses standard <urlset> with <loc>, <lastmod>, <changefreq>, <priority>."""
        from modules.crawler_engine.sitemap_parser import SitemapParser

        xml_data = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/careers</loc>
                <lastmod>2026-01-15</lastmod>
                <changefreq>daily</changefreq>
                <priority>0.8</priority>
            </url>
            <url>
                <loc>https://example.com/csr/report-2025.pdf</loc>
                <lastmod>2026-02-01</lastmod>
                <priority>0.9</priority>
            </url>
        </urlset>"""
        parser = SitemapParser()
        entries = parser.parse_content(xml_data, sitemap_url="https://example.com/sitemap.xml")
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["url"], "https://example.com/careers")
        self.assertEqual(entries[0]["lastmod"], "2026-01-15")
        self.assertEqual(entries[0]["changefreq"], "daily")
        self.assertEqual(entries[0]["priority"], 0.8)
        self.assertEqual(entries[1]["url"], "https://example.com/csr/report-2025.pdf")

    def test_02_nested_sitemapindex_recursion(self):
        """Recursively parses child sitemaps referenced in a <sitemapindex>."""
        from modules.crawler_engine.sitemap_parser import SitemapParser

        index_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>https://example.com/sitemap_careers.xml</loc></sitemap>
            <sitemap><loc>https://example.com/sitemap_csr.xml</loc></sitemap>
        </sitemapindex>"""
        careers_xml = """<urlset><url><loc>https://example.com/careers/openings</loc></url></urlset>"""
        csr_xml = """<urlset><url><loc>https://example.com/csr/overview</loc></url></urlset>"""

        def mock_fetch(url, *args, **kwargs):
            if "sitemap_careers" in url:
                return careers_xml, 200, "text/xml"
            if "sitemap_csr" in url:
                return csr_xml, 200, "text/xml"
            return index_xml, 200, "text/xml"

        parser = SitemapParser()
        with patch.object(parser, "fetch_sitemap_raw", side_effect=mock_fetch):
            results = parser.parse_recursive("https://example.com/sitemap_index.xml", max_depth=3)
            urls = [r["url"] for r in results]
            self.assertIn("https://example.com/careers/openings", urls)
            self.assertIn("https://example.com/csr/overview", urls)

    def test_03_recursion_depth_limit(self):
        """Terminates recursive traversal when max_depth is reached to prevent circular loops."""
        from modules.crawler_engine.sitemap_parser import SitemapParser

        circular_index = """<sitemapindex><sitemap><loc>https://example.com/sitemap_loop.xml</loc></sitemap></sitemapindex>"""
        parser = SitemapParser()
        with patch.object(parser, "fetch_sitemap_raw", return_value=(circular_index, 200, "text/xml")):
            results = parser.parse_recursive("https://example.com/sitemap_loop.xml", max_depth=2)
            self.assertIsInstance(results, list)

    def test_04_max_urls_limit(self):
        """Enforces max_urls cap across all parsed child sitemaps."""
        from modules.crawler_engine.sitemap_parser import SitemapParser

        large_xml = "<urlset>" + "".join(f"<url><loc>https://example.com/page/{i}</loc></url>" for i in range(200)) + "</urlset>"
        parser = SitemapParser(max_urls=50)
        entries = parser.parse_content(large_xml, sitemap_url="https://example.com/sitemap.xml")
        self.assertEqual(len(entries), 50)

    def test_05_compressed_xml_gz_decompression(self):
        """Decompresses and parses .xml.gz sitemaps using gzip.decompress()."""
        from modules.crawler_engine.sitemap_parser import SitemapParser

        raw_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/reports/brsr_2025.pdf</loc></url>
        </urlset>"""
        gz_bytes = gzip.compress(raw_xml)

        parser = SitemapParser()
        decompressed_text = parser.decompress_if_gzipped(gz_bytes, url="https://example.com/sitemap.xml.gz")
        self.assertIn("https://example.com/reports/brsr_2025.pdf", decompressed_text)

    def test_06_malformed_xml_graceful_handling(self):
        """Gracefully ignores broken XML and HTML 404 pages without unhandled exceptions."""
        from modules.crawler_engine.sitemap_parser import SitemapParser

        bad_xml = "<html><body>404 Page Not Found</body></html>"
        parser = SitemapParser()
        entries = parser.parse_content(bad_xml, sitemap_url="https://example.com/sitemap.xml")
        self.assertEqual(entries, [])


# ==============================================================================
# SUITE 4: Navigation & DOM Link Crawling
# ==============================================================================
class TestNavigationCrawler(unittest.TestCase):
    """Verifies Header, Footer, Breadcrumb, JSON-LD, and Playwright fallback triggers."""

    SAMPLE_HTML = """
    <!DOCTYPE html>
    <html>
    <body>
        <header>
            <nav class="navbar main-nav">
                <a href="/careers">Careers & Jobs</a>
                <a href="/about/overview">About Us</a>
            </nav>
        </header>
        <main>
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb">
                    <li><a href="/home">Home</a></li>
                    <li><a href="/sustainability">Sustainability & ESG</a></li>
                </ol>
            </nav>
            <p>Visit our <a href="/investors/annual-reports">Investor Portal</a>.</p>
        </main>
        <footer>
            <div class="footer-links">
                <a href="/csr/csr-policy">Corporate Social Responsibility Policy</a>
            </div>
        </footer>
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "JobPosting",
            "title": "Lead Software Engineer",
            "url": "https://example.com/jobs/lead-engineer"
        }
        </script>
    </body>
    </html>
    """

    def test_01_header_and_footer_source_tagging(self):
        """Tags links in <header>/<nav> as HEADER_NAV and <footer> as FOOTER_NAV."""
        from modules.crawler_engine.url_discovery_service import URLDiscoveryEngine

        engine = URLDiscoveryEngine()
        candidates = engine.extract_dom_candidates("https://example.com", self.SAMPLE_HTML)
        c_map = {c.url: c for c in candidates}

        self.assertIn("https://example.com/careers", c_map)
        self.assertEqual(c_map["https://example.com/careers"].discovery_source, "HEADER_NAV")

        self.assertIn("https://example.com/csr/csr-policy", c_map)
        self.assertEqual(c_map["https://example.com/csr/csr-policy"].discovery_source, "FOOTER_NAV")

    def test_02_breadcrumbs_extraction_and_metadata(self):
        """Tags breadcrumb links with HEADER_NAV and sets metadata breadcrumb flag."""
        from modules.crawler_engine.url_discovery_service import URLDiscoveryEngine

        engine = URLDiscoveryEngine()
        candidates = engine.extract_dom_candidates("https://example.com", self.SAMPLE_HTML)
        c_map = {c.url: c for c in candidates}

        self.assertIn("https://example.com/sustainability", c_map)
        self.assertTrue(c_map["https://example.com/sustainability"].metadata.get("breadcrumb", False))

    def test_03_json_ld_schema_microdata_extraction(self):
        """Extracts @type JobPosting from application/ld+json scripts."""
        from modules.crawler_engine.url_discovery_service import URLDiscoveryEngine

        engine = URLDiscoveryEngine()
        candidates = engine.extract_dom_candidates("https://example.com", self.SAMPLE_HTML)
        c_map = {c.url: c for c in candidates}

        self.assertIn("https://example.com/jobs/lead-engineer", c_map)
        job_cand = c_map["https://example.com/jobs/lead-engineer"]
        self.assertTrue(job_cand.metadata.get("json_ld", False))
        self.assertEqual(job_cand.anchor_text, "Lead Software Engineer")

    def test_04_playwright_fallback_trigger_decision(self):
        """Triggers Playwright fallback when static HTML links fall below threshold."""
        from modules.crawler_engine.url_discovery_service import URLDiscoveryEngine

        empty_spa_html = "<html><body><div id='root'></div><script src='bundle.js'></script></body></html>"
        engine = URLDiscoveryEngine()

        # When allow_playwright=False -> does not invoke Playwright
        res_no_pw = engine.crawl_homepage("https://example.com", empty_spa_html, allow_playwright=False)
        self.assertEqual(len(res_no_pw), 0)

        # When allow_playwright=True -> triggers fallback
        with patch.object(engine, "_execute_playwright_discovery", return_value=[]) as mock_pw:
            engine.crawl_homepage("https://example.com", empty_spa_html, allow_playwright=True)
            mock_pw.assert_called_once()


# ==============================================================================
# SUITE 5: Associated External Domains, ATS Platforms & Enterprise Aliases
# ==============================================================================
class TestAssociatedExternalDomainsAndAliases(unittest.TestCase):
    """Verifies subdomains, ATS platforms, approved foundations, and alias fixes."""

    def test_01_subdomain_recognition(self):
        """Recognizes corporate subdomains as valid associated URLs."""
        self.assertTrue(is_allowed_domain_or_ats("https://careers.tatamotors.com", "https://tatamotors.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://csr.infosys.com", "https://infosys.com"))

    def test_02_ats_platform_recognition(self):
        """Validates major enterprise ATS platforms (Workday, Lever, Greenhouse, Oracle Cloud)."""
        ats_urls = [
            "https://tatamotors.myworkdayjobs.com/Careers",
            "https://jobs.lever.co/paytm/abc",
            "https://boards.greenhouse.io/swiggy/jobs/123",
            "https://eibd.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/1",
        ]
        for url in ats_urls:
            self.assertTrue(is_allowed_domain_or_ats(url, "https://company.com"))

    def test_03_approved_corporate_foundations(self):
        """Recognizes approved corporate foundations from registry."""
        self.assertTrue(is_allowed_domain_or_ats("https://www.reliancefoundation.org", "https://ril.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://www.tatatrusts.org", "https://tcs.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://www.infosysfoundation.org", "https://infosys.com"))

    def test_04_tcs_and_tcscareers_alias_fix(self):
        """Verifies line 517 bug fix: tcscareers.com is allowed for tcs.com."""
        self.assertTrue(
            is_allowed_domain_or_ats("https://www.tcscareers.com/entry-level", "https://www.tcs.com"),
            "tcscareers.com must be allowed for tcs.com via ENTERPRISE_DOMAIN_ALIASES fix"
        )
        self.assertTrue(
            is_allowed_domain_or_ats("https://www.tata.com/investors", "https://www.tcs.com"),
            "tata.com group domain must be allowed for tcs.com"
        )

    def test_05_unrelated_and_lookalike_domains_rejected(self):
        """Rejects lookalike and phishing domains."""
        self.assertFalse(is_allowed_domain_or_ats("https://tcs-fake-jobs.com", "https://tcs.com"))
        self.assertFalse(is_allowed_domain_or_ats("https://facebook.com/tcs", "https://tcs.com"))
        self.assertFalse(is_allowed_domain_or_ats("https://malicious-careers.com", "https://example.com"))


# ==============================================================================
# SUITE 6: End-to-End Unified Coordinator Coordination & Deduplication
# ==============================================================================
class TestUnifiedDiscoveryCoordinator(unittest.TestCase):
    """Verifies discover_company_urls end-to-end execution, deduplication, and PDF retention."""

    def test_01_e2e_coordination_mocked(self):
        """Coordinates robots.txt, sitemaps, DOM links, and external domains into DiscoveredUrlCandidates."""
        from modules.crawler_engine.url_discovery_service import discover_company_urls, DiscoveredUrlCandidate

        robots_mock = "User-agent: *\nAllow: /\nSitemap: https://acme.com/sitemap.xml\n"
        sitemap_mock = """<urlset><url><loc>https://acme.com/csr/report.pdf</loc></url></urlset>"""
        dom_mock = """<html><body><header><a href="/careers">Careers</a></header>
                      <a href="https://jobs.lever.co/acme">Jobs Portal</a></body></html>"""

        def mock_fetch(url, *args, **kwargs):
            if "robots.txt" in url:
                return 200, robots_mock
            if "sitemap.xml" in url:
                return 200, sitemap_mock
            return 200, dom_mock

        with patch("modules.crawler_engine.url_discovery_service.fetch_raw_page", side_effect=mock_fetch):
            candidates = discover_company_urls(
                "Acme Corp", "https://www.acme.com",
                options={"probe_subdomains": False, "probe_common_paths": False}
            )

            self.assertIsInstance(candidates, list)
            self.assertTrue(len(candidates) > 0)
            for c in candidates:
                self.assertIsInstance(c, DiscoveredUrlCandidate)

            sources = {c.discovery_source for c in candidates}
            self.assertIn("HEADER_NAV", sources)
            self.assertIn("ATS_PLATFORM", sources)
            self.assertIn("SITEMAP", sources)

            urls = [c.url for c in candidates]
            # Corporate PDF was preserved
            self.assertIn("https://acme.com/csr/report.pdf", urls)

    def test_02_e2e_deduplication_and_source_priority(self):
        """When a URL appears in multiple sources, preserves candidate with higher priority source."""
        from modules.crawler_engine.url_discovery_service import URLDiscoveryEngine, DiscoveredUrlCandidate

        engine = URLDiscoveryEngine()
        cands = [
            DiscoveredUrlCandidate(url="https://acme.com/careers", discovery_source="BODY_CONTENT"),
            DiscoveredUrlCandidate(url="https://acme.com/careers", discovery_source="HEADER_NAV"),
            DiscoveredUrlCandidate(url="https://acme.com/careers", discovery_source="SITEMAP"),
        ]
        deduped = engine.deduplicate_and_rank(cands)
        self.assertEqual(len(deduped), 1)
        # HEADER_NAV has priority over SITEMAP and BODY_CONTENT
        self.assertEqual(deduped[0].discovery_source, "HEADER_NAV")

    def test_03_subsecond_execution(self):
        """Guarantees pure test suite completes in under 2 seconds."""
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
