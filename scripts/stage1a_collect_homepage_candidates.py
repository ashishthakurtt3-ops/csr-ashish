"""
Homepage candidate collector. READ-ONLY. No database access, no AI.
Sources: old stored URL, Wikidata P856, Yahoo Finance (yfinance).
Usage:
  set HOMEPAGE_LOOKUP_CONTACT=you@example.com
  python scripts/stage1a_collect_homepage_candidates.py --input reports/stage1a_shortcut/companies.csv --limit 5
"""
import argparse, csv, os, re, sys, time
from collections import Counter
from urllib import robotparser
from urllib.parse import urlparse
import requests

CONTACT = os.environ.get("HOMEPAGE_LOOKUP_CONTACT", "").strip()
if not CONTACT:
    # Check if configured in .env as fallback
    try:
        from dotenv import load_dotenv
        load_dotenv()
        env_mail = os.environ.get("HOMEPAGE_LOOKUP_CONTACT") or os.environ.get("DEFAULT_FROM_EMAIL", "")
        emails = re.findall(r"[\w\.-]+@[\w\.-]+", env_mail)
        if emails:
            CONTACT = emails[0]
    except Exception:
        pass

if not CONTACT:
    sys.exit("Set HOMEPAGE_LOOKUP_CONTACT to a real contact email first.")
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
    return [w for w in re.findall(r"[a-z0-9]+", (name or "").lower()) if w not in STOPWORDS]


def name_ok(company_name, other_name):
    """First two distinctive words of our company name must appear in the other name."""
    toks = name_tokens(company_name)[:2]
    other = (other_name or "").lower()
    return bool(toks) and bool(other) and all(t in other for t in toks)


def wikidata_lookup(name, log):
    try:
        r = requests.get(
            "https://www.wikidata.org/w/api.php",
            params={"action": "wbsearchentities", "search": name,
                    "language": "en", "format": "json", "limit": 5},
            headers=UA, timeout=15)
        hits = r.json().get("search", [])
    except Exception as e:
        log(f"  wikidata search error: {e}")
        return "", ""
    for hit in hits:
        label = hit.get("label", "")
        if not name_ok(name, label):
            continue
        time.sleep(DELAY)
        try:
            ent = requests.get(
                f"https://www.wikidata.org/wiki/Special:EntityData/{hit['id']}.json",
                headers=UA, timeout=15).json()
            claims = ent["entities"][hit["id"]].get("claims", {}).get("P856", [])
        except Exception as e:
            log(f"  wikidata entity error: {e}")
            continue
        claims = [c for c in claims if c.get("rank") != "deprecated"]
        claims.sort(key=lambda c: 0 if c.get("rank") == "preferred" else 1)
        for c in claims:
            v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
            if v:
                return v, label
    return "", ""


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out-dir", default="reports/stage1a_shortcut")
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    logf = open(os.path.join(args.out_dir, "collector_log.txt"), "w", encoding="utf-8")

    def log(msg):
        line = time.strftime("[%H:%M:%S] ") + msg
        print(line)
        logf.write(line + "\n")
        logf.flush()

    rows = list(csv.DictReader(open(args.input, encoding="utf-8")))
    if args.limit:
        rows = rows[:args.limit]
    out = []

    for i, r in enumerate(rows, 1):
        name = r["name"]
        log(f"[{i}/{len(rows)}] {r['company_id']} {name}")
        wiki_url, wiki_label = wikidata_lookup(name, log)
        time.sleep(DELAY)
        yahoo_url, yahoo_name, sym = yahoo_lookup(name, r.get("nse_symbol", ""), log)
        time.sleep(DELAY)

        old_d = registrable(r.get("old_url", ""))
        wiki_d = registrable(wiki_url)
        yahoo_d = registrable(yahoo_url)
        srcs = {"old": old_d, "wikidata": wiki_d, "yahoo": yahoo_d}
        valid = {k: v for k, v in srcs.items() if usable(v)}
        counts = Counter(valid.values())
        best, n = (counts.most_common(1) or [("", 0)])[0]
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
            for u in (wiki_url, yahoo_url, r.get("old_url", "")):
                if registrable(u) == proposed_domain:
                    proposed_url = u
                    break
        change = bool(proposed_domain and old_d and proposed_domain != old_d)

        reach, reach_dom = "", ""
        if proposed_domain:
            reach, reach_dom, err = check_reachable(proposed_domain)
            if err:
                notes.append(err)
            time.sleep(DELAY)

        out.append({
            "company_id": r["company_id"], "name": name, "status": status,
            "proposed_domain": proposed_domain, "proposed_url": proposed_url,
            "change_from_old": change, "old_url": r.get("old_url", ""),
            "old_domain": old_d, "wikidata_url": wiki_url,
            "wikidata_domain": wiki_d, "wikidata_label": wiki_label,
            "yahoo_url": yahoo_url, "yahoo_domain": yahoo_d,
            "yahoo_name": yahoo_name, "yahoo_symbol_used": sym,
            "reachability": reach, "reach_final_domain": reach_dom,
            "notes": "; ".join(notes),
        })
        log(f"  -> {status} {proposed_domain} (old={old_d} wiki={wiki_d} yahoo={yahoo_d})")

    path = os.path.join(args.out_dir, "homepage_candidates.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    log(f"Status counts: {dict(Counter(o['status'] for o in out))}")
    log(f"Changes vs old URL: {sum(1 for o in out if o['change_from_old'])}")
    log(f"Written: {path}")
    logf.close()


if __name__ == "__main__":
    main()

