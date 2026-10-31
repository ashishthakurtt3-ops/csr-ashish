"""
modules/crawler_engine/adapters/taleo.py
======================================
Independent ATS extraction adapter for Oracle Taleo and Oracle Cloud career portals.
(*.taleo.net, *.oraclecloud.com)
"""
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from .base import BaseATSAdapter, ExtractedJobRecord


class TaleoAdapter(BaseATSAdapter):
    platform_name = "Oracle Taleo"

    def can_handle(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return "taleo.net" in netloc or "oraclecloud.com" in netloc

    def extract_jobs(self, company_id: str, source_url: str, content: str, content_type: str = "html") -> List[ExtractedJobRecord]:
        results: List[ExtractedJobRecord] = []
        parsed_url = urlparse(source_url)
        base_host = f"{parsed_url.scheme}://{parsed_url.netloc}"
        soup = BeautifulSoup(content, 'html.parser')

        # Taleo uses table rows with class "ftlrow" or requisition spans
        rows = soup.select('tr[id*="requisitionListInterface"], tr.ftlrow, div.multilinecontent')
        for row in rows:
            title_tag = row.select_one('a[id*="requisitionTitle"], span.title, a.title')
            if not title_tag:
                continue
            title = title_tag.get_text(strip=True)
            href = title_tag.get('href') or ""
            detail = urljoin(base_host, href) if href else source_url
            
            # Location
            loc_tag = row.select_one('span[id*="requisitionLocation"], div.location')
            loc_text = loc_tag.get_text(strip=True) if loc_tag else None

            # Requisition ID
            req_tag = row.select_one('span[id*="requisitionNumber"]')
            req_id = req_tag.get_text(strip=True) if req_tag else None

            rec = ExtractedJobRecord(
                company_id=company_id,
                job_title=title,
                detail_url=detail,
                application_url=detail,
                ats_platform=self.platform_name,
                location_raw=loc_text,
                external_job_id=req_id,
                source_evidence={"html_row": row.get_text()[:200]},
                confidence=0.92
            )
            results.append(rec)

        return results

