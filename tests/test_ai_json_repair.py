"""
tests/test_ai_json_repair.py
============================
Unit tests for resilient JSON cleaning and repair logic in AI API Client.
Verifies graceful handling of LLM anomalies: trailing commas, unescaped line breaks,
code blocks, truncated outputs, comments, and single-quoted structures.
"""

from django.test import TestCase
from modules.crawler_engine.ai_api_client import BaseAIClient, AIClientError


class AIJsonRepairTests(TestCase):

    def setUp(self):
        # BaseAIClient is an abstract base, create a minimal concrete instance for testing _clean_json_text
        class ConcreteClient(BaseAIClient):
            def _execute_provider_request(self, prompt: str):
                return {}, "test-model"

        self.client = ConcreteClient()

    def test_clean_valid_json(self):
        raw = '{"candidate_id": 1, "job_title": "Software Engineer"}'
        result = self.client._clean_json_text(raw)
        self.assertEqual(result, {"candidate_id": 1, "job_title": "Software Engineer"})

    def test_clean_markdown_code_fence(self):
        raw = '```json\n[{"candidate_id": 1, "job_title": "Data Scientist"}]\n```'
        result = self.client._clean_json_text(raw)
        self.assertEqual(result, [{"candidate_id": 1, "job_title": "Data Scientist"}])

    def test_clean_reasoning_thinking_tags(self):
        raw = '<think>I should extract the software engineer role.</think>\n[{"candidate_id": 1, "job_title": "DevOps Engineer"}]'
        result = self.client._clean_json_text(raw)
        self.assertEqual(result, [{"candidate_id": 1, "job_title": "DevOps Engineer"}])

    def test_clean_trailing_commas_in_array_and_object(self):
        raw = '[\n  {"candidate_id": 1, "job_title": "Lead Engineer",},\n]'
        result = self.client._clean_json_text(raw)
        self.assertEqual(result, [{"candidate_id": 1, "job_title": "Lead Engineer"}])

    def test_clean_unescaped_linebreaks_and_tabs(self):
        raw = '{\n  "description": "Line 1\nLine 2\twith tab"\n}'
        result = self.client._clean_json_text(raw)
        self.assertEqual(result.get("description"), "Line 1\nLine 2\twith tab")

    def test_clean_salvage_truncated_array(self):
        raw = '[{"candidate_id": 1, "job_title": "Job A"}, {"candidate_id": 2, "job_title": "Job B'
        result = self.client._clean_json_text(raw)
        self.assertEqual(result, [{"candidate_id": 1, "job_title": "Job A"}])

    def test_clean_trailing_commentary(self):
        raw = '[{"candidate_id": 1, "job_title": "Product Manager"}]\n\nHere are the extracted vacancies.'
        result = self.client._clean_json_text(raw)
        self.assertEqual(result, [{"candidate_id": 1, "job_title": "Product Manager"}])

    def test_clean_single_quotes_python_literal(self):
        raw = "[{'candidate_id': 1, 'job_title': 'Accountant', 'active': True}]"
        result = self.client._clean_json_text(raw)
        self.assertEqual(result, [{'candidate_id': 1, 'job_title': 'Accountant', 'active': True}])

    def test_clean_invalid_raises_error(self):
        raw = "This is plain conversational text with no JSON at all."
        with self.assertRaises(AIClientError):
            self.client._clean_json_text(raw)
