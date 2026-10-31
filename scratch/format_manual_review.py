import csv

with open('reports/stage1a_shortcut/part2/manual_review_051_201.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

print(f"Total manual review rows: {len(rows)}")
for r in rows:
    print(f"| {r['company_id']} | {r['name']} | {r['class']} | {r['flags']} | {r['candidate_urls']} | {r['page_title_found'][:40]} | {r['name_check']} | |")

