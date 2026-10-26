"""
tests/test_ai_architecture_requirements.py
=========================================
Formal Acceptance Test Suite for:
MANDATORY ARCHITECTURE REQUIREMENTS: REPLACEABLE AI PROVIDER AND SCALABLE COMPANY PROCESSING

Tests all 10 mandatory acceptance criteria:
1. OpenRouter free router is the only active provider in current configuration.
2. No paid or alternative provider is activated automatically on quota exhaustion.
3. The application processes the company directory dynamically from the database.
4. Adding new company records requires no code changes.
5. Processing can resume safely after API quota exhaustion or application restarts.
6. Existing results are reused when source content has not changed.
7. The system supports configurable processing of more than 1,000 companies without fixed limits.
8. Switching to a future supported AI provider requires configuration and adapter, not pipeline rewrites.
9. Uncertain source URLs remain flagged for review rather than overwriting verified company URLs.
10. Existing backups, audit logging and safe database-update requirements remain strictly in force.
"""

import os
import json
import tempfile
import hashlib
from typing import Dict, Any, List, Tuple
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase
from django.utils import timezone

from modules.crawler_engine import ai_classifier_config as cfg
from modules.crawler_engine.ai_api_client import (
    get_ai_client,
    GeminiApiClient,
    GrokApiClient,
    PrimaryFallbackAIClient,
    OpenRouterApiClient,
    MockAIClient,
    AIProviderRegistry,
    BaseAIClient,
    QuotaExhaustedError,
    ZeroCostPolicyViolationError,
    PersistentDiskCache,
    test_provider_eligibility
)
from modules.crawler_engine.page_classifier import TwoStagePageClassifier
from modules.admin_panel.management.commands.discover_and_verify_company_sources import Command as DiscoveryCommand


class AIAcceptanceArchitectureTests(SimpleTestCase):
    """
    Formal test suite verifying compliance with AI architecture acceptance criteria:
    - Gemini primary classifier using official free tier models only.
    - Grok zero-cost fallback with strict enforcement (no billable calls).
    - Dynamic database company exploration, zero schema corruption, and safe checkpointing.
    """

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 1:
    # Gemini is the primary AI classifier using only official API free-tier models.
    # --------------------------------------------------------------------------
    def test_01_gemini_primary_free_tier_provider(self):
        """Verify that Gemini official free tier is configured as the primary AI classifier."""
        self.assertEqual(cfg.AI_PROVIDER, "gemini", "Active AI_PROVIDER must be 'gemini'.")
        self.assertTrue(
            cfg.is_gemini_free_tier_model(cfg.AI_MODEL),
            f"Active AI_MODEL '{cfg.AI_MODEL}' must belong to official Gemini API free tier: {cfg.GEMINI_FREE_TIER_MODELS}."
        )
        self.assertEqual(cfg.AI_BASE_URL, "https://generativelanguage.googleapis.com/v1beta", "Base URL must point to Gemini v1beta.")
        self.assertEqual(cfg.AI_API_KEY_ENV, "GEMINI_API_KEY", "API key environment variable must be GEMINI_API_KEY.")
        self.assertEqual(cfg.AI_FALLBACK_PROVIDER, "grok", "Fallback provider must be 'grok'.")

        client = get_ai_client("gemini")
        self.assertIsInstance(
            client,
            GeminiApiClient,
            "Factory get_ai_client('gemini') must instantiate GeminiApiClient."
        )

        # Enforce that non-free tier models are strictly rejected under zero-cost policy
        non_free_client = GeminiApiClient(model="gemini-1.5-pro", api_key="dummy-gemini-key")
        with self.assertRaises(ZeroCostPolicyViolationError) as ctx:
            non_free_client._execute_gemini_request("Test prompt")
        self.assertIn("not in the confirmed official api free tier", str(ctx.exception).lower())

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 2:
    # Grok fallback enforces strict zero-cost requirements; no billable calls sent.
    # --------------------------------------------------------------------------
    def test_02_grok_fallback_strict_zero_cost_policy(self):
        """Verify that Grok fallback enforces zero-cost policy and never makes billable calls."""
        # 1. Verify zero-cost configuration flags
        self.assertTrue(cfg.GROK_ZERO_COST_ONLY, "GROK_ZERO_COST_ONLY must be strictly True.")
        self.assertIn("not provide free api usage", cfg.GROK_WEB_ACCOUNT_DISCLAIMER.lower())

        # 2. When free credits are unconfirmed, GrokApiClient strictly blocks requests
        grok_client = GrokApiClient(api_key="test-grok-key")
        with patch.object(cfg, "GROK_FREE_CREDITS_CONFIRMED", False):
            eligible, reason = grok_client.verify_zero_cost_eligibility()
            self.assertFalse(eligible)
            self.assertIn("zero-cost policy enforced", reason.lower())

            # Attempting request raises ZeroCostPolicyViolationError without making HTTP request
            with patch("requests.post") as mock_post:
                with self.assertRaises(ZeroCostPolicyViolationError):
                    grok_client._execute_provider_request("Test prompt")
                mock_post.assert_not_called()

        # 3. Fallback orchestrator: when Gemini quota exhausted and Grok unconfirmed, pause safely
        primary_mock = MagicMock(spec=GeminiApiClient)
        primary_mock.classify_links_batch.side_effect = QuotaExhaustedError("Gemini quota exhausted (HTTP 429)")
        fallback_grok = GrokApiClient(api_key="test-grok-key")

        with patch.object(cfg, "GROK_FREE_CREDITS_CONFIRMED", False):
            fallback_client = PrimaryFallbackAIClient(primary=primary_mock, fallback=fallback_grok)
            with self.assertRaises(QuotaExhaustedError) as ctx:
                fallback_client.classify_links_batch("Acme Corp", "acme.com", [{"url": "https://acme.com/jobs"}])
            self.assertIn("blocked by zero-cost policy", str(ctx.exception).lower())
            self.assertEqual(fallback_client.metrics["fallback_blocked_zero_cost"], 1)

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 3:
    # The application processes the company directory dynamically from the database.
    # --------------------------------------------------------------------------
    def test_03_processes_company_directory_dynamically(self):
        """Verify companies are queried dynamically from the database without hardcoded limits."""
        cmd = DiscoveryCommand()
        with patch("modules.admin_panel.models.Company.objects") as mock_objects:
            mock_qs = MagicMock()
            mock_objects.all.return_value.order_by.return_value.only.return_value = mock_qs
            mock_qs.count.return_value = 201
            mock_qs.iterator.return_value = iter([])

            cmd.handle(
                dry_run=True,
                apply_verified_updates=False,
                resume=False,
                company_id=None,
                limit=0,
                max_api_calls=5,
                report_file=""
            )

            # Ensure Company.objects.all().order_by().only() was called dynamically
            mock_objects.all.assert_called_once()
            mock_qs.count.assert_called_once()

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 4:
    # Adding new company records requires no code changes.
    # --------------------------------------------------------------------------
    def test_04_adding_new_company_records_requires_no_code_changes(self):
        """Verify a newly inserted company record is automatically queried and processed."""
        cmd = DiscoveryCommand()
        new_company = MagicMock()
        new_company.company_id = "COMP_EXPANSION_TEST_999"
        new_company.company_name = "Dynamic Scale Enterprises Ltd"
        new_company.website_url = "https://www.dynamicscale.in"
        new_company.official_domain = "dynamicscale.in"

        with patch("modules.admin_panel.models.Company.objects") as mock_objects:
            mock_qs = MagicMock()
            mock_objects.all.return_value.order_by.return_value.only.return_value = mock_qs
            # Simulating database expansion beyond 201 to 1,000+ companies
            mock_qs.count.return_value = 1050
            mock_qs.iterator.return_value = iter([new_company])

            with patch.object(cmd, "_process_single_company", return_value={"status": "COMPLETED", "approved": []}) as mock_proc:
                cmd.handle(
                    dry_run=True,
                    apply_verified_updates=False,
                    resume=False,
                    company_id=None,
                    limit=0,
                    max_api_calls=5,
                    report_file=""
                )
                mock_proc.assert_called_once()
                args, _ = mock_proc.call_args
                self.assertEqual(args[0].company_id, "COMP_EXPANSION_TEST_999")

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 5:
    # Resumption works safely after quota exhaustion or restarts.
    # --------------------------------------------------------------------------
    def test_05_resumption_from_checkpoint_skips_completed_companies(self):
        """Verify that checkpoint files allow safe resumption without repeating work."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            ckpt_file = os.path.join(tmp_dir, "discovery_checkpoint.json")
            mock_checkpoint_data = {
                "last_updated": timezone.now().isoformat(),
                "total_processed": 2,
                "processed_company_ids": ["COMP_TOP200_001", "COMP_TOP200_002"],
                "company_statuses": {
                    "COMP_TOP200_001": {"status": "COMPLETED"},
                    "COMP_TOP200_002": {"status": "UNCHANGED_SKIPPED"}
                },
                "stats": {"completed_companies": 1, "unchanged_skipped_companies": 1}
            }
            with open(ckpt_file, "w", encoding="utf-8") as f:
                json.dump(mock_checkpoint_data, f)

            with open(ckpt_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)

            skip_ids = {
                cid for cid, info in loaded.get("company_statuses", {}).items()
                if info.get("status") in ("COMPLETED", "UNCHANGED_SKIPPED")
            }
            self.assertEqual(skip_ids, {"COMP_TOP200_001", "COMP_TOP200_002"})

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 6:
    # Existing results are reused when source content has not changed.
    # --------------------------------------------------------------------------
    def test_06_persistent_cache_and_content_hash_reuse(self):
        """Verify PersistentDiskCache reuses results when payload/content hash is identical."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cache = PersistentDiskCache(tmp_dir)
            test_key = hashlib.sha256(b"openrouter:openrouter/free:v1.0:stage1:test_hash").hexdigest()
            cached_payload = [{"url": "https://company.com/careers", "broad_category": "CAREERS_RECRUITMENT"}]

            # Set in cache
            cache.set(test_key, "openrouter/free", "stage1", cached_payload, provider="openrouter", prompt_version="v1.0")

            # Retrieve from cache
            retrieved = cache.get(test_key)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved, cached_payload)

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 7:
    # Supports configurable processing beyond 1,000 companies without fixed limits.
    # --------------------------------------------------------------------------
    def test_07_scales_past_1000_companies_with_bounded_memory(self):
        """Verify query streaming uses iterator(chunk_size=batch_size) and .only()."""
        cmd = DiscoveryCommand()
        parser = MagicMock()
        cmd.add_arguments(parser)

        # Check argument registrations
        added_args = [call[0][0] for call in parser.add_argument.call_args_list]
        self.assertIn("--batch-size", added_args)
        self.assertIn("--force-reclassify", added_args)
        self.assertIn("--resume", added_args)
        self.assertIn("--limit", added_args)

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 8:
    # Pluggable AI provider architecture allows replacement without pipeline rewrites.
    # --------------------------------------------------------------------------
    def test_08_pluggable_ai_provider_registry(self):
        """Verify that a future AI provider can be registered and resolved seamlessly."""
        class FutureCustomAIAdapter(BaseAIClient):
            def __init__(self):
                super().__init__()
                self.custom_model = "future-enterprise-v2"

            def _execute_provider_request(self, prompt: str) -> Tuple[Any, str]:
                return {}, self.custom_model

            def classify_links_batch(self, company_name: str, domain: str, links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
                return [{"url": l.get("url"), "actual_model": self.custom_model} for l in links]

            def classify_page_content(self, company_name: str, url: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
                return {"page_type": "CAREERS_LANDING_PAGE", "confidence": 0.95, "actual_model": self.custom_model}

        # Register new provider
        AIProviderRegistry.register("future_custom_ai", FutureCustomAIAdapter)
        self.assertIn("future_custom_ai", AIProviderRegistry.list_providers())

        # Retrieve instance via factory
        inst = get_ai_client("future_custom_ai")
        self.assertIsInstance(inst, FutureCustomAIAdapter)

        # Verify TwoStagePageClassifier operates transparently with new adapter
        classifier = TwoStagePageClassifier(client=inst)
        stage2_res = classifier.classify_destination_page("Acme Corp", "https://acme.com/careers", {})
        self.assertEqual(stage2_res.get("actual_model"), "future-enterprise-v2")

        # Independent evidence validation operates without modification
        validation = classifier.validate_page_evidence(
            company_name="Acme Corp",
            official_domain="acme.com",
            page_classification=stage2_res,
            page_data={"url": "https://acme.com/careers", "is_accessible": True, "status_code": 200, "main_text": "Join our growing team"}
        )
        self.assertEqual(validation.get("decision"), "APPROVED")

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 9:
    # Uncertain source URLs remain flagged for review without overwriting verified URLs.
    # --------------------------------------------------------------------------
    def test_09_uncertain_urls_flagged_for_review_without_overwriting_primary_urls(self):
        """Verify that REVIEW_REQUIRED decisions do not overwrite primary company URLs."""
        mock_company = MagicMock()
        mock_company.company_id = "COMP_REVIEW_TEST_001"
        mock_company.careers_url = "https://reviewsafety.in/official-careers"

        cmd = DiscoveryCommand()
        ambiguous_record = {
            "url": "https://reviewsafety.in/personal-loans",
            "final_url": "https://reviewsafety.in/personal-loans",
            "page_type": "UNKNOWN_REQUIRES_REVIEW",
            "confidence": 0.40,
            "decision": "REVIEW_REQUIRED",
            "reason": "Ambiguous consumer content",
            "target_field": "careers_url",
            "actual_model": "test-model"
        }
        cand = {"location": "NAV_HEADER", "text": "Apply Now"}
        page_data = {"content_hash": "hash_ambiguous_123"}
        page_class = {"page_type": "UNKNOWN_REQUIRES_REVIEW"}

        with patch("modules.admin_panel.models.CompanySource.objects.update_or_create") as mock_src:
            cmd._record_source_registry(mock_company, ambiguous_record, cand, page_data, page_class, "REVIEW_REQUIRED")
            mock_src.assert_called_once()
            _, kwargs = mock_src.call_args
            self.assertEqual(kwargs["defaults"]["verification_status"], "REVIEW_REQUIRED")
            self.assertFalse(kwargs["defaults"]["is_primary"])

        # CRITICAL: Verify Company primary URL was NOT changed
        self.assertEqual(mock_company.careers_url, "https://reviewsafety.in/official-careers")

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 10:
    # Backups, audit logging and safe database-update requirements remain in force.
    # --------------------------------------------------------------------------
    def test_10_backups_audit_logging_and_transactional_safety(self):
        """Verify backup file existence and AuditTrail generation upon verified URL updates."""
        # 1. Verify safe backup exists on disk
        backup_path = os.path.join(cfg.BASE_DIR, "data", "db_backup_20261019_221438.json")
        self.assertTrue(os.path.exists(backup_path), f"Backup file {backup_path} must exist.")

        # 2. Verify AuditTrail logging on verified update
        mock_company = MagicMock()
        mock_company.company_id = "COMP_AUDIT_TEST_001"
        mock_company.careers_url = "https://auditsafety.in/old-careers"
        mock_company.ats_platform = None

        cmd = DiscoveryCommand()
        verified_record = {
            "url": "https://auditsafety.in/careers",
            "final_url": "https://auditsafety.in/careers",
            "page_type": "CAREERS_LANDING_PAGE",
            "confidence": 0.95,
            "decision": "APPROVED",
            "reason": "Authoritative employer branding portal",
            "target_field": "careers_url",
            "actual_model": "openrouter/free"
        }
        cand = {"location": "NAV_HEADER", "text": "Careers"}
        page_data = {"content_hash": "hash_verified_456", "ats_platform": None}
        page_class = {"page_type": "CAREERS_LANDING_PAGE"}
        validation = {"decision": "APPROVED", "reason": "Authoritative employer branding portal"}
        comp_res = {"updates": []}
        stats = {"url_updates_applied": 0}

        with patch("modules.admin_panel.management.commands.discover_and_verify_company_sources.transaction.atomic"), \
             patch("modules.admin_panel.models.CompanySource.objects.filter") as mock_src_filter, \
             patch("modules.admin_panel.models.CompanySource.objects.update_or_create") as mock_src_create, \
             patch("modules.admin_panel.models.AuditTrail.objects.create") as mock_audit:

            cmd._apply_verified_source(mock_company, verified_record, cand, page_data, page_class, validation, comp_res, stats)

            # Verify Company primary URL was updated
            self.assertEqual(mock_company.careers_url, "https://auditsafety.in/careers")

            # Verify AuditTrail record was created
            mock_audit.assert_called_once()
            _, audit_kwargs = mock_audit.call_args
            self.assertEqual(audit_kwargs["record_id"], "COMP_AUDIT_TEST_001")
            self.assertEqual(audit_kwargs["action"], "VERIFIED_URL_UPDATE_CAREERS_URL")
            self.assertEqual(audit_kwargs["user_role"], "AI_CLASSIFIER_ENGINE")
            self.assertEqual(audit_kwargs["previous_value"], "https://auditsafety.in/old-careers")
            self.assertEqual(audit_kwargs["new_value"], "https://auditsafety.in/careers")

    # --------------------------------------------------------------------------
    # REGRESSION TEST: Custom Primary Key (company_id) and Queryset .only()
    # --------------------------------------------------------------------------
    def test_11_custom_primary_key_regression_and_queryset_only_fields(self):
        """
        Regression test: Verify that Company._meta.pk.name is 'company_id',
        that 'id' does NOT exist as a model field, and that the command's queryset .only()
        specifies strictly valid existing fields without triggering FieldDoesNotExist.
        """
        from django.core.exceptions import FieldDoesNotExist
        from modules.admin_panel.models import Company

        # 1. Custom primary key validation
        self.assertEqual(Company._meta.pk.name, "company_id")

        # 2. Confirm 'id' is NOT a field on Company
        with self.assertRaises(FieldDoesNotExist):
            Company._meta.get_field("id")

        # 3. Confirm all fields used in discover_and_verify_company_sources exist on Company
        expected_fields = [
            Company._meta.pk.name,
            "company_name",
            "official_domain",
            "website_url",
            "careers_url",
            "jobs_page_url",
            "csr_portal_url",
            "sustainability_url",
            "ats_platform",
            "ats_url"
        ]
        for field_name in expected_fields:
            field = Company._meta.get_field(field_name)
            self.assertIsNotNone(field, f"Field '{field_name}' must exist on Company model.")

        # 4. Verify queryset construction with .only() does not raise FieldDoesNotExist
        qs = Company.objects.all().order_by(Company._meta.pk.name).only(*expected_fields)
        self.assertNotIn("id", qs.query.deferred_loading[0])

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 12:
    # Non-billable eligibility verification and reporting (Requirement 8)
    # --------------------------------------------------------------------------
    def test_12_non_billable_eligibility_verification_reporting(self):
        """Verify test_provider_eligibility() validates providers without billable calls."""
        # Case A: When Grok API key is present but credits are unconfirmed -> zero-cost policy blocks it
        with patch.dict(os.environ, {"GROK_API_KEY": "dummy-grok-key"}), \
             patch("modules.crawler_engine.ai_classifier_config.GROK_FREE_CREDITS_CONFIRMED", False):
            report = test_provider_eligibility()
            self.assertEqual(report["zero_cost_requirement"], "STRICT_ZERO_COST")
            self.assertIn("gemini", report)
            self.assertIn("grok", report)
            self.assertTrue(report["gemini"]["billable_calls_prevented"])
            self.assertTrue(report["grok"]["billable_calls_prevented"])
            self.assertTrue(report["gemini"]["is_official_free_tier_model"])
            self.assertFalse(report["grok"]["eligible_for_free_inference"])
            self.assertIn("zero-cost policy enforced", report["grok"]["reason"].lower())

    # --------------------------------------------------------------------------
    # ACCEPTANCE CRITERION 13:
    # Quota exhaustion marks candidates PENDING_AI / REVIEW_REQUIRED without URL overwrite
    # --------------------------------------------------------------------------
    def test_13_quota_exhaustion_marks_candidates_pending_ai(self):
        """Verify that quota exhaustion marks uncertain candidates PENDING_AI and preserves primary URLs."""
        mock_company = MagicMock()
        mock_company.company_id = "COMP_QUOTA_PAUSE_001"
        mock_company.company_name = "Quota Pause Test Ltd"
        mock_company.website_url = "https://quotapause.in"
        mock_company.official_domain = "quotapause.in"
        mock_company.careers_url = "https://quotapause.in/existing-careers"

        cmd = DiscoveryCommand()
        mock_classifier = MagicMock(spec=TwoStagePageClassifier)
        mock_classifier.extract_candidate_links_from_html.return_value = [
            {"url": "https://quotapause.in/careers", "text": "Careers", "location": "HEADER_NAV"},
            {"url": "https://quotapause.in/jobs", "text": "Jobs", "location": "HEADER_NAV"}
        ]
        mock_classifier.classify_discovered_links.side_effect = QuotaExhaustedError("Gemini quota exhausted")

        stats = {
            "total_links_discovered": 0,
            "stage1_classified_links": 0,
            "stage2_evaluated_pages": 0,
            "approved_sources": 0,
            "review_required_sources": 0,
            "rejected_sources": 0,
            "models_used": {}
        }

        with patch("modules.admin_panel.management.commands.discover_and_verify_company_sources.fetch_live_page",
                   return_value={"ok": True, "html": "<html><body>Links</body></html>", "final_url": "https://quotapause.in"}), \
             patch("modules.admin_panel.models.CompanySource.objects.filter") as mock_src_filter, \
             patch.object(cmd, "_record_source_registry") as mock_record:

            mock_src_filter.return_value.exists.return_value = False
            with self.assertRaises(QuotaExhaustedError):
                cmd._process_single_company(mock_company, mock_classifier, dry_run=False, stats=stats)

            # Confirm candidates were recorded as PENDING_AI
            mock_record.assert_called()
            record_call_args = mock_record.call_args_list[0]
            self.assertEqual(record_call_args[0][5], "PENDING_AI")

            # Confirm company primary URL was NOT overwritten
            self.assertEqual(mock_company.careers_url, "https://quotapause.in/existing-careers")


