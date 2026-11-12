import urllib.request
import json

endpoints = [
    'http://127.0.0.1:8000/api/companies/',
    'http://127.0.0.1:8000/api/companies/DUMMY_COMP_MM/dossier',
    'http://127.0.0.1:8000/api/companies/DUMMY_COMP_INFY/dossier',
    'http://127.0.0.1:8000/api/companies/DUMMY_COMP_INFY/jobs/',
    'http://127.0.0.1:8000/api/companies/DUMMY_COMP_INFY/csr/',
    'http://127.0.0.1:8000/api/jobs/DUMMY_JOB_105/',
    'http://127.0.0.1:8000/api/csr/projects/DUMMY_CSR_505/'
]

for url in endpoints:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode('utf-8')
            data = json.loads(body)
            print(f"[SUCCESS {status}] {url}")
            if isinstance(data, dict):
                if 'company' in data:
                    c = data['company']
                    print(f"   -> Entity: {c.get('company_name')} | CIN: {c.get('cin')} | ISIN: {c.get('isin')}")
                    print(f"   -> HQ: {c.get('headquarters')}")
                    print(f"   -> Operating Locations: {data.get('operating_locations')}")
                    print(f"   -> Stat Cards: {data.get('intelligence_summary')}")
                elif 'items' in data:
                    print(f"   -> Preview Companies List count: {len(data['items'])}")
                elif 'job_title' in data:
                    print(f"   -> Job: {data.get('job_title')} @ {data.get('company_name')} | Apply: {data.get('application_url')}")
                elif 'project_name' in data:
                    print(f"   -> CSR: {data.get('project_name')} @ {data.get('company_name')} | Budget: {data.get('budget')}")
            elif isinstance(data, list):
                print(f"   -> List records count: {len(data)}")
    except urllib.error.HTTPError as e:
        print(f"[FAILED {e.code}] {url} -> {e.read().decode('utf-8')[:200]}")

