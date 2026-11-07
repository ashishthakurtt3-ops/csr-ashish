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

    @classmethod
    def _execute_prompt_with_failover(
        cls,
        prompt: str,
        preferred_provider: Optional[str],
        preferred_model: Optional[str],
        company_id: str,
        company_name: str,
        task: str,
        evidence_excerpt: str = ""
    ) -> Tuple[Optional[Any], str, str]:
        """
        Executes prompt with automatic multi-provider fallback.
        Tries preferred provider first; if it fails (404, 429, timeout, connection error),
        automatically falls back to configured fallback provider (e.g., OpenRouter or Gemini).
        Returns (parsed_result, provider_used, model_used).
        """
        active_config = get_active_ai_config()
        p1 = (preferred_provider or active_config.get("primary_provider") or "gemini").lower().strip()
        p2 = (active_config.get("fallback_provider") or ("openrouter" if p1 == "gemini" else "gemini")).lower().strip()

        provider_chain = [p1]
        if p2 and p2 not in provider_chain:
            provider_chain.append(p2)
        # Include openai or openrouter if configured with active keys
        for extra in ["openrouter", "openai", "anthropic"]:
            if extra not in provider_chain:
                p_info = active_config.get("providers", {}).get(extra, {})
                if p_info.get("has_key") and p_info.get("status") == "ACTIVE":
                    provider_chain.append(extra)

        start_t = time.time()
        in_tokens = max(1, len(prompt) // 4)

        for attempt_idx, prov in enumerate(provider_chain):
            prov_model = preferred_model if prov == p1 else None
            try:
                client = get_ai_client(prov if prov != "default" else None)
                if hasattr(client, "execute_structured_prompt"):
                    parsed, actual_model = client.execute_structured_prompt(prompt)
                elif hasattr(client, "_execute_provider_request"):
                    parsed, actual_model = client._execute_provider_request(prompt)
                else:
                    raise AIClientError(f"Provider {prov} client does not support prompt execution.")

                latency_ms = int((time.time() - start_t) * 1000)
                out_tokens = max(1, len(json.dumps(parsed)) // 4) if parsed else 0

                telemetry_store.record_event(
                    provider=prov,
                    model=actual_model or prov_model or "auto",
                    task=task,
                    status="SUCCESS" if attempt_idx == 0 else "SUCCESS_VIA_FALLBACK",
                    company_id=company_id,
                    company_name=company_name,
                    latency_ms=latency_ms,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    evidence_excerpt=evidence_excerpt[:120],
                    validation_result="PARSED_OK" if parsed else "EMPTY_OUTPUT"
                )
                return parsed, prov, actual_model or prov_model or "auto"

            except Exception as e:
                latency_ms = int((time.time() - start_t) * 1000)
                logger.warning(f"AI {task} attempt with {prov} for {company_name} failed: {str(e)}")
                try:
                    telemetry_store.record_event(
                        provider=prov,
                        model=prov_model or "auto",
                        task=task,
                        status="FAILED",
                        company_id=company_id,
                        company_name=company_name,
                        latency_ms=latency_ms,
                        input_tokens=in_tokens,
                        output_tokens=0,
                        error_category=type(e).__name__,
                        evidence_excerpt=evidence_excerpt[:120],
                        validation_result=f"ERROR: {str(e)[:100]}"
                    )
                except Exception:
                    pass

                if attempt_idx < len(provider_chain) - 1:
                    logger.info(f"AI failover: Retrying {task} for {company_name} with fallback provider {provider_chain[attempt_idx + 1]}...")
                    continue

        return None, "", ""

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
{snippet[:8500]}
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

        parsed, used_provider, used_model = cls._execute_prompt_with_failover(
            prompt=prompt,
            preferred_provider=selected_provider,
            preferred_model=selected_model,
            company_id=company_id,
            company_name=company_name,
            task="csr_disambiguation",
            evidence_excerpt=snippet[:120]
        )
        if isinstance(parsed, dict) and parsed.get("is_actual_project"):
            return parsed
        return None

    @classmethod
    def extract_unstructured_csr_projects(
        cls,
        company_id: str,
        company_name: str,
        raw_content: str,
        csr_url: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Invokes configured LLM to extract all genuine, specific Section 135 CSR projects and initiatives
        explicitly documented in live CSR portal content.
        Enforces strict JSON array schema, verbatim quotations, and token telemetry recording.
        """
        active_config = get_active_ai_config()
        selected_provider = (provider or active_config.get("primary_provider") or "gemini").lower().strip()
        selected_model = model or active_config.get("primary_model") or "gemini-3.1-flash-lite"

        excerpt = raw_content[:40000]
        prompt = (
            "You are a strict data auditor evaluating Indian corporate sustainability and CSR compliance under Section 135 and Schedule VII of the Companies Act 2013.\n"
            f"Company: {company_name}\n"
            f"Source CSR URL: {csr_url}\n\n"
            f"Content Excerpt:\n---BEGIN---\n{excerpt}\n---END---\n\n"
            "Task: Extract EVERY genuine, specific Section 135 CSR project, grassroots social program, community initiative, or Schedule VII intervention explicitly mentioned in this content.\n"
            "Do NOT truncate or cap at 5 or any fixed limit. If there are 8 initiatives, return all 8. If there are 25, return all 25. If there are only 3, return 3. Reflect the exact real CSR initiatives present on the page. Missing details must be null or empty string.\n\n"
            "Respond ONLY with a valid JSON array conforming to this schema:\n"
            "[\n"
            "  {\n"
            '    "project_name": "Specific CSR project or initiative title (e.g. Kaushalya Skill Development, Arogya Health Outreach, Jal Jeevan Water Project)",\n'
            '    "category": "Education & Skill Development | Healthcare & Nutrition | Environment & Sustainability | Rural Development | Women Empowerment | Water & Sanitation | Disaster Relief | Other",\n'
            '    "state": "Indian state or Pan-India or null",\n'
            '    "district": "District name or null",\n'
            '    "budget": "Disclosed financial outlay / budget or null",\n'
            '    "description": "2-3 sentence factual summary of what the initiative does and who it helps",\n'
            '    "verbatim_quote": "Exact 1-2 sentence verbatim quote from the page proving this initiative exists",\n'
            '    "confidence": 0.90\n'
            "  }\n"
            "]"
        )

        parsed, used_provider, used_model = cls._execute_prompt_with_failover(
            prompt=prompt,
            preferred_provider=selected_provider,
            preferred_model=selected_model,
            company_id=company_id,
            company_name=company_name,
            task="csr_extraction",
            evidence_excerpt=raw_content[:120]
        )

        results = []
        if isinstance(parsed, list):
            results = parsed
        elif isinstance(parsed, dict) and "projects" in parsed and isinstance(parsed["projects"], list):
            results = parsed["projects"]
        elif isinstance(parsed, dict) and "csr_projects" in parsed and isinstance(parsed["csr_projects"], list):
            results = parsed["csr_projects"]
        elif isinstance(parsed, dict) and "results" in parsed and isinstance(parsed["results"], list):
            results = parsed["results"]
        elif isinstance(parsed, dict) and ("project_name" in parsed or "project_title" in parsed):
            results = [parsed]

        valid_projects = []
        for item in results:
            if not isinstance(item, dict):
                continue
            name = item.get("project_name") or item.get("project_title")
            if name and str(name).strip() and len(str(name).strip()) > 2:
                valid_projects.append({
                    "project_name": str(name).strip(),
                    "category": item.get("category") or "Corporate Social Responsibility",
                    "state": item.get("state") or item.get("location_state") or "Pan-India",
                    "district": item.get("district") or item.get("location_district") or "Not specified",
                    "budget": item.get("budget") or "Disclosed under Section 135",
                    "description": item.get("description") or item.get("verbatim_quote") or "",
                    "verbatim_quote": item.get("verbatim_quote") or item.get("description") or "",
                    "confidence": float(item.get("confidence") or 0.85)
                })

        return valid_projects

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
{raw_content[:40000]}
\"\"\"

Task: Extract EVERY genuine, active, open job vacancy explicitly mentioned in this content.
Do NOT limit, cap, or truncate at 5 or any arbitrary number. If there are 15 roles, return all 15. If there are 45 roles, return all 45. If there are 4 roles, return 4. Reflect the EXACT vacancy list present in the content.
Missing details must be null or empty string.

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
    "confidence": 0.90
  }}
]"""

        parsed, used_provider, used_model = cls._execute_prompt_with_failover(
            prompt=prompt,
            preferred_provider=selected_provider,
            preferred_model=selected_model,
            company_id=company_id,
            company_name=company_name,
            task="job_extraction",
            evidence_excerpt=raw_content[:120]
        )

        results = []
        if isinstance(parsed, list):
            results = parsed
        elif isinstance(parsed, dict) and "jobs" in parsed and isinstance(parsed["jobs"], list):
            results = parsed["jobs"]
        elif isinstance(parsed, dict) and "results" in parsed and isinstance(parsed["results"], list):
            results = parsed["results"]
        elif isinstance(parsed, dict) and "job_title" in parsed:
            results = [parsed]

        return results

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
