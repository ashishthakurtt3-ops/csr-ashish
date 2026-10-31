import csv
import socket

rows = list(csv.DictReader(open('reports/stage1a_shortcut/homepage_candidates_v2.csv', encoding='utf-8')))
p2 = [r for r in rows if r['company_id'] >= 'COMP_TOP200_051']

for r in p2:
    old_d = r.get('old_domain', '').strip()
    status = r.get('status', '').strip()
    change = r.get('change_from_old', '').strip() == 'True'
    if not old_d:
        print(f"NO OLD DOMAIN: {r['company_id']} {r['name']}")
        continue
    try:
        socket.gethostbyname(old_d)
    except Exception as e:
        print(f"DNS FAIL for old domain: {r['company_id']} {r['name']} | old: {old_d} | status: {status} | change: {change} | error: {e}")

