"""
Stage 1A Part 2: Classify Homepage Results for COMP_TOP200_051 to COMP_TOP200_200 (150 companies).
READ-ONLY. No AI calls. No database writes.
"""
import os
import sys
import csv
import time
import re
import socket
import unicodedata
from collections import defaultdict
from urllib import robotparser
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

CONTACT = os.environ.get("HOMEPAGE_LOOKUP_CONTACT", "admin@impactbridge.org").strip()
UA_NAME = "homepage-candidate-lookup"
UA = {"User-Agent": f"{UA_NAME}/1.0 (contact: {CONTACT})"}
DELAY = 1.0

GENERIC_WORDS = {
    "limited", "ltd", "private", "pvt", "corporation", "corp", "company", "co", "the", "and", "of",
    "plc", "inc", "llc", "india", "indian", "industries", "services", "technologies", "technology",
    "finance", "financial", "bank", "banking", "insurance", "general", "power", "energy", "steel",
    "life", "oil", "gas", "natural", "national", "bharat", "hindustan", "solar"
}

STOPWORDS = {"limited", "ltd", "private", "pvt", "company", "co", "the", "and", "of", "inc", "plc"}

GLOBAL_KNOWN_MNC = {
    "siemens.com", "abb.com", "oracle.com", "hyundai.com", "cummins.com",
    "whirlpool.com", "bosch.com", "3m.com", "hitachi.com", "schneider-electric.com",
    "linde.com", "colgatepalmolive.com", "pfizer.com", "sanofi.com", "akzonobel.com"
}


def strip_accents(text):
    if not text:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_name_for_dup(name):
    clean = strip_accents((name or "").lower())
    words = [w for w in re.findall(r"[a-z0-9]+", clean) if w not in STOPWORDS]
    return " ".join(words)


def domain_resolves(d):
    if not d:
        return False
    for prefix in ("", "www."):
        try:
            socket.gethostbyname(f"{prefix}{d}")
            return True
        except Exception:
            pass
    return False


def get_distinctive_tokens(name):
    clean = strip_accents((name or "").lower())
    words = re.findall(r"[a-z0-9]+", clean)
    distinctive = [w for w in words if w not in GENERIC_WORDS]
    if len(distinctive) >= 2:
        return distinctive[:2]
    # If fewer than 2 distinctive words, include business words
    semi = [w for w in words if w not in STOPWORDS]
    return semi[:2] if semi else words[:2]


def robots_allows_root(domain):
    try:
        r = requests.get(f"https://{domain}/robots.txt", headers=UA, timeout=8)
        if r.status_code != 200:
            return True
        rp = robotparser.RobotFileParser()
        rp.parse(r.text.splitlines())
        return rp.can_fetch(UA_NAME, "/")
    except Exception:
        return True


def fetch_homepage_title(url_or_domain, log):
    """Fetches homepage once and extracts <title> and <h1> text."""
    if not url_or_domain:
        return "", "NO_URL"
    
    if "://" in url_or_domain:
        target = url_or_domain
        domain = urlparse(target).netloc.split(":")[0].lower().strip(".")
        if domain.startswith("www."):
            domain = domain[4:]
    else:
        domain = url_or_domain.strip().lower()
        target = f"https://www.{domain}/"

    if not robots_allows_root(domain):
        log(f"  Robots disallows '/' for {domain}")
        return "", "BLOCKED_BY_ROBOTS"

    time.sleep(DELAY)
    candidates_to_try = [target]
    if not target.startswith(f"https://{domain}/"):
        candidates_to_try.append(f"https://{domain}/")

    title_text = ""
    status_note = ""
    for u in candidates_to_try:
        try:
            log(f"  Fetching: {u}")
            resp = requests.get(u, headers=UA, timeout=12, allow_redirects=True)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                t_elem = soup.find("title")
                h1_elem = soup.find("h1")
                t_str = t_elem.get_text(" ", strip=True) if t_elem else ""
                h1_str = h1_elem.get_text(" ", strip=True) if h1_elem else ""
                title_text = f"{t_str} | {h1_str}".strip(" |") if h1_str and h1_str not in t_str else t_str
                status_note = "200"
                break
            else:
                status_note = f"HTTP_{resp.status_code}"
        except Exception as e:
            status_note = type(e).__name__
            log(f"  Error fetching {u}: {e}")

    return title_text, status_note


def main():
    start_time = time.time()
    in_v2 = os.path.join("reports", "stage1a_shortcut", "homepage_candidates_v2.csv")
    out_dir = os.path.join("reports", "stage1a_shortcut", "part2")
    os.makedirs(out_dir, exist_ok=True)

    log_path = os.path.join(out_dir, "part2_log.txt")
    logf = open(log_path, "w", encoding="utf-8")

    def log(msg):
        line = time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg
        print(line)
        logf.write(line + "\n")
        logf.flush()

    log("=" * 70)
    log("Stage 1A Part 2: Classification (COMP_TOP200_051 to COMP_TOP200_200)")
    log(f"User-Agent: {UA['User-Agent']}")
    log(f"Rate limit delay: {DELAY}s")
    log("=" * 70)

    with open(in_v2, "r", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    # Build duplicate name map across all 201 rows
    norm_to_ids = defaultdict(list)
    for r in all_rows:
        norm = normalize_name_for_dup(r["name"])
        if norm:
            norm_to_ids[norm].append(r["company_id"])

    # Target slice: COMP_TOP200_051 onwards
    part2_rows = [r for r in all_rows if r["company_id"] >= "COMP_TOP200_051"]
    log(f"Loaded {len(all_rows)} total companies from {in_v2}.")
    log(f"Selected {len(part2_rows)} companies in Part 2 range [COMP_TOP200_051 .. COMP_TOP200_200].")

    decisions_list = []
    manual_review_list = []
    requests_made = 0
    errors_encountered = 0

    for i, r in enumerate(part2_rows, 1):
        cid = r["company_id"]
        name = r["name"]
        old_d = r.get("old_domain", "").strip()
        wiki_d = r.get("wikidata_domain", "").strip()
        yahoo_d = r.get("yahoo_domain", "").strip()
        prop_d = r.get("proposed_domain", "").strip()
        reach = r.get("reachability", "").strip()
        notes = r.get("notes", "").strip()
        status = r.get("status", "").strip()
        change = r.get("change_from_old", "").strip() == "True"

        # Class determination
        # 1. OLD_CORRECT: old domain equals agreed domain of at least one other independent source
        if status in ("AGREE_2", "AGREE_3") and not change:
            cls = "OLD_CORRECT"
        # 2. OLD_OUTDATED: two independent sources agree on different domain, and old domain resolves/redirects
        elif status in ("AGREE_2", "AGREE_3") and change:
            if not domain_resolves(old_d) or any(k in old_d for k in ["perfdrive", "radware", "validate", "captcha"]) or not old_d:
                cls = "OLD_WRONG"
            else:
                cls = "OLD_OUTDATED"
        # 3. OLD_WRONG: old domain empty or WAF challenge, or does not resolve, and another source gave valid domain
        elif (any(k in old_d for k in ["perfdrive", "radware", "validate", "captcha"]) or not old_d or not domain_resolves(old_d)) and (wiki_d or yahoo_d):
            cls = "OLD_WRONG"
            if not prop_d:
                prop_d = yahoo_d or wiki_d
        # 4. UNDECIDED: sources conflict, only one source, or no data
        else:
            cls = "UNDECIDED"

        # Flags determination
        flags = []

        # Flag 1: GLOBAL_PARENT_CHECK
        name_lower = name.lower()
        if prop_d in GLOBAL_KNOWN_MNC:
            flags.append("GLOBAL_PARENT_CHECK")
        elif ("india" in name_lower or "limited" in name_lower) and prop_d:
            if "india" in name_lower and prop_d.endswith(".com") and "india" not in prop_d:
                flags.append("GLOBAL_PARENT_CHECK")

        # Flag 2: BLOCKED_OR_UNREACHABLE
        if reach.startswith("BLOCKED_") or reach == "UNREACHABLE":
            flags.append("BLOCKED_OR_UNREACHABLE")

        # Flag 3: DUPLICATE_NAME
        norm = normalize_name_for_dup(name)
        if norm and len(norm_to_ids[norm]) > 1:
            flags.append("DUPLICATE_NAME")

        # Flag 4: NAME_CHECK_FAILED (only for rows NOT OLD_CORRECT)
        title_found = ""
        name_check = "N/A"
        if cls != "OLD_CORRECT":
            url_to_fetch = r.get("proposed_url") or (f"https://{prop_d}/" if prop_d else r.get("old_url"))
            log(f"[{i}/{len(part2_rows)}] Fetching homepage for non-OLD_CORRECT: {cid} ({name}) -> {url_to_fetch}")
            title_found, status_note = fetch_homepage_title(url_to_fetch, log)
            requests_made += 1
            if status_note not in ("200", "BLOCKED_BY_ROBOTS"):
                errors_encountered += 1

            distinctive = get_distinctive_tokens(name)
            title_lower = strip_accents(title_found.lower())
            
            # Check if distinctive tokens appear in title/header
            if title_found and all(tok in title_lower for tok in distinctive):
                name_check = "PASS"
            else:
                name_check = "FAIL"
                flags.append("NAME_CHECK_FAILED")
            log(f"  Result: {name_check} (Tokens: {distinctive}, Title: '{title_found[:60]}', Status: {status_note})")
        else:
            log(f"[{i}/{len(part2_rows)}] {cid}: {name} -> OLD_CORRECT ({old_d})")

        flags_str = "; ".join(flags) if flags else "NONE"

        decision_row = {
            "company_id": cid,
            "name": name,
            "class": cls,
            "flags": flags_str,
            "old_domain": old_d,
            "wikidata_domain": wiki_d,
            "yahoo_domain": yahoo_d,
            "proposed_domain": prop_d,
            "reachability": reach,
            "page_title_found": title_found,
            "name_check": name_check,
            "notes": notes
        }
        decisions_list.append(decision_row)

        # Check if requires manual review
        if (cls in ("UNDECIDED", "OLD_OUTDATED", "OLD_WRONG") or
            "NAME_CHECK_FAILED" in flags or
            "GLOBAL_PARENT_CHECK" in flags):
            
            cand_links = []
            if old_d:
                cand_links.append(f"Old: https://{old_d}/")
            if wiki_d and wiki_d != old_d:
                cand_links.append(f"Wiki: https://{wiki_d}/")
            if yahoo_d and yahoo_d not in (old_d, wiki_d):
                cand_links.append(f"Yahoo: https://{yahoo_d}/")
            if prop_d and prop_d not in (old_d, wiki_d, yahoo_d):
                cand_links.append(f"Prop: https://{prop_d}/")

            manual_row = {
                "company_id": cid,
                "name": name,
                "class": cls,
                "flags": flags_str,
                "candidate_urls": " | ".join(cand_links),
                "page_title_found": title_found,
                "name_check": name_check,
                "my_decision": ""  # Blank for user to fill
            }
            manual_review_list.append(manual_row)

    # Write output files
    decisions_csv = os.path.join(out_dir, "homepage_decisions_051_201.csv")
    decision_fields = [
        "company_id", "name", "class", "flags", "old_domain", "wikidata_domain",
        "yahoo_domain", "proposed_domain", "reachability", "page_title_found",
        "name_check", "notes"
    ]
    with open(decisions_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=decision_fields)
        writer.writeheader()
        writer.writerows(decisions_list)
    log(f"Written {len(decisions_list)} rows to {decisions_csv}")

    manual_csv = os.path.join(out_dir, "manual_review_051_201.csv")
    manual_fields = [
        "company_id", "name", "class", "flags", "candidate_urls",
        "page_title_found", "name_check", "my_decision"
    ]
    with open(manual_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=manual_fields)
        writer.writeheader()
        writer.writerows(manual_review_list)
    log(f"Written {len(manual_review_list)} manual review rows to {manual_csv}")

    elapsed = time.time() - start_time
    log("=" * 70)
    log(f"Execution complete in {elapsed:.2f} seconds.")
    log(f"Total network requests made: {requests_made}")
    log(f"Total fetch errors/timeouts: {errors_encountered}")
    log("=" * 70)
    logf.close()


if __name__ == "__main__":
    main()
