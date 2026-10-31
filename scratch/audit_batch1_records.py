import csv, json

print("=== JOB CANDIDATES (3) ===")
with open('reports/accuracy_pilot_batch_001_050/job_candidates.csv', 'r', encoding='utf-8') as f:
    for i, r in enumerate(csv.DictReader(f)):
        print(f"[{i+1}] ID: {r.get('candidate_id')}")
        print(f"    Company: {r.get('company_name')} ({r.get('company_id')})")
        print(f"    Title: {r.get('title')}")
        print(f"    Location: {r.get('location')}")
        print(f"    Apply URL: {r.get('apply_url')}")
        print(f"    Source URL: {r.get('source_url')}")
        print(f"    Evidence: {r.get('evidence_excerpts')}")
        print(f"    Validation: {r.get('validation_results')}")

print("\n=== OPPORTUNITY CANDIDATES (4) ===")
with open('reports/accuracy_pilot_batch_001_050/opportunity_candidates.csv', 'r', encoding='utf-8') as f:
    for i, r in enumerate(csv.DictReader(f)):
        print(f"[{i+1}] ID: {r.get('candidate_id')}")
        print(f"    Company: {r.get('company_name')} ({r.get('company_id')})")
        print(f"    Title: {r.get('opportunity_title')}")
        print(f"    Type: {r.get('opportunity_type')}")
        print(f"    Source URL: {r.get('source_url')}")
        print(f"    Evidence: {r.get('supporting_evidence')}")

