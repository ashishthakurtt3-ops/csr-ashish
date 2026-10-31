import csv

rows = list(csv.DictReader(open('reports/stage1a_shortcut/homepage_candidates_v2.csv', encoding='utf-8')))
p2 = [r for r in rows if r['company_id'] >= 'COMP_TOP200_051']
print(f"Total rows in Part 2: {len(p2)}")
for r in p2:
    if 'india' in r['name'].lower():
        print(f"{r['company_id']} | {r['name']} | prop: {r['proposed_domain']} | old: {r['old_domain']}")

