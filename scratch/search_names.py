import csv

with open("reports/stage1a_shortcut/homepage_candidates.csv", "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

# Let's search for Cummins, ABB, Container Corporation, 3i Infotech, etc.
names_to_check = ["cummins", "abb", "container", "3i", "aakash", "aarey", "aartech", "jindal"]
for term in names_to_check:
    print(f"=== SEARCH FOR '{term}' ===")
    for r in rows:
        if term in r["name"].lower():
            print(f"  {r['company_id']} | '{r['name']}' | symbol={r.get('yahoo_symbol_used')}")
