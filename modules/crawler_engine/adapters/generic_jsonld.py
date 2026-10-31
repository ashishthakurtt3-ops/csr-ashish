"""
modules/crawler_engine/adapters/generic_jsonld.py
=================================================
Generic ATS and Structured Data Adapter for Schema.org JobPosting.
Handles Greenhouse, Lever, Ashby, and modern corporate career hubs with schema markup.
"""
import json
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from .base import BaseATSAdapter, ExtractedJobRecord


class GenericStructuredJobAdapter(BaseATSAdapter):
    platform_name = "Structured JSON-LD"

    def can_handle(self, url: str) -> bool:
        # Can be evaluated on any career page as primary high-precision extraction
        return True

    def extract_jobs(self, company_id: str, source_url: str, content: str, content_type: str = "html") -> List[ExtractedJobRecord]:
        results: List[ExtractedJobRecord] = []
        soup = BeautifulSoup(content, 'html.parser')

        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw_json = (script.string or "").strip()
                if not raw_json:
                    continue
                data = json.loads(raw_json)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    item_type = item.get("@type")
                    if item_type == "JobPosting":
                        title = (item.get("title") or "").strip()
                        if not title:
                            continue
                        
                        loc_str = None
                        job_loc = item.get("jobLocation")
                        if isinstance(job_loc, dict):
                            addr = job_loc.get("address", {})
                            if isinstance(addr, dict):
                                loc_str = addr.get("addressLocality") or addr.get("addressRegion")
                            elif isinstance(addr, str):
                                loc_str = addr
                        elif isinstance(job_loc, list) and job_loc:
                            loc_str = str(job_loc[0])

                        detail_url = item.get("url") or source_url
                        desc = item.get("description")
                        emp_type = item.get("employmentType")

                        rec = ExtractedJobRecord(
                            company_id=company_id,
                            job_title=title,
                            detail_url=detail_url,
                            application_url=detail_url,
                            ats_platform="Schema.org JSON-LD",
                            description=str(desc)[:500] if desc else None,
                            location_raw=str(loc_str) if loc_str else None,
                            employment_type=str(emp_type) if emp_type else None,
                            source_evidence={"schema_org": item},
                            confidence=0.96
                        )
                        results.append(rec)
            except Exception:
                continue

        return results

