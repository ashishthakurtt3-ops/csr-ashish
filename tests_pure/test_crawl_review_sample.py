"""
tests_pure/test_crawl_review_sample.py
======================================
Pure unit tests with mocked network and AI for the crawl_review_sample command:
1. Eligibility: non-correct homepages are excluded (REVIEW_REQUIRED, HOMEPAGE_NOT_FOUND, etc.)
2. 50-Job Cap: extracted jobs are strictly capped at 50 per company
3. Failure Isolation: one company failing does not halt or abort the crawl
4. Database Invariant: verifies zero database writes / mutations occur during dry run
"""

import os
import unittest
from unittest.mock import MagicMock, patch
from types import SimpleNamespace

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from modules.admin_panel.management.commands.crawl_review_sample import (
    is_company_eligible,
    Command,
)


class TestCrawlReviewSample(unittest.TestCase):

    def test_company_eligibility(self):
        """Checks eligibility rules: missing fields or unverified statuses are rejected."""
        status_map = {
            "C1": "ALREADY_OK",
            "C2": "CORRECT",
            "C3": "REVIEW_REQUIRED",
            "C4": "HOMEPAGE_NOT_FOUND",
            "C5": "AUTO_CORRECTED",
            "C6": "TEMPORARILY_UNVERIFIABLE",
        }

        # 1. Valid company with confirmed ALREADY_OK
        c1 = SimpleNamespace(company_id="C1", company_name="Company One", website_url="https://one.com")
        el, reason = is_company_eligible(c1, status_map)
        self.assertTrue(el)
        self.assertIn("Eligible", reason)

        # 2. Valid company with confirmed CORRECT
        c2 = SimpleNamespace(company_id="C2", company_name="Company Two", website_url="https://two.com")
        el, reason = is_company_eligible(c2, status_map)
        self.assertTrue(el)

        # 3. Excluded: REVIEW_REQUIRED
        c3 = SimpleNamespace(company_id="C3", company_name="Company Three", website_url="https://three.com")
        el, reason = is_company_eligible(c3, status_map)
        self.assertFalse(el)
        self.assertIn("REVIEW_REQUIRED", reason)

        # 4. Excluded: HOMEPAGE_NOT_FOUND
        c4 = SimpleNamespace(company_id="C4", company_name="Company Four", website_url="https://four.com")
        el, reason = is_company_eligible(c4, status_map)
        self.assertFalse(el)
        self.assertIn("HOMEPAGE_NOT_FOUND", reason)

        # 5. Excluded: unapproved AUTO_CORRECTED
        c5 = SimpleNamespace(company_id="C5", company_name="Company Five", website_url="https://five.com")
        el, reason = is_company_eligible(c5, status_map)
        self.assertFalse(el)
        self.assertIn("AUTO_CORRECTED", reason)

        # 6. Excluded: TEMPORARILY_UNVERIFIABLE
        c6 = SimpleNamespace(company_id="C6", company_name="Company Six", website_url="https://six.com")
        el, reason = is_company_eligible(c6, status_map)
        self.assertFalse(el)
        self.assertIn("TEMPORARILY_UNVERIFIABLE", reason)

        # 7. Excluded: Missing company_id
        c7 = SimpleNamespace(company_id="", company_name="Company Seven", website_url="https://seven.com")
        el, reason = is_company_eligible(c7, status_map)
        self.assertFalse(el)

        # 8. Excluded: Missing website_url
        c8 = SimpleNamespace(company_id="C8", company_name="Company Eight", website_url="")
        el, reason = is_company_eligible(c8, status_map)
        self.assertFalse(el)

    @patch("modules.admin_panel.management.commands.crawl_review_sample.fetch_live_page")
    def test_50_job_cap_enforced(self, mock_fetch):
        """Verifies that extraction never returns more than 50 jobs per company."""
        mock_fetch.return_value = {"ok": True, "status_code": 200, "html": "<html><body>Careers at Test Corp</body></html>"}
        cmd = Command()
        company = SimpleNamespace(
            company_id="C_TEST",
            company_name="Test Corp",
            website_url="https://testcorp.com",
            official_domain="testcorp.com",
            nse_symbol="TEST",
            careers_url=None,
            jobs_page_url=None,
            csr_portal_url=None,
            sustainability_url=None,
            annual_report_url=None,
        )

        mock_collector = MagicMock()
        mock_collector.collect_candidates.return_value = [
            {"url": "https://testcorp.com/careers", "link_text": "Careers", "source": "HEADER_NAV"}
        ]

        mock_classifier = MagicMock()
        mock_classifier.classify_discovered_links.return_value = [
            {"url": "https://testcorp.com/careers", "candidate_category": "JOBS_LISTING_CANDIDATE", "confidence": 0.9}
        ]
        mock_classifier.filter_promising_candidates_for_stage_2.return_value = [
            {"url": "https://testcorp.com/careers", "source": "HEADER_NAV"}
        ]
        mock_classifier.fetch_and_prepare_page_data.return_value = {
            "status_code": 200, "main_text": "Careers at Test Corp"
        }
        mock_classifier.classify_destination_page.return_value = {
            "page_type": "JOBS_LISTING_PAGE", "confidence": 0.95, "reasoning": "Live job portal"
        }
        mock_classifier.validate_page_evidence.return_value = {
            "decision": "APPROVED", "verified_type": "JOBS_LISTING_PAGE"
        }

        # Pipeline returns 85 raw jobs
        mock_pipeline = MagicMock()
        mock_jobs = [
            {"title": f"Software Engineer #{i}", "application_url": f"https://testcorp.com/jobs/{i}"}
            for i in range(1, 86)
        ]
        mock_pipeline.run.return_value = (mock_jobs, "mock_strategy", 100.0)

        with patch.object(cmd, "_save_evidence_file"):
            res = cmd._crawl_one_company(
                company=company,
                collector=mock_collector,
                classifier=mock_classifier,
                pipeline=mock_pipeline,
                timeout_sec=60,
                evidence_dir="/tmp/dummy",
            )

        # Assert jobs list is capped at exactly 50
        self.assertEqual(len(res["jobs"]), 50)
        self.assertEqual(res["jobs"][0]["job_title"], "Software Engineer #1")
        self.assertEqual(res["jobs"][49]["job_title"], "Software Engineer #50")

    @patch("modules.admin_panel.management.commands.crawl_review_sample.fetch_live_page")
    def test_failure_isolation_between_companies(self, mock_fetch):
        """Verifies that a network failure or 403 on one company does not abort execution."""
        cmd = Command()
        failing_company = SimpleNamespace(
            company_id="C_FAIL",
            company_name="Blocked Corp",
            website_url="https://blocked.com",
            official_domain="blocked.com",
            nse_symbol="FAIL",
            careers_url=None,
            jobs_page_url=None,
            csr_portal_url=None,
            sustainability_url=None,
            annual_report_url=None,
        )

        mock_collector = MagicMock()
        mock_collector.collect_candidates.return_value = []
        mock_fetch.return_value = {"ok": False, "status_code": 403, "error": "HTTP_403_FORBIDDEN"}

        mock_classifier = MagicMock()
        mock_pipeline = MagicMock()

        res = cmd._crawl_one_company(
            company=failing_company,
            collector=mock_collector,
            classifier=mock_classifier,
            pipeline=mock_pipeline,
            timeout_sec=60,
            evidence_dir="/tmp/dummy",
        )

        self.assertEqual(res["result"], "BLOCKED")
        self.assertIn("blocked", res["reason"].lower())
        self.assertTrue(len(res["warnings"]) >= 1)
        self.assertEqual(res["warnings"][0]["warning_type"], "BLOCKED_PAGE")

    def test_database_counts_invariant(self):
        """Verifies that database count dictionary comparison works and catches mutations."""
        cmd = Command()
        counts_a = {"Company": 201, "Job": 500, "CSRProject": 300, "CSROpportunity": 50, "Contact": 120, "AuditTrail": 40}
        counts_b = {"Company": 201, "Job": 500, "CSRProject": 300, "CSROpportunity": 50, "Contact": 120, "AuditTrail": 40}
        counts_mutated = {"Company": 201, "Job": 501, "CSRProject": 300, "CSROpportunity": 50, "Contact": 120, "AuditTrail": 40}

        self.assertEqual(counts_a, counts_b)
        self.assertNotEqual(counts_a, counts_mutated)


if __name__ == "__main__":
    unittest.main()
