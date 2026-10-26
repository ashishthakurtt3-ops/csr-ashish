import os
import logging
import json
import re
import hashlib
import time
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Any, Optional, Set, Tuple

logger = logging.getLogger(__name__)

from bs4 import BeautifulSoup
from curl_cffi import requests as cffi_requests
import trafilatura
import extruct

from django.db import transaction, connection, close_old_connections, models
from django.utils import timezone

from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, CompanyCrawlSummary
from .access_detector import fetch_live_page, DEFAULT_HEADERS
from .link_verifier import build_highlight_url, verify_url_live
from .semantic_matcher import score_link_semantics, probe_subdomains_and_paths, mine_sitemap_for_links
from .normalizers import clean_text, normalize_canonical_url, build_job_fingerprint
from .strategies.pipeline import StrategyPipeline

# Blacklist of navigation/footer garbage and action buttons that must NEVER be saved as a Job title
NAVBAR_BLACKLIST = {
    "careers", "career", "home", "about", "about us", "contact", "contact us",
    "login", "sign in", "sign-in", "register", "privacy policy", "terms of use", "terms & conditions",
    "cookie policy", "disclaimer", "sitemap", "read more", "view all", "know more",
    "learn more", "apply now", "apply", "search jobs", "job search", "explore opportunities",
    "skip to main content", "investor relations", "media", "newsroom", "csr policy",
    "sustainability", "overview", "our impact", "follow us", "download", "click here",
    "view all roles", "explore all roles", "see all roles", "find a job", "find jobs",
    "view openings", "search openings", "open positions", "current openings",
    "soar", "submit resume", "job alert", "join us", "work with us", "see openings",
    "view all jobs", "all jobs", "explore jobs", "search positions", "more details",
    "future ready", "performance driven", "purpose led", "leadership", "values",
    "our history", "our brands", "press releases", "calculator", "branch locator", "locator",
    "free credit score", "annual secretarial compliance", "shareholders", "investor services",
    "media centre", "customer service", "loss of share certificates", "odr portal"
}

GENERIC_BUTTON_PHRASES = re.compile(
    r'^(apply(\s+now)?|view(\s+all)?(\s+roles|\s+jobs)?|read\s+more|know\s+more|learn\s+more|explore(\s+opportunities|\s+careers)?|click\s+here|find\s+a\s+job|search(\s+jobs)?|join\s+our\s+team|submit\s+resume|more\s+details|details|future\s+ready|performance\s+driven|purpose\s+led)$',
    re.IGNORECASE
)

JOB_HREF_PATTERNS = re.compile(
    r'(/job/|/jobs/|/career[s]?/.+|jobid=|job_id=|requisition|opening[s]?/|vacancy|vacancies|positions?/|myworkdayjobs\.com|darwinbox\.(?:in|com)|smartrecruiters\.com|greenhouse\.io|lever\.co|keka\.com|zohorecruit|successfactors|peoplestrong\.com|icims\.com|ashbyhq\.com|oraclecloud\.com|taleo\.net)',
    re.IGNORECASE
)

ATS_DOMAINS = [
    "jobs.lever.co", "lever.co", "boards.greenhouse.io", "greenhouse.io",
    "myworkdayjobs.com", "darwinbox.in", "darwinbox.com", "successfactors.com",
    "successfactors.eu", "oraclecloud.com", "taleo.net", "smartrecruiters.com",
    "zohorecruit.com", "zohorecruit.in", "keka.com", "icims.com",
    "peoplestrong.com", "naukri.com", "ashbyhq.com", "freshteam.com",
    "mahindracareers.com", "tatamotorscareers"
]

SCHEDULE_VII_THEMES = {
    "Education & Skill Development": ["education", "school", "scholarship", "literacy", "digital classroom", "vocational", "skill development", "anganwadi", "stem", "shiksha", "vidya"],
    "Healthcare & Nutrition": ["healthcare", "health camp", "medical", "hospital", "sanitation", "hygiene", "nutrition", "malnutrition", "maternal", "telemedicine", "arogya", "drinking water"],
    "Environment & Sustainability": ["environment", "afforestation", "tree plantation", "water conservation", "watershed", "rainwater", "solar", "renewable", "biodiversity", "carbon", "waste management"],
    "Rural Development & Livelihood": ["rural development", "livelihood", "self-help group", "shg", "women empowerment", "farmer", "agriculture", "livestock", "village development", "micro-enterprise"],
}

CSR_STATUTORY_MARKERS = re.compile(
    r'(section\s*135|schedule\s*vii|csr\s*(?:expenditure|budget|project|initiative|committee|foundation|report|action\s*plan)|implementing\s*agency|beneficiar(?:y|ies)|(?:inr|rs\.?|₹)\s*\d[\d,]*(?:\.\d+)?\s*(?:crore|cr\.?|lakh|million)?)',
    re.IGNORECASE
)

# Strict Budget Regex: MUST require at least one digit \d after currency symbol
CSR_BUDGET_REGEX = re.compile(
    r'(?:INR|Rs\.?|₹)\s*\d[\d,]*(?:\.\d+)?\s*(?:Crore|Cr\.?|Lakh|Million|Billion)?',
    re.IGNORECASE
)

COMMON_INDIAN_LOCATIONS = [
    "mumbai", "bengaluru", "bangalore", "delhi", "new delhi", "hyderabad", "pune",
    "chennai", "kolkata", "noida", "gurgaon", "gurugram", "ahmedabad", "jaipur",
    "kochi", "coimbatore", "chandigarh", "indore", "surat", "vadodara", "nagpur",
    "lucknow", "bhopal", "visakhapatnam", "thiruvananthapuram", "trivandrum",
    "remote", "hybrid", "on-site", "india"
]


def discover_company_official_links(domain_url: str) -> dict:
    """
    Discovers official Careers and CSR deep links using a 3-layer architecture:
    1. Multi-Path & Subdomain Probing Matrix (careers.<domain>, jobs.<domain>, /careers, /sustainability, etc.)
    2. XML Sitemap Mining (/sitemap.xml) scored with local semantic similarity
    3. Live Homepage DOM Link Extraction with local TF-IDF / sentence-transformers scoring
    """
    if not domain_url:
        return {"careers_url": None, "csr_url": None, "error": "No domain provided"}

    if not domain_url.startswith(("http://", "https://")):
        domain_url = f"https://{domain_url}"

    careers_candidates = []
    csr_candidates = []

    # Layer 1: Multi-Subdomain & Path Probing Matrix
    try:
        probed = probe_subdomains_and_paths(domain_url)
        if probed.get("careers_url"):
            careers_candidates.append((0.95, probed["careers_url"]))
        if probed.get("csr_url"):
            csr_candidates.append((0.95, probed["csr_url"]))
    except Exception as e:
        logger.debug("Subdomain probing error: %s", e)

    # Layer 2: XML Sitemap Mining (/sitemap.xml)
    try:
        sitemap_links = mine_sitemap_for_links(domain_url)
        if sitemap_links.get("careers_url"):
            careers_candidates.append((0.90, sitemap_links["careers_url"]))
        if sitemap_links.get("csr_url"):
            csr_candidates.append((0.90, sitemap_links["csr_url"]))
    except Exception as e:
        logger.debug("Sitemap mining error: %s", e)

    # Layer 3: Homepage DOM Scrape & Semantic Link Scoring
    res = fetch_live_page(domain_url)
    if res["ok"]:
        soup = BeautifulSoup(res["html"], "lxml")
        base_url = res["final_url"]

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            full_url = urljoin(base_url, href)
            text = re.sub(r'\s+', ' ', a.get_text(" ", strip=True)).strip()
            if not text and not href:
                continue

            probe_text = f"{text} {urlparse(full_url).path}"

            career_score = score_link_semantics(probe_text, "careers")
            if any(ats in full_url.lower() for ats in ATS_DOMAINS):
                career_score += 0.35
            if any(k in text.lower() for k in ["career", "careers", "jobs", "work with us", "join us", "openings"]):
                career_score += 0.25

            if career_score >= 0.40:
                careers_candidates.append((career_score, full_url))

            csr_score = score_link_semantics(probe_text, "csr")
            if any(k in text.lower() for k in ["csr", "sustainability", "social responsibility", "foundation", "esg", "brsr"]):
                csr_score += 0.30

            if csr_score >= 0.40:
                csr_candidates.append((csr_score, full_url))

    careers_candidates.sort(key=lambda x: x[0], reverse=True)
    csr_candidates.sort(key=lambda x: x[0], reverse=True)

    return {
        "careers_url": careers_candidates[0][1] if careers_candidates else None,
        "csr_url": csr_candidates[0][1] if csr_candidates else None,
        "error": None
    }


# ==============================================================================
# SPECIALIZED ATS JSON & HTML ADAPTERS
# ==============================================================================

def try_fetch_lever_jobs(url: str) -> list:
    """
    Extracts 100% of jobs from Lever job boards (e.g. jobs.lever.co/paytm).
    Hits the official public JSON API `api.lever.co/v0/postings/<token>?mode=json`
    or parses Lever HTML cards if JSON is unavailable.
    """
    parsed = urlparse(url)
    if "lever.co" not in parsed.netloc.lower():
        return []

    token = None
    parts = [p for p in parsed.path.split('/') if p]
    if parts:
        token = parts[0]
    if not token or token in ('postings', 'v0'):
        return []

    # 1. Official Lever JSON API
    api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    try:
        resp = cffi_requests.get(api_url, impersonate="chrome124", timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                jobs = []
                for item in data:
                    title = (item.get("text") or "").strip()
                    if not title or GENERIC_BUTTON_PHRASES.match(title) or title.lower() in NAVBAR_BLACKLIST:
                        continue
                    app_url = item.get("hostedUrl") or item.get("applyUrl") or f"https://jobs.lever.co/{token}/{item.get('id')}"
                    cats = item.get("categories") or {}
                    loc = cats.get("location") or "India"
                    dept = cats.get("department") or cats.get("team") or "Corporate"
                    jobs.append({
                        "title": title,
                        "location": loc,
                        "department": dept,
                        "apply_url": app_url,
                        "posted_on": str(item.get("createdAt", "")),
                        "verbatim_quote": f"{title} - {loc} ({dept})",
                        "verification_status": "PUBLISHED"
                    })
                if jobs:
                    return jobs
    except Exception:
        pass

    # 2. HTML Fallback for Lever
    try:
        resp = cffi_requests.get(url, impersonate="chrome124", timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            jobs = []
            for post in soup.find_all("div", class_="posting"):
                title_elem = post.find(["h5", "a"], {"data-qa": "posting-name"}) or post.find("h5")
                title = title_elem.get_text(strip=True) if title_elem else ""
                link_elem = post.find("a", class_="posting-title") or post.find("a", href=True)
                apply_url = urljoin(url, link_elem["href"]) if link_elem and link_elem.get("href") else url
                loc_elem = post.find("span", class_="sort-by-time") or post.find(class_=re.compile(r"location", re.I))
                loc = loc_elem.get_text(strip=True) if loc_elem else "India"
                if title and not GENERIC_BUTTON_PHRASES.match(title) and title.lower() not in NAVBAR_BLACKLIST:
                    jobs.append({
                        "title": title,
                        "location": loc,
                        "department": "Corporate",
                        "apply_url": apply_url,
                        "posted_on": "",
                        "verbatim_quote": f"{title} - {loc}",
                        "verification_status": "PUBLISHED"
                    })
            if jobs:
                return jobs
    except Exception:
        pass

    return []


def try_fetch_greenhouse_jobs(url: str) -> list:
    """
    Extracts jobs from Greenhouse Boards API (boards.greenhouse.io/<token>).
    """
    parsed = urlparse(url)
    if "greenhouse.io" not in parsed.netloc.lower():
        return []

    token = None
    for_match = re.search(r'[?&]for=([^&#]+)', url, re.IGNORECASE)
    if for_match:
        token = for_match.group(1)
    if not token:
        m = re.search(r'greenhouse\.io/([^/?#]+)', url, re.IGNORECASE)
        if m and m.group(1) not in ('embed', 'js', 'api'):
            token = m.group(1)
    if not token:
        return []

    api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    try:
        resp = cffi_requests.get(api_url, impersonate="chrome124", timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            jobs = []
            for item in data.get("jobs", []):
                title = (item.get("title") or "").strip()
                if not title or GENERIC_BUTTON_PHRASES.match(title) or title.lower() in NAVBAR_BLACKLIST:
                    continue
                app_url = item.get("absolute_url") or f"https://boards.greenhouse.io/{token}/jobs/{item.get('id')}"
                loc_data = item.get("location", {})
                loc = loc_data.get("name") if isinstance(loc_data, dict) else "India"
                jobs.append({
                    "title": title,
                    "location": loc or "India",
                    "department": "Corporate",
                    "apply_url": app_url,
                    "posted_on": str(item.get("updated_at", "")),
                    "verbatim_quote": f"{title} - {loc}",
                    "verification_status": "PUBLISHED"
                })
            return jobs
    except Exception:
        pass
    return []


def try_fetch_workday_json(careers_url: str) -> list:
    """
    Direct Workday JSON API Extractor.
    Matches URLs like https://<tenant>.wd3.myworkdayjobs.com/<en-US>/<site>
    """
    parsed = urlparse(careers_url)
    if "myworkdayjobs.com" not in parsed.netloc.lower():
        return []
    tenant = parsed.netloc.split(".")[0]
    path_parts = [p for p in parsed.path.split("/") if p]
    if not path_parts:
        return []
    site = path_parts[-1]
    api_url = f"{parsed.scheme}://{parsed.netloc}/wday/cxs/{tenant}/{site}/jobs"
    try:
        # Full pagination — no 25-job cap
        jobs = []
        offset = 0
        limit = 25
        total = None
        while True:
            resp = cffi_requests.post(
                api_url,
                impersonate="chrome124",
                json={"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=20
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            if total is None:
                total = data.get("total", 0)
            postings = data.get("jobPostings", [])
            if not postings:
                break
            for item in postings:
                title = (item.get("title") or "").strip()
                ext_path = item.get("externalPath") or ""
                if not title or not ext_path or GENERIC_BUTTON_PHRASES.match(title) or title.lower() in NAVBAR_BLACKLIST:
                    continue
                job_url = f"{parsed.scheme}://{parsed.netloc}/{site}{ext_path}"
                jobs.append({
                    "title": title,
                    "location": item.get("locationsText") or "India",
                    "department": "Corporate",
                    "apply_url": job_url,
                    "posted_on": item.get("postedOn") or "",
                    "verbatim_quote": f"{title} - {item.get('locationsText', 'Workday Portal')}",
                    "verification_status": "PUBLISHED"
                })
            offset += len(postings)
            if total and offset >= total:
                break
            if len(postings) < limit:
                break
            if offset >= 2000:  # absolute safety cap
                break
            import time as _time
            _time.sleep(0.15)
        return jobs
    except Exception:
        pass
    return []


def try_fetch_smartrecruiters_jobs(url: str) -> list:
    """
    SmartRecruiters public postings API.
    """
    parsed = urlparse(url)
    if "smartrecruiters.com" not in parsed.netloc.lower():
        return []

    token = None
    m = re.search(r'smartrecruiters\.com/([^/?#]+)', url, re.I)
    if m and m.group(1) not in ('my-applications', 'job', 'postings'):
        token = m.group(1)
    if not token:
        return []

    api_url = f"https://api.smartrecruiters.com/v1/companies/{token}/postings?pageSize=50"
    try:
        resp = cffi_requests.get(api_url, impersonate="chrome124", timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            jobs = []
            for item in data.get("content", []):
                title = (item.get("name") or "").strip()
                if not title or GENERIC_BUTTON_PHRASES.match(title) or title.lower() in NAVBAR_BLACKLIST:
                    continue
                jid = item.get("id")
                app_url = f"https://jobs.smartrecruiters.com/{token}/{jid}" if jid else url
                loc_dict = item.get("location") or {}
                loc = ", ".join(filter(None, [loc_dict.get("city"), loc_dict.get("country")])) or "India"
                jobs.append({
                    "title": title,
                    "location": loc,
                    "department": (item.get("department") or {}).get("label") or "Corporate",
                    "apply_url": app_url,
                    "posted_on": item.get("releasedDate") or "",
                    "verbatim_quote": f"{title} - {loc}",
                    "verification_status": "PUBLISHED"
                })
            return jobs
    except Exception:
        pass
    return []


def try_fetch_darwinbox_jobs(url: str) -> list:
    """
    Darwinbox candidate API and listing parser (*.darwinbox.in / *.darwinbox.com).
    """
    parsed = urlparse(url)
    if "darwinbox" not in parsed.netloc.lower():
        return []

    base_host = f"{parsed.scheme}://{parsed.netloc}"
    api_url = f"{base_host}/ms/candidateapi/job?page=1&limit=50"
    try:
        resp = cffi_requests.get(api_url, impersonate="chrome124", timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            items = (data.get("message", {}) if isinstance(data.get("message"), dict) else data).get("jobs") or data.get("data") or []
            jobs = []
            for item in items:
                title = (item.get("title") or item.get("job_title") or "").strip()
                jid = item.get("id") or item.get("job_id")
                if not title or not jid or GENERIC_BUTTON_PHRASES.match(title) or title.lower() in NAVBAR_BLACKLIST:
                    continue
                loc = item.get("location") or item.get("city") or "India"
                app_url = f"{base_host}/ms/candidate/careers/{jid}"
                jobs.append({
                    "title": title,
                    "location": loc,
                    "department": item.get("department") or "Corporate",
                    "apply_url": app_url,
                    "posted_on": item.get("created_on") or "",
                    "verbatim_quote": f"{title} - {loc}",
                    "verification_status": "PUBLISHED"
                })
            if jobs:
                return jobs
    except Exception:
        pass
    return []


def try_fetch_successfactors_jobs(url: str) -> list:
    """
    SAP SuccessFactors / Career Site Builder (e.g. jobs.mahindracareers.com).
    Inspects search subpaths /search/ or query parameters to extract individual /job/ postings
    with full pagination up to 40 jobs.
    """
    parsed = urlparse(url)
    is_sf = any(k in url.lower() for k in ["successfactors", "mahindracareers.com", "tatamotorscareers", "heromotocorp"])
    if not is_sf:
        return []

    base_portal = f"{parsed.scheme}://{parsed.netloc}"
    jobs = []
    seen_urls = set()

    for startrow in (0, 25):
        search_url = f"{base_portal}/search/?q=&startrow={startrow}"
        try:
            resp = cffi_requests.get(search_url, impersonate="chrome124", timeout=20)
            if resp.status_code != 200 and startrow == 0:
                resp = cffi_requests.get(url, impersonate="chrome124", timeout=20)

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                page_found = 0
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if "/job/" in href:
                        title = a.get_text(" ", strip=True)
                        if not (4 <= len(title) <= 120):
                            continue
                        if GENERIC_BUTTON_PHRASES.match(title) or title.lower() in NAVBAR_BLACKLIST:
                            continue
                        full_href = urljoin(resp.url, href)
                        if full_href in seen_urls:
                            continue
                        seen_urls.add(full_href)

                        parent_row = a.find_parent(["tr", "div", "li"])
                        loc = "India"
                        if parent_row:
                            loc_elem = parent_row.find(class_=re.compile(r'location|city|country', re.I))
                            if loc_elem:
                                loc = loc_elem.get_text(" ", strip=True)

                        jobs.append({
                            "title": title,
                            "location": loc,
                            "department": "Corporate Openings",
                            "apply_url": build_highlight_url(full_href, title),
                            "verbatim_quote": f"Verified SuccessFactors Opening: {title} ({loc})",
                            "verification_status": "PUBLISHED"
                        })
                        page_found += 1
                if page_found == 0:
                    break
        except Exception:
            break

    return jobs


def try_fetch_oracle_jobs(url: str) -> list:
    """
    Direct Oracle Cloud HCM / Taleo career portal extractor.
    """
    lower = url.lower()
    if not ("oraclecloud.com" in lower or "taleo.net" in lower or "oracle" in lower):
        return []
    try:
        resp = cffi_requests.get(url, impersonate="chrome124", timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            jobs = []
            seen_titles = set()
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if any(p in href.lower() for p in ["/job/", "jobdetail", "requisition", "careersection", "job_detail"]):
                    title = a.get_text(" ", strip=True)
                    if 4 <= len(title) <= 120 and title.lower() not in seen_titles:
                        if not GENERIC_BUTTON_PHRASES.match(title) and title.lower() not in NAVBAR_BLACKLIST:
                            seen_titles.add(title.lower())
                            full_url = urljoin(url, href)
                            jobs.append({
                                "title": title,
                                "location": "India",
                                "department": "Corporate",
                                "apply_url": build_highlight_url(full_url, title),
                                "posted_on": "",
                                "verbatim_quote": f"Verified Oracle Opening: {title}",
                                "verification_status": "SOURCE_CONFIRMED"
                            })
            if jobs:
                return jobs
    except Exception:
        pass
    return []


def try_dispatch_specialized_ats(url: str) -> list:
    """Dispatches URL to any specialized ATS API extractor."""
    lower = url.lower()
    if "lever.co" in lower:
        return try_fetch_lever_jobs(url)
    if "greenhouse.io" in lower:
        return try_fetch_greenhouse_jobs(url)
    if "myworkdayjobs.com" in lower:
        return try_fetch_workday_json(url)
    if "smartrecruiters.com" in lower:
        return try_fetch_smartrecruiters_jobs(url)
    if "darwinbox" in lower:
        return try_fetch_darwinbox_jobs(url)
    if any(k in lower for k in ["successfactors", "mahindracareers.com", "tatamotorscareers", "heromotocorp"]):
        return try_fetch_successfactors_jobs(url)
    if "oraclecloud.com" in lower or "taleo.net" in lower:
        return try_fetch_oracle_jobs(url)
    return []


# ==============================================================================
# REPEATING DOM SIBLING CARD DETECTOR (Step 4.3)
# ==============================================================================

def detect_repeating_dom_job_cards(soup: BeautifulSoup, page_url: str) -> List[Dict[str, Any]]:
    """
    Detects repeating HTML structures (sibling cards) representing job listings
    on any custom careers portal without hardcoded keywords.
    Ensures container is NOT a header/nav/footer or megamenu.
    """
    jobs = []
    seen_urls = set()
    seen_titles = set()

    # Reject header, nav, footer, menu parents
    candidate_parents = []
    for tag in soup.find_all(["ul", "ol", "tbody", "section", "div"]):
        parent_tag_names = [p.name for p in tag.parents]
        if any(bad in parent_tag_names for bad in ["header", "nav", "footer"]):
            continue
        tag_classes = " ".join(tag.get("class", [])).lower()
        if any(bad in tag_classes for bad in ["menu", "nav", "footer", "header", "dropdown"]):
            continue
        candidate_parents.append(tag)

    for parent in candidate_parents:
        children = [c for c in parent.find_all(recursive=False) if getattr(c, 'name', None)]
        if len(children) < 3:
            continue

        sig_groups: Dict[Tuple[str, str], list] = {}
        for child in children:
            classes = " ".join(sorted(child.get("class", [])))
            sig = (child.name, classes)
            sig_groups.setdefault(sig, []).append(child)

        for sig, group in sig_groups.items():
            if len(group) < 3:
                continue

            group_jobs = []
            for card in group:
                heading = card.find(["h2", "h3", "h4", "h5", "strong"])
                link = card.find("a", href=True)

                title_text = ""
                apply_url = ""

                if heading:
                    title_text = heading.get_text(" ", strip=True)
                    h_link = heading.find("a", href=True)
                    if h_link:
                        apply_url = urljoin(page_url, h_link["href"])
                    elif link:
                        apply_url = urljoin(page_url, link["href"])
                elif link:
                    title_text = link.get_text(" ", strip=True)
                    apply_url = urljoin(page_url, link["href"])

                title_clean = re.sub(r'\s+', ' ', title_text).strip()

                if not (5 <= len(title_clean) <= 120):
                    continue
                if GENERIC_BUTTON_PHRASES.match(title_clean) or title_clean.lower() in NAVBAR_BLACKLIST:
                    continue
                if not apply_url or apply_url.startswith(("javascript:", "mailto:", "tel:", "#")):
                    continue

                # Ensure apply_url looks like a job posting rather than a generic top-level service
                p_app = urlparse(apply_url)
                if p_app.path.strip("/") in ("", "careers", "career", "home"):
                    continue

                card_text = card.get_text(" ", strip=True).lower()
                matched_loc = "India"
                for city in COMMON_INDIAN_LOCATIONS:
                    if city in card_text:
                        matched_loc = city.title()
                        break

                if apply_url not in seen_urls and title_clean.lower() not in seen_titles:
                    seen_urls.add(apply_url)
                    seen_titles.add(title_clean.lower())
                    group_jobs.append({
                        "title": title_clean,
                        "location": matched_loc,
                        "department": "Corporate Openings",
                        "apply_url": build_highlight_url(apply_url, title_clean),
                        "verbatim_quote": f"Verified Job Opening on {page_url}: {title_clean} ({matched_loc})",
                        "verification_status": "PUBLISHED"
                    })

            if len(group_jobs) >= 3:
                jobs.extend(group_jobs)
                return jobs

    return jobs


# ==============================================================================
# HOP-2 ATS / JOB PORTAL LINK DISCOVERY
# ==============================================================================

def find_hop2_ats_links(soup: BeautifulSoup, base_url: str) -> List[Tuple[float, str]]:
    """
    Scans a career page HTML for Outbound ATS Boards or Job Portal URLs.
    Scores candidates using domain reputation and character n-gram cosine similarity.
    """
    candidates = []
    seen = set()

    for a in soup.find_all(["a", "iframe"]):
        href = (a.get("href") or a.get("src") or "").strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        full_href = urljoin(base_url, href)
        if full_href.rstrip("/") == base_url.rstrip("/"):
            continue

        lower_href = full_href.lower()
        link_text = re.sub(r'\s+', ' ', a.get_text(" ", strip=True)).strip()

        score = 0.0
        # Priority 1: Direct recognized ATS domain
        if any(ats in lower_href for ats in ATS_DOMAINS):
            score += 0.85
        elif any(sub in lower_href for sub in ["jobs.", "careers."]) and urlparse(full_href).netloc != urlparse(base_url).netloc:
            score += 0.65

        # Priority 2: Call-to-action button semantic similarity (View All Roles, Find Jobs, Explore)
        hop2_sim = score_link_semantics(f"{link_text} {urlparse(full_href).path}", "hop2")
        if hop2_sim >= 0.55:
            score += hop2_sim

        if any(k in link_text.lower() for k in ["view all", "find a job", "find jobs", "explore opportunities", "search openings", "search jobs", "open roles"]):
            score += 0.35

        if score >= 0.60 and full_href not in seen:
            seen.add(full_href)
            candidates.append((score, full_href))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates


CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
if not os.path.exists(CHROME_PATH):
    CHROME_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def _extract_jobs_from_json_blob(data: Any, source_url: str, out_jobs: List[Dict[str, Any]], depth: int = 0):
    if depth > 4 or not data:
        return
    if isinstance(data, list):
        for item in data:
            _extract_jobs_from_json_blob(item, source_url, out_jobs, depth + 1)
    elif isinstance(data, dict):
        title = data.get("title") or data.get("jobTitle") or data.get("name") or data.get("role") or data.get("positionTitle") or data.get("requisitionTitle")
        if isinstance(title, str) and 5 <= len(title.strip()) <= 120:
            title_clean = re.sub(r'\s+', ' ', title).strip()
            if not GENERIC_BUTTON_PHRASES.match(title_clean) and title_clean.lower() not in NAVBAR_BLACKLIST:
                loc = data.get("location") or data.get("locationName") or data.get("city") or data.get("jobLocation")
                if isinstance(loc, dict):
                    loc = loc.get("name") or loc.get("city") or loc.get("addressLocality") or "India"
                elif not loc or not isinstance(loc, str):
                    loc = "India"
                dept = data.get("department") or data.get("businessUnit") or data.get("function") or data.get("category") or "Corporate Openings"
                if not isinstance(dept, str):
                    dept = "Corporate Openings"
                app_url = data.get("absolute_url") or data.get("url") or data.get("applyUrl") or data.get("externalUrl") or data.get("link")
                if not app_url or not isinstance(app_url, str):
                    job_id = data.get("id") or data.get("jobId") or data.get("requisitionId")
                    if job_id:
                        app_url = urljoin(source_url, f"?job_id={job_id}")
                    else:
                        app_url = source_url
                else:
                    app_url = urljoin(source_url, app_url)

                out_jobs.append({
                    "title": title_clean,
                    "location": str(loc)[:60],
                    "department": str(dept)[:60],
                    "apply_url": build_highlight_url(app_url, title_clean),
                    "verbatim_quote": f"Verified Job Opening via ATS API: {title_clean} ({loc})",
                    "verification_status": "PUBLISHED"
                })
                return

        for k, v in data.items():
            if isinstance(v, (dict, list)):
                _extract_jobs_from_json_blob(v, source_url, out_jobs, depth + 1)


def render_spa_page_with_playwright(url: str, timeout_ms: int = 15000) -> Dict[str, Any]:
    """
    Low-RAM, Single-Tab headless Chromium SPA renderer with network interception.
    Blocks images, media, and fonts to keep RAM < 150MB. Intercepts JSON job APIs.
    """
    from playwright.sync_api import sync_playwright

    intercepted_jobs: List[Dict[str, Any]] = []
    rendered_html = ""
    iframe_urls: List[str] = []
    final_url = url

    try:
        with sync_playwright() as p:
            launch_args = [
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
                "--blink-settings=imagesEnabled=false",
            ]
            launch_kwargs = {"headless": True, "args": launch_args}
            if os.path.exists(CHROME_PATH):
                launch_kwargs["executable_path"] = CHROME_PATH

            browser = p.chromium.launch(**launch_kwargs)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = context.new_page()

            def _block_assets(route):
                req = route.request
                if req.resource_type in ["image", "media", "font"]:
                    route.abort()
                else:
                    route.continue_()

            page.route("**/*", _block_assets)

            def _on_response(response):
                try:
                    r_url = response.url.lower()
                    ct = response.headers.get("content-type", "").lower()
                    if "json" in ct or any(k in r_url for k in ["job", "career", "opening", "requisition", "position", "posting", "search"]):
                        text_data = response.text()
                        if text_data:
                            data = json.loads(text_data)
                            _extract_jobs_from_json_blob(data, response.url, intercepted_jobs)
                except Exception:
                    pass

            page.on("response", _on_response)

            try:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                final_url = page.url
                page.wait_for_timeout(2500)

                for btn_text in ["View Jobs", "Current Openings", "Explore Careers", "Search Jobs", "Open Positions", "View All Jobs", "Search"]:
                    try:
                        btn = page.get_by_role("button", name=re.compile(btn_text, re.I))
                        if btn.is_visible(timeout=500):
                            btn.click(timeout=1000)
                            page.wait_for_timeout(1500)
                            break
                    except Exception:
                        pass

                for frame in page.frames:
                    if frame != page.main_frame and frame.url and not frame.url.startswith("about:"):
                        iframe_urls.append(frame.url)

                rendered_html = page.content()
            finally:
                context.close()
                browser.close()
    except Exception as e:
        logger.debug(f"Playwright SPA render error for {url}: {e}")

    return {
        "final_url": final_url,
        "html": rendered_html,
        "intercepted_jobs": intercepted_jobs,
        "iframe_urls": iframe_urls
    }


def extract_genuine_jobs_live(careers_url: str, hop: int = 1) -> dict:
    """
    Executes the 2-Hop ATS Deep Following & Deterministic Extraction Pipeline:
    Step 1: Check if careers_url itself matches a known ATS adapter.
    Step 2: If hop == 1, scan for Outbound ATS / Job Portal links.
            If an Outbound ATS exists, follow that Hop-2 link FIRST!
    Step 3: Fall back to JSON-LD, repeating DOM sibling cards, or verified anchor links.
    """
    # Step 1: Direct ATS check
    direct_ats_jobs = try_dispatch_specialized_ats(careers_url)
    if direct_ats_jobs:
        return {
            "access_status": "PUBLIC_OK",
            "jobs": direct_ats_jobs,
            "confirmed_zero": False,
            "error": None,
            "final_url": careers_url
        }

    page_res = fetch_live_page(careers_url)
    if not page_res["ok"]:
        return {
            "access_status": page_res["access_status"],
            "jobs": [],
            "error": page_res["error"],
            "final_url": page_res.get("final_url", careers_url)
        }

    final_url = page_res["final_url"]
    html = page_res["html"]
    soup = BeautifulSoup(html, "lxml")

    # Step 2: 2-HOP DEEP ATS FOLLOWING (Priority 1 on landing pages)
    if hop == 1:
        hop2_candidates = find_hop2_ats_links(soup, final_url)
        for _, target_hop2 in hop2_candidates[:3]:
            # Try specialized ATS parser directly on Hop-2 link
            ats_hop2_jobs = try_dispatch_specialized_ats(target_hop2)
            if ats_hop2_jobs:
                return {
                    "access_status": "PUBLIC_OK",
                    "jobs": ats_hop2_jobs,
                    "confirmed_zero": False,
                    "error": None,
                    "final_url": target_hop2,
                }
            # Otherwise crawl Hop 2 recursively
            hop2_result = extract_genuine_jobs_live(target_hop2, hop=2)
            if hop2_result.get("jobs"):
                return {
                    "access_status": "PUBLIC_OK",
                    "jobs": hop2_result["jobs"],
                    "confirmed_zero": False,
                    "error": None,
                    "final_url": hop2_result.get("final_url", target_hop2),
                }

    # Step 3: Layer 2 - Schema.org JobPosting JSON-LD via extruct
    extracted_jobs = []
    seen_urls = set()
    seen_titles = set()
    try:
        metadata = extruct.extract(html, base_url=final_url, syntaxes=["json-ld"])
        for ld in metadata.get("json-ld", []):
            items = ld if isinstance(ld, list) else [ld]
            for item in items:
                if isinstance(item, dict) and item.get("@type") == "JobPosting":
                    title = (item.get("title") or "").strip()
                    if not title or GENERIC_BUTTON_PHRASES.match(title) or title.lower() in NAVBAR_BLACKLIST:
                        continue
                    raw_url = item.get("url") or item.get("sameAs") or final_url
                    apply_url = urljoin(final_url, raw_url)
                    if title and apply_url not in seen_urls:
                        seen_urls.add(apply_url)
                        loc = "India"
                        job_loc = item.get("jobLocation")
                        if isinstance(job_loc, dict):
                            loc = job_loc.get("address", {}).get("addressLocality", "India")
                        extracted_jobs.append({
                            "title": title,
                            "location": str(loc),
                            "department": item.get("occupationalCategory") or "General",
                            "apply_url": build_highlight_url(apply_url, title),
                            "verbatim_quote": (item.get("description") or title)[:220],
                            "verification_status": "PUBLISHED"
                        })
    except Exception:
        pass

    # Step 4: Layer 3 - Repeating DOM Sibling Card Detector
    if not extracted_jobs:
        dom_jobs = detect_repeating_dom_job_cards(soup, final_url)
        if dom_jobs:
            extracted_jobs.extend(dom_jobs)

    # Step 5: Layer 4 - Individual Job Anchor Links
    if not extracted_jobs:
        for a in soup.find_all("a", href=True):
            raw_text = re.sub(r'\s+', ' ', a.get_text(" ", strip=True)).strip()
            if not (5 <= len(raw_text) <= 120):
                continue
            if GENERIC_BUTTON_PHRASES.match(raw_text) or raw_text.lower() in NAVBAR_BLACKLIST:
                continue

            full_href = urljoin(final_url, a["href"].strip())
            if full_href in seen_urls or full_href.rstrip("/") == final_url.rstrip("/"):
                continue

            if JOB_HREF_PATTERNS.search(full_href):
                parsed_href = urlparse(full_href)
                if parsed_href.path.strip("/") in ("", "careers", "career", "jobs"):
                    continue

                seen_urls.add(full_href)
                extracted_jobs.append({
                    "title": raw_text,
                    "location": "Refer Official Posting",
                    "department": "Corporate Openings",
                    "apply_url": build_highlight_url(full_href, raw_text),
                    "verbatim_quote": f"Verified Opening on {final_url}: {raw_text}",
                    "verification_status": "PUBLISHED"
                })

    # Step 6: Layer 5 - Playwright Single-Tab JS Renderer Fallback (for React/Angular/Darwinbox/Keka/SPA)
    if len(extracted_jobs) < 2:
        spa_res = render_spa_page_with_playwright(final_url)
        spa_final_url = spa_res.get("final_url", final_url)

        # 6a. Intercepted JSON API jobs
        for ij in spa_res.get("intercepted_jobs", []):
            if ij["apply_url"] not in seen_urls and ij["title"].lower() not in seen_titles:
                seen_urls.add(ij["apply_url"])
                seen_titles.add(ij["title"].lower())
                extracted_jobs.append(ij)

        # 6b. Parse rendered DOM
        spa_html = spa_res.get("html")
        if spa_html:
            spa_soup = BeautifulSoup(spa_html, "lxml")
            spa_dom_jobs = detect_repeating_dom_job_cards(spa_soup, spa_final_url)
            for dj in spa_dom_jobs:
                if dj["apply_url"] not in seen_urls and dj["title"].lower() not in seen_titles:
                    seen_urls.add(dj["apply_url"])
                    seen_titles.add(dj["title"].lower())
                    extracted_jobs.append(dj)

            # Anchor links from rendered DOM
            if len(extracted_jobs) < 2:
                for a in spa_soup.find_all("a", href=True):
                    raw_text = re.sub(r'\s+', ' ', a.get_text(" ", strip=True)).strip()
                    if not (5 <= len(raw_text) <= 120):
                        continue
                    if GENERIC_BUTTON_PHRASES.match(raw_text) or raw_text.lower() in NAVBAR_BLACKLIST:
                        continue
                    full_href = urljoin(spa_final_url, a["href"].strip())
                    if full_href in seen_urls or full_href.rstrip("/") == spa_final_url.rstrip("/"):
                        continue
                    if JOB_HREF_PATTERNS.search(full_href):
                        parsed_href = urlparse(full_href)
                        if parsed_href.path.strip("/") in ("", "careers", "career", "jobs"):
                            continue
                        seen_urls.add(full_href)
                        seen_titles.add(raw_text.lower())
                        extracted_jobs.append({
                            "title": raw_text,
                            "location": "Refer Official Posting",
                            "department": "Corporate Openings",
                            "apply_url": build_highlight_url(full_href, raw_text),
                            "verbatim_quote": f"Verified Opening on {spa_final_url}: {raw_text}",
                            "verification_status": "PUBLISHED"
                        })

    return {
        "access_status": "PUBLIC_OK",
        "jobs": extracted_jobs,
        "confirmed_zero": len(extracted_jobs) == 0,
        "error": None,
        "final_url": final_url,
    }


# ==============================================================================
# CSR MULTI-PAGE & STATUTORY PARAGRAPH EXTRACTOR (Step 5)
# ==============================================================================

def _extract_csr_content_from_page(html: str, page_url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    """Extracts CSR projects and PDF reports from a single page's HTML."""
    clean_body = trafilatura.extract(
        html,
        include_tables=True,
        include_links=False,
        no_fallback=False
    ) or ""

    csr_projects = []
    seen_summaries = set()
    valid_paragraphs = 0

    for block in clean_body.split("\n"):
        paragraph = re.sub(r'\s+', ' ', block).strip()
        if len(paragraph) < 65:
            continue

        matched_theme = None
        for theme, keywords in SCHEDULE_VII_THEMES.items():
            if any(kw in paragraph.lower() for kw in keywords):
                matched_theme = theme
                break

        has_statutory_marker = bool(CSR_STATUTORY_MARKERS.search(paragraph))
        if not matched_theme and not has_statutory_marker:
            continue

        valid_paragraphs += 1
        fingerprint = paragraph[:80].lower()
        if fingerprint in seen_summaries:
            continue
        seen_summaries.add(fingerprint)

        # Clean budget regex: MUST require at least one digit \d after currency symbol
        budget_match = CSR_BUDGET_REGEX.search(paragraph)
        budget_str = budget_match.group(0).strip() if budget_match else "Verified on Official Portal"

        first_clause = re.split(r'[.।:;–—-]', paragraph)[0].strip()
        title = first_clause[:90] if len(first_clause) >= 12 else f"{matched_theme or 'Corporate CSR'} Initiative"

        csr_projects.append({
            "title": title,
            "focus_area": matched_theme or "Schedule VII Statutory CSR",
            "summary": paragraph,
            "budget_allocated": budget_str,
            "source_url": build_highlight_url(page_url, paragraph),
            "verification_status": "PUBLISHED"
        })

    # PDF Reports
    soup = BeautifulSoup(html, "lxml")
    pdf_reports = []
    seen_pdfs = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if ".pdf" in href.lower():
            full_pdf_url = urljoin(page_url, href)
            link_text = re.sub(r'\s+', ' ', a.get_text(" ", strip=True)).strip() or "Official CSR Report PDF"
            if full_pdf_url not in seen_pdfs and any(k in full_pdf_url.lower() or k in link_text.lower() for k in ["csr", "sustainability", "brsr", "annual", "foundation", "impact", "report", "action"]):
                seen_pdfs.add(full_pdf_url)
                pdf_reports.append({"title": link_text[:120], "pdf_url": full_pdf_url})

    return csr_projects, pdf_reports, valid_paragraphs


def extract_genuine_csr_live(csr_url: str) -> dict:
    """
    Extracts authentic Section 135 / Schedule VII CSR projects with multi-page sublink discovery.
    If the landing page contains < 2 paragraphs, automatically follows the top 3 internal CSR sub-pages.
    """
    page_res = fetch_live_page(csr_url)
    if not page_res["ok"]:
        return {
            "access_status": page_res["access_status"],
            "csr_projects": [],
            "pdf_reports": [],
            "error": page_res["error"],
            "final_url": page_res.get("final_url", csr_url)
        }

    final_url = page_res["final_url"]
    html = page_res["html"]

    csr_projects, pdf_reports, valid_paragraphs = _extract_csr_content_from_page(html, final_url)

    # Multi-Page Sub-Link Crawling: If landing page has < 2 paragraphs, crawl top 3 CSR sub-links
    if valid_paragraphs < 2:
        soup = BeautifulSoup(html, "lxml")
        sub_candidates = []
        base_netloc = urlparse(final_url).netloc

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue
            full_href = urljoin(final_url, href)
            if full_href.rstrip("/") == final_url.rstrip("/"):
                continue
            if urlparse(full_href).netloc != base_netloc:
                continue

            link_text = re.sub(r'\s+', ' ', a.get_text(" ", strip=True)).strip()
            score = score_link_semantics(f"{link_text} {urlparse(full_href).path}", "csr")
            if score >= 0.45:
                sub_candidates.append((score, full_href))

        sub_candidates.sort(key=lambda x: x[0], reverse=True)
        seen_sub_urls = set()

        for _, sub_url in sub_candidates[:3]:
            if sub_url in seen_sub_urls:
                continue
            seen_sub_urls.add(sub_url)
            sub_res = fetch_live_page(sub_url)
            if sub_res["ok"] and sub_res["html"]:
                sub_projects, sub_pdfs, _ = _extract_csr_content_from_page(sub_res["html"], sub_res["final_url"])
                csr_projects.extend(sub_projects)
                pdf_reports.extend(sub_pdfs)

    # Playwright SPA fallback for CSR pages if static extraction found 0 projects
    if valid_paragraphs < 2 and not csr_projects:
        spa_res = render_spa_page_with_playwright(final_url)
        if spa_res.get("html"):
            spa_p, spa_pdf, spa_valid = _extract_csr_content_from_page(spa_res["html"], spa_res.get("final_url", final_url))
            csr_projects.extend(spa_p)
            pdf_reports.extend(spa_pdf)

    return {
        "access_status": "PUBLIC_OK",
        "final_csr_url": final_url,
        "csr_projects": csr_projects,
        "pdf_reports": pdf_reports,
        "error": None
    }


# ==============================================================================
# 1:1 LIVE SYNCHRONIZER (MySQL Atomic State Mirror)
# ==============================================================================

def sync_single_company_live(company) -> dict:
    """
    Performs a 100% live scrape of a single company, upserts current live Jobs & CSR records,
    and updates jobs_access / csr_access honestly based on 'Extract First, Login Wall Last'.
    """
    if not connection.in_atomic_block:
        close_old_connections()
    sync_timestamp = timezone.now()
    old_hash = company.content_hash or ""

    # 1. Discover Careers & CSR URLs if missing or outdated
    target_domain = company.website_url or company.official_domain or ""
    if (not company.careers_url or not company.csr_url) and target_domain:
        discovered = discover_company_official_links(target_domain)
        if discovered.get("careers_url") and not company.careers_url:
            company.careers_url = discovered["careers_url"]
        if discovered.get("csr_url") and not company.csr_url:
            company.csr_portal_url = discovered["csr_url"]

    jobs_added, jobs_updated, jobs_removed = 0, 0, 0
    csr_added, csr_updated, csr_removed = 0, 0, 0
    urls_probed = []

    # 2. Sync Live Jobs via Pluggable Strategy Cascade (Phase 2, 3, 4, 5, 6)
    if company.careers_url:
        try:
            pipeline = StrategyPipeline()
            extracted_jobs_list, strategy_name, direct_pct = pipeline.run(company, company.careers_url)
        except Exception as exc:
            logger.error("Job extraction error for %s: %s", company.company_name, exc, exc_info=True)
            company.last_sync_error = f"Job extraction error: {str(exc)[:400]}"
            company.crawl_status = "ERROR"
            try:
                company.save(update_fields=['last_sync_error', 'crawl_status'])
            except Exception:
                pass
            extracted_jobs_list = []
            strategy_name = "ERROR"
            direct_pct = 0.0

        # Update company extraction strategy and success rate
        company.extraction_strategy = strategy_name
        company.last_strategy_success_rate = direct_pct

        previous_active_count = Job.objects.filter(company=company, status='ACTIVE').count()
        extracted_count = len(extracted_jobs_list)
        is_blocked = company.jobs_access in ('LOGIN_REQUIRED', 'BLOCKED')

        if extracted_count > 0:
            company.jobs_access = "PUBLIC"
            company.data_access_note = ""
            company.data_access_checked_at = sync_timestamp
        elif company.crawl_status != "ERROR":
            if previous_active_count > 0:
                logger.warning(
                    "SAFETY GUARD ACTIVATED for %s: extracted 0 jobs vs %d previous active. Skipping prune to prevent data loss.",
                    company.company_name, previous_active_count
                )
                company.crawl_status = "SUSPECT_DROP"
            company.jobs_access = "NOT_PUBLISHED"
            company.data_access_note = ""
            company.data_access_checked_at = sync_timestamp

        urls_probed.append({
            "url": company.careers_url,
            "final_url": company.careers_url,
            "status": 200 if extracted_count > 0 else 404,
            "method": f"STRATEGY_{strategy_name.upper()}",
        })

        try:
            company.save(update_fields=[
                'crawl_status', 'extraction_strategy', 'last_strategy_success_rate',
                'jobs_access', 'data_access_note', 'data_access_checked_at'
            ])
        except Exception:
            pass

        if extracted_count > 0:
            live_canonical_urls = set()
            live_ext_ids = set()

            with transaction.atomic():
                for j in extracted_jobs_list:
                    raw_app_url = j.get("application_url") or ""
                    canon_url = j.get("canonical_url") or normalize_canonical_url(raw_app_url) or raw_app_url
                    quality = j.get("link_quality", "UNVERIFIED")
                    note = j.get("link_check_note") or ""
                    ext_id = j.get("external_job_id")

                    # DIRECT: keep exact canonical_url without any highlight fragment.
                    # LISTING_FALLBACK: provide highlight text fragment to help users find role on listing page.
                    if quality == "DIRECT":
                        app_url = canon_url
                    else:
                        app_url = build_highlight_url(canon_url, j["title"])

                    if canon_url:
                        live_canonical_urls.add(canon_url)
                    if ext_id:
                        live_ext_ids.add(ext_id)

                    # Clean location & city
                    raw_loc = (j.get("location") or "").strip()
                    if not raw_loc or raw_loc.lower() in ("refer official posting", "not available on the company website", "n/a", "none"):
                        loc = company.headquarters or "India"
                    else:
                        loc = raw_loc

                    detected_city = j.get("city")
                    if not detected_city:
                        for c_name in COMMON_INDIAN_LOCATIONS:
                            if c_name != "india" and c_name in loc.lower():
                                detected_city = c_name.title()
                                break
                    if not detected_city:
                        detected_city = company.headquarters or "India"

                    # Deterministic, non-listing fingerprint
                    fp = build_job_fingerprint(
                        company_id=company.company_id,
                        external_job_id=ext_id,
                        canonical_url=canon_url if quality == "DIRECT" else None,
                        title=j["title"],
                        location=loc,
                    )

                    defaults = {
                        "company": company,
                        "job_id": f"JOB_{company.company_id}_{fp[:12]}",
                        "job_title": j["title"],
                        "location": loc,
                        "city": detected_city,
                        "department": j.get("department") or "Corporate",
                        "employment_type": j.get("employment_type") or "Full-time",
                        "work_mode": j.get("work_mode") or "On-site",
                        "job_description": j.get("job_description") or j.get("verbatim_quote") or j["title"],
                        "verification_status": "SOURCE_CONFIRMED",
                        "status": "ACTIVE",
                        "removed_at": None,
                        "link_status": "LINK_OK" if quality == "DIRECT" else "LINK_FALLBACK",
                        "owner_status": "OWNED",
                        "application_url": app_url,
                        "canonical_url": canon_url,
                        "external_job_id": ext_id,
                        "link_quality": quality,
                        "link_check_note": note,
                        "link_verified_at": sync_timestamp if quality == "DIRECT" else None,
                        "last_seen_live_at": sync_timestamp,
                        "last_checked_date": sync_timestamp.isoformat(),
                        "source_url": canon_url,
                        "retrieved_at": sync_timestamp,
                        "last_seen_at": sync_timestamp,
                        "evidence_text": j.get("job_description") or j["title"],
                        "content_hash": hashlib.md5(f"{j['title']}_{canon_url}".encode('utf-8')).hexdigest(),
                        "raw_metadata": j.get("raw_metadata") or j,
                    }
                    obj, created = Job.objects.update_or_create(
                        fingerprint=fp,
                        defaults=defaults,
                    )
                    if created:
                        obj.first_seen_at = sync_timestamp
                        obj.save(update_fields=['first_seen_at'])
                        jobs_added += 1
                    else:
                        jobs_updated += 1

                    if ext_id:
                        Job.objects.filter(company=company, external_job_id=ext_id).update(
                            last_seen_at=sync_timestamp,
                            last_seen_live_at=sync_timestamp,
                            status='ACTIVE',
                            removed_at=None,
                        )

                # PHASE 5: SAFETY GUARDS BEFORE PRUNING
                extracted_count = len(extracted_jobs_list)
                is_blocked = company.jobs_access in ('LOGIN_REQUIRED', 'BLOCKED')
                if extracted_count == 0 or is_blocked or (previous_active_count > 0 and extracted_count < 0.5 * previous_active_count):
                    logger.warning(
                        "SAFETY GUARD ACTIVATED for %s: extracted %d jobs vs %d previous active (<50%%) or blocked (%s). Skipping prune to prevent data loss.",
                        company.company_name, extracted_count, previous_active_count, company.jobs_access
                    )
                    company.crawl_status = "SUSPECT_DROP"
                else:
                    # Safe to prune: prune by (company, external_job_id) or canonical_url
                    stale_jobs_qs = Job.objects.filter(company=company, status='ACTIVE')
                    if live_ext_ids:
                        stale_jobs_qs = stale_jobs_qs.exclude(external_job_id__in=live_ext_ids)
                    if live_canonical_urls:
                        stale_jobs_qs = stale_jobs_qs.exclude(canonical_url__in=live_canonical_urls)

                    stale_count = stale_jobs_qs.count()
                    # Max 50% deletion per run guard
                    max_deletions = max(1, previous_active_count // 2) if previous_active_count > 0 else stale_count
                    if previous_active_count > 0 and stale_count > max_deletions:
                        logger.warning(
                            "JOB PRUNE CAPPED for %s: would remove %d jobs; capping at %d (50%% of previous_active=%d).",
                            company.company_name, stale_count, max_deletions, previous_active_count,
                        )
                        stale_job_ids = list(stale_jobs_qs.order_by('job_id').values_list('job_id', flat=True)[:max_deletions])
                        stale_jobs_qs = Job.objects.filter(job_id__in=stale_job_ids)

                    jobs_removed = stale_jobs_qs.count()
                    # Soft-delete: mark REMOVED with timestamp
                    stale_jobs_qs.update(status='REMOVED', removed_at=sync_timestamp)

                    # Unified lifecycle: transition jobs absent > 7 days to EXPIRED (no hard-deletions)
                    from django.conf import settings
                    if getattr(settings, 'FREEZE_JOB_EXPIRY_AND_DELETION', False):
                        logger.info("FREEZE_JOB_EXPIRY_AND_DELETION is True: Skipping job expiry for %s.", company.company_name)
                    else:
                        purge_cutoff = sync_timestamp - timedelta(days=7)
                        Job.objects.filter(company=company, status='REMOVED', removed_at__lt=purge_cutoff).update(
                            status='EXPIRED',
                            verification_status='STALE',
                        )

            # Save company metadata updates
            try:
                company.save(update_fields=[
                    'crawl_status', 'extraction_strategy', 'last_strategy_success_rate',
                    'jobs_access', 'data_access_note', 'data_access_checked_at'
                ])
            except Exception:
                pass

            # Phase 6: Structured Crawl Summary Logging (outside job upsert atomic transaction)
            try:
                CompanyCrawlSummary.objects.create(
                    company=company,
                    crawl_started_at=sync_timestamp,
                    crawl_finished_at=timezone.now(),
                    career_url_found=company.careers_url,
                    ats_platform=company.ats_type or company.ats_platform,
                    ats_url=company.ats_url,
                    extraction_strategy=strategy_name,
                    direct_percentage=direct_pct,
                    jobs_discovered=extracted_count,
                    jobs_published=jobs_added + jobs_updated,
                    jobs_updated=jobs_updated,
                    jobs_expired=jobs_removed,
                    crawl_status="CRAWLED" if extracted_count > 0 else "PARTIAL",
                )
            except Exception:
                pass

    # 3. Sync Live CSR Details
    csr_target = company.csr_url or company.website_url
    if csr_target:
        try:
            csr_res = extract_genuine_csr_live(csr_target)
        except Exception as exc:
            logger.error("CSR extraction error for %s: %s", company.company_name, exc, exc_info=True)
            csr_res = {"access_status": "ERROR", "error": str(exc), "csr_projects": [], "pdf_reports": []}
        csr_projects_list = csr_res.get("csr_projects", [])
        pdf_reports_list = csr_res.get("pdf_reports", [])

        if len(csr_projects_list) > 0 or len(pdf_reports_list) > 0:
            company.csr_access = "PUBLIC"
            company.data_access_checked_at = sync_timestamp
        elif csr_res.get("access_status") == "LOGIN_REQUIRED":
            company.csr_access = "LOGIN_REQUIRED"
            if not company.data_access_note:
                company.data_access_note = csr_res.get("login_reason") or "Login required on company CSR portal."
            company.data_access_checked_at = sync_timestamp
        else:
            company.csr_access = "NOT_PUBLISHED"
            company.data_access_checked_at = sync_timestamp

        company.contacts_access = "PUBLIC"

        csr_access_status = csr_res.get("access_status", "PUBLIC_OK")
        urls_probed.append({
            "url": csr_target,
            "final_url": csr_res.get("final_csr_url", csr_target),
            "status": 200 if csr_access_status == "PUBLIC_OK" else (401 if csr_access_status == "LOGIN_REQUIRED" else 403),
            "method": "TRAFILATURA_CURL_CFFI",
        })

        if csr_access_status == "PUBLIC_OK" or len(csr_projects_list) > 0 or len(pdf_reports_list) > 0:
            live_csr_urls = set()
            with transaction.atomic():
                for c in csr_projects_list:
                    src_url = c["source_url"]
                    live_csr_urls.add(src_url)
                    fp = hashlib.md5(f"{company.company_id}_{src_url}".encode('utf-8')).hexdigest()

                    # Sanitize budget with regex
                    raw_b = str(c.get("budget_allocated") or "")
                    b_match = CSR_BUDGET_REGEX.search(raw_b)
                    clean_budget = b_match.group(0).strip() if b_match else (raw_b if raw_b else "Statutory CSR Allocation")

                    defaults = {
                        "company": company,
                        "project_name": c["title"],
                        "category": c["focus_area"],
                        "description": c["summary"],
                        "budget": clean_budget,
                        "verification_status": "SOURCE_CONFIRMED",
                        "link_status": "LINK_OK",
                        "last_seen_live_at": sync_timestamp,
                        "last_verified_date": sync_timestamp.isoformat(),
                        "source_url": src_url,
                        "retrieved_at": sync_timestamp,
                        "first_seen_at": sync_timestamp,
                        "last_seen_at": sync_timestamp,
                        "evidence_text": c["summary"],
                        "fingerprint": fp,
                        "content_hash": hashlib.md5(f"{c['title']}_{src_url}".encode('utf-8')).hexdigest(),
                        "raw_metadata": c,
                    }
                    obj, created = CSRProject.objects.update_or_create(
                        fingerprint=fp,
                        defaults=defaults,
                    )
                    if created:
                        csr_added += 1
                    else:
                        csr_updated += 1

                    # PHASE 1: Do NOT clone CSRProject into CSROpportunity.
                    # Synthetic opportunities (cloned from projects) have no real deadline
                    # or application mechanism — they are invalid. Only records with a genuine
                    # submission_deadline or apply_url may become CSROpportunity entries.
                    # (Existing synthetic rows will be marked INVALID_SYNTHETIC by migration.)

                # If official PDF reports exist, persist the reports as statutory CSR entries
                if not csr_projects_list and pdf_reports_list:
                    for rep in pdf_reports_list[:5]:
                        pdf_url = rep["pdf_url"]
                        live_csr_urls.add(pdf_url)
                        fp = hashlib.md5(f"{company.company_id}_{pdf_url}".encode('utf-8')).hexdigest()
                        defaults = {
                            "company": company,
                            "project_name": rep["title"],
                            "category": "Statutory CSR & Sustainability Report",
                            "description": f"Official Statutory Annual CSR / Sustainability Report for {company.company_name}.",
                            "budget": "Statutory Annual Filing",
                            "verification_status": "SOURCE_CONFIRMED",
                            "link_status": "LINK_OK",
                            "last_seen_live_at": sync_timestamp,
                            "last_verified_date": sync_timestamp.isoformat(),
                            "source_url": pdf_url,
                            "retrieved_at": sync_timestamp,
                            "first_seen_at": sync_timestamp,
                            "last_seen_at": sync_timestamp,
                            "evidence_text": f"Official Statutory Document: {rep['title']}",
                            "fingerprint": fp,
                            "content_hash": hashlib.md5(f"{rep['title']}_{pdf_url}".encode('utf-8')).hexdigest(),
                            "raw_metadata": rep,
                        }
                        obj, created = CSRProject.objects.update_or_create(
                            fingerprint=fp,
                            defaults=defaults,
                        )
                        if created:
                            csr_added += 1
                        else:
                            csr_updated += 1

                        # PHASE 1: Do NOT clone PDF statutory report into CSROpportunity.
                        # A PDF annual report is not an open NGO opportunity — it has no
                        # deadline or application mechanism. Suppressed to prevent synthetic rows.

                # 1:1 Live Delta Pruning for CSR Projects and Opportunities
                # Guarded with the same safety rules as Job pruning:
                #   (a) Block if live count is 0 (network / parse failure)
                #   (b) Block if crawl errored or was blocked
                #   (c) Block if live count is < 50% of current DB count
                #   (d) Cap hard-delete at 50% of current DB count per run
                #   (e) Soft-delete for 7 days before hard-delete
                current_csr_count = CSRProject.objects.filter(
                    company=company, status__in=['ACTIVE', '']
                ).exclude(status='INVALID_SYNTHETIC').count()
                live_count = len(live_csr_urls)
                is_csr_blocked = company.csr_access in ('LOGIN_REQUIRED', 'BLOCKED')
                has_csr_error = bool(csr_res.get("error"))

                if live_count == 0 or has_csr_error or is_csr_blocked or (current_csr_count > 0 and live_count < (current_csr_count * 0.5)):
                    logger.warning(
                        "CSR PRUNE BLOCKED for %s: live_count=%d (error=%s, blocked=%s) vs db_count=%d. Skipping prune to prevent data loss.",
                        company.company_name, live_count, has_csr_error, is_csr_blocked, current_csr_count,
                    )
                else:
                        stale_csr_qs = CSRProject.objects.filter(
                            company=company, status='ACTIVE'
                        ).exclude(
                            source_url__in=live_csr_urls
                        )

                        stale_count = stale_csr_qs.count()
                        max_deletions = max(1, current_csr_count // 2) if current_csr_count > 0 else stale_count
                        if current_csr_count > 0 and stale_count > max_deletions:
                            logger.warning(
                                "CSR PRUNE CAPPED for %s: would remove %d rows; capping at %d (50%% of db_count=%d).",
                                company.company_name, stale_count, max_deletions, current_csr_count,
                            )
                            stale_csr_ids = list(stale_csr_qs.order_by('csr_id').values_list('csr_id', flat=True)[:max_deletions])
                            stale_csr_qs = CSRProject.objects.filter(csr_id__in=stale_csr_ids)

                        # Soft-delete: mark status REMOVED with timestamp
                        csr_removed = stale_csr_qs.count()
                        stale_csr_qs.update(status='REMOVED', removed_at=sync_timestamp)

                        # Hard-delete CSRProjects soft-removed for more than 7 days
                        purge_cutoff = sync_timestamp - timedelta(days=7)
                        CSRProject.objects.filter(company=company, status='REMOVED', removed_at__lt=purge_cutoff).delete()

                        # Soft-delete stale OPEN CSROpportunities (7-day grace before hard-delete)
                        stale_opp_qs = CSROpportunity.objects.filter(
                            company=company, status='OPEN'
                        ).exclude(
                            models.Q(portal_url__in=live_csr_urls) | models.Q(source_url__in=live_csr_urls)
                        ).exclude(status='INVALID_SYNTHETIC')

                        current_opp_count = CSROpportunity.objects.filter(
                            company=company, status='OPEN'
                        ).count()
                        stale_opp_count = stale_opp_qs.count()

                        if current_opp_count > 0 and stale_opp_count >= (current_opp_count * 0.5):
                            logger.warning(
                                "OPP PRUNE CAPPED for %s: %d/%d stale; marking REMOVED instead of deleting.",
                                company.company_name, stale_opp_count, current_opp_count,
                            )
                            stale_opp_qs.update(status='REMOVED', last_seen_at=sync_timestamp)
                        else:
                            # Soft-delete: flip to REMOVED; hard-delete after 7 days
                            stale_opp_qs.update(status='REMOVED', last_seen_at=sync_timestamp)

                        # Hard-purge REMOVED opportunities older than 7 days
                        purge_cutoff = sync_timestamp - timedelta(days=7)
                        CSROpportunity.objects.filter(
                            company=company,
                            status='REMOVED',
                            last_seen_at__lt=purge_cutoff,
                        ).delete()

    # Compute SHA-256 payload hash
    active_jobs_count = Job.objects.filter(company=company, status='ACTIVE').count()
    active_csr_count = CSRProject.objects.filter(company=company).count()
    canonical_payload = json.dumps({
        "jobs": list(Job.objects.filter(company=company, status='ACTIVE').values_list('application_url', flat=True)),
        "csr": list(CSRProject.objects.filter(company=company).values_list('source_url', flat=True)),
    }, sort_keys=True)
    new_hash = hashlib.sha256(canonical_payload.encode('utf-8')).hexdigest()

    company.content_hash = new_hash
    if company.crawl_status == "ERROR":
        company.sync_status = "ERROR"
    else:
        company.sync_status = "LIVE_VERIFIED"
        company.last_sync_error = None
    company.last_live_synced_at = sync_timestamp
    company.last_crawled = sync_timestamp.isoformat()
    company.save(update_fields=['content_hash', 'sync_status', 'last_live_synced_at', 'last_crawled', 'last_sync_error'])
    if not connection.in_atomic_block:
        close_old_connections()

    return {
        "status": "SUCCESS",
        "company_id": company.company_id,
        "company_name": company.company_name,
        "access_status": company.jobs_access,
        "sync_start_time": sync_timestamp.isoformat(),
        "synced_at": sync_timestamp.isoformat(),
        "urls_probed": urls_probed,
        "jobs_added": jobs_added,
        "jobs_updated": jobs_updated,
        "jobs_removed": jobs_removed,
        "csr_added": csr_added,
        "csr_updated": csr_updated,
        "csr_removed": csr_removed,
        "active_jobs_count": active_jobs_count,
        "active_csr_count": active_csr_count,
        "old_hash": old_hash,
        "new_hash": new_hash,
        "jobs_diff": {"added": jobs_added, "updated": jobs_updated, "removed": jobs_removed, "active_total": active_jobs_count},
        "csr_diff": {"added": csr_added, "updated": csr_updated, "removed": csr_removed, "active_total": active_csr_count},
    }


def sync_company_live(company_id=None, domain=None, company=None) -> dict:
    """
    Dispatcher accepting company_id, domain, or company instance.
    """
    if not connection.in_atomic_block:
        close_old_connections()
    if not company:
        if company_id:
            cid_str = str(company_id).strip()
            company = Company.objects.filter(company_id=cid_str).first()
            if not company:
                company = Company.objects.filter(company_id__icontains=cid_str).first()
            if not company and cid_str.isdigit():
                company = Company.objects.filter(company_id=f"COMP_TOP200_{int(cid_str):03d}").first()
        elif domain:
            domain_clean = str(domain).strip().lower().removeprefix('https://').removeprefix('http://').split('/')[0]
            company = Company.objects.filter(
                models.Q(official_domain__icontains=domain_clean)
                | models.Q(website_url__icontains=domain_clean)
            ).first()

    if not company:
        return {
            "status": "FAILED",
            "error": f"Company not found for id='{company_id}' domain='{domain}'",
            "jobs_added": 0, "jobs_updated": 0, "jobs_removed": 0,
            "csr_added": 0, "csr_updated": 0, "csr_removed": 0,
            "active_jobs_count": 0, "active_csr_count": 0,
        }

    return sync_single_company_live(company)


def process_company(company) -> dict:
    """Compatibility runner for scripts calling process_company."""
    return sync_single_company_live(company)


def start_background_crawl(company_ids=None):
    """Background crawl compatibility runner."""
    from django.conf import settings
    if not getattr(settings, 'ALLOW_GLOBAL_SYNC', False):
        logger.warning("start_background_crawl REFUSED: ALLOW_GLOBAL_SYNC is False. Background crawling is disabled.")
        return False

    from concurrent.futures import ThreadPoolExecutor
    qs = Company.objects.all()
    if company_ids:
        qs = qs.filter(company_id__in=company_ids)

    def _run():
        close_old_connections()
        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(sync_single_company_live, list(qs))
        close_old_connections()

    import threading
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return True
