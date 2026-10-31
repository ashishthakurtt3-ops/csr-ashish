import csv

csv_path = "reports/stage1a_shortcut/manual_url_review_all_companies.csv"
with open(csv_path, "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

total = len(rows)
print(f"Total rows in generated CSV: {total}")

both_cnt = 0
only_yahoo_cnt = 0
only_wiki_cnt = 0
neither_cnt = 0

both_match_cnt = 0
both_diff_cnt = 0

for r in rows:
    w_u = r["Wikidata Website URL"].strip()
    y_u = r["Yahoo Finance Website URL"].strip()
    w_d = r["Wikidata Domain"].strip()
    y_d = r["Yahoo Finance Domain"].strip()
    
    has_w = (w_u != "NOT COLLECTED" and bool(w_u))
    has_y = (y_u != "NOT COLLECTED" and bool(y_u))
    
    if has_w and has_y:
        both_cnt += 1
        if w_d == y_d:
            both_match_cnt += 1
        else:
            both_diff_cnt += 1
    elif has_y and not has_w:
        only_yahoo_cnt += 1
    elif has_w and not has_y:
        only_wiki_cnt += 1
    else:
        neither_cnt += 1

print("\n--- EXACT COUNTS DIRECTLY FROM GENERATED CSV ---")
print(f"Companies with both Yahoo Finance and Wikidata homepage URLs collected: {both_cnt}")
print(f"Companies with only a Yahoo Finance URL: {only_yahoo_cnt}")
print(f"Companies with only a Wikidata URL: {only_wiki_cnt}")
print(f"Companies with neither URL: {neither_cnt}")
print(f"Sum check: {both_cnt + only_yahoo_cnt + only_wiki_cnt + neither_cnt} == {total}")

print("\n--- DOMAIN COMPARISON (Among companies with both URLs) ---")
print(f"Normalized candidate domains match: {both_match_cnt}")
print(f"Normalized candidate domains differ: {both_diff_cnt}")
print(f"Sum check: {both_match_cnt + both_diff_cnt} == {both_cnt}")

print("\n--- DOMAIN COMPARISON (Across all 201 companies) ---")
print(f"Both present & match: {both_match_cnt}")
print(f"Both present & differ: {both_diff_cnt}")
print(f"Single source (only one present): {only_yahoo_cnt + only_wiki_cnt}")
print(f"Neither source present: {neither_cnt}")

