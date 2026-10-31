import csv

rows = list(csv.DictReader(open('reports/stage1a_shortcut/homepage_candidates_v2.csv', encoding='utf-8')))

print("--- 4 companies with NEITHER URL ---")
for r in rows:
    w_u = r['wikidata_url'].strip()
    y_u = r['yahoo_url'].strip()
    if not w_u and not y_u:
        print(f"{r['company_id']} | {r['name']} | notes: {r['notes']} | symbol: {r['yahoo_symbol_used']}")

print("\n--- 4 companies with ONLY WIKIDATA URL ---")
for r in rows:
    w_u = r['wikidata_url'].strip()
    y_u = r['yahoo_url'].strip()
    if w_u and not y_u:
        print(f"{r['company_id']} | {r['name']} | wiki: {w_u} | notes: {r['notes']} | symbol: {r['yahoo_symbol_used']}")

