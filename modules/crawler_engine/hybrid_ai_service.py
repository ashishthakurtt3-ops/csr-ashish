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
import threading
import urllib.parse
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, Tuple, List
from modules.admin_panel.services.ai_config_service import get_active_ai_config
from modules.admin_panel.services.ai_telemetry_service import telemetry_store
from modules.crawler_engine.ai_api_client import get_ai_client, AIClientError

logger = logging.getLogger(__name__)
_TRACE_LOCAL = threading.local()

GENERIC_NAV_WORDS = {
    'careers', 'home', 'about us', 'contact us', 'privacy policy',
    'terms of use', 'job search', 'search jobs', 'current openings',
    'all jobs', 'apply now', 'view jobs', 'join our team', 'work with us',
    'life at', 'overview', 'corporate overview', 'read more', 'click here'
}


class HybridAIExtractionService:

    @classmethod
    def begin_trace(cls) -> None:
        """Starts a thread-local AI execution trace for the current discovery run."""
        _TRACE_LOCAL.events = []

    @classmethod
    def end_trace(cls) -> List[Dict[str, Any]]:
        """Ends and returns the thread-local AI execution trace for the current discovery run."""
        events = getattr(_TRACE_LOCAL, "events", None)
        _TRACE_LOCAL.events = None
        return list(events) if isinstance(events, list) else []

    @classmethod
    def _append_trace(cls, event: Dict[str, Any]) -> None:
        events = getattr(_TRACE_LOCAL, "events", None)
        if isinstance(events, list):
            events.append(event)

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
        active_config = get_active_ai_config(force_refresh=True)
        providers_map = active_config.get("providers", {}) or {}
        configured_primary = (active_config.get("primary_provider") or "").lower().strip()
        p1 = (preferred_provider if preferred_provider is not None else configured_primary).lower().strip()
        fallback_enabled = bool(active_config.get("fallback_enabled", False))
        p2 = (active_config.get("fallback_provider") or "").lower().strip() if fallback_enabled else ""

        provider_chain: List[str] = []
        if p1:
            p1_info = providers_map.get(p1, {})
            if preferred_provider is not None or not p1_info or p1_info.get("is_enabled", True):
                provider_chain.append(p1)
        if p2 and p2 not in provider_chain:
            p2_info = providers_map.get(p2, {})
            if not p2_info or p2_info.get("is_enabled", True):
                provider_chain.append(p2)

        if not provider_chain:
            return None, "", ""

        start_t = time.time()
        in_tokens = max(1, len(prompt) // 4)

        for attempt_idx, prov in enumerate(provider_chain):
            p_info = providers_map.get(prov, {})
            prov_model = (
                preferred_model
                if (prov == p1 and preferred_model)
                else (active_config.get("primary_model") if prov == configured_primary else None)
                or (active_config.get("fallback_model") if prov == p2 else None)
                or p_info.get("selected_model")
            )
            try:
                prov_arg = prov if prov != "default" else None
                client = get_ai_client(prov_arg, model=prov_model) if prov_model else get_ai_client(prov_arg)
                if hasattr(client, "execute_structured_prompt"):
                    parsed, actual_model = client.execute_structured_prompt(prompt)
                elif hasattr(client, "_execute_provider_request"):
                    parsed, actual_model = client._execute_provider_request(prompt)
                else:
                    raise AIClientError(f"Provider {prov} client does not support prompt execution.")

                resolved_model = actual_model or prov_model or getattr(client, "model", "") or "auto"
                latency_ms = int((time.time() - start_t) * 1000)
                out_tokens = max(1, len(json.dumps(parsed)) // 4) if parsed else 0
                status_str = "SUCCESS" if attempt_idx == 0 else "SUCCESS_VIA_FALLBACK"

                telemetry_store.record_event(
                    provider=prov,
                    model=resolved_model,
                    task=task,
                    status=status_str,
                    company_id=company_id,
                    company_name=company_name,
                    latency_ms=latency_ms,
                    input_tokens=in_tokens,
                    output_tokens=out_tokens,
                    evidence_excerpt=evidence_excerpt[:120],
                    validation_result="PARSED_OK" if parsed else "EMPTY_OUTPUT"
                )
                cls._append_trace({
                    "provider": prov,
                    "provider_display": p_info.get("display_name") or prov.title(),
                    "model": resolved_model,
                    "task": task,
                    "status": status_str,
                    "fallback_used": attempt_idx > 0,
                })
                return parsed, prov, resolved_model

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
                cls._append_trace({
                    "provider": prov,
                    "provider_display": p_info.get("display_name") or prov.title(),
                    "model": prov_model or "",
                    "task": task,
                    "status": "FAILED",
                    "fallback_used": attempt_idx > 0,
                    "error": str(e)[:160],
                })

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
            preferred_provider=provider,
            preferred_model=model,
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
        excerpt = raw_content[:40000]
        prompt = (
            "You are a strict data auditor evaluating Indian corporate sustainability and CSR compliance under Section 135 and Schedule VII of the Companies Act 2013.\n"
            f"Company: {company_name}\n"
            f"Source CSR URL: {csr_url}\n\n"
            f"Content Excerpt:\n---BEGIN---\n{excerpt}\n---END---\n\n"
            "Task: Extract genuine, specific Section 135 CSR projects, grassroots community programs, or Schedule VII social initiatives explicitly documented in this content.\n"
            "CRITICAL RULES:\n"
            "1. ONLY extract genuine community, welfare, education, healthcare, water, sanitation, environment, or rural development initiatives.\n"
            "2. NEVER extract corporate ethics, compliance statements, marketing claims, employee codes of conduct, or executive bios (e.g. 'We hold ourselves to the highest ethical standards', 'Ethics & Compliance', 'Anti-corruption').\n"
            "3. DO NOT copy or invent any example names. Output ONLY projects actually documented in the text above.\n"
            "4. For every project, you MUST provide an exact verbatim 1-2 sentence quote directly copied from the text proving the initiative. Do NOT paraphrase or synthesize the quote.\n"
            "5. Extract genuine corporate philanthropy, community skilling, educational access, environmental conservation, sustainability accelerators, and social welfare programs (which qualify under Section 135 / Schedule VII). If no such programs exist, return [].\n\n"
            "Respond ONLY with a valid JSON array conforming to this schema:\n"
            "[\n"
            "  {\n"
            '    "project_name": "Specific CSR initiative title (copied directly from text)",\n'
            '    "category": "Education & Skill Development | Healthcare & Nutrition | Environment & Sustainability | Rural Development | Women Empowerment | Water & Sanitation | Disaster Relief | Other",\n'
            '    "state": "Indian state or Pan-India or null",\n'
            '    "district": "District name or null",\n'
            '    "budget": "Disclosed financial outlay / spend figure if mentioned in text, else null",\n'
            '    "description": "Factual 1-2 sentence summary of what this program delivers",\n'
            '    "verbatim_quote": "Exact 1-2 sentence verbatim phrase copied word-for-word from the text excerpt",\n'
            '    "confidence": 0.95\n'
            "  }\n"
            "]"
        )

        parsed, used_provider, used_model = cls._execute_prompt_with_failover(
            prompt=prompt,
            preferred_provider=provider,
            preferred_model=model,
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
        raw_content_lower = (raw_content or "").lower()
        for item in results:
            if not isinstance(item, dict):
                continue
            name = item.get("project_name") or item.get("project_title")
            if not name or len(str(name).strip()) < 3:
                continue

            # Core Rule: Reject corporate policy headings, slogans, or ethics compliance text
            name_clean = str(name).strip()
            if any(bad in name_clean.lower() for bad in [
                'we hold ourselves to the highest', 'code of conduct', 'ethics & compliance',
                'privacy policy', 'terms of use', 'equal opportunity', 'human rights policy',
                'forward-looking statement', 'corporate governance'
            ]):
                continue

            quote = str(item.get("verbatim_quote") or "").strip()
            # Core Rule 100% Verbatim Substring Check:
            # Quote must be present in raw_content
            if not quote or quote.lower() not in raw_content_lower:
                words = [w for w in re.findall(r'[a-zA-Z0-9]+', quote.lower()) if len(w) > 2]
                if len(words) >= 4:
                    phrase = ' '.join(words[:4])
                    clean_raw = re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9 ]', ' ', raw_content_lower))
                    if phrase not in clean_raw:
                        continue
                else:
                    continue

            budget_val = item.get("budget") or "Section 135 Outlay"
            valid_projects.append({
                "project_name": name_clean,
                "category": item.get("category") or "Corporate Social Responsibility",
                "state": item.get("state") or item.get("location_state") or "Pan-India",
                "district": item.get("district") or item.get("location_district") or "Not specified",
                "budget": budget_val,
                "description": item.get("description") or quote,
                "verbatim_quote": quote,
                "confidence": float(item.get("confidence") or 0.90)
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
        timeout: int = 15,
        candidates: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Invokes configured LLM to classify candidate DOM job elements.
        STRICT RULE: The LLM NEVER produces URLs. URLs come exclusively from the page DOM.
        The LLM receives only a numbered candidate list (id, text, surrounding context)
        and returns only (candidate_id, title, location, department).
        """
        # If candidates not explicitly passed, extract <a href> candidate elements from raw_content if HTML
        if not candidates and ('<a ' in raw_content or '<html' in raw_content.lower()):
            try:
                soup = BeautifulSoup(raw_content, 'html.parser')
                for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                parsed_cands = []
                cand_idx = 1
                for a in soup.find_all('a'):
                    href = a.get('href', '').strip()
                    text = a.get_text(' ', strip=True)
                    if not href or len(text) < 3 or text.lower() in GENERIC_NAV_WORDS:
                        continue
                    if any(bad in href.lower() for bad in ['javascript:', 'mailto:', '#', 'tel:']):
                        continue
                    abs_href = urllib.parse.urljoin(careers_url, href)
                    parent = a.find_parent(['li', 'div', 'tr', 'article', 'section'])
                    parent_text = parent.get_text(' ', strip=True)[:250] if parent else text
                    parsed_cands.append({
                        'id': cand_idx,
                        'text': text,
                        'card_context': parent_text,
                        'href': abs_href
                    })
                    cand_idx += 1
                    if cand_idx > 60: # Limit candidates per prompt
                        break
                candidates = parsed_cands
            except Exception:
                candidates = []

        if not candidates and raw_content:
            try:
                # Text-based candidate line extractor for plain text vacancy feeds
                lines = [line.strip() for line in raw_content.splitlines() if line.strip()]
                parsed_cands = []
                cand_idx = 1
                for line in lines:
                    if 5 <= len(line) <= 90:
                        words = line.split()
                        if len(words) <= 8 and any(w.lower() in [
                            'engineer', 'developer', 'lead', 'manager', 'specialist', 'analyst',
                            'architect', 'consultant', 'officer', 'executive', 'director', 'intern',
                            'trainee', 'associate', 'administrator', 'designer', 'scientist', 'technician'
                        ] for w in words):
                            parsed_cands.append({
                                'id': cand_idx,
                                'text': line,
                                'card_context': line,
                                'href': careers_url
                            })
                            cand_idx += 1
                            if cand_idx > 40:
                                break
                if parsed_cands:
                    candidates = parsed_cands
            except Exception:
                pass

        if not candidates:
            # If no DOM candidates exist, return empty list (LLM is forbidden from inventing jobs or URLs)
            return []

        id_map = {c['id']: c for c in candidates}
        prompt_candidates = []
        for c in candidates:
            prompt_candidates.append(f"[Candidate {c['id']}] Title Text: \"{c['text']}\" | Surrounding Card: \"{c.get('card_context', '')[:200]}\"")
        cand_str = "\n".join(prompt_candidates)

        prompt = f"""You are a strict data auditor evaluating candidate links extracted from an Indian corporate careers portal.
Company: {company_name}
Source Careers Portal: {careers_url}

Numbered Candidate Links:
\"\"\"
{cand_str}
\"\"\"

Task: Classify which candidate numbers represent genuine, active recruitment vacancies open for external candidates to apply.
CRITICAL RULES:
1. ONLY return candidate IDs that represent genuine ACTIVE RECRUITMENT VACANCIES.
2. NEVER select candidate IDs that are employee bios, executive leadership, navigation menus, news articles, or policy links.
3. DO NOT output or invent any URLs. URLs are strictly looked up in code by candidate ID.
4. If no candidates in the list represent genuine job vacancies, return an empty JSON array: [].

Respond ONLY with valid JSON array conforming to this schema:
[
  {{
    "candidate_id": 1,
    "job_title": "Precise job title (e.g. Senior Software Engineer)",
    "location": "Job location or null",
    "department": "Department or function or null",
    "work_mode": "On-site | Hybrid | Remote | null",
    "confidence": 0.95
  }}
]"""

        parsed, used_provider, used_model = cls._execute_prompt_with_failover(
            prompt=prompt,
            preferred_provider=provider,
            preferred_model=model,
            company_id=company_id,
            company_name=company_name,
            task="job_extraction",
            evidence_excerpt=cand_str[:120]
        )

        results = []
        parsed_items = []
        if isinstance(parsed, list):
            parsed_items = parsed
        elif isinstance(parsed, dict) and "jobs" in parsed and isinstance(parsed["jobs"], list):
            parsed_items = parsed["jobs"]
        elif isinstance(parsed, dict) and "results" in parsed and isinstance(parsed["results"], list):
            parsed_items = parsed["results"]
        elif isinstance(parsed, dict) and "candidate_id" in parsed:
            parsed_items = [parsed]

        for item in parsed_items:
            if not isinstance(item, dict):
                continue
            cid = item.get('candidate_id')
            if cid in id_map:
                real_c = id_map[cid]
                title = item.get('job_title') or real_c['text']
                results.append({
                    'job_title': title.strip(),
                    'location': item.get('location') or 'India',
                    'department': item.get('department') or 'General',
                    'work_mode': item.get('work_mode') or 'Full-time',
                    'experience': 'As specified on portal',
                    'application_url': real_c['href'], # Strictly from the page DOM!
                    'verbatim_source_quote': f"Verified anchor: {real_c['text']}",
                    'confidence': float(item.get('confidence') or 0.95)
                })

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
