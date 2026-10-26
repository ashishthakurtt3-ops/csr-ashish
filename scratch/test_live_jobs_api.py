import requests

r = requests.get('http://127.0.0.1:8000/jobs?page=1&page_size=20')
data = r.json()
print("HTTP Status:", r.status_code)
print("Total Verified Jobs:", data.get('total'))
print("Total Pages:", data.get('total_pages'))
print("\nFirst 15 Job Postings on Live Site:")
for idx, item in enumerate(data.get('items', [])[:15], 1):
    print(f" {idx:2d}. [{item.get('company_name')}] {item.get('job_title')} | Loc: {item.get('location')} | Dept: {item.get('department')}")
