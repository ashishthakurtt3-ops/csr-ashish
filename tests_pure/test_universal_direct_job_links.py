"""
tests_pure/test_universal_direct_job_links.py
=============================================
Comprehensive Unit Tests for Universal Direct Job Link Resolution & Anti-Redirect Trap Engine.
Guarantees that across ANY arbitrary company:
1. Job vacancies link strictly to authentic, specific postings (never generic career homepages).
2. Generic landing pages across custom CMS, Workday, Oracle CX, Taleo, Greenhouse, Lever, etc. are flagged.
3. Redirect-to-homepage / landing traps are caught and rejected.
4. Schema.org JSON-LD and DOM card extractions never substitute landing pages.
"""
import os
import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.crawler_engine.normalizers import is_generic_landing_url
from modules.crawler_engine.adapters.generic_jsonld import GenericStructuredJobAdapter
from modules.crawler_engine.crawler import (
    find_hop2_ats_links,
    detect_repeating_dom_job_cards,
    try_dispatch_specialized_ats
)
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from bs4 import BeautifulSoup


class FakeCompany:
    def __init__(self, name="Acme Corp", domain="acme.com", website="https://www.acme.com"):
        self.company_id = "comp_test_acme"
        self.company_name = name
        self.official_domain = domain
        self.website_url = website
        self.careers_url = f"{website}/careers"


class TestUniversalDirectJobLinks(unittest.TestCase):

    def test_01_generic_landing_url_detection(self):
        """Verify that generic catalog/search/landing pages are recognized across arbitrary domains."""
        generic_urls = [
            "https://www.randomcompany.com/",
            "https://www.randomcompany.com/en/",
            "https://www.randomcompany.com/en-us",
            "https://www.randomcompany.com/careers",
            "https://www.randomcompany.com/careers/",
            "https://www.randomcompany.com/en/careers",
            "https://www.randomcompany.com/careers.html",
            "https://www.randomcompany.com/careers/index.html",
            "https://www.randomcompany.com/careers/all-jobs",
            "https://www.randomcompany.com/careers/search",
            "https://www.randomcompany.com/careers/job-search",
            "https://www.randomcompany.com/careers/open-positions",
            "https://www.randomcompany.com/jobs",
            "https://www.randomcompany.com/jobs/",
            "https://www.randomcompany.com/jobs/search",
            "https://www.randomcompany.com/jobs/search-results",
            "https://jobs.randomcompany.com/",
            "https://jobs.ciklum.com/",
            "https://explore-jobs.ciklum.com/en/sites/ciklum-career",
            "https://explore-jobs.ciklum.com/en/sites/ciklum-career/jobs",
            "https://acme.wd3.myworkdayjobs.com/en-US/Careers",
            "https://acme.wd3.myworkdayjobs.com/en-US/Careers/",
            "https://acme.taleo.net/careersection/2/jobsearch.ftl",
            "https://jobs.acme.com/search/",
            "https://jobs.acme.com/go/All-Jobs/",
            "https://www.randomcompany.com/join-our-team",
            "https://www.randomcompany.com/work-with-us",
            "https://www.randomcompany.com/about/careers",
        ]
        for u in generic_urls:
            self.assertTrue(
                is_generic_landing_url(u),
                f"Expected is_generic_landing_url=True for generic portal: {u}"
            )

    def test_02_authentic_direct_job_url_acceptance(self):
        """Verify that authentic, direct job vacancy URLs are NOT classified as generic landing pages."""
        direct_urls = [
            "https://explore-jobs.ciklum.com/en/sites/ciklum-career/job/3528",
            "https://acme.wd3.myworkdayjobs.com/en-US/Careers/job/Bangalore/Senior-Software-Engineer_R-10092",
            "https://boards.greenhouse.io/acme/jobs/4092837",
            "https://jobs.lever.co/acme/11223344-5566-7788-99aa-bbccddeeff00",
            "https://jobs.smartrecruiters.com/AcmeCorp/743999981234567-lead-architect",
            "https://www.accenture.com/in-en/careers/jobdetails?id=12345",
            "https://acme.taleo.net/careersection/acme_career/jobapply.ftl?lang=en&job=250008N7&src=NGP-10061",
            "https://acme.darwinbox.in/ms/candidate/careers/positions/12345",
            "https://jobs.ashbyhq.com/acme/88776655-4433-2211-00ff-eeddccbbaa99",
            "https://www.randomcompany.com/careers/job/senior-software-engineer-10293",
            "https://www.randomcompany.com/careers/position/sr-developer-992",
            "https://www.randomcompany.com/careers?job_id=456",
            "https://www.randomcompany.com/careers?id=REQ12345",
            "https://careers.ril.com/jobdesc.aspx?job_id=12345",
        ]
        for u in direct_urls:
            self.assertFalse(
                is_generic_landing_url(u),
                f"Expected is_generic_landing_url=False for direct vacancy: {u}"
            )

    @patch.object(BatchDiscoveryService, "_record_dropped_candidate")
    def test_03_validate_job_rejects_landing_page(self, mock_record):
        """Validate that validate_job strictly rejects candidates pointing to careers landing pages."""
        company = FakeCompany()
        seen_urls = set()

        cand_landing = {
            "job_title": "Software Engineer",
            "application_url": "https://www.acme.com/careers",
            "confidence": 0.95
        }
        ok, reason, _ = BatchDiscoveryService.validate_job(cand_landing, company, seen_urls)
        self.assertFalse(ok)
        self.assertIn("LANDING_PAGE_NOT_JOB", reason)

        cand_workday_landing = {
            "job_title": "Product Designer",
            "application_url": "https://acme.wd3.myworkdayjobs.com/en-US/Careers",
            "confidence": 0.95
        }
        ok, reason, _ = BatchDiscoveryService.validate_job(cand_workday_landing, company, seen_urls)
        self.assertFalse(ok)
        self.assertIn("LANDING_PAGE_NOT_JOB", reason)

    @patch.object(BatchDiscoveryService, "_record_dropped_candidate")
    def test_04_validate_job_detects_redirect_to_landing_page_trap(self, mock_record):
        """Validate that when a candidate URL HTTP 301/302 redirects to a careers homepage, it is rejected."""
        company = FakeCompany()
        seen_urls = set()

        cand_redirecting = {
            "job_title": "Cloud Architect",
            "application_url": "https://www.acme.com/jobs/old-slug-123",
            "confidence": 0.85
        }

        # Mock HEAD request simulating redirect to https://www.acme.com/careers
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = "https://www.acme.com/careers"

        with patch("modules.admin_panel.services.batch_discovery_service.cffi_requests.head", return_value=mock_resp):
            ok, reason, _ = BatchDiscoveryService.validate_job(cand_redirecting, company, seen_urls)
            self.assertFalse(ok)
            self.assertIn("REDIRECTED_TO_LANDING_PAGE", reason)

    def test_05_validate_job_accepts_direct_vacancy_and_updates_destination(self):
        """Validate that direct vacancies pass and if redirected to an authentic post, final URL is saved."""
        company = FakeCompany()
        seen_urls = set()

        cand_direct = {
            "job_title": "Full Stack Engineer",
            "application_url": "https://acme.wd3.myworkdayjobs.com/en-US/Careers/job/Bangalore/Full-Stack-Engineer_R-2001",
            "confidence": 0.98,
            "ats_platform": "Workday",
            "extraction_method": "ats_api"
        }
        ok, reason, validated = BatchDiscoveryService.validate_job(cand_direct, company, seen_urls)
        self.assertTrue(ok)
        self.assertEqual(validated["application_url"], cand_direct["application_url"])

    def test_06_schema_org_jsonld_adapter_resolves_relative_and_drops_landing_fallback(self):
        """Validate Schema.org adapter resolves relative URLs and never falls back to landing page."""
        adapter = GenericStructuredJobAdapter()
        content = """
        <html>
            <head>
                <script type="application/ld+json">
                [
                    {
                        "@type": "JobPosting",
                        "title": "Backend Go Developer",
                        "url": "/jobs/detail/backend-go-102",
                        "jobLocation": {"address": {"addressLocality": "Bengaluru"}}
                    },
                    {
                        "@type": "JobPosting",
                        "title": "Missing Link Job",
                        "url": "/careers",
                        "jobLocation": {"address": {"addressLocality": "Pune"}}
                    }
                ]
                </script>
            </head>
        </html>
        """
        records = adapter.extract_jobs("comp_test", "https://www.acme.com/careers", content)
        # First record should have resolved URL: https://www.acme.com/jobs/detail/backend-go-102
        self.assertEqual(len(records), 2)
        rec1 = records[0]
        self.assertEqual(rec1.job_title, "Backend Go Developer")
        self.assertEqual(rec1.application_url, "https://www.acme.com/jobs/detail/backend-go-102")

        # Second record had url="/careers" which is a landing page -> detail_url must be cleared ("")
        rec2 = records[1]
        self.assertEqual(rec2.job_title, "Missing Link Job")
        self.assertEqual(rec2.application_url, "")

    def test_07_find_hop2_ats_links(self):
        """Validate that outbound ATS links on arbitrary company pages are discovered."""
        html = """
        <html>
            <body>
                <header><a href="/about">About</a></header>
                <div class="career-hero">
                    <h1>Join Acme Corp</h1>
                    <a href="https://boards.greenhouse.io/acmecorp">View Open Roles</a>
                    <a href="https://jobs.lever.co/acmecorp">Explore Lever Openings</a>
                </div>
            </body>
        </html>
        """
        soup = BeautifulSoup(html, "html.parser")
        candidates = find_hop2_ats_links(soup, "https://www.acmecorp.com/careers")
        urls = [c[1] for c in candidates]
        self.assertIn("https://boards.greenhouse.io/acmecorp", urls)
        self.assertIn("https://jobs.lever.co/acmecorp", urls)

    def test_08_repeating_dom_job_cards_rejects_landing_page_links(self):
        """Validate that DOM repeating card detector skips cards whose links point back to /careers or /."""
        html = """
        <div class="job-listings">
            <div class="job-card">
                <h3>Senior Java Developer</h3>
                <a href="/careers">Apply Now</a>
            </div>
            <div class="job-card">
                <h3>Lead Python Engineer</h3>
                <a href="/careers/">Apply Now</a>
            </div>
            <div class="job-card">
                <h3>Frontend React Architect</h3>
                <a href="/">Apply Now</a>
            </div>
        </div>
        """
        soup = BeautifulSoup(html, "html.parser")
        cards = detect_repeating_dom_job_cards(soup, "https://www.acme.com/careers")
        # Since all links point to landing pages (/careers, /), 0 valid job cards should be emitted
        self.assertEqual(len(cards), 0)


if __name__ == "__main__":
    unittest.main()
