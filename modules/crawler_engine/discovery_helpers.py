"""
modules/crawler_engine/discovery_helpers.py
===========================================
Pure-Python helper functions for deep link validation, registrable domain
equivalence, and careers page content verification (Stage 1).
"""
import re
import json
from urllib.parse import urlparse
from typing import Optional, Tuple, List, Dict, Any
from bs4 import BeautifulSoup

from .normalizers import clean_text, match_ats_pattern, load_ats_patterns

# Known multi-part Indian and international public suffixes for base domain resolution
_KNOWN_TWO_PART_SUFFIXES = {
    "co.in", "net.in", "org.in", "gov.in", "ac.in", "res.in",
    "co.uk", "org.uk", "me.uk", "ltd.uk", "plc.uk",
    "com.au", "net.au", "org.au", "edu.au",
    "co.za", "co.jp", "com.sg", "com.my", "com.br"
}

JOB_ACTION_PHRASES = re.compile(
    r'\b(apply\s+now|apply\s+for\s+this\s+job|view\s+job|view\s+openings|search\s+jobs|open\s+positions|explore\s+roles|current\s+openings|submit\s+application|job\s+details)\b',
    re.IGNORECASE
)

JOB_URL_PATTERNS = re.compile(
    r'(/job/|/jobs/|/career[s]?/[^/?#]+|jobid=|job_id=|requisition|opening[s]?/[^/?#]+|vacancy/[^/?#]+|vacancies/[^/?#]+|positions?/[^/?#]+)',
    re.IGNORECASE
)

REPEATED_CARD_CLASSES = re.compile(
    r'(job-card|jobcard|job-item|jobitem|job-listing|joblisting|job-row|jobrow|career-item|position-item|opening-card|search-result-item)',
    re.IGNORECASE
)


def normalize_url_for_comparison(url: Optional[str]) -> Tuple[str, str]:
    """
    Normalizes a URL into (clean_host, clean_path) for equivalence checking.
    Strips protocol, port, user info, 'www.' prefix, and trailing slashes.
    """
    cleaned = clean_text(url)
    if not cleaned:
        return "", ""

    if "://" not in cleaned:
        cleaned = f"https://{cleaned}"

    parsed = urlparse(cleaned)
    host = (parsed.netloc or "").lower().split(":")[0].strip()
    if host.startswith("www."):
        host = host[4:]

    path = (parsed.path or "").strip().rstrip("/")
    return host, path


def get_registrable_domain(url_or_host: Optional[str]) -> str:
    """
    Extracts the base registrable domain from a host or URL.
    Examples:
      - 'careers.tatamotors.com' -> 'tatamotors.com'
      - 'www.sbi.co.in' -> 'sbi.co.in'
      - 'new.abb.com' -> 'abb.com'
    """
    cleaned = clean_text(url_or_host)
    if not cleaned:
        return ""

    if "://" in cleaned:
        parsed = urlparse(cleaned)
        host = (parsed.netloc or "").lower().split(":")[0].strip()
    else:
        host = cleaned.lower().split("/")[0].split(":")[0].strip()

    if host.startswith("www."):
        host = host[4:]

    parts = host.split(".")
    if len(parts) <= 2:
        return host

    # Check two-part ccTLDs e.g. .co.in
    last_two = ".".join(parts[-2:])
    if last_two in _KNOWN_TWO_PART_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])

    return ".".join(parts[-2:])


def is_real_deep_url(url: Optional[str], website_url: Optional[str]) -> bool:
    """
    Determines if candidate URL is a genuine deep link rather than a root homepage.
    Returns False if:
      - url is empty or None
      - path is '' or '/' AND the host is the same root host as website_url
      - url equals website_url (ignoring protocol, www, and trailing slash)
    Returns True if:
      - url has a distinct path (e.g. /careers, /jobs, /csr)
      - url has a distinct subdomain (e.g. careers.company.com vs company.com)
      - url is on an external ATS or portal domain
    """
    c_host, c_path = normalize_url_for_comparison(url)
    w_host, w_path = normalize_url_for_comparison(website_url)

    if not c_host:
        return False

    # Check if host and path exactly match the website URL
    if f"{c_host}{c_path}" == f"{w_host}{w_path}":
        return False

    # If the candidate path is root/empty
    if c_path in ("", "/"):
        # If the candidate host is identical to website host (or same registrable with no subdomain)
        if c_host == w_host:
            return False
        # If candidate host is just a www variant of website host
        c_reg = get_registrable_domain(c_host)
        w_reg = get_registrable_domain(w_host)
        if c_host == c_reg and w_host == w_reg:
            return False

    return True


def is_same_registrable_domain_or_ats(cand_url: Optional[str], base_url: Optional[str]) -> bool:
    """
    Validates whether cand_url belongs to:
    1. The same registrable root domain as base_url (including any subdomains)
    2. OR any known enterprise ATS domain (Workday, Lever, Greenhouse, etc.)
    """
    if not cand_url or not base_url:
        return False

    c_host, _ = normalize_url_for_comparison(cand_url)
    w_host, _ = normalize_url_for_comparison(base_url)

    if not c_host or not w_host:
        return False

    # Check if registrable domain matches
    c_reg = get_registrable_domain(c_host)
    w_reg = get_registrable_domain(w_host)
    if c_reg and w_reg and c_reg == w_reg:
        return True

    # Check known ATS domains from ats_domains.json / pattern matcher
    if match_ats_pattern(cand_url) is not None:
        return True

    common_ats = (
        "myworkdayjobs.com", "lever.co", "greenhouse.io", "smartrecruiters.com",
        "darwinbox.in", "darwinbox.com", "successfactors.com", "successfactors.eu",
        "oraclecloud.com", "taleo.net", "keka.com", "icims.com", "ashbyhq.com",
        "zohorecruit.com", "zohorecruit.in", "freshteam.com"
    )
    if any(ats in c_host for ats in common_ats):
        return True

    return False


def verify_careers_url_content(html: Optional[str], url: str = "") -> Tuple[bool, float, List[str]]:
    """
    Verifies whether a discovered careers page contains authentic job-like signals:
    1. schema.org/JobPosting in JSON-LD or microdata
    2. Link (<a href>) or iframe (<iframe src>) pointing to a known ATS domain
    3. Repeated job listing card elements (jobCard, job-item, etc.)
    4. Actionable apply/job links ('Apply Now', '/job/12345')

    Returns:
        (has_signals: bool, confidence_score: float, detected_signals: List[str])
    """
    signals: List[str] = []
    if not html or not html.strip():
        return False, 0.1, ["empty_page_content"]

    soup = BeautifulSoup(html, "lxml")

    # 1. JSON-LD JobPosting check
    for s_tag in soup.find_all("script", type="application/ld+json"):
        try:
            content = s_tag.string or ""
            if '"JobPosting"' in content or '"@type":"JobPosting"' in content:
                signals.append("jsonld_job_posting")
                break
        except Exception:
            pass

    # 2. Check ATS links & iframes
    for tag in soup.find_all(["a", "iframe"], src=True) + soup.find_all("a", href=True):
        target = tag.get("src") or tag.get("href") or ""
        if target and match_ats_pattern(target) is not None:
            signals.append(f"ats_reference:{urlparse(target).netloc}")
            break

    # 3. Repeated job listing elements
    cards = soup.find_all(class_=REPEATED_CARD_CLASSES)
    if len(cards) >= 2:
        signals.append(f"repeated_job_cards_count_{len(cards)}")

    # 4. Actionable apply / job links
    apply_links = 0
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(" ", strip=True)
        if JOB_ACTION_PHRASES.search(text) or JOB_URL_PATTERNS.search(href):
            apply_links += 1
            if apply_links >= 2:
                signals.append(f"job_action_links_count_{apply_links}")
                break

    has_signals = len(signals) > 0
    if has_signals:
        confidence = min(0.95, 0.65 + (len(signals) * 0.10))
    else:
        confidence = 0.25

    return has_signals, round(confidence, 2), signals
