"""
tests_pure/test_tier1_features.py
=================================
Tier 1 Feature Coverage Test Suite for the Autonomous Company URL Discovery
and Content Extraction Engine.

Covers all 14 core features with category-partition equivalence class representatives:
- Feature 1: Single Company Submission & Validation
- Feature 2: Bulk Ingestion Engine
- Feature 3: RFC-Compliant Robots.txt Handler
- Feature 4: Multi-Format Sitemap Parser
- Feature 5: Navigation & Internal Page Discovery
- Feature 6: Associated External Domain Discovery
- Feature 7: URL Normalization & Deduplication
- Feature 8: Multi-Tier URL Classification
- Feature 9: Live URL Verification Engine
- Feature 10: Boilerplate-Free HTML Content Extractor
- Feature 11: Corporate PDF Extraction Engine
- Feature 12: Transaction-Safe MySQL Persistence
- Feature 13: Concurrency, Retries & Structured Logging
- Feature 14: Standardized Outcome Codes

All network I/O and external systems are cleanly mocked for sub-second execution.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import re
import sys
import unittest
import urllib.parse
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

from bs4 import BeautifulSoup

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Initialize Django for models/services without database dependency
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

try:
    django.setup()
except Exception:
    pass

import trafilatura
from modules.admin_panel.models.evidence import VerifiableModel
from modules.admin_panel.services.batch_discovery_service import (
    BatchDiscoveryService,
)
from modules.crawler_engine.discovery_helpers import (
    ALLOWED_ATS_HOSTS,
    APPROVED_FOUNDATION_DOMAINS,
    ENTERPRISE_DOMAIN_ALIASES,
    get_registrable_domain,
    is_allowed_domain_or_ats,
)
from modules.crawler_engine.link_verifier import (
    build_highlight_url,
    title_matches,
    verify_url_live,
)
from modules.crawler_engine.normalizers import (
    build_job_fingerprint,
    clean_text,
    is_junk_url,
    load_ats_patterns,
    match_ats_pattern,
    normalize_canonical_url,
)
from modules.crawler_engine.ai_api_client import (
    AIClientError,
    MockAIClient,
    OpenAICompatibleApiClient,
    PrimaryFallbackAIClient,
)
from modules.crawler_engine.crawler import start_background_crawl
from modules.crawler_engine.page_classifier import TwoStagePageClassifier
from modules.crawler_engine.parsers.corporate import CorporateHTMLParser
from modules.crawler_engine.parsers.csr_pdf import CSRPdfParser
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor
from modules.crawler_engine.parsers.generic import GenericHTMLParser
from modules.crawler_engine.pdf_extractor import PDFReportExtractor
from modules.crawler_engine.state import CRAWL_TASK_STATE, log_event
from modules.crawler_engine.strategies.base import ExtractionContext
from modules.crawler_engine.strategies.sitemap_strategy import JobSitemapStrategy


# ==============================================================================
# FEATURE 1: Single Company Submission & Validation
# ==============================================================================
class TestTier1Feature01SingleCompanySubmission(unittest.TestCase):
    """Tier 1: Validation and normalization of individual company submissions."""

    def test_01_valid_company_name_and_https_url(self):
        """Accepts valid company name and standard HTTPS URL, normalizing keys."""
        raw_row = {
            "Company Name": "Infosys Limited",
            "Homepage URL": "https://www.infosys.com",
        }
        normalized = BatchDiscoveryService._normalize_row(raw_row)
        self.assertEqual(normalized["company_name"], "Infosys Limited")
        self.assertEqual(normalized["website_url"], "https://www.infosys.com")
        self.assertEqual(normalized["homepage_url"], "https://www.infosys.com")

    def test_02_schemeless_url_auto_prefixes_https(self):
        """Automatically prepends 'https://' to valid schemeless domains."""
        sanitized = BatchDiscoveryService._sanitize_url("tcs.com")
        self.assertEqual(sanitized, "https://tcs.com")

        sanitized_sub = BatchDiscoveryService._sanitize_url("careers.tatamotors.com")
        self.assertEqual(sanitized_sub, "https://careers.tatamotors.com")

    def test_03_whitespace_stripping_and_clean_keys(self):
        """Strips leading/trailing whitespace from company name and URL."""
        raw_row = {
            "  Company Name  ": "  3M India Limited  ",
            "  Homepage URL  ": "  https://www.3mindia.in  ",
        }
        normalized = BatchDiscoveryService._normalize_row(raw_row)
        self.assertEqual(normalized["company_name"], "3M India Limited")
        self.assertEqual(normalized["homepage_url"], "https://www.3mindia.in")

    def test_04_valid_url_with_port_and_path(self):
        """Accepts URLs containing custom ports, paths, and trailing slashes."""
        url = "https://portal.example.com:8443/corporate/home/"
        sanitized = BatchDiscoveryService._sanitize_url(url)
        self.assertEqual(sanitized, "https://portal.example.com:8443/corporate/home")

    def test_05_multi_part_tld_and_case_lowercasing(self):
        """Lowercases scheme and domain while preserving valid multi-part TLDs."""
        url = "HTTPS://WWW.RELIANCE.CO.IN/corporate"
        sanitized = BatchDiscoveryService._sanitize_url(url)
        self.assertTrue(sanitized.startswith("https://www.reliance.co.in/"))

    def test_06_reject_non_http_schemes(self):
        """Strictly rejects mailto, javascript, ftp, and tel URIs."""
        for bad_uri in [
            "ftp://files.company.com",
            "mailto:info@company.com",
            "javascript:void(0)",
            "tel:+919876543210",
        ]:
            sanitized = BatchDiscoveryService._sanitize_url(bad_uri)
            self.assertEqual(sanitized, "", f"Expected empty string for {bad_uri}")

    def test_07_discard_extraneous_columns(self):
        """Strips careers, CSR, sector, and ticker columns from single submission."""
        raw_row = {
            "Company Name": "Paytm",
            "Homepage URL": "https://paytm.com",
            "Careers URL": "https://careers.paytm.com",
            "CSR URL": "https://csr.paytm.com",
            "Sector": "FinTech",
            "Headquarters": "Noida",
            "NSE Symbol": "PAYTM",
        }
        normalized = BatchDiscoveryService._normalize_row(raw_row)
        self.assertEqual(set(normalized.keys()), {"company_name", "website_url", "homepage_url"})
        self.assertEqual(normalized["company_name"], "Paytm")
        self.assertEqual(normalized["homepage_url"], "https://paytm.com")


# ==============================================================================
# FEATURE 2: Bulk Ingestion Engine
# ==============================================================================
class TestTier1Feature02BulkIngestionEngine(unittest.TestCase):
    """Tier 1: Bulk ingestion parsing across CSV, TSV, JSON, Excel and row isolation."""

    def test_01_csv_ingestion_standard_comma(self):
        """Parses standard comma-separated CSV with header row."""
        csv_content = (
            "Company Name,Homepage URL\n"
            "Infosys Limited,https://www.infosys.com\n"
            "Wipro Limited,https://www.wipro.com\n"
        ).encode("utf-8")
        file_obj = io.BytesIO(csv_content)
        records = BatchDiscoveryService.parse_uploaded_file(file_obj, "companies.csv")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["company_name"], "Infosys Limited")
        self.assertEqual(records[1]["company_name"], "Wipro Limited")

    def test_02_tsv_ingestion_tab_delimited(self):
        """Parses tab-separated values (.tsv) file."""
        tsv_content = (
            "company_name\thomepage_url\n"
            "Tata Motors\thttps://www.tatamotors.com\n"
            "Mahindra\thttps://www.mahindra.com\n"
        ).encode("utf-8")
        file_obj = io.BytesIO(tsv_content)
        records = BatchDiscoveryService.parse_uploaded_file(file_obj, "companies.tsv")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["company_name"], "Tata Motors")
        self.assertEqual(records[1]["company_name"], "Mahindra")

    def test_03_pipe_and_semicolon_delimited_sniffing(self):
        """Auto-detects pipe '|' and semicolon ';' delimiters."""
        pipe_content = (
            "Company Name|Homepage URL\n"
            "HCL Technologies|https://www.hcltech.com\n"
        ).encode("utf-8")
        records_pipe = BatchDiscoveryService.parse_uploaded_file(io.BytesIO(pipe_content), "companies.txt")
        self.assertEqual(len(records_pipe), 1)
        self.assertEqual(records_pipe[0]["company_name"], "HCL Technologies")

        semi_content = (
            "Company Name;Homepage URL\n"
            "Tech Mahindra;https://www.techmahindra.com\n"
        ).encode("utf-8")
        records_semi = BatchDiscoveryService.parse_uploaded_file(io.BytesIO(semi_content), "companies.txt")
        self.assertEqual(len(records_semi), 1)
        self.assertEqual(records_semi[0]["company_name"], "Tech Mahindra")

    def test_04_json_ingestion_array_and_object(self):
        """Parses JSON input both as array of dicts and nested object with 'companies' key."""
        json_array = json.dumps([
            {"company_name": "Titan Company", "homepage_url": "https://www.titan.co.in"},
            {"company_name": "L&T", "homepage_url": "https://www.larsentoubro.com"},
        ]).encode("utf-8")
        records_arr = BatchDiscoveryService.parse_uploaded_file(io.BytesIO(json_array), "companies.json")
        self.assertEqual(len(records_arr), 2)

        json_obj = json.dumps({
            "companies": [
                {"company_name": "Aarti Drugs", "homepage_url": "https://www.aartidrugs.com"}
            ]
        }).encode("utf-8")
        records_obj = BatchDiscoveryService.parse_uploaded_file(io.BytesIO(json_obj), "companies.json")
        self.assertEqual(len(records_obj), 1)
        self.assertEqual(records_obj[0]["company_name"], "Aarti Drugs")

    def test_05_excel_xlsx_ingestion(self):
        """Parses Microsoft Excel .xlsx workbook using openpyxl."""
        import openpyxl

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Company Name", "Homepage URL"])
        ws.append(["Cipla Limited", "https://www.cipla.com"])
        ws.append(["Dr Reddys", "https://www.drreddys.com"])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        records = BatchDiscoveryService.parse_uploaded_file(buf, "companies.xlsx")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["company_name"], "Cipla Limited")
        self.assertEqual(records[1]["company_name"], "Dr Reddys")

    def test_06_row_isolation_partial_failures(self):
        """Row failures do not interrupt processing of remaining valid rows."""
        mixed_csv = (
            "Company Name,Homepage URL\n"
            "Valid Co 1,https://valid1.com\n"
            "Bad Co Missing URL,\n"
            "Valid Co 2,https://valid2.com\n"
            "Bad Co Scheme,ftp://bad-scheme.com\n"
        ).encode("utf-8")
        records = BatchDiscoveryService.parse_uploaded_file(io.BytesIO(mixed_csv), "mixed.csv")
        # Valid records are parsed; malformed ones with missing or invalid URLs are excluded
        valid_names = [r["company_name"] for r in records if r["homepage_url"]]
        self.assertIn("Valid Co 1", valid_names)
        self.assertIn("Valid Co 2", valid_names)
        self.assertNotIn("Bad Co Scheme", [r["company_name"] for r in records if r["homepage_url"]])


# ==============================================================================
# FEATURE 3: RFC-Compliant Robots.txt Handler
# ==============================================================================
class TestTier1Feature03RobotsTxtHandler(unittest.TestCase):
    """Tier 1: RFC-compliant Robots.txt parsing, directive enforcement, and sitemap extraction."""

    def test_01_robots_sitemap_directive_extraction_via_batch_discovery(self):
        """Extracts declared sitemap URLs from robots.txt content using BatchDiscoveryService."""
        robots_txt = (
            "User-agent: *\n"
            "Disallow: /admin/\n"
            "Sitemap: https://target.com/sitemap_index.xml\n"
            "Sitemap: https://target.com/sitemap_jobs.xml\n"
        )
        sitemap_xml = "<urlset><url><loc>https://target.com/careers/engineering</loc></url></urlset>"

        def fake_fetch(url, timeout=5):
            if "robots.txt" in url:
                return robots_txt, "", 200
            elif "sitemap" in url:
                return sitemap_xml, "", 200
            return "", "", 404

        with patch.object(BatchDiscoveryService, "fetch_page_content", side_effect=fake_fetch):
            discovered = BatchDiscoveryService._fetch_sitemap_urls("https://target.com")
            self.assertIn("https://target.com/careers/engineering", discovered)

    def test_02_robots_fallback_to_standard_sitemap_when_no_sitemap_directive(self):
        """Probes /sitemap.xml as standard RFC fallback when robots.txt lacks Sitemap directives."""
        robots_txt = "User-agent: *\nDisallow: /admin/\nDisallow: /private/\n"
        standard_sitemap = "<urlset><url><loc>https://target.com/csr/overview</loc></url></urlset>"

        def fake_fetch(url, timeout=5):
            if "robots.txt" in url:
                return robots_txt, "", 200
            elif url.endswith("/sitemap.xml"):
                return standard_sitemap, "", 200
            return "", "", 404

        with patch.object(BatchDiscoveryService, "fetch_page_content", side_effect=fake_fetch):
            discovered = BatchDiscoveryService._fetch_sitemap_urls("https://target.com")
            self.assertIn("https://target.com/csr/overview", discovered)

    def test_03_robots_fetch_http_failure_handled_gracefully(self):
        """Recovers gracefully without exception when robots.txt returns 404 or connection fails."""
        def fake_fetch(url, timeout=5):
            if "robots.txt" in url:
                return "", "", 404
            elif url.endswith("/sitemap.xml"):
                return "<urlset><url><loc>https://target.com/portal</loc></url></urlset>", "", 200
            return "", "", 404

        with patch.object(BatchDiscoveryService, "fetch_page_content", side_effect=fake_fetch):
            discovered = BatchDiscoveryService._fetch_sitemap_urls("https://target.com")
            self.assertIn("https://target.com/portal", discovered)

    def test_04_robots_empty_or_malformed_origin_returns_empty(self):
        """Returns empty list immediately when origin URL is missing scheme, netloc, or empty."""
        for invalid_base in ["", "not_a_valid_url", "http://", "https://"]:
            discovered = BatchDiscoveryService._fetch_sitemap_urls(invalid_base)
            self.assertEqual(discovered, [])

    def test_05_job_sitemap_strategy_detects_robots_sitemap_presence(self):
        """JobSitemapStrategy.detect inspects robots.txt and identifies sitemap declarations."""
        strategy = JobSitemapStrategy()
        ctx = ExtractionContext(company=MagicMock(), careers_url="https://example.com/careers")

        mock_resp_with_sitemap = MagicMock(status_code=200, text="User-agent: *\nSitemap: https://example.com/sitemap.xml\n")
        with patch("curl_cffi.requests.get", return_value=mock_resp_with_sitemap):
            self.assertTrue(strategy.detect(ctx))

        mock_resp_404 = MagicMock(status_code=404, text="Not Found")
        with patch("curl_cffi.requests.get", return_value=mock_resp_404):
            self.assertFalse(strategy.detect(ctx))

    def test_06_robots_sitemap_bounding_limits_enforced(self):
        """Enforces max_sitemaps and max_urls bounds to prevent infinite crawl expansion."""
        robots_txt = "User-agent: *\n" + "\n".join(f"Sitemap: https://target.com/sitemap_{i}.xml" for i in range(20))
        single_url_xml = "<urlset>" + "".join(f"<url><loc>https://target.com/page_{j}</loc></url>" for j in range(50)) + "</urlset>"

        def fake_fetch(url, timeout=5):
            if "robots.txt" in url:
                return robots_txt, "", 200
            return single_url_xml, "", 200

        with patch.object(BatchDiscoveryService, "fetch_page_content", side_effect=fake_fetch):
            discovered = BatchDiscoveryService._fetch_sitemap_urls("https://target.com", max_sitemaps=2, max_urls=15)
            self.assertLessEqual(len(discovered), 15)


# ==============================================================================
# FEATURE 4: Multi-Format Sitemap Parser
# ==============================================================================
class TestTier1Feature04SitemapParser(unittest.TestCase):
    """Tier 1: Multi-format XML sitemaps, nested index recursion, and target classification."""

    def test_01_xml_urlset_parsing_and_entity_unescaping(self):
        """Extracts and unescapes XML entities from standard <urlset> sitemaps."""
        xml_content = (
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            "<url><loc>https://example.com/jobs?dept=eng&amp;id=101</loc></url>"
            "<url><loc>https://example.com/csr/annual-summary</loc></url>"
            "</urlset>"
        )

        def fake_fetch(url, timeout=5):
            if url.endswith("/sitemap.xml"):
                return xml_content, "", 200
            return "", "", 404

        with patch.object(BatchDiscoveryService, "fetch_page_content", side_effect=fake_fetch):
            discovered = BatchDiscoveryService._fetch_sitemap_urls("https://example.com")
            self.assertIn("https://example.com/jobs?dept=eng&id=101", discovered)
            self.assertIn("https://example.com/csr/annual-summary", discovered)

    def test_02_nested_sitemapindex_traversal(self):
        """Discovers and recursively traverses child sitemaps listed in <sitemapindex>."""
        index_xml = (
            "<sitemapindex xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            "<sitemap><loc>https://example.com/sitemap_careers.xml</loc></sitemap>"
            "</sitemapindex>"
        )
        child_xml = (
            "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
            "<url><loc>https://example.com/careers/lead-architect</loc></url>"
            "</urlset>"
        )

        def fake_fetch(url, timeout=5):
            if url.endswith("/sitemap.xml"):
                return index_xml, "", 200
            elif "sitemap_careers.xml" in url:
                return child_xml, "", 200
            return "", "", 404

        with patch.object(BatchDiscoveryService, "fetch_page_content", side_effect=fake_fetch):
            discovered = BatchDiscoveryService._fetch_sitemap_urls("https://example.com")
            self.assertIn("https://example.com/careers/lead-architect", discovered)

    def test_03_job_sitemap_strategy_extracts_openings(self):
        """JobSitemapStrategy.extract parses XML sitemap and extracts structured job entities."""
        strategy = JobSitemapStrategy()
        ctx = ExtractionContext(company=MagicMock(), careers_url="https://example.com/careers")

        sitemap_xml = b"<urlset><url><loc>https://example.com/jobs/staff-developer-101</loc></url></urlset>"
        detail_html = "<html><head><title>Staff Developer - Careers</title></head><body><h1>Staff Developer</h1></body></html>"

        def fake_get(url, **kwargs):
            resp = MagicMock(status_code=200)
            if "robots.txt" in url:
                resp.text = "User-agent: *\nSitemap: https://example.com/sitemap-jobs.xml\n"
                resp.content = resp.text.encode("utf-8")
            elif "sitemap" in url:
                resp.text = sitemap_xml.decode("utf-8")
                resp.content = sitemap_xml
            else:
                resp.text = detail_html
                resp.content = detail_html.encode("utf-8")
            return resp

        with patch("curl_cffi.requests.get", side_effect=fake_get):
            jobs = strategy.extract(ctx)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["title"], "Staff Developer")
            self.assertEqual(jobs[0]["application_url"], "https://example.com/jobs/staff-developer-101")
            self.assertEqual(jobs[0]["link_quality"], "DIRECT")

    def test_04_sitemap_target_categorization(self):
        """Categorizes discovered sitemap URLs into careers, csr, and reports."""
        urls = [
            "https://acme.com/careers/openings",
            "https://acme.com/csr/community-development",
            "https://acme.com/reports/annual-report-2025.pdf",
            "https://acme.com/products/widgets",
        ]
        targets = BatchDiscoveryService._pick_sitemap_targets(urls, "acme.com")
        self.assertIn("https://acme.com/careers/openings", targets["careers"])
        self.assertIn("https://acme.com/csr/community-development", targets["csr"])
        self.assertIn("https://acme.com/reports/annual-report-2025.pdf", targets["reports"])
        self.assertNotIn("https://acme.com/products/widgets", targets["careers"])

    def test_05_sitemap_target_deduplication_and_ranking(self):
        """Deduplicates URLs and prioritizes shallow hub URLs for careers and CSR."""
        urls = [
            "https://acme.com/careers/deep/sub/path/job/1",
            "https://acme.com/careers",
            "https://acme.com/careers",
        ]
        targets = BatchDiscoveryService._pick_sitemap_targets(urls, "acme.com")
        self.assertEqual(len(targets["careers"]), 2)
        # Shallow hub sorted first
        self.assertEqual(targets["careers"][0], "https://acme.com/careers")

    def test_06_sitemap_target_cross_domain_filtering(self):
        """Rejects unrelated third-party domains encountered in sitemaps."""
        urls = [
            "https://acme.com/careers/openings",
            "https://thirdparty-tracker.com/pixel",
            "https://unrelated-domain.org/page",
        ]
        targets = BatchDiscoveryService._pick_sitemap_targets(urls, "acme.com")
        self.assertIn("https://acme.com/careers/openings", targets["careers"])
        self.assertNotIn("https://thirdparty-tracker.com/pixel", targets["careers"])
        self.assertNotIn("https://unrelated-domain.org/page", targets["csr"])


# ==============================================================================
# FEATURE 5: Navigation & Internal Page Discovery
# ==============================================================================
class TestTier1Feature05NavigationDiscovery(unittest.TestCase):
    """Tier 1: Header/footer, mega-menu, relative links, and anchor extraction."""

    def setUp(self):
        self.classifier = TwoStagePageClassifier(client=MagicMock())

    def test_01_header_nav_location_tagging(self):
        """Tags candidate links inside <header> or <nav> as HEADER_NAV."""
        html = """
        <html>
            <body>
                <header>
                    <nav>
                        <a href="/careers">Careers & Jobs</a>
                    </nav>
                </header>
            </body>
        </html>
        """
        cands = self.classifier.extract_candidate_links_from_html("https://example.com", html)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["location"], "HEADER_NAV")
        self.assertEqual(cands[0]["url"], "https://example.com/careers")

    def test_02_footer_nav_location_tagging(self):
        """Tags candidate links inside <footer> as FOOTER_NAV."""
        html = """
        <html>
            <body>
                <footer>
                    <a href="/csr-policy">Corporate Social Responsibility</a>
                </footer>
            </body>
        </html>
        """
        cands = self.classifier.extract_candidate_links_from_html("https://example.com", html)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["location"], "FOOTER_NAV")
        self.assertEqual(cands[0]["url"], "https://example.com/csr-policy")

    def test_03_dropdown_menu_location_detection(self):
        """Detects links inside menu dropdown containers."""
        html = """
        <html>
            <body>
                <div class="main-menu dropdown">
                    <a href="/sustainability">ESG & Sustainability</a>
                </div>
            </body>
        </html>
        """
        cands = self.classifier.extract_candidate_links_from_html("https://example.com", html)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["location"], "HEADER_NAV")

    def test_04_relative_url_resolution(self):
        """Resolves relative links against base URL and strips fragments."""
        html = '<html><body><main><a href="../about/jobs#apply">Join Us</a></main></body></html>'
        cands = self.classifier.extract_candidate_links_from_html("https://example.com/portal/home", html)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["url"], "https://example.com/about/jobs")

    def test_05_aria_label_and_title_text_extraction(self):
        """Extracts link text from aria-label or title attributes when inner text is empty."""
        html = """
        <html>
            <body>
                <a href="/careers" aria-label="Job Openings"></a>
                <a href="/csr" title="CSR Initiatives"></a>
            </body>
        </html>
        """
        cands = self.classifier.extract_candidate_links_from_html("https://example.com", html)
        self.assertEqual(len(cands), 2)
        self.assertEqual(cands[0]["text"], "Job Openings")
        self.assertEqual(cands[1]["text"], "CSR Initiatives")

    def test_06_filter_non_http_anchors(self):
        """Filters out javascript, mailto, tel, and pure fragment anchors."""
        html = """
        <html>
            <body>
                <a href="javascript:void(0)">Click Here</a>
                <a href="mailto:info@domain.com">Email Us</a>
                <a href="tel:+911234567890">Call Us</a>
                <a href="#top">Back to top</a>
                <a href="/valid-page">Valid Page</a>
            </body>
        </html>
        """
        cands = self.classifier.extract_candidate_links_from_html("https://example.com", html)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["url"], "https://example.com/valid-page")


# ==============================================================================
# FEATURE 6: Associated External Domain Discovery
# ==============================================================================
class TestTier1Feature06AssociatedExternalDomains(unittest.TestCase):
    """Tier 1: Subdomains, ATS platforms, foundations, and alias matching."""

    def test_01_subdomain_recognition(self):
        """Recognizes corporate subdomains as allowed domains."""
        self.assertTrue(is_allowed_domain_or_ats("https://careers.infosys.com", "https://infosys.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://csr.tatamotors.com", "https://tatamotors.com"))

    def test_02_major_ats_platforms_allowed(self):
        """Validates major enterprise ATS domains (Workday, Lever, Greenhouse, etc.)."""
        ats_urls = [
            "https://tatamotors.myworkdayjobs.com/Careers",
            "https://jobs.lever.co/paytm/123",
            "https://boards.greenhouse.io/swiggy/jobs/456",
            "https://jobs.smartrecruiters.com/AcmeCorp/789",
            "https://eibd.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/1",
        ]
        for url in ats_urls:
            self.assertTrue(
                is_allowed_domain_or_ats(url, "example.com"),
                f"Expected ATS domain to be allowed: {url}",
            )

    def test_03_approved_corporate_foundation_domains(self):
        """Validates approved Indian corporate foundation domains."""
        self.assertTrue(is_allowed_domain_or_ats("https://www.reliancefoundation.org", "https://ril.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://www.tatatrusts.org", "https://tcs.com"))

    def test_04_enterprise_domain_aliases(self):
        """Validates enterprise domain alias pairs from registry."""
        self.assertTrue(is_allowed_domain_or_ats("https://tata.com/investors", "https://tatamotors.com"))

    def test_05_lookalike_and_unrelated_domains_rejected(self):
        """Strictly rejects lookalike or unrelated domains."""
        self.assertFalse(is_allowed_domain_or_ats("https://tcs-fake-jobs.com", "https://tcs.com"))
        self.assertFalse(is_allowed_domain_or_ats("https://infosys-recruitment.org", "https://infosys.com"))
        self.assertFalse(is_allowed_domain_or_ats("https://malicious-site.com", "https://example.com"))

    def test_06_match_ats_pattern_from_config(self):
        """Matches ATS platforms against regex patterns in config/ats_domains.json."""
        patterns = load_ats_patterns()
        workday_match = match_ats_pattern("https://company.myworkdayjobs.com/careers", patterns)
        self.assertIsNotNone(workday_match)
        self.assertEqual(workday_match.get("platform"), "Workday")

        lever_match = match_ats_pattern("https://jobs.lever.co/company/abc", patterns)
        self.assertIsNotNone(lever_match)
        self.assertEqual(lever_match.get("platform"), "Lever")


# ==============================================================================
# FEATURE 7: URL Normalization & Deduplication
# ==============================================================================
class TestTier1Feature07UrlNormalizationDeduplication(unittest.TestCase):
    """Tier 1: Canonical URL standardization, fingerprinting, and junk filtering."""

    def test_01_strip_tracking_parameters(self):
        """Strips UTM, social tracking, and analytics query parameters."""
        url = "https://example.com/careers?utm_source=twitter&utm_medium=social&fbclid=123&gclid=456&ref=nav"
        normalized = normalize_canonical_url(url)
        self.assertEqual(normalized, "https://example.com/careers")

    def test_02_strip_fragments_and_text_fragments(self):
        """Strips URL fragment anchors (#section) and text fragments (#:~:text=)."""
        url = "https://example.com/sustainability#target:~:text=Net%20Zero"
        normalized = normalize_canonical_url(url)
        self.assertEqual(normalized, "https://example.com/sustainability")

    def test_03_trailing_slash_and_scheme_case(self):
        """Normalizes uppercase scheme and trailing slash consistently."""
        u1 = "HTTPS://WWW.EXAMPLE.COM/careers/"
        u2 = "https://www.example.com/careers"
        self.assertEqual(normalize_canonical_url(u1), normalize_canonical_url(u2))

    def test_04_deterministic_job_fingerprint(self):
        """Computes deterministic 64-char SHA-256 fingerprint from entity metadata."""
        fp1 = build_job_fingerprint("COMP_01", external_job_id="REQ-1234")
        fp2 = build_job_fingerprint("COMP_01", external_job_id="REQ-1234")
        fp3 = build_job_fingerprint("COMP_01", external_job_id="REQ-9999")

        self.assertEqual(len(fp1), 64)
        self.assertEqual(fp1, fp2)
        self.assertNotEqual(fp1, fp3)

    def test_05_is_junk_url_filters_assets_and_social(self):
        """Filters image assets, stylesheets, scripts, and social platforms."""
        junk_urls = [
            "https://example.com/logo.png",
            "https://example.com/style.css",
            "https://example.com/bundle.js",
            "https://facebook.com/share?url=abc",
            "https://twitter.com/company",
        ]
        for u in junk_urls:
            is_junk, reason = is_junk_url(u)
            self.assertTrue(is_junk, f"Expected junk for {u}: {reason}")

    def test_06_is_junk_url_preserves_pdf_and_career_links(self):
        """Preserves legitimate PDF reports and career pages without junk false-positives."""
        legit_urls = [
            "https://example.com/csr/annual-report-2025.pdf",
            "https://example.com/careers/software-engineer",
            "https://example.com/sustainability/esg-disclosure",
        ]
        for u in legit_urls:
            is_junk, _ = is_junk_url(u)
            self.assertFalse(is_junk, f"Expected legitimate URL to not be junk: {u}")


# ==============================================================================
# FEATURE 8: Multi-Tier URL Classification
# ==============================================================================
class TestTier1Feature08MultiTierUrlClassification(unittest.TestCase):
    """Tier 1: Multi-category URL classification and independent evidence validation gate."""

    def setUp(self):
        self.classifier = TwoStagePageClassifier(client=MagicMock())

    def test_01_jobs_listing_page_approved(self):
        """Approves verified JOBS_LISTING_PAGE with high confidence mapping to jobs_page_url."""
        page_classification = {
            "page_type": "JOBS_LISTING_PAGE",
            "confidence": 0.95,
            "actual_model": "gemini-2.5-flash",
        }
        page_data = {
            "url": "https://example.com/careers/jobs",
            "is_accessible": True,
            "main_text": "We are currently hiring software developers. Apply now.",
        }
        result = self.classifier.validate_page_evidence("Acme Corp", "example.com", page_classification, page_data)
        self.assertEqual(result["decision"], "APPROVED")
        self.assertEqual(result["target_field"], "jobs_page_url")

    def test_02_careers_landing_page_approved(self):
        """Approves verified CAREERS_LANDING_PAGE mapping to careers_url."""
        page_classification = {
            "page_type": "CAREERS_LANDING_PAGE",
            "confidence": 0.92,
            "actual_model": "gemini-2.5-flash",
        }
        page_data = {
            "url": "https://example.com/careers",
            "is_accessible": True,
            "main_text": "Explore life at Acme and join our world-class team.",
        }
        result = self.classifier.validate_page_evidence("Acme Corp", "example.com", page_classification, page_data)
        self.assertEqual(result["decision"], "APPROVED")
        self.assertEqual(result["target_field"], "careers_url")

    def test_03_csr_disclosure_page_approved(self):
        """Approves verified CSR_PROJECT_DISCLOSURE mapping to csr_portal_url."""
        page_classification = {
            "page_type": "CSR_PROJECT_DISCLOSURE",
            "confidence": 0.94,
            "actual_model": "gemini-2.5-flash",
        }
        page_data = {
            "url": "https://example.com/csr/initiatives",
            "is_accessible": True,
            "main_text": "Section 135 CSR policy and projects in education and healthcare.",
        }
        result = self.classifier.validate_page_evidence("Acme Corp", "example.com", page_classification, page_data)
        self.assertEqual(result["decision"], "APPROVED")
        self.assertEqual(result["target_field"], "csr_portal_url")

    def test_04_sustainability_esg_page_approved(self):
        """Approves verified SUSTAINABILITY_OR_ESG_REPORT mapping to sustainability_url."""
        page_classification = {
            "page_type": "SUSTAINABILITY_OR_ESG_REPORT",
            "confidence": 0.90,
            "actual_model": "gemini-2.5-flash",
        }
        page_data = {
            "url": "https://example.com/sustainability",
            "is_accessible": True,
            "main_text": "Annual ESG disclosure and carbon emission reduction metrics.",
        }
        result = self.classifier.validate_page_evidence("Acme Corp", "example.com", page_classification, page_data)
        self.assertEqual(result["decision"], "APPROVED")
        self.assertEqual(result["target_field"], "sustainability_url")

    def test_05_rule0_deterministic_fallback_never_approved(self):
        """Rule 0: Fallback classifications without genuine AI can NEVER be approved."""
        page_classification = {
            "page_type": "JOBS_LISTING_PAGE",
            "confidence": 0.95,
            "actual_model": "rule_based_fallback",
        }
        page_data = {"url": "https://example.com/careers", "is_accessible": True}
        result = self.classifier.validate_page_evidence("Acme Corp", "example.com", page_classification, page_data)
        self.assertNotEqual(result["decision"], "APPROVED")
        self.assertIn(result["decision"], ["REVIEW_REQUIRED", "PENDING_AI"])

    def test_06_rule1_inaccessible_page_rejected(self):
        """Rule 1: Inaccessible or 404 pages are rejected."""
        page_classification = {
            "page_type": "JOBS_LISTING_PAGE",
            "confidence": 0.95,
            "actual_model": "gemini-2.5-flash",
        }
        page_data = {"url": "https://example.com/careers", "is_accessible": False}
        result = self.classifier.validate_page_evidence("Acme Corp", "example.com", page_classification, page_data)
        self.assertEqual(result["decision"], "REJECTED")

    def test_07_rule2_consumer_banking_loan_rejected(self):
        """Rule 2: Commercial consumer banking or loan application pages are rejected."""
        page_classification = {
            "page_type": "UNRELATED_PAGE",
            "confidence": 0.85,
            "actual_model": "gemini-2.5-flash",
        }
        page_data = {
            "url": "https://example.com/loans",
            "is_accessible": True,
            "main_text": "Apply for personal loan with low interest rates.",
        }
        result = self.classifier.validate_page_evidence("Bank Corp", "bank.com", page_classification, page_data)
        self.assertEqual(result["decision"], "REJECTED")


# ==============================================================================
# FEATURE 9: Live URL Verification Engine
# ==============================================================================
class TestTier1Feature09LiveUrlVerification(unittest.TestCase):
    """Tier 1: Live HTTP verification, redirect following, and status assessment."""

    @patch("modules.crawler_engine.link_verifier.cffi_requests.get")
    def test_01_verify_url_live_200_ok(self, mock_get):
        """Probing a live URL with HTTP 200 returns valid and LINK_OK state."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://example.com/careers"
        mock_get.return_value = mock_resp

        result = verify_url_live("https://example.com/careers")
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["status_code"], 200)
        self.assertEqual(result["verification_state"], "LINK_OK")

    @patch("modules.crawler_engine.link_verifier.cffi_requests.get")
    def test_02_verify_url_live_follow_redirect(self, mock_get):
        """Follows redirect chains and records the final destination URL."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://example.com/jobs/current-openings"
        mock_get.return_value = mock_resp

        result = verify_url_live("https://example.com/careers")
        self.assertTrue(result["is_valid"])
        self.assertEqual(result["final_url"], "https://example.com/jobs/current-openings")

    @patch("modules.crawler_engine.link_verifier.cffi_requests.get")
    def test_03_verify_url_live_404_broken(self, mock_get):
        """Probing an unreachable 404 URL returns is_valid=False and HTTP_404 state."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.url = "https://example.com/old-page"
        mock_get.return_value = mock_resp

        result = verify_url_live("https://example.com/old-page")
        self.assertFalse(result["is_valid"])
        self.assertEqual(result["status_code"], 404)
        self.assertEqual(result["verification_state"], "HTTP_404")

    @patch("modules.crawler_engine.link_verifier.cffi_requests.get")
    def test_04_verify_url_live_timeout_handled(self, mock_get):
        """Handles connection timeouts gracefully returning BROKEN state without crashing."""
        mock_get.side_effect = TimeoutError("Connection timed out")

        result = verify_url_live("https://example.com/hang")
        self.assertFalse(result["is_valid"])
        self.assertEqual(result["status_code"], 0)
        self.assertEqual(result["verification_state"], "BROKEN")

    def test_05_build_highlight_url_clean_requisition(self):
        """Strips fragment hashes and tracking tokens from official ATS links."""
        url = "https://jobs.lever.co/company/abc-123#apply?utm_source=linkedin"
        clean = build_highlight_url(url)
        self.assertEqual(clean, "https://jobs.lever.co/company/abc-123")

    def test_06_title_matches_semantic_overlap(self):
        """Heuristic title matching confirms requisition overlap."""
        self.assertTrue(title_matches("Senior Software Engineer", "Senior Software Engineer - Python"))
        self.assertTrue(title_matches("Lead Chemist", "Lead Chemist - R&D"))
        self.assertFalse(title_matches("Account Executive", "Civil Engineer"))


# ==============================================================================
# FEATURE 10: Boilerplate-Free HTML Content Extractor
# ==============================================================================
class TestTier1Feature10HtmlContentExtractor(unittest.TestCase):
    """Tier 1: HTML content extraction, CorporateHTMLParser, GenericHTMLParser, and UniversalJobDetailExtractor."""

    def test_01_universal_job_detail_extractor_responsibilities_and_qualifications(self):
        """Extracts structured job title, responsibilities, and qualifications from prose text."""
        raw_text = (
            "Job Title: Lead Data Scientist\n\n"
            "Responsibilities:\n"
            "Design, train, and deploy enterprise machine learning models.\n"
            "Collaborate with backend engineering teams.\n\n"
            "Qualifications:\n"
            "B.Tech in Computer Science or equivalent engineering degree.\n"
            "6+ years of production experience in Python and PyTorch.\n"
        )
        extracted = UniversalJobDetailExtractor.extract_from_text(raw_text, job_title="Lead Data Scientist")
        self.assertEqual(extracted.get("job_title"), "Lead Data Scientist")
        self.assertIn("machine learning models", extracted.get("responsibilities", ""))
        self.assertIn("B.Tech", extracted.get("education", ""))
        self.assertIn("6+ years", extracted.get("experience", ""))

    def test_02_corporate_html_parser_company_details(self):
        """Extracts clean company name and evidence text using CorporateHTMLParser."""
        html = "<html><head><title>3M India Limited - Official Corporate Portal</title></head><body></body></html>"
        parser = CorporateHTMLParser(
            company=MagicMock(),
            url="https://www.3mindia.in",
            final_url="https://www.3mindia.in",
            html_content=html,
        )
        details = parser.extract_company_details()
        self.assertIsNotNone(details)
        self.assertEqual(details["company_name"], "3M India Limited")
        self.assertIn("3M India Limited", details["evidence_text"])

    def test_03_corporate_html_parser_csr_initiatives_and_budgets(self):
        """Extracts CSR initiatives, theme categorization, and rupee budget values."""
        html = """
        <html>
        <head><title>Corporate Social Responsibility</title></head>
        <body>
            <div class="initiative-card">
                <h2>Rural Healthcare Mobile Clinics</h2>
                <p>Deploying specialized medical treatment vans across rural districts.
                Total program commitment of INR 15.5 Crore over three years.</p>
            </div>
            <div class="project-block">
                <h3>Primary School Digital Literacy</h3>
                <p>Establishing digital classrooms in state schools to advance student learning.
                Allocated budget of Rs 8.20 Crore for infrastructure and teacher training.</p>
            </div>
        </body>
        </html>
        """
        parser = CorporateHTMLParser(
            company=MagicMock(),
            url="https://example.com/csr",
            final_url="https://example.com/csr",
            html_content=html,
        )
        csr_projects = parser.extract_csr()
        self.assertEqual(len(csr_projects), 2)
        project_names = [p["project_name"] for p in csr_projects]
        self.assertIn("Rural Healthcare Mobile Clinics", project_names)
        self.assertIn("Primary School Digital Literacy", project_names)
        # Verify budget extraction
        budgets = [p.get("budget") for p in csr_projects]
        self.assertTrue(any("15.5" in str(b) for b in budgets if b))

    def test_04_corporate_html_parser_contacts_department_classification(self):
        """Extracts mailto contacts and classifies CSR vs General departments."""
        html = """
        <html>
        <body>
            <div><p>For community partnerships: <a href="mailto:csr@example.com">Contact CSR Team</a></p></div>
            <div><p>General queries: <a href="mailto:info@example.com">Corporate Office</a></p></div>
        </body>
        </html>
        """
        parser = CorporateHTMLParser(
            company=MagicMock(),
            url="https://example.com/contact",
            final_url="https://example.com/contact",
            html_content=html,
        )
        contacts = parser.extract_contacts()
        self.assertEqual(len(contacts), 2)
        email_map = {c["email"]: c["department"] for c in contacts}
        self.assertEqual(email_map.get("csr@example.com"), "CSR & Sustainability")
        self.assertEqual(email_map.get("info@example.com"), "General")

    def test_05_generic_html_parser_json_ld_job_extraction(self):
        """GenericHTMLParser extracts structured JobPosting schema from application/ld+json."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "Principal Cloud Architect",
                "description": "Architect high-availability cloud infrastructure and AWS solutions.",
                "jobLocation": {"address": {"addressLocality": "Bengaluru", "addressCountry": "IN"}},
                "identifier": {"name": "Acme", "value": "REQ-2026-99"}
            }
            </script>
        </head>
        <body><h1>Careers at Acme</h1></body>
        </html>
        """
        parser = GenericHTMLParser(
            company=MagicMock(),
            url="https://example.com/careers",
            final_url="https://example.com/careers",
            html_content=html,
        )
        jobs = parser.extract_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Principal Cloud Architect")
        self.assertIn("cloud infrastructure", jobs[0]["job_description"])
        self.assertEqual(jobs[0]["location"], "Bengaluru, IN")

    def test_06_generic_html_parser_rejects_non_job_titles(self):
        """GenericHTMLParser filters out non-job titles like Privacy Policy or Search Jobs."""
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            [
                {"@type": "JobPosting", "title": "Privacy Policy", "description": "Legal disclaimers"},
                {"@type": "JobPosting", "title": "Senior Backend Engineer", "description": "Build high-throughput APIs"}
            ]
            </script>
        </head>
        <body></body>
        </html>
        """
        parser = GenericHTMLParser(
            company=MagicMock(),
            url="https://example.com/careers",
            final_url="https://example.com/careers",
            html_content=html,
        )
        jobs = parser.extract_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Senior Backend Engineer")


# ==============================================================================
# FEATURE 11: Corporate PDF Extraction Engine
# ==============================================================================
class TestTier1Feature11PdfExtractionEngine(unittest.TestCase):
    """Tier 1: PDF extraction, statutory markers, budget detection, and error states."""

    def test_01_pdf_report_extractor_page_numbered_text(self):
        """Extracts page-by-page text chunks using PDFReportExtractor."""
        extractor = PDFReportExtractor(max_pages=5)
        p1 = MagicMock()
        p1.extract_text.return_value = (
            "Section 135 Annual Report on Corporate Social Responsibility activities: "
            "Total CSR expenditure for the financial year amounted to INR 12.5 Crore."
        )
        mock_reader = MagicMock()
        mock_reader.pages = [p1]

        with patch("pypdf.PdfReader", return_value=mock_reader):
            pages = extractor.extract_from_bytes(b"%PDF-1.4 simulated bytes", filename="csr.pdf")
            self.assertEqual(len(pages), 1)
            self.assertEqual(pages[0]["page_number"], 1)
            self.assertTrue(pages[0]["has_statutory_indicators"])
            self.assertTrue(pages[0]["has_expenditure_indicators"])

    def test_02_statutory_and_expenditure_indicators(self):
        """Detects Schedule VII, Section 135, and expenditure keywords."""
        extractor = PDFReportExtractor()
        p_stat = MagicMock()
        p_stat.extract_text.return_value = "The CSR Committee reviewed projects under Schedule VII of the Companies Act."
        mock_reader = MagicMock()
        mock_reader.pages = [p_stat]

        with patch("pypdf.PdfReader", return_value=mock_reader):
            pages = extractor.extract_from_bytes(b"%PDF-1.4", filename="report.pdf")
            self.assertTrue(pages[0]["has_statutory_indicators"])

    def test_03_pdf_max_pages_bounding(self):
        """Enforces max_pages limit when extracting multi-page documents."""
        extractor = PDFReportExtractor(max_pages=2)
        pages_mock = []
        for i in range(10):
            p = MagicMock()
            p.extract_text.return_value = f"This is page {i+1} containing sufficient text to exceed length limit."
            pages_mock.append(p)

        mock_reader = MagicMock()
        mock_reader.pages = pages_mock

        with patch("pypdf.PdfReader", return_value=mock_reader):
            extracted = extractor.extract_from_bytes(b"%PDF-1.4", filename="large.pdf")
            self.assertEqual(len(extracted), 2)

    def test_04_csr_pdf_parser_magic_bytes_check(self):
        """CSRPdfParser rejects files lacking %PDF magic bytes."""
        parser = CSRPdfParser("https://example.com/not-a-pdf.pdf", company=MagicMock())
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.content = b"<html><body>Not a PDF file</body></html>"

        with patch("requests.get", return_value=mock_resp), patch("requests.head", return_value=mock_resp):
            projects = parser.fetch_and_extract()
            self.assertEqual(projects, [])
            self.assertEqual(parser.error_code, "NOT_A_VALID_PDF")

    def test_05_csr_pdf_parser_size_limit_check(self):
        """Rejects PDF downloads exceeding file size limit."""
        parser = CSRPdfParser("https://example.com/oversized.pdf", company=MagicMock())
        mock_head = MagicMock()
        mock_head.headers = {"content-length": str(10 * 1024 * 1024)}  # 10MB > 3MB limit

        with patch("requests.head", return_value=mock_head):
            projects = parser.fetch_and_extract()
            self.assertEqual(projects, [])
            self.assertEqual(parser.error_code, "PDF_TOO_LARGE")

    def test_06_csr_pdf_parser_timeout_handling(self):
        """Handles download timeouts gracefully with FETCH_TIMEOUT status."""
        import requests

        parser = CSRPdfParser("https://example.com/timeout.pdf", company=MagicMock())
        with patch("requests.head", side_effect=requests.exceptions.Timeout), patch(
            "requests.get", side_effect=requests.exceptions.Timeout
        ):
            projects = parser.fetch_and_extract()
            self.assertEqual(projects, [])
            self.assertEqual(parser.error_code, "FETCH_TIMEOUT")


# ==============================================================================
# FEATURE 12: Transaction-Safe MySQL Persistence
# ==============================================================================
class ConcreteVerifiableModel(VerifiableModel):
    """Concrete subclass of VerifiableModel for validation unit tests."""

    class Meta:
        app_label = "admin_panel"


class TestTier1Feature12TransactionSafePersistence(unittest.TestCase):
    """Tier 1: VerifiableModel save constraints, deduplication, and dropped candidates."""

    def test_01_verifiable_model_save_requires_source_url(self):
        """Raises ValueError if published without a source_url."""
        model = ConcreteVerifiableModel()
        model.verification_status = "PUBLISHED"
        model.retrieved_at = datetime.now(timezone.utc)
        model.evidence_text = "Verified evidence text."
        model.source_url = None

        with self.assertRaises(ValueError) as ctx:
            model.save()
        self.assertIn("source_url", str(ctx.exception))

    def test_02_verifiable_model_save_requires_retrieved_at(self):
        """Raises ValueError if published without a retrieved_at timestamp."""
        model = ConcreteVerifiableModel()
        model.verification_status = "PUBLISHED"
        model.source_url = "https://example.com/evidence"
        model.evidence_text = "Verified evidence text."
        model.retrieved_at = None

        with self.assertRaises(ValueError) as ctx:
            model.save()
        self.assertIn("retrieved_at", str(ctx.exception))

    def test_03_verifiable_model_save_requires_evidence(self):
        """Raises ValueError if published without evidence_text, snapshot, or content_hash."""
        model = ConcreteVerifiableModel()
        model.verification_status = "PUBLISHED"
        model.source_url = "https://example.com/evidence"
        model.retrieved_at = datetime.now(timezone.utc)
        model.evidence_text = None
        model.source_snapshot = None
        model.content_hash = None

        with self.assertRaises(ValueError) as ctx:
            model.save()
        self.assertIn("actual evidence", str(ctx.exception))

    def test_04_verifiable_model_save_succeeds_with_evidence(self):
        """Saves successfully when all mandatory verification fields are present."""
        model = ConcreteVerifiableModel()
        model.verification_status = "PUBLISHED"
        model.source_url = "https://example.com/evidence"
        model.retrieved_at = datetime.now(timezone.utc)
        model.evidence_text = "Documented statutory disclosure text."

        with patch("django.db.models.Model.save") as mock_save:
            model.save()
            self.assertTrue(mock_save.called)

    def test_05_csr_report_content_hash_deduplication(self):
        """Verifies report upsert logic updates existing record when content_hash matches."""
        reports_data = [{
            "title": "Annual CSR Report 2025",
            "report_type": "CSR",
            "financial_year": "2024-25",
            "url": "https://example.com/report.pdf",
            "text": "CSR report narrative text covering educational spending.",
            "summary": "Summary text",
            "topics": ["Education"],
            "initiatives": [],
            "expenditure": "INR 10 Crore",
        }]

        mock_company = MagicMock()
        mock_company.company_id = "COMP_TEST_01"
        now = datetime.now(timezone.utc)
        logs = []

        expected_hash = hashlib.sha256(f"{mock_company.company_id}|https://example.com/report.pdf".encode('utf-8')).hexdigest()

        with patch("modules.admin_panel.models.CSRReport.objects.update_or_create") as mock_uoc:
            mock_uoc.return_value = (MagicMock(), True)
            BatchDiscoveryService._persist_reports(mock_company, reports_data, now, logs)
            self.assertTrue(mock_uoc.called)
            kwargs = mock_uoc.call_args[1]
            self.assertEqual(kwargs["company"], mock_company)
            self.assertEqual(kwargs["content_hash"], expected_hash)

    def test_06_record_dropped_candidate_audit(self):
        """Records dropped candidate to diagnostic audit table."""
        mock_company = MagicMock()
        mock_company.company_name = "Test Corp"

        with patch("modules.admin_panel.models.DroppedCandidate.objects.create") as mock_create:
            BatchDiscoveryService._record_dropped_candidate(
                company=mock_company,
                candidate_type="JOB",
                name="Software Engineer",
                target_url="https://example.com/expired-job",
                reason="Position closed or expired",
                raw_data={"job_id": 123},
            )
            self.assertTrue(mock_create.called)
            kwargs = mock_create.call_args[1]
            self.assertEqual(kwargs["candidate_type"], "JOB")
            self.assertEqual(kwargs["reason"], "Position closed or expired")


# ==============================================================================
# FEATURE 13: Concurrency, Retries & Structured Logging
# ==============================================================================
class TestTier1Feature13ConcurrencyRetriesLogging(unittest.TestCase):
    """Tier 1: Concurrency dispatch, database connection cleanup, API retries, and telemetry."""

    def test_01_deep_enrich_database_connection_cleanup(self):
        """Verifies close_old_connections is called in worker thread lifecycle."""
        with patch("django.db.close_old_connections") as mock_close, \
             patch("django.db.connection.vendor", "mysql"), \
             patch("modules.admin_panel.models.Company.objects.filter") as mock_comp_filter:
            mock_comp_filter.return_value.first.return_value = None
            # Deep enrich invokes close_old_connections on entry and in finally
            BatchDiscoveryService._deep_enrich(
                company_id="COMP_TEST_01",
                options={"concurrent_tracks": False},
                sitemap_targets={},
                processed_careers=[],
                processed_csr=[],
                processed_reports=[],
            )
            self.assertTrue(mock_close.called)

    def test_02_start_background_crawl_dispatch_and_state(self):
        """Verifies start_background_crawl dispatches background thread and logs start event."""
        mock_company = MagicMock()
        mock_company.company_id = "COMP_TEST_01"
        mock_company.company_name = "Acme Corp"

        mock_qs = MagicMock()
        mock_qs.order_by.return_value.filter.return_value = [mock_company]

        CRAWL_TASK_STATE["is_running"] = False
        try:
            with patch("django.conf.settings.ALLOW_GLOBAL_SYNC", True), \
                 patch("modules.crawler_engine.crawler.Company.objects.all", return_value=mock_qs), \
                 patch("threading.Thread") as mock_thread, \
                 patch("modules.crawler_engine.state.log_event") as mock_log:

                result = start_background_crawl(company_ids=["COMP_TEST_01"], batch_label="Test Batch")

                self.assertTrue(result)
                self.assertTrue(mock_thread.called)
                self.assertTrue(mock_log.called)
        finally:
            CRAWL_TASK_STATE["is_running"] = False

    def test_03_ai_client_exponential_backoff_retry_on_5xx(self):
        """Verifies OpenAICompatibleApiClient retries with backoff on transient HTTP 5xx errors."""
        client = OpenAICompatibleApiClient(
            api_key="test-api-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        mock_503 = MagicMock(status_code=503, text="Service Temporarily Unavailable")
        mock_200 = MagicMock(status_code=200)
        mock_200.json.return_value = {"choices": [{"message": {"content": json.dumps({"status": "verified"})}}]}

        with patch("requests.post", side_effect=[mock_503, mock_200]), \
             patch("modules.crawler_engine.ai_api_client.time.sleep") as mock_sleep:
            data, model = client._execute_provider_request("Test extraction prompt")
            self.assertEqual(data, {"status": "verified"})
            self.assertEqual(client.metrics["retries_count"], 1)
            self.assertTrue(mock_sleep.called)

    def test_04_ai_client_max_retries_exhaustion_raises_error(self):
        """Verifies AIClientError is raised after max retries are exhausted on persistent 5xx."""
        client = OpenAICompatibleApiClient(
            api_key="test-api-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
        )
        mock_500 = MagicMock(status_code=500, text="Internal Server Error")

        with patch("requests.post", return_value=mock_500), \
             patch("modules.crawler_engine.ai_api_client.time.sleep"):
            with self.assertRaises(AIClientError) as ctx:
                client._execute_provider_request("Test extraction prompt")
            self.assertIn("max retries", str(ctx.exception).lower())
            self.assertGreaterEqual(client.metrics["retries_count"], 1)

    def test_05_primary_fallback_ai_client_failover(self):
        """Verifies PrimaryFallbackAIClient catches primary errors and invokes fallback client."""
        mock_primary = MagicMock()
        mock_primary.execute_structured_prompt.side_effect = AIClientError("Quota exceeded on primary")

        mock_fallback = MockAIClient(mock_model_name="mock-fallback-v1")

        client = PrimaryFallbackAIClient(primary=mock_primary, fallback=mock_fallback)
        result, model = client.execute_structured_prompt("Classify portal links")

        self.assertIsNotNone(result)
        self.assertEqual(client.metrics["fallback_invocations"], 1)

    def test_06_structured_log_event_fields_and_stats(self):
        """Verifies structured event telemetry formatting in CRAWL_TASK_STATE."""
        log_event(
            category="DISCOVERY",
            status_badge="SUCCESS",
            msg="Verified career portal link.",
            company_id="COMP_TOP200_154",
            company_name="20 Microns Limited",
        )
        self.assertTrue(len(CRAWL_TASK_STATE["events"]) > 0)
        latest_event = CRAWL_TASK_STATE["events"][0]
        self.assertEqual(latest_event["category"], "DISCOVERY")
        self.assertEqual(latest_event["status_badge"], "SUCCESS")
        self.assertEqual(latest_event["company_id"], "COMP_TOP200_154")
        self.assertEqual(latest_event["company_name"], "20 Microns Limited")
        self.assertIn("timestamp", latest_event)


# ==============================================================================
# FEATURE 14: Standardized Outcome Codes
# ==============================================================================
class TestTier1Feature14StandardizedOutcomeCodes(unittest.TestCase):
    """Tier 1: Standardized outcome code mappings in BatchDiscoveryService pipeline."""

    def test_01_outcome_fetch_failed_on_unreachable_homepage(self):
        """BatchDiscoveryService maps unreachable corporate homepage to FETCH_FAILED."""
        with patch.object(BatchDiscoveryService, "fetch_page_content", return_value=("", "", 0)):
            res = BatchDiscoveryService.process_single_company({
                "company_name": "Acme Unreachable",
                "homepage_url": "https://unreachable.example.com",
            })
            self.assertEqual(res.get("outcome"), "FETCH_FAILED")
            self.assertEqual(res.get("status"), "error")

    def test_02_outcome_validation_failed_on_invalid_domain(self):
        """BatchDiscoveryService maps invalid homepage domain to VALIDATION_FAILED."""
        with patch.object(BatchDiscoveryService, "fetch_page_content", return_value=("<html></html>", "content", 200)), \
             patch("modules.admin_panel.services.batch_discovery_service.get_registrable_domain", return_value=""):
            res = BatchDiscoveryService.process_single_company({
                "company_name": "Invalid Domain Corp",
                "homepage_url": "https://example.com",
            })
            self.assertEqual(res.get("outcome"), "VALIDATION_FAILED")
            self.assertEqual(res.get("status"), "error")

    def test_03_outcome_duplicate_company_rejection(self):
        """BatchDiscoveryService maps duplicate company rejection to DUPLICATE_COMPANY."""
        with patch.object(BatchDiscoveryService, "fetch_page_content", return_value=("<html></html>", "content", 200)), \
             patch.object(BatchDiscoveryService, "check_company_duplicate", return_value=(True, MagicMock(company_id="COMP_EXISTING"), "Duplicate exists")):
            res = BatchDiscoveryService.process_single_company(
                {"company_name": "Existing Corp", "homepage_url": "https://existing.com"},
                options={"prevent_duplicates": True},
            )
            self.assertEqual(res.get("outcome"), "DUPLICATE_COMPANY")
            self.assertEqual(res.get("status"), "duplicate")

    def test_04_outcome_success_with_results(self):
        """Maps accessible homepage with verified discovered entities to SUCCESS_WITH_RESULTS."""
        mock_comp = MagicMock(company_id="COMP_01", sector="IT", headquarters="Mumbai", verification_status="VERIFIED")
        mock_job_row = {
            "job_id": "J1", "job_title": "Dev", "job_row_id": 1, "external_job_id": "1",
            "department": "Eng", "location": "India", "work_mode": "remote", "experience": "2",
            "salary": "10", "employment_type": "full_time", "ats_platform": "direct",
            "application_url": "https://example.com/apply", "source_url": "https://example.com/careers",
            "confidence": 1.0, "evidence_text": "Dev job", "job_description": "Build things",
            "skills": "Python", "posted_date": "2026-01-01",
        }
        mock_comp.jobs.all.return_value.order_by.return_value.values.return_value = [mock_job_row]
        mock_comp.csr_projects.all.return_value.order_by.return_value.values.return_value = []
        mock_comp.csr_reports.all.return_value.order_by.return_value = []

        with patch("modules.admin_panel.models.Company.objects.filter") as mock_c_filter, \
             patch("modules.admin_panel.models.AuditTrail.objects.create"), \
             patch("modules.admin_panel.models.DroppedCandidate.objects.filter") as mock_dc_filter, \
             patch.object(BatchDiscoveryService, "fetch_page_content", return_value=("", "", 404)), \
             patch.object(BatchDiscoveryService, "_publish_progress"), \
             patch.object(BatchDiscoveryService, "find_target_links_from_html", return_value={"careers_url": "https://example.com/careers"}), \
             patch.object(BatchDiscoveryService, "crawl_deep_portal_chain", return_value=("https://example.com/careers", "<html></html>", "careers", 200)), \
             patch.object(BatchDiscoveryService, "extract_company_metadata_from_html", return_value={"sector": "IT", "headquarters": "Mumbai"}), \
             patch.object(BatchDiscoveryService, "discover_all_real_jobs", return_value=[mock_job_row]), \
             patch.object(BatchDiscoveryService, "_persist_job_candidates", return_value=([mock_job_row], [1])), \
             patch.object(BatchDiscoveryService, "_fetch_sitemap_urls", return_value=[]), \
             patch.object(BatchDiscoveryService, "_pick_sitemap_targets", return_value={"careers": [], "csr": [], "reports": []}):

            mock_c_filter.return_value.first.return_value = mock_comp
            mock_dc_filter.return_value.count.return_value = 0

            res = BatchDiscoveryService._run_single_company_discovery(
                comp_name="Example Corp",
                final_website="https://example.com",
                official_domain="example.com",
                home_html="<html><body><a href='/careers'>Careers</a></body></html>",
                home_text="Example Corp Careers",
                home_status=200,
                options={"extract_jobs": True, "extract_csr": False, "extract_reports": False, "deep_enrich": False, "concurrent_tracks": False},
                logs=[],
                now=datetime.now(timezone.utc),
            )
            self.assertEqual(res.get("outcome"), "SUCCESS_WITH_RESULTS")

    def test_05_outcome_success_no_results(self):
        """Maps accessible verified portal with confirmed zero listings to SUCCESS_NO_RESULTS."""
        mock_comp = MagicMock(company_id="COMP_01", sector="IT", headquarters="Mumbai", verification_status="VERIFIED")
        mock_comp.jobs.all.return_value.order_by.return_value.values.return_value = []
        mock_comp.csr_projects.all.return_value.order_by.return_value.values.return_value = []
        mock_comp.csr_reports.all.return_value.order_by.return_value = []

        with patch("modules.admin_panel.models.Company.objects.filter") as mock_c_filter, \
             patch("modules.admin_panel.models.AuditTrail.objects.create"), \
             patch("modules.admin_panel.models.DroppedCandidate.objects.filter") as mock_dc_filter, \
             patch.object(BatchDiscoveryService, "fetch_page_content", return_value=("", "", 404)), \
             patch.object(BatchDiscoveryService, "_publish_progress"), \
             patch.object(BatchDiscoveryService, "find_target_links_from_html", return_value={"careers_url": "https://example.com/careers"}), \
             patch.object(BatchDiscoveryService, "crawl_deep_portal_chain", return_value=("https://example.com/careers", "<html></html>", "careers", 200)), \
             patch.object(BatchDiscoveryService, "extract_company_metadata_from_html", return_value={"sector": "IT", "headquarters": "Mumbai"}), \
             patch.object(BatchDiscoveryService, "discover_all_real_jobs", return_value=[]), \
             patch.object(BatchDiscoveryService, "_persist_job_candidates", return_value=([], [])), \
             patch.object(BatchDiscoveryService, "_fetch_sitemap_urls", return_value=[]), \
             patch.object(BatchDiscoveryService, "_pick_sitemap_targets", return_value={"careers": [], "csr": [], "reports": []}):

            mock_c_filter.return_value.first.return_value = mock_comp
            mock_dc_filter.return_value.count.return_value = 0

            res = BatchDiscoveryService._run_single_company_discovery(
                comp_name="Example Corp",
                final_website="https://example.com",
                official_domain="example.com",
                home_html="<html><body><a href='/careers'>Careers</a></body></html>",
                home_text="Example Corp Careers",
                home_status=200,
                options={"extract_jobs": True, "extract_csr": False, "extract_reports": False, "deep_enrich": False, "concurrent_tracks": False},
                logs=[],
                now=datetime.now(timezone.utc),
            )
            self.assertEqual(res.get("outcome"), "SUCCESS_NO_RESULTS")

    def test_06_outcome_partial_success(self):
        """Maps track failure or incomplete discovery to PARTIAL_SUCCESS."""
        mock_comp = MagicMock(company_id="COMP_01", sector="IT", headquarters="Mumbai", verification_status="VERIFIED")
        mock_job_row = {
            "job_id": "J1", "job_title": "Dev", "job_row_id": 1, "external_job_id": "1",
            "department": "Eng", "location": "India", "work_mode": "remote", "experience": "2",
            "salary": "10", "employment_type": "full_time", "ats_platform": "direct",
            "application_url": "https://example.com/apply", "source_url": "https://example.com/careers",
            "confidence": 1.0, "evidence_text": "Dev job", "job_description": "Build things",
            "skills": "Python", "posted_date": "2026-01-01",
        }
        mock_comp.jobs.all.return_value.order_by.return_value.values.return_value = [mock_job_row]
        mock_comp.csr_projects.all.return_value.order_by.return_value.values.return_value = []
        mock_comp.csr_reports.all.return_value.order_by.return_value = []

        with patch("modules.admin_panel.models.Company.objects.filter") as mock_c_filter, \
             patch("modules.admin_panel.models.AuditTrail.objects.create"), \
             patch("modules.admin_panel.models.DroppedCandidate.objects.filter") as mock_dc_filter, \
             patch.object(BatchDiscoveryService, "fetch_page_content", return_value=("", "", 404)), \
             patch.object(BatchDiscoveryService, "_publish_progress"), \
             patch.object(BatchDiscoveryService, "find_target_links_from_html", return_value={"careers_url": "https://example.com/careers"}), \
             patch.object(BatchDiscoveryService, "crawl_deep_portal_chain", return_value=("https://example.com/careers", "<html></html>", "careers", 200)), \
             patch.object(BatchDiscoveryService, "extract_company_metadata_from_html", return_value={"sector": "IT", "headquarters": "Mumbai"}), \
             patch.object(BatchDiscoveryService, "discover_all_real_jobs", side_effect=Exception("Job track error")), \
             patch.object(BatchDiscoveryService, "_persist_job_candidates", return_value=([mock_job_row], [1])), \
             patch.object(BatchDiscoveryService, "_fetch_sitemap_urls", return_value=[]), \
             patch.object(BatchDiscoveryService, "_pick_sitemap_targets", return_value={"careers": [], "csr": [], "reports": []}):

            mock_c_filter.return_value.first.return_value = mock_comp
            mock_dc_filter.return_value.count.return_value = 0

            res = BatchDiscoveryService._run_single_company_discovery(
                comp_name="Example Corp",
                final_website="https://example.com",
                official_domain="example.com",
                home_html="<html><body><a href='/careers'>Careers</a></body></html>",
                home_text="Example Corp Careers",
                home_status=200,
                options={"extract_jobs": True, "extract_csr": False, "extract_reports": False, "deep_enrich": False, "concurrent_tracks": False},
                logs=[],
                now=datetime.now(timezone.utc),
            )
            self.assertEqual(res.get("outcome"), "PARTIAL_SUCCESS")

    def test_07_outcome_validation_rejected_when_all_candidates_dropped(self):
        """Maps crawl where candidates were rejected by the validation gate to VALIDATION_REJECTED."""
        mock_comp = MagicMock(company_id="COMP_01", sector="IT", headquarters="Mumbai", verification_status="VERIFIED")
        mock_comp.jobs.all.return_value.order_by.return_value.values.return_value = []
        mock_comp.csr_projects.all.return_value.order_by.return_value.values.return_value = []
        mock_comp.csr_reports.all.return_value.order_by.return_value = []

        with patch("modules.admin_panel.models.Company.objects.filter") as mock_c_filter, \
             patch("modules.admin_panel.models.AuditTrail.objects.create"), \
             patch("modules.admin_panel.models.DroppedCandidate.objects.filter") as mock_dc_filter, \
             patch.object(BatchDiscoveryService, "fetch_page_content", return_value=("", "", 404)), \
             patch.object(BatchDiscoveryService, "_publish_progress"), \
             patch.object(BatchDiscoveryService, "find_target_links_from_html", return_value={"careers_url": "https://example.com/careers"}), \
             patch.object(BatchDiscoveryService, "crawl_deep_portal_chain", return_value=("https://example.com/careers", "<html></html>", "careers", 200)), \
             patch.object(BatchDiscoveryService, "extract_company_metadata_from_html", return_value={"sector": "IT", "headquarters": "Mumbai"}), \
             patch.object(BatchDiscoveryService, "discover_all_real_jobs", return_value=[{"title": "Unverified Job Candidate"}]), \
             patch.object(BatchDiscoveryService, "_persist_job_candidates", return_value=([], [])), \
             patch.object(BatchDiscoveryService, "_fetch_sitemap_urls", return_value=[]), \
             patch.object(BatchDiscoveryService, "_pick_sitemap_targets", return_value={"careers": [], "csr": [], "reports": []}):

            mock_c_filter.return_value.first.return_value = mock_comp
            mock_dc_filter.return_value.count.return_value = 1

            res = BatchDiscoveryService._run_single_company_discovery(
                comp_name="Example Corp",
                final_website="https://example.com",
                official_domain="example.com",
                home_html="<html><body>Careers</body></html>",
                home_text="Example Corp",
                home_status=200,
                options={"extract_jobs": True, "extract_csr": False, "extract_reports": False, "deep_enrich": False, "concurrent_tracks": False},
                logs=[],
                now=datetime.now(timezone.utc),
            )
            self.assertEqual(res.get("outcome"), "VALIDATION_REJECTED")

    def test_08_outcome_ai_provider_failed(self):
        """Maps failed AI extraction trace when no deterministic results exist to AI_PROVIDER_FAILED."""
        mock_comp = MagicMock(company_id="COMP_01", sector="IT", headquarters="Mumbai", verification_status="VERIFIED")
        mock_comp.jobs.all.return_value.order_by.return_value.values.return_value = []
        mock_comp.csr_projects.all.return_value.order_by.return_value.values.return_value = []
        mock_comp.csr_reports.all.return_value.order_by.return_value = []

        with patch("modules.admin_panel.models.Company.objects.filter") as mock_c_filter, \
             patch("modules.admin_panel.models.AuditTrail.objects.create"), \
             patch("modules.admin_panel.models.DroppedCandidate.objects.filter") as mock_dc_filter, \
             patch.object(BatchDiscoveryService, "fetch_page_content", return_value=("", "", 404)), \
             patch.object(BatchDiscoveryService, "_publish_progress"), \
             patch.object(BatchDiscoveryService, "find_target_links_from_html", return_value={}), \
             patch.object(BatchDiscoveryService, "extract_company_metadata_from_html", return_value={"sector": "IT", "headquarters": "Mumbai"}), \
             patch("modules.crawler_engine.hybrid_ai_service.HybridAIExtractionService.end_trace", return_value=[{"status": "FAILED", "error": "AI Quota Error"}]), \
             patch.object(BatchDiscoveryService, "_fetch_sitemap_urls", return_value=[]), \
             patch.object(BatchDiscoveryService, "_pick_sitemap_targets", return_value={"careers": [], "csr": [], "reports": []}):

            mock_c_filter.return_value.first.return_value = mock_comp
            mock_dc_filter.return_value.count.return_value = 0

            res = BatchDiscoveryService._run_single_company_discovery(
                comp_name="Example Corp",
                final_website="https://example.com",
                official_domain="example.com",
                home_html="<html><body>Portal</body></html>",
                home_text="Example Corp",
                home_status=200,
                options={"extract_jobs": False, "extract_csr": False, "extract_reports": False, "deep_enrich": False, "concurrent_tracks": False},
                logs=[],
                now=datetime.now(timezone.utc),
            )
            self.assertEqual(res.get("outcome"), "AI_PROVIDER_FAILED")

    def test_csr_unmentioned_fields_display_not_mentioned(self):
        """Verifies that missing CSR fields strictly serialize to 'Not Mentioned' with clean portal link and summary."""
        mock_comp = MagicMock(company_id="COMP_CSR_01", sector="Technology", headquarters="Bangalore", verification_status="VERIFIED")
        mock_comp.website_url = "https://example.com"
        mock_comp.csr_portal_url = "https://example.com/sustainability"
        mock_comp.jobs.all.return_value.order_by.return_value.values.return_value = []
        mock_comp.csr_reports.all.return_value.order_by.return_value = []

        # CSR project with missing budget, location, beneficiaries, partner, and FY
        mock_csr_row = {
            'csr_id': 101,
            'project_name': 'Project Clean Water',
            'category': 'Water & Sanitation',
            'state': '',
            'geographic_location': '',
            'budget': '',
            'description': 'Providing safe drinking water to rural communities.',
            'source_url': 'https://example.com/sustainability/water',
            'canonical_url': 'https://example.com/sustainability/water',
            'confidence': 0.95,
            'evidence_text': 'Providing safe drinking water to rural communities.',
            'raw_metadata': {
                'beneficiaries': '',
                'implementing_partner': '',
                'financial_year': '',
                'ai_summary': 'Community water project.',
            },
        }
        mock_comp.csr_projects.all.return_value.order_by.return_value.values.return_value = [mock_csr_row]

        with patch("modules.admin_panel.models.Company.objects.filter") as mock_c_filter, \
             patch("modules.admin_panel.models.AuditTrail.objects.create"), \
             patch("modules.admin_panel.models.DroppedCandidate.objects.filter") as mock_dc_filter, \
             patch.object(BatchDiscoveryService, "fetch_page_content", return_value=("<html></html>", "Text", 200)), \
             patch.object(BatchDiscoveryService, "_publish_progress") as mock_pub, \
             patch.object(BatchDiscoveryService, "find_target_links_from_html", return_value={"csr_url": "https://example.com/sustainability"}), \
             patch.object(BatchDiscoveryService, "extract_company_metadata_from_html", return_value={"sector": "Technology", "headquarters": "Bangalore"}), \
             patch("modules.crawler_engine.hybrid_ai_service.HybridAIExtractionService.end_trace", return_value=[]), \
             patch.object(BatchDiscoveryService, "_fetch_sitemap_urls", return_value=[]), \
             patch.object(BatchDiscoveryService, "_pick_sitemap_targets", return_value={"careers": [], "csr": [], "reports": []}):

            mock_c_filter.return_value.first.return_value = mock_comp
            mock_dc_filter.return_value.count.return_value = 0

            res = BatchDiscoveryService._run_single_company_discovery(
                comp_name="Example Technologies",
                final_website="https://example.com",
                official_domain="example.com",
                home_html="<html><body>Example</body></html>",
                home_text="Example Technologies",
                home_status=200,
                options={"extract_jobs": False, "extract_csr": False, "extract_reports": False, "deep_enrich": False, "concurrent_tracks": False},
                logs=[],
                now=datetime.now(timezone.utc),
            )

            csr_list = res.get("csr", [])
            self.assertEqual(len(csr_list), 1)
            p = csr_list[0]
            # Must strictly be 'Not Mentioned'
            self.assertEqual(p["budget"], "Not Mentioned")
            self.assertEqual(p["state"], "Not Mentioned")
            self.assertEqual(p["geographic_location"], "Not Mentioned")
            self.assertEqual(p["beneficiaries"], "Not Mentioned")
            self.assertEqual(p["implementing_partner"], "Not Mentioned")
            self.assertEqual(p["financial_year"], "Not Mentioned")

            # Must have proper link and summary
            self.assertEqual(p["csr_portal_url"], "https://example.com/sustainability")
            self.assertTrue(bool(p["summary"]))
            self.assertIn("Water & Sanitation", res.get("csr_summary", ""))
            self.assertIn("Example Technologies", res.get("csr_summary", ""))
            self.assertIn("https://example.com/sustainability", res.get("csr_portal_url", ""))


if __name__ == "__main__":
    unittest.main()
