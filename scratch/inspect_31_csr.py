import csv

with open('reports/accuracy_pilot_batch_001_050/csr_candidates.csv', 'r', encoding='utf-8') as f:
    records = list(csv.DictReader(f))

for i, r in enumerate(records):
    pname = r['project_name']
    url = r['source_url']
    comp = r['company_name']
    cid = r['candidate_id']
    cat = r['csr_category']
    print(f"[{i+1:02d}] {cid} | {comp}")
    print(f"     Title: {pname}")
    print(f"     Category: {cat}")
    print(f"     URL: {url}")

