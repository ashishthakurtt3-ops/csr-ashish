"""
modules/crawler_engine/homepage_verifier.py
===========================================
Enterprise Homepage Verification and Self-Correction Engine.

Implements automated multi-tier verification and correction for corporate homepages:
1. Variants First:
   - www vs non-www, http -> https
   - country subpaths (/in, /en-in, /india, or stripping them to root)
   - final redirect target resolution
   - DNS failure and parked domain detection
2. Structured Sources (Plug-in Architecture):
   - Wikidata (property P856 official website, via ISIN or entity search)
   - Exchange data (NSE/BSE, terms-governed, togglable)
   - Each plug-in is fully decoupled and configurable
3. AI Suggestion Fallback:
   - Google Gemini Flash (official API free tier only)
   - Web search grounding when available
   - Strict zero-cost policy, SQLite persistent cache, and quota checkpoints
   - AI outputs are treated strictly as unverified suggestions
4. Deterministic Code Validation:
   - HTTP 200 after all redirects
   - Title/header content matching company name and short brand
   - Strong statutory signal if page / investor section displays company's CIN or ISIN
   - Strict rejection of news portals, directories, job boards, parked domains, and social profiles
5. Confidence Routing:
   - HIGH (>= 70): Auto-update website_url and archive previous URL in website_url_history
   - MEDIUM (40-69): Route to REVIEW_REQUIRED with evidence notes
   - NONE (< 40): Mark HOMEPAGE_NOT_FOUND
6. Inviolable Safety Guards:
   - Never overwrite a locked website_url (website_url_locked == True)
   - Never accept an AI suggestion that fails code validation
7. Monthly Scheduling Support:
   - Supports 30-day freshness checks
"""

from __future__ import annotations

import os
import re
import json
import time
import socket
import logging
import hashlib
from typing import Optional, List, Dict, Any, Tuple
from urllib.parse import urlparse, urlunparse, urljoin
from dataclasses import dataclass, field

def safe_now():
    """Returns current timezone-aware UTC datetime, safe if Django settings are unconfigured."""
    try:
        from django.conf import settings
        if getattr(settings, 'configured', False):
            from django.utils import timezone
            return timezone.now()
    except Exception:
        pass
    import datetime
    return datetime.datetime.now(datetime.timezone.utc)

try:
    from django.conf import settings
    WIKIDATA_ENABLED = getattr(settings, 'HOMEPAGE_WIKIDATA_ENABLED', True)
    EXCHANGE_DATA_ENABLED = getattr(settings, 'HOMEPAGE_EXCHANGE_DATA_ENABLED', False)
    AI_FALLBACK_ENABLED = getattr(settings, 'HOMEPAGE_AI_FALLBACK_ENABLED', True)
except Exception:
    WIKIDATA_ENABLED = True
    EXCHANGE_DATA_ENABLED = False
    AI_FALLBACK_ENABLED = True

from curl_cffi import requests as cffi_requests
from modules.crawler_engine import ai_classifier_config as cfg
from modules.crawler_engine.ai_api_client import PersistentDiskCache, get_ai_client, QuotaExhaustedError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 12
USER_AGENT_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# -----------------------------------------------------------------------------
# Negative Domain Lists & Parked Fingerprints
# -----------------------------------------------------------------------------
DISALLOWED_DOMAINS = {
    # News & Media
    "economictimes.indiatimes.com", "timesofindia.indiatimes.com", "moneycontrol.com",
    "financialexpress.com", "business-standard.com", "livemint.com", "ndtv.com",
    "thehindu.com", "cnbctv18.com", "reuters.com", "bloomberg.com", "forbes.com",
    "wsj.com", "ft.com", "hindustantimes.com", "indianexpress.com",
    # Directories & Corporate Aggregators
    "zaubacorp.com", "tofler.in", "screener.in", "wikipedia.org", "wikidata.org",
    "zoominfo.com", "crunchbase.com", "instafinancials.com", "indiamart.com",
    "justdial.com", "tradeindia.com", "owler.com",
    # Job Boards & Staffing Portals
    "naukri.com", "indeed.com", "monster.com", "shine.com", "foundit.in",
    "glassdoor.com", "linkedin.com", "simplyhired.com", "timesjobs.com",
    # Social Media
    "facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "github.com", "pinterest.com",
    # Domain Registrars / Parking platforms
    "hugedomains.com", "sedoparking.com", "sedo.com", "dan.com", "bodis.com",
    "parkingcrew.com", "domainmarket.com", "afternic.com", "godaddy.com",
    "namecheap.com", "domain.com", "undeveloped.com"
}

PARKED_DOMAIN_KEYWORDS = [
    "domain is parked",
    "this domain is for sale",
    "buy this domain",
    "domain has expired",
    "parked free",
    "sedo",
    "sedoparking",
    "hugedomains",
    "dan.com",
    "bodis",
    "parkingcrew",
    "godaddy.com/park",
    "domainmarket",
    "afternic",
    "renew your domain",
    "domain name is available",
    "inquire about this domain",
    "domain may be for sale",
    "is for sale on",
    "buy now for $"
]

CORPORATE_PAGE_SIGNALS = [
    "investor relations", "investors", "annual report", "corporate governance",
    "board of directors", "about us", "who we are", "sustainability",
    "corporate social responsibility", "csr", "financial results", "shareholder"
]


@dataclass
class FetchResult:
    url: str
    status_code: Optional[int] = None
    final_url: Optional[str] = None
    html: str = ""
    error: Optional[str] = None
    is_dns_failure: bool = False
    redirect_chain: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    valid: bool
    confidence: str  # 'HIGH', 'MEDIUM', 'NONE'
    score: int
    candidate_url: str
    final_url: str
    source: str
    reasons: List[str] = field(default_factory=list)
    statutory_match: bool = False
    brand_match: bool = False
    is_parked: bool = False
    is_disallowed: bool = False
    identity_evidence: bool = False
    identity_evidence_detail: str = ""
    same_legal_entity: bool = True
    wrong_entity_reason: Optional[str] = None


# -----------------------------------------------------------------------------
# 1. Network Fetching, DNS Checking & Diagnostics
# -----------------------------------------------------------------------------
def check_dns_resolution(hostname: str) -> bool:
    """
    Checks whether a hostname resolves via system DNS.
    Returns True if DNS resolves successfully, False on NXDOMAIN or socket error.
    """
    clean_host = hostname.split(':')[0].strip().lower()
    if not clean_host:
        return False
    try:
        socket.getaddrinfo(clean_host, None)
        return True
    except (socket.gaierror, socket.herror, OSError):
        return False


FOREIGN_CCTLDS = {
    "mx", "br", "ru", "de", "fr", "es", "it", "pl", "nl", "se", "no", "dk",
    "fi", "ch", "at", "cz", "ar", "cl", "za", "kr", "jp", "sg", "my", "id",
    "th", "vn", "ph", "nz", "eg", "ng", "ke", "pk", "bd", "lk", "ae", "sa"
}


def is_disallowed_domain(url: str) -> Tuple[bool, str]:
    """
    Checks if the candidate URL domain is a known news site, directory,
    job board, social network, domain parking registrar, or foreign country ccTLD.
    """
    if not url:
        return True, "empty_url"
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower().split(':')[0]
        # Strip common subdomains
        if netloc.startswith("www."):
            base_domain = netloc[4:]
        else:
            base_domain = netloc

        # Reject foreign country code top level domains for Indian corporations
        tld = netloc.split('.')[-1]
        if tld in FOREIGN_CCTLDS:
            return True, f"foreign_country_cctld:.{tld}"

        for disallowed in DISALLOWED_DOMAINS:
            if base_domain == disallowed or base_domain.endswith("." + disallowed) or netloc == disallowed:
                return True, f"disallowed_domain:{disallowed}"
        return False, "ok"
    except Exception as e:
        return True, f"malformed_url:{str(e)}"


def is_parked_domain_content(html: str, url: str) -> Tuple[bool, str]:
    """
    Detects parked domain pages by inspecting HTML title, headers, and text fingerprints.
    """
    if not html:
        return False, "ok"

    lower_html = html.lower()

    # Title check
    title_match = re.search(r'<title[^>]*>(.*?)</title>', lower_html, re.IGNORECASE | re.DOTALL)
    title_text = title_match.group(1).strip() if title_match else ""

    for kw in PARKED_DOMAIN_KEYWORDS:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, title_text, re.IGNORECASE):
            return True, f"parked_keyword_in_title:'{kw}'"
        if re.search(pattern, lower_html[:5000], re.IGNORECASE):
            return True, f"parked_keyword_in_body:'{kw}'"

    return False, "ok"


def _raw_fetch(url: str, timeout: int = DEFAULT_TIMEOUT) -> FetchResult:
    """Internal fetch helper executing curl_cffi HTTP request."""
    try:
        parsed = urlparse(url)
        hostname = parsed.netloc
    except Exception as e:
        return FetchResult(url=url, error=f"invalid_url_syntax:{str(e)}")

    if not check_dns_resolution(hostname):
        return FetchResult(url=url, error=f"DNS_RESOLUTION_FAILED:{hostname}", is_dns_failure=True)

    try:
        resp = cffi_requests.get(
            url,
            impersonate="chrome124",
            timeout=timeout,
            allow_redirects=True,
            verify=False,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": USER_AGENT_DESKTOP,
            }
        )
        final_target = resp.url or url
        html_text = ""
        try:
            html_text = resp.text
        except Exception:
            try:
                html_text = resp.content.decode("utf-8", errors="ignore")
            except Exception:
                html_text = ""

        return FetchResult(
            url=url,
            status_code=resp.status_code,
            final_url=final_target,
            html=html_text,
            error=None if resp.status_code == 200 else f"HTTP_{resp.status_code}"
        )
    except Exception as e:
        err_str = str(e)
        is_dns = "getaddrinfo" in err_str.lower() or "name resolution" in err_str.lower()
        return FetchResult(
            url=url,
            error=err_str,
            is_dns_failure=is_dns
        )


def fetch_candidate_page(url: str, timeout: int = DEFAULT_TIMEOUT) -> FetchResult:
    """
    Safely fetches a candidate homepage using curl_cffi with Chrome 124 TLS fingerprint.
    - Unpacks bot challenge redirect URLs (e.g. validate.perfdrive.com?ssc=...)
    - Tries HTTPS first if given plaintext HTTP (modern servers reject port 80)
    - Tracks DNS failures, redirects, status codes, and final landing target.
    """
    if not url:
        return FetchResult(url=url, error="empty_url")

    # Unpack bot challenge redirect targets
    if "perfdrive.com" in url and "ssc=" in url:
        try:
            import urllib.parse
            parsed_q = urllib.parse.parse_qs(urlparse(url).query)
            if "ssc" in parsed_q and parsed_q["ssc"]:
                url = parsed_q["ssc"][0]
        except Exception:
            pass

    # Ensure valid scheme
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    # If plaintext http://, try https:// first
    if url.startswith("http://"):
        https_url = "https://" + url[7:]
        https_res = _raw_fetch(https_url, timeout=timeout)
        if https_res.status_code == 200:
            return https_res

    return _raw_fetch(url, timeout=timeout)


# -----------------------------------------------------------------------------
# 2. Variant Generator (Stage 1)
# -----------------------------------------------------------------------------
def clean_tokens_for_company(company_name: str, nse_symbol: Optional[str] = None) -> List[str]:
    """
    Extracts brand and distinct tokens from corporate name for content matching.
    Removes standard corporate suffixes like 'Limited', 'Ltd', 'Pvt', etc.
    Keeps 'India' when it is an entity differentiator (e.g. 'ABB India', 'Nestle India').
    Optionally incorporates NSE ticker symbol for statutory corporate identification.
    """
    tokens = []
    if nse_symbol and len(nse_symbol.strip()) >= 2:
        tokens.append(nse_symbol.strip().upper())

    if not company_name:
        return tokens

    name = company_name.strip()
    # Strip parentheticals
    name = re.sub(r'\(.*?\)', '', name).strip()

    # Strip prefixes like Dr., Dr, Shri, M/s
    name = re.sub(r'^(dr\.|dr|shri|m/s)\s+', '', name, flags=re.IGNORECASE).strip()

    # Standard corporate stopwords (do NOT strip 'India' unconditionally!)
    stopwords = {
        'limited', 'ltd', 'private', 'pvt', 'corporation', 'corp',
        'enterprises', 'industries', 'holdings', 'company', 'co',
        'the', 'and', '&', 'plc', 'llc', 'inc'
    }

    words = re.findall(r'[A-Za-z0-9]+', name)
    cleaned_words = [w for w in words if w.lower() not in stopwords]

    # Full stripped name
    if cleaned_words:
        full_brand = " ".join(cleaned_words)
        tokens.append(full_brand)
        # Also stripped without 'India' if 'India' is present
        words_no_india = [w for w in cleaned_words if w.lower() != 'india']
        if words_no_india and len(words_no_india) < len(cleaned_words):
            tokens.append(" ".join(words_no_india))

        # Acronym if multiple words (e.g., TCS for Tata Consultancy Services)
        if len(cleaned_words) >= 2:
            acronym = "".join(w[0] for w in cleaned_words).upper()
            if len(acronym) >= 2:
                tokens.append(acronym)
            # Bigrams
            for i in range(len(cleaned_words) - 1):
                tokens.append(f"{cleaned_words[i]} {cleaned_words[i+1]}")
        # Individual words if distinct (e.g., "ABB", "Infosys", "Wipro", "Blackbio", "Lal")
        for w in cleaned_words:
            if len(w) >= 3 and w.lower() not in ('group', 'india', 'tech', 'dx'):
                tokens.append(w)

    return list(dict.fromkeys(tokens))


def normalize_url_for_comparison(u: Optional[str]) -> str:
    """
    Normalizes a URL for semantic equality comparison to detect no-ops.
    Strips schemes (http/https), port numbers, www. prefix, and trailing slashes.
    """
    if not u:
        return ""
    try:
        raw = u.strip().lower()
        if not raw.startswith("http://") and not raw.startswith("https://"):
            raw = "https://" + raw
        p = urlparse(raw)
        netloc = p.netloc.split(':')[0]
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = p.path.rstrip('/')
        return f"{netloc}{path}"
    except Exception:
        return (u or "").strip().lower().rstrip('/')


def is_wrong_entity_or_parent(candidate_url: str, html: str, company: Any) -> Tuple[bool, str]:
    """
    Wrong-Entity Guard:
    Prevents replacing an entity's official website with a parent, subsidiary, or sister company.
    Path-stripping and domain normalization may only be accepted if the new page still names
    the same legal entity.

    Enforces:
    1. United Spirits: Reject 'theubgroup.com' and any UB Group domains unconditionally.
       United Spirits operates under Diageo India (diageoindia.com).
    2. ABB India: Reject 'abb.com/global/en' or root 'abb.com' without '/indian-subcontinent'.
       ABB India must NOT become abb.com/global/en (the India site is https://new.abb.com/indian-subcontinent).
    3. Bajaj Finance: Reject 'bajajfinserv.in' root and 'aboutbajajfinserv.com'.
       Bajaj Finance must NOT become bajajfinserv.in or aboutbajajfinserv.com.
    4. Oracle Financial Services Software: Reject generic Oracle parent product pages
       like 'oracle.com/financial-services/' or root 'oracle.com' unless the page
       specifically names 'Oracle Financial Services Software' or 'OFSS'.
    5. Conglomerate & Subsidiary Discriminators:
       If the legal/company name contains an entity discriminator ('India', 'Finance',
       'Financial Services', 'Capital', 'Securities', 'Housing', 'Power', 'Infra',
       'Diagnostics', 'Consumer'):
       Path-stripping or domain replacement to a parent conglomerate domain is REJECTED
       if the target page does not name that specific legal entity/subsidiary.
    """
    comp_name = (getattr(company, 'company_name', '') or '').lower()
    legal_name = (getattr(company, 'legal_name', '') or '').lower()
    cand_url_lower = (candidate_url or '').lower()
    html_lower = (html or '').lower()

    # 1. Special guard for United Spirits: official operational site is diageoindia.com, NOT theubgroup.com
    if 'united spirits' in comp_name or 'united spirits' in legal_name:
        if 'theubgroup.com' in cand_url_lower or 'ubgroup' in cand_url_lower:
            return True, "Historical holding entity rejected: United Spirits operates under Diageo India (diageoindia.com), NOT UB Group (theubgroup.com)."

    # 2. ABB India: must NOT become abb.com/global/en or generic abb.com
    if 'abb india' in comp_name or 'abb india' in legal_name:
        if 'abb.com' in cand_url_lower:
            if 'indian-subcontinent' not in cand_url_lower and 'abb india' not in html_lower[:6000]:
                return True, "Global parent portal rejected: ABB India must NOT become abb.com/global/en (the India site is https://new.abb.com/indian-subcontinent)."

    # 3. Bajaj Finance: must NOT become bajajfinserv.in or aboutbajajfinserv.com (parent Bajaj Finserv)
    if ('bajaj finance' in comp_name or 'bajaj finance' in legal_name) and 'bajaj finserv' not in comp_name:
        parsed_cand = urlparse(cand_url_lower)
        if 'bajajfinserv' in parsed_cand.netloc:
            if parsed_cand.path.rstrip('/') in ('', '/') or 'aboutbajajfinserv' in parsed_cand.netloc:
                return True, "Parent company portal rejected: Bajaj Finance must NOT become bajajfinserv.in or aboutbajajfinserv.com."

    # 4. Oracle Financial Services Software: must NOT become Oracle parent product page
    if 'oracle financial services' in comp_name or 'oracle financial services' in legal_name or 'ofss' in comp_name:
        if 'oracle.com' in cand_url_lower:
            if 'oracle financial services' not in html_lower[:6000] and 'ofss' not in html_lower[:6000]:
                return True, "Parent product page rejected: Oracle Financial Services must NOT become the Oracle parent's product page."

    # 5. Discriminator check for path-stripping and conglomerate domains
    discriminators = [
        ('india', 'India subsidiary/entity discriminator missing on target page'),
        ('finance', 'Finance subsidiary discriminator missing on target page'),
        ('financial services', 'Financial Services entity discriminator missing on target page'),
        ('capital', 'Capital markets entity discriminator missing on target page'),
        ('securities', 'Securities brokerage entity discriminator missing on target page'),
        ('diagnostics', 'Diagnostics subsidiary discriminator missing on target page'),
        ('housing', 'Housing finance entity discriminator missing on target page'),
        ('power', 'Power subsidiary entity discriminator missing on target page'),
        ('infra', 'Infrastructure entity discriminator missing on target page'),
        ('consumer', 'Consumer products entity discriminator missing on target page'),
    ]

    orig_url = (getattr(company, 'website_url', '') or '').lower()
    for disc, msg in discriminators:
        if disc in comp_name or disc in legal_name:
            try:
                orig_net = urlparse(orig_url).netloc.replace('www.', '')
                cand_net = urlparse(cand_url_lower).netloc.replace('www.', '')
                # If path was stripped or domain changed to generic parent
                if (cand_net == orig_net and disc in orig_url and disc not in cand_url_lower) or (cand_net != orig_net):
                    if disc not in cand_url_lower and disc not in html_lower[:6000]:
                        return True, f"Wrong-entity/parent site detected: {msg}"
            except Exception:
                pass

    return False, "ok"


def generate_homepage_variants(initial_url: Optional[str], company_name: Optional[str] = None) -> List[str]:
    """
    Generates an ordered, prioritized list of candidate variants:
    1. Scheme variants: http -> https
    2. Country path variants: strip /in, /en-in, /india, or add /in
    3. Hostname variants: www. vs non-www
    4. Path stripping: remove subpaths (e.g. /home, /index.html, /default.aspx)
    5. Clean root URL
    """
    variants: List[str] = []
    if not initial_url:
        return variants

    raw_url = initial_url.strip()
    if "perfdrive.com" in raw_url and "ssc=" in raw_url:
        try:
            import urllib.parse
            parsed_q = urllib.parse.parse_qs(urlparse(raw_url).query)
            if "ssc" in parsed_q and parsed_q["ssc"]:
                raw_url = parsed_q["ssc"][0]
        except Exception:
            pass

    if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
        raw_url = "https://" + raw_url

    parsed = urlparse(raw_url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc.lower().split(':')[0]
    path = parsed.path or ""

    if not netloc:
        return variants

    # Base host without www
    bare_host = netloc[4:] if netloc.startswith("www.") else netloc
    www_host = "www." + bare_host

    # Common path normalizations
    # Country paths that might be broken or redirect targets
    country_slugs = ['/in', '/in/', '/en-in', '/en-in/', '/india', '/india/', '/global/en', '/en']
    stripped_path = path
    for slug in country_slugs:
        if stripped_path.rstrip('/').lower() == slug.rstrip('/').lower():
            stripped_path = ""
            break
        elif stripped_path.lower().startswith(slug.rstrip('/') + '/'):
            stripped_path = stripped_path[len(slug.rstrip('/')):]
            break

    # Also strip index / home slugs
    for index_slug in ['/index.html', '/index.php', '/default.aspx', '/home']:
        if stripped_path.rstrip('/').lower().endswith(index_slug):
            stripped_path = stripped_path[: -len(index_slug)]

    # 1. Clean root with HTTPS and original host
    variants.append(f"https://{netloc}/")

    # 2. Clean root with www/non-www opposite
    opposite_host = bare_host if netloc.startswith("www.") else www_host
    variants.append(f"https://{opposite_host}/")

    # 3. Country path variations if stripped path changed
    if path and path != stripped_path:
        variants.append(f"https://{netloc}{stripped_path.rstrip('/')}/")
        variants.append(f"https://{opposite_host}{stripped_path.rstrip('/')}/")

    # 4. Indian country path addition if not present
    if not any(c in path.lower() for c in ['/in', '/india']):
        variants.append(f"https://{netloc}/in")
        variants.append(f"https://{netloc}/en-in")

    # 5. Original URL normalized to HTTPS
    normalized_orig = f"https://{netloc}{path.rstrip('/')}"
    if normalized_orig not in variants:
        variants.insert(0, normalized_orig)

    # 6. HTTP fallbacks as last resort
    variants.append(f"http://{netloc}/")
    variants.append(f"http://{opposite_host}/")

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for v in variants:
        clean = v.rstrip('/')
        if clean not in seen:
            seen.add(clean)
            deduped.append(v)

    return deduped


# -----------------------------------------------------------------------------
# 3. Structured Sources Plug-ins (Stage 2)
# -----------------------------------------------------------------------------
class StructuredSourcePlugin:
    """Base interface for structured official source lookup plug-ins."""
    name: str = "base"

    def is_enabled(self) -> bool:
        raise NotImplementedError

    def lookup(self, company: Any) -> List[str]:
        raise NotImplementedError


class WikidataPlugin(StructuredSourcePlugin):
    """
    Plug-in: Looks up official website (P856) from Wikidata.
    1. First queries by ISIN (wdt:P946).
    2. Fallback searches Wikidata entities by company name / short name.
    """
    name: str = "wikidata"

    def is_enabled(self) -> bool:
        return WIKIDATA_ENABLED

    def lookup(self, company: Any) -> List[str]:
        if not self.is_enabled():
            return []

        candidates: List[str] = []
        headers = {
            "User-Agent": "CSRJobIntel/1.0 (academic research platform; mailto:admin@impactbridge.org)",
            "Accept": "application/json"
        }

        # 1. Search by ISIN via MediaWiki / SPARQL if available
        isin = getattr(company, 'isin', None)
        if isin:
            sparql_isin = f"""
            SELECT ?website WHERE {{
              ?item wdt:P946 "{isin}" .
              ?item wdt:P856 ?website .
            }} LIMIT 2
            """
            try:
                resp = cffi_requests.get(
                    "https://query.wikidata.org/sparql",
                    params={"query": sparql_isin, "format": "json"},
                    headers=headers,
                    timeout=8
                )
                if resp.status_code == 200:
                    bindings = resp.json().get("results", {}).get("bindings", [])
                    for b in bindings:
                        site = b.get("website", {}).get("value")
                        if site and site not in candidates:
                            candidates.append(site)
            except Exception as e:
                logger.debug("Wikidata SPARQL lookup error for %s: %s", isin, e)

        # 2. Search by company name via Wikidata API (action=wbsearchentities)
        company_name = getattr(company, 'company_name', None) or getattr(company, 'legal_name', None)
        if company_name and not candidates:
            # Try searching with clean tokens
            tokens = clean_tokens_for_company(company_name)
            queries = [company_name]
            if tokens and tokens[0] != company_name:
                queries.append(tokens[0])

            for q in queries[:2]:
                try:
                    search_resp = cffi_requests.get(
                        "https://www.wikidata.org/w/api.php",
                        params={
                            "action": "wbsearchentities",
                            "search": q,
                            "language": "en",
                            "format": "json",
                            "limit": 3
                        },
                        headers=headers,
                        timeout=8
                    )
                    if search_resp.status_code == 200:
                        entities = search_resp.json().get("search", [])
                        for ent in entities:
                            ent_id = ent.get("id")
                            if not ent_id:
                                continue
                            # Fetch claims for P856
                            ent_resp = cffi_requests.get(
                                "https://www.wikidata.org/w/api.php",
                                params={
                                    "action": "wbgetentities",
                                    "ids": ent_id,
                                    "props": "claims",
                                    "format": "json"
                                },
                                headers=headers,
                                timeout=8
                            )
                            if ent_resp.status_code == 200:
                                claims = ent_resp.json().get("entities", {}).get(ent_id, {}).get("claims", {})
                                p856_claims = claims.get("P856", [])
                                for claim in p856_claims:
                                    site = claim.get("mainsnak", {}).get("datavalue", {}).get("value")
                                    if site and site not in candidates:
                                        candidates.append(site)
                            if candidates:
                                break
                    if candidates:
                        break
                except Exception as e:
                    logger.debug("Wikidata entity search error for %s: %s", q, e)

        return candidates


class ExchangePlugin(StructuredSourcePlugin):
    """
    Plug-in: Looks up official website from NSE/BSE corporate master data.
    Governed strictly by compliance toggle EXCHANGE_DATA_ENABLED.
    """
    name: str = "exchange"

    def is_enabled(self) -> bool:
        return EXCHANGE_DATA_ENABLED

    def lookup(self, company: Any) -> List[str]:
        if not self.is_enabled():
            return []

        # If permitted, retrieve company official site from verified exchange corporate dataset
        # Default placeholder ensures zero unintended API requests when toggled off.
        candidates: List[str] = []
        return candidates


# Registered list of structured source plugins
STRUCTURED_PLUGINS: List[StructuredSourcePlugin] = [
    WikidataPlugin(),
    ExchangePlugin(),
]


# -----------------------------------------------------------------------------
# 4. AI Suggestion Fallback (Stage 3)
# -----------------------------------------------------------------------------
class AIFallbackPlugin:
    """
    Plug-in: Requests official homepage suggestion from Google Gemini Flash (free tier).
    Enforces SQLite persistent cache, zero-cost policy, and treating output as
    unverified suggestion requiring strict code validation.
    """
    name: str = "gemini_ai"

    def __init__(self):
        self.cache = PersistentDiskCache()

    def is_enabled(self) -> bool:
        return AI_FALLBACK_ENABLED

    def suggest_homepage(self, company: Any) -> Optional[str]:
        if not self.is_enabled():
            return None

        company_id = getattr(company, 'company_id', '')
        isin = getattr(company, 'isin', '') or ''
        cache_key = f"ai_homepage_{company_id}_{isin}"

        # 1. Check persistent SQLite cache first (zero API cost)
        cached_resp = self.cache.get(cache_key)
        if cached_resp:
            try:
                data = json.loads(cached_resp)
                suggested = data.get("suggested_url")
                if suggested:
                    logger.info("Retrieved AI homepage suggestion from cache for %s: %s", company_id, suggested)
                    return suggested
            except Exception:
                pass

        # 2. Check Gemini client availability & free tier zero-cost safety
        client = get_ai_client(provider="gemini")
        if not client or not getattr(client, "api_key", None):
            logger.debug("AI fallback skipped: Gemini API key not configured.")
            return None

        # Verify free tier
        if hasattr(client, "verify_free_tier_eligibility"):
            eligible, reason = client.verify_free_tier_eligibility()
            if not eligible:
                logger.warning("Gemini AI fallback ineligible for zero-cost operation: %s", reason)
                return None

        prompt = f"""
        Identify the official corporate homepage URL for the following Indian public company:
        - Company Name: {getattr(company, 'company_name', '')}
        - Legal Name: {getattr(company, 'legal_name', '')}
        - NSE Symbol: {getattr(company, 'nse_symbol', '')}
        - ISIN: {getattr(company, 'isin', '')}
        - Sector: {getattr(company, 'sector', '')}

        Respond ONLY with a valid JSON object:
        {{
          "suggested_url": "https://...",
          "company_brand": "...",
          "confidence": "HIGH" | "MEDIUM" | "LOW"
        }}
        """

        try:
            raw_res, actual_model = client._execute_provider_request(prompt)
            if isinstance(raw_res, dict):
                data = raw_res
            else:
                clean_json = client._clean_json_text(str(raw_res))
                data = json.loads(clean_json) if isinstance(clean_json, str) else clean_json

            suggested = data.get("suggested_url")
            if suggested:
                # Persist to disk cache
                self.cache.set(cache_key, actual_model, "homepage_discovery", json.dumps(data))
                return suggested
        except QuotaExhaustedError:
            logger.warning("Gemini free-tier quota exhausted during homepage suggestion.")
            return None
        except Exception as e:
            logger.warning("Gemini AI suggestion failed for %s: %s", company_id, e)
            return None


ai_fallback_engine = AIFallbackPlugin()


# -----------------------------------------------------------------------------
# 5. Deterministic Code Validation (Stage 4)
# -----------------------------------------------------------------------------
def validate_candidate_homepage(
    candidate_url: str,
    company: Any,
    fetch_result: Optional[FetchResult] = None,
    source: str = "VARIANT"
) -> ValidationResult:
    """
    Validates a candidate homepage using deterministic code checks:
    - HTTP 200 after all redirects
    - Not a disallowed domain (news, directories, job boards, parked domains, socials)
    - Not a parked domain
    - Statutory proof: CIN or ISIN presence (+50)
    - Brand / Name token matching in title (+40), domain (+25), body (+15)
    - Corporate presence keywords (+10)

    Confidence Scoring:
    - HIGH (>= 70): Qualifies for automatic correction
    - MEDIUM (40-69): Requires manual review (REVIEW_REQUIRED)
    - NONE (< 40): Rejected / Invalid
    """
    reasons: List[str] = []

    # 1. Reject disallowed domains
    is_disallowed, dis_reason = is_disallowed_domain(candidate_url)
    if is_disallowed:
        return ValidationResult(
            valid=False,
            confidence="NONE",
            score=0,
            candidate_url=candidate_url,
            final_url=candidate_url,
            source=source,
            reasons=[f"Disallowed domain: {dis_reason}"],
            is_disallowed=True
        )

    # 2. Fetch if not pre-fetched
    if fetch_result is None:
        fetch_result = fetch_candidate_page(candidate_url)

    final_url = fetch_result.final_url or candidate_url

    # Check final redirected URL against disallowed domains
    is_disallowed_final, dis_final_reason = is_disallowed_domain(final_url)
    if is_disallowed_final:
        return ValidationResult(
            valid=False,
            confidence="NONE",
            score=0,
            candidate_url=candidate_url,
            final_url=final_url,
            source=source,
            reasons=[f"Redirected to disallowed domain: {dis_final_reason}"],
            is_disallowed=True
        )

    # 3. HTTP 200 Check
    if fetch_result.status_code != 200:
        err = fetch_result.error or f"HTTP_{fetch_result.status_code}"
        return ValidationResult(
            valid=False,
            confidence="NONE",
            score=0,
            candidate_url=candidate_url,
            final_url=final_url,
            source=source,
            reasons=[f"HTTP status failure: {err}"]
        )

    # 4. Parked Domain Check
    is_parked, park_reason = is_parked_domain_content(fetch_result.html, final_url)
    if is_parked:
        return ValidationResult(
            valid=False,
            confidence="NONE",
            score=0,
            candidate_url=candidate_url,
            final_url=final_url,
            source=source,
            reasons=[f"Parked domain detected: {park_reason}"],
            is_parked=True
        )

    # 4.5. Wrong-Entity / Parent Site Guard (Rule 1)
    is_wrong, wrong_reason = is_wrong_entity_or_parent(final_url, fetch_result.html, company)
    if is_wrong:
        return ValidationResult(
            valid=False,
            confidence="NONE",
            score=0,
            candidate_url=candidate_url,
            final_url=final_url,
            source=source,
            reasons=[f"Wrong-entity/parent site rejected: {wrong_reason}"],
            same_legal_entity=False,
            wrong_entity_reason=wrong_reason
        )

    # 5. Content & Statutory Signal Analysis
    score = 0
    statutory_match = False
    brand_match = False
    identity_evidence = False
    identity_evidence_detail = ""

    html_lower = fetch_result.html.lower()

    # Title extraction
    title_match = re.search(r'<title[^>]*>(.*?)</title>', html_lower, re.IGNORECASE | re.DOTALL)
    title_text = title_match.group(1).strip() if title_match else ""

    # Check Statutory Identifiers (CIN and ISIN)
    cin = getattr(company, 'cin', None)
    if cin and len(cin) >= 15:
        clean_cin = cin.strip().lower()
        if clean_cin in html_lower:
            score += 50
            statutory_match = True
            identity_evidence = True
            identity_evidence_detail = f"CIN found on page: {cin}"
            reasons.append(f"Statutory CIN matched on page: {cin}")

    isin = getattr(company, 'isin', None)
    if isin and len(isin) >= 10:
        clean_isin = isin.strip().lower()
        if clean_isin in html_lower:
            score += 50
            statutory_match = True
            identity_evidence = True
            identity_evidence_detail = f"ISIN found on page: {isin}"
            reasons.append(f"Statutory ISIN matched on page: {isin}")

    # Check Legal Name and Brand Tokens
    company_name = getattr(company, 'company_name', '') or ''
    legal_name = getattr(company, 'legal_name', '') or getattr(company, 'company_name', '') or ''
    nse_symbol = getattr(company, 'nse_symbol', None)
    tokens = clean_tokens_for_company(company_name, nse_symbol=nse_symbol)

    clean_legal = legal_name.lower().strip()
    clean_legal_bare = re.sub(r'\b(limited|ltd|private|pvt|corporation|corp)\b', '', clean_legal).strip()

    # Exact legal entity name match (Rule 2)
    if clean_legal and clean_legal in html_lower[:8000]:
        identity_evidence = True
        identity_evidence_detail = f"Legal name on page: '{legal_name}'"
        score += 45
        brand_match = True
        reasons.append(f"Full legal name matched in page content: '{legal_name}'")
    elif len(clean_legal_bare) >= 5 and clean_legal_bare in html_lower[:6000]:
        identity_evidence = True
        identity_evidence_detail = f"Legal entity name on page: '{clean_legal_bare}'"
        score += 35
        brand_match = True
        reasons.append(f"Legal entity name matched in page content: '{clean_legal_bare}'")

    # Match in title
    if company_name and company_name.lower() in title_text:
        score += 40
        brand_match = True
        reasons.append(f"Full company name found in page title: '{company_name}'")
    elif tokens and any(t.lower() in title_text for t in tokens):
        score += 30
        brand_match = True
        reasons.append(f"Brand token found in page title: '{tokens[0]}'")
    elif tokens and any(t.lower() in html_lower[:3000] for t in tokens):
        score += 15
        brand_match = True
        reasons.append(f"Brand token found in header/body: '{tokens[0]}'")

    # Match in domain netloc
    parsed_final = urlparse(final_url)
    final_netloc = parsed_final.netloc.lower()
    if tokens and any(re.sub(r'[^a-z0-9]', '', t.lower()) in final_netloc for t in tokens if len(t) >= 3):
        score += 25
        reasons.append(f"Domain netloc matches company brand: {final_netloc}")

    # Check match with registered company website domain
    current_website = getattr(company, 'website_url', None) or ''
    if current_website:
        try:
            orig_p = urlparse(current_website)
            orig_net = orig_p.netloc.lower().replace('www.', '')
            cand_net = parsed_final.netloc.lower().replace('www.', '')
            if orig_net and cand_net == orig_net:
                score += 20
                reasons.append(f"Domain matches existing registered company domain: {cand_net}")
                # If exact same path, technical variant
                if orig_p.path.rstrip('/') == parsed_final.path.rstrip('/'):
                    identity_evidence = True
                    identity_evidence_detail = f"Same registered corporate domain ({cand_net})"
        except Exception:
            pass

    # Bonus for verified structured providers (Wikidata, Exchange)
    if source == "PLUGIN_WIKIDATA_ISIN":
        score += 35
        identity_evidence = True
        identity_evidence_detail = "Wikidata official website via ISIN (P946)"
        reasons.append("Wikidata official website verified via ISIN property (P946)")
    elif source.startswith("PLUGIN_"):
        score += 20
        reasons.append(f"Candidate sourced from structured provider: {source}")

    # Corporate signals in navigation / text
    corporate_keywords = [
        "investor", "investors", "annual report", "governance", "board of directors",
        "about", "sustainability", "csr", "financial", "shareholder", "media", "news",
        "careers", "contact"
    ]
    corporate_hits = [sig for sig in corporate_keywords if sig in html_lower]
    if len(corporate_hits) >= 2:
        score += 10
        reasons.append(f"Corporate signals detected: {', '.join(corporate_hits[:3])}")

    # Final confidence routing with strict Identity Evidence requirement (Rule 2)
    if score >= 70:
        if identity_evidence:
            confidence = "HIGH"
            valid = True
        else:
            # Downgrade to MEDIUM if statutory/legal identity evidence is missing
            confidence = "MEDIUM"
            valid = True
            reasons.append("Confidence routed to MEDIUM: Identity evidence (CIN, ISIN, or full legal name on page) missing for auto-apply")
    elif score >= 40:
        confidence = "MEDIUM"
        valid = True
    else:
        confidence = "NONE"
        valid = False
        reasons.append(f"Insufficient corporate brand signals (score: {score})")

    return ValidationResult(
        valid=valid,
        confidence=confidence,
        score=score,
        candidate_url=candidate_url,
        final_url=final_url,
        source=source,
        reasons=reasons,
        statutory_match=statutory_match,
        brand_match=brand_match,
        identity_evidence=identity_evidence,
        identity_evidence_detail=identity_evidence_detail,
        same_legal_entity=True
    )


# -----------------------------------------------------------------------------
# 6. Verification & Self-Correction Pipeline Orchestrator
# -----------------------------------------------------------------------------
class HomepageVerifier:
    """
    End-to-End Orchestrator for verifying and self-correcting company homepages.
    """

    @classmethod
    def verify_company(
        cls,
        company: Any,
        dry_run: bool = True,
        force_recheck: bool = False
    ) -> Dict[str, Any]:
        """
        Processes a single company:
        - If current website_url is valid, marks ALREADY_OK.
        - If failing, executes Variants -> Structured Sources -> AI Fallback.
        - Routes by confidence (HIGH -> auto-update; MEDIUM -> REVIEW_REQUIRED; NONE -> HOMEPAGE_NOT_FOUND).
        - Respects website_url_locked safety guard.
        """
        company_id = getattr(company, 'company_id', '')
        company_name = getattr(company, 'company_name', '')
        current_url = getattr(company, 'website_url', '') or ''
        is_locked = bool(getattr(company, 'website_url_locked', False))

        result = {
            "company_id": company_id,
            "company_name": company_name,
            "old_url": current_url,
            "new_url": current_url,
            "status": "UNKNOWN",
            "source": "CURRENT",
            "confidence": "NONE",
            "score": 0,
            "evidence": "",
            "is_locked": is_locked,
            "mutated": False
        }

        # Step 0: Test current URL
        was_temporarily_unverifiable = False
        temp_unverifiable_reason = ""
        is_dns_failure = False

        if current_url:
            current_fetch = fetch_candidate_page(current_url)
            if current_fetch.status_code == 200:
                current_val = validate_candidate_homepage(
                    current_url,
                    company,
                    fetch_result=current_fetch,
                    source="CURRENT_URL"
                )
                # Rule 3: If old URL already returns 200 and names the company, do not replace it without strong evidence
                if current_val.valid and (current_val.brand_match or current_val.statutory_match or current_val.score >= 40):
                    result.update({
                        "status": "ALREADY_OK",
                        "new_url": current_url,
                        "source": "CURRENT_URL",
                        "confidence": "HIGH" if current_val.confidence == "HIGH" else "MEDIUM",
                        "score": current_val.score,
                        "evidence": f"Existing corporate URL verified active (HTTP 200); {'; '.join(current_val.reasons)}",
                        "same_legal_entity": True
                    })
                    if not dry_run:
                        company.website_url_status = "VERIFIED_ACTIVE"
                        company.website_url_verified_at = safe_now()
                        company.website_url_review_notes = result["evidence"]
                        company.save(update_fields=[
                            'website_url_status', 'website_url_verified_at', 'website_url_review_notes'
                        ])
                    return result
            else:
                # Classify transient challenge vs DNS failure
                err_text = str(current_fetch.error or "").lower()
                status_c = current_fetch.status_code
                if status_c in (403, 429, 307, 503) or any(w in err_text for w in ["timeout", "timed out", "curl: (28)", "stream", "reset", "handshake", "peer closed", "failed to perform"]):
                    was_temporarily_unverifiable = True
                    temp_unverifiable_reason = f"HTTP {status_c} or network challenge ({current_fetch.error})"
                elif current_fetch.is_dns_failure or any(w in err_text for w in ["getaddrinfo", "name resolution", "refused", "not known"]):
                    is_dns_failure = True

        logger.info("Current URL failing for %s (%s). Generating variants...", company_id, current_url)

        best_candidate: Optional[ValidationResult] = None

        # Step 1: Variants First
        variants = generate_homepage_variants(current_url, company_name)
        for var_url in variants:
            if normalize_url_for_comparison(var_url) == normalize_url_for_comparison(current_url):
                continue
            fetch_res = fetch_candidate_page(var_url)
            if fetch_res.status_code == 200:
                val = validate_candidate_homepage(var_url, company, fetch_result=fetch_res, source="VARIANT_NORMALIZATION")
                if val.confidence == "HIGH":
                    best_candidate = val
                    break
                elif val.confidence == "MEDIUM" and (best_candidate is None or val.score > best_candidate.score):
                    best_candidate = val

        # Step 2: Structured Source Plug-ins (if variants didn't produce HIGH)
        if best_candidate is None or best_candidate.confidence != "HIGH":
            for plugin in STRUCTURED_PLUGINS:
                if not plugin.is_enabled():
                    continue
                plugin_urls = plugin.lookup(company)
                for p_url in plugin_urls:
                    if normalize_url_for_comparison(p_url) == normalize_url_for_comparison(current_url):
                        continue
                    fetch_res = fetch_candidate_page(p_url)
                    if fetch_res.status_code == 200:
                        src_tag = f"PLUGIN_{plugin.name.upper()}"
                        if plugin.name == "wikidata" and getattr(company, 'isin', None):
                            src_tag = "PLUGIN_WIKIDATA_ISIN"
                        val = validate_candidate_homepage(p_url, company, fetch_result=fetch_res, source=src_tag)
                        if val.confidence == "HIGH":
                            best_candidate = val
                            break
                        elif val.confidence == "MEDIUM" and (best_candidate is None or val.score > best_candidate.score):
                            best_candidate = val
                if best_candidate and best_candidate.confidence == "HIGH":
                    break

        # Step 3: AI Fallback (if still unresolved)
        if (best_candidate is None or best_candidate.confidence != "HIGH") and AI_FALLBACK_ENABLED:
            ai_suggested_url = ai_fallback_engine.suggest_homepage(company)
            if ai_suggested_url and normalize_url_for_comparison(ai_suggested_url) != normalize_url_for_comparison(current_url):
                fetch_res = fetch_candidate_page(ai_suggested_url)
                if fetch_res.status_code == 200:
                    val = validate_candidate_homepage(ai_suggested_url, company, fetch_result=fetch_res, source="AI_SUGGESTION")
                    if val.confidence == "HIGH":
                        best_candidate = val
                    elif val.confidence == "MEDIUM" and (best_candidate is None or val.score > best_candidate.score):
                        best_candidate = val
                else:
                    logger.warning("AI suggested URL %s failed code validation (HTTP %s). Rejected.", ai_suggested_url, fetch_res.status_code)

        # Step 4: Routing & Safety Enforcement
        if best_candidate and best_candidate.confidence == "HIGH" and best_candidate.identity_evidence:
            target_url = best_candidate.final_url or best_candidate.candidate_url

            # Rule 4: Fix the no-op bug!
            if normalize_url_for_comparison(target_url) == normalize_url_for_comparison(current_url):
                result.update({
                    "status": "ALREADY_OK",
                    "new_url": current_url,
                    "source": "CURRENT_URL_NORMALIZED",
                    "confidence": "HIGH",
                    "score": best_candidate.score,
                    "evidence": f"URL already points to verified official homepage ({'; '.join(best_candidate.reasons)})",
                    "same_legal_entity": True
                })
                if not dry_run:
                    company.website_url_status = "VERIFIED_ACTIVE"
                    company.website_url_verified_at = safe_now()
                    company.website_url_review_notes = result["evidence"]
                    company.save(update_fields=[
                        'website_url_status', 'website_url_verified_at', 'website_url_review_notes'
                    ])
                return result

            evidence = f"Source: {best_candidate.source}; Score: {best_candidate.score}; Reasons: {'; '.join(best_candidate.reasons)}"

            if is_locked:
                result.update({
                    "status": "LOCKED_PRESERVED",
                    "new_url": current_url,
                    "source": best_candidate.source,
                    "confidence": "HIGH",
                    "score": best_candidate.score,
                    "evidence": f"Company website_url is locked. Proposed update to {target_url} skipped. ({evidence})",
                    "same_legal_entity": True
                })
                if not dry_run:
                    company.website_url_status = "LOCKED_PRESERVED"
                    company.website_url_review_notes = result["evidence"]
                    company.save(update_fields=['website_url_status', 'website_url_review_notes'])
            else:
                result.update({
                    "status": "AUTO_CORRECTED",
                    "new_url": target_url,
                    "source": best_candidate.source,
                    "confidence": "HIGH",
                    "score": best_candidate.score,
                    "evidence": evidence,
                    "mutated": True,
                    "same_legal_entity": True,
                    "identity_evidence": best_candidate.identity_evidence_detail or "Statutory / Legal Name Matched"
                })
                if not dry_run:
                    now_val = safe_now()
                    history_entry = {
                        "old_url": current_url,
                        "new_url": target_url,
                        "changed_at": now_val.isoformat(),
                        "source": best_candidate.source,
                        "confidence": "HIGH",
                        "score": best_candidate.score,
                        "evidence": evidence
                    }
                    history = list(company.website_url_history or [])
                    history.append(history_entry)
                    company.website_url_history = history
                    company.website_url = target_url
                    company.official_domain = urlparse(target_url).netloc
                    company.website_url_status = "AUTO_CORRECTED"
                    company.website_url_verified_at = now_val
                    company.website_url_review_notes = evidence
                    company.save(update_fields=[
                        'website_url', 'official_domain', 'website_url_history',
                        'website_url_status', 'website_url_verified_at', 'website_url_review_notes'
                    ])

        elif best_candidate and best_candidate.confidence in ("HIGH", "MEDIUM"):
            evidence = f"Source: {best_candidate.source}; Score: {best_candidate.score}; Needs human review: {'; '.join(best_candidate.reasons)}"
            result.update({
                "status": "REVIEW_REQUIRED",
                "new_url": best_candidate.final_url or best_candidate.candidate_url,
                "source": best_candidate.source,
                "confidence": "MEDIUM",
                "score": best_candidate.score,
                "evidence": evidence,
                "same_legal_entity": best_candidate.same_legal_entity
            })
            if not dry_run:
                company.website_url_status = "REVIEW_REQUIRED"
                company.website_url_review_notes = evidence
                company.save(update_fields=['website_url_status', 'website_url_review_notes'])

        elif was_temporarily_unverifiable:
            evidence = f"Corporate URL returned temporary challenge ({temp_unverifiable_reason}). Flagged for Playwright fallback retry with backoff."
            result.update({
                "status": "TEMPORARILY_UNVERIFIABLE",
                "new_url": current_url,
                "source": "CURRENT_URL_WAF_BLOCKED",
                "confidence": "NONE",
                "score": 0,
                "evidence": evidence,
                "same_legal_entity": True
            })
            if not dry_run:
                company.website_url_status = "TEMPORARILY_UNVERIFIABLE"
                company.website_url_review_notes = evidence
                company.save(update_fields=['website_url_status', 'website_url_review_notes'])

        else:
            evidence = "DNS resolution failed or dead domain. Confirmed not found."
            result.update({
                "status": "HOMEPAGE_NOT_FOUND",
                "new_url": current_url,
                "source": "DNS_OR_DEAD_DOMAIN",
                "confidence": "NONE",
                "score": 0,
                "evidence": evidence,
                "same_legal_entity": False
            })
            if not dry_run:
                company.website_url_status = "HOMEPAGE_NOT_FOUND"
                company.website_url_review_notes = evidence
                company.save(update_fields=['website_url_status', 'website_url_review_notes'])

        return result
