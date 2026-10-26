"""
Intercepted XHR JSON Strategy for ImpactBridge™ Job Discovery Engine.

Captures and parses backend REST/XHR API responses during page loading.
Extracts job entities containing title, id/slug/jobId, and builds valid direct links.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin

from .base import BaseStrategy, ExtractionContext
from .embedded_state_strategy import find_job_arrays_recursively
from ..normalizers import clean_text, normalize_canonical_url

logger = logging.getLogger(__name__)


class XhrJsonStrategy(BaseStrategy):
    name = "xhr_json"

    def detect(self, context: ExtractionContext) -> bool:
        # Check if context already intercepted XHR responses or has candidates in extra_metadata
        return bool(context.extra_metadata.get("intercepted_xhr_payloads"))

    def extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        xhr_payloads = context.extra_metadata.get("intercepted_xhr_payloads", [])
        if not xhr_payloads:
            return []

        all_candidate_items = []
        for payload in xhr_payloads:
            if isinstance(payload, (dict, list)):
                items = find_job_arrays_recursively(payload)
                all_candidate_items.extend(items)

        jobs = []
        seen = set()

        for item in all_candidate_items:
            title = clean_text(
                item.get("title")
                or item.get("jobTitle")
                or item.get("job_title")
                or item.get("positionName")
                or item.get("postingTitle")
            )
            if not title or len(title) < 3 or len(title) > 120:
                continue

            jid = str(
                item.get("id")
                or item.get("jobId")
                or item.get("job_id")
                or item.get("reqId")
                or item.get("slug")
                or ""
            ).strip()

            direct_url = (
                item.get("url")
                or item.get("applyUrl")
                or item.get("hostedUrl")
                or item.get("canonical_url")
            )
            if direct_url:
                direct_url = urljoin(context.final_url, str(direct_url))
            elif jid:
                direct_url = f"{context.final_url.rstrip('/')}/{jid}"
            else:
                direct_url = context.final_url

            canon = normalize_canonical_url(direct_url) or direct_url
            key = f"{title}_{canon}"
            if key in seen:
                continue
            seen.add(key)

            loc = item.get("location") or item.get("city") or "India"
            is_direct = bool(canon and canon != context.final_url and "#:~:text=" not in canon)

            jobs.append({
                "title": title,
                "location": str(loc),
                "department": item.get("department") or "Corporate",
                "application_url": canon,
                "external_job_id": jid or None,
                "raw_metadata": item,
                "link_quality": "DIRECT" if is_direct else "LISTING_FALLBACK",
                "link_check_note": "xhr_json_direct" if is_direct else "xhr_json_missing_direct_url",
            })

        return jobs
