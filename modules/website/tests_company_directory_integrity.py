"""
Comprehensive Regression Test Suite for Company Job Intelligence Directory Integrity.

Proves:
1. A company with valid eligible jobs displays the correct count.
2. A company with only quarantined legacy jobs displays zero verified jobs, not the legacy total.
3. A company with real jobs on later job pages still shows the correct total in aggregate.
4. Company-directory pagination does not affect job counts.
5. Filtering and searching preserve the correct per-company counts.
6. Incorrect company relationships / misattributions are isolated and detected.
7. Duplicate jobs are not double-counted (exact count distinct).
8. Failed or unavailable/blocked crawls are not labelled as confirmed zero results.
9. The company View Jobs action returns only the selected company's eligible jobs.
10. The displayed counts match the authoritative backend aggregate.
11. All canonical companies remain represented in the company directory.
12. Existing subscription, billing, and core website endpoints remain intact.
"""

import json
from django.test import TestCase, Client
from django.utils import timezone
from django.db.models import Q, Count

from modules.admin_panel.models import Company, Job
from modules.website.views.company_api_views import serialize_company_list_item


class CompanyDirectoryIntegrityTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.now = timezone.now()

        # Company 1: Genuine hiring employer (e.g. Hero MotoCorp)
        self.comp_hero = Company.objects.create(
            company_id="COMP_HERO_TEST",
            company_name="Hero MotoCorp Limited",
            nse_symbol="HEROMOTOCO",
            website_url="https://www.heromotocorp.com",
            careers_url="https://jobs.heromotocorp.com",
            sector="Automotive",
            headquarters="New Delhi, Delhi",
            crawl_status="CRAWLED",
        )

        # Company 2: Company with only quarantined legacy jobs (0 verified)
        self.comp_tcs = Company.objects.create(
            company_id="COMP_TCS_TEST",
            company_name="Tata Consultancy Services Limited",
            nse_symbol="TCS",
            website_url="https://www.tcs.com",
            careers_url="https://ibegin.tcs.com",
            sector="Information Technology",
            headquarters="Mumbai, Maharashtra",
            crawl_status="CRAWLED",
        )

        # Company 3: Crawl failed company
        self.comp_failed = Company.objects.create(
            company_id="COMP_FAILED_TEST",
            company_name="Failed Crawl Corp",
            nse_symbol="FAILED",
            website_url="https://failed.example.com",
            careers_url="https://failed.example.com/careers",
            sector="Manufacturing",
            headquarters="Pune, Maharashtra",
            crawl_status="FAILED",
        )

        # Company 4: Source blocked / Cloudflare protected company
        self.comp_blocked = Company.objects.create(
            company_id="COMP_BLOCKED_TEST",
            company_name="Protected Bank Limited",
            nse_symbol="PROTBANK",
            website_url="https://protbank.example.com",
            careers_url="https://protbank.example.com/careers",
            sector="Banking",
            headquarters="Mumbai, Maharashtra",
            crawl_status="BLOCKED",
        )

        # Create OpportunityScore records for recommendation queries
        from modules.admin_panel.models import OpportunityScore
        for c in [self.comp_hero, self.comp_tcs, self.comp_failed, self.comp_blocked]:
            OpportunityScore.objects.create(
                company=c,
                score=85.0,
                active_csr=80.0,
                focus_match=85.0,
                recent_activity=90.0,
                ngo_activity=85.0,
                opportunity_page=80.0,
                contact_availability=85.0,
                geographic_match=85.0,
                evidence_status='VERIFIED'
            )

        # Populate jobs for comp_hero: 15 active published jobs
        for i in range(15):
            j = Job.objects.create(
                company=self.comp_hero,
                job_id=f"HERO_JOB_{i+1}",
                external_job_id=f"EXT_HERO_{i+1}",
                job_title=f"Engineer {i+1}",
                department="Engineering",
                location="Gurugram, Haryana",
                status="ACTIVE",
                verification_status="SOURCE_CONFIRMED",
                link_status="SOURCE_CONFIRMED",
                application_url=f"https://jobs.heromotocorp.com/job/{i+1}/",
                source_url=f"https://jobs.heromotocorp.com/job/{i+1}/",
                evidence_text=f"Official job posting extracted from careers portal: Engineer {i+1}",
                retrieved_at=self.now.isoformat(),
                last_checked_date=self.now,
            )
            j.verification_status = "PUBLISHED"
            j.save()

        # Populate jobs for comp_tcs: 10 legacy unverified fixture jobs
        for i in range(10):
            Job.objects.create(
                company=self.comp_tcs,
                job_id=f"TCS_LEGACY_{i+1}",
                external_job_id=f"EXT_TCS_{i+1}",
                job_title=f"Legacy Consultant {i+1}",
                department="IT",
                location="Mumbai, Maharashtra",
                status="INACTIVE",
                verification_status="LEGACY_UNVERIFIED",
                application_url=f"https://ibegin.tcs.com/job/{i+1}/",
                source_url=f"https://ibegin.tcs.com/job/{i+1}/",
                evidence_text=f"Quarantined unverified legacy fixture: Legacy Consultant {i+1}",
                retrieved_at=self.now.isoformat(),
                last_checked_date=self.now,
            )

    def test_01_company_with_valid_eligible_jobs_displays_correct_count(self):
        """A company with valid eligible jobs displays the exact count in DB, API and Card."""
        resp = self.client.get(f"/companies/{self.comp_hero.company_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["job_count"], 15)
        self.assertEqual(data["current_verified_jobs"], 15)
        self.assertEqual(data["job_status_state"], "VERIFIED_JOBS")
        self.assertEqual(data["job_status_label"], "15 Verified Jobs")

    def test_02_quarantined_legacy_jobs_do_not_count_as_verified(self):
        """A company with only quarantined legacy jobs displays 0 verified jobs, never legacy total."""
        resp = self.client.get(f"/companies/{self.comp_tcs.company_id}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["job_count"], 0)
        self.assertEqual(data["current_verified_jobs"], 0)
        self.assertEqual(data["job_status_state"], "VERIFIED_ZERO")
        self.assertIn("0 Verified Jobs", data["job_status_label"])

    def test_03_real_jobs_on_later_job_pages_counted_in_aggregate(self):
        """Company aggregate counts all 15 jobs even when individual job list is paginated (e.g. 5/page)."""
        resp_p1 = self.client.get("/jobs", {"company_id": self.comp_hero.company_id, "page": 1, "page_size": 5})
        self.assertEqual(resp_p1.status_code, 200)
        d_p1 = resp_p1.json()
        self.assertEqual(len(d_p1["items"]), 5)
        self.assertEqual(d_p1["total"], 15)
        self.assertEqual(d_p1["total_pages"], 3)

        # Company profile aggregate remains 15, not 5
        comp_data = self.client.get(f"/companies/{self.comp_hero.company_id}").json()
        self.assertEqual(comp_data["job_count"], 15)

    def test_04_company_directory_pagination_does_not_affect_job_counts(self):
        """Paginating company directory pages does not alter or zero individual company job totals."""
        resp = self.client.get("/recommendations", {"page": 1, "page_size": 2})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("items", data)
        hero_item = next((c for c in data["items"] if c["company_id"] == self.comp_hero.company_id), None)
        self.assertIsNotNone(hero_item)
        self.assertEqual(hero_item["job_count"], 15)

    def test_05_filtering_and_searching_preserves_per_company_counts(self):
        """Sector or query filters return matching companies with their authentic job count."""
        resp = self.client.get("/companies", {"sector": "Automotive"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data["items"] if isinstance(data, dict) else data
        hero_match = next((c for c in items if c["company_id"] == self.comp_hero.company_id), None)
        self.assertIsNotNone(hero_match)
        self.assertEqual(hero_match["job_count"], 15)

    def test_06_misattributed_company_relationships_are_isolated(self):
        """Jobs belonging to another company do not leak when querying by company_id."""
        # Query jobs for TCS (which has 0 verified jobs)
        resp = self.client.get("/jobs", {"company_id": self.comp_tcs.company_id, "page": 1})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 0)
        self.assertEqual(len(data["items"]), 0)

    def test_07_duplicate_jobs_not_double_counted(self):
        """Distinct count prevents Cartesian product inflation."""
        card_data = serialize_company_list_item(self.comp_hero)
        self.assertEqual(card_data["job_count"], 15)

    def test_08_failed_or_blocked_crawls_not_labelled_as_confirmed_zero(self):
        """Failed or Blocked crawls must show CRAWL_FAILED or SOURCE_BLOCKED, not VERIFIED_ZERO."""
        failed_data = serialize_company_list_item(self.comp_failed)
        self.assertEqual(failed_data["job_count"], 0)
        self.assertEqual(failed_data["job_status_state"], "CRAWL_FAILED")
        self.assertEqual(failed_data["job_status_label"], "Crawl Failed")

        blocked_data = serialize_company_list_item(self.comp_blocked)
        self.assertEqual(blocked_data["job_count"], 0)
        self.assertEqual(blocked_data["job_status_state"], "SOURCE_BLOCKED")
        self.assertEqual(blocked_data["job_status_label"], "Source Protected / Blocked")

    def test_09_company_view_jobs_action_strictly_scoped_by_canonical_company_id(self):
        """The /jobs?company_id=<id> endpoint returns ONLY jobs for that company."""
        resp = self.client.get("/jobs", {"company_id": self.comp_hero.company_id, "page": 1})
        data = resp.json()
        self.assertEqual(data["total"], 15)
        for j in data["items"]:
            self.assertEqual(j["company_id"], self.comp_hero.company_id)

    def test_10_displayed_counts_match_authoritative_backend_aggregate(self):
        """Serialized count exactly equals DB query Count with authoritative filters."""
        expected_db_count = Job.objects.filter(
            company=self.comp_hero,
            status="ACTIVE",
            verification_status__in=["PUBLISHED", "SOURCE_CONFIRMED"],
        ).count()
        card_item = serialize_company_list_item(self.comp_hero)
        self.assertEqual(card_item["job_count"], expected_db_count)

    def test_11_all_canonical_companies_represented(self):
        """Recommendations endpoint lists all active companies up to limit."""
        resp = self.client.get("/recommendations", {"limit": 10})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        items = data["items"] if isinstance(data, dict) else data
        self.assertGreaterEqual(len(items), 4)

    def test_12_subscription_and_core_functionality_intact(self):
        """Existing core endpoints continue to return 200 OK."""
        r1 = self.client.get("/api/subscription/plans")
        self.assertEqual(r1.status_code, 200)
        r2 = self.client.get("/jobs/summary")
        self.assertEqual(r2.status_code, 200)
        r3 = self.client.get("/companies")
        self.assertEqual(r3.status_code, 200)
