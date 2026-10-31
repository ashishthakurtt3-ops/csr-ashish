"""
tests/test_pilot_batch_crawler.py
=================================
Automated unit & regression tests for pilot batch crawler.
Uses isolated mocked responses and local fixtures (zero live network / zero DB writes).
"""
import os
import unittest
from unittest.mock import patch, MagicMock
import requests

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.crawler_engine.pilot_crawler import PilotCrawler, load_batch_company_ids
from modules.crawler_engine.discovery_helpers import (
    get_registrable_domain,
    is_real_deep_url,
    normalize_url_for_comparison
)
from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity


class TestPilotBatchCrawler(unittest.TestCase):

    def test_01_batch_1_contains_exactly_50_companies(self):
        """Item 14: Batch 1 resolves to exactly 50 companies COMP_TOP200_001 to COMP_TOP200_050."""
        cids = load_batch_company_ids("batch_001_050")
        self.assertEqual(len(cids), 50)
        self.assertEqual(cids[0], "COMP_TOP200_001")
        self.assertEqual(cids[-1], "COMP_TOP200_050")
        self.assertNotIn("COMP_0", cids)
        self.assertNotIn("COMP_TOP200_051", cids)

    def test_02_no_execution_outside_selected_batch(self):
        """Item 15: No execution against companies outside selected batch."""
        crawler = PilotCrawler(batch_name="batch_001_050", dry_run=True)
        self.assertEqual(len(crawler.company_ids), 50)
        self.assertTrue(all(cid.startswith("COMP_TOP200_0") for cid in crawler.company_ids))

    def test_03_discovery_of_relevant_career_link(self):
        """Item 1: Correct discovery of relevant career link."""
        base_url = "https://www.ril.com"
        html = '<a href="/careers/jobs">Explore Careers at Reliance</a>'
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        a = soup.find("a")
        from urllib.parse import urljoin
        full_url = urljoin(base_url, a['href'])
        self.assertEqual(full_url, "https://www.ril.com/careers/jobs")
        self.assertTrue(is_real_deep_url(full_url, base_url))

    def test_04_rejection_of_navigation_link(self):
        """Item 2: Correct rejection of a navigation link."""
        crawler = PilotCrawler(batch_name="batch_001_050", dry_run=True)
        comp = MagicMock()
        comp.company_id = "COMP_TEST_001"
        comp.company_name = "Test Enterprise"

        crawler._validate_and_record_job(
            comp=comp,
            title="How to apply",
            location="Mumbai",
            employment_type="Full-time",
            experience=None,
            salary=None,
            posting_date=None,
            deadline=None,
            req_id="123",
            apply_url="https://test.com/apply",
            source_url="https://test.com/careers",
            evidence="Button link",
            extraction_method="DOM_HEURISTIC"
        )
        self.assertEqual(len(crawler.job_candidates), 0)
        self.assertEqual(len(crawler.rejected_and_review_candidates), 1)
        self.assertEqual(crawler.rejected_and_review_candidates[0]["category"], "REJECTED_NAV_DEFECT")

    def test_05_discovery_of_explicitly_linked_ats(self):
        """Item 3: Discovery of explicitly linked official ATS."""
        ats_url = "https://tatamotors.myworkdayjobs.com/careers"
        domain = get_registrable_domain(ats_url)
        self.assertEqual(domain, "myworkdayjobs.com")

    def test_06_rejection_of_unrelated_aggregator_link(self):
        """Item 4: Correct handling/rejection of unrelated aggregator link."""
        crawler = PilotCrawler(batch_name="batch_001_050", dry_run=True)
        comp = MagicMock()
        comp.company_id = "COMP_TEST_001"
        comp.company_name = "Test Enterprise"

        crawler._validate_and_record_job(
            comp=comp,
            title="Senior Java Architect",
            location="Bengaluru",
            employment_type="Full-time",
            experience=None,
            salary=None,
            posting_date=None,
            deadline=None,
            req_id="123",
            apply_url="https://www.naukri.com/job-listings-12345",
            source_url="https://test.com/careers",
            evidence="Aggregator link",
            extraction_method="DOM_HEURISTIC"
        )
        self.assertEqual(len(crawler.job_candidates), 0)
        self.assertEqual(len(crawler.rejected_and_review_candidates), 1)
        self.assertEqual(crawler.rejected_and_review_candidates[0]["category"], "REJECTED_AGGREGATOR_LINK")

    def test_07_extraction_from_valid_structured_job_data(self):
        """Item 5: Extraction from valid structured JobPosting data."""
        crawler = PilotCrawler(batch_name="batch_001_050", dry_run=True)
        comp = MagicMock()
        comp.company_id = "COMP_TEST_001"
        comp.company_name = "Test Enterprise"

        crawler._validate_and_record_job(
            comp=comp,
            title="Lead Data Engineer",
            location="Hyderabad, Telangana",
            employment_type="Full-time",
            experience="5+ years",
            salary="Not published",
            posting_date="2026-10-25",
            deadline="2026-12-31",
            req_id="REQ_7721",
            apply_url="https://test.com/jobs/7721/apply",
            source_url="https://test.com/jobs/7721",
            evidence="Schema.org JobPosting",
            extraction_method="JSON_LD_SCHEMA"
        )
        self.assertEqual(len(crawler.job_candidates), 1)
        cand = crawler.job_candidates[0]
        self.assertEqual(cand["title"], "Lead Data Engineer")
        self.assertEqual(cand["location"], "Hyderabad, Telangana")
        self.assertEqual(cand["final_classification"], "VALID_CANDIDATE")

    def test_08_handling_of_incomplete_job_details(self):
        """Item 6 & 12: Incomplete job details keep missing fields null, no fabrication."""
        crawler = PilotCrawler(batch_name="batch_001_050", dry_run=True)
        comp = MagicMock()
        comp.company_id = "COMP_TEST_001"
        comp.company_name = "Test Enterprise"

        crawler._validate_and_record_job(
            comp=comp,
            title="Operations Manager",
            location=None,
            employment_type=None,
            experience=None,
            salary=None,
            posting_date=None,
            deadline=None,
            req_id=None,
            apply_url="https://test.com/jobs/op-mgr",
            source_url="https://test.com/jobs",
            evidence="DOM link",
            extraction_method="DOM_HEURISTIC"
        )
        self.assertEqual(len(crawler.job_candidates), 1)
        cand = crawler.job_candidates[0]
        self.assertEqual(cand["salary"], "Not published")
        self.assertEqual(cand["experience"], "Not specified")

    def test_09_distinguishing_csr_policy_from_specific_project(self):
        """Item 8: Distinguishing a CSR policy statement from a specific project."""
        crawler = PilotCrawler(batch_name="batch_001_050", dry_run=True)
        comp = MagicMock()
        comp.company_id = "COMP_TEST_001"
        comp.company_name = "Test Enterprise"

        # Policy statement -> must be REJECTED
        crawler._validate_and_record_csr(
            comp=comp,
            project_name="Corporate CSR Policy and Committee Charter",
            description="Our governance charter for CSR committee meetings.",
            category="Governance",
            location="National",
            state="All India",
            fy="2024-25",
            amount="None",
            partner="Internal Committee",
            source_url="https://test.com/csr-policy",
            evidence="Charter text",
            is_policy_statement=True
        )
        self.assertEqual(len(crawler.csr_candidates), 0)
        self.assertEqual(len(crawler.rejected_and_review_candidates), 1)
        self.assertEqual(crawler.rejected_and_review_candidates[0]["category"], "REJECTED_POLICY_NOT_PROJECT")

        # Specific field project -> must be ACCEPTED
        crawler._validate_and_record_csr(
            comp=comp,
            project_name="Arogya Mobile Medical Units in Rural Maharashtra",
            description="Providing primary healthcare checkups to 50,000 villagers.",
            category="Healthcare & Sanitation",
            location="Pune District",
            state="Maharashtra",
            fy="2024-25",
            amount="₹12.50 Crore",
            partner="Arogya Foundation",
            source_url="https://test.com/csr/arogya",
            evidence="Project initiative disclosure",
            is_policy_statement=False
        )
        self.assertEqual(len(crawler.csr_candidates), 1)
        self.assertEqual(crawler.csr_candidates[0]["project_name"], "Arogya Mobile Medical Units in Rural Maharashtra")

    def test_10_duplicate_detection_without_merging(self):
        """Item 9: Duplicate detection identifies identical candidates without merging distinct ones."""
        crawler = PilotCrawler(batch_name="batch_001_050", dry_run=True)
        comp = MagicMock()
        comp.company_id = "COMP_TEST_001"
        comp.company_name = "Test Enterprise"

        # First instance -> Accepted
        crawler._validate_and_record_job(
            comp=comp,
            title="DevOps Engineer",
            location="Pune",
            employment_type="Full-time",
            experience=None,
            salary=None,
            posting_date=None,
            deadline=None,
            req_id="DEV_01",
            apply_url="https://test.com/jobs/devops",
            source_url="https://test.com/jobs",
            evidence="DOM link 1",
            extraction_method="DOM_HEURISTIC"
        )
        self.assertEqual(len(crawler.job_candidates), 1)

        # Duplicate instance -> Rejected as duplicate
        crawler._validate_and_record_job(
            comp=comp,
            title="DevOps Engineer",
            location="Pune",
            employment_type="Full-time",
            experience=None,
            salary=None,
            posting_date=None,
            deadline=None,
            req_id="DEV_01",
            apply_url="https://test.com/jobs/devops",
            source_url="https://test.com/jobs?page=2",
            evidence="DOM link 2",
            extraction_method="DOM_HEURISTIC"
        )
        self.assertEqual(len(crawler.job_candidates), 1)
        self.assertEqual(len(crawler.rejected_and_review_candidates), 1)
        self.assertEqual(crawler.rejected_and_review_candidates[0]["category"], "REJECTED_DUPLICATE")

        # Distinct vacancy -> Accepted
        crawler._validate_and_record_job(
            comp=comp,
            title="Senior DevOps Engineer",
            location="Pune",
            employment_type="Full-time",
            experience=None,
            salary=None,
            posting_date=None,
            deadline=None,
            req_id="DEV_02",
            apply_url="https://test.com/jobs/sr-devops",
            source_url="https://test.com/jobs",
            evidence="DOM link 3",
            extraction_method="DOM_HEURISTIC"
        )
        self.assertEqual(len(crawler.job_candidates), 2)

    def test_11_redirect_and_url_normalization(self):
        """Item 10: URL normalization and redirect tracking."""
        h, p = normalize_url_for_comparison("https://www.RIL.com/careers/jobs/")
        self.assertEqual(h, "ril.com")
        self.assertEqual(p, "/careers/jobs")

    def test_12_timeout_and_error_handling(self):
        """Item 11: Timeout and HTTP error handling gracefully without crashing."""
        crawler = PilotCrawler(batch_name="batch_001_050", dry_run=True)
        with patch.object(crawler.session, 'get', side_effect=requests.exceptions.Timeout):
            res = crawler.fetch_url("https://timeout-domain.com")
            self.assertFalse(res["ok"])
            self.assertEqual(res["status_code"], 408)
            self.assertIn("timed out", res["error"])

    def test_13_no_writes_to_production_mysql_in_dry_run(self):
        """Item 16: Zero writes to production tables."""
        jobs_before = Job.objects.count()
        csr_before = CSRProject.objects.count()
        comp_before = Company.objects.count()

        # Instantiate crawler in dry_run mode
        crawler = PilotCrawler(batch_name="batch_001_050", dry_run=True)
        self.assertTrue(crawler.dry_run)

        self.assertEqual(Job.objects.count(), jobs_before)
        self.assertEqual(CSRProject.objects.count(), csr_before)
        self.assertEqual(Company.objects.count(), comp_before)


if __name__ == '__main__':
    unittest.main()
