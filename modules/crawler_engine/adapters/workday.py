"""
modules/crawler_engine/adapters/workday.py
=========================================
Independent ATS extraction adapter for Workday career portals (*.myworkdayjobs.com).
Parses Workday public JSON API responses and HTML fallback pages.
"""
import json
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from .base import BaseATSAdapter, ExtractedJobRecord


class WorkdayAdapter(BaseATSAdapter):
    platform_name = "Workday"

    def can_handle(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return "myworkdayjobs.com" in netloc

    def extract_jobs(self, company_id: str, source_url: str, content: str, content_type: str = "html") -> List[ExtractedJobRecord]:
        results: List[ExtractedJobRecord] = []
        parsed_url = urlparse(source_url)
        base_host = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # 1. Try parsing JSON API payload if content is JSON
        if content_type == "json" or content.strip().startswith("{"):
            try:
                data = json.loads(content)
                job_postings = data.get("jobPostings") or data.get("items") or []
                for posting in job_postings:
                    title = (posting.get("title") or "").strip()
                    if not title:
                        continue
                    external_id = posting.get("bulletFields", [None])[0] or posting.get("externalPath") or posting.get("id")
                    external_path = posting.get("externalPath", "")
                    if external_path:
                        detail_url = urljoin(base_host, external_path)
                    else:
                        detail_url = source_url

                    location = posting.get("locationsText") or posting.get("location")
                    posted_date = posting.get("postedOn")
                    rec = ExtractedJobRecord(
                        company_id=company_id,
                        job_title=title,
                        detail_url=detail_url,
                        application_url=detail_url,
                        ats_platform=self.platform_name,
                        location_raw=str(location) if location else None,
                        external_job_id=str(external_id) if external_id else None,
                        source_evidence={
                            "posted_on": posted_date,
                            "raw_posting": posting
                        },
                        confidence=0.98
                    )
                    results.append(rec)
                if results:
                    return results
            except Exception:
                pass

        # 2. Fallback: Parse HTML DOM for Workday JSON-LD or data attributes
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check for schema.org JobPosting in JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                ld = json.loads(script.string or "{}")
                items = ld if isinstance(ld, list) else [ld]
                for item in items:
                    if item.get("@type") == "JobPosting":
                        title = item.get("title")
                        if not title:
                            continue
                        job_loc = item.get("jobLocation", {})
                        loc_str = None
                        if isinstance(job_loc, dict):
                            loc_str = job_loc.get("address", {}).get("addressLocality")
                        detail = item.get("url") or source_url
                        rec = ExtractedJobRecord(
                            company_id=company_id,
                            job_title=title,
                            detail_url=detail,
                            application_url=detail,
                            ats_platform=self.platform_name,
                            description=item.get("description"),
                            location_raw=loc_str,
                            employment_type=item.get("employmentType"),
                            external_job_id=item.get("identifier", {}).get("value") if isinstance(item.get("identifier"), dict) else None,
                            source_evidence={"schema_org": item},
                            confidence=0.95
                        )
                        results.append(rec)
            except Exception:
                pass

        if results:
            return results

        # 3. HTML DOM card extraction (for server-rendered Workday pages)
        cards = soup.select('li[data-automation-id="compositeSubHeaderComposite"], div[data-automation-id="jobCard"]')
        for card in cards:
            title_elem = card.select_one('a[data-automation-id="jobTitle"], h3')
            if not title_elem:
                continue
            title = title_elem.get_text(strip=True)
            href = title_elem.get('href') or ""
            detail = urljoin(base_host, href) if href else source_url
            loc_elem = card.select_one('span[data-automation-id="locations"], div[data-automation-id="locations"]')
            loc_text = loc_elem.get_text(strip=True) if loc_elem else None
            
            rec = ExtractedJobRecord(
                company_id=company_id,
                job_title=title,
                detail_url=detail,
                application_url=detail,
                ats_platform=self.platform_name,
                location_raw=loc_text,
                source_evidence={"html_card": card.get_text()[:200]},
                confidence=0.90
            )
            results.append(rec)

        return results

