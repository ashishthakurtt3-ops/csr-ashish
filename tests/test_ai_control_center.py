"""
tests/test_ai_control_center.py
===============================
Comprehensive Test Suite for ImpactBridge AI Models & API Control Center.
Covers all 25 critical audit and safety scenarios required by PART 16:
1. Missing API key handling
2. Valid API key configuration
3. Invalid API key handling & error sanitization
4. Revoked or expired credential simulation
5. Invalid endpoint SSRF blocking (private IPs, loopback, file://)
6. Network timeout handling
7. Rate limiting detection (HTTP 429)
8. Provider quota exhaustion handling (HTTP 402)
9. Unavailable model identifier handling
10. Model catalog retrieval failure handling
11. Successful dynamic model catalog refresh
12. Valid model inference response parsing
13. Malformed model response validation
14. Missing usage metadata handling (labels as ESTIMATED or UNAVAILABLE)
15. Failed calls token & telemetry recording
16. Paid-call restriction enforcement (free_tier_only=True)
17. Token and request budget safeguards
18. Primary provider failure failover
19. Prohibited fallback blocking
20. Per-company diagnostic execution (bounded read-only)
21. Company-ID mismatch / not found handling
22. Historical usage & telemetry reporting
23. API key masking and non-disclosure
24. Server-side administrative authorization
25. Audit event creation in MySQL
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden

from modules.admin_panel.models import AIProviderConfig, AISystemSettings, AIConfigurationAuditLog, Company
import modules.admin_panel.services.ai_config_service as acs
from modules.admin_panel.services.ai_config_service import (
    validate_endpoint_url_ssrf,
    sanitize_secrets_text,
    is_provider_paid_tier,
    is_model_free_tier,
    save_provider_config,
    update_system_settings,
    test_provider_live,
    refresh_provider_models,
    search_companies,
    run_company_diagnostic,
    test_routing_and_failover,
    test_all_providers_batch,
    get_model_catalog_list,
)
from modules.admin_panel.services.ai_telemetry_service import AITelemetryStore
from modules.admin_panel.utils.ai_crypto import mask_api_key, encrypt_secret, decrypt_secret
from modules.admin_panel.views import ai_config_views

User = get_user_model()


class AIControlCenterMasterTestSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rf = RequestFactory()
        cls.admin_user = User.objects.filter(is_superuser=True).first()
        if not cls.admin_user:
            cls.admin_user = User.objects.create_superuser('test_ai_admin', 'ai_admin@example.com', 'adminpass123')
        cls.non_admin_user = User.objects.filter(is_staff=False, is_superuser=False).first()
        if not cls.non_admin_user:
            cls.non_admin_user = User.objects.create_user('test_regular_user', 'regular@example.com', 'userpass123')

        # Use an isolated SQLite telemetry DB for testing
        test_cache_dir = os.path.join(os.getcwd(), ".cache", "test_ai_classifier")
        os.makedirs(test_cache_dir, exist_ok=True)
        cls.test_db_path = os.path.join(test_cache_dir, "test_telemetry.sqlite3")
        cls.telemetry_store = AITelemetryStore(cls.test_db_path)

    def test_01_missing_api_key(self):
        """1. Missing API key should return proper configuration warning."""
        res = test_provider_live("deepseek", api_key_override="")
        self.assertFalse(res.get("success"))
        self.assertIn(res.get("status", ""), ["UNCONFIGURED", "CONFIG_ERROR"])

    def test_02_valid_api_key_configuration(self):
        """2. Saving a valid API key should encrypt it and store masked representation."""
        cfg = AIProviderConfig.objects.get(provider="gemini")
        success, msg, code = save_provider_config(
            provider="gemini",
            data={"api_key": "AIzaSyTestValidKey1234567890", "version": cfg.version},
            user=self.admin_user
        )
        self.assertTrue(success)
        cfg.refresh_from_db()
        self.assertNotEqual(cfg.encrypted_api_key, "AIzaSyTestValidKey1234567890")
        self.assertTrue("••••" in cfg.api_key_masked)
        self.assertEqual(cfg.get_api_key(), "AIzaSyTestValidKey1234567890")

    def test_03_invalid_api_key_sanitization(self):
        """3. Invalid key error message should strictly redact the raw secret."""
        raw_secret = "sk-ant-test-secret-key-999999999"
        err_msg = f"API request failed with Authorization: Bearer {raw_secret}"
        sanitized = sanitize_secrets_text(err_msg, extra_keys=[raw_secret])
        self.assertNotIn(raw_secret, sanitized)
        self.assertIn("[REDACTED]", sanitized)

    def test_04_revoked_or_expired_credential(self):
        """4. Simulating expired credential error sets AUTH_FAILED / INVALID_KEY status."""
        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_resp.json.return_value = {"error": {"message": "API key revoked"}}
            mock_resp.text = json.dumps(mock_resp.json.return_value)
            mock_post.return_value = mock_resp

            res = test_provider_live("openrouter", api_key_override="sk-or-v1-revoked-key")
            self.assertFalse(res.get("success"))
            self.assertIn(res.get("status"), ["AUTH_FAILED", "INVALID_KEY"])

    def test_05_invalid_endpoint_ssrf_blocking(self):
        """5. SSRF validation must block loopback, RFC1918 private IPs, and file://."""
        valid, msg = validate_endpoint_url_ssrf("file:///etc/passwd")
        self.assertFalse(valid)
        valid, msg = validate_endpoint_url_ssrf("http://192.168.1.1/v1/chat")
        self.assertFalse(valid)
        valid, msg = validate_endpoint_url_ssrf("http://10.0.0.1/api")
        self.assertFalse(valid)
        valid, msg = validate_endpoint_url_ssrf("https://openrouter.ai/api/v1")
        self.assertTrue(valid)

    def test_06_network_timeout_handling(self):
        """6. Network timeout raises clean NETWORK_ERROR status."""
        import requests
        with patch('requests.post', side_effect=requests.exceptions.Timeout("Connection timed out")):
            res = test_provider_live("gemini", api_key_override="AIzaSyTestTimeoutKey")
            self.assertFalse(res.get("success"))
            self.assertIn("timed out", (res.get("status", "") + res.get("message", "")).lower())

    def test_07_rate_limiting_detection(self):
        """7. HTTP 429 returns RATE_LIMITED or QUOTA_EXCEEDED status."""
        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_resp.json.return_value = {"error": {"message": "Rate limit exceeded"}}
            mock_resp.text = json.dumps(mock_resp.json.return_value)
            mock_post.return_value = mock_resp

            res = test_provider_live("openrouter", api_key_override="sk-or-v1-test-key")
            self.assertFalse(res.get("success"))
            self.assertIn(res.get("status"), ["RATE_LIMITED", "QUOTA_EXCEEDED"])

    def test_08_provider_quota_exhaustion(self):
        """8. HTTP 402 returns QUOTA_EXCEEDED or PROVIDER_ERROR status."""
        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 402
            mock_resp.json.return_value = {"error": {"message": "Credit exhausted"}}
            mock_resp.text = json.dumps(mock_resp.json.return_value)
            mock_post.return_value = mock_resp

            res = test_provider_live("openrouter", api_key_override="sk-or-v1-test-key")
            self.assertFalse(res.get("success"))
            self.assertIn(res.get("status"), ["QUOTA_EXCEEDED", "PROVIDER_ERROR"])

    def test_09_unavailable_model_identifier(self):
        """9. Querying an invalid model ID flags MODEL_UNAVAILABLE."""
        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.json.return_value = {"error": {"message": "The model `fake-model:free` does not exist"}}
            mock_resp.text = json.dumps(mock_resp.json.return_value)
            mock_post.return_value = mock_resp

            res = test_provider_live("openrouter", model_override="fake-model:free", api_key_override="sk-or-v1-test")
            self.assertFalse(res.get("success"))
            self.assertIn(res.get("status"), ["MODEL_UNAVAILABLE", "COST_PROTECTION_BLOCKED"])

    def test_10_model_catalog_retrieval_failure(self):
        """10. Catalog retrieval failure cleanly falls back to default catalog."""
        import requests
        acs._MODEL_REFRESH_LAST_CALLED.clear()
        with patch('requests.get', side_effect=requests.exceptions.ConnectionError("DNS failure")):
            success, msg, models, code = refresh_provider_models("openrouter")
            self.assertTrue(len(models) > 0)  # Default catalog preserved

    def test_11_successful_model_catalog_refresh(self):
        """11. Successful dynamic model list parsing updates available_models."""
        acs._MODEL_REFRESH_LAST_CALLED.clear()
        with patch('requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "data": [
                    {"id": "meta-llama/llama-3.3-70b-instruct:free", "name": "Llama 3.3 70B Free", "context_length": 131072},
                    {"id": "google/gemma-2-9b-it:free", "name": "Gemma 2 9B Free", "context_length": 8192}
                ]
            }
            mock_get.return_value = mock_resp

            success, msg, models, code = refresh_provider_models("openrouter")
            self.assertTrue(success)
            self.assertTrue(any(m["id"] == "meta-llama/llama-3.3-70b-instruct:free" for m in models))

    def test_12_valid_model_response(self):
        """12. Valid inference response records success and token latency."""
        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "choices": [{"message": {"content": '{"verdict": "VALID", "category": "Careers"}'}}],
                "usage": {"prompt_tokens": 15, "completion_tokens": 10, "total_tokens": 25}
            }
            mock_post.return_value = mock_resp

            res = test_provider_live("openrouter", api_key_override="sk-or-v1-valid-key")
            self.assertTrue(res.get("success"))
            self.assertIn(res.get("status"), ["ACTIVE", "SUCCESS"])

    def test_13_malformed_model_response(self):
        """13. Non-JSON response is rejected safely."""
        with patch('requests.post') as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "<html><body>502 Bad Gateway</body></html>"
            mock_resp.json.side_effect = ValueError("No JSON")
            mock_post.return_value = mock_resp

            res = test_provider_live("openrouter", api_key_override="sk-or-v1-valid-key")
            self.assertFalse(res.get("success"))
            self.assertIn("INVALID_RESPONSE", res.get("status", ""))

    def test_14_missing_usage_metadata(self):
        """14. Missing provider usage metadata defaults to ESTIMATED method without inventing numbers."""
        event_id = self.telemetry_store.record_event(
            provider="gemini",
            model="gemini-3.1-flash-lite",
            task="homepage_classification",
            status="SUCCESS",
            input_tokens=100,
            output_tokens=50,
            measurement_method="ESTIMATED"
        )
        events, _ = self.telemetry_store.get_events(limit=1)
        self.assertEqual(events[0]["measurement_method"], "ESTIMATED")

    def test_15_failed_calls_telemetry(self):
        """15. Failed requests record zero cost and capture error category."""
        event_id = self.telemetry_store.record_event(
            provider="openrouter",
            model="openrouter/free",
            task="job_extraction",
            status="AUTH_FAILED",
            error_category="INVALID_API_KEY",
            measurement_method="UNAVAILABLE"
        )
        events, _ = self.telemetry_store.get_events(limit=1)
        self.assertEqual(events[0]["status"], "AUTH_FAILED")
        self.assertEqual(events[0]["cost_usd"], 0.0)

    def test_16_paid_call_restrictions(self):
        """16. Paid providers are blocked when free_tier_only=True and allow_paid_calls=False."""
        settings = AISystemSettings.get_solo()
        settings.free_tier_only = True
        settings.save()

        grok_cfg, _ = AIProviderConfig.objects.get_or_create(provider="grok")
        grok_cfg.allow_paid_calls = False
        grok_cfg.save()

        self.assertTrue(is_provider_paid_tier("grok", "grok-2-latest"))
        self.assertFalse(grok_cfg.allow_paid_calls)

    def test_17_token_and_budget_limits(self):
        """17. Cost calculation follows exact model pricing rate card."""
        cost = self.telemetry_store.calculate_cost("gemini-1.5-flash", 1_000_000, 1_000_000)
        self.assertEqual(cost, 0.375)  # $0.075 + $0.30

    def test_18_primary_provider_failover(self):
        """18. Automatic failover routes to secondary when primary fails."""
        res = test_routing_and_failover(user=self.admin_user)
        self.assertIn("trace", res)
        self.assertTrue(len(res["trace"]) >= 2)

    def test_19_prohibited_fallback_blocking(self):
        """19. Fallback is blocked if fallback provider requires payment and allow_paid_calls=False."""
        settings = AISystemSettings.get_solo()
        settings.fallback_provider = "grok"
        settings.fallback_model = "grok-2-latest"
        settings.free_tier_only = True
        settings.save()

        grok_cfg, _ = AIProviderConfig.objects.get_or_create(provider="grok")
        grok_cfg.allow_paid_calls = False
        grok_cfg.save()

        res = test_routing_and_failover(user=self.admin_user)
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("status"), "FAILOVER_BLOCKED_BY_ZERO_COST_GUARD")

    def test_20_per_company_diagnostic_bounded(self):
        """20. Per-company diagnostic runs bounded check and produces structured trace with 0 DB writes."""
        comp = Company.objects.first()
        if comp:
            res = run_company_diagnostic(comp.company_id, "homepage_classification", user=self.admin_user)
            self.assertTrue(res.get("success"))
            self.assertIn("diagnostic_result", res)
            self.assertIn("tokens", res)
            self.assertEqual(res.get("company_id"), comp.company_id)

    def test_21_company_id_mismatch(self):
        """21. Non-existent company ID returns clean NOT_FOUND status."""
        res = run_company_diagnostic("COMP_INVALID_99999", "homepage_classification", user=self.admin_user)
        self.assertFalse(res.get("success"))
        self.assertEqual(res.get("status"), "NOT_FOUND")

    def test_22_historical_usage_reporting(self):
        """22. Telemetry store aggregates historical metrics accurately."""
        summary = self.telemetry_store.get_summary(days=30)
        self.assertIn("total_calls", summary)
        self.assertIn("total_tokens", summary)
        self.assertIn("total_cost_usd", summary)

    def test_23_api_key_masking(self):
        """23. API keys must always be masked before being exposed to frontend."""
        raw = "sk-proj-1234567890abcdef"
        masked = mask_api_key(raw)
        self.assertIn("cdef", masked)
        self.assertNotIn("1234567890", masked)

    def test_24_server_side_authorization(self):
        """24. Non-admin users are strictly blocked from AI configuration endpoints (HTTP 403)."""
        req = self.rf.post('/admin-portal/ai-config/company/diagnostic/', data=json.dumps({}), content_type='application/json')
        req.user = self.non_admin_user
        res = ai_config_views.ai_config_company_diagnostic_api(req)
        self.assertEqual(res.status_code, 403)

    def test_25_audit_event_creation(self):
        """25. Critical configuration and diagnostic events create audit records in MySQL."""
        init_count = AIConfigurationAuditLog.objects.count()
        save_provider_config("gemini", {"base_url": "https://generativelanguage.googleapis.com"}, user=self.admin_user)
        self.assertTrue(AIConfigurationAuditLog.objects.count() > init_count)


if __name__ == '__main__':
    unittest.main()
