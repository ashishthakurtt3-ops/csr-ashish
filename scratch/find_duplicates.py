import csv, re, unicodedata
from collections import defaultdict

def strip_accents(text):
    if not text:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))

STOPWORDS = {"limited", "ltd", "private", "pvt", "corporation", "corp", "company", "co", "the", "and", "of", "plc", "inc", "llc"}

def normalize_name(name):
    clean = strip_accents((name or "").lower())
    words = [w for w in re.findall(r"[a-z0-9]+", clean) if w not in STOPWORDS]
    return " ".join(words)

with open("reports/stage1a_shortcut/companies.csv", "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

norm_map = defaultdict(list)
for r in rows:
    norm = normalize_name(r["name"])
    norm_map[norm].append(r)

print("=== EXACT MATCHES ON NORMALIZED NAME ===")
group_idx = 0
for norm, comps in sorted(norm_map.items()):
    if len(comps) > 1:
        group_idx += 1
        print(f"Group {group_idx}: '{norm}' (Count: {len(comps)})")
        for c in comps:
            print(f"  {c['company_id']} | {c['name']} | symbol={c['nse_symbol']} | url={c['old_url']}")

print("\n=== NEAR-IDENTICAL PAIRS (E.G. JINDAL STEEL VS JINDAL STEEL & POWER) ===")
checked = set()
for r1 in rows:
    for r2 in rows:
        cid1, cid2 = r1["company_id"], r2["company_id"]
        if cid1 >= cid2:
            continue
        n1 = normalize_name(r1["name"])
        n2 = normalize_name(r2["name"])
        pair_key = (cid1, cid2)
        if n1 != n2 and (n1 in n2 or n2 in n1) and len(n1) > 4 and len(n2) > 4:
            print(f"  {cid1} ('{r1['name']}') <--> {cid2} ('{r2['name']}')")
