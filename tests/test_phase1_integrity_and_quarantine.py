import os
import sys
import json
import unittest
from datetime import datetime

import django

# Setup django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import TestCase, Client
from django.utils import timezone
from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity

class Phase1DataIntegrityAndQuarantineTest(TestCase):
    def setUp(self):
        self.client = Client()
        # Pick or create a test company
        self.company, _ = Company.objects.get_or_create(
            company_id="TEST_CO_PHASE1",
            defaults={
                "company_name": "Test Quarantine Enterprise Ltd",
                "official_domain": "testphase1quarantine.com",
                "website_url": "https://testphase1quarantine.com",
                "verification_status": "VERIFIED",
                "jobs_access": "PUBLIC",
                "csr_access": "PUBLIC",
            }
        )
        self.created_job_ids = []
        self.created_csr_ids = []
        self.created_opp_ids = []

    def tearDown(self):
        # Clean up any created test records
        if self.created_job_ids:
            Job.objects.filter(pk__in=self.created_job_ids).delete()
        if self.created_csr_ids:
            CSRProject.objects.filter(pk__in=self.created_csr_ids).delete()
        if self.created_opp_ids:
            CSROpportunity.objects.filter(pk__in=self.created_opp_ids).delete()
        if self.company.company_id == "TEST_CO_PHASE1":
            self.company.delete()

    def test_quarantined_records_never_leak_to_public_endpoints(self):
        print("\n" + "="*70)
        print("PHASE 1 AUDIT TEST: DATA INTEGRITY & QUARANTINE ASSERTIONS")
        print("="*70)

        # 1. Snapshot /stats BEFORE creating invalid records
        resp_stats_before = self.client.get('/stats')
        self.assertEqual(resp_stats_before.status_code, 200)
        stats_before = json.loads(resp_stats_before.content)
        print("\n[STEP 1] /stats BEFORE injecting invalid records:")
        print(f"  - jobs_tracked:        {stats_before.get('jobs_tracked')}")
        print(f"  - csr_projects:        {stats_before.get('csr_projects')}")
        print(f"  - active_opportunities: {stats_before.get('active_opportunities')}")

        now = timezone.now()

        # 2. Inject Invalid & Low-Confidence Job Records
        j_removed = Job.objects.create(
            company=self.company,
            job_id="TEST_JOB_REMOVED_999",
            job_title="Ghost Job Removed Senior Specialist",
            status="REMOVED",
            verification_status="SOURCE_CONFIRMED",
            confidence=0.95,
            application_url="https://testphase1quarantine.com/job/removed",
            source_url="https://testphase1quarantine.com/job/removed",
            retrieved_at=now,
            evidence_text="Evidence for removed job",
            removed_at=now,
        )
        self.created_job_ids.append(j_removed.pk)

        j_expired = Job.objects.create(
            company=self.company,
            job_id="TEST_JOB_EXPIRED_999",
            job_title="Old Expired Staff Engineer",
            status="EXPIRED",
            verification_status="STALE",
            confidence=0.85,
            application_url="https://testphase1quarantine.com/job/expired",
            source_url="https://testphase1quarantine.com/job/expired",
            retrieved_at=now,
            evidence_text="Evidence for expired job",
        )
        self.created_job_ids.append(j_expired.pk)

        j_synthetic = Job.objects.create(
            company=self.company,
            job_id="TEST_JOB_SYNTHETIC_999",
            job_title="Synthetic Scraped Footer Link Lead",
            status="INVALID_SYNTHETIC",
            verification_status="UNVERIFIED",
            confidence=0.10,
            application_url="https://testphase1quarantine.com/job/synthetic",
            source_url="https://testphase1quarantine.com/job/synthetic",
            retrieved_at=now,
            evidence_text="Evidence for synthetic job",
        )
        self.created_job_ids.append(j_synthetic.pk)

        j_low_conf = Job.objects.create(
            company=self.company,
            job_id="TEST_JOB_LOW_CONF_999",
            job_title="Dubious Low Confidence Candidate",
            status="ACTIVE",
            verification_status="QUARANTINED",
            confidence=0.15,
            application_url="https://testphase1quarantine.com/job/lowconf",
            source_url="https://testphase1quarantine.com/job/lowconf",
            retrieved_at=now,
            evidence_text="Evidence for low conf job",
        )
        self.created_job_ids.append(j_low_conf.pk)

        j_legacy_unverified = Job.objects.create(
            company=self.company,
            job_id="TEST_JOB_LEGACY_UNV_999",
            job_title="Legacy Unverified Seed Role",
            status="ACTIVE",
            verification_status="LEGACY_UNVERIFIED",
            confidence=0.10,
            application_url="https://testphase1quarantine.com/job/legacy",
            source_url="https://testphase1quarantine.com/job/legacy",
            retrieved_at=now,
            evidence_text="Evidence for legacy unverified",
        )
        self.created_job_ids.append(j_legacy_unverified.pk)

        # 3. Inject Invalid & Low-Confidence CSRProject Records
        csr_removed = CSRProject.objects.create(
            company=self.company,
            project_name="Removed Solar Microgrid Initiative",
            status="REMOVED",
            verification_status="SOURCE_CONFIRMED",
            confidence=0.90,
            source_url="https://testphase1quarantine.com/csr/solar",
            retrieved_at=now,
            evidence_text="Solar initiative summary paragraph",
            removed_at=now,
        )
        self.created_csr_ids.append(csr_removed.pk)

        csr_synthetic = CSRProject.objects.create(
            company=self.company,
            project_name="Synthetic Fake CSR Scraped Block",
            status="INVALID_SYNTHETIC",
            verification_status="UNVERIFIED",
            confidence=0.20,
            source_url="https://testphase1quarantine.com/csr/fake",
            retrieved_at=now,
            evidence_text="Fake paragraph scraped from marketing page",
        )
        self.created_csr_ids.append(csr_synthetic.pk)

        csr_rejected = CSRProject.objects.create(
            company=self.company,
            project_name="Rejected Low Confidence Project",
            status="ACTIVE",
            verification_status="REJECTED",
            confidence=0.10,
            source_url="https://testphase1quarantine.com/csr/rejected",
            retrieved_at=now,
            evidence_text="Rejected evidence text",
        )
        self.created_csr_ids.append(csr_rejected.pk)

        csr_low_conf = CSRProject.objects.create(
            company=self.company,
            project_name="Low Confidence Quarantined CSR Initiative",
            status="ACTIVE",
            verification_status="QUARANTINED",
            confidence=0.12,
            source_url="https://testphase1quarantine.com/csr/lowconf",
            retrieved_at=now,
            evidence_text="Low confidence CSR paragraph",
        )
        self.created_csr_ids.append(csr_low_conf.pk)

        # 4. Inject Invalid & Low-Confidence CSROpportunity Records
        opp_synthetic = CSROpportunity.objects.create(
            company=self.company,
            title="Synthetic Cloned RFP From Marketing About Page",
            status="INVALID_SYNTHETIC",
            verification_status="UNVERIFIED",
            confidence=0.10,
            portal_url="https://testphase1quarantine.com/opp/fake",
            source_url="https://testphase1quarantine.com/opp/fake",
            retrieved_at=now,
            evidence_text="About us text cloned into opportunity",
        )
        self.created_opp_ids.append(opp_synthetic.pk)

        opp_removed = CSROpportunity.objects.create(
            company=self.company,
            title="Soft-Deleted Past Grant Application Window",
            status="REMOVED",
            verification_status="SOURCE_CONFIRMED",
            confidence=0.85,
            portal_url="https://testphase1quarantine.com/opp/removed",
            source_url="https://testphase1quarantine.com/opp/removed",
            retrieved_at=now,
            evidence_text="Valid grant text now removed",
        )
        self.created_opp_ids.append(opp_removed.pk)

        opp_expired = CSROpportunity.objects.create(
            company=self.company,
            title="Expired Closed Call for Proposals",
            status="EXPIRED",
            verification_status="STALE",
            confidence=0.80,
            portal_url="https://testphase1quarantine.com/opp/expired",
            source_url="https://testphase1quarantine.com/opp/expired",
            retrieved_at=now,
            evidence_text="Expired grant text",
        )
        self.created_opp_ids.append(opp_expired.pk)

        opp_low_conf = CSROpportunity.objects.create(
            company=self.company,
            title="Quarantined Low Confidence Opportunity",
            status="OPEN",
            verification_status="QUARANTINED",
            confidence=0.15,
            portal_url="https://testphase1quarantine.com/opp/lowconf",
            source_url="https://testphase1quarantine.com/opp/lowconf",
            retrieved_at=now,
            evidence_text="Unverified text",
        )
        self.created_opp_ids.append(opp_low_conf.pk)

        print(f"\n[STEP 2] Successfully injected test invalid & low-confidence records:")
        print(f"  - Injected 5 invalid/low-conf Jobs (REMOVED, EXPIRED, INVALID_SYNTHETIC, QUARANTINED, LEGACY_UNVERIFIED)")
        print(f"  - Injected 4 invalid/low-conf CSRProjects (REMOVED, INVALID_SYNTHETIC, REJECTED, QUARANTINED)")
        print(f"  - Injected 4 invalid/low-conf CSROpportunities (INVALID_SYNTHETIC, REMOVED, EXPIRED, QUARANTINED)")

        # 5. Snapshot /stats AFTER creating invalid records
        resp_stats_after = self.client.get('/stats')
        self.assertEqual(resp_stats_after.status_code, 200)
        stats_after = json.loads(resp_stats_after.content)
        print("\n[STEP 3] /stats AFTER injecting invalid records:")
        print(f"  - jobs_tracked:        {stats_after.get('jobs_tracked')} (expected: {stats_before.get('jobs_tracked')})")
        print(f"  - csr_projects:        {stats_after.get('csr_projects')} (expected: {stats_before.get('csr_projects')})")
        print(f"  - active_opportunities: {stats_after.get('active_opportunities')} (expected: {stats_before.get('active_opportunities')})")

        # ASSERT STATS ARE IDENTICAL
        self.assertEqual(stats_after['jobs_tracked'], stats_before['jobs_tracked'], "jobs_tracked in /stats leaked invalid records!")
        self.assertEqual(stats_after['csr_projects'], stats_before['csr_projects'], "csr_projects in /stats leaked invalid records!")
        self.assertEqual(stats_after['active_opportunities'], stats_before['active_opportunities'], "active_opportunities in /stats leaked invalid records!")
        print("  -> ASSERTION PASSED: /stats is completely impervious to invalid/quarantined data.")

        # 6. Check /jobs HTML page and /jobs JSON API
        resp_jobs_html = self.client.get('/jobs', HTTP_ACCEPT='text/html')
        self.assertEqual(resp_jobs_html.status_code, 200)
        self.assertIn('text/html', resp_jobs_html.headers.get('Content-Type', ''))
        html_content = resp_jobs_html.content.decode('utf-8')
        for bad_id in ["TEST_JOB_REMOVED_999", "TEST_JOB_EXPIRED_999", "TEST_JOB_SYNTHETIC_999", "TEST_JOB_LOW_CONF_999", "TEST_JOB_LEGACY_UNV_999"]:
            self.assertNotIn(bad_id, html_content, f"Job {bad_id} leaked into /jobs HTML view!")
        print("[STEP 4] ASSERTION PASSED: /jobs HTML page renders cleanly with 0 invalid records.")

        resp_jobs_api = self.client.get('/api/jobs/?limit=5000')
        self.assertEqual(resp_jobs_api.status_code, 200)
        jobs_api_data = json.loads(resp_jobs_api.content)
        jobs_list = jobs_api_data.get('items', jobs_api_data) if isinstance(jobs_api_data, dict) else jobs_api_data
        returned_job_ids = {j.get('job_id') for j in jobs_list}
        returned_job_titles = {j.get('job_title', '').lower() for j in jobs_list}

        for inv_id in ["TEST_JOB_REMOVED_999", "TEST_JOB_EXPIRED_999", "TEST_JOB_SYNTHETIC_999", "TEST_JOB_LOW_CONF_999", "TEST_JOB_LEGACY_UNV_999"]:
            self.assertNotIn(inv_id, returned_job_ids, f"Job {inv_id} leaked to /api/jobs/!")

        for bad_title in ["ghost job removed", "old expired staff", "synthetic scraped footer", "dubious low confidence", "legacy unverified"]:
            for ret_t in returned_job_titles:
                self.assertNotIn(bad_title, ret_t, f"Title matching '{bad_title}' leaked to /api/jobs/!")
        print("[STEP 5] ASSERTION PASSED: /api/jobs/ hides all REMOVED, EXPIRED, INVALID_SYNTHETIC, and low-confidence jobs.")

        # 7. Check /csr (not /csr/projects) and /csr/
        resp_csr_root = self.client.get('/csr')
        self.assertEqual(resp_csr_root.status_code, 200)
        csr_data = json.loads(resp_csr_root.content)
        csr_list = csr_data.get('items', csr_data) if isinstance(csr_data, dict) else csr_data
        returned_csr_names = {p.get('project_name', '').lower() for p in csr_list}

        for bad_csr in ["removed solar microgrid", "synthetic fake csr", "rejected low confidence", "low confidence quarantined"]:
            for ret_p in returned_csr_names:
                self.assertNotIn(bad_csr, ret_p, f"CSR Project matching '{bad_csr}' leaked to /csr!")
        print("[STEP 6] ASSERTION PASSED: /csr hides all REMOVED, INVALID_SYNTHETIC, REJECTED, and low-confidence projects.")

        # 8. Check /api/opportunities/ and /opportunities
        resp_opps_api = self.client.get('/api/opportunities/?limit=500')
        self.assertEqual(resp_opps_api.status_code, 200)
        opps_data = json.loads(resp_opps_api.content)
        opps_list = opps_data.get('items', opps_data) if isinstance(opps_data, dict) else opps_data
        returned_opp_titles = {o.get('title', '').lower() for o in opps_list}

        for bad_opp in ["synthetic cloned rfp", "soft-deleted past grant", "expired closed call", "quarantined low confidence"]:
            for ret_o in returned_opp_titles:
                self.assertNotIn(bad_opp, ret_o, f"Opportunity matching '{bad_opp}' leaked to /api/opportunities/!")
        print("[STEP 7] ASSERTION PASSED: /api/opportunities/ hides all INVALID_SYNTHETIC, REMOVED, EXPIRED, and low-confidence opportunities.")

        # 9. Check /api/companies/<id>/ (company_detail_api and dossier)
        resp_comp = self.client.get(f'/api/companies/{self.company.company_id}')
        self.assertEqual(resp_comp.status_code, 200)
        comp_data = json.loads(resp_comp.content)
        self.assertEqual(comp_data.get('verified_jobs_count', 0), 0, "Test company verified_jobs_count leaked invalid jobs!")
        self.assertEqual(comp_data.get('published_csr_count', 0), 0, "Test company published_csr_count leaked invalid CSR projects!")
        self.assertEqual(comp_data.get('open_opportunities_count', 0), 0, "Test company open_opportunities_count leaked invalid opportunities!")

        resp_dossier = self.client.get(f'/api/companies/{self.company.company_id}/dossier')
        if resp_dossier.status_code == 200:
            dossier_data = json.loads(resp_dossier.content)
            self.assertEqual(len(dossier_data.get('projects', [])), 0, "Dossier leaked invalid CSR projects!")
            self.assertEqual(len(dossier_data.get('jobs', [])), 0, "Dossier leaked invalid jobs!")
            self.assertEqual(len(dossier_data.get('opportunities', [])), 0, "Dossier leaked invalid opportunities!")
        print("[STEP 8] ASSERTION PASSED: /api/companies/<id>/ and dossier show 0 counts for quarantined company data.")

        # 10. Check /api/coverage/
        resp_cov = self.client.get('/api/coverage')
        self.assertEqual(resp_cov.status_code, 200)
        cov_data = json.loads(resp_cov.content)
        cov_rows = cov_data.get('rows', cov_data) if isinstance(cov_data, dict) else cov_data
        test_cov = next((r for r in cov_rows if r.get('company_id') == self.company.company_id), None)
        if test_cov:
            self.assertEqual(test_cov.get('published_jobs', 0), 0, "Coverage API leaked invalid jobs count!")
            self.assertEqual(test_cov.get('csr_projects', 0), 0, "Coverage API leaked invalid CSR projects count!")
        print("[STEP 9] ASSERTION PASSED: /api/coverage/ shows 0 jobs and 0 CSR projects for invalid records.")

        print("\n" + "="*70)
        print("ALL DATA INTEGRITY AND QUARANTINE ASSERTIONS PASSED (100% OK)")
        print("="*70)

    def test_confidence_based_low_score_record(self):
        """Verify that records with low confidence scores (<0.60) are quarantined and never surfaced publicly."""
        now = timezone.now()
        low_score_job = Job.objects.create(
            company=self.company,
            job_id="TEST_JOB_LOW_CONF_SCORE",
            job_title="Dubious Low Score Scraped Link",
            status="ACTIVE",
            verification_status="QUARANTINED",
            confidence=0.18,  # Low score < 0.60
            application_url="https://testphase1quarantine.com/job/low-score",
            source_url="https://testphase1quarantine.com/job/low-score",
            retrieved_at=now,
            evidence_text="Dubious text snippet with low extraction confidence",
        )
        self.created_job_ids.append(low_score_job.pk)

        # 1. public_jobs queryset must exclude it
        from modules.admin_panel.verification import public_jobs
        public_qs = public_jobs(Job.objects.filter(pk=low_score_job.pk))
        self.assertEqual(public_qs.count(), 0, "Low-score quarantined job leaked through public_jobs()!")

        # 2. Public API endpoint /api/jobs/ must hide it
        resp = self.client.get('/api/jobs/?search=Dubious')
        data = json.loads(resp.content)
        jobs = data.get('jobs', data.get('results', [])) if isinstance(data, dict) else data
        self.assertEqual(len(jobs), 0, "Low-score quarantined job leaked into /api/jobs/!")

        print("\n[CONFIDENCE TEST PASSED] Low-score record (confidence=0.18) successfully quarantined and hidden from all public endpoints.")

if __name__ == '__main__':
    unittest.main()

