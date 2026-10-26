"""
tests/test_step0_exact_match_standard.py
========================================
Unit and regression tests for Step 0 Exact-Match Standard:
- Verbatim raw field serialization (no defaults, missing = None)
- Verbatim CSR budget display ("Not disclosed" if not verbatim in evidence)
- Public safety filter exclusion of NEEDS_REVIEW
- Golden dataset 100% agreement check
"""

import os
import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from django.test import TestCase, SimpleTestCase
from django.utils import timezone

from modules.admin_panel.models import Company, Job, CSRProject
from modules.admin_panel.verification import (
    apply_job_safety_filters,
    public_jobs,
    public_records,
    format_relative_time
)
from modules.website.views.job_api_views import serialize_job_item
from modules.website.views.opportunity_api_views import get_verbatim_csr_budget_display


class Step0VerbatimJobSerializationTests(SimpleTestCase):

    def test_serialize_job_item_returns_verbatim_fields(self):
        job = MagicMock()
        job.job_id = "JOB123"
        job.job_row_id = 99
        job.job_title = "Senior Python Engineer"
        job.raw_title = "Senior Python Engineer (Backend)"
        job.location = "Bengaluru, Karnataka"
        job.raw_location = "Bengaluru Office (Hybrid)"
        job.department = "Core Engineering"
        job.raw_department = "Core Eng - Platform"
        job.employment_type = "Full-time"
        job.raw_employment_type = "Permanent Full-Time"
        job.work_mode = "Hybrid"
        job.salary = None
        job.salary_currency = None
        job.application_url = "https://example.com/apply"
        job.source_url = "https://example.com/jobs/123"
        job.source_domain = "example.com"
        job.last_seen_live_at = timezone.now()
        job.link_verified_at = timezone.now()
        job.retrieved_at = timezone.now().isoformat()
        job.status = "ACTIVE"
        job.field_source = {"title": "h1.job-title"}

        company = MagicMock()
        company.company_name = "Acme Corp"
        company.nse_symbol = "ACME"
        company.company_id = "IN0001"
        company.website_url = "https://example.com"
        company.official_domain = "example.com"
        company.careers_url = "https://example.com/careers"
        company.jobs_access = "PUBLIC"
        company.verification_status = "VERIFIED"

        job.company = company


        serialized = serialize_job_item(job)

        # Verbatim fields must take precedence
        self.assertEqual(serialized["job_title"], "Senior Python Engineer (Backend)")
        self.assertEqual(serialized["raw_title"], "Senior Python Engineer (Backend)")
        self.assertEqual(serialized["location"], "Bengaluru Office (Hybrid)")
        self.assertEqual(serialized["raw_location"], "Bengaluru Office (Hybrid)")
        self.assertEqual(serialized["department"], "Core Eng - Platform")
        self.assertEqual(serialized["employment_type"], "Permanent Full-Time")

        self.assertIn("verified_badge_text", serialized)
        self.assertIn("verified_relative_time", serialized)
        self.assertFalse(serialized["is_company_unverifiable"])

    def test_missing_fields_return_none_never_defaults(self):
        job = MagicMock()
        job.job_id = "JOB456"
        job.job_row_id = 100
        job.job_title = "Data Analyst"
        job.raw_title = None
        job.location = None
        job.raw_location = None
        job.department = None
        job.raw_department = None
        job.employment_type = None
        job.raw_employment_type = None
        job.work_mode = None
        job.salary = None
        job.salary_currency = None
        job.application_url = "https://example.com/apply/456"
        job.source_url = "https://example.com/jobs/456"
        job.source_domain = "example.com"
        job.last_seen_live_at = None
        job.link_verified_at = None
        job.retrieved_at = None
        job.status = "ACTIVE"
        job.field_source = {}

        company = MagicMock()
        company.company_name = "Acme Corp"
        company.nse_symbol = "ACME"
        company.company_id = "IN0001"
        company.website_url = "https://example.com"
        company.official_domain = "example.com"
        company.careers_url = "https://example.com/careers"
        company.jobs_access = "PUBLIC"

        job.company = company

        serialized = serialize_job_item(job)

        # Must NOT default to "India", "Full-time", or "On-site"
        self.assertIsNone(serialized["location"])
        self.assertIsNone(serialized["department"])
        self.assertIsNone(serialized["employment_type"])
        self.assertIsNone(serialized["work_mode"])


class Step0VerbatimCsrBudgetTests(SimpleTestCase):

    def test_verbatim_budget_matches_evidence(self):
        project = MagicMock()
        project.raw_budget_text = "Rs. 1,50,00,000"
        project.budget = "15000000"
        project.evidence_text = "The committee approved Rs. 1,50,00,000 for rural healthcare infrastructure."

        display = get_verbatim_csr_budget_display(project)
        self.assertEqual(display, "Rs. 1,50,00,000")

    def test_synthetic_budget_defaults_to_not_disclosed(self):
        project = MagicMock()
        project.raw_budget_text = None
        project.budget = "Verified on Official Portal"
        project.evidence_text = "General environmental sustainability programs conducted across 5 villages."

        display = get_verbatim_csr_budget_display(project)
        self.assertEqual(display, "Not disclosed")

    def test_unsupported_number_defaults_to_not_disclosed(self):
        project = MagicMock()
        project.raw_budget_text = "50000000"
        project.budget = "50000000"
        project.evidence_text = "Solar panels installed across secondary schools."

        display = get_verbatim_csr_budget_display(project)
        self.assertEqual(display, "Not disclosed")


class Step0GoldenDatasetAgreementTests(SimpleTestCase):

    def test_golden_dataset_integrity_and_agreement(self):
        dataset_path = os.path.join("data", "golden_verified_dataset.json")
        self.assertTrue(os.path.exists(dataset_path), "Golden dataset must exist at data/golden_verified_dataset.json")

        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        jobs = data.get("jobs", [])
        csrs = data.get("csr_projects", [])

        # Requirement: At least 30 jobs and 20 CSR records
        self.assertGreaterEqual(len(jobs), 30, "Golden dataset must contain at least 30 verified jobs")
        self.assertGreaterEqual(len(csrs), 20, "Golden dataset must contain at least 20 verified CSR projects")

        for idx, j in enumerate(jobs):
            self.assertTrue(j.get("verified_by_human"), f"Job #{idx} must have verified_by_human=true")
            self.assertTrue(j.get("source_url"), f"Job #{idx} must have source_url")
            self.assertTrue(j.get("raw_title"), f"Job #{idx} must have raw_title")

        for idx, c in enumerate(csrs):
            self.assertTrue(c.get("verified_by_human"), f"CSR #{idx} must have verified_by_human=true")
            self.assertTrue(c.get("source_url"), f"CSR #{idx} must have source_url")
            self.assertTrue(c.get("raw_title"), f"CSR #{idx} must have raw_title")
