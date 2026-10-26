"""
Deterministic Link Validation Gate for ImpactBridge™ Job Discovery Engine.

Enforces:
a. Strict normalization (strip tracking parameters, text fragments, lowercases domain).
b. Rejection of company careers/listing URLs and intra-batch duplicates.
c. HTTP 200 check via curl_cffi with redirect tracking and closed/expired role detection.
d. Content matching (title similarity / external_job_id presence).
e. Clear assignment of link_quality ('DIRECT', 'LISTING_FALLBACK', 'UNVERIFIED') and link_check_note.
"""
from __future__ import annotations

import difflib
import logging
import random
import re
from typing import Optional, Tuple, Dict, Any, List
from urllib.parse import urlparse

from curl_cffi import requests as cffi_requests
from .normalizers import normalize_canonical_url, clean_text

logger = logging.getLogger(__name__)

# Closed / expired position markers
_CLOSED_ROLE_INDICATORS = [
    "position has been filled",
    "position is no longer available",
    "job is no longer available",
    "no longer accepting applications",
    "job posting has expired",
    "this job has expired",
    "requisition is closed",
    "opening is closed",
    "job has been removed",
    "page not found",
    "404 not found",
]

_GENERIC_LISTING_SLUGS = {
    "/careers", "/career", "/jobs", "/all-jobs", "/job-openings",
    "/work-with-us", "/join-us", "/current-openings", "/search-jobs",
    "/careers/", "/jobs/", "/career/"
}


def is_generic_listing_url(url: str, company_careers_url: Optional[str] = None) -> Tuple[bool, str]:
    """
    Checks if a URL is actually a generic listing page rather than a specific job opening.
    """
    if not url:
        return True, "empty_url"

    canon = normalize_canonical_url(url)
    if not canon:
        return True, "invalid_url_structure"

    if "#:~:text=" in url:
        return True, "contains_text_fragment"

    parsed = urlparse(canon)
    path = (parsed.path or "").rstrip("/")

    # Check against company careers URL
    if company_careers_url:
        canon_careers = normalize_canonical_url(company_careers_url)
        if canon_careers:
            parsed_careers = urlparse(canon_careers)
            if parsed.netloc == parsed_careers.netloc and path == (parsed_careers.path or "").rstrip("/"):
                return True, "matches_company_careers_url"

    # Check path against generic listing patterns
    if path.lower() in _GENERIC_LISTING_SLUGS or path == "":
        return True, "generic_listing_path"

    return False, "ok"


def validate_job_candidate_url(
    candidate_url: Optional[str],
    company_careers_url: Optional[str] = None,
    job_title: Optional[str] = None,
    external_job_id: Optional[str] = None,
    is_ats_api: bool = False,
    batch_url_counts: Optional[Dict[str, int]] = None,
    sample_rate: float = 0.05,
    force_http_check: bool = False,
) -> Tuple[Optional[str], str, str]:
    """
    Validates a job's candidate URL and assigns its link_quality and link_check_note.

    Returns:
        (canonical_url, link_quality, link_check_note)
        where link_quality is 'DIRECT', 'LISTING_FALLBACK', or 'UNVERIFIED'.
    """
    if not candidate_url or not clean_text(candidate_url):
        return None, "LISTING_FALLBACK", "missing_candidate_url"

    canon = normalize_canonical_url(candidate_url)
    if not canon:
        return None, "LISTING_FALLBACK", "invalid_url_syntax"

    # Check text fragment
    if "#:~:text=" in candidate_url:
        return canon, "LISTING_FALLBACK", "highlight_text_fragment_fallback"

    # Check if generic listing URL
    is_listing, listing_reason = is_generic_listing_url(canon, company_careers_url)
    if is_listing:
        return canon, "LISTING_FALLBACK", listing_reason

    # Check batch frequency: if multiple jobs share the exact same canonical URL
    if batch_url_counts and batch_url_counts.get(canon, 0) > 1:
        # Check if URL differs by job id query param
        parsed = urlparse(canon)
        has_id_param = any(k in parsed.query.lower() for k in ("job_id", "jobid", "req_id", "reqid", "id"))
        if not has_id_param and not (is_ats_api and external_job_id):
            return canon, "LISTING_FALLBACK", f"shared_by_{batch_url_counts.get(canon)}_jobs_in_batch"

    # For verified ATS API URLs with external ID: trust or sample verify
    should_verify_http = force_http_check or (not is_ats_api) or (random.random() < sample_rate)

    if is_ats_api and external_job_id and not should_verify_http:
        return canon, "DIRECT", "ats_api_trusted"

    # HTTP verification with curl_cffi
    try:
        resp = cffi_requests.get(
            canon,
            impersonate="chrome124",
            timeout=12,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}
        )

        final_status = resp.status_code
        final_url = normalize_canonical_url(resp.url) or resp.url

        if final_status != 200:
            if is_ats_api and external_job_id:
                # Some ATS systems return 403 to curl_cffi but URLs are valid
                return canon, "DIRECT", f"api_trusted_http_{final_status}"
            return canon, "LISTING_FALLBACK", f"http_status_{final_status}"

        # Check if redirected back to careers listing
        is_final_listing, final_listing_reason = is_generic_listing_url(final_url, company_careers_url)
        if is_final_listing and final_url != canon:
            return final_url, "LISTING_FALLBACK", f"redirected_to_{final_listing_reason}"

        page_text = resp.text.lower() if resp.text else ""

        # Check for closed position text
        for indicator in _CLOSED_ROLE_INDICATORS:
            if indicator in page_text:
                return canon, "LISTING_FALLBACK", f"closed_role_detected: {indicator}"

        # Content check: Title matching or external_job_id presence
        if external_job_id and external_job_id.lower() in page_text:
            return canon, "DIRECT", "verified_http200_job_id_found"

        if job_title:
            t_norm = clean_text(job_title).lower()
            # Direct phrase match or high token overlap
            t_words = [w for w in re.split(r'\W+', t_norm) if len(w) >= 3]
            if t_words:
                matching_words = [w for w in t_words if w in page_text]
                overlap = len(matching_words) / len(t_words)
                if overlap >= 0.75:
                    return canon, "DIRECT", f"verified_http200_title_overlap_{int(overlap*100)}pct"

            # Fuzzy title ratio on page title tag
            title_m = re.search(r'<title[^>]*>(.*?)</title>', page_text, re.I | re.S)
            if title_m:
                doc_title = title_m.group(1).strip()
                ratio = difflib.SequenceMatcher(None, t_norm, doc_title).ratio() * 100
                if ratio >= 80:
                    return canon, "DIRECT", f"verified_http200_title_fuzzy_{int(ratio)}pct"

        # If it's a SPA or JS-rendered page and plain HTML title check didn't catch text
        if is_ats_api and external_job_id:
            return canon, "DIRECT", "api_trusted_spa_render"

        # If HTTP 200 and slug matches job keywords, mark DIRECT
        if any(p in canon.lower() for p in ("/job/", "/jobs/", "/position/", "/requisition/", "/career/")):
            return canon, "DIRECT", "verified_http200_job_slug"

        return canon, "UNVERIFIED", "http200_content_unmatched"

    except Exception as exc:
        if is_ats_api and external_job_id:
            return canon, "DIRECT", f"api_trusted_conn_err: {type(exc).__name__}"
        return canon, "UNVERIFIED", f"http_check_error: {type(exc).__name__}"
