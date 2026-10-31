import csv
from collections import defaultdict
import unicodedata, re

def strip_accents(text):
    if not text:
        return ""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))

STOPWORDS = {"limited", "ltd", "private", "pvt", "company", "co", "the", "and", "of", "inc", "plc"}

def normalize_name_for_dup(name):
    clean = strip_accents((name or "").lower())
    words = [w for w in re.findall(r"[a-z0-9]+", clean) if w not in STOPWORDS]
    return " ".join(words)

rows = list(csv.DictReader(open('reports/stage1a_shortcut/homepage_candidates_v2.csv', encoding='utf-8')))
norm_map = defaultdict(list)
for r in rows:
    norm = normalize_name_for_dup(r['name'])
    norm_map[norm].append((r['company_id'], r['name']))

dups = {k: v for k, v in norm_map.items() if len(v) > 1}
print(f"Total duplicate normalized names: {len(dups)}")
for k, v in dups.items():
    print(k, "->", v)

