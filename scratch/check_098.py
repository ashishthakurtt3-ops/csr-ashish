import csv

rows = list(csv.DictReader(open('reports/stage1a_shortcut/homepage_candidates_v2.csv', encoding='utf-8')))
for r in rows:
    if r['company_id'] == 'COMP_TOP200_098':
        print(r)

