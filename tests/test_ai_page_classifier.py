"""
tests/test_ai_page_classifier.py
================================
Unit tests for AI-powered website discovery, two-stage page classification,
evidence validation gate, caching, and quota handling.
"""

import json
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase

from modules.crawler_engine.page_classifier import TwoStagePageClassifier
from modules.crawler_engine.ai_api_client import GeminiApiClient, QuotaExhaustedError
from modules.crawler_engine import ai_classifier_config as cfg


class TwoStageClassifierTests(SimpleTestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=GeminiApiClient)
        self.classifier = TwoStagePageClassifier(client=self.mock_client)

    def test_extract_candidate_links_preserves_context(self):
        html = """
        <html>
            <header>
                <nav>
                    <a href="/join-us">Join Our Team</a>
                    <a href="/about">About Us</a>
                </nav>
            </header>
            <main>
                <a href="/apply/personal-loan">Apply Now for Home Loan</a>
            </main>
            <footer>
                <a href="/sustainability/csr-policy">CSR Initiatives & Impact</a>
                <a href="/reports/annual-report-2025.pdf">Annual Report 2024-25</a>
            </footer>
        </html>
        """
        candidates = self.classifier.extract_candidate_links_from_html("https://example.com", html)
        urls = [c["url"] for c in candidates]
        self.assertIn("https://example.com/join-us", urls)
        self.assertIn("https://example.com/sustainability/csr-policy", urls)
        self.assertIn("https://example.com/reports/annual-report-2025.pdf", urls)

        # Check location context tags
        join_cand = next(c for c in candidates if "join-us" in c["url"])
        self.assertEqual(join_cand["location"], "HEADER_NAV")

        csr_cand = next(c for c in candidates if "csr-policy" in c["url"])
        self.assertEqual(csr_cand["location"], "FOOTER_NAV")

    def test_classify_discovered_links_batch(self):
        self.mock_client.classify_links_batch.return_value = [
            {
                "url": "https://example.com/careers",
                "broad_category": "CAREERS_RECRUITMENT",
                "candidate_category": "CAREERS_LANDING_CANDIDATE",
                "confidence": 0.95,
                "reasoning": "Clear careers portal link"
            },
            {
                "url": "https://example.com/csr",
                "broad_category": "CSR_SOCIAL_IMPACT",
                "candidate_category": "CSR_OVERVIEW_CANDIDATE",
                "confidence": 0.92,
                "reasoning": "Social responsibility overview"
            }
        ]

        links = [
            {"url": "https://example.com/careers", "text": "Join Us", "location": "HEADER_NAV"},
            {"url": "https://example.com/csr", "text": "Our Responsibility", "location": "FOOTER_NAV"}
        ]

        results = self.classifier.classify_discovered_links("Example Corp", "example.com", links)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["candidate_category"], "CAREERS_LANDING_CANDIDATE")
        self.assertEqual(results[1]["candidate_category"], "CSR_OVERVIEW_CANDIDATE")

    def test_filter_promising_candidates_priority(self):
        classified = [
            {"url": "https://example.com/careers/jobs", "candidate_category": "JOBS_LISTING_CANDIDATE", "confidence": 0.9},
            {"url": "https://example.com/about", "candidate_category": "OTHER_COMPANY_INFORMATION", "confidence": 0.8},
            {"url": "https://example.com/csr/projects", "candidate_category": "CSR_PROJECT_DISCLOSURE_CANDIDATE", "confidence": 0.95},
        ]
        filtered = self.classifier.filter_promising_candidates_for_stage_2(classified, max_pages=2)
        filtered_urls = [f["url"] for f in filtered]
        self.assertIn("https://example.com/careers/jobs", filtered_urls)
        self.assertIn("https://example.com/csr/projects", filtered_urls)
        self.assertNotIn("https://example.com/about", filtered_urls)

    def test_evidence_gate_rejects_consumer_loan_application(self):
        page_classification = {
            "page_type": "JOB_APPLICATION_PAGE",
            "confidence": 0.88,
            "evidence": "Apply online form"
        }
        page_data = {
            "url": "https://bank.com/apply/personal-loan",
            "is_accessible": True,
            "main_text": "Apply for personal loan online with instant approval in 5 minutes. Check credit score."
        }
        validation = self.classifier.validate_page_evidence("Example Bank", "bank.com", page_classification, page_data)
        self.assertEqual(validation["decision"], "REJECTED")
        self.assertIn("commercial consumer banking/loan application", validation["reason"])

    def test_evidence_gate_approves_jobs_listing(self):
        page_classification = {
            "page_type": "JOBS_LISTING_PAGE",
            "confidence": 0.92,
            "evidence": "Search openings and department filters"
        }
        page_data = {
            "url": "https://techcorp.com/careers/openings",
            "is_accessible": True,
            "main_text": "Search 45 open positions across Engineering, Product, and Sales in Mumbai and Bengaluru."
        }
        validation = self.classifier.validate_page_evidence("Tech Corp", "techcorp.com", page_classification, page_data)
        self.assertEqual(validation["decision"], "APPROVED")
        self.assertEqual(validation["target_field"], "jobs_page_url")

    def test_evidence_gate_rejects_inaccessible_404(self):
        page_classification = {"page_type": "INACCESSIBLE_PAGE", "confidence": 0.99}
        page_data = {"url": "https://corp.com/careers", "is_accessible": False}
        validation = self.classifier.validate_page_evidence("Corp", "corp.com", page_classification, page_data)
        self.assertEqual(validation["decision"], "REJECTED")

    def test_evidence_gate_generic_partnership_requires_review_without_rfp(self):
        page_classification = {
            "page_type": "CSR_PARTNERSHIP_OR_RFP",
            "confidence": 0.85
        }
        page_data = {
            "url": "https://corp.com/partner-with-us",
            "is_accessible": True,
            "main_text": "We welcome collaborations with organizations who share our vision."
        }
        validation = self.classifier.validate_page_evidence("Corp", "corp.com", page_classification, page_data)
        self.assertEqual(validation["decision"], "REVIEW_REQUIRED")
        self.assertIn("does not contain concrete RFP/grant documentation", validation["reason"])

    def test_evidence_gate_genuine_csr_rfp_approved(self):
        page_classification = {
            "page_type": "CSR_PARTNERSHIP_OR_RFP",
            "confidence": 0.90
        }
        page_data = {
            "url": "https://corp.com/csr/rfp-2026",
            "is_accessible": True,
            "main_text": "Request for Proposal (RFP): Call for proposals from registered NGOs for FY26 Schedule VII healthcare grants."
        }
        validation = self.classifier.validate_page_evidence("Corp", "corp.com", page_classification, page_data)
        self.assertEqual(validation["decision"], "APPROVED")
        self.assertEqual(validation["target_field"], "csr_portal_url")

    def test_quota_exhausted_error_handling(self):
        self.mock_client.classify_links_batch.side_effect = QuotaExhaustedError("Daily RPD limit reached")
        with self.assertRaises(QuotaExhaustedError):
            self.classifier.classify_discovered_links(
                "Corp", "corp.com", [{"url": "https://corp.com/careers", "text": "Careers"}]
            )


class OpenRouterApiClientTests(SimpleTestCase):

    def test_factory_returns_openrouter_client(self):
        from modules.crawler_engine.ai_api_client import get_ai_client, OpenRouterApiClient, GeminiApiClient
        client_or = get_ai_client(provider="openrouter")
        self.assertIsInstance(client_or, OpenRouterApiClient)

        client_gemini = get_ai_client(provider="gemini")
        self.assertIsInstance(client_gemini, GeminiApiClient)

    @patch("requests.post")
    def test_openrouter_successful_request_parsing(self, mock_post):
        from modules.crawler_engine.ai_api_client import OpenRouterApiClient

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "meta-llama/llama-3.3-70b-instruct:free",
            "choices": [
                {
                    "message": {
                        "content": '```json\n[{"url": "https://example.com/careers", "candidate_category": "CAREERS_LANDING_CANDIDATE", "confidence": 0.95}]\n```'
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        client = OpenRouterApiClient()
        client.api_key = "test-openrouter-key"
        parsed, actual_model = client._execute_provider_request("Test prompt")

        self.assertIsInstance(parsed, list)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["candidate_category"], "CAREERS_LANDING_CANDIDATE")
        self.assertEqual(actual_model, "meta-llama/llama-3.3-70b-instruct:free")

    @patch("requests.post")
    def test_openrouter_rate_limit_raises_quota_exhausted(self, mock_post):
        from modules.crawler_engine.ai_api_client import OpenRouterApiClient

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Rate limit reached for free tier model"
        mock_post.return_value = mock_resp

        client = OpenRouterApiClient()
        client.api_key = "test-openrouter-key"

        with self.assertRaises(QuotaExhaustedError):
            client._execute_provider_request("Test prompt")

