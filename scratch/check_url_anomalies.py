import csv

with open('reports/stage1a_shortcut/manual_url_review_all_companies.csv', mode='r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

for r in rows:
    raw_url = r['Yahoo Finance Website URL'].strip()
    if raw_url and raw_url != 'NOT COLLECTED':
        # Check for any backslashes or unexpected characters
        if '\\' in raw_url:
            print("Backslash in URL:", r['Company ID'], raw_url)
        if not (raw_url.startswith('http://') or raw_url.startswith('https://')):
            print("Non-http URL:", r['Company ID'], raw_url)

print("Checked all 193 Yahoo URLs for anomalies.")

