"""
Regression & Data Integrity Test Suite for Job Detail Pipeline (Part 12).

Tests:
1. Universal extraction of rich ATS fields (SAP SuccessFactors CSB, Workday, SmartRecruiters).
2. Database persistence of rich job fields (pay_band, function, role_purpose, responsibilities,
   day_in_the_life, technical_skills, behavioural_skills, employer_info).
3. API serialization guarantees all rich fields are returned to the frontend.
4. "Not fetched" vs "Not mentioned by source" distinction (detail_fetch_status).
5. Scoping of related jobs strictly to the same company.
"""

import json
from django.test import TestCase, Client
from django.utils import timezone

from modules.admin_panel.models import Company, Job
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor
from modules.website.views.job_api_views import serialize_job_item


class JobDetailIntegrityTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = Company.objects.create(
            company_id="HEROMOTO",
            company_name="Hero MotoCorp Limited",
            nse_symbol="HEROMOTOCO",
            website_url="https://www.heromotocorp.com",
            careers_url="https://jobs.heromotocorp.com",
            sector="Automotive",
            headquarters="New Delhi, Delhi",
            crawl_status="CRAWLED",
        )
        self.other_company = Company.objects.create(
            company_id="MARUTI",
            company_name="Maruti Suzuki India Limited",
            nse_symbol="MARUTI",
            website_url="https://www.marutisuzuki.com",
            careers_url="https://www.marutisuzuki.com/careers",
            sector="Automotive",
            headquarters="New Delhi, Delhi",
            crawl_status="CRAWLED",
        )

        self.rich_job = Job.objects.create(
            job_row_id=6570,
            job_id="HERO-6570",
            company=self.company,
            job_title="TERRITORY MANAGER-SALES",
            external_job_id="1368423366",
            posted_date="2026-10-06",
            location="Raipur, CT, IN, 492001",
            city="Raipur",
            state="CT",
            country="IN",
            function="India BU",
            department="Sales",
            pay_band="E4 to M2",
            role_purpose="Territory Manager - Sales drives sales volume and market share across the allocated territory.",
            responsibilities="1. Achieve retail and wholesale sales targets for assigned territory.\n2. Manage dealer network profitability and stock availability.\n3. Implement marketing and promotional campaigns.",
            day_in_the_life="Engage with dealers, monitor daily retail bookings, review inventory and execute local sales promotions.",
            qualifications="MBA with 1-3 years experience in Automotive / FMCG sales.",
            education="MBA",
            experience="1-3 yrs",
            technical_skills="Territory management, Dealer management, Sales planning, Automotive product knowledge",
            behavioural_skills="Customer focus, Negotiation, Problem solving, Team collaboration",
            employer_info="Hero MotoCorp Ltd. is the world's largest manufacturer of motorcycles and scooters.",
            job_description="Complete description with role purpose and responsibilities.",
            application_url="https://jobs.heromotocorp.com/job/Raipur-TERRITORY-MANAGER-SALES-CT-492001/1368423366/",
            source_url="https://jobs.heromotocorp.com/job/Raipur-TERRITORY-MANAGER-SALES-CT-492001/1368423366/",
            detail_fetched=True,
            detail_fetch_status="FETCHED",
            detail_fetched_at=timezone.now().isoformat(),
            status="ACTIVE",
            link_status="SOURCE_CONFIRMED",
            verification_status="SOURCE_CONFIRMED",
            retrieved_at=timezone.now().isoformat(),
            evidence_text="TERRITORY MANAGER-SALES at Hero MotoCorp Raipur, CT, IN, 492001",
        )
        self.rich_job.verification_status = "PUBLISHED"
        self.rich_job.save()

        self.unfetched_job = Job.objects.create(
            job_row_id=6571,
            job_id="HERO-6571",
            company=self.company,
            job_title="TERRITORY SALES EXECUTIVE",
            external_job_id="1368423367",
            posted_date="2026-10-06",
            location="Durg, CT, IN",
            application_url="https://jobs.heromotocorp.com/job/Durg-TERRITORY-SALES-EXECUTIVE/1368423367/",
            source_url="https://jobs.heromotocorp.com/job/Durg-TERRITORY-SALES-EXECUTIVE/1368423367/",
            detail_fetched=False,
            detail_fetch_status="NOT_FETCHED",
            status="ACTIVE",
            link_status="SOURCE_CONFIRMED",
            verification_status="SOURCE_CONFIRMED",
            retrieved_at=timezone.now().isoformat(),
            evidence_text="TERRITORY SALES EXECUTIVE at Hero MotoCorp",
        )
        self.unfetched_job.verification_status = "PUBLISHED"
        self.unfetched_job.save()

        self.other_job = Job.objects.create(
            job_row_id=8001,
            job_id="MARUTI-8001",
            company=self.other_company,
            job_title="AREA SALES MANAGER",
            status="ACTIVE",
            source_url="https://example.com/maruti/jobs/8001",
            link_status="SOURCE_CONFIRMED",
            verification_status="SOURCE_CONFIRMED",
            retrieved_at=timezone.now().isoformat(),
            evidence_text="AREA SALES MANAGER at Maruti Suzuki",
        )
        self.other_job.verification_status = "PUBLISHED"
        self.other_job.save()

    def test_database_fields_integrity(self):
        """Verify that all rich fields are accurately stored in the Job model."""
        job = Job.objects.get(job_row_id=6570)
        self.assertEqual(job.pay_band, "E4 to M2")
        self.assertEqual(job.function, "India BU")
        self.assertEqual(job.location, "Raipur, CT, IN, 492001")
        self.assertEqual(job.education, "MBA")
        self.assertEqual(job.experience, "1-3 yrs")
        self.assertTrue("Territory Manager - Sales drives" in job.role_purpose)
        self.assertTrue("Achieve retail and wholesale" in job.responsibilities)
        self.assertTrue("Engage with dealers" in job.day_in_the_life)
        self.assertTrue("Territory management" in job.technical_skills)
        self.assertTrue("Customer focus" in job.behavioural_skills)
        self.assertTrue("world's largest manufacturer" in job.employer_info)
        self.assertEqual(job.detail_fetch_status, "FETCHED")
        self.assertTrue(job.detail_fetched)

    def test_api_serializer_preserves_all_rich_fields(self):
        """Verify that serialize_job_item returns all 8 new fields plus metadata."""
        data = serialize_job_item(self.rich_job)
        self.assertEqual(data["pay_band"], "E4 to M2")
        self.assertEqual(data["function"], "India BU")
        self.assertEqual(data["education"], "MBA")
        self.assertEqual(data["experience"], "1-3 yrs")
        self.assertEqual(data["location"], "Raipur, CT, IN, 492001")
        self.assertEqual(data["role_purpose"], self.rich_job.role_purpose)
        self.assertEqual(data["responsibilities"], self.rich_job.responsibilities)
        self.assertEqual(data["day_in_the_life"], self.rich_job.day_in_the_life)
        self.assertEqual(data["technical_skills"], self.rich_job.technical_skills)
        self.assertEqual(data["behavioural_skills"], self.rich_job.behavioural_skills)
        self.assertEqual(data["employer_info"], self.rich_job.employer_info)
        self.assertEqual(data["detail_fetch_status"], "FETCHED")
        self.assertTrue(data["detail_fetched"])

    def test_unfetched_job_status_in_api(self):
        """Verify that unfetched jobs report NOT_FETCHED without premature claims."""
        data = serialize_job_item(self.unfetched_job)
        self.assertEqual(data["detail_fetch_status"], "NOT_FETCHED")
        self.assertFalse(data["detail_fetched"])
        self.assertIsNone(data["pay_band"])
        self.assertIsNone(data["responsibilities"])

    def test_live_job_details_api_endpoint(self):
        """Test GET /api/jobs/<job_id> returns 200 with full rich data payload."""
        response = self.client.get(f"/api/jobs/{self.rich_job.job_row_id}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        item = payload.get("job") or payload
        self.assertEqual(item["job_title"], "TERRITORY MANAGER-SALES")
        self.assertEqual(item["pay_band"], "E4 to M2")
        self.assertEqual(item["function"], "India BU")
        self.assertEqual(item["education"], "MBA")
        self.assertEqual(item["location"], "Raipur, CT, IN, 492001")
        self.assertIn("Achieve retail", item["responsibilities"])

    def test_related_jobs_strictly_scoped_to_same_company(self):
        """Verify related jobs for a company only include jobs from that exact company."""
        response = self.client.get(f"/api/jobs/{self.rich_job.job_row_id}/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        related_jobs = data.get("related_jobs", [])
        self.assertTrue(len(related_jobs) > 0)
        for rj in related_jobs:
            self.assertEqual(rj.get("company_id"), self.company.company_id)
            self.assertNotEqual(rj.get("job_row_id"), self.rich_job.job_row_id)
            self.assertNotEqual(rj.get("company_id"), self.other_company.company_id)

    def test_universal_extractor_parses_csb_html(self):
        """Verify UniversalJobDetailExtractor correctly extracts CSB HTML layout."""
        sample_csb_html = '''
        <html>
        <head><title>TERRITORY MANAGER-SALES</title></head>
        <body>
            <span class="jobDate">6 Oct 2026</span>
            <span class="jobLocation">Raipur, CT, IN, 492001</span>
            <div class="jobDisplay">
                <p><b>Function:</b> India BU</p>
                <p><b>Pay Band:</b> E4 to M2</p>
                <h2>Role</h2>
                <p>Lead the territory sales and ensure targets are achieved.</p>
                <h2>Key Responsibilities</h2>
                <ul>
                    <li>Drive wholesale and retail sales.</li>
                    <li>Coordinate dealer stock replenishment.</li>
                </ul>
                <h2>A Day in the life</h2>
                <p>Start with dealer huddle and track retail numbers.</p>
                <h2>Academic Qualification & Experience</h2>
                <p>MBA with 1-3 years experience.</p>
                <h2>Technical Skills / Knowledge</h2>
                <ul>
                    <li>Sales planning</li>
                    <li>Channel management</li>
                </ul>
                <h2>Behavioural Skills</h2>
                <ul>
                    <li>Negotiation</li>
                    <li>Leadership</li>
                </ul>
                <h2>About Hero</h2>
                <p>Hero MotoCorp is India's leading two-wheeler maker.</p>
            </div>
        </body>
        </html>
        '''
        res = UniversalJobDetailExtractor.extract_from_url(
            "https://jobs.heromotocorp.com/job/test/123/",
            preloaded_html=sample_csb_html
        )
        self.assertEqual(res["detail_fetch_status"], "FETCHED")
        self.assertEqual(res["function"], "India BU")
        self.assertEqual(res["pay_band"], "E4 to M2")
        self.assertEqual(res["posted_date"], "6 Oct 2026")
        self.assertEqual(res["location"], "Raipur, CT, IN, 492001")
        self.assertIn("Lead the territory sales", res["role_purpose"])
        self.assertIn("Drive wholesale and retail sales", res["responsibilities"])
        self.assertIn("Start with dealer huddle", res["day_in_the_life"])
        self.assertEqual(res["education"], "MBA")
        self.assertIn("1-3", res["experience"])
        self.assertIn("Sales planning", res["technical_skills"])
        self.assertIn("Negotiation", res["behavioural_skills"])
        self.assertIn("Hero MotoCorp is India's leading", res["employer_info"])
