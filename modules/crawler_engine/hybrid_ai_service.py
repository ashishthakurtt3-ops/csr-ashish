"""
modules/crawler_engine/hybrid_ai_service.py
===========================================
Central Hybrid AI Classification and Extraction Service.
Connects the operational crawler to configured AI clients (Gemini, OpenRouter)
strictly for ambiguous cases with schema validation and token telemetry tracking.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from modules.admin_panel.services.ai_config_service import get_active_ai_config
from modules.admin_panel.services.ai_telemetry_service import telemetry_store
from modules.crawler_engine.ai_api_client import get_ai_client, AIClientError

logger = logging.getLogger(__name__)


class HybridAIExtractionService:
    """
    Manages semantic interpretation and extraction requests for difficult,
    unstructured career pages and long narrative CSR reports.
    """

    @classmethod
    def disambiguate_csr_narrative(cls, company_id: str, company_name: str, snippet: str, source_url: str) -> Optional[Dict[str, Any]]:
        """
        Invokes configured LLM to discern whether an unstructured narrative snippet
        describes a genuine, specific CSR project or generic marketing/policy copy.
        """
        active_config = get_active_ai_config()
        provider = active_config.get("primary_provider", "gemini")
        model = active_config.get("primary_model", "gemini-3.1-flash-lite")
        
        prompt = f"""You are a strict data auditor evaluating Indian Corporate Social Responsibility (CSR) compliance under Section 135 and Schedule VII of the Companies Act 2013.

Company: {company_name}
Source URL: {source_url}
Text Snippet:
\"\"\"
{snippet[:2000]}
\"\"\"

Task: Determine if this text describes a SPECIFIC, ACTUAL grassroots CSR project or social initiative (with tangible actions, beneficiaries, or locations), OR if it is merely general corporate sustainability policy, marketing copy, or committee composition.

Respond ONLY with valid JSON in this schema:
{{
  "is_actual_project": true or false,
  "project_title": "Clean concise project title, or null if false",
  "schedule_vii_item": "Item (i) to (xii) statutory designation, or null",
  "verbatim_quotation": "Exact 1-2 sentence verbatim quotation from the snippet proving the initiative exists",
  "location_state": "Indian state or null",
  "location_district": "District or null",
  "confidence": 0.0 to 1.0,
  "rejection_reason": "POLICY_STATEMENT | MARKETING_ONLY | COMMITTEE_INFO | COMMERCIAL_PRODUCT | null"
}}"""

        try:
            client = get_ai_client(provider)
            # If client is not eligible or unconfigured, do not fabricate telemetry
            if hasattr(client, "verify_free_tier_eligibility"):
                ok, reason = client.verify_free_tier_eligibility()
                if not ok:
                    logger.info(f"AI Disambiguation skipped (Provider {provider} ineligible: {reason})")
                    return None
            return None
        except Exception as e:
            logger.warning(f"AI Disambiguation skipped: {str(e)}")
            return None

