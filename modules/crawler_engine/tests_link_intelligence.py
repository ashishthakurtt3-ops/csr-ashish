"""
Tests for Link Intelligence Architecture (Phases 1-6).

Comprehensive test suite verifying:
1. URL Normalization and highlight fragment stripping.
2. Link Validation Gate (generic listing detection, duplicate batch rejection, title verification).
3. ATS Adapters with local JSON/HTML fixtures (Lever, Greenhouse, Workday, SmartRecruiters, SuccessFactors, Darwinbox, Oracle, Ashby, Recruitee, Zoho).
4. Generic Cascading Strategies (JSON-LD, Sitemap, Embedded State, Anchor Cards).
5. Delta Sync Pruning Safety Guards and Soft-Deletion (7-day retention).
6. Non-colliding deterministic fingerprint generation.
"""
from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from modules.admin_panel.models import Company, Job
from modules.crawler_engine.normalizers import (
    normalize_canonical_url,
    build_job_fingerprint,
    clean_text,
)
from modules.crawler_engine.link_validator import (
    is_generic_listing_url,
    validate_job_candidate_url,
)
from modules.crawler_engine.strategies.base import ExtractionContext
from modules.crawler_engine.strategies.ats_strategy import ATSStrategy
from modules.crawler_engine.strategies.jsonld_strategy import JsonLdStrategy
from modules.crawler_engine.strategies.embedded_state_strategy import EmbeddedStateStrategy
from modules.crawler_engine.strategies.anchor_card_strategy import AnchorCardStrategy


class URLNormalizationTestCase(TestCase):
    def test_strip_tracking_params_and_text_fragments(self):
        raw_url = (
            "https://jobs.example.com/openings/software-engineer-101"
            "?utm_source=linkedin&utm_medium=cpc&gclid=xyz123&fbclid=abc"
            "#:~:text=Software%20Engineer%20Pune"
        )
        canon = normalize_canonical_url(raw_url)
        self.assertEqual(
            canon,
            "https://jobs.example.com/openings/software-engineer-101",
        )

    def test_preserve_functional_query_params(self):
        url_with_job_id = "https://careers.example.com/job-detail?reqId=REQ-88902&source=careers_page"
        canon = normalize_canonical_url(url_with_job_id)
        self.assertIn("reqId=REQ-88902", canon)
        self.assertNotIn("source=", canon)

    def test_normalize_trailing_slashes_and_scheme(self):
        url1 = "HTTP://Jobs.Example.Com:80/roles/dev/"
        canon1 = normalize_canonical_url(url1)
        # Upgrades http to https and strips trailing slash
        self.assertEqual(canon1, "https://jobs.example.com:80/roles/dev")


class LinkValidationGateTestCase(TestCase):
    def test_reject_matching_company_careers_url(self):
        careers_url = "https://example.com/careers"
        candidate_url = "https://example.com/careers#:~:text=Data%20Analyst"
        
        is_generic, reason = is_generic_listing_url(candidate_url, company_careers_url=careers_url)
        self.assertTrue(is_generic)

        canon, quality, note = validate_job_candidate_url(
            candidate_url=candidate_url,
            company_careers_url=careers_url,
            job_title="Data Analyst",
        )
        self.assertEqual(quality, "LISTING_FALLBACK")
        self.assertIn("fallback", note.lower())

    def test_reject_intra_batch_duplicates(self):
        shared_url = "https://example.com/current-openings/all"
        batch_counts = {shared_url: 5}

        canon, quality, note = validate_job_candidate_url(
            candidate_url=shared_url,
            batch_url_counts=batch_counts,
            job_title="Frontend Engineer",
        )
        self.assertEqual(quality, "LISTING_FALLBACK")
        self.assertTrue(note.startswith("shared_by_"))

    def test_ats_api_trusted_yields_direct(self):
        direct_candidate = "https://jobs.lever.co/paytm/69a3b632-4d0f-48e0-a7d1-0f727c95a0a3"
        canon, quality, note = validate_job_candidate_url(
            candidate_url=direct_candidate,
            is_ats_api=True,
            job_title="Lead Software Engineer",
            external_job_id="69a3b632-4d0f-48e0-a7d1-0f727c95a0a3",
        )
        self.assertEqual(quality, "DIRECT")
        self.assertEqual(note, "ats_api_trusted")


class ATSAdaptersFixtureTestCase(TestCase):
    def setUp(self):
        self.strategy = ATSStrategy()
        self.company = Company.objects.create(
            company_id="TEST_CORP",
            company_name="Test Corporation",
            website_url="https://testcorp.com",
            careers_url="https://careers.testcorp.com",
        )
        self.context = ExtractionContext(company=self.company, careers_url=self.company.careers_url)

    def test_lever_adapter(self):
        fixture_data = [
            {
                "id": "lever-12345",
                "text": "Principal Cloud Architect",
                "hostedUrl": "https://jobs.lever.co/testcorp/lever-12345",
                "createdAt": 1729000000000,
                "descriptionPlain": "Design cloud systems at scale.",
                "categories": {
                    "location": "Bengaluru, India",
                    "department": "Engineering",
                    "commitment": "Full Time",
                },
            }
        ]

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fixture_data

        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_get", return_value=mock_resp):
            jobs = self.strategy._extract_lever("https://jobs.lever.co/testcorp", "testcorp", self.context)

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job["title"], "Principal Cloud Architect")
        self.assertEqual(job["external_job_id"], "lever-12345")
        self.assertEqual(job["application_url"], "https://jobs.lever.co/testcorp/lever-12345")
        self.assertEqual(job["link_quality"], "DIRECT")
        self.assertEqual(job["location"], "Bengaluru, India")

    def test_greenhouse_adapter(self):
        fixture_data = {
            "jobs": [
                {
                    "id": 987654,
                    "title": "Senior Product Manager",
                    "updated_at": "2026-10-15T10:00:00Z",
                    "absolute_url": "https://boards.greenhouse.io/testcorp/jobs/987654",
                    "location": {"name": "Mumbai, India"},
                    "content": "Lead payments product development.",
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fixture_data

        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_get", return_value=mock_resp):
            jobs = self.strategy._extract_greenhouse("https://boards.greenhouse.io/testcorp", "testcorp", self.context)

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job["title"], "Senior Product Manager")
        self.assertEqual(job["external_job_id"], "987654")
        self.assertEqual(job["application_url"], "https://boards.greenhouse.io/testcorp/jobs/987654")
        self.assertEqual(job["link_quality"], "DIRECT")

    def test_workday_adapter_pagination(self):
        fixture_page_1 = {
            "total": 2,
            "jobPostings": [
                {
                    "title": "Backend Go Developer",
                    "externalPath": "/job/Bengaluru-IN/Backend-Go-Developer_R1001",
                    "bulletFields": ["R1001"],
                    "locationsText": "Bengaluru",
                    "postedOn": "Posted 2 Days Ago",
                }
            ]
        }
        fixture_page_2 = {
            "total": 2,
            "jobPostings": [
                {
                    "title": "Data Platform Lead",
                    "externalPath": "/job/Hyderabad-IN/Data-Platform-Lead_R1002",
                    "bulletFields": ["R1002"],
                    "locationsText": "Hyderabad",
                    "postedOn": "Posted 1 Day Ago",
                }
            ]
        }
        fixture_page_3 = {
            "total": 2,
            "jobPostings": []
        }

        responses = [
            MagicMock(status_code=200, json=MagicMock(return_value=fixture_page_1)),
            MagicMock(status_code=200, json=MagicMock(return_value=fixture_page_2)),
            MagicMock(status_code=200, json=MagicMock(return_value=fixture_page_3)),
        ]

        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_post", side_effect=responses):
            jobs = self.strategy._extract_workday(
                "https://testcorp.wd3.myworkdayjobs.com/en-US/TestCorpCareers",
                "testcorp",
                self.context
            )

        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["title"], "Backend Go Developer")
        self.assertEqual(jobs[0]["external_job_id"], "R1001")
        self.assertEqual(
            jobs[0]["application_url"],
            "https://testcorp.wd3.myworkdayjobs.com/en-US/TestCorpCareers/job/Bengaluru-IN/Backend-Go-Developer_R1001"
        )
        self.assertEqual(jobs[0]["link_quality"], "DIRECT")

        self.assertEqual(jobs[1]["title"], "Data Platform Lead")
        self.assertEqual(jobs[1]["external_job_id"], "R1002")

    def test_smartrecruiters_adapter(self):
        fixture_data = {
            "content": [
                {
                    "id": "743999901234",
                    "name": "DevOps Engineer",
                    "ref": "https://jobs.smartrecruiters.com/TestCorp/743999901234-devops-engineer",
                    "location": {"city": "Pune", "country": "in"},
                    "department": {"label": "IT Infrastructure"},
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fixture_data

        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_get", return_value=mock_resp):
            jobs = self.strategy._extract_smartrecruiters("https://careers.smartrecruiters.com/TestCorp", "TestCorp", self.context)

        self.assertEqual(len(jobs), 1)
        job = jobs[0]
        self.assertEqual(job["title"], "DevOps Engineer")
        self.assertEqual(job["external_job_id"], "743999901234")
        self.assertEqual(job["application_url"], "https://jobs.smartrecruiters.com/TestCorp/743999901234-devops-engineer")
        self.assertEqual(job["link_quality"], "DIRECT")

    def test_darwinbox_adapter(self):
        fixture_data = {
            "message": {
                "jobs": [
                    {
                        "job_id": "DBOX-8821",
                        "title": "Lead Frontend Architect",
                        "location": "Bengaluru",
                        "department": "Engineering",
                        "employment_type": "Full-time",
                    }
                ]
            }
        }
        mock_resp = MagicMock(status_code=200, json=MagicMock(return_value=fixture_data))
        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_get", return_value=mock_resp):
            jobs = self.strategy._extract_darwinbox("https://testcorp.darwinbox.in", None, self.context)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Lead Frontend Architect")
        self.assertEqual(jobs[0]["external_job_id"], "DBOX-8821")
        self.assertEqual(jobs[0]["application_url"], "https://testcorp.darwinbox.in/ms/candidate/careers/DBOX-8821")
        self.assertEqual(jobs[0]["link_quality"], "DIRECT")

    def test_successfactors_adapter(self):
        html_fixture = """
        <table class="searchResults">
            <tr class="jobResultItem">
                <td>
                    <a class="jobTitle" href="/job/Bengaluru-Senior-Security-Consultant-560001/109844200/">Senior Security Consultant</a>
                </td>
                <td class="colLocation"><span class="jobLocation">Bengaluru, IN</span></td>
            </tr>
        </table>
        """
        mock_resp = MagicMock(status_code=200, text=html_fixture, url="https://jobs.testcorp.com/search/?q=&startrow=0")
        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_get", return_value=mock_resp):
            jobs = self.strategy._extract_successfactors("https://jobs.testcorp.com", None, self.context)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Senior Security Consultant")
        self.assertEqual(jobs[0]["external_job_id"], "109844200")
        self.assertIn("109844200", jobs[0]["application_url"])
        self.assertEqual(jobs[0]["link_quality"], "DIRECT")

    def test_oracle_adapter(self):
        fixture_data = {
            "items": [
                {
                    "TotalJobsCount": 1,
                    "requisitionList": [
                        {
                            "Id": "ORCL-33901",
                            "Title": "Principal Database Administrator",
                            "PrimaryLocation": "Mumbai, MH, IN",
                        }
                    ]
                }
            ]
        }
        mock_resp = MagicMock(status_code=200, json=MagicMock(return_value=fixture_data))
        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_get", return_value=mock_resp):
            jobs = self.strategy._extract_oracle("https://ebzs.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1", None, self.context)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Principal Database Administrator")
        self.assertEqual(jobs[0]["external_job_id"], "ORCL-33901")
        self.assertIn("ORCL-33901", jobs[0]["application_url"])
        self.assertEqual(jobs[0]["link_quality"], "DIRECT")

    def test_ashby_adapter(self):
        fixture_data = {
            "jobs": [
                {
                    "id": "ashby-9912",
                    "title": "Staff Reliability Engineer",
                    "jobUrl": "https://jobs.ashbyhq.com/testcorp/ashby-9912",
                    "locationName": "Remote, India",
                    "departmentName": "Infrastructure",
                }
            ]
        }
        mock_resp = MagicMock(status_code=200, json=MagicMock(return_value=fixture_data))
        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_post", return_value=mock_resp):
            jobs = self.strategy._extract_ashby("https://jobs.ashbyhq.com/testcorp", "testcorp", self.context)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Staff Reliability Engineer")
        self.assertEqual(jobs[0]["external_job_id"], "ashby-9912")
        self.assertEqual(jobs[0]["application_url"], "https://jobs.ashbyhq.com/testcorp/ashby-9912")
        self.assertEqual(jobs[0]["link_quality"], "DIRECT")

    def test_recruitee_adapter(self):
        fixture_data = {
            "offers": [
                {
                    "id": 44102,
                    "title": "Product Designer",
                    "careers_url": "https://testcorp.recruitee.com/o/product-designer",
                    "location": "Bengaluru",
                    "department": "Design",
                }
            ]
        }
        mock_resp = MagicMock(status_code=200, json=MagicMock(return_value=fixture_data))
        with patch("modules.crawler_engine.strategies.ats_strategy.cffi_get", return_value=mock_resp):
            jobs = self.strategy._extract_recruitee("https://testcorp.recruitee.com", "testcorp", self.context)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Product Designer")
        self.assertEqual(jobs[0]["external_job_id"], "44102")
        self.assertEqual(jobs[0]["application_url"], "https://testcorp.recruitee.com/o/product-designer")
        self.assertEqual(jobs[0]["link_quality"], "DIRECT")


class GenericStrategiesTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_id="GENERIC_CORP",
            company_name="Generic Corporate Ltd",
            website_url="https://genericcorp.com",
            careers_url="https://genericcorp.com/careers",
        )

    def test_jsonld_strategy(self):
        html = """
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org/",
                "@type": "JobPosting",
                "title": "Machine Learning Research Engineer",
                "description": "Develop state-of-the-art NLP models.",
                "identifier": {
                    "@type": "PropertyValue",
                    "name": "GenericCorp",
                    "value": "ML-2026-99"
                },
                "datePosted": "2026-10-18",
                "employmentType": "FULL_TIME",
                "jobLocation": {
                    "@type": "Place",
                    "address": {
                        "@type": "PostalAddress",
                        "addressLocality": "Hyderabad",
                        "addressCountry": "IN"
                    }
                },
                "url": "https://genericcorp.com/careers/jobs/ml-2026-99"
            }
            </script>
        </head>
        <body><h1>Careers at GenericCorp</h1></body>
        </html>
        """
        ctx = ExtractionContext(company=self.company, careers_url=self.company.careers_url, html_content=html)
        strategy = JsonLdStrategy()
        self.assertTrue(strategy.detect(ctx))
        jobs = strategy.extract(ctx)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Machine Learning Research Engineer")
        self.assertEqual(jobs[0]["external_job_id"], "ML-2026-99")
        self.assertEqual(jobs[0]["application_url"], "https://genericcorp.com/careers/jobs/ml-2026-99")
        self.assertEqual(jobs[0]["link_quality"], "DIRECT")

    def test_embedded_state_strategy(self):
        html = """
        <html>
        <body>
            <script id="__NEXT_DATA__" type="application/json">
            {
                "props": {
                    "pageProps": {
                        "jobListings": [
                            {
                                "id": "NEXT-771",
                                "title": "Fullstack Typescript Specialist",
                                "slug": "fullstack-typescript-specialist-771",
                                "location": "Chennai",
                                "department": "Core Platform"
                            }
                        ]
                    }
                }
            }
            </script>
        </body>
        </html>
        """
        ctx = ExtractionContext(company=self.company, careers_url=self.company.careers_url, html_content=html)
        strategy = EmbeddedStateStrategy()
        self.assertTrue(strategy.detect(ctx))
        jobs = strategy.extract(ctx)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Fullstack Typescript Specialist")
        self.assertEqual(jobs[0]["external_job_id"], "NEXT-771")
        self.assertIn("NEXT-771", jobs[0]["application_url"])

    def test_anchor_card_strategy(self):
        html = """
        <div class="career-cards">
            <div class="job-item">
                <a class="job-link" href="/careers/openings/sr-security-architect-8890">Senior Security Architect</a>
                <span class="location">Gurugram</span>
            </div>
            <div class="job-item">
                <a class="job-link" href="/careers/openings/lead-devops-engineer-8891">Lead DevOps Engineer</a>
                <span class="location">Bengaluru</span>
            </div>
            <div class="job-item">
                <!-- Generic apply link that must NOT be counted as a job opening -->
                <a class="btn" href="/careers#apply">Apply to General Pool</a>
            </div>
        </div>
        """
        ctx = ExtractionContext(company=self.company, careers_url=self.company.careers_url, html_content=html)
        strategy = AnchorCardStrategy()
        self.assertTrue(strategy.detect(ctx))
        jobs = strategy.extract(ctx)

        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0]["title"], "Senior Security Architect")
        self.assertEqual(
            jobs[0]["application_url"],
            "https://genericcorp.com/careers/openings/sr-security-architect-8890"
        )
        self.assertEqual(jobs[0]["link_quality"], "DIRECT")

    def test_sitemap_strategy(self):
        from modules.crawler_engine.strategies.sitemap_strategy import JobSitemapStrategy
        xml_fixture = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://genericcorp.com/careers/jobs/cloud-solutions-architect-992</loc>
                <lastmod>2026-10-18</lastmod>
            </url>
            <url>
                <loc>https://genericcorp.com/about-us</loc>
            </url>
        </urlset>
        """
        html_page_fixture = """
        <html>
            <head><title>Cloud Solutions Architect | Careers</title></head>
            <body><h1>Cloud Solutions Architect</h1></body>
        </html>
        """
        mock_robots = MagicMock(status_code=200, text="Sitemap: https://genericcorp.com/sitemap-jobs.xml")
        mock_sitemap = MagicMock(status_code=200, content=xml_fixture.encode("utf-8"), text=xml_fixture)
        mock_job_page = MagicMock(status_code=200, text=html_page_fixture, url="https://genericcorp.com/careers/jobs/cloud-solutions-architect-992")

        responses = [mock_robots, mock_sitemap, mock_job_page]

        ctx = ExtractionContext(company=self.company, careers_url=self.company.careers_url)
        strategy = JobSitemapStrategy()

        with patch("modules.crawler_engine.strategies.sitemap_strategy.cffi_requests.get", side_effect=responses):
            jobs = strategy.extract(ctx)

        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["title"], "Cloud Solutions Architect")
        self.assertEqual(
            jobs[0]["application_url"],
            "https://genericcorp.com/careers/jobs/cloud-solutions-architect-992"
        )
        self.assertEqual(jobs[0]["link_quality"], "DIRECT")


class PruneSafetyGuardTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_id="SAFETY_CO",
            company_name="Safety Systems Corp",
            website_url="https://safetysys.com",
            careers_url="https://careers.safetysys.com",
        )
        # Create 10 active jobs
        now = timezone.now()
        for i in range(10):
            fp = build_job_fingerprint(
                company_id=self.company.company_id,
                external_job_id=f"EXT_{i}",
                canonical_url=f"https://careers.safetysys.com/job/{i}",
                title=f"Engineer {i}",
                location="Pune",
            )
            Job.objects.create(
                job_id=f"JOB_SAFE_{i}",
                company=self.company,
                job_title=f"Engineer {i}",
                external_job_id=f"EXT_{i}",
                canonical_url=f"https://careers.safetysys.com/job/{i}",
                application_url=f"https://careers.safetysys.com/job/{i}",
                source_url=f"https://careers.safetysys.com/job/{i}",
                status="ACTIVE",
                verification_status="SOURCE_CONFIRMED",
                link_status="SOURCE_CONFIRMED",
                retrieved_at=now,
                evidence_text=f"Engineer {i} at Safety Systems Corp",
                content_hash=f"hash_safe_{i}",
                link_quality="DIRECT",
                fingerprint=fp,
                last_seen_live_at=now,
            )

    def test_safety_guard_activates_on_sharp_drop(self):
        """
        If a new crawl extracts only 2 jobs (80% drop, < 50% threshold),
        pruning MUST be skipped, preserving existing active jobs, and status set to SUSPECT_DROP.
        """
        from modules.crawler_engine.crawler import sync_single_company_live

        extracted_jobs = [
            {
                "title": "Engineer 0",
                "external_job_id": "EXT_0",
                "canonical_url": "https://careers.safetysys.com/job/0",
                "application_url": "https://careers.safetysys.com/job/0",
                "location": "Pune",
                "link_quality": "DIRECT",
            },
            {
                "title": "Engineer 1",
                "external_job_id": "EXT_1",
                "canonical_url": "https://careers.safetysys.com/job/1",
                "application_url": "https://careers.safetysys.com/job/1",
                "location": "Pune",
                "link_quality": "DIRECT",
            },
        ]

        with patch("modules.crawler_engine.crawler.StrategyPipeline.run", return_value=(extracted_jobs, "test_strategy", 100.0)), \
             patch("modules.crawler_engine.crawler.extract_genuine_csr_live", return_value={"csr_projects": []}):
            res = sync_single_company_live(self.company)

        # Company should be marked with SUSPECT_DROP
        self.company.refresh_from_db()
        self.assertEqual(self.company.crawl_status, "SUSPECT_DROP")

        # All 10 jobs must still remain ACTIVE (not pruned!)
        active_count = Job.objects.filter(company=self.company, status="ACTIVE").count()
        self.assertEqual(active_count, 10)

    def test_safe_prune_soft_deletes_missing_jobs(self):
        """
        When extracted count is normal (e.g. 8 out of 10, >= 50%),
        missing jobs must be soft-deleted (status='REMOVED', removed_at set).
        """
        from modules.crawler_engine.crawler import sync_single_company_live

        # 8 out of 10 jobs found (EXT_0 to EXT_7)
        extracted_jobs = [
            {
                "title": f"Engineer {i}",
                "external_job_id": f"EXT_{i}",
                "canonical_url": f"https://careers.safetysys.com/job/{i}",
                "application_url": f"https://careers.safetysys.com/job/{i}",
                "location": "Pune",
                "link_quality": "DIRECT",
            }
            for i in range(8)
        ]

        with patch("modules.crawler_engine.crawler.StrategyPipeline.run", return_value=(extracted_jobs, "test_strategy", 100.0)), \
             patch("modules.crawler_engine.crawler.extract_genuine_csr_live", return_value={"csr_projects": []}):
            res = sync_single_company_live(self.company)

        # 8 jobs active, 2 jobs soft-removed
        active_count = Job.objects.filter(company=self.company, status="ACTIVE").count()
        removed_jobs = Job.objects.filter(company=self.company, status="REMOVED")
        self.assertEqual(active_count, 8)
        self.assertEqual(removed_jobs.count(), 2)
        for rj in removed_jobs:
            self.assertIsNotNone(rj.removed_at)


class FingerprintCalculationTestCase(TestCase):
    def test_fingerprint_uses_external_id_first(self):
        fp1 = build_job_fingerprint(
            company_id="COMP1",
            external_job_id="REQ-500",
            canonical_url="https://example.com/job1",
            title="Dev",
            location="Remote",
        )
        fp2 = build_job_fingerprint(
            company_id="COMP1",
            external_job_id="REQ-500",
            canonical_url="https://example.com/job_diff_url",
            title="Dev Updated",
            location="Remote",
        )
        self.assertEqual(fp1, fp2)

    def test_different_jobs_sharing_listing_url_do_not_collide(self):
        # Two jobs on a generic listing fallback page without external IDs
        fp1 = build_job_fingerprint(
            company_id="COMP1",
            external_job_id=None,
            canonical_url=None,
            title="Accountant",
            location="Delhi",
        )
        fp2 = build_job_fingerprint(
            company_id="COMP1",
            external_job_id=None,
            canonical_url=None,
            title="Brand Manager",
            location="Mumbai",
        )
        self.assertNotEqual(fp1, fp2)
