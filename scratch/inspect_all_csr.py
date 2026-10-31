import csv

print("=== ALL CSR CANDIDATES (63) ===")
with open('reports/accuracy_pilot_batch_001_050/csr_candidates.csv', 'r', encoding='utf-8') as f:
    records = list(csv.DictReader(f))
    print(f"Total records: {len(records)}\n")
    for i, r in enumerate(records):
        print(f"[{i+1}] {r.get('candidate_id')} | {r.get('company_id')} | {r.get('company_name')}")
        print(f"    Project: {r.get('project_name')}")
        print(f"    Category: {r.get('csr_category')}")
        print(f"    URL: {r.get('source_url')}")
        print(f"    Evidence: {r.get('supporting_evidence')}")
        print(f"    Amount: {r.get('amount_budget')} ({r.get('amount_meaning')})")
        print()

