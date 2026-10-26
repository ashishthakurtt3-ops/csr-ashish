"""
tests/test_ai_role_routing.py
=============================
Automated test suite proving that changing Primary and Failover roles in AI Models & API Configuration
dynamically changes which provider page_classifier / ai_api_client calls first, correctly
honoring primary_provider, fallback_provider, and fallback_enabled settings.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from modules.admin_panel.models import AIProviderConfig, AISystemSettings
from modules.admin_panel.services.ai_config_service import (
    save_provider_config,
    update_system_settings,
    clear_config_cache,
    bootstrap_default_configs,
)
from modules.crawler_engine.ai_api_client import (
    get_ai_client,
    PrimaryFallbackAIClient,
    GeminiApiClient,
    GrokApiClient,
    OpenRouterApiClient,
    OpenAICompatibleApiClient,
    QuotaExhaustedError,
)
from modules.crawler_engine.page_classifier import TwoStagePageClassifier


class AIRoleRoutingTestCase(unittest.TestCase):
    """Verifies that primary and fallback provider routing reacts immediately to role changes."""

    def setUp(self):
        bootstrap_default_configs()
        clear_config_cache()
        self.settings = AISystemSettings.get_solo()

    def tearDown(self):
        # Reset to safe default
        self.settings.primary_provider = "gemini"
        self.settings.primary_model = "gemini-3.1-flash-lite"
        self.settings.fallback_enabled = True
        self.settings.fallback_provider = "grok"
        self.settings.fallback_model = "grok-2-latest"
        self.settings.free_tier_only = True
        self.settings.version += 1
        self.settings.save()
        clear_config_cache()

    def test_default_role_routing_gemini_primary_grok_fallback(self):
        """Proves that by default Gemini is primary and Grok is fallback."""
        self.settings.primary_provider = "gemini"
        self.settings.fallback_enabled = True
        self.settings.fallback_provider = "grok"
        self.settings.save()
        clear_config_cache()

        client = get_ai_client()
        self.assertIsInstance(client, PrimaryFallbackAIClient)
        self.assertIsInstance(client.primary, GeminiApiClient)
        self.assertIsInstance(client.fallback, GrokApiClient)

        # Verify page classifier adopts the same client
        classifier = TwoStagePageClassifier()
        self.assertIsInstance(classifier.client, PrimaryFallbackAIClient)
        self.assertIsInstance(classifier.client.primary, GeminiApiClient)
        self.assertIsInstance(classifier.client.fallback, GrokApiClient)

    def test_role_change_alters_primary_and_failover_call_order(self):
        """
        Proves that changing Primary role to OpenRouter and Failover to Groq
        dynamically re-routes get_ai_client and TwoStagePageClassifier.
        """
        # Switch Primary to OpenRouter, Failover to Groq
        update_system_settings({
            "primary_provider": "openrouter",
            "primary_model": "openrouter/free",
            "fallback_enabled": True,
            "fallback_provider": "groq",
            "fallback_model": "llama-3.3-70b-versatile",
            "version": self.settings.version,
        })

        client = get_ai_client()
        self.assertIsInstance(client, PrimaryFallbackAIClient)
        self.assertIsInstance(client.primary, OpenRouterApiClient)
        self.assertIsInstance(client.fallback, OpenAICompatibleApiClient)

        # TwoStagePageClassifier initialization reflects new primary/failover
        classifier = TwoStagePageClassifier()
        self.assertIsInstance(classifier.client.primary, OpenRouterApiClient)
        self.assertIsInstance(classifier.client.fallback, OpenAICompatibleApiClient)

    def test_disabling_failover_returns_single_primary_client(self):
        """Proves that disabling fallback returns the primary client directly without PrimaryFallbackAIClient wrapper."""
        update_system_settings({
            "primary_provider": "gemini",
            "fallback_enabled": False,
            "fallback_provider": "",
            "version": self.settings.version,
        })

        client = get_ai_client()
        self.assertNotIsInstance(client, PrimaryFallbackAIClient)
        self.assertIsInstance(client, GeminiApiClient)

        classifier = TwoStagePageClassifier()
        self.assertNotIsInstance(classifier.client, PrimaryFallbackAIClient)
        self.assertIsInstance(classifier.client, GeminiApiClient)

    def test_fallback_invocation_order_on_primary_failure(self):
        """
        Mocks client inference to verify that Primary is called first;
        if Primary raises QuotaExhaustedError, Failover is invoked second.
        """
        mock_primary = MagicMock()
        mock_primary.classify_page_content.side_effect = QuotaExhaustedError("Primary API rate limited (429)")

        mock_fallback = MagicMock()
        mock_fallback.verify_zero_cost_eligibility.return_value = (True, "Confirmed")
        mock_fallback.classify_page_content.return_value = {
            "category": "CAREERS",
            "confidence": 0.95,
            "provider": "grok"
        }

        chained_client = PrimaryFallbackAIClient(primary=mock_primary, fallback=mock_fallback)
        result = chained_client.classify_page_content("ImpactBridge", "https://example.com/careers", {})

        # Verify Primary was attempted first
        mock_primary.classify_page_content.assert_called_once()
        # Verify Fallback was called after Primary failed
        mock_fallback.classify_page_content.assert_called_once()
        self.assertEqual(result["provider"], "grok")
        self.assertEqual(result["category"], "CAREERS")


if __name__ == "__main__":
    unittest.main()
