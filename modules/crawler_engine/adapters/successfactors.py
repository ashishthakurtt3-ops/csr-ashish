"""
modules/crawler_engine/adapters/successfactors.py
================================================
Independent ATS extraction adapter for SAP SuccessFactors career portals.
(*.successfactors.com, *.successfactors.eu)
"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from .base import BaseATSAdapter, ExtractedJobRecord


class SuccessFactorsAdapter(BaseATSAdapter):
    platform_name = "SAP SuccessFactors"

    def can_handle(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return "successfactors.com" in netloc or "successfactors.eu" in netloc

    def extract_jobs(self, company_id: str, source_url: str, content: str, content_type: str = "html") -> List[ExtractedJobRecord]:
        results: List[ExtractedJobRecord] = []
        parsed_url = urlparse(source_url)
        base_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
        soup = BeautifulSoup(content, 'html.parser')

        # SuccessFactors job rows
        rows = soup.select('tr.jobResultItem, div.job-tile, div.sf-job-item, li.job-item')
        for row in rows:
            title_tag = row.select_one('a.jobTitle, a[href*="career"], h3 a')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get('href') or ""
            detail = urljoin(base_host, href) if href else source_url
            
            loc_tag = row.select_one('span.jobLocation, span.location, div.location')
            loc_text = loc_tag.get_text(strip=True) if loc_tag else None

            dept_tag = row.select_one('span.jobDepartment, span.department')
            dept_text = dept_tag.get_text(strip=True) if dept_tag else None

            rec = ExtractedJobRecord(
                company_id=company_id,
                job_title=title,
                detail_url=detail,
                application_url=detail,
                ats_platform=self.platform_name,
                department=dept_text,
                location_raw=loc_text,
                source_evidence={"html_row": row.get_text()[:200]},
                confidence=0.92
            )
            results.append(rec)

        return results

