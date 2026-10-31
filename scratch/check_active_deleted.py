import json

with open('reports/audit/confirmed_fabricated_records_20261029_163921.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

active_deleted = [r for r in data['deleted_records'] if r.get('entity') == 'Job' and r.get('status') == 'ACTIVE']
print(f'Active deleted count: {len(active_deleted)}')
for r in active_deleted:
    t = (r['title'][:40] or '').encode('ascii', 'replace').decode('ascii')
    u = (r['url'][:65] or '').encode('ascii', 'replace').decode('ascii')
    print(f"[{r['company'][:20]}] {t} | Reason: {r['reason'][:50]} | URL: {u}")
