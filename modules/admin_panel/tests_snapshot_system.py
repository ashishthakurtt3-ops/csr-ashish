"""
Comprehensive Verification Test Suite for Precomputed Snapshot & Reconciliation System.

Covers all STEP 8 requirements:
1. snapshot built after audit
2. failed audit keeps the previous snapshot
3. suspect audit not published
4. atomic switch
5. endpoints return from snapshot with assertNumQueries <= 2
6. edit event updates metrics immediately
7. envelope unchanged
8. defective-flag parity with old logic on all rows
9. stats header total equals the /jobs list total for the same filters
10. validation failures block publishing
11. reconcile detects a deliberately corrupted snapshot
12. fallback runs only when no snapshot exists
"""
from django.test import TestCase, Client
from django.core.cache import cache
from django.utils import timezone
from modules.admin_panel.models import (
    Company, Job, CSRProject, CSROpportunity, Contact, OpportunityScore
)
from modules.admin_panel.models.snapshot import (
    AuditRun, StatsSnapshot, JobSummarySnapshot, CompanyMetrics
)
from modules.admin_panel.snapshot_service import (
    build_snapshots, reconcile_snapshots, recompute_job_defective_flags,
    get_current_stats_snapshot, get_current_job_summary_snapshot,
    sync_company_metrics_event
)
from modules.admin_panel.verification import (
    public_jobs, is_defective_job_record
)


class SnapshotSystemTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()

        # Create baseline company
        self.company = Company.objects.create(
            company_id="TEST_CORP_1",
            company_name="Test Enterprise Limited",
            nse_symbol="TESTCORP",
            sector="Technology",
            website_url="https://testcorp.example.com",
            careers_url="https://testcorp.example.com/careers",
            crawl_status="CRAWLED"
        )
        self.company2 = Company.objects.create(
            company_id="TEST_CORP_2",
            company_name="Second Enterprise Limited",
            nse_symbol="SECONDCORP",
            sector="Healthcare",
            website_url="https://second.example.com",
            careers_url="https://second.example.com/careers",
            crawl_status="CRAWLED"
        )

        now = timezone.now()
        # Create genuine jobs
        self.job1 = Job.objects.create(
            job_id="TEST-JOB-1",
            company=self.company,
            job_title="Software Engineer - Python Backend",
            application_url="https://testcorp.example.com/jobs/1",
            source_url="https://testcorp.example.com/jobs/1",
            retrieved_at=now,
            evidence_text="Software engineer role verified on official careers portal",
            status="ACTIVE",
            verification_status="PUBLISHED",
            work_mode="On-site",
            link_quality="DIRECT"
        )
        self.job2 = Job.objects.create(
            job_id="TEST-JOB-2",
            company=self.company,
            job_title="Impact Program Director",
            application_url="https://testcorp.example.com/jobs/2",
            source_url="https://testcorp.example.com/jobs/2",
            retrieved_at=now,
            evidence_text="Director role verified on official careers portal",
            status="ACTIVE",
            verification_status="PUBLISHED",
            work_mode="Remote",
            link_quality="DIRECT"
        )
        # Create defective job
        self.defective_job = Job.objects.create(
            job_id="TEST-JOB-DEFECT",
            company=self.company,
            job_title="Click here",
            application_url="https://testcorp.example.com/faqs",
            source_url="https://testcorp.example.com/faqs",
            retrieved_at=now,
            evidence_text="Defect boilerplate nav element",
            status="ACTIVE",
            verification_status="PUBLISHED",
            work_mode="On-site"
        )

        # Create CSR project
        self.csr1 = CSRProject.objects.create(
            company=self.company,
            project_name="Clean Drinking Water Initiative",
            category="Water & Sanitation",
            source_url="https://testcorp.example.com/csr",
            retrieved_at=now,
            evidence_text="Clean drinking water project disclosed in report",
            status="ACTIVE",
            verification_status="PUBLISHED",
            confidence=0.95
        )

    def test_01_snapshot_built_after_audit(self):
        """1. Verify snapshot is built, validated, and published after audit."""
        audit_run = build_snapshots(triggered_by="TEST_SUITE", notes="Baseline test")
        self.assertEqual(audit_run.status, "COMPLETE")
        self.assertTrue(audit_run.is_current)
        self.assertEqual(audit_run.job_count, 2)  # 2 genuine jobs, 1 defective excluded

        # Snapshots exist
        self.assertTrue(StatsSnapshot.objects.filter(audit_run=audit_run).exists())
        self.assertTrue(JobSummarySnapshot.objects.filter(audit_run=audit_run).exists())
        self.assertEqual(CompanyMetrics.objects.filter(audit_run=audit_run).count(), 2)

    def test_02_failed_audit_keeps_previous_snapshot(self):
        """2. Verify failed audit leaves previous current run untouched."""
        run1 = build_snapshots(triggered_by="TEST_1")
        self.assertTrue(run1.is_current)

        # Force failure in a second run by simulating an unhandled error
        try:
            with self.settings():
                # Temporarily corrupt a validator to raise exception
                def fail_compute():
                    raise RuntimeError("Simulated database timeout")
                from modules.admin_panel import snapshot_service
                orig_compute = snapshot_service.compute_live_stats
                snapshot_service.compute_live_stats = fail_compute
                try:
                    build_snapshots(triggered_by="TEST_FAIL")
                finally:
                    snapshot_service.compute_live_stats = orig_compute
        except RuntimeError:
            pass

        # Previous run must STILL be current
        run1.refresh_from_db()
        self.assertTrue(run1.is_current)
        self.assertEqual(run1.status, "COMPLETE")

    def test_03_suspect_audit_not_published(self):
        """3. Verify suspect audit (anti-drop >50% or threshold) is marked SKIPPED_SUSPECT and not published."""
        run1 = build_snapshots(triggered_by="TEST_BASELINE")
        self.assertTrue(run1.is_current)

        # Now remove all genuine jobs to trigger the >50% anti-drop guard
        Job.objects.filter(job_id__in=["TEST-JOB-1", "TEST-JOB-2"]).update(status="INACTIVE")

        suspect_run = build_snapshots(triggered_by="TEST_SUSPECT")
        self.assertEqual(suspect_run.status, "SKIPPED_SUSPECT")
        self.assertFalse(suspect_run.is_current)

        # Previous run must remain current
        run1.refresh_from_db()
        self.assertTrue(run1.is_current)

    def test_04_atomic_switch(self):
        """4. Verify switching current snapshot is atomic (only one complete run is current)."""
        run1 = build_snapshots(triggered_by="RUN_1")
        self.assertTrue(run1.is_current)

        run2 = build_snapshots(triggered_by="RUN_2")
        self.assertTrue(run2.is_current)

        run1.refresh_from_db()
        self.assertFalse(run1.is_current)
        self.assertEqual(AuditRun.objects.filter(is_current=True).count(), 1)

    def test_05_endpoints_return_from_snapshot_assert_queries(self):
        """5. Endpoints /stats and /jobs/summary return from snapshot with assertNumQueries <= 2."""
        build_snapshots(triggered_by="QUERY_TEST")

        # Clear memory cache to test direct DB query count from snapshot
        cache.clear()
        with self.assertNumQueries(1):  # Exactly 1 query to fetch StatsSnapshot
            res = self.client.get('/stats')
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data['jobs_tracked'], 2)
            self.assertIn('data_as_of', data)

        cache.clear()
        with self.assertNumQueries(1):  # Exactly 1 query to fetch JobSummarySnapshot
            res = self.client.get('/jobs/summary')
            self.assertEqual(res.status_code, 200)
            s_data = res.json()
            self.assertEqual(s_data['total_roles'], 2)
            self.assertIn('data_as_of', s_data)

    def test_06_edit_event_updates_metrics_immediately(self):
        """6. Edit event recomputes CompanyMetrics and global snapshot immediately without waiting for audit."""
        build_snapshots(triggered_by="EVENT_TEST")
        current_run = AuditRun.objects.get(is_current=True)

        cm = CompanyMetrics.objects.get(audit_run=current_run, company=self.company)
        self.assertEqual(cm.active_jobs_count, 2)

        # Admin creates or edits a new job
        Job.objects.create(
            job_id="TEST-JOB-NEW",
            company=self.company,
            job_title="Senior Impact Analyst",
            application_url="https://testcorp.example.com/jobs/3",
            source_url="https://testcorp.example.com/jobs/3",
            retrieved_at=timezone.now(),
            evidence_text="Senior Analyst role verified on portal",
            status="ACTIVE",
            verification_status="PUBLISHED",
            work_mode="On-site",
            link_quality="DIRECT"
        )

        # CompanyMetrics and snapshot must reflect the new job immediately
        cm.refresh_from_db()
        self.assertEqual(cm.active_jobs_count, 3)

        stats_snap = StatsSnapshot.objects.get(audit_run=current_run)
        self.assertEqual(stats_snap.payload['jobs_tracked'], 3)

    def test_07_envelope_unchanged(self):
        """7. Pagination envelope remains strictly compliant ({items, total, page, page_size, total_pages, has_next, has_prev})."""
        build_snapshots(triggered_by="ENVELOPE_TEST")

        res = self.client.get('/jobs?page=1&page_size=12')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        expected_keys = {"items", "total", "page", "page_size", "total_pages", "has_next", "has_prev"}
        self.assertTrue(expected_keys.issubset(data.keys()))
        self.assertIsInstance(data['items'], list)

    def test_08_defective_flag_parity_with_old_logic(self):
        """8. Prove 100% parity between stored is_defective flag and old in-memory is_defective_job_record logic."""
        recompute_job_defective_flags(force=True)
        all_jobs = list(Job.objects.all())
        for job in all_jobs:
            old_result = is_defective_job_record(job.job_title, job.application_url, job.source_url)
            self.assertEqual(
                job.is_defective, old_result,
                f"Mismatch on Job #{job.job_row_id} ('{job.job_title}'): stored={job.is_defective}, old={old_result}"
            )

    def test_09_stats_header_total_equals_jobs_list_total(self):
        """9. /stats jobs_tracked exactly equals /jobs?page=1 total count for the same filters."""
        build_snapshots(triggered_by="PARITY_TEST")

        stats_res = self.client.get('/stats').json()
        jobs_res = self.client.get('/jobs?page=1&page_size=12').json()

        self.assertEqual(stats_res['jobs_tracked'], jobs_res['total'])

    def test_10_validation_failures_block_publishing(self):
        """10. Validation checks detect corrupt data (e.g. negative values or mismatched sums) and block publishing."""
        # Intentionally craft a scenario with negative counts
        from modules.admin_panel import snapshot_service
        orig_stats = snapshot_service.compute_live_stats
        try:
            snapshot_service.compute_live_stats = lambda: {
                **orig_stats(),
                'jobs_tracked': -5  # Negative count
            }
            audit_run = build_snapshots(triggered_by="CORRUPT_TEST")
            self.assertEqual(audit_run.status, "FAILED")
            self.assertFalse(audit_run.is_current)
        finally:
            snapshot_service.compute_live_stats = orig_stats

    def test_11_reconcile_detects_deliberately_corrupted_snapshot(self):
        """11. reconcile_snapshots() accurately detects a corrupted figure and returns all_matched=False."""
        audit_run = build_snapshots(triggered_by="RECONCILE_TEST")

        # Corrupt the snapshot payload deliberately
        snap = StatsSnapshot.objects.get(audit_run=audit_run)
        snap.payload['jobs_tracked'] = 999999  # deliberate falsification
        snap.save()

        matched, results = reconcile_snapshots(audit_run)
        self.assertFalse(matched)

        # Verify discrepancy was recorded
        job_result = next((r for r in results if r['metric'] == 'jobs_tracked'), None)
        self.assertIsNotNone(job_result)
        self.assertFalse(job_result['match'])
        self.assertNotEqual(job_result['diff'], 0)

    def test_12_fallback_runs_only_when_no_snapshot_exists(self):
        """12. Fallback runs live when no snapshot exists; when a snapshot exists, fallback never runs."""
        AuditRun.objects.all().delete()
        cache.clear()

        # No snapshot exists: fallback provides live data without error
        data, is_stale, run_id, as_of = get_current_stats_snapshot()
        self.assertEqual(as_of, "Live")
        self.assertIsNone(run_id)
        self.assertEqual(data['jobs_tracked'], 2)

        # Now build a snapshot
        build_snapshots(triggered_by="FALLBACK_TEST")
        cache.clear()

        # Snapshot exists: returns snapshot data and real audit run id
        data2, is_stale2, run_id2, as_of2 = get_current_stats_snapshot()
        self.assertNotEqual(as_of2, "Live")
        self.assertIsNotNone(run_id2)

    def test_13_coverage_response_shape_and_headers(self):
        """13. Coverage response shape is unchanged list of dicts with data_as_of and audit_run_id."""
        build_snapshots(triggered_by="TEST_COV_SHAPE")
        cache.clear()
        res = self.client.get('/api/coverage')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.has_header('X-Data-As-Of'))
        self.assertTrue(res.has_header('X-Audit-Run-Id'))
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        required_fields = {
            'company_id', 'name', 'nse_symbol', 'website', 'careers_url', 'ats',
            'jobs_found', 'jobs_published', 'direct_link_percentage', 'csr_records',
            'crawl_status', 'last_verified', 'explanation', 'data_as_of', 'audit_run_id'
        }
        for item in data:
            self.assertTrue(required_fields.issubset(item.keys()))

    def test_14_coverage_at_most_2_queries(self):
        """14. Coverage endpoint executes at most 2 queries on cold cache."""
        build_snapshots(triggered_by="TEST_COV_QUERIES")
        cache.clear()
        with self.assertNumQueries(2):
            res = self.client.get('/api/coverage')
            self.assertEqual(res.status_code, 200)

    def test_15_coverage_totals_equal_stats_totals(self):
        """15. Coverage jobs sum and CSR sum equal /stats totals."""
        build_snapshots(triggered_by="TEST_COV_TOTALS")
        cache.clear()
        cov_res = self.client.get('/api/coverage').json()
        stats_res = self.client.get('/stats').json()

        cov_jobs_sum = sum(c['jobs_published'] for c in cov_res)
        cov_csr_sum = sum(c['csr_records'] for c in cov_res)

        self.assertEqual(cov_jobs_sum, stats_res['jobs_tracked'])
        self.assertEqual(cov_csr_sum, stats_res['csr_projects'])

    def test_16_coverage_fallback_runs_only_when_no_snapshot(self):
        """16. Coverage fallback runs only when no snapshot exists; does not run when snapshot exists."""
        from modules.admin_panel.snapshot_service import get_current_coverage_snapshot
        AuditRun.objects.all().delete()
        cache.clear()

        # No snapshot exists: fallback computes live without error
        rows, is_stale, run_id, as_of = get_current_coverage_snapshot()
        self.assertEqual(as_of, "Live")
        self.assertIsNone(run_id)
        self.assertEqual(len(rows), 2)

        # Build snapshot
        audit_run = build_snapshots(triggered_by="TEST_COV_FB")
        cache.clear()

        # Snapshot exists: returns snapshot data and audit_run id
        rows2, is_stale2, run_id2, as_of2 = get_current_coverage_snapshot()
        self.assertNotEqual(as_of2, "Live")
        self.assertEqual(run_id2, audit_run.id)

    def test_17_coverage_old_vs_new_parity_fixture(self):
        """17. Snapshot coverage rows perfectly match old live calculation on fixture data."""
        from modules.admin_panel.snapshot_service import _compute_live_coverage_rows_fallback, get_current_coverage_snapshot
        build_snapshots(triggered_by="TEST_COV_PARITY")
        cache.clear()

        old_rows = _compute_live_coverage_rows_fallback()
        new_rows, _, _, _ = get_current_coverage_snapshot()

        old_by_id = {r['company_id']: r for r in old_rows}
        new_by_id = {r['company_id']: r for r in new_rows}

        fields_to_check = [
            'company_id', 'name', 'nse_symbol', 'website', 'careers_url', 'ats',
            'jobs_found', 'jobs_published', 'direct_link_percentage', 'csr_records',
            'crawl_status', 'last_verified', 'explanation'
        ]
        for cid, old_item in old_by_id.items():
            new_item = new_by_id[cid]
            for f in fields_to_check:
                self.assertEqual(old_item[f], new_item[f], f"Mismatch on field {f} for company {cid}")

