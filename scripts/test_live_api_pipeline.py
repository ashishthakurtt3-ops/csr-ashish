import urllib.request
import urllib.parse
import json

base_url = 'http://127.0.0.1:8000/api/jobs'

# Get jobs list
req = urllib.request.Request(f'{base_url}?page_size=20', headers={'User-Agent': 'TestRunner'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

print('Jobs list response status: OK')
jobs = data if isinstance(data, list) else (data.get('jobs') or data.get('results') or [])
print(f'Total jobs in response: {len(jobs)}')

sample_companies = ['Hero MotoCorp', 'Mahindra', 'One 97', 'Reddy', 'Fortis']
tested = 0
for comp_query in sample_companies:
    c_req = urllib.request.Request(f'{base_url}?q={urllib.parse.quote(comp_query)}&page_size=3', headers={'User-Agent': 'TestRunner'})
    try:
        with urllib.request.urlopen(c_req) as c_resp:
            c_data = json.loads(c_resp.read().decode('utf-8'))
            c_jobs = c_data if isinstance(c_data, list) else (c_data.get('jobs') or c_data.get('results') or [])
            if c_jobs:
                j = c_jobs[0]
                jid = j.get('job_row_id') or j.get('job_id')
                d_req = urllib.request.Request(f'{base_url}/{jid}', headers={'User-Agent': 'TestRunner'})
                with urllib.request.urlopen(d_req) as d_resp:
                    detail = json.loads(d_resp.read().decode('utf-8'))
                    title = detail.get("job_title")
                    comp = detail.get("company_name")
                    status = detail.get("detail_fetch_status")
                    pb = detail.get("pay_band")
                    fn = detail.get("function")
                    desc_len = len(detail.get("job_description") or "")
                    resp_len = len(detail.get("responsibilities") or "")
                    qual_len = len(detail.get("qualifications") or "")
                    rel_cnt = len(detail.get("related_jobs") or [])
                    print(f"\n--- {comp_query}: Job {jid} ---")
                    print(f"Title: {title}")
                    print(f"Company: {comp}")
                    print(f"Status: {status}")
                    print(f"Pay Band: {pb}")
                    print(f"Function: {fn}")
                    print(f"Desc len: {desc_len}")
                    print(f"Responsibilities len: {resp_len}")
                    print(f"Qualifications len: {qual_len}")
                    print(f"Related jobs: {rel_cnt}")
                    tested += 1
    except Exception as e:
        print(f"Error testing {comp_query}: {e}")

print(f"\nTotal verified end-to-end via API: {tested}")
