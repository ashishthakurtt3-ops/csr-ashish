import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import unittest
from modules.crawler_engine.adapters.base import ExtractedJobRecord
from modules.crawler_engine.adapters.workday import WorkdayAdapter
from modules.crawler_engine.adapters.darwinbox import DarwinboxAdapter
from modules.crawler_engine.adapters import resolve_adapter_for_url
from modules.crawler_engine.evidence_verifier import IndependentEvidenceVerifier
from modules.crawler_engine.staging_manager import CandidateStagingManager
from modules.crawler_engine.pdf_extractor import PDFReportExtractor


class TestHighAccuracyPipeline(unittest.TestCase):

    def test_workday_adapter_matching(self):
        adapter = resolve_adapter_for_url("https://tcs.myworkdayjobs.com/en-US/Careers")
        self.assertIsInstance(adapter, WorkdayAdapter)
        self.assertEqual(adapter.platform_name, "Workday")

    def test_darwinbox_adapter_matching(self):
        adapter = resolve_adapter_for_url("https://kotak.darwinbox.in/ms/candidate/careers")
        self.assertIsInstance(adapter, DarwinboxAdapter)
        self.assertEqual(adapter.platform_name, "Darwinbox")

    def test_workday_json_extraction(self):
        adapter = WorkdayAdapter()
        mock_payload = '''{
            "jobPostings": [
                {
                    "title": "Senior Python Backend Engineer",
                    "externalPath": "/job/R102394",
                    "locationsText": "Mumbai, Maharashtra, India",
                    "postedOn": "Posted 2 Days Ago"
                }
            ]
        }'''
        jobs = adapter.extract_jobs("COMP_TOP200_001", "https://example.myworkdayjobs.com/careers", mock_payload, "json")
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].job_title, "Senior Python Backend Engineer")
        self.assertEqual(jobs[0].location_raw, "Mumbai, Maharashtra, India")
        self.assertEqual(jobs[0].ats_platform, "Workday")

    def test_job_evidence_verifier_rejects_generic_nav(self):
        candidate = {
            "job_title": "Careers",
            "application_url": "https://example.com/careers"
        }
        valid, decision, _ = IndependentEvidenceVerifier.verify_job_candidate(candidate, "Welcome to our careers page.")
        self.assertFalse(valid)
        self.assertEqual(decision, "NAV_LABEL_NOT_JOB")

    def test_job_evidence_verifier_accepts_valid_job(self):
        page_text = "We are currently hiring a Lead Data Architect in Bengaluru. Click here to apply."
        candidate = {
            "job_title": "Lead Data Architect",
            "application_url": "https://example.com/jobs/apply/123"
        }
        valid, decision, _ = IndependentEvidenceVerifier.verify_job_candidate(candidate, page_text)
        self.assertTrue(valid)
        self.assertEqual(decision, "VERIFIED")

    def test_csr_verifier_rejects_policy_charters(self):
        candidate = {
            "project_name": "Corporate CSR Policy Document 2024",
            "evidence_text": "This is our statutory policy document approved by the board of directors."
        }
        valid, decision, _ = IndependentEvidenceVerifier.verify_csr_candidate(candidate, "This is our statutory policy document approved by the board of directors.")
        self.assertFalse(valid)
        self.assertEqual(decision, "POLICY_OR_GOVERNANCE_DOCUMENT")

    def test_csr_verifier_rejects_broad_thematic_focus_areas(self):
        thematic_areas = [
            "Health", "Healthcare", "Education", "Sports", "Women Empowerment",
            "Arts, Culture & Heritage", "Rural Transformation", "Disaster Management"
        ]
        source_text = "Our key focus areas include Health, Education, Sports and Women Empowerment across rural communities."
        for area in thematic_areas:
            candidate = {
                "project_name": area,
                "evidence_text": f"Focus area heading for {area} within company foundation programs."
            }
            valid, decision, details = IndependentEvidenceVerifier.verify_csr_candidate(candidate, source_text)
            self.assertFalse(valid, f"Expected {area} to be rejected as a broad focus area")
            self.assertEqual(decision, "BROAD_FOCUS_AREA_NOT_PROJECT")

    def test_csr_verifier_rejects_generic_synthetic_titles(self):
        synthetic_titles = [
            "Reliance Industries Community Development Program",
            "Company Social Responsibility Initiative",
            "Annual CSR Program",
            "Corporate Sustainability Project"
        ]
        source_text = "The company conducted its community development program across multiple districts."
        for title in synthetic_titles:
            candidate = {
                "project_name": title,
                "evidence_text": "The company conducted its community development program across multiple districts."
            }
            valid, decision, _ = IndependentEvidenceVerifier.verify_csr_candidate(candidate, source_text)
            self.assertFalse(valid, f"Expected {title} to be rejected as generic/synthetic title")
            self.assertEqual(decision, "GENERIC_SYNTHETIC_TITLE")

    def test_csr_verifier_rejects_general_sustainability_statements(self):
        sustainability_statements = [
            "Sustainability Overview",
            "Commitment to Sustainability",
            "Net Zero Strategy 2035",
            "Carbon Neutral Roadmap"
        ]
        source_text = "Our sustainability overview highlights our goal to reach net zero emissions by 2035."
        for stmt in sustainability_statements:
            candidate = {
                "project_name": stmt,
                "evidence_text": "Our sustainability overview highlights our goal to reach net zero emissions by 2035."
            }
            valid, decision, _ = IndependentEvidenceVerifier.verify_csr_candidate(candidate, source_text)
            self.assertFalse(valid, f"Expected {stmt} to be rejected as general sustainability statement")
            self.assertEqual(decision, "GENERAL_SUSTAINABILITY_STATEMENT")

    def test_csr_verifier_accepts_genuine_identifiable_project(self):
        source_text = "Under Project Drishti, Reliance Foundation has conducted over 20,000 corneal transplants for visually impaired patients."
        candidate = {
            "project_name": "Project Drishti - Corneal Transplants",
            "evidence_text": "Under Project Drishti, Reliance Foundation has conducted over 20,000 corneal transplants for visually impaired patients.",
            "category": "Item (i) - Health, Sanitation & Poverty"
        }
        valid, decision, details = IndependentEvidenceVerifier.verify_csr_candidate(candidate, source_text)
        self.assertTrue(valid)
        self.assertEqual(decision, "VERIFIED")
        self.assertTrue(details.get("source_match"))

    def test_csr_verifier_confirms_verbatim_quote(self):
        source_text = "Under Project Swachh Jal, ImpactBridge provided clean drinking water filtration systems to 15 rural villages in Pune district."
        candidate = {
            "project_name": "Project Swachh Jal",
            "evidence_text": "Under Project Swachh Jal, ImpactBridge provided clean drinking water filtration systems to 15 rural villages in Pune district.",
            "category": "Item (i) - Health, Sanitation & Poverty"
        }
        valid, decision, details = IndependentEvidenceVerifier.verify_csr_candidate(candidate, source_text)
        self.assertTrue(valid)
        self.assertEqual(decision, "VERIFIED")
        self.assertTrue(details.get("source_match"))

    def test_staging_dry_run_does_not_mutate_db(self):
        candidate = {
            "job_title": "Staff Cloud Engineer",
            "application_url": "https://example.com/jobs/999",
            "detail_url": "https://example.com/jobs/999"
        }
        res = CandidateStagingManager.stage_and_publish_job("COMP_TOP200_001", candidate, "Hiring Staff Cloud Engineer now.", dry_run=True)
        self.assertEqual(res["action_taken"], "STAGED_ONLY")
        self.assertTrue(res["is_valid"])


if __name__ == '__main__':
    unittest.main()

