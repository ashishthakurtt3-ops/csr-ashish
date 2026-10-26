"""
Pure-Python normalisers applied at ingest time (no Django imports so they can
be unit-tested anywhere).

Rule: NEVER guess. If a value cannot be normalised with certainty the function
returns None and the UI shows "Not available on the company website".
"""
from __future__ import annotations

import hashlib
import re
import json
import fnmatch
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse, urljoin, parse_qsl, urlencode

# --------------------------------------------------------------------------- #
# Placeholders
# --------------------------------------------------------------------------- #
NOT_AVAILABLE_TEXT = "Not available on the company website"
LOGIN_REQUIRED_TEXT = "Available only after login on the company website"

_EMPTY_TOKENS = {
    '', '-', '--', '---', 'null', 'none', 'n/a', 'na', 'undefined', 'unspecified',
    'uncategorized', 'not specified', 'not provided by source', 'not available',
    'not available on the company website', 'tbd', 'nil',
}


def clean_text(value) -> Optional[str]:
    """Strip and convert placeholder strings to None."""
    if value is None:
        return None
    s = re.sub(r'\s+', ' ', str(value)).strip()
    if s.lower() in _EMPTY_TOKENS:
        return None
    return s


# --------------------------------------------------------------------------- #
# Dates  ->  ISO-8601 (YYYY-MM-DD)
# --------------------------------------------------------------------------- #
_REL_RE = re.compile(r'(?:posted\s+)?(\d+)\+?\s+(day|days|week|weeks|month|months)\s+ago', re.I)
_FORMATS = (
    '%Y-%m-%d', '%d %b %Y', '%d %B %Y', '%b %d, %Y', '%B %d, %Y',
    '%d-%m-%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%b-%Y', '%d-%b-%y',
    '%d.%m.%Y', '%B %d %Y', '%b %d %Y',
)


def normalize_date(value, now: Optional[datetime] = None) -> Optional[str]:
    """
    Accepts ISO strings, epoch seconds/milliseconds, 'Posted N Days Ago',
    'Posted Today/Yesterday' and common textual formats.
    Returns 'YYYY-MM-DD' or None. Relative dates are resolved against `now`
    (the crawl time) and are therefore only as exact as the source ("30+ days"
    is NOT converted because it is open-ended).
    """
    s = clean_text(value)
    if not s:
        return None
    now = now or datetime.now(timezone.utc)

    if re.fullmatch(r'\d{13}', s):                       # epoch ms
        return datetime.fromtimestamp(int(s) / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
    if re.fullmatch(r'\d{10}', s):                       # epoch s
        return datetime.fromtimestamp(int(s), tz=timezone.utc).strftime('%Y-%m-%d')

    low = s.lower()
    if low in ('posted today', 'today', 'just posted', 'posted just now'):
        return now.strftime('%Y-%m-%d')
    if low in ('posted yesterday', 'yesterday'):
        return (now - timedelta(days=1)).strftime('%Y-%m-%d')
    if re.search(r'\d+\+', low):                         # e.g. "Posted 30+ Days Ago" – open ended
        return None
    m = _REL_RE.search(s)
    if m:
        n, unit = int(m.group(1)), m.group(2).lower()
        days = n if unit.startswith('day') else n * 7 if unit.startswith('week') else n * 30
        return (now - timedelta(days=days)).strftime('%Y-%m-%d')

    iso = re.match(r'(\d{4}-\d{2}-\d{2})', s)             # 2026-07-03 or 2026-07-03T10:..Z
    if iso:
        try:
            datetime.strptime(iso.group(1), '%Y-%m-%d')
            return iso.group(1)
        except ValueError:
            return None
    for fmt in _FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------------- #
# Employment type / work mode  ->  fixed vocabulary
# --------------------------------------------------------------------------- #
VALID_EMPLOYMENT_TYPES = ('Full-time', 'Part-time', 'Contract', 'Internship', 'Temporary')
VALID_WORK_MODES = ('On-site', 'Remote', 'Hybrid')


def normalize_employment_type(value) -> Optional[str]:
    """Full-time / Part-time / Contract / Internship / Temporary / None.

    Terms such as 'Regular', 'On-roll', 'Professional' or 'Lateral - Below AVP'
    describe grade or payroll status, NOT working hours, so they are *not*
    mapped (None) rather than guessed.
    """
    s = clean_text(value)
    if not s:
        return None
    low = re.sub(r'[\s_\-]+', ' ', s.lower()).strip()
    if 'part time' in low or low in ('parttime', 'pt'):
        return 'Part-time'
    if 'full time' in low or low in ('fulltime', 'ft'):
        return 'Full-time'
    if 'intern' in low or 'trainee' in low or 'apprentice' in low:
        return 'Internship'
    if 'contract' in low or 'consult' in low or 'fixed term' in low or 'freelance' in low:
        return 'Contract'
    if 'temp' in low or 'seasonal' in low:
        return 'Temporary'
    return None


def normalize_work_mode(value) -> Optional[str]:
    s = clean_text(value)
    if not s:
        return None
    low = re.sub(r'[\s_\-]+', ' ', s.lower()).strip()
    if 'hybrid' in low:
        return 'Hybrid'
    if 'remote' in low or 'work from home' in low or low == 'wfh':
        return 'Remote'
    if low in ('onsite', 'on site', 'in office', 'office') or 'on site' in low or 'work from office' in low:
        return 'On-site'
    return None


# --------------------------------------------------------------------------- #
# Locations / country
# --------------------------------------------------------------------------- #
INDIA_STATES = (
    'andhra pradesh', 'arunachal pradesh', 'assam', 'bihar', 'chhattisgarh', 'goa', 'gujarat',
    'haryana', 'himachal pradesh', 'jharkhand', 'karnataka', 'kerala', 'madhya pradesh',
    'maharashtra', 'manipur', 'meghalaya', 'mizoram', 'nagaland', 'odisha', 'orissa', 'punjab',
    'rajasthan', 'sikkim', 'tamil nadu', 'telangana', 'tripura', 'uttar pradesh', 'uttarakhand',
    'west bengal', 'delhi', 'new delhi', 'chandigarh', 'puducherry', 'pondicherry',
    'jammu and kashmir', 'jammu & kashmir', 'ladakh', 'dadra and nagar haveli', 'daman and diu',
)
INDIA_CITIES = (
    'mumbai', 'pune', 'bengaluru', 'bangalore', 'chennai', 'hyderabad', 'kolkata', 'ahmedabad',
    'gurgaon', 'gurugram', 'noida', 'jaipur', 'lucknow', 'nagpur', 'nashik', 'vizag',
    'visakhapatnam', 'patna', 'kochi', 'coimbatore', 'indore', 'bhopal', 'surat', 'vadodara',
    'thane', 'navi mumbai', 'faridabad', 'ghaziabad', 'bhubaneswar', 'mysore', 'mysuru',
    'mangalore', 'mangaluru', 'thiruvananthapuram', 'trivandrum', 'vijayawada', 'guntur',
    'warangal', 'tiruchirappalli', 'madurai', 'salem', 'hosur', 'vellore', 'hubli', 'belgaum',
    'aurangabad', 'solapur', 'kolhapur', 'rajkot', 'jamnagar', 'bhavnagar', 'bharuch', 'ankleshwar',
    'vapi', 'valsad', 'gandhinagar', 'mundra', 'dahej', 'hazira', 'sanand', 'halol', 'udaipur',
    'jodhpur', 'kota', 'bikaner', 'ajmer', 'alwar', 'neemrana', 'bhiwadi', 'ludhiana', 'amritsar',
    'jalandhar', 'mohali', 'panchkula', 'ambala', 'karnal', 'panipat', 'sonipat', 'rohtak',
    'hisar', 'manesar', 'bawal', 'dehradun', 'haridwar', 'roorkee', 'rudrapur', 'pantnagar',
    'kanpur', 'agra', 'varanasi', 'prayagraj', 'allahabad', 'meerut', 'bareilly', 'aligarh',
    'moradabad', 'gorakhpur', 'greater noida', 'ranchi', 'jamshedpur', 'dhanbad', 'bokaro',
    'raipur', 'bilaspur', 'bhilai', 'korba', 'cuttack', 'rourkela', 'sambalpur', 'jharsuguda',
    'angul', 'kalinganagar', 'paradeep', 'guwahati', 'dibrugarh', 'silchar', 'shillong', 'gangtok',
    'agartala', 'imphal', 'aizawl', 'kohima', 'itanagar', 'panaji', 'vasco', 'margao', 'baddi',
    'solan', 'shimla', 'jammu', 'srinagar', 'leh',
)
# Countries that appear in global ATS feeds. Used only to *reject* India labelling.
_FOREIGN = (
    'united states', 'usa', 'u.s.', 'united kingdom', 'uk', 'germany', 'netherlands', 'australia',
    'vietnam', 'philippines', 'thailand', 'sri lanka', 'indonesia', 'malaysia', 'singapore',
    'china', 'japan', 'south africa', 'morocco', 'canada', 'france', 'italy', 'spain', 'brazil',
    'mexico', 'turkey', 'uae', 'united arab emirates', 'dubai', 'cambodia', 'pakistan',
    'bangladesh', 'nepal', 'switzerland', 'sweden', 'poland', 'ireland', 'egypt', 'kenya',
    'nigeria', 'ghana', 'ethiopia', 'tanzania', 'uganda', 'saudi arabia', 'qatar', 'oman',
    'kuwait', 'bahrain', 'israel', 'south korea', 'korea', 'taiwan', 'hong kong', 'new zealand',
    'argentina', 'chile', 'colombia', 'peru', 'belgium', 'austria', 'denmark', 'norway', 'finland',
    'portugal', 'greece', 'czechia', 'czech republic', 'hungary', 'romania',
)
_US_STATE_SUFFIX = re.compile(r',\s*(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY)\b')


def _has_word(hay: str, needle: str) -> bool:
    return re.search(r'(?<![a-z])' + re.escape(needle) + r'(?![a-z])', hay) is not None


def infer_country(location: Optional[str], explicit_country: Optional[str] = None) -> Optional[str]:
    """
    Country is taken from the source if the source states one, otherwise from the
    location text *only when unambiguous*. Returns None if unknown (never defaults to India).
    """
    ec = clean_text(explicit_country)
    if ec:
        low = ec.lower()
        if low in ('in', 'ind', 'india', 'republic of india'):
            return 'India'
        for f in _FOREIGN:
            if low == f:
                return {'usa': 'United States', 'u.s.': 'United States', 'uk': 'United Kingdom',
                        'uae': 'United Arab Emirates', 'dubai': 'United Arab Emirates'}.get(f, f.title())
        return ec
    loc = clean_text(location)
    if not loc:
        return None
    low = loc.lower()
    if re.search(r',\s*(in|ind|india)$', low) or _has_word(low, 'india'):
        return 'India'
    for f in _FOREIGN:
        if _has_word(low, f):
            return {'usa': 'United States', 'u.s.': 'United States', 'uk': 'United Kingdom',
                    'uae': 'United Arab Emirates', 'dubai': 'United Arab Emirates'}.get(f, f.title())
    if _US_STATE_SUFFIX.search(loc):
        return 'United States'
    if any(_has_word(low, s) for s in INDIA_STATES) or any(_has_word(low, c) for c in INDIA_CITIES):
        return 'India'
    return None


def is_india_location(location: Optional[str], explicit_country: Optional[str] = None) -> bool:
    return infer_country(location, explicit_country) == 'India'


def split_location(location: Optional[str]):
    """'Noida, Uttar Pradesh' -> ('Noida', 'Uttar Pradesh'); duplicate parts removed."""
    loc = clean_text(location)
    if not loc:
        return None, None
    parts = []
    for p in (x.strip() for x in loc.split(',')):
        if p and p.lower() not in [q.lower() for q in parts] and p.upper() not in ('IN', 'IND') and p.lower() != 'india':
            parts.append(p)
    state = None
    for p in parts:
        if p.lower() in INDIA_STATES:
            state = p
            break
    city = parts[0] if parts and parts[0] != state else None
    return city, state


# --------------------------------------------------------------------------- #
# URLs
# --------------------------------------------------------------------------- #
_SR_API = re.compile(r'^https?://api\.smartrecruiters\.com/v1/companies/([^/]+)/postings/([^/?#]+)', re.I)


def normalize_application_url(url: Optional[str]) -> Optional[str]:
    """Convert machine (API) URLs to the human job page; reject non-http(s) and search engines."""
    u = clean_text(url)
    if not u:
        return None
    if 'google.com/search' in u.lower() or 'bing.com/search' in u.lower():
        return None
    m = _SR_API.match(u)
    if m:
        return f"https://jobs.smartrecruiters.com/{m.group(1)}/{m.group(2)}"
    if not re.match(r'^https?://', u, re.I):
        return None
    return u.replace(' ', '%20')


_GENERIC_PATH = re.compile(
    r'^/?(?:[a-z]{2}(?:-[a-z]{2})?/)?(?:careers?|jobs?|search|openings?|opportunities|join-us|work-with-us|about-us/careers|personal/about-us/careers)?/?(?:index\.(?:html?|aspx?|php))?$',
    re.I)


def is_generic_landing_url(url: Optional[str]) -> bool:
    """True for site roots / careers index pages that cannot identify ONE job."""
    u = clean_text(url)
    if not u:
        return True
    p = urlparse(u)
    if p.query and re.search(r'(job|req|posting|id| vacancy)=', p.query, re.I):
        return False
    return bool(_GENERIC_PATH.match(p.path or '/'))


# --------------------------------------------------------------------------- #
# CSR & Contact Integrity Helpers
# --------------------------------------------------------------------------- #
_GENERIC_CSR_PAGE_TITLES = {
    'csr', 'corporate social responsibility', 'social responsibility', 'sustainability',
    'esg', 'environmental social governance', 'home', 'homepage', 'welcome', 'about',
    'about us', 'who we are', 'overview', 'our approach', 'our vision', 'our mission',
    'csr policy', 'csr overview', 'csr activities', 'csr initiatives', 'csr projects',
    'csr programmes', 'csr programs', 'csr disclosures', 'csr report', 'csr reports',
    'annual report', 'annual reports', 'brsr', 'business responsibility', 'investor relations',
    'investors', 'contact', 'contact us', 'reach us', 'get in touch', 'media', 'news',
    'press releases', 'careers', 'jobs', 'privacy policy', 'disclaimer', 'terms of use',
    'terms & conditions', 'terms and conditions', 'sitemap', 'login', 'sign in',
    '404', 'page not found', 'not found', 'error', 'access denied', 'forbidden',
    'know more', 'read more', 'learn more', 'view details', 'click here', 'download',
    'download pdf', 'view pdf', 'community', 'community development', 'foundation',
    'corporate citizen', 'corporate citizenship', 'social impact', 'giving back',
}


def is_page_title_not_csr_project(name: Optional[str], company_name: Optional[str] = None) -> bool:
    """
    Returns True when a putative CSR 'project_name' is actually just a webpage
    title, navigation item, or company name header rather than a real CSR project.
    """
    s = clean_text(name)
    if not s or len(s) < 4:
        return True
    low = re.sub(r'\s+', ' ', s.lower()).strip()
    if low in _GENERIC_CSR_PAGE_TITLES:
        return True
    # Strip company name and common legal suffixes to see if only a generic page title remains
    stripped = low
    if company_name:
        cn_low = company_name.lower().strip()
        for suffix in (' limited', ' ltd.', ' ltd', ' pvt', ' private', ' india', ' corp', ' corporation'):
            if cn_low.endswith(suffix):
                cn_base = cn_low[:-len(suffix)].strip()
                if cn_base and len(cn_base) >= 3:
                    stripped = stripped.replace(cn_base, ' ')
        stripped = stripped.replace(cn_low, ' ')
    # Split by common HTML <title> separators (|, -, –, —, :, ::, »)
    segments = [
        re.sub(r'\b(limited|ltd|india|group|company|corp|corporation)\b', '', seg).strip(' .,-–—|:»/\\')
        for seg in re.split(r'\s*[\|\-–—:»/]\s*', stripped)
    ]
    non_empty = [seg for seg in segments if seg]
    if not non_empty:
        return True
    if all(seg in _GENERIC_CSR_PAGE_TITLES for seg in non_empty):
        return True
    return False


_GENERIC_EMAIL_PREFIXES = {
    'info', 'information', 'webmaster', 'support', 'help', 'helpdesk', 'customercare',
    'customerservice', 'customer.care', 'customer.service', 'care', 'service', 'sales',
    'marketing', 'billing', 'accounts', 'finance', 'investors', 'investor',
    'investor.relations', 'investorrelations', 'ir', 'secretarial', 'company.secretary',
    'companysecretary', 'cs', 'careers', 'career', 'hr', 'jobs', 'recruitment', 'talent',
    'hiring', 'media', 'press', 'pr', 'communications', 'corpcomm', 'feedback', 'admin',
    'administrator', 'noreply', 'no-reply', 'donotreply', 'do-not-reply', 'security',
    'privacy', 'legal', 'compliance', 'grievance', 'nodalofficer', 'enquiries', 'enquiry',
    'inquiry', 'inquiries', 'contact', 'contactus', 'contact.us', 'office', 'mail',
    'hello', 'general', ' reception', 'postmaster', 'hostmaster', 'abuse',
}
_CSR_EMAIL_KEYWORDS = ('csr', 'foundation', 'sustainab', 'impact', 'philanthrop', 'social', 'trust', 'esg', 'community')


def is_generic_or_non_csr_contact_email(email: Optional[str]) -> bool:
    """
    Returns True if the email is empty, invalid, or a generic non-CSR role mailbox
    (e.g. info@, webmaster@, customercare@, investors@, careers@) unless the mailbox
    or domain is specifically dedicated to CSR/Foundation/Sustainability.
    """
    s = clean_text(email)
    if not s or '@' not in s:
        return True
    s_low = s.lower().strip()
    local, _, domain = s_low.partition('@')
    if not local or not domain or '.' not in domain:
        return True
    # If either the local mailbox or the domain explicitly indicates CSR/Foundation, keep it
    if any(k in local for k in _CSR_EMAIL_KEYWORDS):
        return False
    # If the domain is a dedicated foundation domain (e.g. @reliancefoundation.org), allow contact@/info@
    if any(k in domain for k in ('foundation', 'trust', 'philanthrop')):
        if local not in ('webmaster', 'noreply', 'no-reply', 'donotreply', 'postmaster', 'abuse'):
            return False
    local_norm = re.sub(r'[0-9_\-\.]+$', '', local)
    if local in _GENERIC_EMAIL_PREFIXES or local_norm in _GENERIC_EMAIL_PREFIXES:
        return True
    return False


def detect_csr_source_format(url: Optional[str]) -> str:
    """
    Classifies how CSR data is published at the given URL (Webpage, PDF Document,
    Foundation Portal, Sustainability/ESG Page, BRSR/Annual Report, or Not available).
    """
    u = clean_text(url)
    if not u or not re.match(r'^https?://', u, re.I) or 'google.com/search' in u.lower():
        return NOT_AVAILABLE_TEXT
    low = u.lower()
    parsed = urlparse(low)
    path_and_query = (parsed.path or '') + '?' + (parsed.query or '')
    if '.pdf' in path_and_query:
        if 'brsr' in path_and_query:
            return 'PDF Document (BRSR Filing)'
        if 'annual' in path_and_query:
            return 'PDF Document (Annual Report)'
        return 'PDF Document (CSR Disclosure)'
    if 'foundation' in (parsed.netloc or '') or 'foundation' in (parsed.path or ''):
        return 'Foundation Portal Webpage'
    if 'brsr' in path_and_query:
        return 'BRSR Disclosure Webpage'
    if 'sustainab' in path_and_query or 'esg' in path_and_query:
        return 'Sustainability / ESG Webpage'
    return 'CSR Webpage'


# --------------------------------------------------------------------------- #
# Canonical URL & Fingerprint Helpers
# --------------------------------------------------------------------------- #
_TRACKING_PARAMS = {
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
    'gclid', 'fbclid', 'ref', 'source', 'mc_eid', '_ga', 'ncid', 'yclid',
    '_hsenc', '_hsmi', 'tracking_id', 'trid'
}


def normalize_canonical_url(url: Optional[str], base_url: Optional[str] = None) -> Optional[str]:
    """
    Cleans, strips tracking parameters, fragments (including #:~:text=),
    resolves relative paths, and ensures standard scheme/host.
    """
    raw = clean_text(url)
    if not raw:
        return None

    # Resolve relative URL against base_url if applicable
    if base_url and not re.match(r'^[a-z]+://', raw, re.I):
        try:
            raw = urljoin(base_url, raw)
        except Exception:
            pass

    # Strip fragments completely (especially #:~:text=...)
    raw = raw.split('#')[0].strip()
    if not raw or not re.match(r'^https?://', raw, re.I):
        return None

    try:
        parsed = urlparse(raw)
        scheme = parsed.scheme.lower()
        # Default/prefer https
        if scheme == 'http' and not parsed.netloc.startswith('localhost') and not parsed.netloc.startswith('127.0.0.1'):
            scheme = 'https'
        netloc = parsed.netloc.lower()

        # Parse query params, filtering out known tracking / telemetry keys
        query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
        clean_pairs = [
            (k, v) for k, v in query_pairs
            if k.lower() not in _TRACKING_PARAMS and not k.lower().startswith('utm_')
        ]
        # Sort query keys for determinism
        clean_pairs.sort(key=lambda x: x[0])
        clean_query = urlencode(clean_pairs) if clean_pairs else ''

        path = parsed.path or ''
        # Normalize double slashes in path
        path = re.sub(r'/{2,}', '/', path)
        # Strip trailing slash
        if path.endswith('/'):
            path = path[:-1]

        canonical = f"{scheme}://{netloc}{path}"
        if clean_query:
            canonical = f"{canonical}?{clean_query}"
        return canonical
    except Exception:
        return raw.split('#')[0].strip()


def build_job_fingerprint(
    company_id: str,
    external_job_id: Optional[str] = None,
    canonical_url: Optional[str] = None,
    title: Optional[str] = None,
    location: Optional[str] = None,
) -> str:
    """
    Builds a robust, deterministic fingerprint for a job.
    Priority:
    1. company_id + external_job_id (if available)
    2. company_id + canonical_url (if available and not generic)
    3. company_id + normalized title + normalized location
    """
    c_id = str(company_id).strip()
    ext_id = clean_text(external_job_id)
    if ext_id:
        seed = f"{c_id}_ext_{ext_id}"
        return hashlib.sha256(seed.encode('utf-8')).hexdigest()

    canon = clean_text(canonical_url)
    if canon:
        norm_url = normalize_canonical_url(canon) or canon
        seed = f"{c_id}_url_{norm_url}"
        return hashlib.sha256(seed.encode('utf-8')).hexdigest()

    norm_t = (clean_text(title) or "").lower()
    norm_l = (clean_text(location) or "").lower()
    seed = f"{c_id}_title_{norm_t}_loc_{norm_l}"
    return hashlib.sha256(seed.encode('utf-8')).hexdigest()


# --------------------------------------------------------------------------- #
# Junk Filtering & ATS Pattern Detection
# --------------------------------------------------------------------------- #
_ATS_CONFIG_CACHE: Optional[List[Dict[str, Any]]] = None

def load_ats_patterns(config_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Loads ATS pattern definitions from config/ats_domains.json."""
    global _ATS_CONFIG_CACHE
    if _ATS_CONFIG_CACHE is not None and config_path is None:
        return _ATS_CONFIG_CACHE

    path = config_path or (Path(__file__).resolve().parents[2] / "config" / "ats_domains.json")
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            patterns = data.get("ats_list", [])
            if config_path is None:
                _ATS_CONFIG_CACHE = patterns
            return patterns
    except Exception:
        pass
    return []


def match_ats_pattern(url: str, ats_patterns: Optional[List[Dict[str, Any]]] = None) -> Optional[Dict[str, Any]]:
    """
    Checks if a URL matches any known ATS career-site patterns.
    Returns dict with platform and matched pattern, or None.
    """
    if not url:
        return None
    patterns = ats_patterns if ats_patterns is not None else load_ats_patterns()
    parsed = urlparse(url)
    host = (parsed.netloc or '').lower()

    for item in patterns:
        platform = item.get("platform", "Unknown_ATS")
        # 1. Check specific regex url_patterns first
        for pat in item.get("url_patterns", []):
            try:
                if re.match(pat, url, re.IGNORECASE):
                    return {
                        "platform": platform,
                        "matched_rule": pat,
                        "match_type": "url_pattern",
                        "host": host
                    }
            except re.error:
                continue

        # 2. Check host_patterns
        for h_pat in item.get("host_patterns", []):
            h_pat_low = h_pat.lower()
            if fnmatch.fnmatch(host, h_pat_low) or (h_pat_low.startswith("*.") and host.endswith(h_pat_low[1:])):
                return {
                    "platform": platform,
                    "matched_rule": h_pat,
                    "match_type": "host_pattern",
                    "host": host
                }

    return None


_JUNK_SCHEMES = ("mailto:", "tel:", "javascript:", "whatsapp:", "sms:", "callto:")
_JUNK_EXTENSIONS = (
    ".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".mp4", ".mp3", ".avi", ".mov", ".zip", ".tar", ".gz", ".exe", ".dmg",
    ".apk", ".woff", ".woff2", ".ttf", ".eot"
)
_SOCIAL_DOMAINS = (
    "facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "pinterest.com", "whatsapp.com", "t.me", "telegram.org", "reddit.com"
)
_JUNK_PATH_TOKENS = (
    "privacy-policy", "privacy_policy", "privacypolicy", "terms-of-use", "terms-and-conditions",
    "terms_and_conditions", "terms-conditions", "termsofuse", "cookie-policy", "cookie_policy",
    "cookiepolicy", "disclaimer", "legal-notice", "accessibility-statement", "skip-to-content",
    "login", "signin", "sign-in", "signup", "sign-up", "register", "forgot-password",
    "reset-password", "client-login", "user-login", "logout", "cart", "checkout",
    "buy-now", "add-to-cart", "branch-locator", "atm-locator", "store-locator",
    "page-not-found", "page-not-foud", "pagenotfound", "error-404", "/404", "not-found",
)


def is_junk_url(url: Optional[str], link_text: Optional[str] = None) -> Tuple[bool, str]:
    """
    Identifies whether a candidate URL is irrelevant noise/junk:
    - Protocol junk (mailto, tel, javascript)
    - Social media networks and generic share links
    - Static media/code assets
    - Authentication/login screens
    - Legal notices, privacy, cookie policy, disclaimers
    - Consumer retail, loan applications, banking tools, cart/checkout
    """
    raw = (url or "").strip()
    if not raw or raw.startswith("#"):
        return True, "empty or fragment-only link"

    raw_lower = raw.lower()
    if any(raw_lower.startswith(scheme) for scheme in _JUNK_SCHEMES):
        return True, "non-http protocol link"

    parsed = urlparse(raw)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    text = (link_text or "").lower().strip()

    # Asset extensions
    clean_path = path.split("?")[0]
    if any(clean_path.endswith(ext) for ext in _JUNK_EXTENSIONS):
        return True, "static asset/media file"

    # Social media domains
    if any(s_dom in host for s_dom in _SOCIAL_DOMAINS):
        return True, "social media platform"
    if "linkedin.com" in host and any(p in path for p in ("/share", "/sharing", "/in/")):
        return True, "social share link"

    # Junk path tokens
    for token in _JUNK_PATH_TOKENS:
        if token in path:
            return True, f"junk path token ({token})"

    # Junk link text checks
    if text:
        text_clean = re.sub(r'\s+', ' ', text)
        if any(token in text_clean for token in (
            "privacy policy", "terms of use", "terms & conditions", "terms and conditions",
            "cookie policy", "disclaimer", "legal notice", "accessibility statement",
            "skip to content", "skip to main content", "login", "sign in", "sign up",
            "register", "customer login", "client login", "personal loan", "credit card",
            "apply for loan", "track application", "fixed deposit", "netbanking", "branch locator"
        )):
            return True, f"junk link text phrase ({text_clean[:30]})"

    return False, ""


