"""
modules/admin_panel/management/commands/test_ai_providers.py
============================================================
Management command to test Gemini and Grok AI provider configurations
WITHOUT making any billable API calls.

Validates official API free-tier accessibility for Gemini and enforces the strict
zero-cost policy for Grok fallback, reporting which providers are actually eligible
for free inference.
"""

import sys
from django.core.management.base import BaseCommand
from modules.crawler_engine import ai_classifier_config as cfg
from modules.crawler_engine.ai_api_client import test_provider_eligibility


class Command(BaseCommand):
    help = "Test Gemini and Grok provider configurations without making any billable API calls."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("  ZERO-COST AI CLASSIFIER CONFIGURATION & ELIGIBILITY AUDIT"))
        self.stdout.write(self.style.SUCCESS("=" * 70))

        report = test_provider_eligibility()

        # 1. Primary: Gemini
        gemini = report["gemini"]
        self.stdout.write(self.style.MIGRATE_HEADING("\n[1] PRIMARY PROVIDER: Google Gemini"))
        self.stdout.write(f"  - Provider Role          : {gemini['role']}")
        self.stdout.write(f"  - Configured Model       : {gemini['model']}")
        self.stdout.write(f"  - Official Free Tier     : {'YES' if gemini['is_official_free_tier_model'] else 'NO (VIOLATION)'}")
        self.stdout.write(f"  - Free-Tier Models List  : {', '.join(cfg.GEMINI_FREE_TIER_MODELS)}")
        self.stdout.write(f"  - API Key Env Variable   : {cfg.GEMINI_API_KEY_ENV}")
        self.stdout.write(f"  - Billable Calls Blocked : {gemini['billable_calls_prevented']}")

        if gemini["eligible_for_free_inference"]:
            self.stdout.write(self.style.SUCCESS(f"  - Free Inference Status  : [ELIGIBLE] {gemini['reason']}"))
        else:
            self.stdout.write(self.style.WARNING(f"  - Free Inference Status  : [INELIGIBLE] {gemini['reason']}"))

        # 2. Fallback: Grok
        grok = report["grok"]
        self.stdout.write(self.style.MIGRATE_HEADING("\n[2] FALLBACK PROVIDER: xAI Grok"))
        self.stdout.write(f"  - Provider Role          : {grok['role']}")
        self.stdout.write(f"  - Configured Model       : {grok['model']}")
        self.stdout.write(f"  - Zero-Cost Only Policy  : {'ENFORCED (Strict Zero Cost)' if grok['zero_cost_only_enforced'] else 'OFF'}")
        self.stdout.write(f"  - Web Account Disclaimer : {grok['web_account_disclaimer']}")
        self.stdout.write(f"  - Free Credits Confirmed : {grok['free_credits_confirmed']} (GROK_FREE_CREDITS_CONFIRMED)")
        self.stdout.write(f"  - API Key Env Variable   : {cfg.GROK_API_KEY_ENV} (or XAI_API_KEY)")
        self.stdout.write(f"  - Billable Calls Blocked : {grok['billable_calls_prevented']}")

        if grok["eligible_for_free_inference"]:
            self.stdout.write(self.style.SUCCESS(f"  - Free Inference Status  : [ELIGIBLE] {grok['reason']}"))
        else:
            self.stdout.write(self.style.WARNING(f"  - Free Inference Status  : [INELIGIBLE] {grok['reason']}"))

        # 3. Overall Zero-Cost Policy Summary
        self.stdout.write(self.style.SUCCESS("\n" + "-" * 70))
        self.stdout.write(self.style.SUCCESS("                   OPERATIONAL VERDICT                   "))
        self.stdout.write(self.style.SUCCESS("-" * 70))
        self.stdout.write(f"* Policy Mode: {report['zero_cost_requirement']}")

        if gemini["eligible_for_free_inference"] and grok["eligible_for_free_inference"]:
            self.stdout.write(self.style.SUCCESS(
                "* BOTH Gemini (primary) and Grok (fallback) are verified and eligible for zero-cost operation."
            ))
        elif gemini["eligible_for_free_inference"] and not grok["eligible_for_free_inference"]:
            self.stdout.write(self.style.SUCCESS(
                "* Gemini (primary) is ELIGIBLE for free-tier operation.\n"
                "* Grok (fallback) is INELIGIBLE/DISABLED to protect zero-cost requirement (no billable calls will be sent).\n"
                "* System will pause safely and checkpoint if Gemini reaches quota."
            ))
        elif not gemini["eligible_for_free_inference"] and grok["eligible_for_free_inference"]:
            self.stdout.write(self.style.WARNING(
                "* Gemini (primary) is not currently eligible.\n"
                "* Grok has confirmed free credits."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                "* Neither provider has an active, verified zero-cost API key configured.\n"
                "* Deterministic rule-based fallback will operate safely offline at 100% zero cost."
            ))

        self.stdout.write(self.style.SUCCESS("=" * 70 + "\n"))
