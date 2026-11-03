"""
modules/crawler_engine/hybrid_ai_service.py
===========================================
Central Hybrid AI Classification and Extraction Service.
Connects the operational crawler to configured AI clients (Gemini, OpenRouter, etc.)
strictly for ambiguous cases with schema validation, independent evidence verification,
and persistent token telemetry tracking.
"""
import os
import re
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple, List
from modules.admin_panel.services.ai_config_service import get_active_ai_config
from modules.admin_panel.services.ai_telemetry_service import telemetry_store
from modules.crawler_engine.ai_api_client import get_ai_client, AIClientError

logger = logging.getLogger(__name__)

GENERIC_NAV_WORDS = {
    'careers', 'home', 'about us', 'contact us', 'privacy policy',
    'terms of use', 'job search', 'search jobs', 'current openings',
    'all jobs', 'apply now', 'view jobs', 'join our team', 'work with us',
    'life at', 'overview', 'corporate overview', 'read more', 'click here'
}


class HybridAIExtractionService:
    """
    Manages semantic interpretation and extraction requests for difficult,
    unstructured career pages and long narrative Section 135 CSR reports.
    """

    @classmethod
    def disambiguate_csr_narrative(
        cls,
        company_id: str,
        company_name: str,
        snippet: str,
        source_url: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 15
    ) -> Optional[Dict[str, Any]]:
        """
        Invokes configured LLM to discern whether an unstructured narrative snippet
        describes a genuine, specific Section 135 CSR project or generic marketing/policy copy.
        Returns parsed structured dictionary with verbatim quotation and statutory category.
        """
        active_config = get_active_ai_config()
        selected_provider = (provider or active_config.get("primary_provider") or "gemini").lower().strip()
        selected_model = model or active_config.get("primary_model") or "gemini-3.1-flash-lite"

        prompt = f"""You are a strict data auditor evaluating Indian Corporate Social Responsibility (CSR) compliance under Section 135 and Schedule VII of the Companies Act 2013.

Company: {company_name}
Source URL: {source_url}
Text Snippet:
\"\"\"
{snippet[:2500]}
\"\"\"

Task: Determine if this text describes a SPECIFIC, ACTUAL grassroots CSR project or social initiative (with tangible actions, beneficiaries, or locations), OR if it is merely general corporate sustainability policy, marketing copy, or committee composition.

Respond ONLY with valid JSON in this schema:
{{
  "is_actual_project": true,
  "project_title": "Clean concise project title, or null if false",
  "category": "Education & Skill Development | Healthcare & Nutrition | Environment & Sustainability | Rural Development | Women Empowerment | Disaster Relief | Other",
  "schedule_vii_item": "Item (i) to (xii) statutory designation, or null",
  "description": "2-3 sentence factual summary of the specific project",
  "verbatim_quotation": "Exact 1-2 sentence verbatim quotation from the snippet proving the initiative exists",
  "geographic_location": "District/State or null",
  "location_state": "Indian state or null",
  "location_district": "District or null",
  "budget": "Disclosed budget figure or null",
  "confidence": 0.85,
  "rejection_reason": "POLICY_STATEMENT | MARKETING_ONLY | COMMITTEE_INFO | COMMERCIAL_PRODUCT | null"
}}"""

        start_t = time.time()
        in_tokens = max(1, len(prompt) // 4)
        out_tokens = 0
        actual_model = selected_model

        try:
            client = get_ai_client(selected_provider if selected_provider != "default" else None)
            
            # Execute structured JSON prompt
            if hasattr(client, "execute_structured_prompt"):
                parsed, actual_model = client.execute_structured_prompt(prompt)
            elif hasattr(client, "_execute_provider_request"):
                parsed, actual_model = client._execute_provider_request(prompt)
            else:
                logger.warning(f"AI Client for {selected_provider} does not support prompt execution.")
                return None

            latency_ms = int((time.time() - start_t) * 1000)
            out_tokens = max(1, len(json.dumps(parsed)) // 4) if parsed else 0

            # Record telemetry in SQLite store
            telemetry_store.record_event(
                provider=selected_provider,
                model=actual_model or selected_model,
                task="csr_disambiguation",
                status="SUCCESS",
                company_id=company_id,
                company_name=company_name,
                latency_ms=latency_ms,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                evidence_excerpt=snippet[:120],
                validation_result="PARSED_OK" if isinstance(parsed, dict) else "PARSE_FAILED"
            )

            if isinstance(parsed, dict) and parsed.get("is_actual_project"):
                return parsed
            return None

        except Exception as e:
            latency_ms = int((time.time() - start_t) * 1000)
            logger.warning(f"AI CSR Disambiguation error for {company_name} ({selected_provider}): {str(e)}")
            try:
                telemetry_store.record_event(
                    provider=selected_provider,
                    model=actual_model or selected_model,
                    task="csr_disambiguation",
                    status="FAILED",
                    company_id=company_id,
                    company_name=company_name,
                    latency_ms=latency_ms,
                    input_tokens=in_tokens,
                    output_tokens=0,
                    error_category=type(e).__name__,
                    evidence_excerpt=snippet[:120],
                    validation_result=f"ERROR: {str(e)[:100]}"
                )
            except Exception:
                pass
            return None

    @classmethod
    def extract_unstructured_jobs(
        cls,
        company_id: str,
        company_name: str,
        raw_content: str,
        careers_url: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Invokes configured LLM to extract active job openings from unstructured careers portal content.
        Enforces strict JSON schema, verbatim source quotation, and token telemetry recording.
        """
        active_config = get_active_ai_config()
        selected_provider = (provider or active_config.get("primary_provider") or "gemini").lower().strip()
        selected_model = model or active_config.get("primary_model") or "gemini-3.1-flash-lite"

        prompt = f"""You are a strict data auditor evaluating Indian corporate careers portals and job vacancy postings.
Company: {company_name}
Source URL: {careers_url}

Content Excerpt:
\"\"\"
{raw_content[:3500]}
\"\"\"

Task: Extract all genuine, open, specific job vacancies explicitly mentioned in this content. Do not hallucinate or invent roles that are not present. Missing details must be null or empty string.

Respond ONLY with valid JSON array conforming to this schema:
[
  {{
    "job_title": "Precise job title (e.g. Senior Software Engineer, Area Sales Manager)",
    "location": "Job location or city/state (e.g. Bengaluru, Mumbai, Remote, India) or null",
    "department": "Department or function (e.g. Engineering, Sales, Human Resources) or null",
    "employment_type": "Full-time | Part-time | Contract | Internship | null",
    "work_mode": "On-site | Hybrid | Remote | null",
    "job_description": "Concise summary of key duties or qualifications",
    "verbatim_quote": "Exact 1-2 sentence verbatim phrase from the content mentioning this role",
    "application_url": "Direct apply URL if present, or null",
    "confidence": 0.85
  }}
]"""

        start_t = time.time()
        in_tokens = max(1, len(prompt) // 4)
        out_tokens = 0
        actual_model = selected_model

        try:
            client = get_ai_client(selected_provider if selected_provider != "default" else None)

            if hasattr(client, "execute_structured_prompt"):
                parsed, actual_model = client.execute_structured_prompt(prompt)
            elif hasattr(client, "_execute_provider_request"):
                parsed, actual_model = client._execute_provider_request(prompt)
            else:
                logger.warning(f"AI Client for {selected_provider} does not support prompt execution.")
                return []

            latency_ms = int((time.time() - start_t) * 1000)
            
            # Normalize list output
            results = []
            if isinstance(parsed, list):
                results = parsed
            elif isinstance(parsed, dict) and "jobs" in parsed and isinstance(parsed["jobs"], list):
                results = parsed["jobs"]
            elif isinstance(parsed, dict) and "results" in parsed and isinstance(parsed["results"], list):
                results = parsed["results"]
            elif isinstance(parsed, dict) and "job_title" in parsed:
                results = [parsed]

            out_tokens = max(1, len(json.dumps(results)) // 4) if results else 0

            # Record telemetry in SQLite store
            telemetry_store.record_event(
                provider=selected_provider,
                model=actual_model or selected_model,
                task="job_extraction",
                status="SUCCESS",
                company_id=company_id,
                company_name=company_name,
                latency_ms=latency_ms,
                input_tokens=in_tokens,
                output_tokens=out_tokens,
                evidence_excerpt=raw_content[:120],
                validation_result=f"EXTRACTED_{len(results)}_JOBS"
            )

            return results

        except Exception as e:
            latency_ms = int((time.time() - start_t) * 1000)
            logger.warning(f"AI Job Extraction error for {company_name} ({selected_provider}): {str(e)}")
            try:
                telemetry_store.record_event(
                    provider=selected_provider,
                    model=actual_model or selected_model,
                    task="job_extraction",
                    status="FAILED",
                    company_id=company_id,
                    company_name=company_name,
                    latency_ms=latency_ms,
                    input_tokens=in_tokens,
                    output_tokens=0,
                    error_category=type(e).__name__,
                    evidence_excerpt=raw_content[:120],
                    validation_result=f"ERROR: {str(e)[:100]}"
                )
            except Exception:
                pass
            return []

    @classmethod
    def verify_job_evidence(cls, candidate: Dict[str, Any], raw_source: str) -> Tuple[bool, str]:
        """
        Independent verification engine: checks that candidate vacancy possesses valid title,
        non-navigational identity, and authentic verbatim evidence in the original source content.
        Rejects hallucinations and generic menu items.
        """
        if not candidate or not isinstance(candidate, dict):
            return False, "Candidate payload is empty or invalid"

        title = (candidate.get("job_title") or "").strip()
        if len(title) < 3:
            return False, "Job title is too short or missing"

        # Check against generic navigational items
        title_norm = re.sub(r'\s+', ' ', re.sub(r'[^a-z0-9 ]', ' ', title.lower())).strip()
        if (
            title_norm in GENERIC_NAV_WORDS
            or any(g in title_norm for g in ["search jobs", "current openings", "apply now", "view jobs", "work with us", "join us", "all jobs", "privacy policy"])
            or all(w in GENERIC_NAV_WORDS or w in {"and", "or", "in", "the", "for", "at", "&"} for w in title_norm.split())
        ):
            return False, f"Title '{title}' resembles navigational menu text, not a vacancy"

        # Evidence verification: check that verbatim quote or key title words appear in raw_source
        source_lower = (raw_source or "").lower()
        quote = (candidate.get("verbatim_quote") or "").strip().lower()

        # If a quote is provided and has substance (> 15 chars), check for it
        if len(quote) >= 15:
            # Check exact or fuzzy sub-phrase
            clean_quote = re.sub(r'\s+', ' ', quote)
            clean_src = re.sub(r'\s+', ' ', source_lower)
            if clean_quote in clean_src:
                return True, "Verbatim quotation verified in source content"

            # Check 8-word window
            words = clean_quote.split()
            if len(words) >= 4:
                sub_phrase = " ".join(words[:5])
                if sub_phrase in clean_src:
                    return True, "Sub-phrase quotation verified in source content"

        # Check if job title keywords appear in source
        title_words = [w for w in title.lower().split() if len(w) > 3 and w not in GENERIC_NAV_WORDS]
        if title_words and all(w in source_lower for w in title_words[:2]):
            return True, "Job title verified in source content"

        return False, "Failed independent evidence verification: no verbatim citation in source text"

    @classmethod
    def verify_csr_evidence(cls, candidate: Dict[str, Any], raw_source: str) -> Tuple[bool, str]:
        """
        Independent verification engine: checks that statutory Section 135 CSR candidate
        describes an authentic initiative with verbatim citations in the fetched corporate source.
        Rejects policy statements, marketing copy, and ungrounded claims.
        """
        if not candidate or not isinstance(candidate, dict):
            return False, "Candidate payload is empty or invalid"

        if not candidate.get("is_actual_project"):
            reason = candidate.get("rejection_reason") or "Not an actual CSR project"
            return False, f"Rejected: {reason}"

        title = (candidate.get("project_title") or "").strip()
        if len(title) < 4:
            return False, "Project title is missing or insufficient"

        source_lower = (raw_source or "").lower()
        quote = (candidate.get("verbatim_quotation") or "").strip().lower()

        if len(quote) >= 15:
            clean_quote = re.sub(r'\s+', ' ', quote)
            clean_src = re.sub(r'\s+', ' ', source_lower)
            if clean_quote in clean_src:
                return True, "Statutory quotation verified in source content"

            words = clean_quote.split()
            if len(words) >= 4:
                sub_phrase = " ".join(words[:5])
                if sub_phrase in clean_src:
                    return True, "Sub-phrase quotation verified in source content"

        title_words = [w for w in title.lower().split() if len(w) > 3]
        if title_words and any(w in source_lower for w in title_words):
            return True, "Project title verified in source content"

        return False, "Failed independent verification: statutory evidence not confirmed in source"
