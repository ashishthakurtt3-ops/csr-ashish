import csv

rows = list(csv.DictReader(open('reports/stage1a_shortcut/homepage_candidates_v2.csv', encoding='utf-8')))
p2 = [r for r in rows if r['company_id'] >= 'COMP_TOP200_051']
for r in p2:
    cid = r['company_id']
    name = r['name']
    prop = r['proposed_domain']
    old = r['old_domain']
    wiki = r['wikidata_domain']
    yahoo = r['yahoo_domain']
    # Check if domain is .com and doesn't have india or ltd in domain
    if prop.endswith('.com') and not any(x in prop for x in ['india', 'ltd', 'tat', 'relianc', 'infy', 'wipro', 'hcl']):
        print(f"{cid} | {name} | prop: {prop}")

