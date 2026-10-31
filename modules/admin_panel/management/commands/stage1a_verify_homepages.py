"""
Stage 1A: Find and Verify the Official Homepage for Each Company (Batch 1: COMP_TOP200_001 to COMP_TOP200_050)
Strict DRY RUN mode: Absolutely no database writes, updates, or deletes.

Usage:
    python manage.py stage1a_verify_homepages --batch 1 --dry-run
    python manage.py stage1a_verify_homepages --batch 1 --dry-run --limit 5
    python manage.py stage1a_verify_homepages --company-ids COMP_TOP200_001,COMP_TOP200_018
"""

import os
import sys
import re
import csv
import json
import time
import urllib.parse
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set

from django.core.management.base import BaseCommand
from django.db import connection
from bs4 import BeautifulSoup
from curl_cffi import requests

# ==============================================================================
# SCORING CONSTANTS & THRESHOLDS
# ==============================================================================

HIGH_THRESHOLD = 70
MARGIN_THRESHOLD = 15
LOW_THRESHOLD = 40

# Points
HTTPS_200_POINTS = 20
TITLE_OG_MATCH_POINTS = 25
TITLE_OG_PARTIAL_POINTS = 15
FOOTER_COPYRIGHT_POINTS = 20
FOOTER_ABOUT_POINTS = 10
DOMAIN_RESEMBLANCE_EXACT_POINTS = 25
DOMAIN_RESEMBLANCE_TOKEN_POINTS = 15
CORPORATE_LINKS_POINTS = 15  # Up to 15 (5 per category: careers, investors, sustainability/csr)

# Penalties
PARKED_DOMAIN_PENALTY = -60
LOGIN_WALL_PENALTY = -40
AGGREGATOR_REDIRECT_PENALTY = -60
WRONG_ENTITY_MISMATCH_PENALTY = -50
REGIONAL_NON_MAIN_PENALTY = -20

# Polite Crawler Configuration
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
    "(CSR-Job-Intelligence-Auditor/1.0; mailto:compliance@csrjobintel.org)"
)
REQUEST_DELAY_SEC = 1.0
DEFAULT_TIMEOUT_SEC = 12

# Multi-part country code top-level domains for registrable domain extraction
MULTI_PART_TLDS = {
    "co.in", "bank.in", "gov.in", "org.in", "ac.in", "net.in", "res.in", "nic.in", "gen.in",
    "co.uk", "org.uk", "gov.uk", "ac.uk", "ltd.uk", "plc.uk",
    "com.au", "net.au", "org.au", "edu.au", "gov.au",
    "co.jp", "ne.jp", "ac.jp", "go.jp", "or.jp",
    "co.za", "org.za", "gov.za",
    "com.sg", "edu.sg", "gov.sg",
    "com.my", "edu.my", "gov.my"
}

# Blocklist of aggregators, social networks, directories, financial portals, and search engines
DISALLOWED_DOMAINS = {
    # Job portals & professional networks
    "linkedin.com", "naukri.com", "glassdoor.com", "indeed.com", "ambitionbox.com",
    "shine.com", "foundit.in", "monsterindia.com", "freshersworld.com", "internshala.com",
    "upwork.com", "freelancer.com", "fiverr.com", "hirist.tech", "iimjobs.com",
    # Financial & corporate aggregators
    "screener.in", "moneycontrol.com", "zaubacorp.com", "tofler.in", "economictimes.indiatimes.com",
    "timesofindia.indiatimes.com", "indiatimes.com", "bloomberg.com", "reuters.com",
    "bseindia.com", "nseindia.com", "livemint.com", "business-standard.com",
    "financialexpress.com", "equitymaster.com", "trendlyne.com", "tickertape.in",
    "topstockresearch.com", "marketsmojo.com", "investing.com", "tradingview.com",
    "fintrackr.com", "entrackr.com", "inc42.com", "yourstory.com", "quartr.com",
    # Encyclopedias & generic reference
    "wikipedia.org", "wikidata.org", "wikimedia.org", "wiktionary.org",
    # Search engines
    "google.com", "duckduckgo.com", "bing.com", "yahoo.com", "baidu.com", "yandex.com",
    # Social media & video
    "facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com",
    "quora.com", "reddit.com", "pinterest.com", "threads.net", "tiktok.com",
    # Local & B2B directories
    "justdial.com", "indiamart.com", "tradeindia.com", "yellowpages.in", "sulekha.com",
    # App stores
    "play.google.com", "apps.apple.com",
    # Bot challenge & WAF interceptors
    "perfdrive.com", "cloudflare.com", "radware.com", "incapsula.com", "akamai.com"
}

# Parked domain signatures
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
    "buy now for $"
]

# Corporate signal keywords
CAREER_KEYWORDS = ["careers", "career", "jobs", "job openings", "work with us", "join us", "current openings"]
INVESTOR_KEYWORDS = ["investor relations", "investors", "financial results", "annual report", "shareholder", "corporate governance"]
CSR_KEYWORDS = ["sustainability", "csr", "corporate social responsibility", "esg", "social impact", "foundation"]


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_registrable_domain(url_or_netloc: str) -> str:
    """
    Extracts the clean registrable domain (e.g., 'ril.com', 'hdfc.bank.in', 'licindia.in').
    Strips protocol, port, path, query, and leading 'www.'.
    """
    if not url_or_netloc:
        return ""
    if "://" in url_or_netloc:
        netloc = urllib.parse.urlparse(url_or_netloc).netloc
    else:
        netloc = url_or_netloc.split("/")[0]
    
    netloc = netloc.split(":")[0].lower().strip()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    
    parts = netloc.split(".")
    if len(parts) >= 3:
        last_two = ".".join(parts[-2:])
        if last_two in MULTI_PART_TLDS:
            return ".".join(parts[-3:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return netloc


def is_blocked_aggregator(domain: str) -> bool:
    """Checks if domain or any parent domain is in the disallowed blocklist."""
    if not domain:
        return True
    domain_clean = domain.lower().strip()
    if domain_clean in DISALLOWED_DOMAINS:
        return True
    for blocked in DISALLOWED_DOMAINS:
        if domain_clean.endswith("." + blocked):
            return True
    return False


def clean_company_name(name: str) -> Tuple[List[str], str]:
    """
    Extracts core tokens and abbreviation/acronym from company name.
    Example: 'Reliance Industries Limited' -> (['reliance', 'industries'], 'ril')
             'Tata Consultancy Services Limited' -> (['tata', 'consultancy', 'services'], 'tcs')
    """
    if not name:
        return [], ""
    raw = re.sub(r"\(.*?\)", "", name).strip()
    raw = re.sub(r"^(dr\.|dr|shri|m/s)\s+", "", raw, flags=re.IGNORECASE).strip()
    
    stopwords = {
        "limited", "ltd", "private", "pvt", "corporation", "corp",
        "enterprises", "industries", "holdings", "company", "co",
        "the", "and", "&", "plc", "llc", "inc", "of"
    }
    
    words = re.findall(r"[A-Za-z0-9]+", raw)
    filtered = [w.lower() for w in words if w.lower() not in stopwords]
    
    # Generate acronym from core words (or all words if filtered is too short)
    acronym_words = filtered if len(filtered) >= 2 else [w.lower() for w in words if w.lower() not in {"the", "and", "&", "of"}]
    acronym = "".join(w[0] for w in acronym_words if w)
    
    return filtered, acronym


def check_robots_txt_allowed(domain: str, logger_func=None) -> bool:
    """
    Polite robots.txt inspection for homepage ('/').
    Returns True if allowed or if robots.txt is unavailable/permissive.
    """
    try:
        robots_url = f"https://{domain}/robots.txt"
        resp = requests.get(
            robots_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/plain,*/*"
            },
            impersonate="chrome124",
            timeout=5
        )
        if resp.status_code == 200:
            lines = resp.text.splitlines()
            current_applies = False
            for line in lines:
                line = line.strip().lower()
                if line.startswith("user-agent:"):
                    ua = line.split(":", 1)[1].strip()
                    if ua == "*":
                        current_applies = True
                    else:
                        current_applies = False
                elif current_applies and line.startswith("disallow:"):
                    dis = line.split(":", 1)[1].strip()
                    if dis == "/":
                        if logger_func:
                            logger_func(f"[ROBOTS.TXT] {domain} explicitly disallows '/' for user-agent *")
                        return False
    except Exception:
        pass
    return True


# ==============================================================================
# CANDIDATE GENERATION (CODE ONLY, NO AI)
# ==============================================================================

def generate_candidates(company_name: str, old_url: str, logger_func=None) -> List[Dict[str, Any]]:
    """
    Step 1: Uses DuckDuckGo HTML search and Wikidata fallback to collect up to 10
    candidate URLs for a company name, reduced to registrable domains and filtered by blocklist.
    Also incorporates the old stored URL marked as 'old'.
    """
    candidates_map: Dict[str, Dict[str, Any]] = {}
    
    # 1. Add OLD URL domain as baseline candidate
    old_domain = get_registrable_domain(old_url)
    if old_domain and not is_blocked_aggregator(old_domain):
        candidates_map[old_domain] = {
            "domain": old_domain,
            "source": "old_database",
            "sample_url": old_url if old_url.startswith("http") else f"https://{old_domain}/"
        }
    
    # Search queries without exact quotes to prevent search engine 202 challenge
    clean_name = re.sub(r"[^\w\s]", " ", company_name).strip()
    clean_name = re.sub(r"\s+", " ", clean_name)
    queries = [
        f"{clean_name} official website",
        f"{clean_name} investor relations"
    ]
    
    ddg_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://html.duckduckgo.com/",
    }

    for q in queries:
        time.sleep(REQUEST_DELAY_SEC)
        ddg_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(q)}"
        try:
            resp = requests.get(
                ddg_url,
                headers=ddg_headers,
                impersonate="chrome124",
                timeout=DEFAULT_TIMEOUT_SEC
            )
            if logger_func:
                logger_func(f"[SEARCH] Query: '{q}' -> Status: {resp.status_code}")
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for body in soup.select(".result__body"):
                    title_a = body.select_one(".result__title a")
                    if title_a and title_a.get("href"):
                        href = title_a.get("href")
                        qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                        target_url = qs.get("uddg", [None])[0]
                        if target_url:
                            dom = get_registrable_domain(target_url)
                            if dom and not is_blocked_aggregator(dom) and dom not in candidates_map:
                                candidates_map[dom] = {
                                    "domain": dom,
                                    "source": "duckduckgo_search",
                                    "sample_url": target_url
                                }
                                if len(candidates_map) >= 10:
                                    break
            elif resp.status_code in (403, 429, 202):
                if logger_func:
                    logger_func(f"[SEARCH BLOCKED] Query '{q}' returned status {resp.status_code}")
        except Exception as e:
            if logger_func:
                logger_func(f"[SEARCH ERROR] Query '{q}': {e}")
        
        if len(candidates_map) >= 10:
            break
            
    # Wikidata fallback if fewer than 3 candidates
    if len(candidates_map) < 3:
        try:
            time.sleep(REQUEST_DELAY_SEC)
            wiki_search_url = (
                f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={urllib.parse.quote(clean_name)}"
                f"&language=en&format=json&limit=3"
            )
            w_resp = requests.get(wiki_search_url, headers={"User-Agent": USER_AGENT}, timeout=8)
            if w_resp.status_code == 200:
                entities = w_resp.json().get("search", [])
                for ent in entities:
                    ent_id = ent.get("id")
                    if ent_id:
                        ent_url = f"https://www.wikidata.org/wiki/Special:EntityData/{ent_id}.json"
                        e_resp = requests.get(ent_url, headers={"User-Agent": USER_AGENT}, timeout=8)
                        if e_resp.status_code == 200:
                            claims = e_resp.json().get("entities", {}).get(ent_id, {}).get("claims", {})
                            p856 = claims.get("P856", [])
                            for p in p856:
                                site = p.get("mainsnak", {}).get("datavalue", {}).get("value")
                                if site:
                                    dom = get_registrable_domain(site)
                                    if dom and not is_blocked_aggregator(dom) and dom not in candidates_map:
                                        candidates_map[dom] = {
                                            "domain": dom,
                                            "source": "wikidata_p856",
                                            "sample_url": site
                                        }
        except Exception as e:
            if logger_func:
                logger_func(f"[WIKIDATA ERROR] {e}")

    return list(candidates_map.values())[:10]


# ==============================================================================
# CANDIDATE VERIFICATION & SCORING (CODE ONLY, NO AI)
# ==============================================================================

def score_candidate(
    candidate: Dict[str, Any],
    company_name: str,
    logger_func=None
) -> Dict[str, Any]:
    """
    Step 2: Fetches candidate homepage and calculates transparent score based on
    signals and penalties.
    """
    domain = candidate["domain"]
    test_urls = [f"https://www.{domain}/", f"https://{domain}/"]
    
    core_tokens, acronym = clean_company_name(company_name)
    primary_token = core_tokens[0] if core_tokens else ""
    full_brand_str = " ".join(core_tokens)
    
    score_breakdown: Dict[str, int] = {}
    evidence: Dict[str, Any] = {
        "title": "",
        "matched_name_text": "",
        "footer_text": "",
        "final_domain": "",
        "final_url": "",
        "status_code": None,
        "signals": []
    }
    
    # 1. Respect Robots.txt
    robots_ok = check_robots_txt_allowed(domain, logger_func)
    if not robots_ok:
        evidence["signals"].append("robots_txt_disallow_slash")
    
    fetch_success = False
    html = ""
    status_code = None
    final_url = ""
    
    # Fetch candidate with polite delay
    time.sleep(REQUEST_DELAY_SEC)
    for target in test_urls:
        try:
            resp = requests.get(
                target,
                headers={"User-Agent": USER_AGENT},
                impersonate="chrome124",
                timeout=DEFAULT_TIMEOUT_SEC,
                allow_redirects=True
            )
            status_code = resp.status_code
            final_url = resp.url
            if resp.status_code == 200:
                html = resp.text
                fetch_success = True
                break
            elif resp.status_code in (403, 429):
                if logger_func:
                    logger_func(f"[FETCH BLOCKED] {target}: Status {resp.status_code}")
        except Exception as e:
            if logger_func:
                logger_func(f"[FETCH ERROR] {target}: {e}")
            continue

    evidence["status_code"] = status_code
    evidence["final_url"] = final_url
    final_domain = get_registrable_domain(final_url) if final_url else domain
    evidence["final_domain"] = final_domain
    
    if not fetch_success or not html:
        score_breakdown["fetch_failure"] = 0
        total_score = 0
        return {
            "candidate": candidate,
            "score": total_score,
            "breakdown": score_breakdown,
            "evidence": evidence
        }

    soup = BeautifulSoup(html, "html.parser")
    title_text = soup.title.string.strip() if soup.title and soup.title.string else ""
    evidence["title"] = title_text
    
    og_elem = soup.find("meta", property="og:site_name")
    og_site_name = og_elem.get("content", "").strip() if og_elem else ""
    
    h1_elem = soup.find("h1")
    h1_text = h1_elem.get_text().strip() if h1_elem else ""
    
    combined_header = f"{title_text} {og_site_name} {h1_text}".lower()
    
    # Extract footer & copyright text
    footer_elem = soup.find("footer")
    footer_text = footer_elem.get_text(" ", strip=True) if footer_elem else ""
    copyright_matches = re.findall(r"(?:copyright|©|\(c\)).{5,120}", html, re.IGNORECASE)
    combined_footer = f"{footer_text} {' '.join(copyright_matches)}".lower()
    evidence["footer_text"] = (copyright_matches[0].strip() if copyright_matches else footer_text[:120]).strip()
    
    # Full lower html text
    full_text_lower = soup.get_text(" ", strip=True).lower()
    
    # Check Penalties First
    # Penalty 1: Aggregator or bot interceptor redirect
    if is_blocked_aggregator(final_domain):
        score_breakdown["aggregator_redirect_penalty"] = AGGREGATOR_REDIRECT_PENALTY
        evidence["signals"].append("aggregator_redirect")

    # Penalty 2: Parked / for-sale domain
    for park_kw in PARKED_DOMAIN_KEYWORDS:
        if park_kw in full_text_lower[:5000] or park_kw in title_text.lower():
            score_breakdown["parked_domain_penalty"] = PARKED_DOMAIN_PENALTY
            evidence["signals"].append("parked_domain")
            break

    # Penalty 3: Login wall only
    login_keywords = ["sign in to your account", "login to continue", "employee portal", "portal login"]
    if any(lk in full_text_lower[:2000] for lk in login_keywords) and len(full_text_lower) < 1500:
        score_breakdown["login_wall_penalty"] = LOGIN_WALL_PENALTY
        evidence["signals"].append("login_wall_only")

    # Penalty 4: Foreign regional site when Indian parent sought
    if re.search(r"\.(us|uk|de|fr|au|sg|ae)$", final_domain) and not re.search(r"\.(in|com|org|net)$", final_domain):
        if "india" not in final_domain and "india" not in title_text.lower():
            score_breakdown["regional_non_main_penalty"] = REGIONAL_NON_MAIN_PENALTY
            evidence["signals"].append("foreign_regional_non_main")

    # Signal 1: HTTP 200 over HTTPS
    if status_code == 200 and final_url.startswith("https://"):
        score_breakdown["https_200"] = HTTPS_200_POINTS
        evidence["signals"].append("https_200")
    elif status_code == 200:
        score_breakdown["https_200"] = HTTPS_200_POINTS // 2
        evidence["signals"].append("http_200_insecure")

    # Signal 2: Title / OG site name / Header match
    if full_brand_str and full_brand_str in combined_header:
        score_breakdown["title_og_match"] = TITLE_OG_MATCH_POINTS
        evidence["signals"].append("full_brand_in_title_or_og")
        evidence["matched_name_text"] = full_brand_str
    elif primary_token and primary_token in combined_header:
        score_breakdown["title_og_match"] = TITLE_OG_PARTIAL_POINTS
        evidence["signals"].append("primary_token_in_title_or_og")
        evidence["matched_name_text"] = primary_token
    elif acronym and len(acronym) >= 3 and acronym in combined_header.split():
        score_breakdown["title_og_match"] = TITLE_OG_PARTIAL_POINTS
        evidence["signals"].append("acronym_in_title")
        evidence["matched_name_text"] = acronym.upper()

    # Signal 3: Footer Copyright / About match
    if full_brand_str and full_brand_str in combined_footer:
        score_breakdown["footer_copyright"] = FOOTER_COPYRIGHT_POINTS
        evidence["signals"].append("full_brand_in_footer_copyright")
    elif primary_token and primary_token in combined_footer:
        score_breakdown["footer_copyright"] = FOOTER_COPYRIGHT_POINTS
        evidence["signals"].append("primary_token_in_footer_copyright")
    elif full_brand_str and full_brand_str in full_text_lower:
        score_breakdown["footer_copyright"] = FOOTER_ABOUT_POINTS
        evidence["signals"].append("brand_in_page_body")

    # Signal 4: Domain resemblance (acronym or name tokens)
    domain_stem = domain.split(".")[0].lower()
    if acronym and len(acronym) >= 3 and domain_stem == acronym:
        score_breakdown["domain_resemblance"] = DOMAIN_RESEMBLANCE_EXACT_POINTS
        evidence["signals"].append("domain_exact_acronym_match")
    elif full_brand_str and (full_brand_str.replace(" ", "") in domain_stem or domain_stem in full_brand_str.replace(" ", "")):
        score_breakdown["domain_resemblance"] = DOMAIN_RESEMBLANCE_EXACT_POINTS
        evidence["signals"].append("domain_full_brand_match")
    elif primary_token and primary_token in domain_stem:
        score_breakdown["domain_resemblance"] = DOMAIN_RESEMBLANCE_TOKEN_POINTS
        evidence["signals"].append("domain_primary_token_match")

    # Signal 5: Corporate links on homepage
    all_links_text = " ".join([a.get_text(" ", strip=True).lower() for a in soup.find_all("a")]).lower()
    all_links_href = " ".join([str(a.get("href", "")).lower() for a in soup.find_all("a")]).lower()
    combined_links = f"{all_links_text} {all_links_href}"
    
    corp_points = 0
    if any(k in combined_links for k in CAREER_KEYWORDS):
        corp_points += 5
        evidence["signals"].append("careers_link")
    if any(k in combined_links for k in INVESTOR_KEYWORDS):
        corp_points += 5
        evidence["signals"].append("investors_link")
    if any(k in combined_links for k in CSR_KEYWORDS):
        corp_points += 5
        evidence["signals"].append("sustainability_csr_link")
    
    if corp_points > 0:
        score_breakdown["corporate_links"] = corp_points

    # Compute Final Total
    total_score = max(0, min(100, sum(score_breakdown.values())))
    
    return {
        "candidate": candidate,
        "score": total_score,
        "breakdown": score_breakdown,
        "evidence": evidence
    }


# ==============================================================================
# AI TIE-BREAKER (FREE TIER ONLY, STRICT REVIEW TIE-BREAK ONLY)
# ==============================================================================

def ai_tie_break(
    company_name: str,
    cand1: Dict[str, Any],
    cand2: Dict[str, Any],
    logger_func=None
) -> Optional[str]:
    """
    Step 3 Optional AI tie-break:
    Only called when two candidates are in REVIEW with close scores.
    Strictly picks between cand1 and cand2. Re-checked by code.
    Zero-cost policy: free tier only. Max 15 calls across run.
    """
    try:
        from modules.crawler_engine.ai_api_client import get_ai_client
        client = get_ai_client(provider="gemini")
        if not client or not getattr(client, "api_key", None):
            return None
        
        prompt = (
            f"You are a strict corporate data verification assistant. Identify the official corporate website for Indian public company:\n"
            f"Company: '{company_name}'\n\n"
            f"Pick strictly between these two candidate URLs:\n"
            f"Candidate A: {cand1['evidence']['final_url']} (Title: {cand1['evidence']['title']})\n"
            f"Candidate B: {cand2['evidence']['final_url']} (Title: {cand2['evidence']['title']})\n\n"
            f"Return JSON strictly with keys:\n"
            f'{{"chosen_url": "<Candidate A or Candidate B URL>", "reason": "<short evidence sentence>"}}\n'
            f"Do not invent any third URL."
        )
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{client.model}:generateContent?key={client.api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=12)
        if resp.status_code == 200:
            res_json = resp.json()
            content_str = res_json.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            data = json.loads(content_str)
            chosen = data.get("chosen_url", "").strip()
            c1_url = cand1['evidence']['final_url']
            c2_url = cand2['evidence']['final_url']
            c1_dom = cand1['candidate']['domain']
            c2_dom = cand2['candidate']['domain']
            if chosen == c1_url or c1_dom in chosen:
                return c1_dom
            elif chosen == c2_url or c2_dom in chosen:
                return c2_dom
    except Exception as e:
        if logger_func:
            logger_func(f"[AI TIE-BREAK ERROR] {e}")
    return None


# ==============================================================================
# MAIN MANAGEMENT COMMAND
# ==============================================================================

class Command(BaseCommand):
    help = "Stage 1A: Find and verify official homepage for Batch 1 (COMP_TOP200_001 to 050) in strict DRY RUN."

    def add_arguments(self, parser):
        parser.add_argument("--batch", type=int, default=1, help="Batch number (1 for COMP_TOP200_001 to 050)")
        parser.add_argument("--dry-run", action="store_true", default=True, help="Strict dry run mode (default: True)")
        parser.add_argument("--limit", type=int, default=None, help="Limit number of companies to process")
        parser.add_argument("--company-ids", type=str, default=None, help="Comma-separated company IDs")

    def handle(self, *args, **options):
        sys.stdout.reconfigure(encoding="utf-8")
        start_time = time.time()
        
        batch = options.get("batch", 1)
        dry_run = options.get("dry_run", True)
        limit = options.get("limit")
        company_ids_arg = options.get("company_ids")
        
        reports_dir = os.path.abspath(os.path.join("reports", "stage1a"))
        os.makedirs(reports_dir, exist_ok=True)
        log_file_path = os.path.join(reports_dir, "stage1a_log.txt")
        log_file = open(log_file_path, "w", encoding="utf-8")
        
        def log_msg(msg: str):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{timestamp}] {msg}"
            self.stdout.write(line)
            log_file.write(line + "\n")
            log_file.flush()

        log_msg("================================================================================")
        log_msg(f"STAGE 1A: OFFICIAL HOMEPAGE VERIFICATION (BATCH {batch}) - DRY RUN: {dry_run}")
        log_msg("================================================================================")

        # 1. Check DB row count BEFORE
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM admin_panel_company")
            before_count = cursor.fetchone()[0]
        log_msg(f"[AUDIT] admin_panel_company row count BEFORE execution: {before_count}")

        # 2. Select target companies
        from modules.admin_panel.models import Company
        if company_ids_arg:
            ids = [cid.strip() for cid in company_ids_arg.split(",") if cid.strip()]
            qs = Company.objects.filter(company_id__in=ids).order_by("company_id")
        else:
            qs = Company.objects.filter(
                company_id__gte="COMP_TOP200_001",
                company_id__lte="COMP_TOP200_050"
            ).order_by("company_id")
        
        if limit:
            qs = qs[:limit]
            
        companies = list(qs)
        log_msg(f"Selected {len(companies)} companies for Batch {batch}.")

        # Tracking metrics
        total_searches = 0
        ai_calls_made = 0
        results_list: List[Dict[str, Any]] = []
        all_candidates_dict: Dict[str, List[Dict[str, Any]]] = {}

        for idx, comp in enumerate(companies, 1):
            comp_id = comp.company_id
            name = comp.name
            old_url = comp.website_url or ""
            old_domain = get_registrable_domain(old_url)

            log_msg(f"\n--- [{idx}/{len(companies)}] Processing {comp_id}: '{name}' ---")
            log_msg(f"    Stored Old URL: {old_url} (Domain: {old_domain})")

            # Step 1: Candidate Generation
            candidates = generate_candidates(name, old_url, logger_func=log_msg)
            total_searches += 2  # 2 queries per company
            log_msg(f"    Generated {len(candidates)} candidates: {[c['domain'] for c in candidates]}")

            # Step 2: Scoring
            scored_candidates: List[Dict[str, Any]] = []
            for cand in candidates:
                cand_score_res = score_candidate(cand, name, logger_func=log_msg)
                scored_candidates.append(cand_score_res)
                log_msg(
                    f"      Candidate: {cand['domain']:<28} | Score: {cand_score_res['score']:>3} | "
                    f"Breakdown: {cand_score_res['breakdown']}"
                )

            # Sort by score descending
            scored_candidates.sort(key=lambda x: x["score"], reverse=True)
            all_candidates_dict[comp_id] = scored_candidates

            # Step 3: Decision
            top_cand = scored_candidates[0] if scored_candidates else None
            runner_up = scored_candidates[1] if len(scored_candidates) > 1 else None

            top_score = top_cand["score"] if top_cand else 0
            runner_score = runner_up["score"] if runner_up else 0

            decision = "NOT FOUND"
            tie_break_used = False

            if top_cand and top_score >= HIGH_THRESHOLD:
                if not runner_up or (top_score - runner_score >= MARGIN_THRESHOLD):
                    decision = "VERIFIED"
                else:
                    decision = "REVIEW"
            elif top_cand and top_score >= LOW_THRESHOLD:
                decision = "REVIEW"
            else:
                decision = "NOT FOUND"

            # Optional AI tie-break: only for REVIEW with two close candidates (both >= LOW_THRESHOLD)
            if decision == "REVIEW" and runner_up and runner_score >= LOW_THRESHOLD and (top_score - runner_score < MARGIN_THRESHOLD):
                if ai_calls_made < 15:
                    log_msg("    [AI TIE-BREAK] Triggering Gemini Flash tie-break for close candidates...")
                    chosen_dom = ai_tie_break(name, top_cand, runner_up, logger_func=log_msg)
                    ai_calls_made += 1
                    if chosen_dom:
                        tie_break_used = True
                        log_msg(f"    [AI TIE-BREAK] AI selected: {chosen_dom}")
                        if runner_up["candidate"]["domain"] == chosen_dom:
                            # Swap top and runner up
                            top_cand, runner_up = runner_up, top_cand
                            top_score, runner_score = runner_score, top_score

            new_url = top_cand["evidence"]["final_url"] if top_cand and top_cand["evidence"]["final_url"] else (
                f"https://{top_cand['candidate']['domain']}/" if top_cand else ""
            )
            new_domain = top_cand["evidence"]["final_domain"] if top_cand else ""
            same_domain = (old_domain.lower() == new_domain.lower()) if old_domain and new_domain else False

            result_entry = {
                "company_id": comp_id,
                "name": name,
                "old_homepage_url": old_url,
                "new_homepage_url": new_url,
                "old_domain": old_domain,
                "new_domain": new_domain,
                "decision": decision,
                "score": top_score,
                "runner_up_url": runner_up["evidence"]["final_url"] if runner_up else "",
                "runner_up_score": runner_score if runner_up else 0,
                "final_domain": new_domain,
                "evidence_title": top_cand["evidence"]["title"] if top_cand else "",
                "evidence_matched_text": top_cand["evidence"]["matched_name_text"] if top_cand else "",
                "evidence_footer": top_cand["evidence"]["footer_text"] if top_cand else "",
                "same_domain_as_old": same_domain,
                "signals": top_cand["evidence"]["signals"] if top_cand else [],
                "notes_and_errors": f"Tie-break used: {tie_break_used}" if tie_break_used else ""
            }
            results_list.append(result_entry)
            log_msg(f"    DECISION: {decision} | Score: {top_score} | New Domain: {new_domain} | Same as Old: {same_domain}")

        # 3. Check DB row count AFTER
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM admin_panel_company")
            after_count = cursor.fetchone()[0]
        log_msg(f"\n[AUDIT] admin_panel_company row count AFTER execution: {after_count} (Delta: {after_count - before_count})")

        # 4. Write Output Files
        csv_file_path = os.path.join(reports_dir, "stage1a_results.csv")
        json_file_path = os.path.join(reports_dir, "stage1a_results.json")
        cand_file_path = os.path.join(reports_dir, "stage1a_candidates.json")

        # Write CSV
        with open(csv_file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "company_id", "name", "old_homepage_url", "new_homepage_url", "decision",
                "score", "runner_up_url", "runner_up_score", "final_domain",
                "evidence_title", "evidence_matched_text", "evidence_footer",
                "same_domain_as_old", "notes_and_errors"
            ])
            for r in results_list:
                writer.writerow([
                    r["company_id"],
                    r["name"],
                    r["old_homepage_url"],
                    r["new_homepage_url"],
                    r["decision"],
                    r["score"],
                    r["runner_up_url"],
                    r["runner_up_score"],
                    r["final_domain"],
                    r["evidence_title"],
                    r["evidence_matched_text"],
                    r["evidence_footer"],
                    r["same_domain_as_old"],
                    r["notes_and_errors"]
                ])
        log_msg(f"[OUTPUT] Written CSV to {csv_file_path}")

        # Write Results JSON
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(results_list, f, indent=2, ensure_ascii=False)
        log_msg(f"[OUTPUT] Written Results JSON to {json_file_path}")

        # Write Candidates JSON
        with open(cand_file_path, "w", encoding="utf-8") as f:
            json.dump(all_candidates_dict, f, indent=2, ensure_ascii=False)
        log_msg(f"[OUTPUT] Written Candidates JSON to {cand_file_path}")

        runtime_sec = time.time() - start_time
        log_msg(f"\nExecution finished in {runtime_sec:.2f} seconds.")
        log_msg(f"Total web searches: {total_searches}")
        log_msg(f"Total AI calls: {ai_calls_made}")
        log_file.close()
