"""
Embedded State JSON Extraction Strategy for ImpactBridge™ Job Discovery Engine.

Parses hydration state payloads in modern web applications:
- __NEXT_DATA__ (Next.js)
- __NUXT__ (Nuxt.js)
- window.__INITIAL_STATE__
- window.__APOLLO_STATE__

Finds job objects containing title, id/slug/jobId, constructs direct URLs.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup

from .base import BaseStrategy, ExtractionContext
from ..normalizers import clean_text, normalize_canonical_url

logger = logging.getLogger(__name__)


def find_job_arrays_recursively(obj: Any, depth: int = 0) -> List[Dict[str, Any]]:
    """Walks an arbitrary nested JSON object searching for lists of job-like dicts."""
    if depth > 7:
        return []

    results = []
    if isinstance(obj, dict):
        # Check if dict itself is a job item
        has_title = any(k in obj for k in ("title", "jobTitle", "job_title", "positionName", "postingTitle"))
        has_id_or_url = any(k in obj for k in ("id", "jobId", "slug", "reqId", "job_id", "url", "applyUrl", "externalPath"))
        if has_title and has_id_or_url:
            results.append(obj)
            return results

        for k, v in obj.items():
            results.extend(find_job_arrays_recursively(v, depth + 1))
    elif isinstance(obj, list):
        for item in obj:
            results.extend(find_job_arrays_recursively(item, depth + 1))

    return results


class EmbeddedStateStrategy(BaseStrategy):
    name = "embedded_state_json"

    def detect(self, context: ExtractionContext) -> bool:
        if not context.html_content:
            return False
        return any(
            marker in context.html_content
            for marker in ("__NEXT_DATA__", "__NUXT__", "__INITIAL_STATE__", "__APOLLO_STATE__")
        )

    def extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        if not context.html_content:
            return []

        parsed = urlparse(context.final_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        soup = BeautifulSoup(context.html_content, "lxml")
        raw_json_payloads = []

        # 1. __NEXT_DATA__
        next_tag = soup.find("script", id="__NEXT_DATA__")
        if next_tag and next_tag.string:
            try:
                raw_json_payloads.append(json.loads(next_tag.string))
            except Exception:
                pass

        # 2. window.__INITIAL_STATE__ or __NUXT__ via regex
        for script in soup.find_all("script"):
            text = script.string or ""
            if not text:
                continue
            m = re.search(r"window\.(?:__INITIAL_STATE__|__APOLLO_STATE__)\s*=\s*(\{.*?\});", text, re.S)
            if m:
                try:
                    raw_json_payloads.append(json.loads(m.group(1)))
                except Exception:
                    pass

        all_candidate_jobs = []
        for payload in raw_json_payloads:
            found = find_job_arrays_recursively(payload)
            all_candidate_jobs.extend(found)

        jobs = []
        seen = set()

        for item in all_candidate_jobs:
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
                # Construct standard detail pattern
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
                "link_check_note": "embedded_state_json_direct" if is_direct else "embedded_state_missing_url",
            })

        return jobs
