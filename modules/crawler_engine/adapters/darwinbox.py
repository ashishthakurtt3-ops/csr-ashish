"""
modules/crawler_engine/adapters/darwinbox.py
===========================================
Independent ATS extraction adapter for Darwinbox career portals (*.darwinbox.in / *.darwinbox.com).
Parses Darwinbox candidate recruitment API endpoints and rendered listing tables.
"""
import json
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from .base import BaseATSAdapter, ExtractedJobRecord


class DarwinboxAdapter(BaseATSAdapter):
    platform_name = "Darwinbox"

    def can_handle(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return "darwinbox.in" in netloc or "darwinbox.com" in netloc

    def extract_jobs(self, company_id: str, source_url: str, content: str, content_type: str = "html") -> List[ExtractedJobRecord]:
        results: List[ExtractedJobRecord] = []
        parsed_url = urlparse(source_url)
        base_host = f"{parsed_url.scheme}://{parsed_url.netloc}"

        # 1. Parse JSON if returned by Darwinbox AJAX recruitment API
        if content_type == "json" or content.strip().startswith("{"):
            try:
                data = json.loads(content)
                jobs_list = data.get("data") or data.get("jobs") or data.get("positions") or []
                if isinstance(jobs_list, dict):
                    jobs_list = jobs_list.get("data") or []
                for j in jobs_list:
                    title = (j.get("job_title") or j.get("title") or j.get("position_name") or "").strip()
                    if not title:
                        continue
                    job_id = str(j.get("job_id") or j.get("id") or "")
                    apply_link = j.get("apply_url") or j.get("job_url") or (f"{source_url.rstrip('/')}/job/{job_id}" if job_id else source_url)
                    loc = j.get("location") or j.get("job_location") or j.get("city")
                    dept = j.get("department") or j.get("function")
                    exp = j.get("experience") or j.get("experience_required")
                    
                    rec = ExtractedJobRecord(
                        company_id=company_id,
                        job_title=title,
                        detail_url=apply_link,
                        application_url=apply_link,
                        ats_platform=self.platform_name,
                        department=str(dept) if dept else None,
                        location_raw=str(loc) if loc else None,
                        external_job_id=job_id or None,
                        source_evidence={"raw_data": j, "experience": exp},
                        confidence=0.98
                    )
                    results.append(rec)
                if results:
                    return results
            except Exception:
                pass

        # 2. Parse HTML DOM listing
        soup = BeautifulSoup(content, 'html.parser')
        # Typical Darwinbox job rows: .job-list-item, .job_row, tr[data-job-id]
        rows = soup.select('.job-card, .job-item, .job_row, tr.job-list-row, div.careers-job-item')
        for row in rows:
            title_tag = row.select_one('.job-title, .job_title, h3, h4, a.title')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            link_tag = row.select_one('a[href*="job"], a.apply-btn, a[href*="career"]') or title_tag
            href = link_tag.get('href') if link_tag.name == 'a' else (link_tag.find('a') or {}).get('href')
            detail = urljoin(base_host, href) if href else source_url
            
            loc_tag = row.select_one('.job-location, .location, span.loc')
            loc_text = loc_tag.get_text(strip=True) if loc_tag else None
            
            dept_tag = row.select_one('.job-department, .department')
            dept_text = dept_tag.get_text(strip=True) if dept_tag else None

            rec = ExtractedJobRecord(
                company_id=company_id,
                job_title=title,
                detail_url=detail,
                application_url=detail,
                ats_platform=self.platform_name,
                department=dept_text,
                location_raw=loc_text,
                source_evidence={"html_snippet": row.get_text()[:200]},
                confidence=0.92
            )
            results.append(rec)

        return results

