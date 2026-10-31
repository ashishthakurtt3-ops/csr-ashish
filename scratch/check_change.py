import csv

rows = list(csv.DictReader(open('reports/stage1a_shortcut/homepage_candidates_v2.csv', encoding='utf-8')))
for r in rows:
    if r['change_from_old'] == 'True':
        print(r['company_id'], r['name'], 'status:', r['status'], 'old:', r['old_domain'], 'prop:', r['proposed_domain'], 'wiki:', r['wikidata_domain'], 'yahoo:', r['yahoo_domain'])

