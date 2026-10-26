"""
JSON-LD Extraction Strategy for ImpactBridge™ Job Discovery Engine.

Parses all <script type="application/ld+json"> tags for @type JobPosting,
including within @graph, ItemList, or direct array structures.
Extracts title, url, identifier, jobLocation, datePosted, employmentType, description.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseStrategy, ExtractionContext
from ..normalizers import clean_text, normalize_canonical_url

logger = logging.getLogger(__name__)


class JsonLdStrategy(BaseStrategy):
    name = "jsonld"

    def detect(self, context: ExtractionContext) -> bool:
        if not context.html_content:
            return False
        return "application/ld+json" in context.html_content and "JobPosting" in context.html_content

    def extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        if not context.html_content:
            return []

        soup = BeautifulSoup(context.html_content, "lxml")
        jobs = []
        seen_keys = set()

        for script in soup.find_all("script", type="application/ld+json"):
            raw = script.string or ""
            if not raw.strip():
                continue

            try:
                data = json.loads(raw)
            except Exception:
                continue

            items_to_check = []
            if isinstance(data, dict):
                if "@graph" in data and isinstance(data["@graph"], list):
                    items_to_check.extend(data["@graph"])
                elif data.get("@type") == "ItemList" and "itemListElement" in data:
                    elements = data.get("itemListElement", [])
                    for el in elements:
                        if isinstance(el, dict) and "item" in el and isinstance(el["item"], dict):
                            items_to_check.append(el["item"])
                        elif isinstance(el, dict):
                            items_to_check.append(el)
                else:
                    items_to_check.append(data)
            elif isinstance(data, list):
                items_to_check.extend(data)

            for item in items_to_check:
                if not isinstance(item, dict):
                    continue

                item_type = item.get("@type", "")
                is_job = item_type == "JobPosting" or (isinstance(item_type, list) and "JobPosting" in item_type)
                if not is_job:
                    continue

                title = clean_text(item.get("title"))
                if not title or len(title) < 3:
                    continue

                # URL extraction
                app_url = item.get("url") or item.get("sameAs")
                if app_url:
                    app_url = urljoin(context.final_url, str(app_url).strip())
                else:
                    app_url = context.final_url

                # Identifier / external job ID
                ident = item.get("identifier")
                ext_id = None
                if isinstance(ident, dict):
                    ext_id = clean_text(str(ident.get("value") or ident.get("name") or ""))
                elif ident:
                    ext_id = clean_text(str(ident))

                # Location
                loc_val = None
                job_loc = item.get("jobLocation")
                if isinstance(job_loc, dict):
                    addr = job_loc.get("address", {})
                    if isinstance(addr, dict):
                        city = addr.get("addressLocality")
                        state = addr.get("addressRegion")
                        country = addr.get("addressCountry")
                        loc_val = ", ".join(filter(None, [city, state, country]))
                elif isinstance(job_loc, list) and job_loc:
                    addr = job_loc[0].get("address", {}) if isinstance(job_loc[0], dict) else {}
                    if isinstance(addr, dict):
                        loc_val = ", ".join(filter(None, [addr.get("addressLocality"), addr.get("addressRegion")]))

                loc = loc_val or "India"

                key = f"{title}_{app_url}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                is_direct = bool(app_url and app_url != context.final_url and "#:~:text=" not in app_url)

                jobs.append({
                    "title": title,
                    "location": loc,
                    "department": item.get("occupationalCategory") or item.get("department") or "Corporate",
                    "employment_type": item.get("employmentType"),
                    "application_url": app_url,
                    "external_job_id": ext_id,
                    "posted_date": item.get("datePosted"),
                    "job_description": BeautifulSoup(item.get("description", ""), "lxml").get_text("\n", strip=True)[:4000] if item.get("description") else None,
                    "raw_metadata": item,
                    "link_quality": "DIRECT" if is_direct else "LISTING_FALLBACK",
                    "link_check_note": "jsonld_jobposting_url" if is_direct else "jsonld_missing_direct_url",
                })

        return jobs
