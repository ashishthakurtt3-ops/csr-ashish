import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import unittest
from unittest.mock import MagicMock, patch
from modules.crawler_engine.pilot_crawler import PilotCrawler
from modules.admin_panel.models import Company, Job, CSRProject


class TestCrawlerEndToEndBridge(unittest.TestCase):

    def setUp(self):
        self.crawler = PilotCrawler(batch_name="batch_001_050", dry_run=True)
        self.comp = Company(
            company_id="COMP_MOCK_001",
            company_name="Acme Technology Ltd",
            website_url="https://acme-mock.com"
        )

    def test_01_workday_url_invokes_workday_adapter(self):
        """Verifies that discovered Workday URL routes through WorkdayAdapter."""
        workday_html = '''
        <html>
            <head><title>Acme Careers</title></head>
            <body>
                <div data-automation-id="jobCard">
                    <a data-automation-id="jobTitle" href="/job/R992">Staff Cloud Platform Engineer</a>
                    <span data-automation-id="locations">Bengaluru, Karnataka, India</span>
                </div>
            </body>
        </html>
        '''
        crawl_summary = {"pages_inspected": 0, "careers_ats_result": "", "relevant_pages_discovered": 0}
        with patch.object(self.crawler, 'fetch_url', return_value={
            "ok": True,
            "status_code": 200,
            "html": workday_html,
            "final_url": "https://acme.myworkdayjobs.com/Careers"
        }):
            self.crawler._inspect_and_extract_careers(self.comp, "https://acme.myworkdayjobs.com/Careers", crawl_summary)
            
        self.assertEqual(len(self.crawler.job_candidates), 1)
        job = self.crawler.job_candidates[0]
        self.assertEqual(job["title"], "Staff Cloud Platform Engineer")
        self.assertEqual(job["location"], "Bengaluru, Karnataka, India")
        self.assertEqual(job["extraction_method"], "ATS_ADAPTER_WORKDAY")
        self.assertEqual(job["staging_action"], "STAGED_ONLY")

    def test_02_darwinbox_url_invokes_darwinbox_adapter(self):
        """Verifies that discovered Darwinbox URL routes through DarwinboxAdapter."""
        darwinbox_html = '''
        <html>
            <head><title>Acme Careers</title></head>
            <body>
                <div class="job-card">
                    <h3 class="job-title"><a href="/job/D100">DevOps Engineer</a></h3>
                    <span class="location">Mumbai</span>
                </div>
            </body>
        </html>
        '''
        crawl_summary = {"pages_inspected": 0, "careers_ats_result": "", "relevant_pages_discovered": 0}
        with patch.object(self.crawler, 'fetch_url', return_value={
            "ok": True,
            "status_code": 200,
            "html": darwinbox_html,
            "final_url": "https://acme.darwinbox.in/ms/candidate/careers"
        }):
            self.crawler._inspect_and_extract_careers(self.comp, "https://acme.darwinbox.in/ms/candidate/careers", crawl_summary)
            
        self.assertEqual(len(self.crawler.job_candidates), 1)
        job = self.crawler.job_candidates[0]
        self.assertEqual(job["title"], "DevOps Engineer")
        self.assertEqual(job["location"], "Mumbai")
        self.assertEqual(job["extraction_method"], "ATS_ADAPTER_DARWINBOX")

    def test_03_invalid_nav_heading_cannot_be_published(self):
        """Verifies that generic navigation headings are rejected by IndependentEvidenceVerifier."""
        crawl_summary = {"pages_inspected": 0, "careers_ats_result": "", "relevant_pages_discovered": 0}
        with patch.object(self.crawler, 'fetch_url', return_value={
            "ok": True,
            "status_code": 200,
            "html": '<html><body><a href="/jobs/search">careers</a></body></html>',
            "final_url": "https://acme-mock.com/careers"
        }):
            self.crawler._inspect_and_extract_careers(self.comp, "https://acme-mock.com/careers", crawl_summary)
            
        self.assertEqual(len(self.crawler.job_candidates), 0)
        self.assertTrue(any("NAV_DEFECT" in r["category"] for r in self.crawler.rejected_and_review_candidates))

    def test_04_dry_run_strictly_zero_database_mutations(self):
        """Verifies that running crawler with dry_run=True mutates exactly 0 rows in MySQL."""
        init_jobs = Job.objects.count()
        init_csr = CSRProject.objects.count()
        
        # Simulate extracted candidate
        self.crawler._validate_and_record_job(
            comp=self.comp,
            title="Principal Security Engineer",
            location="Bengaluru",
            employment_type="Full-time",
            experience="10+ yrs",
            salary="INR 45L",
            posting_date="2026-10-30",
            deadline="2026-12-31",
            req_id="REQ_SEC_01",
            apply_url="https://acme-mock.com/jobs/sec01/apply",
            source_url="https://acme-mock.com/jobs/sec01",
            evidence="Hiring Principal Security Engineer for Bengaluru office",
            extraction_method="ATS_ADAPTER_TEST"
        )
        self.assertEqual(len(self.crawler.job_candidates), 1)
        self.assertEqual(self.crawler.job_candidates[0]["staging_action"], "STAGED_ONLY")
        self.assertEqual(Job.objects.count(), init_jobs)
        self.assertEqual(CSRProject.objects.count(), init_csr)


if __name__ == '__main__':
    unittest.main()
