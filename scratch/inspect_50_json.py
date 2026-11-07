import json, os

with open('scratch/50_companies_crawled_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total companies in 50_companies: {len(data)}")

for c in data:
    sample_jobs = c.get('sample_jobs', [])
    sample_csr = c.get('sample_csr_projects', [])
    print(f"\n[{c['index']}] {c['name']} ({c['company_id']}) - Jobs: {c['verified_jobs_count']}, CSR: {c['csr_projects_count']}")
    if sample_jobs:
        print("   Jobs:", sample_jobs)
    if sample_csr:
        print("   CSR:", sample_csr)

