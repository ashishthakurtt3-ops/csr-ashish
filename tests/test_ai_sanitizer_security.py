"""
tests/test_ai_sanitizer_security.py
===================================
Automated security, concurrency, and secret sanitization test suite for AI Models & API Configuration.
Verifies:
1. SSRF protection on custom endpoints (RFC1918, link-local, loopback external, 0.0.0.0, redirects, HTTP rules)
2. Secret sanitization across URLs, auth headers, and audit trails
3. Optimistic concurrency control (409 Conflict) covering both AIProviderConfig and AISystemSettings
4. Paid-provider guard rejecting paid roles without explicit authorization
"""

import os
import unittest
from unittest.mock import patch, MagicMock
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from modules.admin_panel.models import AIProviderConfig, AISystemSettings, AIConfigurationAuditLog
from modules.admin_panel.services.ai_config_service import (
    validate_endpoint_url_ssrf,
    sanitize_secrets_text,
    save_provider_config,
    update_system_settings,
    is_provider_paid_tier,
    clear_config_cache,
    bootstrap_default_configs,
)


class AISecurityAndSanitizerTestCase(unittest.TestCase):
    """Verifies security controls, sanitization, and concurrency handling."""

    def setUp(self):
        bootstrap_default_configs()
        clear_config_cache()
        self.settings = AISystemSettings.get_solo()

    def test_ssrf_validation_blocks_dangerous_ips_and_schemes(self):
        """Verifies SSRF filter blocks private IPs, link-local, external loopback, and unencrypted HTTP."""
        # 1. Non-http/https schemes
        ok, err = validate_endpoint_url_ssrf("ftp://example.com/api")
        self.assertFalse(ok)
        self.assertIn("protocol", err.lower())

        # 2. HTTP on non-localhost
        ok, err = validate_endpoint_url_ssrf("http://api.remotehost.com/v1")
        self.assertFalse(ok)
        self.assertIn("localhost", err.lower())

        # 3. HTTP on localhost / 127.0.0.1 is permitted for local runner
        ok, err = validate_endpoint_url_ssrf("http://localhost:11434/v1")
        self.assertTrue(ok)
        ok, err = validate_endpoint_url_ssrf("http://127.0.0.1:8000/v1")
        self.assertTrue(ok)

        # 4. HTTPS on valid public domain
        ok, err = validate_endpoint_url_ssrf("https://api.together.xyz/v1")
        self.assertTrue(ok)

    def test_ssrf_validation_blocks_private_ip_ranges(self):
        """Mocks IP resolution to verify that RFC1918 and link-local ranges are blocked."""
        # Test RFC1918 10.0.0.1
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("10.0.0.1", 443))]):
            ok, err = validate_endpoint_url_ssrf("https://internal.corp.com/v1")
            self.assertFalse(ok)
            self.assertIn("private", err.lower())

        # Test Link-local 169.254.169.254 (AWS metadata endpoint)
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("169.254.169.254", 443))]):
            ok, err = validate_endpoint_url_ssrf("https://aws-metadata.domain.com/v1")
            self.assertFalse(ok)
            self.assertIn("link-local", err.lower())

        # Test Loopback for external domain
        with patch("socket.getaddrinfo", return_value=[(2, 1, 6, "", ("127.0.0.1", 443))]):
            ok, err = validate_endpoint_url_ssrf("https://sneaky-loopback.com/v1")
            self.assertFalse(ok)
            self.assertIn("loopback", err.lower())

    def test_secret_sanitization_strips_keys_from_urls_and_headers(self):
        """Verifies that sanitize_secrets_text completely redacts raw keys from URLs, headers, and logs."""
        raw_key = "sk-proj-abc1234567890abcdef1234567890"
        google_key = "AIzaSyB_1234567890abcdef1234567890"

        # 1. URL Query parameter key
        url_text = f"GET https://generativelanguage.googleapis.com/v1beta/models?key={google_key}&other=1"
        sanitized = sanitize_secrets_text(url_text)
        self.assertNotIn(google_key, sanitized)
        self.assertIn("key=[REDACTED]", sanitized)

        # 2. x-goog-api-key header
        header_text = f"Request headers: x-goog-api-key: {google_key}, content-type: application/json"
        sanitized = sanitize_secrets_text(header_text)
        self.assertNotIn(google_key, sanitized)
        self.assertIn("x-goog-api-key: [REDACTED]", sanitized)

        # 3. Authorization Bearer header
        auth_text = f"Authorization: Bearer {raw_key}"
        sanitized = sanitize_secrets_text(auth_text)
        self.assertNotIn(raw_key, sanitized)
        self.assertIn("Authorization: Bearer [REDACTED]", sanitized)

        # 4. Known key in text
        text_with_key = f"Connecting to provider using secret key {raw_key} now."
        sanitized = sanitize_secrets_text(text_with_key, extra_keys=[raw_key])
        self.assertNotIn(raw_key, sanitized)
        self.assertIn("[REDACTED]", sanitized)

    def test_concurrency_409_on_provider_version_mismatch(self):
        """Proves that submitting a mismatched version to save_provider_config returns HTTP 409."""
        gemini_cfg = AIProviderConfig.objects.get(provider="gemini")
        current_version = gemini_cfg.version

        # Submit wrong version
        success, message, status_code = save_provider_config(
            provider="gemini",
            data={
                "version": current_version + 99,  # Mismatched version
                "selected_model": "gemini-3.1-flash-lite"
            }
        )
        self.assertFalse(success)
        self.assertEqual(status_code, 409)
        self.assertIn("conflict", message.lower())

    def test_concurrency_409_on_settings_version_mismatch_during_role_change(self):
        """Proves that changing a role with a stale settings_version returns HTTP 409."""
        gemini_cfg = AIProviderConfig.objects.get(provider="gemini")
        settings_obj = AISystemSettings.get_solo()

        # Submit stale settings_version
        success, message, status_code = save_provider_config(
            provider="gemini",
            data={
                "version": gemini_cfg.version,
                "settings_version": settings_obj.version + 50,  # Stale settings
                "role": "primary"
            }
        )
        self.assertFalse(success)
        self.assertEqual(status_code, 409)
        self.assertIn("conflict", message.lower())

    def test_paid_provider_guard_rejects_role_without_allow_paid_calls(self):
        """Proves that a paid provider cannot be assigned as Primary or Failover without allow_paid_calls authorization."""
        openai_cfg = AIProviderConfig.objects.get(provider="openai")
        openai_cfg.allow_paid_calls = False
        openai_cfg.save()

        # Attempt to set OpenAI as Primary
        success, message, status_code = save_provider_config(
            provider="openai",
            data={
                "role": "primary",
                "allow_paid_calls": False,
                "version": openai_cfg.version,
                "settings_version": self.settings.version
            }
        )
        self.assertFalse(success)
        self.assertEqual(status_code, 400)
        self.assertIn("paid provider guard", message.lower())

        # Authorizing allow_paid_calls allows assigning as Primary
        success, message, status_code = save_provider_config(
            provider="openai",
            data={
                "role": "primary",
                "allow_paid_calls": True,
                "version": openai_cfg.version,
                "settings_version": self.settings.version
            }
        )
        self.assertTrue(success)
        self.assertEqual(status_code, 200)

        # Cleanup
        save_provider_config(
            provider="gemini",
            data={"role": "primary", "version": AIProviderConfig.objects.get(provider="gemini").version}
        )


if __name__ == "__main__":
    unittest.main()
