"""
tests/test_stage1_discovery_helpers.py
======================================
Unit tests for Stage 1 discovery helpers without live network requests.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

import django
if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()

from modules.crawler_engine.discovery_helpers import (
    is_real_deep_url,
    get_registrable_domain,
    is_same_registrable_domain_or_ats,
    is_allowed_domain_or_ats,
    is_document_asset_url,
    is_static_asset_url,
    verify_careers_url_content,
    fast_homepage_intelligence,
)
from modules.crawler_engine.strategies.ats_strategy import ATSStrategy
from modules.crawler_engine.strategies.base import ExtractionContext
from modules.crawler_engine.crawler import (
    try_fetch_workday_json,
    try_fetch_greenhouse_jobs,
    try_fetch_successfactors_jobs,
    dispatch_ats_direct,
)


class Stage1DiscoveryHelpersTestCase(unittest.TestCase):

    def test_is_real_deep_url_rejects_empty_or_none(self):
        self.assertFalse(is_real_deep_url(None, "https://company.com"))
        self.assertFalse(is_real_deep_url("", "https://company.com"))
        self.assertFalse(is_real_deep_url("   ", "https://company.com"))

    def test_is_real_deep_url_rejects_root_homepage(self):
        # Exact match
        self.assertFalse(is_real_deep_url("https://company.com", "https://company.com"))
        # Trailing slash differences
        self.assertFalse(is_real_deep_url("https://company.com/", "https://company.com"))
        self.assertFalse(is_real_deep_url("http://company.com", "https://company.com/"))
        # www prefix differences
        self.assertFalse(is_real_deep_url("https://www.company.com/", "https://company.com"))
        self.assertFalse(is_real_deep_url("https://company.com", "https://www.company.com/"))
        # Case insensitivity
        self.assertFalse(is_real_deep_url("https://WWW.Company.Com/", "https://company.com"))

    def test_is_real_deep_url_accepts_subdomains_and_paths(self):
        # Deep path
        self.assertTrue(is_real_deep_url("https://company.com/careers", "https://company.com"))
        self.assertTrue(is_real_deep_url("https://company.com/jobs/openings", "https://company.com"))
        self.assertTrue(is_real_deep_url("https://www.company.com/sustainability", "https://company.com"))
        # Deep subdomain
        self.assertTrue(is_real_deep_url("https://careers.company.com", "https://company.com"))
        self.assertTrue(is_real_deep_url("https://careers.company.com/", "https://www.company.com"))
        self.assertTrue(is_real_deep_url("https://jobs.company.com", "https://company.com"))
        # External ATS domain
        self.assertTrue(is_real_deep_url("https://jobs.lever.co/company", "https://company.com"))
        self.assertTrue(is_real_deep_url("https://company.myworkdayjobs.com/careers", "https://company.com"))

    def test_get_registrable_domain(self):
        self.assertEqual(get_registrable_domain("https://careers.tatamotors.com/openings"), "tatamotors.com")
        self.assertEqual(get_registrable_domain("https://www.sbi.co.in/careers"), "sbi.co.in")
        self.assertEqual(get_registrable_domain("new.abb.com"), "abb.com")
        self.assertEqual(get_registrable_domain("https://iocl.com"), "iocl.com")
        self.assertEqual(get_registrable_domain("https://sec.wd3.myworkdayjobs.com/Samsung_Careers"), "myworkdayjobs.com")

    def test_is_same_registrable_domain_or_ats(self):
        # Same domain / subdomain
        self.assertTrue(is_same_registrable_domain_or_ats("https://careers.tatapower.com", "https://www.tatapower.com"))
        self.assertTrue(is_same_registrable_domain_or_ats("https://tatapower.com/csr", "https://tatapower.com"))
        # Unrelated domain
        self.assertFalse(is_same_registrable_domain_or_ats("https://randomdomain.com/jobs", "https://tatapower.com"))
        # Known ATS domains
        self.assertTrue(is_same_registrable_domain_or_ats("https://tatapower.myworkdayjobs.com/en-US/careers", "https://tatapower.com"))
        self.assertTrue(is_same_registrable_domain_or_ats("https://jobs.lever.co/tatapower", "https://tatapower.com"))
        self.assertTrue(is_same_registrable_domain_or_ats("https://boards.greenhouse.io/tatapower", "https://tatapower.com"))

    def test_document_asset_classification(self):
        # PDF and document assets must be recognized by is_document_asset_url
        self.assertTrue(is_document_asset_url("https://company.com/reports/CSR_Annual_Report_2024.pdf"))
        self.assertTrue(is_document_asset_url("https://company.com/download.aspx?file=BRSR_Report.pdf"))
        self.assertTrue(is_document_asset_url("https://company.com/disclosures/esg_data.xlsx"))
        self.assertTrue(is_document_asset_url("https://company.com/docs/csr_policy.docx"))
        self.assertTrue(is_document_asset_url("https://company.com/presentations/csr_overview.pptx"))
        # Media / code are not document assets
        self.assertFalse(is_document_asset_url("https://company.com/assets/logo.png"))
        self.assertFalse(is_document_asset_url("https://company.com/scripts/bundle.js"))

        # Statutory PDF reports must NEVER be treated as static noise in is_static_asset_url
        self.assertFalse(is_static_asset_url("https://company.com/reports/CSR_Report_2023_24.pdf"))
        self.assertFalse(is_static_asset_url("https://company.com/wp-content/uploads/2024/05/BRSR_Disclosure.pdf"))
        self.assertFalse(is_static_asset_url("https://company.com/downloads/csr_policy.pdf?v=2"))

        # Pure static noise (images, fonts, styles, scripts) must be rejected
        self.assertTrue(is_static_asset_url("https://company.com/assets/banner.png"))
        self.assertTrue(is_static_asset_url("https://company.com/static/style.css"))
        self.assertTrue(is_static_asset_url("https://company.com/fonts/inter.woff2"))
        self.assertTrue(is_static_asset_url("https://company.com/assets/images/header.jpg"))

    def test_short_and_foundation_domain_matching(self):
        # 2- and 3-character enterprise roots
        self.assertTrue(is_allowed_domain_or_ats("https://www.itcportal.com/sustainability", "https://itc.in"))
        self.assertTrue(is_allowed_domain_or_ats("https://careers.ril.com/rilcareers", "https://ril.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://sbifoundation.co.in/projects", "https://sbi.co.in"))
        self.assertTrue(is_allowed_domain_or_ats("https://new.abb.com/careers", "https://abb.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://www.ibm.com/employment", "https://ibm.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://tcscareers.com/india", "https://tcs.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://www.gecareers.com", "https://ge.com"))

        # Approved corporate foundations and CSR initiative domains
        self.assertTrue(is_allowed_domain_or_ats("https://tatatrusts.org/our-work", "https://tata.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://reliancefoundation.org/our-focus", "https://ril.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://azimpremjifoundation.org/what-we-do", "https://wipro.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://infosysprize.org/laureates", "https://infosys.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://adlsfoundation.org/initiatives", "https://adls.com"))
        self.assertTrue(is_allowed_domain_or_ats("https://adanifoundation.org/programmes", "https://adani.com"))

        # Unrelated domains must be rejected
        self.assertFalse(is_allowed_domain_or_ats("https://unrelatedcompetitor.com/jobs", "https://tatamotors.com"))
        self.assertFalse(is_allowed_domain_or_ats("https://phishingportal.org/login", "https://sbi.co.in"))

    def test_greenhouse_token_extraction(self):
        strategy = ATSStrategy()

        # Script embed with ?for=company
        html_script = '<script src="https://boards.greenhouse.io/embed/job_board.js?for=stripe"></script>'
        ctx = ExtractionContext(company=MagicMock(ats_platform=None, ats_type=None), careers_url="https://company.com/careers", html_content=html_script)
        detected = strategy.detect(ctx)
        self.assertTrue(detected)
        self.assertEqual(ctx.discovered_ats_platform, "greenhouse")
        self.assertEqual(ctx.discovered_ats_token, "stripe")
        self.assertNotEqual(ctx.discovered_ats_token, "embed")
        self.assertEqual(ctx.discovered_ats_url, "https://boards.greenhouse.io/stripe")

        # Iframe embed with ?for=company
        html_iframe = '<iframe src="https://boards.greenhouse.io/embed/job_board?for=figma" width="100%"></iframe>'
        ctx2 = ExtractionContext(company=MagicMock(ats_platform=None, ats_type=None), careers_url="https://company.com/careers", html_content=html_iframe)
        detected2 = strategy.detect(ctx2)
        self.assertTrue(detected2)
        self.assertEqual(ctx2.discovered_ats_token, "figma")
        self.assertEqual(ctx2.discovered_ats_url, "https://boards.greenhouse.io/figma")

    def test_workday_cxs_url_parsing_and_no_india_filter(self):
        strategy = ATSStrategy()

        # Workday URL embedded in HTML
        html_wd = '<a href="https://company.wd3.myworkdayjobs.com/en-US/Careers/job/Bengaluru/Software-Engineer_R123">Apply</a>'
        ctx = ExtractionContext(company=MagicMock(ats_platform=None, ats_type=None), careers_url="https://company.com/jobs", html_content=html_wd)
        detected = strategy.detect(ctx)
        self.assertTrue(detected)
        self.assertEqual(ctx.discovered_ats_platform, "workday")
        self.assertIn("company.wd3.myworkdayjobs.com", ctx.discovered_ats_url)
        self.assertEqual(ctx.final_url, ctx.discovered_ats_url)

        # Mock cffi_post to inspect payload
        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "total": 1,
                "jobPostings": [{
                    "title": "Cloud Architect",
                    "externalPath": "/job/Bengaluru/Cloud-Architect_R999",
                    "locationsText": "Bengaluru, Karnataka",
                    "postedOn": "Posted 2 Days Ago"
                }]
            }
            mock_post.return_value = mock_resp

            jobs = strategy._extract_workday("https://company.wd3.myworkdayjobs.com/en-US/Careers/job/Bengaluru/Software-Engineer_R123", None, ctx)

            # Ensure post payload does NOT have hardcoded searchText: 'India'
            call_kwargs = mock_post.call_args[1]
            payload = call_kwargs.get("json", {})
            self.assertEqual(payload.get("searchText"), "")

            # Ensure extraction constructed direct URL preserving locale and site, NOT '/job' or job ID
            self.assertEqual(len(jobs), 1)
            self.assertEqual(jobs[0]["title"], "Cloud Architect")
            self.assertTrue(jobs[0]["application_url"].startswith("https://company.wd3.myworkdayjobs.com/en-US/Careers/job/"))

    def test_successfactors_query_preservation(self):
        strategy = ATSStrategy()
        ctx = ExtractionContext(company=MagicMock(ats_platform=None, ats_type=None), careers_url="https://career8.successfactors.com/career?company=tatamotors")

        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.url = "https://career8.successfactors.com/search/?company=tatamotors&q=&startrow=0"
            mock_resp.text = """
            <html><body>
                <a href="/job/Pune-Engineer/12345/">Lead Vehicle Dynamics Engineer</a>
            </body></html>
            """
            mock_get.return_value = mock_resp

            # Call extract on SuccessFactors with multi-tenant company query
            jobs = strategy._extract_successfactors("https://career8.successfactors.com/career?company=tatamotors", None, ctx)

            # Check that cffi_get was called with the company query preserved
            call_url = mock_get.call_args_list[0][0][0]
            self.assertIn("company=tatamotors", call_url)
            self.assertIn("startrow=0", call_url)

    def test_fast_homepage_intelligence_schema_and_caching(self):
        mock_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <link rel="canonical" href="https://www.examplecorp.com/">
        </head>
        <body>
            <header>
                <nav>
                    <a href="/about">About Us</a>
                    <a href="/careers">Careers</a>
                </nav>
            </header>
            <main>
                <h1>Welcome to ExampleCorp</h1>
                <iframe src="https://examplecorp.wd3.myworkdayjobs.com/en-US/External"></iframe>
            </main>
            <footer>
                <a href="/sustainability">Sustainability</a>
                <a href="/csr-policy.pdf">CSR Policy</a>
            </footer>
        </body>
        </html>
        """
        session_cache = {}
        with patch("curl_cffi.requests.get") as mock_get:
            resp = MagicMock()
            resp.status_code = 200
            resp.url = "https://www.examplecorp.com/"
            resp.text = mock_html
            mock_get.return_value = resp

            intel = fast_homepage_intelligence("https://examplecorp.com", session_cache=session_cache)

            # Check schema
            self.assertIn("canonical_url", intel)
            self.assertIn("domain", intel)
            self.assertIn("nav_links", intel)
            self.assertIn("footer_links", intel)
            self.assertIn("sitemaps", intel)
            self.assertIn("detected_ats", intel)
            self.assertIn("ats_url", intel)

            self.assertEqual(intel["domain"], "examplecorp.com")
            self.assertEqual(intel["detected_ats"], "workday")
            self.assertIn("examplecorp.wd3.myworkdayjobs.com", intel["ats_url"])

            # Verify session caching: subsequent call uses cache without network hit
            mock_get.reset_mock()
            cached_intel = fast_homepage_intelligence("https://examplecorp.com", session_cache=session_cache)
            mock_get.assert_not_called()
            self.assertEqual(cached_intel["domain"], "examplecorp.com")

    def test_dispatch_ats_direct_interface(self):
        with patch("modules.crawler_engine.crawler.try_fetch_lever_jobs") as mock_lever:
            mock_lever.return_value = [{
                "title": "Principal Architect",
                "location": "Bengaluru",
                "department": "Engineering",
                "apply_url": "https://jobs.lever.co/techcorp/abc-123",
                "posted_on": "2024-05-01",
                "verbatim_quote": "Principal Architect - Bengaluru",
                "verification_status": "PUBLISHED"
            }]

            results = dispatch_ats_direct("lever", "https://jobs.lever.co/techcorp")
            self.assertEqual(len(results), 1)
            item = results[0]
            self.assertEqual(item["title"], "Principal Architect")
            self.assertEqual(item["location"], "Bengaluru")
            self.assertEqual(item["application_url"], "https://jobs.lever.co/techcorp/abc-123")
            self.assertEqual(item["source_url"], "https://jobs.lever.co/techcorp")
            self.assertEqual(item["department"], "Engineering")

    def test_verify_careers_url_content_jsonld(self):
        html = """
        <html>
            <head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org/",
                    "@type": "JobPosting",
                    "title": "Software Engineer",
                    "description": "Develop high-scale cloud platforms"
                }
                </script>
            </head>
            <body><h1>Welcome to Careers</h1></body>
        </html>
        """
        has_signals, conf, signals = verify_careers_url_content(html, "https://company.com/careers")
        self.assertTrue(has_signals)
        self.assertGreaterEqual(conf, 0.70)
        self.assertIn("jsonld_job_posting", signals)

    def test_verify_careers_url_content_ats_iframe(self):
        html = """
        <html>
            <body>
                <h1>Current Openings</h1>
                <iframe src="https://company.myworkdayjobs.com/en-US/careers" width="100%" height="600"></iframe>
            </body>
        </html>
        """
        has_signals, conf, signals = verify_careers_url_content(html, "https://company.com/careers")
        self.assertTrue(has_signals)
        self.assertTrue(any("ats_reference" in s for s in signals))

    def test_verify_careers_url_content_apply_links(self):
        html = """
        <html>
            <body>
                <div class="openings">
                    <div>
                        <h2>Data Engineer</h2>
                        <a href="/job/49210">Apply Now</a>
                    </div>
                    <div>
                        <h2>DevOps Lead</h2>
                        <a href="/job/49211">Apply Now</a>
                    </div>
                </div>
            </body>
        </html>
        """
        has_signals, conf, signals = verify_careers_url_content(html, "https://company.com/careers")
        self.assertTrue(has_signals)
        self.assertTrue(any("job_action_links" in s for s in signals))

    def test_verify_careers_url_content_empty_or_no_signals(self):
        html = "<html><body><h1>About Our Leadership Team</h1><p>We are dedicated to excellence.</p></body></html>"
        has_signals, conf, signals = verify_careers_url_content(html, "https://company.com/about")
        self.assertFalse(has_signals)
        self.assertEqual(conf, 0.25)
        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()

