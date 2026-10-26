"""
tests/test_ai_admin_configuration.py
====================================
Comprehensive Test Suite for Centralized AI Models & API Configuration:
- Secure API key encryption and decryption at rest (Fernet / AES-128-CBC)
- API key masking (no plaintext leakage in DOM, logs, or responses)
- Model & provider configuration persistence
- Free-tier cost protection enforcement
- Dynamic model switching across crawler and client modules without restart
- Server-side live test probe validation (success, 401, 404, 429, network error)
- Administrator permission validation
- Sanitized audit trail logging
- Preservation of crawler and source verification safety
"""

import os
import json
from unittest.mock import patch, MagicMock
import requests
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from modules.admin_panel.models import AIProviderConfig, AISystemSettings, AIConfigurationAuditLog
from modules.admin_panel.utils.ai_crypto import encrypt_secret, decrypt_secret, mask_api_key, is_masked_placeholder
from modules.admin_panel.services.ai_config_service import (
    bootstrap_default_configs,
    get_active_ai_config,
    save_provider_config,
    update_system_settings,
    test_provider_live,
    clear_config_cache,
    is_model_free_tier,
)
from modules.crawler_engine import ai_classifier_config as cfg
from modules.crawler_engine.ai_api_client import get_ai_client, GeminiApiClient, OpenRouterApiClient
from modules.crawler_engine.page_classifier import TwoStagePageClassifier

User = get_user_model()


class AIAdminConfigurationTests(TestCase):
    """
    Validates end-to-end functionality for the AI Models & API Configuration admin section.
    """

    def setUp(self):
        clear_config_cache()
        # Create an administrative user and a regular non-staff user
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@impactbridge.org',
            password='Password123!',
            role='SUPERADMIN'
        )
        self.regular_user = User.objects.create_user(
            username='viewer_test',
            email='viewer@impactbridge.org',
            password='Password123!',
            role='VIEWER'
        )
        self.client = Client()
        bootstrap_default_configs()

    def tearDown(self):
        clear_config_cache()

    # --------------------------------------------------------------------------
    # 1. Cryptographic Security & API Key Masking
    # --------------------------------------------------------------------------
    def test_encryption_and_decryption_roundtrip(self):
        raw_key = "AIzaSyTestKey_Secret_1234567890abcdef"
        encrypted = encrypt_secret(raw_key)
        self.assertNotEqual(encrypted, raw_key)
        self.assertNotIn(raw_key, encrypted)

        decrypted = decrypt_secret(encrypted)
        self.assertEqual(decrypted, raw_key)

    def test_api_key_masking_never_reveals_plaintext(self):
        raw_key = "AIzaSyD-7VbAbCdEfGhIjKlMnOpQrStUvWxYz12345"
        masked = mask_api_key(raw_key)

        self.assertNotIn("AIzaSyD-7VbAbCdEfGhIjKlMnOpQrStUvWxYz", masked)
        self.assertTrue(masked.startswith("••••••••••••"))
        self.assertTrue(masked.endswith("2345 (42 chars)"))

        # Test empty / short keys
        self.assertEqual(mask_api_key("", default="(Not configured)"), "(Not configured)")
        self.assertEqual(mask_api_key("short"), "•••••••• (5 chars)")
        self.assertTrue(is_masked_placeholder("••••••••••••2345 (42 chars)"))
        self.assertFalse(is_masked_placeholder("AIzaSyValidNewKey123456"))

    def test_provider_model_encrypts_key_at_rest(self):
        prov, _ = AIProviderConfig.objects.get_or_create(
            provider='gemini',
            defaults={
                'display_name': 'Google Gemini',
                'selected_model': 'gemini-3.1-flash-lite'
            }
        )
        raw_key = "AIzaSyRealSecretKey9988776655"
        prov.set_api_key(raw_key)
        prov.save()

        # Reload directly from DB
        fresh = AIProviderConfig.objects.get(pk=prov.pk)
        self.assertNotEqual(fresh.encrypted_api_key, raw_key)
        self.assertNotIn(raw_key, fresh.encrypted_api_key)
        self.assertEqual(fresh.get_api_key(), raw_key)
        self.assertTrue(fresh.api_key_masked.startswith("••••••••••••"))
        self.assertIn("6655", fresh.api_key_masked)

    # --------------------------------------------------------------------------
    # 2. Key Update Safety & Preservation
    # --------------------------------------------------------------------------
    def test_save_provider_preserves_existing_key_when_empty_or_masked(self):
        prov_code = 'gemini'
        original_key = "AIzaSyOriginalSecretKey123456"
        save_provider_config(
            provider=prov_code,
            data={'api_key': original_key, 'is_enabled': True, 'selected_model': 'gemini-3.1-flash-lite'},
            user=self.admin_user
        )

        cfg_obj = AIProviderConfig.objects.get(provider=prov_code)
        self.assertEqual(cfg_obj.get_api_key(), original_key)

        # Update card with empty / mask placeholder
        save_provider_config(
            provider=prov_code,
            data={'api_key': '••••••••••••3456 (30 chars)', 'selected_model': 'gemini-3.8-flash'},
            user=self.admin_user
        )

        cfg_obj.refresh_from_db()
        self.assertEqual(cfg_obj.get_api_key(), original_key, "Existing API key must NOT be overwritten by mask!")
        self.assertEqual(cfg_obj.selected_model, 'gemini-3.8-flash')

    def test_save_provider_explicit_clear_key(self):
        prov_code = 'openrouter'
        save_provider_config(
            provider=prov_code,
            data={'api_key': 'sk-or-test-key-123456', 'is_enabled': True},
            user=self.admin_user
        )
        cfg_obj = AIProviderConfig.objects.get(provider=prov_code)
        self.assertTrue(bool(cfg_obj.encrypted_api_key))

        # Explicit clear
        save_provider_config(
            provider=prov_code,
            data={'clear_api_key': True},
            user=self.admin_user
        )
        cfg_obj.refresh_from_db()
        self.assertEqual(cfg_obj.get_api_key(), "")
        self.assertEqual(cfg_obj.status, AIProviderConfig.STATUS_UNCONFIGURED)

    # --------------------------------------------------------------------------
    # 3. Free-Tier Cost Protection Enforcement
    # --------------------------------------------------------------------------
    def test_cost_protection_blocks_paid_models(self):
        # Gemini free models are approved
        self.assertTrue(is_model_free_tier('gemini', 'gemini-3.1-flash-lite'))
        self.assertTrue(is_model_free_tier('gemini', 'gemini-3.8-flash'))
        # Gemini paid models are rejected
        self.assertFalse(is_model_free_tier('gemini', 'gemini-1.5-pro'))

        # OpenRouter free models are approved
        self.assertTrue(is_model_free_tier('openrouter', 'openrouter/free'))
        self.assertTrue(is_model_free_tier('openrouter', 'google/gemma-2-9b-it:free'))
        # OpenRouter paid models rejected
        self.assertFalse(is_model_free_tier('openrouter', 'anthropic/claude-3.5-sonnet'))

        # Attempt to set paid model with Free-Tier Protection ON
        success, msg = update_system_settings({
            'primary_provider': 'gemini',
            'primary_model': 'gemini-1.5-pro',
            'free_tier_only': True
        }, user=self.admin_user)

        self.assertFalse(success)
        self.assertIn("Cost Protection Error", msg)

        # Disabling Free-Tier Protection permits custom/paid selection
        success, msg = update_system_settings({
            'primary_provider': 'gemini',
            'primary_model': 'gemini-1.5-pro',
            'free_tier_only': False
        }, user=self.admin_user)
        self.assertTrue(success)

    # --------------------------------------------------------------------------
    # 4. Centralized Dynamic Model Switching Without Restart
    # --------------------------------------------------------------------------
    def test_dynamic_model_switching_affects_all_modules(self):
        # Configure Gemini with a test key
        save_provider_config('gemini', {
            'api_key': 'AIzaSyTestKeyDynamic123',
            'selected_model': 'gemini-3.1-flash-lite',
            'is_enabled': True
        }, user=self.admin_user)

        update_system_settings({
            'primary_provider': 'gemini',
            'primary_model': 'gemini-3.1-flash-lite',
            'free_tier_only': True
        }, user=self.admin_user)

        config_snapshot = get_active_ai_config()
        self.assertEqual(config_snapshot['primary_provider'], 'gemini')
        self.assertEqual(config_snapshot['primary_model'], 'gemini-3.1-flash-lite')
        self.assertEqual(cfg.AI_MODEL, 'gemini-3.1-flash-lite')

        client = get_ai_client()
        self.assertEqual(client.model, 'gemini-3.1-flash-lite')
        self.assertEqual(client.provider, 'gemini')

        # Now switch centrally to gemini-3.8-flash via system settings
        update_system_settings({
            'primary_provider': 'gemini',
            'primary_model': 'gemini-3.8-flash',
            'free_tier_only': True
        }, user=self.admin_user)

        # Verify dynamic reflection immediately
        config_snapshot = get_active_ai_config()
        self.assertEqual(config_snapshot['primary_model'], 'gemini-3.8-flash')
        self.assertEqual(cfg.AI_MODEL, 'gemini-3.8-flash')

        client_new = get_ai_client()
        self.assertEqual(client_new.model, 'gemini-3.8-flash')
        self.assertEqual(client_new.provider, 'gemini')

    # --------------------------------------------------------------------------
    # 5. Real-Time Server-Side Probe Testing (Mocked External HTTP)
    # --------------------------------------------------------------------------
    @patch('modules.admin_panel.services.ai_config_service.requests.post')
    def test_live_probe_gemini_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{
                "content": {
                    "parts": [{"text": '{"status": "ok", "provider": "gemini"}'}]
                }
            }]
        }
        mock_post.return_value = mock_response

        result = test_provider_live(
            provider='gemini',
            api_key_override='AIzaSyDummyKeyForTest123',
            model_override='gemini-3.1-flash-lite',
            user=self.admin_user
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn("responded successfully", result['message'])
        self.assertGreaterEqual(result['latency_ms'], 0)

        # Verify DB status updated
        cfg_obj = AIProviderConfig.objects.get(provider='gemini')
        self.assertEqual(cfg_obj.status, AIProviderConfig.STATUS_ACTIVE)
        self.assertEqual(cfg_obj.last_test_result, 'SUCCESS')

    @patch('modules.admin_panel.services.ai_config_service.requests.post')
    def test_live_probe_invalid_api_key(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": {
                "code": 400,
                "message": "API key not valid. Please pass a valid API key.",
                "status": "INVALID_ARGUMENT"
            }
        }
        mock_post.return_value = mock_response

        result = test_provider_live(
            provider='gemini',
            api_key_override='invalid_key',
            model_override='gemini-3.1-flash-lite',
            user=self.admin_user
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'INVALID_KEY')
        self.assertIn("API key not valid", result['message'])

    @patch('modules.admin_panel.services.ai_config_service.requests.post')
    def test_live_probe_model_unavailable_404(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "error": {
                "code": 404,
                "message": "models/gemini-2.5-flash is not found for API version v1beta",
                "status": "NOT_FOUND"
            }
        }
        mock_post.return_value = mock_response

        # Test model that is whitelisted in free tier catalog but returns 404 from API
        result = test_provider_live(
            provider='gemini',
            api_key_override='AIzaSyTestKey123',
            model_override='gemini-2.5-flash',
            user=self.admin_user
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'MODEL_UNAVAILABLE')
        self.assertIn("not found", result['message'].lower())

    @patch('modules.admin_panel.services.ai_config_service.requests.post')
    def test_live_probe_quota_exceeded_429(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": {
                "code": 429,
                "message": "Resource has been exhausted (e.g. check quota).",
                "status": "RESOURCE_EXHAUSTED"
            }
        }
        mock_post.return_value = mock_response

        result = test_provider_live(
            provider='gemini',
            api_key_override='AIzaSyTestKey123',
            model_override='gemini-3.1-flash-lite',
            user=self.admin_user
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'QUOTA_EXCEEDED')
        self.assertIn("quota or rate limit exceeded", result['message'])

    @patch('modules.admin_panel.services.ai_config_service.requests.post')
    def test_live_probe_network_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out after 30 seconds")

        result = test_provider_live(
            provider='gemini',
            api_key_override='AIzaSyTestKey123',
            model_override='gemini-3.1-flash-lite',
            user=self.admin_user
        )

        self.assertFalse(result['success'])
        self.assertEqual(result['status'], 'NETWORK_ERROR')
        self.assertIn("timed out", result['message'])

    # --------------------------------------------------------------------------
    # 6. Admin Panel View & API Security
    # --------------------------------------------------------------------------
    def test_unauthenticated_and_regular_user_blocked(self):
        # 1. Unauthenticated redirect to login
        resp = self.client.get('/admin-portal/ai-config/')
        self.assertEqual(resp.status_code, 302)

        # 2. Regular viewer user forbidden / redirected
        self.client.force_login(self.regular_user)
        resp = self.client.get('/admin-portal/ai-config/')
        self.assertEqual(resp.status_code, 302)

        resp_api = self.client.post('/admin-portal/ai-config/settings/save/', data=json.dumps({}), content_type='application/json')
        self.assertEqual(resp_api.status_code, 403)

    def test_authorized_admin_access(self):
        self.client.force_login(self.admin_user)
        resp = self.client.get('/admin-portal/ai-config/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "AI Models &amp; API Configuration")
        self.assertContains(resp, "Google Gemini")
        self.assertContains(resp, "OpenRouter")
        self.assertContains(resp, "xAI Grok")

    # --------------------------------------------------------------------------
    # 7. Audit Trail Sanitization
    # --------------------------------------------------------------------------
    def test_audit_trail_never_stores_plaintext_keys(self):
        raw_key = "AIzaSySuperSecretKeyToAudit987"
        save_provider_config('gemini', {
            'api_key': raw_key,
            'selected_model': 'gemini-3.1-flash-lite',
            'is_enabled': True
        }, user=self.admin_user)

        logs = AIConfigurationAuditLog.objects.filter(provider='gemini')
        self.assertTrue(logs.exists())
        for log in logs:
            self.assertNotIn(raw_key, log.message)
            self.assertNotIn(raw_key, json.dumps(log.details))

    # --------------------------------------------------------------------------
    # 8. Crawler Engine Integration Compatibility
    # --------------------------------------------------------------------------
    def test_page_classifier_uses_active_client(self):
        classifier = TwoStagePageClassifier()
        self.assertIsNotNone(classifier.client)
        self.assertEqual(classifier.client.model, cfg.AI_MODEL)

    # --------------------------------------------------------------------------
    # 9. Universal AI Provider Architecture & Dynamic Extensibility
    # --------------------------------------------------------------------------
    def test_all_major_providers_registered_in_ai_registry(self):
        from modules.crawler_engine.ai_api_client import AIProviderRegistry
        providers = AIProviderRegistry.list_providers()
        expected = ["gemini", "openrouter", "grok", "anthropic", "openai", "groq", "mistral", "deepseek", "ollama", "custom"]
        for p in expected:
            self.assertIn(p, providers)

    def test_dynamic_fallback_for_arbitrary_custom_provider(self):
        from modules.crawler_engine.ai_api_client import AIProviderRegistry, OpenAICompatibleApiClient
        # Any arbitrary new provider should resolve cleanly to OpenAICompatibleApiClient
        client = AIProviderRegistry.get("together_ai_custom", model="meta-llama/Llama-3-70b-chat-hf", api_key="test_key_xyz", base_url="https://api.together.xyz/v1")
        self.assertIsInstance(client, OpenAICompatibleApiClient)
        self.assertEqual(client.provider_name, "together_ai_custom")
        self.assertEqual(client.model, "meta-llama/Llama-3-70b-chat-hf")
        self.assertEqual(client.base_url, "https://api.together.xyz/v1")

    @patch('modules.admin_panel.services.ai_config_service.requests.post')
    def test_anthropic_live_test_probe_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "claude-3-5-haiku-latest",
            "content": [{"type": "text", "text": '{"status": "ok", "ping": "pong"}'}]
        }
        mock_post.return_value = mock_resp

        # Allow paid models during test probe
        settings = AISystemSettings.get_solo()
        settings.free_tier_only = False
        settings.save()

        result = test_provider_live(
            provider='anthropic',
            api_key_override='sk-ant-test-key-12345',
            model_override='claude-3-5-haiku-latest',
            user=self.admin_user
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn("Anthropic authentication successful", result['message'])

    @patch('modules.admin_panel.services.ai_config_service.requests.post')
    def test_ollama_local_probe_without_api_key(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "model": "llama3.2",
            "choices": [{"message": {"content": '{"status": "ok"}'}}]
        }
        mock_post.return_value = mock_resp

        result = test_provider_live(
            provider='ollama',
            model_override='llama3.2',
            user=self.admin_user
        )
        self.assertTrue(result['success'])
        self.assertEqual(result['status'], 'SUCCESS')
        self.assertIn("Ollama local runner is active", result['message'])

    def test_create_and_delete_custom_provider_api(self):
        self.client.force_login(self.admin_user)
        # 1. Create a custom provider
        create_payload = {
            "provider": "vllm_internal",
            "display_name": "vLLM Internal Cluster",
            "base_url": "http://10.0.0.50:8000/v1",
            "default_model": "mistral-7b-instruct-v0.3",
            "api_key": "vllm-secret-key-123",
            "available_models": "mistral-7b-instruct-v0.3, llama-3-8b"
        }
        resp = self.client.post('/admin-portal/ai-config/provider/create/', data=json.dumps(create_payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()['success'])

        cfg_obj = AIProviderConfig.objects.filter(provider="vllm_internal").first()
        self.assertIsNotNone(cfg_obj)
        self.assertEqual(cfg_obj.display_name, "vLLM Internal Cluster")
        self.assertEqual(cfg_obj.get_api_key(), "vllm-secret-key-123")

        # 2. Cannot delete core providers
        del_core = self.client.post('/admin-portal/ai-config/provider/gemini/delete/')
        self.assertEqual(del_core.status_code, 400)
        self.assertIn("Cannot delete core system provider", del_core.json()['message'])

        # 3. Delete custom provider
        del_resp = self.client.post('/admin-portal/ai-config/provider/vllm_internal/delete/')
        self.assertEqual(del_resp.status_code, 200)
        self.assertTrue(del_resp.json()['success'])
        self.assertFalse(AIProviderConfig.objects.filter(provider="vllm_internal").exists())
