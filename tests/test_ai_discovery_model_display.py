"""
tests/test_ai_discovery_model_display.py
========================================
Regression tests verifying that AI Bulk Discovery (/admin-portal/ai-discovery/)
always displays and reports the exact AI provider and model currently in use
(both configured and runtime-resolved), with zero hardcoded or stale model names.
"""

import os
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.contrib.auth import get_user_model

from modules.admin_panel.models import AIProviderConfig, AISystemSettings, Company, AuditTrail
from modules.admin_panel.services.ai_config_service import (
    bootstrap_default_configs,
    clear_config_cache,
    get_active_ai_config,
    resolve_active_ai_summary,
    save_provider_config,
    update_system_settings,
)
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.crawler_engine.ai_api_client import get_ai_client
from modules.crawler_engine.hybrid_ai_service import HybridAIExtractionService

User = get_user_model()


class AIDiscoveryModelDisplayTests(TestCase):

    def setUp(self):
        clear_config_cache()
        bootstrap_default_configs()
        self.admin_user = User.objects.create_superuser(
            username='ai_disc_admin',
            email='ai_disc_admin@example.com',
            password='Password123!',
            role='SUPERADMIN',
        )
        self.regular_user = User.objects.create_user(
            username='ai_disc_viewer',
            email='ai_disc_viewer@example.com',
            password='Password123!',
            role='VIEWER',
        )
        self.client = Client(HTTP_HOST='localhost')

    def tearDown(self):
        clear_config_cache()

    def test_no_hardcoded_random_model_in_ai_discovery_page(self):
        """AI Bulk Discovery page must never contain hardcoded 'Gemini 3.8 Flash (Live Web)'."""
        save_provider_config(
            'gemini',
            {
                'api_key': 'AIzaSyTestKey1234567890',
                'selected_model': 'gemini-2.5-flash',
                'is_enabled': True,
                'role': 'primary',
            },
            user=self.admin_user,
        )
        self.client.force_login(self.admin_user)
        resp = self.client.get('/admin-portal/ai-discovery/')
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode('utf-8')
        self.assertNotIn('Gemini 3.8 Flash (Live Web)', html)
        self.assertIn('gemini-2.5-flash (Google Gemini)', html)

    def test_provider_model_change_without_role_syncs_system_settings_and_discovery_ui(self):
        """Changing selected_model or custom_model on the active primary provider immediately updates AI Bulk Discovery."""
        save_provider_config(
            'gemini',
            {
                'api_key': 'AIzaSyTestKey1234567890',
                'selected_model': 'gemini-2.5-flash',
                'is_enabled': True,
                'role': 'primary',
            },
            user=self.admin_user,
        )

        # Update selected_model WITHOUT passing role
        ok, msg, code = save_provider_config(
            'gemini',
            {'selected_model': 'gemini-2.0-flash', 'custom_model': ''},
            user=self.admin_user,
        )
        self.assertTrue(ok, msg)

        settings_obj = AISystemSettings.get_solo()
        self.assertEqual(settings_obj.primary_model, 'gemini-2.0-flash')
        self.assertEqual(get_ai_client('gemini').model, 'gemini-2.0-flash')

        self.client.force_login(self.admin_user)
        resp = self.client.get('/admin-portal/ai-discovery/')
        self.assertContains(resp, 'gemini-2.0-flash (Google Gemini)')

        # Update custom_model WITHOUT passing role
        ok, msg, code = save_provider_config(
            'gemini',
            {'custom_model': 'gemini-2.5-flash-lite'},
            user=self.admin_user,
        )
        self.assertTrue(ok, msg)
        status_resp = self.client.get('/admin-portal/ai-discovery/ai-status/')
        self.assertEqual(status_resp.status_code, 200)
        payload = status_resp.json()
        self.assertEqual(payload['ai_model'], 'gemini-2.5-flash-lite')
        self.assertEqual(payload['ai_badge_label'], 'gemini-2.5-flash-lite (Google Gemini)')

    def test_switching_primary_provider_to_openrouter_updates_discovery_badge_and_client(self):
        """Switching primary provider via update_system_settings syncs AIProviderConfig and discovery UI."""
        save_provider_config(
            'openrouter',
            {
                'api_key': 'sk-or-v1-test-openrouter-key-12345',
                'selected_model': 'openrouter/free',
                'is_enabled': True,
            },
            user=self.admin_user,
        )
        settings_obj = AISystemSettings.get_solo()
        ok, msg, code = update_system_settings(
            {
                'version': settings_obj.version,
                'primary_provider': 'openrouter',
                'primary_model': 'google/gemma-2-9b-it:free',
                'fallback_enabled': False,
                'fallback_provider': '',
                'free_tier_only': True,
            },
            user=self.admin_user,
        )
        self.assertTrue(ok, msg)

        or_cfg = AIProviderConfig.objects.get(provider='openrouter')
        self.assertEqual(or_cfg.effective_model, 'google/gemma-2-9b-it:free')
        self.assertEqual(get_ai_client('openrouter').model, 'google/gemma-2-9b-it:free')

        self.client.force_login(self.admin_user)
        resp = self.client.get('/admin-portal/ai-discovery/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'google/gemma-2-9b-it:free (OpenRouter)')

    def test_unconfigured_or_empty_primary_never_shows_random_gemini_model(self):
        """When no primary/fallback provider is configured, UI must show 'No AI Model Configured'."""
        settings_obj = AISystemSettings.get_solo()
        update_system_settings(
            {
                'version': settings_obj.version,
                'primary_provider': '',
                'primary_model': '',
                'fallback_enabled': False,
                'fallback_provider': '',
                'fallback_model': '',
            },
            user=self.admin_user,
        )
        summary = resolve_active_ai_summary(force_refresh=True)
        self.assertFalse(summary['is_configured'])
        self.assertEqual(summary['model'], '')
        self.assertEqual(summary['badge_label'], 'No AI Model Configured')

        self.client.force_login(self.admin_user)
        resp = self.client.get('/admin-portal/ai-discovery/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'No AI Model Configured')
        self.assertNotIn('gemini-3.1-flash-lite', resp.content.decode('utf-8'))

    def test_missing_primary_key_uses_ready_failover_or_marks_needs_key(self):
        """If primary provider has no key, report active failover if ready, else 'Needs API Key'."""
        save_provider_config(
            'gemini',
            {'clear_api_key': True, 'selected_model': 'gemini-2.5-flash'},
            user=self.admin_user,
        )
        save_provider_config(
            'openrouter',
            {
                'api_key': 'sk-or-v1-test-key-999',
                'selected_model': 'openrouter/free',
                'is_enabled': True,
            },
            user=self.admin_user,
        )
        settings_obj = AISystemSettings.get_solo()
        update_system_settings(
            {
                'version': settings_obj.version,
                'primary_provider': 'gemini',
                'primary_model': 'gemini-2.5-flash',
                'fallback_enabled': True,
                'fallback_provider': 'openrouter',
                'fallback_model': 'openrouter/free',
            },
            user=self.admin_user,
        )
        with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
            summary_with_fb = resolve_active_ai_summary(force_refresh=True)
            self.assertEqual(summary_with_fb['provider_id'], 'openrouter')
            self.assertEqual(summary_with_fb['model'], 'openrouter/free')
            self.assertTrue(summary_with_fb['using_failover'])
            self.assertIn('Failover', summary_with_fb['badge_label'])

            # Disable fallback -> should reflect that primary needs API key
            settings_obj.refresh_from_db()
            update_system_settings(
                {
                    'version': settings_obj.version,
                    'primary_provider': 'gemini',
                    'primary_model': 'gemini-2.5-flash',
                    'fallback_enabled': False,
                    'fallback_provider': '',
                    'fallback_model': '',
                },
                user=self.admin_user,
            )
            summary_no_fb = resolve_active_ai_summary(force_refresh=True)
            self.assertFalse(summary_no_fb['is_ready'])
            self.assertEqual(summary_no_fb['status'], 'NEEDS_KEY')
            self.assertIn('Needs API Key', summary_no_fb['badge_label'])

    def test_ai_status_api_requires_admin_and_never_exposes_secrets(self):
        """ai_status_api must reject unauthenticated/non-admin callers and never expose API keys."""
        from django.test import RequestFactory
        from modules.admin_panel.views.batch_discovery_views import ai_status_api

        rf = RequestFactory()
        req_unauth = rf.get('/admin-portal/ai-discovery/ai-status/')
        from django.contrib.auth.models import AnonymousUser
        req_unauth.user = AnonymousUser()
        self.assertEqual(ai_status_api(req_unauth).status_code, 401)

        req_non_admin = rf.get('/admin-portal/ai-discovery/ai-status/')
        req_non_admin.user = self.regular_user
        self.assertEqual(ai_status_api(req_non_admin).status_code, 401)

        unauth_resp = self.client.get('/admin-portal/ai-discovery/ai-status/')
        self.assertEqual(unauth_resp.status_code, 302)

        self.client.force_login(self.regular_user)
        non_admin_resp = self.client.get(
            '/admin-portal/ai-discovery/ai-status/',
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(non_admin_resp.status_code, 403)

        secret_key = 'AIzaSyTopSecretKeyDoNotExpose999'
        save_provider_config(
            'gemini',
            {'api_key': secret_key, 'selected_model': 'gemini-2.5-flash', 'role': 'primary'},
            user=self.admin_user,
        )
        self.client.force_login(self.admin_user)
        ok_resp = self.client.get('/admin-portal/ai-discovery/ai-status/')
        self.assertEqual(ok_resp.status_code, 200)
        body = ok_resp.content.decode('utf-8')
        self.assertNotIn(secret_key, body)
        self.assertEqual(ok_resp.json()['ai_model'], 'gemini-2.5-flash')

    def test_runtime_failover_and_disabled_extras_are_tracked_in_process_single_company(self):
        """
        HybridAIExtractionService must skip disabled extra providers and report the actual
        runtime provider/model used back to BatchDiscoveryService.process_single_company.
        """
        save_provider_config(
            'gemini',
            {'api_key': 'AIzaSyFakeKey1', 'selected_model': 'gemini-2.5-flash', 'is_enabled': True, 'role': 'primary'},
            user=self.admin_user,
        )
        save_provider_config(
            'openrouter',
            {'api_key': 'sk-or-v1-test-key', 'selected_model': 'openrouter/free', 'is_enabled': True, 'role': 'failover'},
            user=self.admin_user,
        )
        # Ensure openai is disabled even if it has a key and ACTIVE status
        openai_cfg = AIProviderConfig.objects.get(provider='openai')
        openai_cfg.set_api_key('sk-openai-disabled')
        openai_cfg.is_enabled = False
        openai_cfg.status = AIProviderConfig.STATUS_ACTIVE
        openai_cfg.save()
        clear_config_cache()

        called_providers = []

        class FailingPrimaryClient:
            model = 'gemini-2.5-flash'
            def execute_structured_prompt(self, prompt):
                called_providers.append('gemini')
                raise RuntimeError('Simulated 429 quota error')

        class SucceedingFallbackClient:
            model = 'openrouter/free'
            def execute_structured_prompt(self, prompt):
                called_providers.append('openrouter')
                return [], 'nvidia/nemotron-runtime-test:free'

        def fake_get_ai_client(prov=None, model=None):
            if prov == 'gemini':
                return FailingPrimaryClient()
            if prov == 'openrouter':
                return SucceedingFallbackClient()
            called_providers.append(f'unexpected:{prov}')
            raise RuntimeError(f'Unexpected provider {prov}')

        test_domain = 'runtimemodeltrace.in'
        home_html = (
            '<html><head><title>Trace Corp</title></head><body>'
            '<nav><a href="https://www.runtimemodeltrace.in/careers">Careers</a>'
            '<a href="https://www.runtimemodeltrace.in/csr">CSR</a></nav>'
            '<footer>Corporate Office: Bengaluru, Karnataka</footer></body></html>'
        )
        csr_html = (
            '<html><body><h1>CSR Programs</h1>'
            '<p>We operate rural education initiatives across Karnataka districts under Schedule VII.</p>'
            '</body></html>'
        )

        def fake_fetch(url, timeout=6):
            u = url.rstrip('/')
            if u == f'https://www.{test_domain}':
                return home_html, 'Trace Corp Bengaluru Karnataka', 200
            if u == f'https://www.{test_domain}/careers':
                return '<html><body><h1>Careers</h1></body></html>', 'Careers', 200
            if u == f'https://www.{test_domain}/csr':
                return csr_html, 'We operate rural education initiatives across Karnataka districts under Schedule VII. ' * 2, 200
            return '', '', 404

        with patch('modules.crawler_engine.hybrid_ai_service.get_ai_client', side_effect=fake_get_ai_client), \
             patch('modules.crawler_engine.hybrid_ai_service.telemetry_store.record_event'), \
             patch.object(BatchDiscoveryService, 'fetch_page_content', side_effect=fake_fetch), \
             patch.object(BatchDiscoveryService, 'discover_all_real_jobs', return_value=[]):
            res = BatchDiscoveryService.process_single_company({
                'company_name': 'Trace Corp',
                'homepage_url': f'https://www.{test_domain}',
            })

        self.assertEqual(res['status'], 'success')
        self.assertEqual(called_providers, ['gemini', 'openrouter'])
        ai_cfg = res.get('ai_config', {})
        self.assertTrue(ai_cfg['ai_invoked'])
        self.assertTrue(ai_cfg['ai_succeeded'])
        self.assertEqual(ai_cfg['used_provider'], 'openrouter')
        self.assertEqual(ai_cfg['used_model'], 'nvidia/nemotron-runtime-test:free')
        self.assertTrue(ai_cfg['fallback_used'])
        self.assertTrue(any('nvidia/nemotron-runtime-test:free' in line for line in res['logs']))

    def test_openai_compatible_and_anthropic_clients_parse_json_cleanly(self):
        """OpenAICompatibleApiClient (Groq/OpenAI/etc.) and AnthropicApiClient must parse JSON via _clean_json_text."""
        save_provider_config(
            'groq',
            {'api_key': 'gsk-test-123456', 'selected_model': 'llama-3.3-70b-versatile', 'is_enabled': True, 'role': 'primary'},
            user=self.admin_user,
        )
        groq_client = get_ai_client('groq')
        mock_groq_resp = MagicMock()
        mock_groq_resp.status_code = 200
        mock_groq_resp.json.return_value = {
            'model': 'llama-3.3-70b-versatile',
            'choices': [{'message': {'content': '```json\n[{"candidate_id": 1, "job_title": "Engineer"}]\n```'}}],
        }
        with patch('modules.crawler_engine.ai_api_client.requests.post', return_value=mock_groq_resp):
            parsed, actual_model = groq_client.execute_structured_prompt('Extract jobs')
        self.assertEqual(actual_model, 'llama-3.3-70b-versatile')
        self.assertEqual(parsed, [{'candidate_id': 1, 'job_title': 'Engineer'}])

        save_provider_config(
            'anthropic',
            {'api_key': 'sk-ant-test-123456', 'selected_model': 'claude-3-5-haiku-latest', 'is_enabled': True, 'allow_paid_calls': True, 'role': 'primary'},
            user=self.admin_user,
        )
        ant_client = get_ai_client('anthropic')
        mock_ant_resp = MagicMock()
        mock_ant_resp.status_code = 200
        mock_ant_resp.json.return_value = {
            'model': 'claude-3-5-haiku-latest',
            'content': [{'type': 'text', 'text': '{"is_actual_project": false}'}],
        }
        with patch('modules.crawler_engine.ai_api_client.requests.post', return_value=mock_ant_resp):
            parsed_ant, actual_ant_model = ant_client.execute_structured_prompt('Check CSR')
        self.assertEqual(actual_ant_model, 'claude-3-5-haiku-latest')
        self.assertEqual(parsed_ant, {'is_actual_project': False})

    def test_hybrid_service_never_invokes_unconfigured_or_inactive_extra_providers(self):
        """
        HybridAIExtractionService must NOT fall back to hardcoded gemini or Inactive (not_used) extra providers
        when unconfigured or when fallback_enabled is False.
        """
        # Mark openrouter and openai as is_enabled=True, ACTIVE, with keys — but role is Inactive (not_used)
        save_provider_config(
            'openrouter',
            {'api_key': 'sk-or-v1-inactive-key', 'selected_model': 'openrouter/free', 'is_enabled': True, 'role': 'not_used'},
            user=self.admin_user,
        )
        or_cfg = AIProviderConfig.objects.get(provider='openrouter')
        or_cfg.status = AIProviderConfig.STATUS_ACTIVE
        or_cfg.save()

        settings_obj = AISystemSettings.get_solo()
        update_system_settings(
            {
                'version': settings_obj.version,
                'primary_provider': '',
                'primary_model': '',
                'fallback_enabled': False,
                'fallback_provider': '',
                'fallback_model': '',
            },
            user=self.admin_user,
        )

        with patch('modules.crawler_engine.hybrid_ai_service.get_ai_client') as mock_get_client:
            csr_res = HybridAIExtractionService.extract_unstructured_csr_projects(
                company_id='COMP_1',
                company_name='Test Co',
                raw_content='We support rural education programs under Section 135 Schedule VII across districts.',
                csr_url='https://example.com/csr',
            )
            job_res = HybridAIExtractionService.extract_unstructured_jobs(
                company_id='COMP_1',
                company_name='Test Co',
                raw_content='Senior Software Engineer\n',
                careers_url='https://example.com/careers',
                candidates=[{'id': 1, 'text': 'Senior Software Engineer', 'card_context': 'Senior Software Engineer', 'href': 'https://example.com/jobs/1'}],
            )
        self.assertEqual(csr_res, [])
        self.assertEqual(job_res, [])
        mock_get_client.assert_not_called()

        # Now configure primary=gemini with fallback_enabled=False; failing gemini must NOT silently call openrouter
        save_provider_config(
            'gemini',
            {'api_key': 'AIzaSyTestKey1234', 'selected_model': 'gemini-2.5-flash', 'is_enabled': True, 'role': 'primary'},
            user=self.admin_user,
        )
        called = []

        class FailingGemini:
            model = 'gemini-2.5-flash'
            def execute_structured_prompt(self, prompt):
                called.append('gemini')
                raise RuntimeError('Simulated Gemini failure')

        with patch('modules.crawler_engine.hybrid_ai_service.get_ai_client', return_value=FailingGemini()), \
             patch('modules.crawler_engine.hybrid_ai_service.telemetry_store.record_event'):
            res2 = HybridAIExtractionService.extract_unstructured_csr_projects(
                company_id='COMP_1',
                company_name='Test Co',
                raw_content='We support rural education programs under Section 135 Schedule VII across districts.',
                csr_url='https://example.com/csr',
            )
        self.assertEqual(res2, [])
        self.assertEqual(called, ['gemini'])

    def test_save_selected_model_clears_stale_custom_model_and_not_used_clears_primary_model(self):
        """Selecting a catalog model in AI Config clears stale custom_model; setting role='not_used' clears primary_model."""
        save_provider_config(
            'gemini',
            {
                'api_key': 'AIzaSyTestKey1234',
                'selected_model': 'gemini-2.5-flash',
                'custom_model': 'stale-custom-model',
                'role': 'primary',
            },
            user=self.admin_user,
        )
        # Simulate AI Config UI saving selected_model without custom_model field
        ok, msg, code = save_provider_config(
            'gemini',
            {'selected_model': 'gemini-2.0-flash', 'role': 'primary'},
            user=self.admin_user,
        )
        self.assertTrue(ok, msg)
        gem_cfg = AIProviderConfig.objects.get(provider='gemini')
        self.assertEqual(gem_cfg.custom_model, '')
        self.assertEqual(gem_cfg.effective_model, 'gemini-2.0-flash')
        self.assertEqual(AISystemSettings.get_solo().primary_model, 'gemini-2.0-flash')

        # Setting role='not_used' clears primary_provider and primary_model
        ok, msg, code = save_provider_config('gemini', {'role': 'not_used'}, user=self.admin_user)
        self.assertTrue(ok, msg)
        s = AISystemSettings.get_solo()
        self.assertEqual(s.primary_provider, '')
        self.assertEqual(s.primary_model, '')
        self.assertEqual(resolve_active_ai_summary(force_refresh=True)['badge_label'], 'No AI Model Configured')

    def test_resolve_active_ai_summary_flags_cost_blocked_when_free_tier_only_blocks_grok(self):
        """When free_tier_only=True blocks Grok (no free credits), resolve_active_ai_summary reports COST_BLOCKED."""
        with patch.dict(os.environ, {'GROK_FREE_CREDITS_CONFIRMED': 'true'}):
            ok, msg, code = save_provider_config(
                'grok',
                {
                    'api_key': 'xai-test-key-1234',
                    'selected_model': 'grok-2-latest',
                    'is_enabled': True,
                    'allow_paid_calls': True,
                    'role': 'primary',
                },
                user=self.admin_user,
            )
            self.assertTrue(ok, msg)
            s = AISystemSettings.get_solo()
            ok_s, msg_s, code_s = update_system_settings(
                {
                    'version': s.version,
                    'primary_provider': 'grok',
                    'primary_model': 'grok-2-latest',
                    'fallback_enabled': False,
                    'fallback_provider': '',
                    'fallback_model': '',
                    'free_tier_only': True,
                },
                user=self.admin_user,
            )
            self.assertTrue(ok_s, msg_s)

        with patch.dict(os.environ, {'GROK_FREE_CREDITS_CONFIRMED': 'false'}):
            summary = resolve_active_ai_summary(force_refresh=True)
        self.assertFalse(summary['is_ready'])
        self.assertEqual(summary['status'], 'COST_BLOCKED')
        self.assertIn('Zero-Cost Guard Blocked', summary['badge_label'])

    def test_process_single_company_cleans_up_trace_on_exception(self):
        """Thread-local AI trace must be cleaned up via finally even if discovery raises mid-execution."""
        HybridAIExtractionService.end_trace()

        def _crash_after_trace(*args, **kwargs):
            HybridAIExtractionService._append_trace({'provider': 'stale', 'model': 'stale-model', 'success': True})
            raise RuntimeError('Simulated unexpected crash')

        with patch.object(
            BatchDiscoveryService,
            'fetch_page_content',
            return_value=('<html><head><title>Crash Co</title></head><body></body></html>', '', 200),
        ), patch.object(
            BatchDiscoveryService,
            '_run_single_company_discovery',
            side_effect=_crash_after_trace,
        ):
            with self.assertRaises(RuntimeError):
                BatchDiscoveryService.process_single_company(
                    {'company_name': 'Crash Co', 'homepage_url': 'https://example.com'}
                )

        # Trace must be completely empty after process_single_company exits on exception
        self.assertEqual(HybridAIExtractionService.end_trace(), [])


class AIDiscoveryPlaywrightE2ETests(StaticLiveServerTestCase):

    def setUp(self):
        clear_config_cache()
        bootstrap_default_configs()
        self.admin_user = User.objects.create_superuser(
            username='pw_ai_admin',
            email='pw_ai_admin@example.com',
            password='Password123!',
            role='SUPERADMIN',
        )
        save_provider_config(
            'gemini',
            {'api_key': 'AIzaSyPlaywrightTestKey1234', 'selected_model': 'gemini-2.5-flash', 'is_enabled': True, 'role': 'primary'},
            user=self.admin_user,
        )
        save_provider_config(
            'openrouter',
            {'api_key': 'sk-or-v1-playwright-test-key', 'selected_model': 'openrouter/free', 'is_enabled': True, 'role': 'not_used'},
            user=self.admin_user,
        )
        settings_obj = AISystemSettings.get_solo()
        update_system_settings(
            {
                'version': settings_obj.version,
                'primary_provider': 'gemini',
                'primary_model': 'gemini-2.5-flash',
                'fallback_enabled': False,
                'fallback_provider': '',
                'fallback_model': '',
                'free_tier_only': True,
            },
            user=self.admin_user,
        )

    def tearDown(self):
        clear_config_cache()

    def test_browser_ai_config_switch_back_navigation_runtime_failover_and_log_export(self):
        """
        Real Chromium Playwright E2E test:
        1. Verify initial configured model on /admin-portal/ai-discovery/.
        2. Switch Primary provider/model in /admin-portal/ai-config/ to OpenRouter (openrouter/free).
        3. Return via browser Back navigation and verify header/init/footer badges auto-update via pageshow/ai-status.
        4. Simulate a discovery response with runtime failover (Groq llama-3.3-70b-versatile) and verify:
           - Terminal footer updates to runtime model while header stays configured model.
           - Triggering window focus does NOT clobber the runtime footer label.
           - Exported .log file contains the runtime Active AI Model.
        """
        from playwright.sync_api import sync_playwright

        console_errors = []
        page_errors = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(accept_downloads=True, viewport={'width': 1440, 'height': 900})
            page = context.new_page()
            page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
            page.on('pageerror', lambda exc: page_errors.append(str(exc)))

            # 1. Login
            page.goto(f'{self.live_server_url}/admin-portal/login/', wait_until='networkidle')
            page.fill("input[name='username']", 'pw_ai_admin')
            page.fill("input[name='password']", 'Password123!')
            page.click("button[type='submit']")
            page.wait_for_load_state('networkidle')

            # 2. Open AI Bulk Discovery
            page.goto(f'{self.live_server_url}/admin-portal/ai-discovery/', wait_until='networkidle')
            self.assertEqual(page.inner_text('#header-ai-model-text').strip(), 'gemini-2.5-flash (Google Gemini)')
            self.assertEqual(page.inner_text('#footer-ai-model-text').strip(), 'gemini-2.5-flash (Google Gemini)')
            self.assertEqual(page.inner_text('#init-ai-model-text').strip(), 'gemini-2.5-flash (Google Gemini)')

            # 3. Click "Configure AI Models" link, switch OpenRouter to Primary, save
            page.click("a[href='/admin-portal/ai-config/']")
            page.wait_for_load_state('networkidle')
            if page.locator('#drawerBackdrop.is-open').is_visible():
                page.click('#drawerBackdrop')
                page.wait_for_timeout(150)
            page.click('#row-openrouter')
            page.wait_for_timeout(150)
            page.select_option('#drawerModelSelect', 'openrouter/free')
            page.click('#roleCardPrimary')
            page.click('#btnDrawerSave')
            page.wait_for_timeout(500)

            # 4. Navigate back via browser Back button and verify pageshow + /ai-status/ updates badges
            page.go_back(wait_until='networkidle')
            page.wait_for_function(
                "() => document.getElementById('header-ai-model-text')?.textContent?.trim() === 'openrouter/free (OpenRouter)'",
                timeout=5000,
            )
            self.assertEqual(page.inner_text('#footer-ai-model-text').strip(), 'openrouter/free (OpenRouter)')
            self.assertEqual(page.inner_text('#init-ai-model-text').strip(), 'openrouter/free (OpenRouter)')

            # 5. Intercept process-company POST to simulate runtime failover to Groq
            def handle_process_company(route):
                route.fulfill(
                    status=200,
                    content_type='application/json',
                    body=json.dumps({
                        'status': 'success',
                        'is_new_company': False,
                        'company_name': 'Example Corp',
                        'company_id': 'COMP_PW_1',
                        'sector': 'Information Technology',
                        'headquarters': 'Bengaluru, Karnataka',
                        'website_url': 'https://www.example.com',
                        'careers_url': 'https://www.example.com/careers',
                        'csr_url': 'https://www.example.com/csr',
                        'jobs_discovered': 0,
                        'jobs_imported': 0,
                        'csr_discovered': 0,
                        'csr_imported': 0,
                        'jobs': [],
                        'csr': [],
                        'logs': ['AI Model Used: llama-3.3-70b-versatile (Groq Cloud (Fast Llama) · Failover)'],
                        'ai_config': {
                            'provider_id': 'openrouter',
                            'provider_display': 'OpenRouter',
                            'model': 'openrouter/free',
                            'status': 'ACTIVE',
                            'is_ready': True,
                            'badge_label': 'openrouter/free (OpenRouter)',
                            'ai_invoked': True,
                            'ai_succeeded': True,
                            'used_provider': 'groq',
                            'used_provider_display': 'Groq Cloud (Fast Llama)',
                            'used_model': 'llama-3.3-70b-versatile',
                            'fallback_used': True,
                            'models_used': ['llama-3.3-70b-versatile (Groq Cloud (Fast Llama) · Failover)'],
                        },
                    }),
                )

            page.route('**/admin-portal/ai-discovery/process-company/', handle_process_company)
            page.fill('#quick-company-input', 'Example Corp')
            page.fill('#quick-website-input', 'https://www.example.com')
            page.click('#btn-quick-discover')

            page.wait_for_function(
                "() => document.getElementById('footer-ai-model-text')?.textContent?.includes('llama-3.3-70b-versatile')",
                timeout=5000,
            )
            self.assertEqual(page.inner_text('#header-ai-model-text').strip(), 'openrouter/free (OpenRouter)')
            self.assertEqual(
                page.inner_text('#footer-ai-model-text').strip(),
                'llama-3.3-70b-versatile (Groq Cloud (Fast Llama) · Failover)',
            )

            # 6. Trigger forced status refresh (as focus/visibility would) and confirm runtime footer is NOT clobbered
            page.evaluate('() => refreshActiveAiModelBadge(true)')
            page.wait_for_timeout(400)
            self.assertEqual(
                page.inner_text('#footer-ai-model-text').strip(),
                'llama-3.3-70b-versatile (Groq Cloud (Fast Llama) · Failover)',
            )

            # 7. Export terminal log file and verify Active AI Model header
            with page.expect_download() as dl_info:
                page.evaluate('() => downloadTerminalLogFile()')
            download = dl_info.value
            log_path = download.path()
            with open(log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
            self.assertIn('Active AI Model: llama-3.3-70b-versatile (Groq Cloud (Fast Llama) · Failover)', log_content)

            browser.close()

        self.assertEqual(console_errors, [], f'Browser console errors: {console_errors}')
        self.assertEqual(page_errors, [], f'Browser page errors: {page_errors}')
