import urllib.request
import json

req = urllib.request.Request('http://127.0.0.1:8000/jobs?page=1&page_size=30', headers={'Accept': 'application/json'})



try:
    with urllib.request.urlopen(req) as resp:
        content_type = resp.headers.get('Content-Type')
        raw = resp.read()
        print(f"Content-Type: {content_type}")
        if 'application/json' in content_type:
            data = json.loads(raw.decode())
            total = data.get('total')
            print(f"Total jobs count: {total}")
            items = data.get('items', [])
            for i, j in enumerate(items, 1):
                print(f"{i:2d}. [{j.get('company_name')}] {j.get('job_title')} | URL: {j.get('application_url')[:80] if j.get('application_url') else 'None'}")


        else:
            print("Received HTML:", raw.decode()[:300])
except Exception as e:
    print('Error:', e)

