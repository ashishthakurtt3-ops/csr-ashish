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
from modules.crawler_engine.normalizers import is_generic_landing_url

logger = logging.getLogger(__name__)
_TRACE_LOCAL = threading.local()
_TRACE_LOCK = threading.Lock()
_ACTIVE_PARENT_TRACES: Dict[int, List[Dict[str, Any]]] = {}
_ACTIVE_GLOBAL_TRACE_LIST: List[List[Dict[str, Any]]] = []

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
        events: List[Dict[str, Any]] = []
        _TRACE_LOCAL.events = events
        tid = threading.get_ident()
        with _TRACE_LOCK:
            _ACTIVE_PARENT_TRACES[tid] = events
            if events not in _ACTIVE_GLOBAL_TRACE_LIST:
                _ACTIVE_GLOBAL_TRACE_LIST.append(events)

    @classmethod
    def get_trace(cls) -> List[Dict[str, Any]]:
        """Returns the thread-local AI execution trace without clearing it."""
        events = getattr(_TRACE_LOCAL, "events", None)
        return list(events) if isinstance(events, list) else []

    @classmethod
    def end_trace(cls) -> List[Dict[str, Any]]:
        """Ends and returns the thread-local AI execution trace for the current discovery run."""
        events = getattr(_TRACE_LOCAL, "events", None)
        _TRACE_LOCAL.events = None
        tid = threading.get_ident()
        with _TRACE_LOCK:
            _ACTIVE_PARENT_TRACES.pop(tid, None)
            if events in _ACTIVE_GLOBAL_TRACE_LIST:
                _ACTIVE_GLOBAL_TRACE_LIST.remove(events)
        return list(events) if isinstance(events, list) else []

    @classmethod
    def _append_trace(cls, event: Dict[str, Any]) -> None:
        events = getattr(_TRACE_LOCAL, "events", None)
        if isinstance(events, list):
            with _TRACE_LOCK:
                events.append(event)
            return
        # If running inside a concurrent worker thread where _TRACE_LOCAL is not initialized,
        # publish directly into the active parent trace.
        with _TRACE_LOCK:
            if _ACTIVE_GLOBAL_TRACE_LIST:
                _ACTIVE_GLOBAL_TRACE_LIST[-1].append(event)

    @classmethod
    def aggregate_thread_traces(cls, traces: List[Any]) -> Dict[str, Any]:
        """
        Combines trace events or summaries from concurrent worker threads into
        the current parent thread's active trace context before end_trace().
        """
        target = getattr(_TRACE_LOCAL, "events", None)
        if target is None:
            target = []
            _TRACE_LOCAL.events = target
            with _TRACE_LOCK:
                if target not in _ACTIVE_GLOBAL_TRACE_LIST:
                    _ACTIVE_GLOBAL_TRACE_LIST.append(target)

        with _TRACE_LOCK:
            for t in traces:
                if not t:
                    continue
                ev_list = []
                if isinstance(t, list):
                    ev_list = t
                elif isinstance(t, dict):
                    if "events" in t and isinstance(t["events"], list):
                        ev_list = t["events"]
                    else:
                        ev_list = [t]
                for ev in ev_list:
                    if isinstance(ev, dict) and ev not in target:
                        target.append(ev)

        return {
            "status": "success",
            "events_count": len(target),
            "events": list(target),
            "providers_used": list({ev.get("provider") for ev in target if ev.get("provider")}),
            "models_used": list({ev.get("model") for ev in target if ev.get("model")}),
        }

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
    def _verify_quote_resilient(cls, quote: str, text: str) -> bool:
        """
        Resilient quotation verification supporting exact, normalized alphanumeric,
        continuous n-gram, and token overlap matching to accommodate LLM formatting.
        """
        if not quote or not text:
            return False
        q_lower = quote.strip().lower()
        t_lower = text.lower()
        # 1. Exact substring
        if q_lower in t_lower:
            return True
        # 2. Normalized alphanumeric
        norm_q = re.sub(r'[^a-z0-9 ]', ' ', q_lower).strip()
        norm_t = re.sub(r'[^a-z0-9 ]', ' ', t_lower)
        norm_q = re.sub(r'\s+', ' ', norm_q)
        norm_t = re.sub(r'\s+', ' ', norm_t)
        if norm_q and norm_q in norm_t:
            return True
        # 3. Continuous N-gram match (min 4 words)
        words_q = [w for w in norm_q.split() if len(w) > 1]
        if len(words_q) >= 4:
            n = min(len(words_q), 5)
            for i in range(len(words_q) - n + 1):
                sub = ' '.join(words_q[i:i+n])
                if sub in norm_t:
                    return True
        # 4. Token overlap of significant words (>= 75%)
        sig_words = [w for w in words_q if len(w) >= 3 and w not in GENERIC_NAV_WORDS]
        if len(sig_words) >= 3:
            found = sum(1 for w in sig_words if w in norm_t)
            if (found / len(sig_words)) >= 0.75:
                return True
        return False

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
        Uses compact batched prompts (max ~7,000 chars per batch) with token limit protection.
        Enforces strict JSON array schema, verbatim quotations, and token telemetry recording.
        """
        if not raw_content:
            return []

        # Partition into compact chunks of max ~7,000 characters to prevent 429 quota exhaustion
        chunks = []
        MAX_CHUNK_CHARS = 7000
        if len(raw_content) <= MAX_CHUNK_CHARS:
            chunks = [raw_content]
        else:
            # Split by double-newlines, paragraphs, or section headings
            raw_sections = [s.strip() for s in re.split(r'\n{2,}|\r\n{2,}', raw_content) if s.strip()]
            curr_chunk = []
            curr_len = 0
            for sec in raw_sections:
                sec_len = len(sec)
                if curr_len + sec_len > MAX_CHUNK_CHARS and curr_chunk:
                    chunks.append("\n\n".join(curr_chunk))
                    curr_chunk = [sec]
                    curr_len = sec_len
                else:
                    curr_chunk.append(sec)
                    curr_len += sec_len
            if curr_chunk:
                chunks.append("\n\n".join(curr_chunk))

            # Prioritize chunks with high CSR / Section 135 keyword density
            csr_keywords = [
                'section 135', 'schedule vii', 'csr', 'sustainability', 'initiative',
                'project', 'community', 'education', 'healthcare', 'sanitation',
                'environment', 'rural', 'skilling', 'crore', 'lakh', 'beneficiar',
                'expenditure', 'outlay', 'social', 'welfare', 'program'
            ]
            scored_chunks = []
            for ch in chunks:
                ch_lower = ch.lower()
                score = sum(ch_lower.count(k) for k in csr_keywords)
                scored_chunks.append((score, ch))
            # Sort descending by CSR relevance
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            # Evaluate top 2-3 chunks max to respect time and quota budgets
            chunks = [ch for _, ch in scored_chunks[:3]]

        valid_projects = []
        seen_names = set()

        for chunk_idx, excerpt in enumerate(chunks, start=1):
            prompt = (
                "You are a strict data auditor evaluating Indian corporate sustainability and CSR compliance under Section 135 and Schedule VII of the Companies Act 2013.\n"
                f"Company: {company_name}\n"
                f"Source CSR URL: {csr_url}\n\n"
                f"Content Excerpt (Batch {chunk_idx}):\n---BEGIN---\n{excerpt[:MAX_CHUNK_CHARS]}\n---END---\n\n"
                "Task: Extract genuine, specific Section 135 CSR projects, grassroots community programs, or Schedule VII social initiatives explicitly documented in this content.\n"
                "CRITICAL RULES:\n"
                "1. ONLY extract genuine community, welfare, education, healthcare, water, sanitation, environment, or rural development initiatives.\n"
                "2. NEVER extract corporate ethics, compliance statements, marketing claims, employee codes of conduct, or executive bios (e.g. 'We hold ourselves to the highest ethical standards', 'Ethics & Compliance', 'Anti-corruption').\n"
                "3. DO NOT copy or invent any example names. Output ONLY projects actually documented in the text above.\n"
                "4. For every project, you MUST provide an exact verbatim 1-2 sentence quote directly copied from the text proving the initiative. Do NOT paraphrase or synthesize the quote.\n"
                "5. Extract genuine corporate philanthropy, community skilling, educational access, environmental conservation, sustainability accelerators, and social welfare programs (which qualify under Section 135 / Schedule VII). If no such programs exist, return [].\n"
                "6. If budget, state, district, or beneficiaries are not explicitly stated in the source text, set them to null. NEVER guess, assume, or fabricate financial or geographic figures.\n"
                "7. For description, you MUST copy the exact sentence or phrasing from the text excerpt explaining what this program delivers. NEVER invent, paraphrase, or synthesize a new summary.\n\n"
                "Respond ONLY with a valid JSON array conforming to this schema:\n"
                "[\n"
                "  {\n"
                '    "project_name": "Specific CSR initiative title (copied directly from text)",\n'
                '    "category": "Education & Skill Development | Healthcare & Nutrition | Environment & Sustainability | Rural Development | Women Empowerment | Water & Sanitation | Disaster Relief | Other",\n'
                '    "state": "Indian state if explicitly mentioned, else null",\n'
                '    "district": "District name if explicitly mentioned, else null",\n'
                '    "budget": "Disclosed financial spend / budget figure if explicitly mentioned, else null",\n'
                '    "description": "Exact 1-2 sentence verbatim excerpt from the text describing what this program does (do not invent or rephrase)",\n'
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
                evidence_excerpt=excerpt[:120]
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

            for item in results:
                if not isinstance(item, dict):
                    continue
                name = item.get("project_name") or item.get("project_title")
                if not name or len(str(name).strip()) < 3:
                    continue

                name_clean = str(name).strip()
                norm_name_key = name_clean.lower()
                if norm_name_key in seen_names:
                    continue

                # Reject corporate policy headings, slogans, or ethics compliance text
                if any(bad in norm_name_key for bad in [
                    'we hold ourselves to the highest', 'code of conduct', 'ethics & compliance',
                    'privacy policy', 'terms of use', 'equal opportunity', 'human rights policy',
                    'forward-looking statement', 'corporate governance'
                ]):
                    continue

                quote = str(item.get("verbatim_quote") or "").strip()
                # Resilient quotation check in raw_content
                if quote and not cls._verify_quote_resilient(quote, raw_content):
                    continue

                seen_names.add(norm_name_key)
                raw_b = str(item.get("budget") or "").strip()
                budget_val = raw_b if raw_b and raw_b.lower() not in ('null', 'none', 'n/a', 'not published', 'not specified', 'section 135 outlay', 'not mentioned', '') else 'Not Mentioned'

                raw_st = str(item.get("state") or item.get("location_state") or "").strip()
                state_val = raw_st if raw_st and raw_st.lower() not in ('null', 'none', 'n/a', 'not specified', 'not mentioned', '') else 'Not Mentioned'

                raw_dist = str(item.get("district") or item.get("location_district") or "").strip()
                district_val = raw_dist if raw_dist and raw_dist.lower() not in ('null', 'none', 'n/a', 'not specified', 'not mentioned', '') else 'Not Mentioned'

                # The summary/description must be the exact excerpt as mentioned on the page (verbatim quote or exact page sentence)
                exact_text = quote if (quote and len(quote) > 15) else (str(item.get("description") or "").strip() or "Not Mentioned")

                valid_projects.append({
                    "project_name": name_clean,
                    "category": item.get("category") or "Corporate Social Responsibility",
                    "state": state_val,
                    "district": district_val,
                    "budget": budget_val,
                    "description": exact_text,
                    "summary": exact_text,
                    "verbatim_quote": quote or exact_text,
                    "confidence": float(item.get("confidence") or 0.90)
                })

        return valid_projects

    @classmethod
    def summarize_csr_report(
        cls,
        company_id: str,
        company_name: str,
        report_url: str,
        raw_content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 18
    ) -> Dict[str, Any]:
        """Summarises a CSR / annual / BRSR / sustainability document using the
        configured AI provider.  The model must stay grounded in the supplied
        text; the caller stores the original document URL as evidence.

        Returns a dict with summary, topics, initiatives, key_findings,
        expenditure, beneficiaries, geographic_coverage, implementing_partners,
        financial_year and evidence_quote.  Returns {} when the provider fails
        or the response cannot be parsed.
        """
        if not raw_content or len(raw_content.strip()) < 200:
            return {}

        excerpt = raw_content[:14000]
        prompt = (
            "You are a strict corporate disclosure analyst. Summarise the official corporate report below "
            "for an Indian CSR intelligence database.\n"
            f"Company: {company_name}\n"
            f"Document URL: {report_url}\n\n"
            f"Document text:\n---BEGIN---\n{excerpt}\n---END---\n\n"
            "RULES:\n"
            "1. Use ONLY facts stated in the document. Do not invent numbers, projects, partners or locations.\n"
            "2. This is a document-level report, not an individual project. Summarise the document as a whole.\n"
            "3. Provide an evidence_quote copied verbatim from the text (1-2 sentences).\n"
            "4. Extract the financial year if stated (e.g. FY 2023-24).\n"
            "5. Return ONLY a valid JSON object with this schema:\n"
            "{\n"
            '  "summary": "concise 3-5 sentence summary",\n'
            '  "financial_year": "FY 2023-24 or null",\n'
            '  "topics": ["CSR topic", "..."],\n'
            '  "initiatives": ["major initiative mentioned", "..."],\n'
            '  "key_findings": ["important finding", "..."],\n'
            '  "expenditure": "disclosed CSR spend or null",\n'
            '  "beneficiaries": "beneficiary groups or null",\n'
            '  "geographic_coverage": "states/regions or null",\n'
            '  "implementing_partners": "partners or null",\n'
            '  "evidence_quote": "verbatim quote from document"\n'
            "}"
        )
        parsed, _used_provider, _used_model = cls._execute_prompt_with_failover(
            prompt=prompt,
            preferred_provider=provider,
            preferred_model=model,
            company_id=company_id,
            company_name=company_name,
            task="csr_report_summary",
            evidence_excerpt=excerpt[:120],
        )
        if not isinstance(parsed, dict):
            return {}

        def _clean(value: Any) -> str:
            if value is None:
                return ''
            if isinstance(value, (list, tuple)):
                return '; '.join(str(v).strip() for v in value if str(v).strip())
            return str(value).strip()

        def _items(value: Any) -> List[str]:
            if isinstance(value, list):
                return [str(v).strip() for v in value if str(v).strip()]
            if isinstance(value, str) and value.strip():
                return [part.strip() for part in re.split(r'[;\n]+', value) if part.strip()]
            return []

        summary = _clean(parsed.get("summary"))
        if len(summary) < 30:
            return {}

        evidence_quote = _clean(parsed.get("evidence_quote"))
        if evidence_quote and not cls._verify_quote_resilient(evidence_quote, raw_content):
            evidence_quote = ''

        return {
            "summary": summary[:4000],
            "financial_year": _clean(parsed.get("financial_year"))[:30],
            "topics": _items(parsed.get("topics")),
            "initiatives": _items(parsed.get("initiatives")),
            "key_findings": _items(parsed.get("key_findings")),
            "expenditure": _clean(parsed.get("expenditure"))[:1000],
            "beneficiaries": _clean(parsed.get("beneficiaries"))[:2000],
            "geographic_coverage": _clean(parsed.get("geographic_coverage"))[:1000],
            "implementing_partners": _clean(parsed.get("implementing_partners"))[:2000],
            "evidence_quote": evidence_quote[:4000],
        }

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
        Prioritizes links inside <main>, <article>, <section>, and job card containers over generic nav links.
        Batches candidate items into compact prompts (15 items per batch) with token limit protection.
        """
        if not candidates and ('<a ' in raw_content or '<html' in raw_content.lower()):
            try:
                soup = BeautifulSoup(raw_content, 'html.parser')
                # 1. Decompose noisy layout & non-content tags
                for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript', 'svg', 'iframe']):
                    tag.decompose()

                # 2. Decompose non-content containers (cookie banners, popups, footers, headers)
                for el in soup.find_all(attrs={'class': True}):
                    classes = ' '.join(el.get('class', [])).lower()
                    if re.search(r'\b(cookie|banner|modal|popup|social|footer|header|navbar)\b', classes):
                        if not re.search(r'\b(job|career|vacancy|opening|position|role|listing)\b', classes):
                            el.decompose()

                seen_cands = set()
                tier1_cands = []
                tier2_cands = []
                tier3_cands = []

                def _evaluate_anchor(a_tag, priority_tier):
                    href = a_tag.get('href', '').strip()
                    text = a_tag.get_text(' ', strip=True)
                    if not href or len(text) < 3 or len(text) > 180:
                        return
                    norm_text = text.lower()
                    if norm_text in GENERIC_NAV_WORDS:
                        return
                    if any(norm_text == bad or bad in norm_text for bad in [
                        'sign in', 'log in', 'login', 'register', 'privacy policy', 'terms & conditions',
                        'terms of service', 'cookie policy', 'view all', 'learn more', 'read more', 'back to top'
                    ]):
                        return
                    if any(bad in href.lower() for bad in [
                        'javascript:', 'mailto:', '#', 'tel:', 'whatsapp:', 'callto:',
                        'linkedin.com/company', 'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com'
                    ]):
                        return

                    abs_href = urllib.parse.urljoin(careers_url, href)
                    if not abs_href or is_generic_landing_url(abs_href) or abs_href.rstrip('/') == careers_url.rstrip('/'):
                        return
                    cand_key = (abs_href.lower(), norm_text)
                    if cand_key in seen_cands:
                        return
                    seen_cands.add(cand_key)

                    parent = a_tag.find_parent(['li', 'div', 'tr', 'article', 'section'])
                    parent_text = parent.get_text(' ', strip=True)[:250] if parent else text
                    cand_item = {
                        'text': text,
                        'card_context': parent_text,
                        'href': abs_href
                    }
                    if priority_tier == 1:
                        tier1_cands.append(cand_item)
                    elif priority_tier == 2:
                        tier2_cands.append(cand_item)
                    else:
                        tier3_cands.append(cand_item)

                # Tier 1: Dedicated vacancy/job containers or cards
                job_container_regex = re.compile(r'(?:job|career|vacancy|opening|position|role|opportunity|listing|posting|result)', re.I)
                for container in soup.find_all(lambda tag: tag.name in ['div', 'li', 'article', 'section', 'tr', 'td', 'ul'] and (
                    job_container_regex.search(' '.join(tag.get('class', []))) or
                    job_container_regex.search(tag.get('id', ''))
                )):
                    for a in container.find_all('a'):
                        _evaluate_anchor(a, priority_tier=1)

                # Tier 2: Semantic content containers (<main>, <article>, <section>, role="main")
                for sem in soup.find_all(['main', 'article', 'section']):
                    for a in sem.find_all('a'):
                        _evaluate_anchor(a, priority_tier=2)
                for sem in soup.find_all(attrs={'role': 'main'}):
                    for a in sem.find_all('a'):
                        _evaluate_anchor(a, priority_tier=2)

                # Tier 3: General document anchors (fallback)
                for a in soup.find_all('a'):
                    _evaluate_anchor(a, priority_tier=3)

                ordered_cands = tier1_cands + tier2_cands + tier3_cands
                parsed_cands = []
                for idx, c in enumerate(ordered_cands[:60], start=1):
                    c['id'] = idx
                    parsed_cands.append(c)
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
                                'href': ''
                            })
                            cand_idx += 1
                            if cand_idx > 40:
                                break
                if parsed_cands:
                    candidates = parsed_cands
            except Exception:
                pass

        if not candidates:
            return []

        id_map = {c['id']: c for c in candidates}
        results = []
        BATCH_SIZE = 15

        for b_start in range(0, len(candidates), BATCH_SIZE):
            batch = candidates[b_start:b_start + BATCH_SIZE]
            prompt_candidates = []
            for c in batch:
                prompt_candidates.append(
                    f"[Candidate {c['id']}] Title Text: \"{c['text'][:100]}\" | Surrounding Card: \"{c.get('card_context', '')[:150]}\""
                )
            cand_str = "\n".join(prompt_candidates)

            prompt = f"""You are a strict data auditor evaluating candidate links extracted from an Indian corporate careers portal.
Company: {company_name}
Source Careers Portal: {careers_url}

Numbered Candidate Links (Batch {b_start // BATCH_SIZE + 1}):
\"\"\"
{cand_str}
\"\"\"

Task: Classify which candidate numbers represent genuine, active recruitment vacancies open for external candidates to apply.
CRITICAL RULES:
1. ONLY return candidate IDs that represent genuine ACTIVE RECRUITMENT VACANCIES.
2. NEVER select candidate IDs that are employee bios, executive leadership, navigation menus, news articles, or policy links.
3. DO NOT output or invent any URLs. URLs are strictly looked up in code by candidate ID.
4. If no candidates in this batch represent genuine job vacancies, return an empty JSON array: [].

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
                    app_u = real_c.get('href', '').strip()
                    if not app_u or is_generic_landing_url(app_u):
                        continue
                    title = (item.get('job_title') or real_c['text']).strip()
                    results.append({
                        'job_title': title,
                        'location': item.get('location') or 'India',
                        'department': item.get('department') or 'General',
                        'work_mode': item.get('work_mode') or 'Full-time',
                        'experience': 'As specified on portal',
                        'application_url': app_u, # Strictly from the page DOM!
                        'verbatim_source_quote': f"Verified anchor: {real_c['text']}",
                        'confidence': float(item.get('confidence') or 0.95)
                    })

        return results

    @classmethod
    def extract_jobs_concurrent(
        cls,
        content: str,
        source_url: str,
        company_name: str,
        company_id: str = "",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Independent concurrent AI agent for Job Discovery.
        Extracts verified active vacancies from page content using prioritized DOM candidate
        selection and compact batched prompts, emitting trace events to thread-safe telemetry.
        """
        return cls.extract_unstructured_jobs(
            company_id=company_id or company_name,
            company_name=company_name,
            raw_content=content,
            careers_url=source_url,
            provider=provider,
            model=model,
            timeout=timeout
        )

    @classmethod
    def extract_csr_concurrent(
        cls,
        content: str,
        source_url: str,
        company_name: str,
        company_id: str = "",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 15
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Independent concurrent AI agent for CSR Discovery.
        Extracts verified Section 135 CSR projects and statutory report assets (PDFs/disclosures)
        from page content using compact batched prompts, emitting trace events to thread-safe telemetry.
        Returns (projects_list, reports_list).
        """
        # 1. Extract Section 135 projects
        projects = cls.extract_unstructured_csr_projects(
            company_id=company_id or company_name,
            company_name=company_name,
            raw_content=content,
            csr_url=source_url,
            provider=provider,
            model=model,
            timeout=timeout
        )

        # 2. Extract CSR & statutory reports (PDFs, annual reports, BRSR, sustainability filings)
        reports = []
        seen_report_urls = set()

        if source_url and source_url.lower().endswith('.pdf'):
            reports.append({
                'report_name': f"{company_name} Statutory Report",
                'report_url': source_url,
                'report_type': 'CSR_REPORT',
                'source_url': source_url,
            })
            seen_report_urls.add(source_url.lower())

        if content and ('<a ' in content or '<html' in content.lower()):
            try:
                soup = BeautifulSoup(content, 'html.parser')
                report_keywords = ['csr', 'sustainability', 'annual-report', 'annual_report', 'annual report',
                                   'schedule-vii', 'schedule_vii', 'section-135', 'section_135', 'brsr', 'esg']
                for a in soup.find_all('a', href=True):
                    href = a['href'].strip()
                    text = a.get_text(' ', strip=True)
                    h_lower = href.lower()
                    t_lower = text.lower()
                    if h_lower.endswith('.pdf') or any(k in h_lower or k in t_lower for k in report_keywords):
                        abs_url = urllib.parse.urljoin(source_url, href)
                        if abs_url.lower() not in seen_report_urls and not any(bad in abs_url.lower() for bad in ['javascript:', '#', 'mailto:']):
                            seen_report_urls.add(abs_url.lower())
                            rtype = 'CSR_REPORT'
                            if 'brsr' in h_lower or 'brsr' in t_lower:
                                rtype = 'BRSR_REPORT'
                            elif 'sustainability' in h_lower or 'sustainability' in t_lower or 'esg' in h_lower:
                                rtype = 'SUSTAINABILITY_REPORT'
                            elif 'annual' in h_lower or 'annual' in t_lower:
                                rtype = 'ANNUAL_REPORT'

                            rname = text if len(text) >= 5 else f"{company_name} {rtype.replace('_', ' ').title()}"
                            reports.append({
                                'report_name': rname[:120],
                                'report_url': abs_url,
                                'report_type': rtype,
                                'source_url': source_url,
                            })
            except Exception as e:
                logger.debug(f"Report link extraction note: {e}")

        return projects, reports

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
        # Require every distinctive title word (at least two) to be grounded in the
        # source.  The previous `any()` fallback accepted unrelated candidates that
        # merely shared a generic word such as "project" with the page.
        if len(title_words) >= 2 and all(w in source_lower for w in title_words):
            return True, "Project title verified in source content"

        return False, "Failed independent verification: statutory evidence not confirmed in source"


# Module-level aliases conforming to interface contract
extract_jobs_concurrent = HybridAIExtractionService.extract_jobs_concurrent
extract_csr_concurrent = HybridAIExtractionService.extract_csr_concurrent
aggregate_thread_traces = HybridAIExtractionService.aggregate_thread_traces
