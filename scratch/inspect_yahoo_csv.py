import csv

with open('reports/stage1a_shortcut/manual_url_review_all_companies.csv', mode='r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    print("Fieldnames:", reader.fieldnames)
    rows = list(reader)

print('Total rows:', len(rows))
usable_yahoo = [r for r in rows if r['Yahoo Finance Website URL'] and r['Yahoo Finance Website URL'].strip() != 'NOT COLLECTED']
not_usable = [r for r in rows if not r['Yahoo Finance Website URL'] or r['Yahoo Finance Website URL'].strip() == 'NOT COLLECTED']

print('Usable Yahoo Finance URLs:', len(usable_yahoo))
print('Not Usable Yahoo Finance URLs:', len(not_usable))
print('\nNot usable companies (8 records):')
for r in not_usable:
    print(f"  {r['Company ID']}: {r['Company Name']} -> {r['Yahoo Finance Website URL']}")
