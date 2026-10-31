import csv

pairs = [
    ('COMP_TOP200_048', 'COMP_TOP200_124'),
    ('COMP_TOP200_060', 'COMP_TOP200_152'),
    ('COMP_TOP200_136', 'COMP_TOP200_147'),
    ('COMP_TOP200_158', 'COMP_TOP200_160'),
    ('COMP_TOP200_166', 'COMP_TOP200_194'),
    ('COMP_TOP200_167', 'COMP_TOP200_195'),
    ('COMP_TOP200_168', 'COMP_TOP200_198'),
    ('COMP_TOP200_074', 'COMP_TOP200_075'),
]

rows = {r['company_id']: r['name'] for r in csv.DictReader(open('reports/stage1a_shortcut/companies.csv', encoding='utf-8'))}

for c1, c2 in pairs:
    n1 = rows.get(c1, 'MISSING')
    n2 = rows.get(c2, 'MISSING')
    print(f"{c1} ('{n1}') vs {c2} ('{n2}')")
