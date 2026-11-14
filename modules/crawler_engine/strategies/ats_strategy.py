"""
ATS Strategy & Unified Adapters for ImpactBridge™ Job Discovery Engine.

Implements auto-detection across:
- Lever
- Greenhouse
- Workday
- SmartRecruiters
- Darwinbox
- SuccessFactors
- Oracle Cloud HCM / Taleo
- iCIMS
- Ashby
- Recruitee
- Zoho Recruit
- Keka
- Freshteam
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests

from .base import BaseStrategy, ExtractionContext
from ..normalizers import clean_text, normalize_canonical_url

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def cffi_get(url: str, **kwargs) -> Optional[Any]:
    try:
        kwargs.setdefault("impersonate", "chrome124")
        kwargs.setdefault("timeout", 18)
        kwargs.setdefault("headers", HEADERS)
        resp = cffi_requests.get(url, **kwargs)
        return resp
    except Exception as exc:
        logger.debug("GET %s failed: %s", url[:100], exc)
        return None


def cffi_post(url: str, **kwargs) -> Optional[Any]:
    try:
        kwargs.setdefault("impersonate", "chrome124")
        kwargs.setdefault("timeout", 18)
        kwargs.setdefault("headers", {**HEADERS, "Content-Type": "application/json"})
        resp = cffi_requests.post(url, **kwargs)
        return resp
    except Exception as exc:
        logger.debug("POST %s failed: %s", url[:100], exc)
        return None


class ATSStrategy(BaseStrategy):
    name = "ats_api"

    ATS_SIGNATURES = [
        ("lever", re.compile(r"lever\.co/([^/?#]+)", re.I)),
        ("greenhouse", re.compile(r"greenhouse\.io/([^/?#]+)", re.I)),
        ("workday", re.compile(r"([a-z0-9\-]+)\.(?:wd\d+\.)?myworkdayjobs\.com", re.I)),
        ("smartrecruiters", re.compile(r"smartrecruiters\.com/([^/?#]+)", re.I)),
        ("darwinbox", re.compile(r"([a-z0-9\-]+)\.darwinbox\.(?:in|com)", re.I)),
        ("successfactors", re.compile(r"successfactors|jobs\.mahindracareers|tatamotorscareers|heromotocorp", re.I)),
        ("oracle", re.compile(r"oraclecloud\.com|taleo\.net", re.I)),
        ("icims", re.compile(r"([a-z0-9\-]+)\.icims\.com", re.I)),
        ("ashby", re.compile(r"ashbyhq\.com/([^/?#]+)", re.I)),
        ("recruitee", re.compile(r"([a-z0-9\-]+)\.recruitee\.com", re.I)),
        ("zohorecruit", re.compile(r"([a-z0-9\-]+)\.zohorecruit\.(?:com|in)", re.I)),
        ("keka", re.compile(r"([a-z0-9\-]+)\.keka\.com", re.I)),
        ("freshteam", re.compile(r"([a-z0-9\-]+)\.freshteam\.com", re.I)),
    ]

    def detect(self, context: ExtractionContext) -> bool:
        # 1. Check company fields
        if getattr(context.company, "ats_platform", None) or getattr(context.company, "ats_type", None):
            return True

        # 2. Check careers_url and final_url
        urls_to_check = [context.careers_url, context.final_url]
        for u in urls_to_check:
            if not u:
                continue
            for platform, regex in self.ATS_SIGNATURES:
                m = regex.search(u)
                if m:
                    context.discovered_ats_platform = platform
                    token = m.group(1) if m.lastindex else platform
                    if platform == "greenhouse":
                        for_m = re.search(r"[?&]for=([^&#]+)", u, re.I)
                        if for_m:
                            token = for_m.group(1)
                        elif token in ("embed", "js", "api"):
                            token = None
                    context.discovered_ats_token = token
                    context.discovered_ats_url = u
                    return True

        # 3. Check HTML content for iframe, script src, or links (Fix Target URL Desynchronization)
        if context.html_content:
            text = context.html_content[:150000]

            # Priority A: Greenhouse embed with ?for=company
            gh_for = re.search(r'boards\.greenhouse\.io.*?[\?&]for=([a-zA-Z0-9_\-]+)', text, re.I)
            if gh_for:
                token = gh_for.group(1)
                context.discovered_ats_platform = "greenhouse"
                context.discovered_ats_token = token
                ats_url = f"https://boards.greenhouse.io/{token}"
                context.discovered_ats_url = ats_url
                context.final_url = ats_url
                return True

            # Priority B: Workday portal iframe or link
            wd_match = re.search(r'https?://([a-zA-Z0-9_\-\.]+\.myworkdayjobs\.com/[^"\'<>\s]+)', text, re.I)
            if wd_match:
                ats_url = wd_match.group(0).rstrip('"\')')
                context.discovered_ats_platform = "workday"
                context.discovered_ats_url = ats_url
                context.final_url = ats_url
                sub = urlparse(ats_url).netloc.split(".")[0]
                context.discovered_ats_token = sub
                return True

            # Priority C: Lever direct portal
            lev_match = re.search(r'https?://jobs\.lever\.co/([a-zA-Z0-9_\-]+)', text, re.I)
            if lev_match:
                token = lev_match.group(1)
                context.discovered_ats_platform = "lever"
                context.discovered_ats_token = token
                ats_url = f"https://jobs.lever.co/{token}"
                context.discovered_ats_url = ats_url
                context.final_url = ats_url
                return True

            # Priority D: SmartRecruiters
            sr_match = re.search(r'https?://(?:careers|jobs|www)?\.smartrecruiters\.com/([a-zA-Z0-9_\-]+)', text, re.I)
            if sr_match:
                token = sr_match.group(1)
                context.discovered_ats_platform = "smartrecruiters"
                context.discovered_ats_token = token
                ats_url = sr_match.group(0)
                context.discovered_ats_url = ats_url
                context.final_url = ats_url
                return True

            # Priority E: SuccessFactors
            sf_match = re.search(r'https?://[a-zA-Z0-9_\-\.]*successfactors\.[a-z]+/[^"\'<>\s]+', text, re.I)
            if sf_match:
                ats_url = sf_match.group(0).rstrip('"\')')
                context.discovered_ats_platform = "successfactors"
                context.discovered_ats_url = ats_url
                context.final_url = ats_url
                context.discovered_ats_token = urlparse(ats_url).netloc
                return True

            # Priority F: Darwinbox
            db_match = re.search(r'https?://([a-zA-Z0-9_\-]+)\.darwinbox\.(?:in|com)/?[^"\'<>\s]*', text, re.I)
            if db_match:
                token = db_match.group(1)
                context.discovered_ats_platform = "darwinbox"
                context.discovered_ats_token = token
                ats_url = db_match.group(0).rstrip('"\')')
                context.discovered_ats_url = ats_url
                context.final_url = ats_url
                return True

            # General signature fallback
            for platform, regex in self.ATS_SIGNATURES:
                m = regex.search(text)
                if m:
                    token = m.group(1) if m.lastindex else platform
                    if platform == "greenhouse" and token in ("embed", "js", "api"):
                        for_m = re.search(r"[?&]for=([^&#]+)", text, re.I)
                        if for_m:
                            token = for_m.group(1)
                    context.discovered_ats_platform = platform
                    context.discovered_ats_token = token

                    # Extract full ATS URL from surrounding markup
                    m_str = m.group(0)
                    url_m = re.search(r'https?://[^\s"\'<>]*' + re.escape(m_str) + r'[^\s"\'<>]*', text)
                    if url_m:
                        ats_url = url_m.group(0).rstrip('"\')')
                        context.discovered_ats_url = ats_url
                        context.final_url = ats_url
                    return True

        return False

    def extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        platform = (
            context.discovered_ats_platform
            or getattr(context.company, "ats_type", None)
            or getattr(context.company, "ats_platform", None)
            or ""
        ).lower()

        token = context.discovered_ats_token or getattr(context.company, "ats_token", None)
        # Fix Target URL Desynchronization: prioritize discovered_ats_url
        target_url = (
            getattr(context, "discovered_ats_url", None)
            or getattr(context.company, "ats_url", None)
            or context.final_url
            or context.careers_url
        )

        # Dispatch to specific adapter
        if "lever" in platform or "lever.co" in target_url:
            return self._extract_lever(target_url, token, context)
        if "greenhouse" in platform or "greenhouse.io" in target_url:
            return self._extract_greenhouse(target_url, token, context)
        if "workday" in platform or "myworkdayjobs" in target_url:
            return self._extract_workday(target_url, token, context)
        if "smartrecruiters" in platform or "smartrecruiters.com" in target_url:
            return self._extract_smartrecruiters(target_url, token, context)
        if "darwinbox" in platform or "darwinbox" in target_url:
            return self._extract_darwinbox(target_url, token, context)
        if "successfactors" in platform or any(k in target_url for k in ("successfactors", "mahindracareers", "tatamotorscareers", "heromotocorp")):
            return self._extract_successfactors(target_url, token, context)
        if "oracle" in platform or "taleo" in platform or "oraclecloud" in target_url or "taleo.net" in target_url:
            return self._extract_oracle(target_url, token, context)
        if "recruitee" in platform or "recruitee.com" in target_url:
            return self._extract_recruitee(target_url, token, context)
        if "ashby" in platform or "ashbyhq.com" in target_url:
            return self._extract_ashby(target_url, token, context)
        if "icims" in platform or "icims.com" in target_url:
            return self._extract_icims(target_url, token, context)
        if "zohorecruit" in platform or "zohorecruit" in target_url:
            return self._extract_zohorecruit(target_url, token, context)
        if "keka" in platform or "keka.com" in target_url:
            return self._extract_keka(target_url, token, context)
        if "freshteam" in platform or "freshteam.com" in target_url:
            return self._extract_freshteam(target_url, token, context)

        return []

    # -------------------------------------------------------------------------
    # 1. Lever Adapter
    # -------------------------------------------------------------------------
    def _extract_lever(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        if not token:
            m = re.search(r"lever\.co/([^/?#]+)", url, re.I)
            if m:
                token = m.group(1)
        if not token:
            return []

        context.discovered_ats_platform = "Lever"
        context.discovered_ats_token = token
        api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"
        resp = cffi_get(api_url)
        if not resp or resp.status_code != 200:
            return []

        try:
            items = resp.json()
        except Exception:
            return []

        jobs = []
        for item in items:
            title = clean_text(item.get("text"))
            jid = clean_text(item.get("id"))
            if not title:
                continue

            # Prioritize hostedUrl, then fallback to standard direct link
            direct_url = item.get("hostedUrl") or (f"https://jobs.lever.co/{token}/{jid}" if jid else None)
            cats = item.get("categories") or {}
            loc = cats.get("location") or "India"

            jobs.append({
                "title": title,
                "location": loc,
                "department": cats.get("department") or cats.get("team") or "Corporate",
                "employment_type": cats.get("commitment"),
                "application_url": direct_url,
                "external_job_id": jid,
                "posted_date": str(item.get("createdAt", "")) if item.get("createdAt") else None,
                "job_description": item.get("descriptionPlain"),
                "raw_metadata": item,
                "link_quality": "DIRECT" if direct_url else "LISTING_FALLBACK",
                "link_check_note": "lever_hosted_url" if direct_url else "missing_direct_url",
            })
        return jobs

    # -------------------------------------------------------------------------
    # 2. Greenhouse Adapter
    # -------------------------------------------------------------------------
    def _extract_greenhouse(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        if not token or token in ("embed", "js", "api", "greenhouse"):
            for_m = re.search(r"[?&]for=([^&#]+)", url, re.I)
            if for_m:
                token = for_m.group(1)
            elif context.html_content:
                for_m = re.search(r"boards\.greenhouse\.io.*?[\?&]for=([a-zA-Z0-9_\-]+)", context.html_content, re.I)
                if for_m:
                    token = for_m.group(1)
            if not token:
                m = re.search(r"greenhouse\.io/([^/?#]+)", url, re.I)
                if m and m.group(1).lower() not in ("embed", "js", "api"):
                    token = m.group(1)
        if not token or token in ("embed", "js", "api", "greenhouse"):
            return []

        context.discovered_ats_platform = "Greenhouse"
        context.discovered_ats_token = token
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        resp = cffi_get(api_url)
        if not resp or resp.status_code != 200:
            return []

        try:
            data = resp.json()
        except Exception:
            return []

        jobs = []
        for item in data.get("jobs", []):
            title = clean_text(item.get("title"))
            jid = str(item.get("id", "")).strip() if item.get("id") else None
            if not title:
                continue

            direct_url = item.get("absolute_url") or (f"https://boards.greenhouse.io/{token}/jobs/{jid}" if jid else None)
            loc_data = item.get("location") or {}
            loc = loc_data.get("name") if isinstance(loc_data, dict) else "India"

            jobs.append({
                "title": title,
                "location": loc or "India",
                "department": "Corporate",
                "application_url": direct_url,
                "external_job_id": jid,
                "posted_date": str(item.get("updated_at", "")),
                "job_description": item.get("content"),
                "raw_metadata": item,
                "link_quality": "DIRECT" if direct_url else "LISTING_FALLBACK",
                "link_check_note": "greenhouse_absolute_url" if direct_url else "missing_direct_url",
            })
        return jobs

    # -------------------------------------------------------------------------
    # 3. Workday CXS Adapter with FULL Pagination
    # -------------------------------------------------------------------------
    def _extract_workday(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        if not host:
            return []
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]

        # Detect locale (e.g. en-US, en_US, en)
        locale = None
        remaining_parts = list(path_parts)
        if remaining_parts and re.match(r"^[a-z]{2}([-_][a-z]{2})?$", remaining_parts[0], re.I):
            locale = remaining_parts.pop(0)

        # Determine tenant and site
        sub = host.split(".")[0]
        is_generic_host = (sub.startswith("wd") and sub[2:].isdigit()) or sub == "myworkdayjobs"

        if is_generic_host:
            # Format: https://wd3.myworkdayjobs.com/<tenant>/<site>
            tenant = remaining_parts.pop(0) if remaining_parts else (token.split(":")[0] if token and ":" in token else "")
            site = remaining_parts.pop(0) if remaining_parts else "Careers"
        else:
            # Format: https://<tenant>.wd3.myworkdayjobs.com/<site> or https://<tenant>.myworkdayjobs.com/<site>
            tenant = sub
            if remaining_parts:
                if "job" in remaining_parts:
                    job_idx = remaining_parts.index("job")
                    site = remaining_parts[job_idx - 1] if job_idx > 0 else "Careers"
                else:
                    site = remaining_parts[0]
            else:
                site = "Careers"

        if not tenant:
            return []

        context.discovered_ats_platform = "Workday"
        context.discovered_ats_token = f"{tenant}:{site}"

        api_url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        jobs = []
        offset = 0
        limit = 25
        total: Optional[int] = None

        while True:
            # REMOVE hardcoded searchText filter so all active vacancies are discovered
            payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
            resp = cffi_post(api_url, json=payload)
            if not resp or resp.status_code != 200:
                break

            try:
                data = resp.json()
            except Exception:
                break

            if total is None:
                total = data.get("total", 0)

            postings = data.get("jobPostings", [])
            if not postings:
                break

            for item in postings:
                title = clean_text(item.get("title"))
                ext_path = item.get("externalPath") or ""
                if not title or not ext_path:
                    continue

                # Build exact direct URL with locale if present
                if locale:
                    direct_url = f"https://{host}/{locale}/{site}{ext_path}"
                else:
                    direct_url = f"https://{host}/{site}{ext_path}"

                # Extract external job ID from bulletFields or last segment
                ext_id = None
                bullet = item.get("bulletFields")
                if bullet and isinstance(bullet, list) and bullet[0]:
                    ext_id = str(bullet[0]).strip()
                if not ext_id:
                    ext_id = ext_path.strip("/").split("/")[-1]

                jobs.append({
                    "title": title,
                    "location": item.get("locationsText") or "India",
                    "department": "Corporate",
                    "employment_type": item.get("timeType"),
                    "application_url": direct_url,
                    "external_job_id": ext_id,
                    "posted_date": item.get("postedOn"),
                    "raw_metadata": item,
                    "link_quality": "DIRECT",
                    "link_check_note": "workday_cxs_direct",
                })

            offset += len(postings)
            if total is not None and total > 0:
                if offset >= total:
                    break
            elif len(postings) < limit:
                break
            if offset >= 2000:  # safety cap
                break
            time.sleep(0.15)

        return jobs

    # -------------------------------------------------------------------------
    # 4. SmartRecruiters Adapter with Full Pagination
    # -------------------------------------------------------------------------
    def _extract_smartrecruiters(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        if not token:
            dcr_m = re.search(r"[?&]dcr_ci=([^&#]+)", url, re.I)
            if dcr_m:
                token = dcr_m.group(1)
            else:
                m = re.search(r"smartrecruiters\.com/([^/?#]+)", url, re.I)
                if m and m.group(1) not in ("my-applications", "job", "postings"):
                    token = m.group(1)
        if not token:
            return []

        context.discovered_ats_platform = "SmartRecruiters"
        context.discovered_ats_token = token
        base_api = f"https://api.smartrecruiters.com/v1/companies/{token}/postings"

        jobs = []
        page = 0
        page_size = 50

        while True:
            resp = cffi_get(f"{base_api}?pageSize={page_size}&pageNumber={page}")
            if not resp or resp.status_code != 200:
                break

            try:
                data = resp.json()
            except Exception:
                break

            items = data.get("content", [])
            if not items:
                break

            for item in items:
                title = clean_text(item.get("name"))
                jid = clean_text(item.get("id"))
                if not title or not jid:
                    continue

                # Store canonical user-facing posting URL: jobs.smartrecruiters.com/<company>/<id>
                direct_url = f"https://jobs.smartrecruiters.com/{token}/{jid}"
                loc_dict = item.get("location") or {}
                loc = ", ".join(filter(None, [loc_dict.get("city"), loc_dict.get("country")])) or "India"

                jobs.append({
                    "title": title,
                    "location": loc,
                    "department": (item.get("department") or {}).get("label") or "Corporate",
                    "employment_type": (item.get("typeOfEmployment") or {}).get("label"),
                    "application_url": direct_url,
                    "external_job_id": jid,
                    "posted_date": item.get("releasedDate"),
                    "raw_metadata": item,
                    "link_quality": "DIRECT",
                    "link_check_note": "smartrecruiters_posting_id",
                })

            total_pages = data.get("totalPages", 1)
            page += 1
            if page >= total_pages or page > 20:
                break
            time.sleep(0.15)

        return jobs

    # -------------------------------------------------------------------------
    # 5. Darwinbox Adapter with Full Pagination & Verified Pattern
    # -------------------------------------------------------------------------
    def _extract_darwinbox(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        parsed = urlparse(url)
        base_host = f"{parsed.scheme}://{parsed.netloc}"
        context.discovered_ats_platform = "Darwinbox"
        context.discovered_ats_token = parsed.netloc

        jobs = []
        page = 1
        while page <= 25:
            api_url = f"{base_host}/ms/candidateapi/job?page={page}&limit=50"
            resp = cffi_get(api_url)
            if not resp or resp.status_code != 200:
                break

            try:
                data = resp.json()
            except Exception:
                break

            items = (
                data.get("message", {}).get("jobs")
                if isinstance(data.get("message"), dict)
                else (data.get("data") or data.get("jobs") or [])
            )
            if not isinstance(items, list) or not items:
                break

            for item in items:
                title = clean_text(item.get("title") or item.get("job_title"))
                jid = clean_text(str(item.get("id") or item.get("job_id") or ""))
                if not title or not jid:
                    continue

                direct_url = f"{base_host}/ms/candidate/careers/{jid}"
                loc = item.get("location") or item.get("city") or "India"

                jobs.append({
                    "title": title,
                    "location": loc,
                    "department": item.get("department") or "Corporate",
                    "employment_type": item.get("employment_type") or item.get("job_type"),
                    "application_url": direct_url,
                    "external_job_id": jid,
                    "posted_date": item.get("created_on") or item.get("posted_date"),
                    "raw_metadata": item,
                    "link_quality": "DIRECT",
                    "link_check_note": "darwinbox_detail_id",
                })

            if len(items) < 50:
                break
            page += 1
            time.sleep(0.15)

        return jobs

    # -------------------------------------------------------------------------
    # 6. SuccessFactors Adapter (OData & CSB Paginated, No 40 Cap)
    # -------------------------------------------------------------------------
    def _extract_successfactors(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        parsed = urlparse(url)
        base_portal = f"{parsed.scheme}://{parsed.netloc}"
        context.discovered_ats_platform = "SuccessFactors"
        context.discovered_ats_token = parsed.netloc

        jobs = []
        seen_urls = set()
        startrow = 0
        step = 25

        # Preserve query parameters (e.g. company=tatamotors) for multi-tenant portals
        from urllib.parse import parse_qsl, urlencode
        orig_params = dict(parse_qsl(parsed.query))

        while True:
            params = dict(orig_params)
            params["q"] = ""
            params["startrow"] = startrow
            search_url = f"{base_portal}/search/?{urlencode(params)}"
            resp = cffi_get(search_url)
            if not resp or resp.status_code != 200:
                if startrow == 0:
                    resp = cffi_get(url)
                    if not resp or resp.status_code != 200:
                        break
                else:
                    break

            soup = BeautifulSoup(resp.text, "lxml")
            new_found = 0

            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if "/job/" in href:
                    title = clean_text(a.get_text(" ", strip=True))
                    if not title or len(title) < 3:
                        continue

                    full_href = urljoin(resp.url, href)
                    canon = normalize_canonical_url(full_href) or full_href
                    if canon in seen_urls:
                        continue
                    seen_urls.add(canon)

                    # Extract req ID from href e.g. /job/<slug>/<reqId>/
                    m = re.search(r"/job/(?:[^/]+/)?(\d+)", href)
                    req_id = m.group(1) if m else None

                    parent_row = a.find_parent(["tr", "div", "li"])
                    loc = "India"
                    if parent_row:
                        loc_elem = parent_row.find(class_=re.compile(r"location|city|country", re.I))
                        if loc_elem:
                            loc = clean_text(loc_elem.get_text(" ", strip=True)) or "India"

                    jobs.append({
                        "title": title,
                        "location": loc,
                        "department": "Corporate",
                        "application_url": canon,
                        "external_job_id": req_id,
                        "raw_metadata": {"href": href, "req_id": req_id},
                        "link_quality": "DIRECT",
                        "link_check_note": "successfactors_csb_job_row",
                    })
                    new_found += 1

            if new_found == 0:
                break
            startrow += step
            if startrow >= 1000:  # Paginate until results end (up to 1,000 jobs)
                break
            time.sleep(0.15)

        return jobs

    # -------------------------------------------------------------------------
    # 7. Oracle Cloud HCM & Taleo Adapter
    # -------------------------------------------------------------------------
    def _extract_oracle(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        context.discovered_ats_platform = "Oracle_Cloud"
        parsed = urlparse(url)
        oracle_host = f"{parsed.scheme}://{parsed.netloc}"

        site_m = re.search(r"sites/(CX_\w+)", url, re.I)
        site_number = site_m.group(1) if site_m else "CX_1"

        jobs = []
        offset = 0
        limit = 25
        total: Optional[int] = None

        while True:
            finder = f"findReqs;siteNumber={site_number},limit={limit},offset={offset},sortBy=POSTING_DATES_DESC"
            api_url = (
                f"{oracle_host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
                f"?onlyData=true&expand=requisitionList&finder={finder}"
            )
            resp = cffi_get(api_url)
            if not resp or resp.status_code != 200:
                break

            try:
                data = resp.json()
            except Exception:
                break

            items = data.get("items", [])
            if not items:
                break

            if total is None:
                try:
                    total = int(items[0].get("TotalJobsCount", 0))
                except Exception:
                    total = None

            req_list = items[0].get("requisitionList", [])
            if not req_list:
                break

            for req in req_list:
                title = clean_text(req.get("Title"))
                req_id = req.get("Id")
                if not title or not req_id:
                    continue

                direct_url = f"{oracle_host}/hcmUI/CandidateExperience/en/sites/{site_number}/job/{req_id}"
                loc = req.get("PrimaryLocation") or "India"

                jobs.append({
                    "title": title,
                    "location": loc,
                    "department": req.get("Department") or req.get("JobFamily") or "Corporate",
                    "employment_type": req.get("JobSchedule") or req.get("Schedule"),
                    "application_url": direct_url,
                    "external_job_id": str(req_id),
                    "posted_date": req.get("PostedDate"),
                    "job_description": req.get("ShortDescriptionStr"),
                    "raw_metadata": req,
                    "link_quality": "DIRECT",
                    "link_check_note": "oracle_ce_requisition",
                })

            offset += len(req_list)
            if total is not None and total > 0:
                if offset >= total:
                    break
            elif len(req_list) < limit:
                break
            if offset >= 2000:
                break
            time.sleep(0.15)

        return jobs

    # -------------------------------------------------------------------------
    # 8. Recruitee Adapter
    # -------------------------------------------------------------------------
    def _extract_recruitee(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        if not token:
            m = re.search(r"([a-z0-9\-]+)\.recruitee\.com", url, re.I)
            if m:
                token = m.group(1)
        if not token:
            return []

        context.discovered_ats_platform = "Recruitee"
        context.discovered_ats_token = token
        api_url = f"https://{token}.recruitee.com/api/offers/"
        resp = cffi_get(api_url)
        if not resp or resp.status_code != 200:
            return []

        try:
            data = resp.json()
        except Exception:
            return []

        offers = data.get("offers", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
        jobs = []
        for offer in offers:
            title = clean_text(offer.get("title"))
            oid = str(offer.get("id", "")).strip() if offer.get("id") else None
            if not title:
                continue

            direct_url = offer.get("careers_url") or (f"https://{token}.recruitee.com/o/{offer.get('slug')}" if offer.get("slug") else None)
            loc = offer.get("location") or "India"

            jobs.append({
                "title": title,
                "location": loc,
                "department": offer.get("department") or "Corporate",
                "employment_type": offer.get("employment_type_code"),
                "application_url": direct_url,
                "external_job_id": oid,
                "posted_date": offer.get("created_at"),
                "raw_metadata": offer,
                "link_quality": "DIRECT" if direct_url else "LISTING_FALLBACK",
                "link_check_note": "recruitee_careers_url" if direct_url else "missing_direct_url",
            })
        return jobs

    # -------------------------------------------------------------------------
    # 9. Ashby Adapter
    # -------------------------------------------------------------------------
    def _extract_ashby(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        if not token:
            m = re.search(r"ashbyhq\.com/([^/?#]+)", url, re.I)
            if m:
                token = m.group(1)
        if not token:
            return []

        context.discovered_ats_platform = "Ashby"
        context.discovered_ats_token = token
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
        resp = cffi_post(api_url, json={})
        if not resp or resp.status_code != 200:
            return []

        try:
            data = resp.json()
        except Exception:
            return []

        jobs = []
        for item in data.get("jobs", []):
            title = clean_text(item.get("title"))
            jid = clean_text(item.get("id"))
            if not title:
                continue

            direct_url = item.get("jobUrl") or item.get("applyUrl") or (f"https://jobs.ashbyhq.com/{token}/{jid}" if jid else None)
            jobs.append({
                "title": title,
                "location": item.get("locationName") or "India",
                "department": item.get("departmentName") or "Corporate",
                "employment_type": item.get("employmentType"),
                "application_url": direct_url,
                "external_job_id": jid,
                "posted_date": item.get("publishedAt"),
                "raw_metadata": item,
                "link_quality": "DIRECT" if direct_url else "LISTING_FALLBACK",
                "link_check_note": "ashby_job_url" if direct_url else "missing_direct_url",
            })
        return jobs

    # -------------------------------------------------------------------------
    # 10. iCIMS Adapter
    # -------------------------------------------------------------------------
    def _extract_icims(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        context.discovered_ats_platform = "iCIMS"
        sep = "&" if "?" in url else "?"
        target = f"{url}{sep}in_iframe=1" if "in_iframe=1" not in url else url
        resp = cffi_get(target)
        if not resp or resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        jobs = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = re.search(r"/jobs/(\d+)/", href)
            if m:
                jid = m.group(1)
                title = clean_text(re.sub(r"^Job\s+Title\s*", "", a.get_text(" ", strip=True), flags=re.I))
                if not title or len(title) < 3 or jid in seen:
                    continue
                seen.add(jid)
                clean_url = urljoin(resp.url, href).replace("?in_iframe=1", "").replace("&in_iframe=1", "")
                jobs.append({
                    "title": title,
                    "location": "India",
                    "department": "Corporate",
                    "application_url": clean_url,
                    "external_job_id": jid,
                    "raw_metadata": {"id": jid, "href": href},
                    "link_quality": "DIRECT",
                    "link_check_note": "icims_detail_link",
                })
        return jobs

    # -------------------------------------------------------------------------
    # 11. Zoho Recruit Adapter
    # -------------------------------------------------------------------------
    def _extract_zohorecruit(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        context.discovered_ats_platform = "Zoho_Recruit"
        resp = cffi_get(url)
        if not resp or resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "lxml")
        jobs = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(k in href for k in ("/jobs/", "Job_Description", "careerportal", "job-detail")):
                title = clean_text(a.get_text(strip=True))
                if not title or len(title) < 3 or title.lower() in ("apply", "apply now", "view", "view all"):
                    continue
                full_url = urljoin(resp.url, href)
                canon = normalize_canonical_url(full_url) or full_url
                if canon in seen:
                    continue
                seen.add(canon)

                m = re.search(r"[?&]jobId=([^&#]+)|/jobs/(\d+)", href, re.I)
                jid = (m.group(1) or m.group(2)) if m else None

                jobs.append({
                    "title": title,
                    "location": "India",
                    "department": "Corporate",
                    "application_url": canon,
                    "external_job_id": jid,
                    "raw_metadata": {"href": href, "id": jid},
                    "link_quality": "DIRECT",
                    "link_check_note": "zohorecruit_job_url",
                })
        return jobs

    # -------------------------------------------------------------------------
    # 12. Keka Adapter
    # -------------------------------------------------------------------------
    def _extract_keka(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        parsed = urlparse(url)
        base_host = f"{parsed.scheme}://{parsed.netloc}"
        context.discovered_ats_platform = "Keka"
        api_url = f"{base_host}/careers/api/embedjobs/default"
        resp = cffi_get(api_url)
        if not resp or resp.status_code != 200:
            return []

        try:
            data = resp.json()
        except Exception:
            return []

        items = data if isinstance(data, list) else (data.get("data") or data.get("jobs") or [])
        jobs = []
        for item in items:
            title = clean_text(item.get("title"))
            jid = clean_text(str(item.get("id", "")))
            if not title or not jid:
                continue

            locs = item.get("jobLocations") or []
            loc_str = ", ".join(l.get("name", "") for l in locs if isinstance(l, dict) and l.get("name")) or "India"
            direct_url = f"{base_host}/careers/jobdetails/{jid}"

            jobs.append({
                "title": title,
                "location": loc_str,
                "department": item.get("departmentName") or "Corporate",
                "employment_type": item.get("jobType"),
                "application_url": direct_url,
                "external_job_id": jid,
                "posted_date": item.get("publishedOn"),
                "raw_metadata": item,
                "link_quality": "DIRECT",
                "link_check_note": "keka_job_details",
            })
        return jobs

    # -------------------------------------------------------------------------
    # 13. Freshteam Adapter
    # -------------------------------------------------------------------------
    def _extract_freshteam(self, url: str, token: Optional[str], context: ExtractionContext) -> List[Dict[str, Any]]:
        parsed = urlparse(url)
        base_host = f"{parsed.scheme}://{parsed.netloc}"
        context.discovered_ats_platform = "Freshteam"
        api_url = f"{base_host}/hire/widgets/jobs.json"
        resp = cffi_get(api_url)
        if not resp or resp.status_code != 200:
            return []

        try:
            data = resp.json()
        except Exception:
            return []

        items = data.get("jobs") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        jobs = []
        for item in items or []:
            title = clean_text(item.get("title"))
            jid = clean_text(str(item.get("id", "")))
            if not title:
                continue

            direct_url = item.get("url") or (f"{base_host}/jobs/{jid}" if jid else None)
            branch = item.get("branch") or {}
            loc_str = ", ".join(filter(None, [branch.get("city"), branch.get("state"), branch.get("country")])) or "India"

            jobs.append({
                "title": title,
                "location": loc_str,
                "department": (item.get("department") or {}).get("name") or "Corporate",
                "employment_type": item.get("type"),
                "application_url": direct_url,
                "external_job_id": jid,
                "posted_date": item.get("created_at"),
                "raw_metadata": item,
                "link_quality": "DIRECT" if direct_url else "LISTING_FALLBACK",
                "link_check_note": "freshteam_direct_url" if direct_url else "missing_direct_url",
            })
        return jobs


def dispatch_ats_direct(ats_platform: str, ats_url: str, tenant: Optional[str] = None) -> list:
    """
    Unified entry point for direct ATS extraction without browser rendering.
    """
    from modules.crawler_engine.crawler import dispatch_ats_direct as _crawler_dispatch
    return _crawler_dispatch(ats_platform, ats_url, tenant)
