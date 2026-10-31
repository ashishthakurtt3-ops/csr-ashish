"""
Reconcile and apply Fix 3 (strict AGREE_2 logic) and Fix 4 (accent-normalized name matching)
to generate reports/stage1a_shortcut/homepage_candidates_v2.csv.
"""
import os
import sys
import csv
import time
import unicodedata
import re
from collections import Counter
from urllib import robotparser
from urllib.parse import urlparse
import requests

CONTACT = os.environ.get("HOMEPAGE_LOOKUP_CONTACT", "admin@impactbridge.org").strip()
UA_NAME = "homepage-candidate-lookup"
UA = {"User-Agent": f"{UA_NAME}/1.0 (contact: {CONTACT})"}
DELAY = 1.0

MULTI_PART_TLDS = {
    "co.in", "bank.in", "gov.in", "org.in", "ac.in", "net.in", "res.in",
    "nic.in", "gen.in", "co.uk", "org.uk", "gov.uk", "ac.uk", "com.au",
    "net.au", "org.au", "co.jp", "co.za", "com.sg", "com.my",
}
BLOCKED_DOMAINS = {
    "linkedin.com", "naukri.com", "glassdoor.com", "indeed.com", "wikipedia.org",
    "wikidata.org", "screener.in", "moneycontrol.com", "zaubacorp.com",
    "tofler.in", "economictimes.indiatimes.com", "facebook.com", "twitter.com",
    "x.com", "instagram.com", "youtube.com", "justdial.com", "ambitionbox.com",
    "bseindia.com", "nseindia.com", "google.com", "perfdrive.com", "radware.com",
}
STOPWORDS = {"limited", "ltd", "private", "pvt", "corporation", "corp",
             "company", "co", "the", "and", "of", "plc", "inc", "llc"}


def strip_accents(text):
    if not text:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def registrable(url_or_host):
    if not url_or_host:
        return ""
    s = url_or_host.strip()
    if "://" not in s:
        s = "https://" + s
    h = urlparse(s).netloc.lower().split(":")[0].strip(".")
    if h.startswith("www."):
        h = h[4:]
    parts = h.split(".")
    if len(parts) >= 3 and ".".join(parts[-2:]) in MULTI_PART_TLDS:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:]) if len(parts) >= 2 else h


def usable(domain):
    return bool(domain) and domain not in BLOCKED_DOMAINS


def name_tokens(name):
    clean = strip_accents((name or "").lower())
    return [w for w in re.findall(r"[a-z0-9]+", clean) if w not in STOPWORDS]


def name_ok(company_name, other_name):
    """First two distinctive words of our company name must appear in the other name (accent-normalized)."""
    toks = name_tokens(company_name)[:2]
    other = strip_accents((other_name or "").lower())
    return bool(toks) and bool(other) and all(t in other for t in toks)


def yahoo_lookup(name, symbol, log):
    """Returns (website, yahoo_name, symbol_used)."""
    try:
        import yfinance as yf
    except ImportError:
        log("  yfinance is not installed")
        return "", "", ""
    sym = (symbol or "").strip().upper()
    if not sym:
        try:
            for q in yf.Search(name, max_results=6).quotes:
                s = q.get("symbol", "")
                if s.endswith(".NS"):
                    sym = s
                    break
        except Exception as e:
            log(f"  yahoo search error: {e}")
    if not sym:
        return "", "", ""
    if not (sym.endswith(".NS") or sym.endswith(".BO")):
        sym += ".NS"
    site, yname = "", ""
    for _ in range(2):
        try:
            info = yf.Ticker(sym).info or {}
            site = info.get("website", "") or ""
            yname = info.get("longName") or info.get("shortName") or ""
            if site or yname:
                break
        except Exception as e:
            log(f"  yahoo info error for {sym}: {e}")
            time.sleep(3)
    if not name_ok(name, yname):
        log(f"  yahoo name mismatch: '{yname}' for symbol {sym}; result ignored")
        return "", yname, sym
    return site, yname, sym


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


def check_reachable(domain):
    """One polite homepage request. Blocks are recorded, never bypassed."""
    if not robots_allows_root(domain):
        return "BLOCKED_BY_ROBOTS", "", ""
    last = ""
    for u in (f"https://www.{domain}/", f"https://{domain}/"):
        try:
            r = requests.get(u, headers=UA, timeout=12, allow_redirects=True)
            if r.status_code in (403, 429):
                return f"BLOCKED_{r.status_code}", registrable(r.url), ""
            return str(r.status_code), registrable(r.url), ""
        except Exception as e:
            last = str(e)[:120]
    return "UNREACHABLE", "", last


FIELDS = ["company_id", "name", "status", "proposed_domain", "proposed_url",
          "change_from_old", "old_url", "old_domain", "wikidata_url",
          "wikidata_domain", "wikidata_label", "yahoo_url", "yahoo_domain",
          "yahoo_name", "yahoo_symbol_used", "reachability",
          "reach_final_domain", "notes"]


def compute_status_and_proposal(old_d, wiki_d, yahoo_d, wiki_url, yahoo_url, old_url):
    srcs = {"old": old_d, "wikidata": wiki_d, "yahoo": yahoo_d}
    valid = {k: v for k, v in srcs.items() if usable(v)}
    
    # Map domain -> list of supporting sources
    domain_to_sources = {}
    for src, dom in valid.items():
        domain_to_sources.setdefault(dom, []).append(src)
    
    sorted_domains = sorted(domain_to_sources.items(), key=lambda x: len(x[1]), reverse=True)
    best, sources_for_best = sorted_domains[0] if sorted_domains else ("", [])
    n = len(sources_for_best)
    
    notes = []
    for k, v in srcs.items():
        if v and not usable(v):
            notes.append(f"{k} ignored (aggregator/WAF domain: {v})")

    if n >= 3:
        status = "AGREE_3"
    elif n == 2:
        status = "AGREE_2"
        odd = [k for k, v in valid.items() if v != best]
        if odd:
            notes.append(f"differs: {odd[0]}={valid[odd[0]]}")
    elif len(valid) >= 2:
        status = "CONFLICT"
    elif len(valid) == 1:
        status = "SINGLE_SOURCE"
    else:
        status = "NO_DATA"

    proposed_domain = best if status.startswith("AGREE") else ""
    proposed_url = ""
    if proposed_domain:
        for u in (wiki_url, yahoo_url, old_url):
            if registrable(u) == proposed_domain:
                proposed_url = u
                break
    change = bool(proposed_domain and old_d and proposed_domain != old_d)
    return status, proposed_domain, proposed_url, change, "; ".join(notes)


def main():
    in_v1 = os.path.join("reports", "stage1a_shortcut", "homepage_candidates.csv")
    out_v2 = os.path.join("reports", "stage1a_shortcut", "homepage_candidates_v2.csv")

    with open(in_v1, "r", encoding="utf-8") as f:
        v1_rows = list(csv.DictReader(f))

    v2_rows = []
    re_run_rows = []

    for r in v1_rows:
        cid = r["company_id"]
        name = r["name"]
        
        # If Nestle (COMP_TOP200_024), re-query Yahoo with accent normalization
        if cid == "COMP_TOP200_024":
            print(f"Re-querying Yahoo for {cid} ({name}) with accent normalization...")
            y_url, y_name, sym = yahoo_lookup(name, "NESTLEIND", print)
            r["yahoo_url"] = y_url
            r["yahoo_domain"] = registrable(y_url)
            r["yahoo_name"] = y_name
            r["yahoo_symbol_used"] = sym

        # Re-compute status and proposal with Fix 3 logic
        old_d = registrable(r.get("old_url", ""))
        wiki_d = registrable(r.get("wikidata_url", ""))
        yahoo_d = registrable(r.get("yahoo_url", ""))
        
        status, prop_d, prop_u, change, notes = compute_status_and_proposal(
            old_d, wiki_d, yahoo_d,
            r.get("wikidata_url", ""),
            r.get("yahoo_url", ""),
            r.get("old_url", "")
        )

        reach = r.get("reachability", "")
        reach_dom = r.get("reach_final_domain", "")

        # If proposal changed or newly proposed, check reachability
        if prop_d and prop_d != r.get("proposed_domain", ""):
            reach, reach_dom, err = check_reachable(prop_d)
            if err:
                notes = (notes + "; " + err) if notes else err

        updated_row = dict(r)
        updated_row["status"] = status
        updated_row["proposed_domain"] = prop_d
        updated_row["proposed_url"] = prop_u
        updated_row["change_from_old"] = str(change)
        updated_row["notes"] = notes
        updated_row["reachability"] = reach
        updated_row["reach_final_domain"] = reach_dom

        v2_rows.append(updated_row)

        # Check if changed from v1
        if updated_row["status"] != r["status"] or updated_row["proposed_domain"] != r["proposed_domain"]:
            re_run_rows.append((r, updated_row))

    with open(out_v2, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(v2_rows)

    print(f"Wrote {len(v2_rows)} rows to {out_v2}")
    print(f"Total rows that changed between v1 and v2: {len(re_run_rows)}")
    for r1, r2 in re_run_rows:
        print(f"  {r1['company_id']} | {r1['name']}:")
        print(f"    v1: status={r1['status']} prop={r1['proposed_domain']}")
        print(f"    v2: status={r2['status']} prop={r2['proposed_domain']}")


if __name__ == "__main__":
    main()
