"""
modules/crawler_engine/ai_api_client.py
=======================================
Dedicated AI API Client Adapter Layer for Official Website Discovery and Page Classification.

Active Primary Provider:
- OpenRouter API (Free Models Router: `openrouter/free`, `meta-llama/llama-3.3-70b-instruct:free`, etc.)
  - Base URL: `https://openrouter.ai/api/v1`
  - Endpoint: `/chat/completions`
  - Captures and records the dynamically returned actual model for every classification.

Secondary / Extensible Provider:
- Google Gemini Hosted API (`gemini-2.5-flash`, `gemini-1.5-flash`)

Features:
- Strict Schema Validation: Enforces required keys, valid broad/candidate categories, and valid page types.
- SQLite Persistent Disk Cache (`PersistentDiskCache`): Caches responses by content hash, stage, and model.
- Bounded Retries: Exponential backoff on transient 5xx server errors.
- Free-Tier Quota Exhaustion Handling: Catches HTTP 429 and 402, sets flags, raises `QuotaExhaustedError`,
  persists checkpoints, and pauses safely without switching to paid models.
- High-Precision Deterministic Fallbacks: Rule-based fallback for offline testing or when API key is unconfigured.
"""

import os
import re
import json
import time
import logging
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import requests

from . import ai_classifier_config as cfg

logger = logging.getLogger(__name__)


class AIClientError(Exception):
    """Base exception for AI API client failures."""
    pass


class QuotaExhaustedError(AIClientError):
    """Raised when the free-tier API quota has been exhausted (HTTP 429 / HTTP 402 / RESOURCE_EXHAUSTED)."""
    pass


class ZeroCostPolicyViolationError(QuotaExhaustedError):
    """Raised when an operation would violate the strict zero-cost requirement."""
    pass


class AIClient:
    """Base interface for all AI classification adapters."""

    def classify_links_batch(self, company_name: str, domain: str, links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def classify_page_content(self, company_name: str, url: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def get_metrics(self) -> Dict[str, Any]:
        raise NotImplementedError


class PersistentDiskCache:
    """Lightweight SQLite-backed cache for AI classification prompts and responses."""

    def __init__(self, cache_dir: Optional[str] = None):
        cache_dir = str(cache_dir or cfg.CACHE_DIR)
        os.makedirs(cache_dir, exist_ok=True)
        self.db_path = os.path.join(cache_dir, "ai_cache.sqlite3")
        self._init_db()

    def _init_db(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ai_cache (
                    cache_key TEXT PRIMARY KEY,
                    model_name TEXT,
                    stage TEXT,
                    response_json TEXT,
                    created_at TEXT,
                    provider TEXT DEFAULT 'openrouter',
                    prompt_version TEXT DEFAULT 'v1.0'
                )
            """)
            cursor = conn.execute("PRAGMA table_info(ai_cache)")
            cols = {row[1] for row in cursor.fetchall()}
            if "provider" not in cols:
                conn.execute("ALTER TABLE ai_cache ADD COLUMN provider TEXT DEFAULT 'openrouter'")
            if "prompt_version" not in cols:
                conn.execute("ALTER TABLE ai_cache ADD COLUMN prompt_version TEXT DEFAULT 'v1.0'")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_cache_created ON ai_cache(created_at)")
            conn.commit()
        except Exception as e:
            logger.warning("Failed to initialize SQLite AI cache: %s", e)
        finally:
            if conn:
                conn.close()

    def get(
        self,
        cache_key: str,
        max_age_hours: int = 168,
        expected_provider: Optional[str] = None,
        expected_model: Optional[str] = None,
        allow_fallback: bool = False
    ) -> Optional[Any]:
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT response_json, created_at, model_name, provider FROM ai_cache WHERE cache_key = ?",
                (cache_key,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            resp_text, created_at_str, model_name, provider = row
            created_dt = datetime.fromisoformat(created_at_str)
            age_hours = (datetime.utcnow() - created_dt).total_seconds() / 3600.0
            if age_hours > max_age_hours:
                return None

            # Requirement 5: Never reuse fallback or wrong-model/wrong-provider entries as valid AI results
            if not allow_fallback and (model_name or "").lower() in ("fallback", "rule_based_fallback", "offline_fallback"):
                return None
            if expected_provider and provider and provider.lower() != expected_provider.lower():
                return None
            if expected_model and model_name and model_name.lower() != expected_model.lower():
                return None

            data = json.loads(resp_text)
            if not allow_fallback:
                if isinstance(data, list):
                    if any(isinstance(item, dict) and item.get("actual_model") in ("fallback", "rule_based_fallback") for item in data):
                        return None
                elif isinstance(data, dict):
                    if data.get("actual_model") in ("fallback", "rule_based_fallback"):
                        return None

            return data
        except Exception as e:
            logger.debug("Cache lookup error for key %s: %s", cache_key, e)
            return None
        finally:
            if conn:
                conn.close()

    def set(self, cache_key: str, model_name: str, stage: str, data: Any, provider: Optional[str] = None, prompt_version: Optional[str] = None):
        # Requirement 5: Results produced by rule_based_fallback must not be cached as AI classifications
        if (model_name or "").lower() in ("fallback", "rule_based_fallback", "offline_fallback"):
            return

        conn = None
        try:
            prov = provider or cfg.AI_PROVIDER
            p_ver = prompt_version or cfg.PROMPT_VERSION
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """
                INSERT OR REPLACE INTO ai_cache (cache_key, model_name, stage, response_json, created_at, provider, prompt_version)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (cache_key, model_name, stage, json.dumps(data), datetime.utcnow().isoformat(), prov, p_ver)
            )
            conn.commit()
        except Exception as e:
            logger.debug("Cache write error for key %s: %s", cache_key, e)
        finally:
            if conn:
                conn.close()

    def purge_invalid_cache(self) -> int:
        """Purges any cached responses produced by rule_based_fallback or deprecated models."""
        conn = None
        deleted = 0
        try:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute(
                "DELETE FROM ai_cache WHERE model_name IN ('fallback', 'rule_based_fallback', 'gemini-2.5-flash') "
                "OR response_json LIKE '%rule_based_fallback%'"
            )
            deleted = cur.rowcount
            conn.commit()
            if deleted > 0:
                logger.info("Purged %d invalid/fallback rows from AI classification disk cache.", deleted)
        except Exception as e:
            logger.warning("Cache purge failed: %s", e)
        finally:
            if conn:
                conn.close()
        return deleted



class BaseAIClient(AIClient):
    """
    Common base class implementing prompt construction, JSON parsing, schema validation,
    disk caching, metric tracking, and deterministic fallback logic.
    """

    def __init__(self):
        self.api_key = os.environ.get(cfg.AI_API_KEY_ENV, "").strip()
        self.model = cfg.AI_MODEL
        self.base_url = cfg.AI_BASE_URL.rstrip('/')
        self.cache = PersistentDiskCache(str(cfg.CACHE_DIR)) if cfg.AI_CACHE_ENABLED else None
        self.max_api_calls = cfg.MAX_API_CALLS_PER_RUN

        # Metrics
        self.metrics = {
            "api_calls_made": 0,
            "cache_hits": 0,
            "quota_warnings": 0,
            "retries_count": 0,
            "errors_count": 0,
            "quota_exhausted": False,
            "models_used": {},
        }

    @property
    def model_name(self) -> str:
        return getattr(self, "model", cfg.AI_MODEL)

    def _build_cache_key(self, stage: str, payload: Any, content_hash: Optional[str] = None) -> str:
        serialized = json.dumps(payload, sort_keys=True, default=str)
        payload_hash = content_hash or hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        prov = getattr(self, "provider_name", cfg.AI_PROVIDER)
        raw = f"{prov}:{self.model}:{cfg.PROMPT_VERSION}:{stage}:{payload_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _clean_json_text(self, raw_text: str) -> Any:
        """Strips markdown codeblocks and extracts valid JSON objects or arrays."""
        text = str(raw_text or "").strip()
        # Strip reasoning thinking tags if present
        text = re.sub(r'<think>[\s\S]*?</think>', '', text).strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # 1. Direct parse attempt
        try:
            return json.loads(text)
        except Exception:
            pass

        # 2. Raw decode attempt from first bracket to ignore trailing commentary
        for i, ch in enumerate(text):
            if ch in ('{', '['):
                try:
                    obj, _ = json.JSONDecoder().raw_decode(text[i:])
                    return obj
                except Exception:
                    continue

        # 3. Fallback regex extraction of embedded JSON array or object
        match = re.search(r'(\[[\s\S]*\]|\{[\s\S]*\})', text)
        if match:
            return json.loads(match.group(1))

        raise AIClientError(f"Failed to parse JSON from AI response: {text[:200]}")

    def _execute_provider_request(self, prompt: str) -> Tuple[Any, str]:
        """
        Executes HTTP request against the configured provider.
        Must return a tuple: (parsed_json_data, actual_model_name).
        """
        raise NotImplementedError

    def _validate_stage1_schema(self, data: Any, links: List[Dict[str, Any]], actual_model: str) -> List[Dict[str, Any]]:
        """
        Validates Stage 1 output against the required schema.
        Ensures valid broad categories, candidate categories, confidence range, and records actual model.
        """
        valid_broad = {
            "CAREERS_RECRUITMENT", "CSR_SOCIAL_IMPACT", "SUSTAINABILITY_ESG",
            "REPORTS_PUBLICATIONS", "OTHER_COMPANY_INFORMATION", "UNRELATED", "AMBIGUOUS"
        }
        valid_candidate = {
            "CAREERS_LANDING_CANDIDATE", "JOBS_LISTING_CANDIDATE", "INDIVIDUAL_JOB_CANDIDATE",
            "JOB_APPLICATION_CANDIDATE", "HR_INFORMATION_CANDIDATE", "CSR_OVERVIEW_CANDIDATE",
            "CSR_PROJECT_DISCLOSURE_CANDIDATE", "CSR_PARTNERSHIP_RFP_CANDIDATE",
            "SUSTAINABILITY_REPORT_CANDIDATE", "ANNUAL_REPORT_CANDIDATE",
            "CSR_REPORT_CANDIDATE", "UNKNOWN_REQUIRES_REVIEW"
        }

        if not isinstance(data, list):
            if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
                data = data["results"]
            else:
                logger.warning("Stage 1 AI response was not a list. Received: %s", type(data))
                data = []

        res_map = {item.get("url"): item for item in data if isinstance(item, dict) and item.get("url")}
        validated = []

        for l in links:
            u = l.get("url")
            c = res_map.get(u, {})

            broad = c.get("broad_category")
            if broad not in valid_broad:
                broad = "OTHER_COMPANY_INFORMATION"

            candidate = c.get("candidate_category")
            if candidate not in valid_candidate:
                candidate = "UNKNOWN_REQUIRES_REVIEW"

            try:
                conf = float(c.get("confidence", 0.5))
                conf = max(0.0, min(1.0, conf))
            except (ValueError, TypeError):
                conf = 0.5

            reasoning = str(c.get("reasoning", "") or "Classified by OpenRouter").strip()

            validated.append({
                "url": u,
                "text": l.get("text", ""),
                "location": l.get("location", "BODY_CONTENT"),
                "broad_category": broad,
                "candidate_category": candidate,
                "confidence": conf,
                "reasoning": reasoning,
                "actual_model": actual_model
            })

        return validated

    def _validate_stage2_schema(self, data: Any, company_name: str, url: str, actual_model: str) -> Dict[str, Any]:
        """
        Validates Stage 2 output against the required schema.
        Ensures valid page_type, confidence range, evidence fields, and records actual model.
        """
        valid_page_types = {
            "CAREERS_LANDING_PAGE", "JOBS_LISTING_PAGE", "INDIVIDUAL_JOB_PAGE",
            "JOB_APPLICATION_PAGE", "HR_INFORMATION_PAGE", "CSR_OVERVIEW_PAGE",
            "CSR_PROJECT_DISCLOSURE", "CSR_PARTNERSHIP_OR_RFP", "SUSTAINABILITY_OR_ESG_REPORT",
            "ANNUAL_REPORT_WITH_CSR_EVIDENCE", "CSR_REPORT", "UNRELATED_PAGE",
            "INACCESSIBLE_PAGE", "UNKNOWN_REQUIRES_REVIEW"
        }

        if not isinstance(data, dict):
            logger.warning("Stage 2 AI response was not a dict. Received: %s", type(data))
            data = {}

        page_type = data.get("page_type")
        if page_type not in valid_page_types:
            page_type = "UNKNOWN_REQUIRES_REVIEW"

        try:
            conf = float(data.get("confidence", 0.40))
            conf = max(0.0, min(1.0, conf))
        except (ValueError, TypeError):
            conf = 0.40

        supporting = data.get("supporting_evidence", [])
        if not isinstance(supporting, list):
            supporting = [str(supporting)] if supporting else []

        contradictory = data.get("contradictory_evidence", [])
        if not isinstance(contradictory, list):
            contradictory = [str(contradictory)] if contradictory else []

        review_status = data.get("review_status", "REVIEW_REQUIRED")
        if review_status not in ("APPROVED", "REVIEW_REQUIRED", "REJECTED"):
            review_status = "REVIEW_REQUIRED"

        reasoning = str(data.get("reasoning", "") or "Evaluated by OpenRouter").strip()

        return {
            "company_name": company_name,
            "url": url,
            "page_type": page_type,
            "confidence": conf,
            "is_company_match": bool(data.get("is_company_match", True)),
            "supporting_evidence": supporting,
            "contradictory_evidence": contradictory,
            "review_status": review_status,
            "reasoning": reasoning,
            "actual_model": actual_model
        }

    def classify_links_batch(self, company_name: str, domain: str, links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not links:
            return []

        cache_key = self._build_cache_key("stage1_links", {"company": company_name, "links": links})
        prov = getattr(self, "provider_name", cfg.AI_PROVIDER)
        if self.cache:
            cached = self.cache.get(
                cache_key,
                cfg.CACHE_EXPIRATION_HOURS,
                expected_provider=prov,
                expected_model=self.model,
                allow_fallback=False
            )
            if cached and isinstance(cached, list):
                self.metrics["cache_hits"] += 1
                return cached

        # Fallback if key missing or AI disabled
        if not self.api_key or not cfg.AI_CLASSIFICATION_ENABLED:
            return self._fallback_classify_links(company_name, links)

        prompt = f"""You are an enterprise link classifier for official Indian company websites.
Target Company: {company_name} (domain: {domain})

Classify each link in the provided JSON array into:
1. broad_category: MUST be one of:
   - CAREERS_RECRUITMENT
   - CSR_SOCIAL_IMPACT
   - SUSTAINABILITY_ESG
   - REPORTS_PUBLICATIONS
   - OTHER_COMPANY_INFORMATION
   - UNRELATED
   - AMBIGUOUS

2. candidate_category: MUST be one of:
   - CAREERS_LANDING_CANDIDATE
   - JOBS_LISTING_CANDIDATE
   - INDIVIDUAL_JOB_CANDIDATE
   - JOB_APPLICATION_CANDIDATE
   - HR_INFORMATION_CANDIDATE
   - CSR_OVERVIEW_CANDIDATE
   - CSR_PROJECT_DISCLOSURE_CANDIDATE
   - CSR_PARTNERSHIP_RFP_CANDIDATE
   - SUSTAINABILITY_REPORT_CANDIDATE
   - ANNUAL_REPORT_CANDIDATE
   - CSR_REPORT_CANDIDATE
   - UNKNOWN_REQUIRES_REVIEW

3. confidence: float between 0.0 and 1.0.
4. reasoning: brief 1-sentence explanation based on link text and URL path.

Input Links:
{json.dumps(links, indent=1)}

Output strictly valid JSON with format:
[
  {{
    "url": "<link url>",
    "broad_category": "<broad>",
    "candidate_category": "<candidate>",
    "confidence": 0.85,
    "reasoning": "..."
  }}
]
"""
        try:
            raw_response, actual_model = self._execute_provider_request(prompt)
            validated = self._validate_stage1_schema(raw_response, links, actual_model)
            if self.cache:
                self.cache.set(cache_key, actual_model, "stage1_links", validated, provider=prov)
            return validated
        except QuotaExhaustedError:
            raise
        except Exception as e:
            err_msg = str(e)
            logger.warning("AI link batch classification failed: %s. Using rule-based fallback.", err_msg)
            self.metrics["errors_count"] += 1
            self.metrics["last_error"] = err_msg
            return self._fallback_classify_links(company_name, links, error=err_msg)

    def classify_page_content(self, company_name: str, url: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
        cache_key = self._build_cache_key("stage2_page", {"company": company_name, "url": url, "hash": page_data.get("content_hash")})
        prov = getattr(self, "provider_name", cfg.AI_PROVIDER)
        if self.cache:
            cached = self.cache.get(
                cache_key,
                cfg.CACHE_EXPIRATION_HOURS,
                expected_provider=prov,
                expected_model=self.model,
                allow_fallback=False
            )
            if cached and isinstance(cached, dict):
                self.metrics["cache_hits"] += 1
                return cached

        if not self.api_key or not cfg.AI_CLASSIFICATION_ENABLED:
            return self._fallback_classify_page(company_name, url, page_data)

        title = page_data.get("title", "")
        headings = page_data.get("headings", [])[:6]
        snippet = (page_data.get("main_text", "") or "")[:cfg.MAX_INPUT_CHARS]
        ats_platform = page_data.get("ats_platform")
        job_indicators = page_data.get("job_indicators", {})
        csr_indicators = page_data.get("csr_indicators", {})

        prompt = f"""You are an enterprise page classifier for official Indian corporate websites.
Target Company: {company_name}
Target URL: {url}

Page Metadata:
- Title: {title}
- Headings: {json.dumps(headings)}
- ATS Platform Detected: {ats_platform or 'None'}
- Job Vacancy Count Signals: {job_indicators.get('job_card_count', 0)}
- CSR Section 135 Signals: {csr_indicators.get('statutory_terms_found', False)}

Main Content Excerpt:
{snippet}

Classify the destination page into EXACTLY ONE page_type:
- CAREERS_LANDING_PAGE (corporate culture, employer branding, general career overview)
- JOBS_LISTING_PAGE (searchable database or listing of active job vacancies)
- INDIVIDUAL_JOB_PAGE (specific individual job opening with duties and apply button)
- JOB_APPLICATION_PAGE (actual candidate application submission form)
- HR_INFORMATION_PAGE (benefits, policies, employee login portal)
- CSR_OVERVIEW_PAGE (corporate social responsibility policy, vision, themes)
- CSR_PROJECT_DISCLOSURE (specific projects with budget, location, implementing partner)
- CSR_PARTNERSHIP_OR_RFP (open call for proposals, grants, NGO partner invitation)
- SUSTAINABILITY_OR_ESG_REPORT (ESG overview or sustainability report)
- ANNUAL_REPORT_WITH_CSR_EVIDENCE (annual statutory report containing CSR disclosures)
- CSR_REPORT (standalone annual CSR report)
- UNRELATED_PAGE (commercial product, consumer banking/loan application, blog, marketing promo)
- INACCESSIBLE_PAGE (HTTP 404, forbidden, login wall)
- UNKNOWN_REQUIRES_REVIEW (insufficient information)

Output strictly valid JSON with format:
{{
  "company_name": "{company_name}",
  "url": "{url}",
  "page_type": "<TYPE>",
  "confidence": 0.90,
  "is_company_match": true,
  "supporting_evidence": ["item 1", "item 2"],
  "contradictory_evidence": [],
  "review_status": "APPROVED" | "REVIEW_REQUIRED" | "REJECTED",
  "reasoning": "..."
}}
"""
        try:
            raw_response, actual_model = self._execute_provider_request(prompt)
            validated = self._validate_stage2_schema(raw_response, company_name, url, actual_model)
            if self.cache:
                self.cache.set(cache_key, actual_model, "stage2_page", validated, provider=prov)
            return validated
        except QuotaExhaustedError:
            raise
        except Exception as e:
            err_msg = str(e)
            logger.warning("AI page classification failed: %s. Using rule-based fallback.", err_msg)
            self.metrics["errors_count"] += 1
            self.metrics["last_error"] = err_msg
            return self._fallback_classify_page(company_name, url, page_data, error=err_msg)

    def _fallback_classify_links(self, company_name: str, links: List[Dict[str, Any]], error: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for l in links:
            url = l.get("url", "")
            text = (l.get("text", "") or "").lower().strip()
            url_lower = url.lower()

            broad = "OTHER_COMPANY_INFORMATION"
            cand = "UNKNOWN_REQUIRES_REVIEW"
            conf = 0.50
            reason = "Pattern heuristic match"

            # 1. Careers patterns
            if any(k in text for k in ["career", "careers", "jobs", "work with us", "join us", "openings", "vacancies", "join our team", "explore opportunities", "current openings", "apply"]) or any(k in url_lower for k in ["/career", "/careers", "/jobs", "greenhouse.io", "lever.co", "smartrecruiters.com", "myworkdayjobs.com", "darwinbox.in", "successfactors"]):
                broad = "CAREERS_RECRUITMENT"
                if any(ats in url_lower for ats in ["greenhouse.io", "lever.co", "smartrecruiters.com", "myworkdayjobs", "jobs."]) or "current-openings" in url_lower or "search-jobs" in url_lower:
                    cand = "JOBS_LISTING_CANDIDATE"
                    conf = 0.90
                    reason = "Direct ATS domain or active openings URL"
                elif any(k in text for k in ["apply now", "view jobs", "current openings", "search jobs"]):
                    cand = "JOBS_LISTING_CANDIDATE"
                    conf = 0.85
                    reason = "Action link text for jobs listing"
                else:
                    cand = "CAREERS_LANDING_CANDIDATE"
                    conf = 0.80
                    reason = "General careers portal navigation link"

            # 2. CSR patterns
            elif any(k in text for k in ["csr", "social responsibility", "sustainability", "esg", "foundation", "community", "social impact", "giving back", "responsible business", "brsr"]) or any(k in url_lower for k in ["/csr", "/sustainability", "/esg", "/foundation"]):
                if any(k in text for k in ["sustainability", "esg", "brsr"]):
                    broad = "SUSTAINABILITY_ESG"
                    cand = "SUSTAINABILITY_REPORT_CANDIDATE" if "report" in text or ".pdf" in url_lower else "CSR_OVERVIEW_CANDIDATE"
                    conf = 0.80
                elif any(k in text for k in ["partner with us", "grant", "rfp", "proposal"]):
                    broad = "CSR_SOCIAL_IMPACT"
                    cand = "CSR_PARTNERSHIP_RFP_CANDIDATE"
                    conf = 0.85
                elif "report" in text or ".pdf" in url_lower or "annual report" in text:
                    broad = "REPORTS_PUBLICATIONS"
                    cand = "CSR_REPORT_CANDIDATE"
                    conf = 0.85
                else:
                    broad = "CSR_SOCIAL_IMPACT"
                    cand = "CSR_OVERVIEW_CANDIDATE"
                    conf = 0.85
                reason = "Corporate social responsibility / sustainability text match"

            # 3. Customer-facing false positives
            elif any(k in text for k in ["customer", "loan", "credit", "card", "calculator", "branch locator", "faq", "terms", "privacy", "investor", "shareholder"]):
                broad = "UNRELATED"
                cand = "UNKNOWN_REQUIRES_REVIEW"
                conf = 0.85
                reason = "Non-recruitment / customer service link"

            results.append({
                "url": url,
                "text": l.get("text", ""),
                "location": l.get("location", "BODY_CONTENT"),
                "broad_category": broad,
                "candidate_category": cand,
                "confidence": min(conf, 0.50),
                "reasoning": f"{reason} (Fallback: AI not used)" + (f". Error: {error}" if error else ""),
                "actual_model": "rule_based_fallback",
                "error": error
            })
        return results

    def _fallback_classify_page(self, company_name: str, url: str, page_data: Dict[str, Any], error: Optional[str] = None) -> Dict[str, Any]:
        text = (page_data.get("main_text", "") or "").lower()
        title = (page_data.get("title", "") or "").lower()
        url_lower = url.lower()
        ats = page_data.get("ats_platform")
        status_code = page_data.get("status_code", 200)

        # Requirement 4: Deterministic fallback MUST NOT approve or verify a source.
        # Mark as PENDING_AI if an AI error occurred, otherwise REVIEW_REQUIRED.
        fallback_status = "PENDING_AI" if error else "REVIEW_REQUIRED"
        err_note = f" AI Error: {error}" if error else ""

        if status_code in (404, 410, 403, 500) or any(err in text for err in ["404 not found", "page not found"]):
            return {
                "company_name": company_name,
                "url": url,
                "page_type": "INACCESSIBLE_PAGE",
                "confidence": 0.95,
                "is_company_match": True,
                "supporting_evidence": ["HTTP status error or page not found marker"],
                "contradictory_evidence": [],
                "review_status": "REJECTED",
                "reasoning": "Page is inaccessible or returned 404" + err_note,
                "actual_model": "rule_based_fallback",
                "error": error
            }

        if any(term in text for term in ["personal loan", "home loan", "credit card", "apply for card", "savings account", "fixed deposit"]) and not any(ats_d in url_lower for ats_d in ["greenhouse.io", "lever.co", "smartrecruiters.com", "myworkdayjobs.com"]):
            return {
                "company_name": company_name,
                "url": url,
                "page_type": "UNRELATED_PAGE",
                "confidence": 0.90,
                "is_company_match": True,
                "supporting_evidence": ["Commercial banking / consumer financial products present"],
                "contradictory_evidence": ["No recruitment ATS signatures"],
                "review_status": "REJECTED",
                "reasoning": "Consumer financial application, not employee recruitment" + err_note,
                "actual_model": "rule_based_fallback",
                "error": error
            }

        if ats or any(k in url_lower for k in ["greenhouse.io", "lever.co", "smartrecruiters.com", "myworkdayjobs.com"]) or any(k in title for k in ["open positions", "job openings", "current vacancies", "search jobs"]) or page_data.get("job_indicators", {}).get("job_card_count", 0) > 0:
            return {
                "company_name": company_name,
                "url": url,
                "page_type": "JOBS_LISTING_PAGE",
                "confidence": 0.70,
                "is_company_match": True,
                "supporting_evidence": ["Pattern heuristic: ATS platform or active vacancy listings found"],
                "contradictory_evidence": ["Fallback heuristic classification only - live AI verification required"],
                "review_status": fallback_status,
                "reasoning": f"Pattern match for jobs listing. Fallback cannot approve without live AI verification.{err_note}",
                "actual_model": "rule_based_fallback",
                "error": error
            }

        if any(k in title for k in ["careers", "working at", "life at", "join us", "work with us"]) or "/careers" in url_lower:
            return {
                "company_name": company_name,
                "url": url,
                "page_type": "CAREERS_LANDING_PAGE",
                "confidence": 0.70,
                "is_company_match": True,
                "supporting_evidence": ["Pattern heuristic: Employer branding and career portal navigation"],
                "contradictory_evidence": ["Fallback heuristic classification only - live AI verification required"],
                "review_status": fallback_status,
                "reasoning": f"Pattern match for corporate careers. Fallback cannot approve without live AI verification.{err_note}",
                "actual_model": "rule_based_fallback",
                "error": error
            }

        if any(k in text for k in ["section 135", "schedule vii", "csr committee", "csr expenditure", "csr projects", "csr policy", "annual action plan"]):
            return {
                "company_name": company_name,
                "url": url,
                "page_type": "CSR_PROJECT_DISCLOSURE" if ("project" in text or "beneficiar" in text) else "CSR_OVERVIEW_PAGE",
                "confidence": 0.70,
                "is_company_match": True,
                "supporting_evidence": ["Pattern heuristic: Section 135 / Schedule VII statutory indicators found"],
                "contradictory_evidence": ["Fallback heuristic classification only - live AI verification required"],
                "review_status": fallback_status,
                "reasoning": f"Pattern match for CSR disclosure. Fallback cannot approve without live AI verification.{err_note}",
                "actual_model": "rule_based_fallback",
                "error": error
            }

        if any(k in title for k in ["sustainability", "esg", "foundation", "social responsibility"]):
            return {
                "company_name": company_name,
                "url": url,
                "page_type": "SUSTAINABILITY_OR_ESG_REPORT" if (".pdf" in url_lower or "report" in title) else "CSR_OVERVIEW_PAGE",
                "confidence": 0.70,
                "is_company_match": True,
                "supporting_evidence": ["Pattern heuristic: Sustainability / ESG themes present"],
                "contradictory_evidence": ["Fallback heuristic classification only - live AI verification required"],
                "review_status": fallback_status,
                "reasoning": f"Pattern match for sustainability. Fallback cannot approve without live AI verification.{err_note}",
                "actual_model": "rule_based_fallback",
                "error": error
            }

        return {
            "company_name": company_name,
            "url": url,
            "page_type": "UNKNOWN_REQUIRES_REVIEW",
            "confidence": 0.40,
            "is_company_match": True,
            "supporting_evidence": [],
            "contradictory_evidence": ["Ambiguous content signals"],
            "review_status": "REVIEW_REQUIRED",
            "reasoning": f"Content does not meet high-confidence threshold.{err_note}",
            "actual_model": "rule_based_fallback",
            "error": error
        }


    def get_metrics(self) -> Dict[str, Any]:
        return dict(self.metrics)


class OpenRouterApiClient(BaseAIClient):
    """
    Dedicated client for OpenRouter hosted AI API.
    Interacts via OpenAI-compatible HTTPS REST endpoints: https://openrouter.ai/api/v1/chat/completions
    Compatible with OpenRouter Free Models Router ("openrouter/free") and other free models.
    Captures the dynamically returned actual model from the OpenRouter response.
    """
    provider_name = "openrouter"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__()
        try:
            from modules.admin_panel.services.ai_config_service import get_active_ai_config
            _act = get_active_ai_config()
            db_or = _act.get("providers", {}).get("openrouter", {})
        except Exception:
            _act = {}
            db_or = {}

        self.model = (
            model
            or (_act.get("primary_model") if _act.get("primary_provider") == "openrouter" else None)
            or db_or.get("selected_model")
            or os.environ.get("OPENROUTER_MODEL", "").strip()
            or cfg.OPENROUTER_MODEL
        )
        self.api_key = (
            api_key
            or db_or.get("_api_key")
            or os.environ.get(cfg.OPENROUTER_API_KEY_ENV, "").strip()
            or os.environ.get("OPENROUTER_API_KEY", "").strip()
            or (self.api_key if getattr(cfg, "AI_PROVIDER", "gemini") == "openrouter" else "")
        )
        self.base_url = (base_url or db_or.get("base_url") or cfg.OPENROUTER_BASE_URL).rstrip('/')

    def _execute_provider_request(self, prompt: str) -> Tuple[Any, str]:
        if not self.api_key:
            raise AIClientError(f"OpenRouter API key not found in environment variable '{cfg.AI_API_KEY_ENV}'.")

        if self.metrics["api_calls_made"] >= self.max_api_calls:
            raise QuotaExhaustedError(
                f"Reached configured run limit of {self.max_api_calls} API calls. "
                "Pausing safely to protect quota."
            )

        endpoint = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": cfg.OPENROUTER_REFERER,
            "X-Title": cfg.OPENROUTER_TITLE,
            "Content-Type": "application/json"
        }

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an enterprise corporate website and source classification engine. You must output strictly valid JSON conforming to the requested schema. No conversational prose or introductory text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": cfg.MAX_OUTPUT_TOKENS,
        }

        delay = cfg.BACKOFF_DELAY
        for attempt in range(1, cfg.MAX_RETRIES + 1):
            try:
                self.metrics["api_calls_made"] += 1
                resp = requests.post(endpoint, json=body, headers=headers, timeout=cfg.REQUEST_TIMEOUT)

                if resp.status_code == 200:
                    data = resp.json()
                    actual_model = data.get("model") or self.model
                    self.metrics["models_used"][actual_model] = self.metrics["models_used"].get(actual_model, 0) + 1
                    
                    choices = data.get("choices", [])
                    if not choices:
                        raise AIClientError(f"OpenRouter returned empty choices: {data}")
                    msg = choices[0].get("message", {})
                    raw_text = msg.get("content")
                    if not raw_text:
                        raw_text = msg.get("reasoning") or ""
                    if not raw_text and "text" in choices[0]:
                        raw_text = choices[0].get("text") or ""
                    raw_text = str(raw_text or "").strip()
                    parsed_json = self._clean_json_text(raw_text)
                    return parsed_json, actual_model

                elif resp.status_code in (429, 402):
                    self.metrics["quota_warnings"] += 1
                    self.metrics["quota_exhausted"] = True
                    err_msg = f"OpenRouter quota/rate limit exhausted (HTTP {resp.status_code}): {resp.text}"
                    logger.error(err_msg)
                    raise QuotaExhaustedError(err_msg)

                elif resp.status_code in (500, 502, 503, 504):
                    self.metrics["retries_count"] += 1
                    logger.warning("OpenRouter transient error HTTP %d (attempt %d/%d). Retrying in %.1fs...", resp.status_code, attempt, cfg.MAX_RETRIES, delay)
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    self.metrics["errors_count"] += 1
                    raise AIClientError(f"OpenRouter API returned HTTP {resp.status_code}: {resp.text}")

            except requests.exceptions.Timeout:
                self.metrics["retries_count"] += 1
                if attempt == cfg.MAX_RETRIES:
                    raise AIClientError("OpenRouter API request timed out after multiple retries.")
                time.sleep(delay)
                delay *= 2
            except requests.exceptions.RequestException as e:
                self.metrics["errors_count"] += 1
                raise AIClientError(f"OpenRouter network error: {str(e)}")

        raise AIClientError("Failed to obtain response from OpenRouter API after max retries.")


class OpenAICompatibleApiClient(BaseAIClient):
    """
    Universal client for OpenAI-compatible REST API endpoints:
    Supports OpenAI, Groq, Mistral, DeepSeek, Ollama, Together AI, Perplexity, vLLM, LM Studio, etc.
    Endpoint: {base_url}/chat/completions
    Payload: {"model": model, "messages": [...], "temperature": 0.0}
    """
    def __init__(
        self,
        provider_name: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        super().__init__()
        self.provider_name = (provider_name or "openai").lower().strip()
        try:
            from modules.admin_panel.services.ai_config_service import get_active_ai_config
            _act = get_active_ai_config()
            db_p = _act.get("providers", {}).get(self.provider_name, {})
        except Exception:
            _act = {}
            db_p = {}

        default_base_urls = {
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "mistral": "https://api.mistral.ai/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "ollama": "http://localhost:11434/v1",
            "together": "https://api.together.xyz/v1",
            "fireworks": "https://api.fireworks.ai/inference/v1",
            "perplexity": "https://api.perplexity.ai",
        }

        default_models = {
            "openai": "gpt-4o-mini",
            "groq": "llama-3.3-70b-versatile",
            "mistral": "mistral-small-latest",
            "deepseek": "deepseek-chat",
            "ollama": "llama3:latest",
            "together": "meta-llama/Llama-3-70b-chat-hf",
            "fireworks": "accounts/fireworks/models/llama-v3-70b-instruct",
            "perplexity": "llama-3.1-sonar-small-128k-online",
        }

        self.model = (
            model
            or (_act.get("primary_model") if _act.get("primary_provider") == self.provider_name else None)
            or db_p.get("selected_model")
            or default_models.get(self.provider_name, "default")
        )
        self.api_key = (
            api_key
            or db_p.get("_api_key")
            or os.environ.get(f"{self.provider_name.upper()}_API_KEY", "").strip()
            or ("ollama" if self.provider_name in ("ollama", "local") else "")
        )
        self.base_url = (
            base_url
            or db_p.get("base_url")
            or default_base_urls.get(self.provider_name, "https://api.openai.com/v1")
        ).rstrip('/')

    def _execute_provider_request(self, prompt: str) -> Tuple[Any, str]:
        if not self.api_key and self.provider_name not in ("ollama", "local"):
            raise AIClientError(f"{self.provider_name.upper()} API key not configured.")

        if self.metrics["api_calls_made"] >= self.max_api_calls:
            raise QuotaExhaustedError(
                f"Reached configured run limit of {self.max_api_calls} API calls. Pausing safely."
            )

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an enterprise corporate website and source classification engine. You must output strictly valid JSON conforming to the requested schema. No conversational prose or introductory text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.0,
            "max_tokens": 1200
        }

        delay = 1.0
        for attempt in range(1, cfg.MAX_RETRIES + 1):
            try:
                self.metrics["api_calls_made"] += 1
                resp = requests.post(endpoint, json=body, headers=headers, timeout=cfg.REQUEST_TIMEOUT)

                if resp.status_code == 200:
                    data = resp.json()
                    content = ""
                    choices = data.get("choices", [])
                    if choices and isinstance(choices, list):
                        msg = choices[0].get("message", {})
                        content = msg.get("content", "")

                    actual_model = data.get("model", self.model)
                    parsed_json = self._extract_json_payload(content)
                    return parsed_json, actual_model

                elif resp.status_code in (429, 402):
                    self.metrics["quota_warnings"] += 1
                    self.metrics["quota_exhausted"] = True
                    err_msg = f"{self.provider_name.upper()} quota/rate limit exhausted (HTTP {resp.status_code}): {resp.text}"
                    logger.error(err_msg)
                    raise QuotaExhaustedError(err_msg)

                elif resp.status_code in (500, 502, 503, 504):
                    self.metrics["retries_count"] += 1
                    logger.warning("%s transient error HTTP %d (attempt %d/%d). Retrying...", self.provider_name.upper(), resp.status_code, attempt, cfg.MAX_RETRIES)
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    self.metrics["errors_count"] += 1
                    raise AIClientError(f"{self.provider_name.upper()} API returned HTTP {resp.status_code}: {resp.text}")

            except requests.exceptions.Timeout:
                self.metrics["retries_count"] += 1
                if attempt == cfg.MAX_RETRIES:
                    raise AIClientError(f"{self.provider_name.upper()} API request timed out after multiple retries.")
                time.sleep(delay)
                delay *= 2
            except requests.exceptions.RequestException as e:
                self.metrics["errors_count"] += 1
                raise AIClientError(f"{self.provider_name.upper()} network error: {str(e)}")

        raise AIClientError(f"Failed to obtain response from {self.provider_name.upper()} API after max retries.")


class AnthropicApiClient(BaseAIClient):
    """
    Dedicated client for Anthropic Claude API (https://api.anthropic.com/v1/messages).
    Uses official Anthropic Messages format and schema.
    """
    provider_name = "anthropic"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__()
        try:
            from modules.admin_panel.services.ai_config_service import get_active_ai_config
            _act = get_active_ai_config()
            db_p = _act.get("providers", {}).get("anthropic", {})
        except Exception:
            _act = {}
            db_p = {}

        self.model = (
            model
            or (_act.get("primary_model") if _act.get("primary_provider") == "anthropic" else None)
            or db_p.get("selected_model")
            or os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest").strip()
        )
        self.api_key = (
            api_key
            or db_p.get("_api_key")
            or os.environ.get("ANTHROPIC_API_KEY", "").strip()
        )
        self.base_url = (base_url or db_p.get("base_url") or "https://api.anthropic.com/v1").rstrip('/')

    def _execute_provider_request(self, prompt: str) -> Tuple[Any, str]:
        if not self.api_key:
            raise AIClientError("Anthropic API key not configured.")

        if self.metrics["api_calls_made"] >= self.max_api_calls:
            raise QuotaExhaustedError(
                f"Reached configured run limit of {self.max_api_calls} API calls."
            )

        endpoint = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        body: Dict[str, Any] = {
            "model": self.model,
            "max_tokens": 1200,
            "system": "You are an enterprise corporate website and source classification engine. You must output strictly valid JSON conforming to the requested schema. No conversational prose or introductory text.",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        delay = 1.0
        for attempt in range(1, cfg.MAX_RETRIES + 1):
            try:
                self.metrics["api_calls_made"] += 1
                resp = requests.post(endpoint, json=body, headers=headers, timeout=cfg.REQUEST_TIMEOUT)

                if resp.status_code == 200:
                    data = resp.json()
                    content = ""
                    for block in data.get("content", []):
                        if block.get("type") == "text":
                            content += block.get("text", "")

                    actual_model = data.get("model", self.model)
                    parsed_json = self._extract_json_payload(content)
                    return parsed_json, actual_model

                elif resp.status_code in (429, 529):
                    self.metrics["quota_warnings"] += 1
                    self.metrics["quota_exhausted"] = True
                    raise QuotaExhaustedError(f"Anthropic quota or rate limit exceeded: {resp.text}")
                elif resp.status_code in (500, 502, 503, 504):
                    self.metrics["retries_count"] += 1
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    self.metrics["errors_count"] += 1
                    raise AIClientError(f"Anthropic API returned HTTP {resp.status_code}: {resp.text}")

            except requests.exceptions.Timeout:
                self.metrics["retries_count"] += 1
                if attempt == cfg.MAX_RETRIES:
                    raise AIClientError("Anthropic API request timed out.")
                time.sleep(delay)
                delay *= 2
            except requests.exceptions.RequestException as e:
                self.metrics["errors_count"] += 1
                raise AIClientError(f"Anthropic network error: {str(e)}")

        raise AIClientError("Failed to obtain response from Anthropic API after max retries.")



class GeminiApiClient(BaseAIClient):
    """
    Dedicated client for Google Gemini hosted AI API.
    Interacts via Google's official Interactions API (https://generativelanguage.googleapis.com/v1beta/interactions)
    for model inference, structured JSON output validation, and state tracking.
    Enforces official API free-tier models and zero-cost operation.
    """
    provider_name = "gemini"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__()
        try:
            from modules.admin_panel.services.ai_config_service import get_active_ai_config
            _act = get_active_ai_config()
            db_gemini = _act.get("providers", {}).get("gemini", {})
        except Exception:
            _act = {}
            db_gemini = {}

        self.model = (
            model
            or (_act.get("primary_model") if _act.get("primary_provider") == "gemini" else None)
            or db_gemini.get("selected_model")
            or os.environ.get("GEMINI_MODEL", "").strip()
            or cfg.GEMINI_MODEL
        )
        self.api_key = (
            api_key
            or db_gemini.get("_api_key")
            or os.environ.get(cfg.GEMINI_API_KEY_ENV, "").strip()
            or os.environ.get("GEMINI_API_KEY", "").strip()
            or (self.api_key if getattr(cfg, "AI_PROVIDER", "gemini") == "gemini" else "")
        )
        self.base_url = (base_url or db_gemini.get("base_url") or cfg.GEMINI_BASE_URL).rstrip('/')

    def verify_free_tier_eligibility(self) -> Tuple[bool, str]:
        """
        Tests Gemini provider configuration without making any billable API calls.
        Uses non-billable GET metadata endpoint to verify API key and model availability.
        """
        if not self.api_key:
            return False, f"Gemini API key not found in environment variable '{cfg.GEMINI_API_KEY_ENV}'."

        if not cfg.is_gemini_free_tier_model(self.model):
            return False, (
                f"Model '{self.model}' is not in the confirmed official API free tier "
                f"({cfg.GEMINI_FREE_TIER_MODELS}). Paid models violate the zero-cost policy."
            )

        endpoint = f"{self.base_url}/models/{self.model}?key={self.api_key}"
        try:
            resp = requests.get(endpoint, timeout=cfg.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return True, f"Gemini API key is verified and free-tier model '{self.model}' is accessible (0 billable cost)."
            elif resp.status_code == 429:
                return False, f"Gemini free-tier quota is currently exhausted (HTTP 429)."
            elif resp.status_code in (400, 403):
                return False, f"Gemini API authentication rejected key (HTTP {resp.status_code}): {resp.text}"
            else:
                return False, f"Gemini API returned HTTP {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, f"Gemini connection probe failed: {str(e)}"

    def _execute_provider_request(self, prompt: str) -> Tuple[Any, str]:
        return self._execute_gemini_request(prompt)

    def _execute_gemini_request(self, prompt: str, schema: Optional[Dict[str, Any]] = None) -> Tuple[Any, str]:
        # Enforce official free tier models only (Requirement 1 & 5)
        if not cfg.is_gemini_free_tier_model(self.model):
            raise ZeroCostPolicyViolationError(
                f"Configured Gemini model '{self.model}' is not in the confirmed official API free tier "
                f"({cfg.GEMINI_FREE_TIER_MODELS}). Paid models violate the strict zero-cost requirement."
            )

        if not self.api_key:
            raise AIClientError(f"API key not found in environment variable '{cfg.GEMINI_API_KEY_ENV}'.")

        if self.metrics["api_calls_made"] >= cfg.MAX_API_CALLS_PER_RUN:
            raise QuotaExhaustedError(f"Reached configured run limit of {cfg.MAX_API_CALLS_PER_RUN} API calls.")

        # Google Gemini Interactions API endpoint
        endpoint = f"{self.base_url}/interactions?key={self.api_key}"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }

        body: Dict[str, Any] = {
            "model": self.model,
            "input": prompt,
            "response_format": {
                "type": "text",
                "mime_type": "application/json"
            }
        }

        delay = cfg.BACKOFF_DELAY
        for attempt in range(1, cfg.MAX_RETRIES + 1):
            try:
                self.metrics["api_calls_made"] += 1
                resp = requests.post(endpoint, json=body, headers=headers, timeout=cfg.REQUEST_TIMEOUT)

                if resp.status_code == 200:
                    data = resp.json()
                    actual_model = data.get("model") or self.model
                    raw_text = ""

                    # Interactions API: step-based response
                    for step in data.get("steps", []):
                        if step.get("type") == "model_output":
                            for part in step.get("content", []):
                                if isinstance(part, dict) and "text" in part:
                                    raw_text += part["text"]
                                elif isinstance(part, str):
                                    raw_text += part

                    # Legacy candidates fallback
                    if not raw_text and "candidates" in data:
                        candidates = data.get("candidates", [])
                        if candidates:
                            text_parts = candidates[0].get("content", {}).get("parts", [])
                            if text_parts:
                                raw_text = text_parts[0].get("text", "").strip()

                    if not raw_text:
                        raise AIClientError(f"Gemini Interactions API returned empty output text. Status: {data.get('status')}")

                    self.metrics["models_used"][actual_model] = self.metrics["models_used"].get(actual_model, 0) + 1
                    cleaned = self._clean_json_text(raw_text)
                    return cleaned, actual_model

                elif resp.status_code in (429, 402):
                    self.metrics["quota_warnings"] += 1
                    self.metrics["quota_exhausted"] = True
                    err_msg = f"Gemini quota exhausted (HTTP {resp.status_code}): {resp.text}"
                    logger.error(err_msg)
                    raise QuotaExhaustedError(err_msg)

                elif resp.status_code in (500, 502, 503, 504):
                    self.metrics["retries_count"] += 1
                    logger.warning(
                        "Gemini transient server error HTTP %d (attempt %d/%d). Retrying in %.1fs...",
                        resp.status_code, attempt, cfg.MAX_RETRIES, delay
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    self.metrics["errors_count"] += 1
                    raise AIClientError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")

            except requests.exceptions.Timeout:
                self.metrics["retries_count"] += 1
                if attempt == cfg.MAX_RETRIES:
                    raise AIClientError("Gemini API request timed out after multiple retries.")
                time.sleep(delay)
                delay *= 2
            except requests.exceptions.RequestException as e:
                self.metrics["errors_count"] += 1
                raise AIClientError(f"Gemini network error: {str(e)}")

        raise AIClientError("Failed to obtain response from Gemini API after max retries.")



class GrokApiClient(BaseAIClient):
    """
    Dedicated client for xAI Grok API, configured strictly as a zero-cost fallback.
    Interacts via OpenAI-compatible HTTPS REST endpoints: https://api.x.ai/v1/chat/completions.

    Strict Zero-Cost Safeguards:
    1. NEVER assumes a free Grok web/app account provides free API usage.
    2. Enforces GROK_ZERO_COST_ONLY=True at all times.
    3. Blocks any outgoing request unless xAI account has confirmed, usable, non-billable
       promotional/grant credits (GROK_FREE_CREDITS_CONFIRMED=True).
    4. If free API access cannot be verified, disables Grok calls and does NOT send billable requests.
    5. Never automatically activates billing, purchases credits, or switches to paid models.
    """
    provider_name = "grok"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__()
        try:
            from modules.admin_panel.services.ai_config_service import get_active_ai_config
            _act = get_active_ai_config()
            db_grok = _act.get("providers", {}).get("grok", {})
        except Exception:
            _act = {}
            db_grok = {}

        self.model = (
            model
            or (_act.get("fallback_model") if _act.get("fallback_provider") == "grok" else None)
            or db_grok.get("selected_model")
            or os.environ.get("GROK_MODEL", "").strip()
            or cfg.GROK_MODEL
        )
        self.api_key = (
            api_key
            or db_grok.get("_api_key")
            or os.environ.get(cfg.GROK_API_KEY_ENV, "").strip()
            or os.environ.get("GROK_API_KEY", "").strip()
            or os.environ.get("XAI_API_KEY", "").strip()
            or (self.api_key if getattr(cfg, "AI_PROVIDER", "gemini") == "grok" else "")
        )
        self.base_url = (base_url or db_grok.get("base_url") or cfg.GROK_BASE_URL).rstrip('/')
        self.zero_cost_only = cfg.GROK_ZERO_COST_ONLY

    def verify_zero_cost_eligibility(self) -> Tuple[bool, str]:
        """
        Enforces and tests the strict zero-cost policy for Grok/xAI before every request.
        Guarantees zero billable calls are made.
        """
        # 1. API key check
        if not self.api_key:
            return False, (
                f"xAI API key not found in environment variable '{cfg.GROK_API_KEY_ENV}' "
                "(or 'XAI_API_KEY'). Grok fallback is unavailable."
            )

        # 2. Web/app account disclaimer and confirmed credits check
        # Requirement 3: Never assume a free Grok web/app account provides free API usage!
        if not cfg.GROK_FREE_CREDITS_CONFIRMED:
            return False, (
                "Zero-cost policy enforced: Free Grok web/app accounts do NOT provide free API usage. "
                "xAI developer API requires confirmed, non-billable promotional/grant credits to operate at zero cost. "
                "GROK_FREE_CREDITS_CONFIRMED is currently False. All billable requests are strictly blocked."
            )

        # 3. Non-billable verification of API key using metadata endpoints (GET /api-key or /models)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        try:
            # Metadata probe (0 tokens generated, 0 inference cost)
            resp = requests.get(f"{self.base_url}/api-key", headers=headers, timeout=cfg.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return True, "xAI API key verified and zero-cost promotional/grant credits confirmed."
            # Fallback probe to /models if /api-key is unsupported
            resp = requests.get(f"{self.base_url}/models", headers=headers, timeout=cfg.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return True, "xAI API key verified and zero-cost promotional/grant credits confirmed."
            elif resp.status_code in (401, 403):
                return False, f"xAI API authentication rejected key (HTTP {resp.status_code}): {resp.text}"
            elif resp.status_code == 429:
                return False, f"xAI API rate limit or credit limit reached (HTTP 429): {resp.text}"
            else:
                return False, f"xAI API returned HTTP {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, f"xAI connection probe failed: {str(e)}"

    def _execute_provider_request(self, prompt: str) -> Tuple[Any, str]:
        # Enforce zero-cost policy before EVERY Grok request (Requirements 2, 4, 5)
        eligible, reason = self.verify_zero_cost_eligibility()
        if not eligible:
            logger.error("Zero-cost policy blocked Grok request: %s", reason)
            raise ZeroCostPolicyViolationError(
                f"Grok request blocked by zero-cost policy: {reason}. "
                "Zero-cost restriction takes priority over automatic fallback."
            )

        if self.metrics["api_calls_made"] >= self.max_api_calls:
            raise QuotaExhaustedError(
                f"Reached configured run limit of {self.max_api_calls} API calls. "
                "Pausing safely to protect quota."
            )

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an enterprise corporate website and source classification engine. "
                        "You must output strictly valid JSON conforming to the requested schema. "
                        "No conversational prose or introductory text."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,
            "max_tokens": cfg.MAX_OUTPUT_TOKENS,
        }

        delay = cfg.BACKOFF_DELAY
        for attempt in range(1, cfg.MAX_RETRIES + 1):
            try:
                self.metrics["api_calls_made"] += 1
                resp = requests.post(endpoint, json=body, headers=headers, timeout=cfg.REQUEST_TIMEOUT)

                if resp.status_code == 200:
                    data = resp.json()
                    actual_model = data.get("model") or self.model
                    self.metrics["models_used"][actual_model] = self.metrics["models_used"].get(actual_model, 0) + 1

                    choices = data.get("choices", [])
                    if not choices:
                        raise AIClientError(f"Grok returned empty choices: {data}")
                    msg = choices[0].get("message", {})
                    raw_text = msg.get("content") or ""
                    parsed_json = self._clean_json_text(raw_text)
                    return parsed_json, actual_model

                elif resp.status_code in (429, 402):
                    self.metrics["quota_warnings"] += 1
                    self.metrics["quota_exhausted"] = True
                    err_msg = f"Grok quota/credits exhausted (HTTP {resp.status_code}): {resp.text}"
                    logger.error(err_msg)
                    raise QuotaExhaustedError(err_msg)

                elif resp.status_code in (500, 502, 503, 504):
                    self.metrics["retries_count"] += 1
                    logger.warning(
                        "Grok transient error HTTP %d (attempt %d/%d). Retrying in %.1fs...",
                        resp.status_code, attempt, cfg.MAX_RETRIES, delay
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                else:
                    self.metrics["errors_count"] += 1
                    raise AIClientError(f"Grok API returned HTTP {resp.status_code}: {resp.text}")

            except requests.exceptions.Timeout:
                self.metrics["retries_count"] += 1
                if attempt == cfg.MAX_RETRIES:
                    raise AIClientError("Grok API request timed out after multiple retries.")
                time.sleep(delay)
                delay *= 2
            except requests.exceptions.RequestException as e:
                self.metrics["errors_count"] += 1
                raise AIClientError(f"Grok network error: {str(e)}")

        raise AIClientError("Failed to obtain response from Grok API after max retries.")


class PrimaryFallbackAIClient(AIClient):
    """
    Orchestrates Primary classification via Gemini (official free tier) and zero-cost fallback via Grok (xAI).
    
    Zero-Cost Guarantees:
    - Primary uses only official free-tier Gemini models.
    - Fallback engages only if Grok has confirmed, non-billable zero-cost promotional/grant credits.
    - If Gemini hits quota and Grok cannot be used for free, pauses AI classification safely,
      saves checkpoints, and keeps uncertain candidates marked PENDING_AI or REVIEW_REQUIRED.
    - NEVER automatically activates billing or switches to paid models.
    """

    def __init__(
        self,
        primary: Optional[AIClient] = None,
        fallback: Optional[AIClient] = None
    ):
        self.primary = primary or GeminiApiClient()
        self.fallback = fallback or GrokApiClient()
        self.fallback_enabled = cfg.AI_FALLBACK_ENABLED
        self.metrics = {
            "fallback_invocations": 0,
            "fallback_blocked_zero_cost": 0,
        }

    @property
    def provider_name(self) -> str:
        return getattr(self.primary, "provider_name", "gemini")

    @property
    def provider(self) -> str:
        return getattr(self.primary, "provider", getattr(self.primary, "provider_name", "gemini"))

    @property
    def model_name(self) -> str:
        return getattr(self.primary, "model_name", getattr(self.primary, "model", cfg.AI_MODEL))

    @property
    def model(self) -> str:
        return getattr(self.primary, "model", getattr(self.primary, "model_name", cfg.AI_MODEL))

    def classify_links_batch(self, company_name: str, domain: str, links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        try:
            return self.primary.classify_links_batch(company_name, domain, links)
        except QuotaExhaustedError as qe:
            logger.warning("Primary provider quota exhausted: %s", qe)
            if not self.fallback_enabled:
                raise

            # Enforce Grok zero-cost eligibility before fallback
            if hasattr(self.fallback, "verify_zero_cost_eligibility"):
                eligible, reason = self.fallback.verify_zero_cost_eligibility()
                if not eligible:
                    self.metrics["fallback_blocked_zero_cost"] += 1
                    logger.warning(
                        "Grok fallback blocked by zero-cost policy: %s. "
                        "Pausing safely to protect zero-cost requirement.", reason
                    )
                    raise QuotaExhaustedError(
                        f"Primary quota exhausted and Grok fallback blocked by zero-cost policy: {reason}"
                    )

            logger.info("Falling back to Grok with confirmed zero-cost credits...")
            self.metrics["fallback_invocations"] += 1
            return self.fallback.classify_links_batch(company_name, domain, links)

    def classify_page_content(self, company_name: str, url: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self.primary.classify_page_content(company_name, url, page_data)
        except QuotaExhaustedError as qe:
            logger.warning("Primary provider quota exhausted: %s", qe)
            if not self.fallback_enabled:
                raise

            if hasattr(self.fallback, "verify_zero_cost_eligibility"):
                eligible, reason = self.fallback.verify_zero_cost_eligibility()
                if not eligible:
                    self.metrics["fallback_blocked_zero_cost"] += 1
                    logger.warning(
                        "Grok fallback blocked by zero-cost policy: %s. "
                        "Pausing safely to protect zero-cost requirement.", reason
                    )
                    raise QuotaExhaustedError(
                        f"Primary quota exhausted and Grok fallback blocked by zero-cost policy: {reason}"
                    )

            logger.info("Falling back to Grok with confirmed zero-cost credits...")
            self.metrics["fallback_invocations"] += 1
            return self.fallback.classify_page_content(company_name, url, page_data)

    def get_metrics(self) -> Dict[str, Any]:
        p_metrics = self.primary.get_metrics() if hasattr(self.primary, "get_metrics") else {}
        f_metrics = self.fallback.get_metrics() if hasattr(self.fallback, "get_metrics") else {}
        combined = dict(p_metrics)
        combined["fallback_metrics"] = f_metrics
        combined.update(self.metrics)
        return combined


class MockAIClient(BaseAIClient):
    """
    Mock AI Client for deterministic testing, CI validation, and quota-free simulation.
    Uses rule-based fallbacks and returns mock model metadata.
    """

    def __init__(self, mock_model_name: str = "mock-provider/free-model-v1"):
        super().__init__()
        self.mock_model_name = mock_model_name

    def _execute_provider_request(self, prompt: str) -> Tuple[Any, str]:
        return {}, self.mock_model_name

    def classify_links_batch(self, company_name: str, domain: str, links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        self.metrics["api_calls_made"] += 1
        self.metrics["models_used"][self.mock_model_name] = self.metrics["models_used"].get(self.mock_model_name, 0) + 1
        res = self._fallback_classify_links(company_name, links)
        for r in res:
            r["actual_model"] = self.mock_model_name
        return res

    def classify_page_content(self, company_name: str, url: str, page_data: Dict[str, Any]) -> Dict[str, Any]:
        self.metrics["api_calls_made"] += 1
        self.metrics["models_used"][self.mock_model_name] = self.metrics["models_used"].get(self.mock_model_name, 0) + 1
        res = self._fallback_classify_page(company_name, url, page_data)
        res["actual_model"] = self.mock_model_name
        return res


class AIProviderRegistry:
    """
    Pluggable registry for AI API client adapters.
    Enables adding future AI providers without modifying the crawler, page classifier,
    evidence validation, extraction pipeline, or database layer.
    """
    _registry: Dict[str, type] = {}

    @classmethod
    def register(cls, provider_name: str, client_cls: type):
        """Register a new AI provider adapter class."""
        cls._registry[provider_name.lower().strip()] = client_cls

    @classmethod
    def get(cls, provider_name: Optional[str] = None, **kwargs) -> AIClient:
        """Instantiate and return the configured or requested provider client."""
        name = (provider_name or getattr(cfg, "AI_PROVIDER", "gemini")).lower().strip()
        import inspect

        if name in cls._registry:
            target_cls = cls._registry[name]
            sig = inspect.signature(target_cls.__init__)
            if "provider_name" in sig.parameters and "provider_name" not in kwargs:
                kwargs["provider_name"] = name
            valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters and v is not None}
            return target_cls(**valid_kwargs)

        # Extensible Universal Fallback:
        # Any arbitrary custom provider connects via the industry-standard OpenAI-compatible REST interface
        logger.info("Instantiating OpenAICompatibleApiClient for dynamic/custom provider: '%s'", name)
        if "provider_name" not in kwargs:
            kwargs["provider_name"] = name
        sig = inspect.signature(OpenAICompatibleApiClient.__init__)
        valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters and v is not None}
        return OpenAICompatibleApiClient(**valid_kwargs)

    @classmethod
    def list_providers(cls) -> List[str]:
        """Return a sorted list of registered provider names."""
        return sorted(list(cls._registry.keys()))


# Register all supported major AI providers
AIProviderRegistry.register("gemini", GeminiApiClient)
AIProviderRegistry.register("grok", GrokApiClient)
AIProviderRegistry.register("openrouter", OpenRouterApiClient)
AIProviderRegistry.register("anthropic", AnthropicApiClient)
AIProviderRegistry.register("openai", OpenAICompatibleApiClient)
AIProviderRegistry.register("groq", OpenAICompatibleApiClient)
AIProviderRegistry.register("mistral", OpenAICompatibleApiClient)
AIProviderRegistry.register("deepseek", OpenAICompatibleApiClient)
AIProviderRegistry.register("ollama", OpenAICompatibleApiClient)
AIProviderRegistry.register("custom", OpenAICompatibleApiClient)
AIProviderRegistry.register("mock", MockAIClient)
AIProviderRegistry.register("fallback", PrimaryFallbackAIClient)


def get_ai_client(provider: Optional[str] = None) -> AIClient:
    """
    Factory function retrieving the configured AI client instance via AIProviderRegistry.
    When no provider is explicitly specified:
    - Queries centralized AIConfigService for active primary_provider, primary_model,
      fallback_enabled, fallback_provider, fallback_model, and free_tier_only policy.
    - If primary provider is 'mock', returns MockAIClient.
    - If fallback_enabled is True and fallback_provider is set, returns PrimaryFallbackAIClient
      managing primary and fallback client instances.
    - Otherwise returns the active primary client from registry.
    """
    try:
        from modules.admin_panel.services.ai_config_service import get_active_ai_config
        active_cfg = get_active_ai_config()
    except Exception:
        active_cfg = {}

    if provider:
        p_name = provider.lower().strip()
        p_info = active_cfg.get("providers", {}).get(p_name, {})
        p_model = p_info.get("selected_model") or getattr(cfg, "AI_MODEL", "")
        p_key = p_info.get("_api_key") or ""
        p_base = p_info.get("base_url") or ""
        return AIProviderRegistry.get(p_name, model=p_model, api_key=p_key, base_url=p_base)

    primary_name = str(active_cfg.get("primary_provider") or cfg.AI_PROVIDER).lower().strip()
    if primary_name == "mock":
        return AIProviderRegistry.get("mock")

    primary_model = active_cfg.get("primary_model") or getattr(cfg, "AI_MODEL", "")
    primary_key = active_cfg.get("primary_api_key") or ""
    primary_base = active_cfg.get("primary_base_url") or ""

    primary_inst = AIProviderRegistry.get(primary_name, model=primary_model, api_key=primary_key, base_url=primary_base)

    fallback_enabled = active_cfg.get("fallback_enabled", cfg.AI_FALLBACK_ENABLED)
    fallback_name = str(active_cfg.get("fallback_provider") or cfg.AI_FALLBACK_PROVIDER).lower().strip()

    if fallback_enabled and fallback_name:
        fallback_model = active_cfg.get("fallback_model") or getattr(cfg, "GROK_MODEL", "")
        fallback_key = active_cfg.get("fallback_api_key") or ""
        fallback_base = active_cfg.get("fallback_base_url") or ""
        fallback_inst = AIProviderRegistry.get(fallback_name, model=fallback_model, api_key=fallback_key, base_url=fallback_base)
        return PrimaryFallbackAIClient(primary=primary_inst, fallback=fallback_inst)

    return primary_inst


def test_provider_eligibility() -> Dict[str, Any]:
    """
    Tests both Gemini (primary) and Grok (fallback) provider configurations
    WITHOUT making any billable API calls.
    Returns structured verification results and reports which providers are actually
    eligible for free inference under the strict zero-cost policy.
    """
    gemini_client = GeminiApiClient()
    gemini_ok, gemini_reason = gemini_client.verify_free_tier_eligibility()

    grok_client = GrokApiClient()
    grok_ok, grok_reason = grok_client.verify_zero_cost_eligibility()

    return {
        "gemini": {
            "provider": "gemini",
            "role": "PRIMARY",
            "model": gemini_client.model,
            "is_official_free_tier_model": cfg.is_gemini_free_tier_model(gemini_client.model),
            "eligible_for_free_inference": gemini_ok,
            "status": "ELIGIBLE" if gemini_ok else "INELIGIBLE",
            "reason": gemini_reason,
            "billable_calls_prevented": True,
        },
        "grok": {
            "provider": "grok",
            "role": "FALLBACK",
            "model": grok_client.model,
            "zero_cost_only_enforced": cfg.GROK_ZERO_COST_ONLY,
            "free_credits_confirmed": cfg.GROK_FREE_CREDITS_CONFIRMED,
            "web_account_disclaimer": cfg.GROK_WEB_ACCOUNT_DISCLAIMER,
            "eligible_for_free_inference": grok_ok,
            "status": "ELIGIBLE" if grok_ok else "INELIGIBLE",
            "reason": grok_reason,
            "billable_calls_prevented": True,
        },
        "zero_cost_requirement": "STRICT_ZERO_COST",
        "summary": (
            f"Gemini (Primary): {'ELIGIBLE' if gemini_ok else 'INELIGIBLE'} - {gemini_reason} | "
            f"Grok (Fallback): {'ELIGIBLE' if grok_ok else 'INELIGIBLE'} - {grok_reason}"
        )
    }

