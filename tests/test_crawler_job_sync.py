import os
import sys
import unittest
from datetime import timedelta
from unittest.mock import patch, MagicMock

import django

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.management import call_command
from django.utils import timezone
from django.test import TestCase, override_settings
from modules.admin_panel.models import Company, Job
from modules.crawler_engine.crawler import sync_single_company_live, build_job_fingerprint

class CrawlerJobSyncUnitTest(TestCase):
    def setUp(self):
        self.company, _ = Company.objects.get_or_create(
            company_id="TEST_SYNC_CO_001",
            defaults={
                "company_name": "Sync Test Enterprise Ltd",
                "official_domain": "synctest001.com",
                "careers_url": "https://synctest001.com/careers",
                "website_url": "https://synctest001.com",
                "jobs_access": "PUBLIC",
            }
        )
        self.company.careers_url = "https://synctest001.com/careers"
        self.company.save()
        Job.objects.filter(company=self.company).delete()

    def tearDown(self):
        Job.objects.filter(company=self.company).delete()
        if self.company.company_id == "TEST_SYNC_CO_001":
            self.company.delete()

    @patch('modules.crawler_engine.crawler.StrategyPipeline.run')
    def test_01_normal_crawl(self, mock_pipeline_run):
        """Scenario 1: Normal crawl discovers jobs, sets status='ACTIVE', last_seen_at set, removed_at=None."""
        mock_pipeline_run.return_value = (
            [
                {
                    "title": "Senior Cloud Engineer",
                    "application_url": "https://synctest001.com/jobs/101",
                    "canonical_url": "https://synctest001.com/jobs/101",
                    "external_job_id": "EXT-101",
                    "link_quality": "DIRECT",
                    "department": "Engineering",
                    "location": "Bengaluru",
                },
                {
                    "title": "Lead Product Designer",
                    "application_url": "https://synctest001.com/jobs/102",
                    "canonical_url": "https://synctest001.com/jobs/102",
                    "external_job_id": "EXT-102",
                    "link_quality": "DIRECT",
                    "department": "Design",
                    "location": "Mumbai",
                }
            ],
            "WORKDAY_DIRECT",
            100.0
        )

        res = sync_single_company_live(self.company)
        self.assertEqual(res['status'], 'SUCCESS')
        self.assertEqual(res['jobs_added'], 2)

        jobs = Job.objects.filter(company=self.company, status='ACTIVE')
        self.assertEqual(jobs.count(), 2)
        for j in jobs:
            self.assertIsNotNone(j.last_seen_at)
            self.assertIsNotNone(j.last_seen_live_at)
            self.assertIsNone(j.removed_at)
            self.assertEqual(j.status, 'ACTIVE')
        print("\n[SCENARIO 1 PASSED] Normal crawl: 2 jobs created with status='ACTIVE', valid last_seen_at, removed_at=None.")

    @patch('modules.crawler_engine.crawler.StrategyPipeline.run')
    def test_02_zero_results_safety_guard(self, mock_pipeline_run):
        """Scenario 2: Crawl returns 0 results -> safety guard activates, skips prune, preserves active jobs."""
        now = timezone.now()
        j1 = Job.objects.create(
            company=self.company,
            job_id="TEST_J_001",
            job_title="DevOps Lead",
            external_job_id="EXT-101",
            status="ACTIVE",
            first_seen_at=now,
            last_seen_at=now,
            application_url="https://synctest001.com/jobs/101",
            canonical_url="https://synctest001.com/jobs/101",
        )
        j2 = Job.objects.create(
            company=self.company,
            job_id="TEST_J_002",
            job_title="Security Architect",
            external_job_id="EXT-102",
            status="ACTIVE",
            first_seen_at=now,
            last_seen_at=now,
            application_url="https://synctest001.com/jobs/102",
            canonical_url="https://synctest001.com/jobs/102",
        )

        # Mock returns 0 jobs
        mock_pipeline_run.return_value = ([], "HTML_FALLBACK", 0.0)

        res = sync_single_company_live(self.company)
        self.company.refresh_from_db()

        self.assertEqual(self.company.crawl_status, "SUSPECT_DROP")
        # Ensure 0 jobs were pruned
        active_count = Job.objects.filter(company=self.company, status='ACTIVE').count()
        self.assertEqual(active_count, 2, "Safety guard failed: active jobs were pruned on 0-result crawl!")
        print("[SCENARIO 2 PASSED] 0 results: safety guard activated (SUSPECT_DROP), 0 jobs pruned.")

    @patch('modules.crawler_engine.crawler.StrategyPipeline.run')
    def test_03_error_isolation(self, mock_pipeline_run):
        """Scenario 3: Crawl throws exception -> error is caught, logged in last_sync_error, existing jobs untouched."""
        now = timezone.now()
        Job.objects.create(
            company=self.company,
            job_id="TEST_J_003",
            job_title="Data Scientist",
            status="ACTIVE",
            first_seen_at=now,
            last_seen_at=now,
            application_url="https://synctest001.com/jobs/103",
            canonical_url="https://synctest001.com/jobs/103",
        )

        # Simulate ATS API connection failure
        mock_pipeline_run.side_effect = RuntimeError("504 Gateway Timeout while contacting ATS")

        res = sync_single_company_live(self.company)
        self.company.refresh_from_db()

        self.assertEqual(self.company.crawl_status, "ERROR")
        self.assertIn("504 Gateway Timeout", self.company.last_sync_error)
        # Ensure existing jobs were NOT pruned
        self.assertEqual(Job.objects.filter(company=self.company, status='ACTIVE').count(), 1)
        print("[SCENARIO 3 PASSED] Error isolation: exception caught, crawl_status='ERROR', last_sync_error set, existing jobs safe.")

    @patch('modules.crawler_engine.crawler.StrategyPipeline.run')
    def test_04_under_50_percent_found_safety_guard(self, mock_pipeline_run):
        """Scenario 4: Previous count is 10, crawl finds 3 (<50%) -> prune guard triggers, skips prune."""
        now = timezone.now()
        for i in range(10):
            fp = build_job_fingerprint(
                company_id=self.company.company_id,
                external_job_id=f"EXT-BATCH-{i}",
                canonical_url=f"https://synctest001.com/jobs/{i}",
                title=f"Engineer {i}",
                location="India",
            )
            Job.objects.create(
                company=self.company,
                job_id=f"TEST_J_BATCH_{i}",
                job_title=f"Engineer {i}",
                fingerprint=fp,
                external_job_id=f"EXT-BATCH-{i}",
                status="ACTIVE",
                first_seen_at=now,
                last_seen_at=now,
                application_url=f"https://synctest001.com/jobs/{i}",
                canonical_url=f"https://synctest001.com/jobs/{i}",
            )

        # Only 3 jobs found (3 < 5 = 50% of 10)
        mock_pipeline_run.return_value = (
            [
                {"title": f"Engineer {i}", "application_url": f"https://synctest001.com/jobs/{i}", "canonical_url": f"https://synctest001.com/jobs/{i}", "external_job_id": f"EXT-BATCH-{i}", "link_quality": "DIRECT"}
                for i in range(3)
            ],
            "WORKDAY_DIRECT",
            100.0
        )

        res = sync_single_company_live(self.company)
        self.company.refresh_from_db()

        self.assertEqual(self.company.crawl_status, "SUSPECT_DROP")
        # All 10 jobs must remain ACTIVE (prune blocked)
        self.assertEqual(Job.objects.filter(company=self.company, status='ACTIVE').count(), 10)
        print("[SCENARIO 4 PASSED] <50% found guard: 3/10 found triggers SUSPECT_DROP, prune blocked, all 10 jobs preserved.")

    @patch('modules.crawler_engine.crawler.StrategyPipeline.run')
    def test_05_reappearing_job_reactivates(self, mock_pipeline_run):
        """Scenario 5: Soft-removed or EXPIRED job reappears -> must reactivate to ACTIVE and clear removed_at."""
        past = timezone.now() - timedelta(days=10)
        # Create a REMOVED job
        j_rem = Job.objects.create(
            company=self.company,
            job_id="TEST_J_REAPPEAR_REM",
            job_title="Staff Frontend Architect",
            external_job_id="EXT-REACTIVATE-1",
            status="REMOVED",
            first_seen_at=past,
            last_seen_at=past,
            removed_at=past,
            application_url="https://synctest001.com/jobs/reactivate-1",
            canonical_url="https://synctest001.com/jobs/reactivate-1",
        )
        # Create an EXPIRED job
        j_exp = Job.objects.create(
            company=self.company,
            job_id="TEST_J_REAPPEAR_EXP",
            job_title="Principal Database Admin",
            external_job_id="EXT-REACTIVATE-2",
            status="EXPIRED",
            first_seen_at=past,
            last_seen_at=past,
            removed_at=past,
            application_url="https://synctest001.com/jobs/reactivate-2",
            canonical_url="https://synctest001.com/jobs/reactivate-2",
        )

        mock_pipeline_run.return_value = (
            [
                {
                    "title": "Staff Frontend Architect",
                    "application_url": "https://synctest001.com/jobs/reactivate-1",
                    "canonical_url": "https://synctest001.com/jobs/reactivate-1",
                    "external_job_id": "EXT-REACTIVATE-1",
                    "link_quality": "DIRECT",
                },
                {
                    "title": "Principal Database Admin",
                    "application_url": "https://synctest001.com/jobs/reactivate-2",
                    "canonical_url": "https://synctest001.com/jobs/reactivate-2",
                    "external_job_id": "EXT-REACTIVATE-2",
                    "link_quality": "DIRECT",
                }
            ],
            "WORKDAY_DIRECT",
            100.0
        )

        res = sync_single_company_live(self.company)

        j_rem.refresh_from_db()
        j_exp.refresh_from_db()

        self.assertEqual(j_rem.status, "ACTIVE", "Soft-removed job did not reactivate!")
        self.assertIsNone(j_rem.removed_at, "Soft-removed job removed_at was not cleared!")
        self.assertGreater(j_rem.last_seen_at, past, "last_seen_at was not refreshed!")

        self.assertEqual(j_exp.status, "ACTIVE", "EXPIRED job did not reactivate!")
        self.assertIsNone(j_exp.removed_at, "EXPIRED job removed_at was not cleared!")
        self.assertGreater(j_exp.last_seen_at, past, "last_seen_at was not refreshed!")

        print("[SCENARIO 5 PASSED] Reappearing jobs: REMOVED and EXPIRED jobs reactivated to ACTIVE, removed_at cleared, last_seen_at refreshed.")

    def test_06_expire_jobs_absence_only(self):
        """Scenario 6: expire_jobs only expires jobs soft-removed >7d, leaving active jobs and <7d removed untouched."""
        now = timezone.now()
        past_8d = now - timedelta(days=8)
        past_3d = now - timedelta(days=3)

        # 1. Soft-removed 8 days ago (>7d)
        j_old_rem = Job.objects.create(
            company=self.company,
            job_id="TEST_J_EXP_8D",
            job_title="Old Soft-Removed Job",
            status="REMOVED",
            removed_at=past_8d,
            last_seen_at=past_8d,
            application_url="https://synctest001.com/jobs/8d",
        )
        # 2. Soft-removed 3 days ago (<7d) -> should stay REMOVED (grace period)
        j_recent_rem = Job.objects.create(
            company=self.company,
            job_id="TEST_J_REM_3D",
            job_title="Recent Soft-Removed Job",
            status="REMOVED",
            removed_at=past_3d,
            last_seen_at=past_3d,
            application_url="https://synctest001.com/jobs/3d",
        )
        # 3. Active job last seen 30 days ago -> age alone must NOT expire active jobs
        j_active_old = Job.objects.create(
            company=self.company,
            job_id="TEST_J_ACTIVE_OLD",
            job_title="Long Active Role",
            status="ACTIVE",
            first_seen_at=now - timedelta(days=60),
            last_seen_at=now - timedelta(days=30),
            application_url="https://synctest001.com/jobs/active-old",
        )

        # First verify FREEZE_JOB_EXPIRY_AND_DELETION = True prevents any expiry
        with override_settings(FREEZE_JOB_EXPIRY_AND_DELETION=True):
            call_command('expire_jobs')
            j_old_rem.refresh_from_db()
            self.assertEqual(j_old_rem.status, 'REMOVED', "Freeze setting failed: job was expired while frozen!")

        # Now test when FREEZE_JOB_EXPIRY_AND_DELETION = False (operator approved)
        with override_settings(FREEZE_JOB_EXPIRY_AND_DELETION=False):
            call_command('expire_jobs')

        j_old_rem.refresh_from_db()
        j_recent_rem.refresh_from_db()
        j_active_old.refresh_from_db()

        self.assertEqual(j_old_rem.status, 'EXPIRED', "Job removed >7d was not transitioned to EXPIRED!")
        self.assertEqual(j_old_rem.verification_status, 'STALE')
        self.assertEqual(j_recent_rem.status, 'REMOVED', "Job removed <7d was prematurely expired!")
        self.assertEqual(j_active_old.status, 'ACTIVE', "Active job was wrongly expired by age alone!")

        print("[SCENARIO 6 PASSED] expire_jobs: strictly honors freeze setting, expires only by absence (>7d soft-removed), leaves active jobs and <7d grace period untouched.")

if __name__ == '__main__':
    unittest.main()
