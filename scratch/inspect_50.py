import json

with open('scratch/50_companies_crawled_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data[:50]:
    print(f"{item.get('index')}. {item.get('name')} ({item.get('company_id')}) - Jobs: {item.get('verified_jobs_count')}, CSR: {item.get('csr_projects_count')}")

