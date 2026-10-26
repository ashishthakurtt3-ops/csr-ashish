"""
tests_pure/test_homepage_verifier.py
====================================
Pure unit tests for Homepage Verification and Auto-Correction:
1. Variant generation (www/non-www, http->https, country subpath stripping / adding)
2. Disallowed domain filtering (news, directories, job boards, parked registrars, socials)
3. Parked domain detection (title & body heuristics)
4. Statutory proof validation (CIN and ISIN matching)
5. Confidence scoring & routing (HIGH, MEDIUM, NONE)
6. Locked website_url preservation
7. AI suggestion code validation gate (unvalidated suggestions rejected)
"""

import sys, types, os, unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for name, rel in (('modules', 'modules'), ('modules.crawler_engine', 'modules/crawler_engine')):
    if name not in sys.modules or not hasattr(sys.modules[name], '__path__'):
        m = types.ModuleType(name)
        m.__path__ = [str(ROOT / rel)]
        sys.modules[name] = m

from modules.crawler_engine.homepage_verifier import (
    generate_homepage_variants,
    is_disallowed_domain,
    is_parked_domain_content,
    validate_candidate_homepage,
    clean_tokens_for_company,
    FetchResult,
    HomepageVerifier,
)


class DummyCompany:
    """Lightweight mock of Company model for pure unit tests."""
    def __init__(
        self,
        company_id="COMP_TEST_001",
        company_name="ABB India Limited",
        legal_name="ABB India Limited",
        cin="L40266MH2008PLC343461",
        isin="INE117A01022",
        website_url="https://www.abb.com/in",
        website_url_locked=False,
        website_url_history=None,
        website_url_status="UNKNOWN",
        website_url_verified_at=None,
        website_url_review_notes=""
    ):
        self.company_id = company_id
        self.company_name = company_name
        self.legal_name = legal_name
        self.cin = cin
        self.isin = isin
        self.website_url = website_url
        self.website_url_locked = website_url_locked
        self.website_url_history = website_url_history or []
        self.website_url_status = website_url_status
        self.website_url_verified_at = website_url_verified_at
        self.website_url_review_notes = website_url_review_notes
        self.official_domain = None

    def save(self, update_fields=None):
        pass


class TestVariantGeneration(unittest.TestCase):
    def test_strip_country_subpath_in(self):
        url = "https://www.abb.com/in"
        variants = generate_homepage_variants(url, "ABB India Limited")
        # Should include root URL with and without www
        self.assertIn("https://www.abb.com/", variants)
        self.assertIn("https://abb.com/", variants)

    def test_www_and_non_www_alternation(self):
        url1 = "https://tatamotors.com"
        variants1 = generate_homepage_variants(url1, "Tata Motors")
        self.assertIn("https://www.tatamotors.com/", variants1)

        url2 = "https://www.infosys.com"
        variants2 = generate_homepage_variants(url2, "Infosys")
        self.assertIn("https://infosys.com/", variants2)

    def test_strip_common_landing_pages(self):
        url = "http://www.relianceindustries.com/home/index.html"
        variants = generate_homepage_variants(url, "Reliance Industries")
        self.assertIn("https://www.relianceindustries.com/", variants)
        # Scheme upgraded to HTTPS in top variants
        self.assertTrue(variants[0].startswith("https://"))

    def test_clean_company_tokens(self):
        tokens = clean_tokens_for_company("ABB India Limited")
        self.assertIn("ABB", tokens)

        tokens_tcs = clean_tokens_for_company("Tata Consultancy Services Limited")
        self.assertIn("Tata Consultancy Services", tokens_tcs)
        self.assertIn("TCS", tokens_tcs)


class TestDisallowedDomains(unittest.TestCase):
    def test_news_sites_rejected(self):
        disallowed = [
            "https://economictimes.indiatimes.com/company-profile",
            "https://www.moneycontrol.com/india/stockpricequote/auto-lcvs-hcvs/tatamotors/TM03",
            "https://www.livemint.com/companies/news/reliance-q3-results",
            "https://www.reuters.com/markets/companies/TCS.NS"
        ]
        for url in disallowed:
            rejected, reason = is_disallowed_domain(url)
            self.assertTrue(rejected, f"Should reject {url}")
            self.assertIn("disallowed_domain", reason)

    def test_directories_and_job_boards_rejected(self):
        disallowed = [
            "https://www.zaubacorp.com/company/ABB-INDIA-LIMITED/L32202KA1949PLC032923",
            "https://www.tofler.in/company/abb-india-limited",
            "https://www.naukri.com/abb-india-jobs",
            "https://www.linkedin.com/company/abb",
            "https://en.wikipedia.org/wiki/ABB"
        ]
        for url in disallowed:
            rejected, reason = is_disallowed_domain(url)
            self.assertTrue(rejected, f"Should reject {url}")

    def test_legitimate_domains_allowed(self):
        allowed = [
            "https://www.abb.com/global/en",
            "https://www.tcs.com",
            "https://www.tatamotors.com",
            "https://www.infosys.com"
        ]
        for url in allowed:
            rejected, reason = is_disallowed_domain(url)
            self.assertFalse(rejected, f"Should allow {url}")


class TestParkedDomainDetection(unittest.TestCase):
    def test_parked_domain_in_title(self):
        html = "<html><head><title>This domain is for sale | Sedo</title></head><body>Welcome</body></html>"
        is_parked, reason = is_parked_domain_content(html, "https://example-parked.com")
        self.assertTrue(is_parked)
        self.assertIn("parked_keyword", reason)

    def test_parked_domain_in_body(self):
        html = "<html><body><h1>Welcome</h1><p>Buy this domain now on HugeDomains</p></body></html>"
        is_parked, reason = is_parked_domain_content(html, "https://example-parked.com")
        self.assertTrue(is_parked)

    def test_normal_corporate_page_not_parked(self):
        html = (
            "<html><head><title>ABB - Technology Leader in Electrification and Automation</title></head>"
            "<body><h1>ABB Corporate</h1><a href='/investor-relations'>Investor Relations</a></body></html>"
        )
        is_parked, reason = is_parked_domain_content(html, "https://www.abb.com")
        self.assertFalse(is_parked)
        self.assertEqual(reason, "ok")


class TestDeterministicCodeValidation(unittest.TestCase):
    def test_statutory_cin_match_boosts_high_confidence(self):
        company = DummyCompany(company_name="ABB India Limited", cin="L40266MH2008PLC343461")
        html = (
            "<html><head><title>ABB India - Electrification</title></head>"
            "<body><footer>Corporate Identity Number: L40266MH2008PLC343461 | Registered Office</footer></body></html>"
        )
        fetch_res = FetchResult(
            url="https://www.abb.com/global/en",
            status_code=200,
            final_url="https://www.abb.com/global/en",
            html=html
        )
        val = validate_candidate_homepage("https://www.abb.com", company, fetch_result=fetch_res)
        self.assertTrue(val.valid)
        self.assertEqual(val.confidence, "HIGH")
        self.assertTrue(val.statutory_match)
        self.assertGreaterEqual(val.score, 70)

    def test_http_non_200_fails_validation(self):
        company = DummyCompany()
        fetch_res = FetchResult(
            url="https://www.abb.com/in",
            status_code=503,
            final_url="https://new.abb.com/indian-subcontinent",
            error="HTTP_503"
        )
        val = validate_candidate_homepage("https://www.abb.com/in", company, fetch_result=fetch_res)
        self.assertFalse(val.valid)
        self.assertEqual(val.confidence, "NONE")
        self.assertEqual(val.score, 0)

    def test_disallowed_domain_fails_validation(self):
        company = DummyCompany()
        val = validate_candidate_homepage("https://www.moneycontrol.com/india/stockpricequote/abb", company)
        self.assertFalse(val.valid)
        self.assertEqual(val.confidence, "NONE")
        self.assertTrue(val.is_disallowed)


class TestLockedAndSafetyGuards(unittest.TestCase):
    @patch("modules.crawler_engine.homepage_verifier.fetch_candidate_page")
    def test_never_overwrite_locked_website_url(self, mock_fetch):
        # Current URL returns 503
        fetch_current = FetchResult(url="https://www.abb.com/in", status_code=503)
        # Variant returns 200 with valid Indian subcontinent URL and statutory CIN
        fetch_variant = FetchResult(
            url="https://new.abb.com/indian-subcontinent",
            status_code=200,
            final_url="https://new.abb.com/indian-subcontinent",
            html="<html><head><title>ABB India - Electrification</title></head><body>CIN: L40266MH2008PLC343461</body></html>"
        )

        def side_effect(url, **kwargs):
            if "abb.com/in" in url:
                return fetch_current
            return fetch_variant

        mock_fetch.side_effect = side_effect

        company = DummyCompany(
            website_url="https://www.abb.com/in",
            website_url_locked=True  # LOCKED!
        )

        res = HomepageVerifier.verify_company(company, dry_run=False)
        self.assertEqual(res["status"], "LOCKED_PRESERVED")
        self.assertEqual(company.website_url, "https://www.abb.com/in")  # MUST NOT CHANGE
        self.assertIn("locked", res["evidence"].lower())

    @patch("modules.crawler_engine.homepage_verifier.fetch_candidate_page")
    def test_auto_corrects_when_not_locked(self, mock_fetch):
        fetch_current = FetchResult(url="https://www.abb.com/in", status_code=503)
        fetch_variant = FetchResult(
            url="https://new.abb.com/indian-subcontinent",
            status_code=200,
            final_url="https://new.abb.com/indian-subcontinent",
            html="<html><head><title>ABB India - Electrification</title></head><body>CIN: L40266MH2008PLC343461</body></html>"
        )

        def side_effect(url, **kwargs):
            if "abb.com/in" in url:
                return fetch_current
            return fetch_variant

        mock_fetch.side_effect = side_effect

        company = DummyCompany(
            website_url="https://www.abb.com/in",
            website_url_locked=False
        )

        res = HomepageVerifier.verify_company(company, dry_run=False)
        self.assertEqual(res["status"], "AUTO_CORRECTED")
        self.assertEqual(company.website_url, "https://new.abb.com/indian-subcontinent")
        self.assertEqual(len(company.website_url_history), 1)
        self.assertEqual(company.website_url_history[0]["old_url"], "https://www.abb.com/in")
        self.assertEqual(company.website_url_status, "AUTO_CORRECTED")


class TestWrongEntityGuardAndNoOp(unittest.TestCase):
    def test_abb_india_rejects_global_en(self):
        from modules.crawler_engine.homepage_verifier import is_wrong_entity_or_parent
        company = DummyCompany(company_name="ABB India Limited", legal_name="ABB India Limited")
        is_wrong, reason = is_wrong_entity_or_parent("https://www.abb.com/global/en", "<html><title>ABB Group</title></html>", company)
        self.assertTrue(is_wrong)
        self.assertIn("abb.com/global/en", reason)

    def test_bajaj_finance_rejects_finserv_root(self):
        from modules.crawler_engine.homepage_verifier import is_wrong_entity_or_parent
        company = DummyCompany(company_name="Bajaj Finance Limited", legal_name="Bajaj Finance Limited")
        is_wrong, reason = is_wrong_entity_or_parent("https://www.bajajfinserv.in/", "<html><title>Bajaj Finserv</title></html>", company)
        self.assertTrue(is_wrong)
        self.assertIn("bajajfinserv.in", reason)

    def test_united_spirits_rejects_theubgroup(self):
        from modules.crawler_engine.homepage_verifier import is_wrong_entity_or_parent
        company = DummyCompany(company_name="United Spirits Limited", legal_name="United Spirits Limited")
        is_wrong, reason = is_wrong_entity_or_parent("https://www.theubgroup.com/", "<html><title>UB Group</title></html>", company)
        self.assertTrue(is_wrong)
        self.assertIn("UB Group", reason)

    def test_no_op_prevention(self):
        from modules.crawler_engine.homepage_verifier import normalize_url_for_comparison
        self.assertEqual(
            normalize_url_for_comparison("https://www.au.bank.in/"),
            normalize_url_for_comparison("https://au.bank.in")
        )
        self.assertEqual(
            normalize_url_for_comparison("http://bel-india.in/"),
            normalize_url_for_comparison("https://bel-india.in")
        )


if __name__ == '__main__':
    unittest.main()
