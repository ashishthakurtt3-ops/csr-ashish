"""
Job Sitemap Extraction Strategy for ImpactBridge™ Job Discovery Engine.

Inspects robots.txt for sitemap directives and probes common sitemap patterns:
/sitemap-jobs.xml, /jobs-sitemap.xml, /careers-sitemap.xml, /sitemap_careers.xml.
Filters for individual job posting URLs (containing slugs or ID segments),
fetches individual pages to confirm job titles.
"""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from .base import BaseStrategy, ExtractionContext
from ..normalizers import clean_text, normalize_canonical_url

logger = logging.getLogger(__name__)

COMMON_JOB_SITEMAPS = [
    "/sitemap-jobs.xml",
    "/jobs-sitemap.xml",
    "/careers-sitemap.xml",
    "/sitemap_careers.xml",
    "/sitemap_jobs.xml",
    "/careers/sitemap.xml",
    "/jobs/sitemap.xml",
]

_JOB_PATH_REGEX = re.compile(r"/(?:job|jobs|career|careers|opening|openings|position|positions)/([a-zA-Z0-9_\-]+)", re.I)


class JobSitemapStrategy(BaseStrategy):
    name = "job_sitemap"

    def detect(self, context: ExtractionContext) -> bool:
        # Fast probe for robots.txt or sitemaps
        parsed = urlparse(context.careers_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        try:
            resp = cffi_requests.get(f"{base}/robots.txt", impersonate="chrome124", timeout=6)
            if resp.status_code == 200 and "sitemap" in resp.text.lower():
                return True
        except Exception:
            pass
        return False

    def extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        parsed = urlparse(context.careers_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        sitemap_urls = set()

        # 1. Check robots.txt
        try:
            resp = cffi_requests.get(f"{base}/robots.txt", impersonate="chrome124", timeout=8)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    if line.strip().lower().startswith("sitemap:"):
                        sm = line.split(":", 1)[1].strip()
                        if any(k in sm.lower() for k in ("job", "career", "work")):
                            sitemap_urls.add(sm)
        except Exception:
            pass

        # 2. Add common fallback sitemaps
        for path in COMMON_JOB_SITEMAPS:
            sitemap_urls.add(f"{base}{path}")

        # 3. Fetch sitemaps and find job URLs
        candidate_job_urls = []
        for sm_url in sitemap_urls:
            try:
                resp = cffi_requests.get(sm_url, impersonate="chrome124", timeout=10)
                if resp.status_code != 200:
                    continue

                # Parse XML
                root = ET.fromstring(resp.content)
                # Handle xmlns
                for elem in root.iter():
                    if elem.tag.endswith("loc") and elem.text:
                        loc = elem.text.strip()
                        if _JOB_PATH_REGEX.search(loc):
                            candidate_job_urls.append(loc)
                            if len(candidate_job_urls) >= 100:
                                break
                if candidate_job_urls:
                    break
            except Exception:
                continue

        if not candidate_job_urls:
            return []

        # 4. Fetch detail pages to confirm titles
        jobs = []
        for url in candidate_job_urls[:40]:  # Cap to polite sample
            canon = normalize_canonical_url(url)
            if not canon:
                continue
            try:
                page_resp = cffi_requests.get(canon, impersonate="chrome124", timeout=8)
                if page_resp.status_code != 200:
                    continue

                soup = BeautifulSoup(page_resp.text, "lxml")
                # Title extraction
                title = None
                h1 = soup.find("h1")
                if h1:
                    title = clean_text(h1.get_text(strip=True))
                if not title:
                    title_elem = soup.find("title")
                    if title_elem:
                        raw_title = clean_text(title_elem.get_text(strip=True))
                        if raw_title:
                            title = re.split(r"\s*[\|\-–—:»/]\s*", raw_title)[0].strip()

                if not title or len(title) < 3 or len(title) > 120:
                    continue

                # Extract ID from URL
                m = _JOB_PATH_REGEX.search(canon)
                ext_id = m.group(1) if m else None

                jobs.append({
                    "title": title,
                    "location": "India",
                    "department": "Corporate",
                    "application_url": canon,
                    "external_job_id": ext_id,
                    "raw_metadata": {"source_sitemap_url": url},
                    "link_quality": "DIRECT",
                    "link_check_note": "sitemap_direct_job_page",
                })
            except Exception:
                continue

        return jobs
