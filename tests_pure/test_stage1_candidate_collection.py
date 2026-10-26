"""
tests_pure/test_stage1_candidate_collection.py
==============================================
Pure unit tests for Pipeline Stage 1:
- URL normalization & canonicalization
- ATS pattern matching from config/ats_domains.json
- Junk filtering (social, login, terms, loan forms, assets)
- Candidate link collection & hierarchy extraction
- Multi-tenant ATS ownership filtering
"""

import unittest
from pathlib import Path

from modules.crawler_engine.normalizers import (
    normalize_canonical_url,
    is_junk_url,
    match_ats_pattern,
    load_ats_patterns,
)
from modules.crawler_engine.candidate_collector import CandidateCollector


class TestURLNormalization(unittest.TestCase):
    def test_tracking_params_stripped(self):
        url = "https://www.acme.com/careers?utm_source=linkedin&utm_medium=cpc&utm_campaign=hiring&fbclid=12345&ref=homepage"
        norm = normalize_canonical_url(url)
        self.assertEqual(norm, "https://www.acme.com/careers")

    def test_fragments_stripped(self):
        url = "https://www.acme.com/csr#section2"
        norm = normalize_canonical_url(url)
        self.assertEqual(norm, "https://www.acme.com/csr")

    def test_text_fragments_stripped(self):
        url = "https://www.acme.com/sustainability#:~:text=Net%20Zero%20by%202030"
        norm = normalize_canonical_url(url)
        self.assertEqual(norm, "https://www.acme.com/sustainability")

    def test_trailing_slashes_normalized(self):
        url1 = "https://www.acme.com/careers/"
        url2 = "https://www.acme.com/careers"
        self.assertEqual(normalize_canonical_url(url1), normalize_canonical_url(url2))

    def test_relative_url_resolution(self):
        norm = normalize_canonical_url("/about/csr", base_url="https://www.acme.com/index.html")
        self.assertEqual(norm, "https://www.acme.com/about/csr")


class TestATSPatternMatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = load_ats_patterns()

    def test_workday_career_site_match(self):
        url = "https://unilever.wd3.myworkdayjobs.com/Unilever_Careers/job/Mumbai/Analyst_123"
        m = match_ats_pattern(url, self.patterns)
        self.assertIsNotNone(m)
        self.assertEqual(m["platform"], "Workday")

    def test_greenhouse_board_match(self):
        url = "https://boards.greenhouse.io/razorpay/jobs/4123456"
        m = match_ats_pattern(url, self.patterns)
        self.assertIsNotNone(m)
        self.assertEqual(m["platform"], "Greenhouse")

    def test_lever_jobs_match(self):
        url = "https://jobs.lever.co/paytm/9eed4fec-73f7-4114"
        m = match_ats_pattern(url, self.patterns)
        self.assertIsNotNone(m)
        self.assertEqual(m["platform"], "Lever")

    def test_smartrecruiters_careers_match(self):
        url = "https://careers.smartrecruiters.com/AcmeCorp/743999"
        m = match_ats_pattern(url, self.patterns)
        self.assertIsNotNone(m)
        self.assertEqual(m["platform"], "SmartRecruiters")

    def test_oracle_cloud_career_site_match(self):
        url = "https://eibd.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/1"
        m = match_ats_pattern(url, self.patterns)
        self.assertIsNotNone(m)
        self.assertEqual(m["platform"], "Oracle_Cloud")

    def test_broad_non_ats_domain_not_matched(self):
        # A broad domain without career site path must NOT match
        url = "https://www.oraclecloud.com"
        m = match_ats_pattern(url, self.patterns)
        self.assertIsNone(m)

        url_general = "https://www.google.com/search?q=jobs"
        m_gen = match_ats_pattern(url_general, self.patterns)
        self.assertIsNone(m_gen)


class TestJunkFiltering(unittest.TestCase):
    def test_protocol_junk(self):
        self.assertTrue(is_junk_url("mailto:careers@acme.com")[0])
        self.assertTrue(is_junk_url("tel:+919876543210")[0])
        self.assertTrue(is_junk_url("javascript:void(0)")[0])

    def test_social_media_junk(self):
        self.assertTrue(is_junk_url("https://www.facebook.com/acme")[0])
        self.assertTrue(is_junk_url("https://twitter.com/acme")[0])
        self.assertTrue(is_junk_url("https://instagram.com/acme")[0])
        self.assertTrue(is_junk_url("https://linkedin.com/shareArticle?url=xyz")[0])

    def test_legal_and_privacy_junk(self):
        self.assertTrue(is_junk_url("https://acme.com/privacy-policy")[0])
        self.assertTrue(is_junk_url("https://acme.com/terms-and-conditions")[0])
        self.assertTrue(is_junk_url("https://acme.com/cookie-policy")[0])
        self.assertTrue(is_junk_url("https://acme.com/disclaimer")[0])

    def test_auth_login_junk(self):
        self.assertTrue(is_junk_url("https://acme.com/login")[0])
        self.assertTrue(is_junk_url("https://acme.com/signin")[0])
        self.assertTrue(is_junk_url("https://acme.com/forgot-password")[0])

    def test_consumer_banking_and_retail_junk(self):
        self.assertTrue(is_junk_url("https://acme.com/apply-for-personal-loan", "Personal Loan")[0])
        self.assertTrue(is_junk_url("https://acme.com/credit-card", "Apply Credit Card")[0])
        self.assertTrue(is_junk_url("https://acme.com/cart")[0])
        self.assertTrue(is_junk_url("https://acme.com/branch-locator")[0])

    def test_static_assets_junk(self):
        self.assertTrue(is_junk_url("https://acme.com/static/logo.png")[0])
        self.assertTrue(is_junk_url("https://acme.com/static/style.css")[0])
        self.assertTrue(is_junk_url("https://acme.com/static/bundle.js")[0])

    def test_valid_pages_not_junk(self):
        self.assertFalse(is_junk_url("https://acme.com/careers", "Careers")[0])
        self.assertFalse(is_junk_url("https://acme.com/csr", "Corporate Social Responsibility")[0])
        self.assertFalse(is_junk_url("https://acme.com/sustainability", "Sustainability & ESG")[0])
        self.assertFalse(is_junk_url("https://acme.com/investors/annual-reports", "Annual Reports")[0])

    def test_pdf_files_not_junk(self):
        """PDFs on official corporate domains must NEVER be filtered as junk media."""
        self.assertFalse(is_junk_url("https://acme.com/csr/csr-policy-2024.pdf", "CSR Policy")[0])
        self.assertFalse(is_junk_url("https://acme.com/csr/csr_project_list_2023_24.pdf", "CSR Project List FY24")[0])
        self.assertFalse(is_junk_url("https://acme.com/investor-relations/annual_report_2024.pdf", "Annual Report FY24")[0])
        self.assertFalse(is_junk_url("https://acme.com/sustainability/brsr_report_2024.pdf", "BRSR Report 2023-24")[0])


class TestCandidateCollection(unittest.TestCase):
    SAMPLE_HTML = """
    <!DOCTYPE html>
    <html>
    <head><title>Acme Corporation</title></head>
    <body>
      <header>
        <nav class="navbar">
          <ul>
            <li class="nav-item dropdown">
              <span class="dropdown-title">About Us</span>
              <ul class="submenu">
                <li><a href="/about/overview">Overview</a></li>
                <li><a href="/careers">Careers & Jobs</a></li>
                <li><a href="https://acmefoundation.org">Acme Foundation (CSR)</a></li>
              </ul>
            </li>
            <li class="nav-item">
              <a href="/sustainability">Sustainability</a>
            </li>
            <li class="nav-item">
              <a href="https://jobs.lever.co/acme">Open Vacancies</a>
            </li>
            <li><a href="/privacy-policy">Privacy Policy</a></li>
            <li><a href="https://facebook.com/acme">Facebook</a></li>
            <li><a href="https://randomnews.com/news/123">Random News Article</a></li>
          </ul>
        </nav>
      </header>
      <main>
        <p>Welcome to Acme Corporation. Explore our <a href="/investors/annual-reports">Annual Reports</a>.</p>
        <p>Download our <a href="/investor-relations/annual_report_2024.pdf">Annual Report FY24 PDF</a>.</p>
        <p>Contact us at <a href="mailto:info@acme.com">info@acme.com</a>.</p>
      </main>
      <footer>
        <a href="/csr-policy">CSR Policy</a>
        <a href="/csr/csr_policy_2024.pdf">CSR Policy PDF</a>
        <a href="/terms-of-use">Terms of Use</a>
      </footer>
    </body>
    </html>
    """

    def setUp(self):
        self.collector = CandidateCollector(
            allow_playwright=False,
            probe_sitemaps=False,
            probe_subdomains=False,
            probe_common_paths=False,
        )

    def test_collection_and_hierarchy(self):
        candidates = self.collector.collect_candidates(
            homepage_url="https://www.acme.com",
            company_symbol="ACME",
            html_override=self.SAMPLE_HTML,
            max_candidates=30
        )

        self.assertTrue(len(candidates) > 0)
        self.assertTrue(len(candidates) <= 30)

        # Check candidate structure and strict 1..N IDs
        for idx, c in enumerate(candidates, start=1):
            self.assertEqual(c["id"], idx)
            self.assertIn("url", c)
            self.assertIn("link_text", c)
            self.assertIn("menu_path", c)
            self.assertIn("source", c)

        # Check careers candidate with hierarchy
        urls = [c["url"] for c in candidates]
        self.assertIn("https://www.acme.com/careers", urls)
        career_cand = next(c for c in candidates if c["url"] == "https://www.acme.com/careers")
        self.assertIn("About Us", career_cand["menu_path"])

        # Check external linked navigation site (Acme Foundation)
        self.assertIn("https://acmefoundation.org", urls)
        found_cand = next(c for c in candidates if c["url"] == "https://acmefoundation.org")
        self.assertTrue(found_cand["external_linked"])

        # Check Lever ATS detection
        self.assertIn("https://jobs.lever.co/acme", urls)
        lever_cand = next(c for c in candidates if c["url"] == "https://jobs.lever.co/acme")
        self.assertTrue(lever_cand["ats_match"])
        self.assertEqual(lever_cand["ats_platform"], "Lever")

        # Check junk was filtered out
        self.assertNotIn("https://www.acme.com/privacy-policy", urls)
        self.assertNotIn("https://facebook.com/acme", urls)
        self.assertNotIn("mailto:info@acme.com", urls)

        # Check unrelated external domain was dropped
        self.assertNotIn("https://randomnews.com/news/123", urls)

        # Check PDF candidates on official domain are preserved
        self.assertIn("https://www.acme.com/investor-relations/annual_report_2024.pdf", urls)
        self.assertIn("https://www.acme.com/csr/csr_policy_2024.pdf", urls)

    def test_shared_tenant_ownership_filtering(self):
        # Oracle Cloud shared site CX_3003 belongs to ADANIPOWER, NOT ACC
        # When crawling ACC, an ATS link to CX_3003 must be discarded!
        html_with_wrong_ats = """
        <header>
          <a href="https://eibd.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_3003/job/1">Adani Power Job</a>
        </header>
        """
        candidates = self.collector.collect_candidates(
            homepage_url="https://www.accltd.com",
            company_symbol="ACC",
            html_override=html_with_wrong_ats,
            max_candidates=10
        )
        urls = [c["url"] for c in candidates]
        self.assertNotIn("https://eibd.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_3003/job/1", urls)

    def test_sitemap_extraction_with_mock(self):
        from unittest.mock import patch, MagicMock
        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
          <url><loc>https://www.acme.com/about-us</loc></url>
          <url><loc>https://www.acme.com/careers/digital-roles</loc></url>
          <url><loc>https://www.acme.com/csr/annual-action-plan-2025</loc></url>
          <url><loc>https://www.acme.com/sustainability/net-zero</loc></url>
          <url><loc>https://www.acme.com/products/item-999</loc></url>
        </urlset>
        """
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = sitemap_xml

        with patch("curl_cffi.requests.get", return_value=mock_resp):
            sitemap_links = self.collector._extract_sitemap_candidates("https://www.acme.com")
            urls = [item["url"] for item in sitemap_links]
            self.assertIn("https://www.acme.com/careers/digital-roles", urls)
            self.assertIn("https://www.acme.com/csr/annual-action-plan-2025", urls)
            self.assertIn("https://www.acme.com/sustainability/net-zero", urls)
            # Products page is not in the career/csr/sustainability keyword list
            self.assertNotIn("https://www.acme.com/products/item-999", urls)


if __name__ == "__main__":
    unittest.main()

