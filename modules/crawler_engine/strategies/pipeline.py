"""
Pluggable Strategy Pipeline for ImpactBridge™ Job Discovery Engine.

Coordinates the 8-tier extraction cascade cheapest-first:
1. ATS auto-detection & adapters
2. JSON-LD schema.org parsing
3. Job sitemap XML probing
4. Embedded state JSON (__NEXT_DATA__, __NUXT__, Apollo)
5. Anchor-card extraction (repeated DOM elements)
6. Intercepted XHR JSON responses
7. Single-tab Playwright Click-and-capture fallback
8. Graceful LISTING_FALLBACK marking

Caches winning strategy per company (company.extraction_strategy), re-validates each job
through the pre-save link validation gate (link_validator.py).
"""
from __future__ import annotations

import logging
import os
import yaml
from typing import Dict, Any, List, Optional, Tuple

from curl_cffi import requests as cffi_requests

from .base import BaseStrategy, ExtractionContext
from .ats_strategy import ATSStrategy
from .jsonld_strategy import JsonLdStrategy
from .sitemap_strategy import JobSitemapStrategy
from .embedded_state_strategy import EmbeddedStateStrategy
from .anchor_card_strategy import AnchorCardStrategy
from .xhr_json_strategy import XhrJsonStrategy
from .click_capture_strategy import ClickCaptureStrategy
from ..link_validator import validate_job_candidate_url
from ..normalizers import clean_text, normalize_canonical_url

logger = logging.getLogger(__name__)


def load_domain_overrides() -> Dict[str, Any]:
    """Loads optional domain-level configuration from overrides.yaml without hardcoding in Python."""
    override_path = os.path.join(os.path.dirname(__file__), "overrides.yaml")
    if os.path.exists(override_path):
        try:
            with open(override_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}


class StrategyPipeline:
    def __init__(self):
        self.strategies: List[BaseStrategy] = [
            ATSStrategy(),
            JsonLdStrategy(),
            JobSitemapStrategy(),
            EmbeddedStateStrategy(),
            AnchorCardStrategy(),
            XhrJsonStrategy(),
            ClickCaptureStrategy(),
        ]
        self.strategy_map: Dict[str, BaseStrategy] = {s.name: s for s in self.strategies}
        self.overrides = load_domain_overrides()

    def run(self, company: Any, careers_url: str) -> Tuple[List[Dict[str, Any]], str, float]:
        """
        Runs the extraction cascade for a company.

        Returns:
            (validated_jobs, winning_strategy_name, direct_percentage)
        """
        if not careers_url or not clean_text(careers_url):
            return [], "none", 0.0

        context = ExtractionContext(company=company, careers_url=careers_url)

        # 1. Fetch landing HTML once to share across detectors
        try:
            resp = cffi_requests.get(
                careers_url,
                impersonate="chrome124",
                timeout=18,
                allow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}
            )
            context.status_code = resp.status_code
            context.final_url = resp.url
            context.html_content = resp.text
        except Exception as exc:
            logger.debug("Failed initial fetch of careers URL %s: %s", careers_url, exc)
            context.final_url = careers_url
            context.html_content = ""

        # 2. Check cached strategy
        cached_strategy = getattr(company, "extraction_strategy", None)
        ordered_strategies: List[BaseStrategy] = []

        if cached_strategy and cached_strategy in self.strategy_map and cached_strategy != "none":
            # Fast-path: try cached strategy FIRST
            ordered_strategies.append(self.strategy_map[cached_strategy])
            ordered_strategies.extend([s for s in self.strategies if s.name != cached_strategy])
        else:
            ordered_strategies = list(self.strategies)

        winning_strategy = "none"
        raw_extracted_jobs: List[Dict[str, Any]] = []

        # 3. Cascade execution: stop when one yields results that pass validation
        for strategy in ordered_strategies:
            try:
                if strategy.detect(context):
                    jobs = strategy.extract(context)
                    if jobs:
                        raw_extracted_jobs = jobs
                        winning_strategy = strategy.name
                        break
            except Exception as exc:
                logger.debug("Strategy %s failed for %s: %s", strategy.name, company, exc)
                continue

        # 4. If nothing works or 0 jobs found
        if not raw_extracted_jobs:
            reason = "no_jobs_found"
            if context.status_code in (401, 403):
                reason = "login_required_or_bot_blocked"
            elif context.status_code in (404, 500, 502, 503):
                reason = f"http_{context.status_code}"

            company.extraction_strategy = "none"
            company.last_strategy_success_rate = 0.0
            return [], "none", 0.0

        # 5. Pre-save Link Validation Gate (Phase 4)
        is_ats = winning_strategy in ("ats_api", "lever_api", "greenhouse_api", "workday_cxs")
        canon_careers = normalize_canonical_url(context.careers_url)

        # Count frequencies in this batch
        batch_counts: Dict[str, int] = {}
        for j in raw_extracted_jobs:
            u = normalize_canonical_url(j.get("application_url"))
            if u:
                batch_counts[u] = batch_counts.get(u, 0) + 1

        validated_jobs = []
        direct_count = 0

        for raw_job in raw_extracted_jobs:
            cand_url = raw_job.get("application_url")
            ext_id = raw_job.get("external_job_id")
            title = raw_job.get("title")

            canon, quality, note = validate_job_candidate_url(
                candidate_url=cand_url,
                company_careers_url=canon_careers,
                job_title=title,
                external_job_id=ext_id,
                is_ats_api=is_ats,
                batch_url_counts=batch_counts,
                sample_rate=0.05,
            )

            # Never allow listing URL to be marked DIRECT
            if canon == canon_careers:
                quality = "LISTING_FALLBACK"
                note = "canonical_equals_company_careers_url"

            if quality == "DIRECT":
                direct_count += 1

            job_dict = dict(raw_job)
            job_dict["application_url"] = canon or cand_url
            job_dict["canonical_url"] = canon
            job_dict["link_quality"] = quality
            job_dict["link_check_note"] = note
            job_dict["external_job_id"] = ext_id
            validated_jobs.append(job_dict)

        total_v = len(validated_jobs)
        success_rate = round((direct_count / total_v) * 100, 2) if total_v > 0 else 0.0

        # Save winning strategy to company
        company.extraction_strategy = winning_strategy
        company.last_strategy_success_rate = success_rate
        if context.discovered_ats_platform:
            company.ats_type = context.discovered_ats_platform
        if context.discovered_ats_token:
            company.ats_token = context.discovered_ats_token

        return validated_jobs, winning_strategy, success_rate
