import csv

rows = list(csv.DictReader(open('reports/stage1a_shortcut/homepage_candidates_v2.csv', encoding='utf-8')))

match_cnt = 0
diff_cnt = 0
for r in rows:
    w_d = r['wikidata_domain'].strip()
    y_d = r['yahoo_domain'].strip()
    if w_d and y_d:
        if w_d == y_d:
            match_cnt += 1
        else:
            diff_cnt += 1
            print(f"DIFF: {r['company_id']} {r['name']} | wiki: {w_d} ({r['wikidata_url']}) | yahoo: {y_d} ({r['yahoo_url']})")

print(f"\nCompanies with both URLs: Match = {match_cnt}, Differ = {diff_cnt}")

# What if comparing across all 201 companies?
# (e.g. where at least one exists or comparing non-empty vs empty)
all_diff_or_missing = 201 - match_cnt
print(f"Across all 201 companies: exactly match both = {match_cnt}, do not match both = {all_diff_or_missing}")

