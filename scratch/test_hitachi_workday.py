from curl_cffi import requests
import json

cxs_url = "https://hitachi.wd1.myworkdayjobs.com/wday/cxs/hitachi/hitachi/jobs"
payload = json.dumps({'appliedFacets': {}, 'limit': 10, 'offset': 0, 'searchText': 'India'})
try:
    r = requests.post(cxs_url, data=payload, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, impersonate="chrome124", timeout=12)
    print("Workday Status:", r.status_code)
    if r.status_code == 200:
        data = r.json()
        print("Total jobs found on Workday for Hitachi:", data.get('total'))
        for j in data.get('jobPostings', [])[:5]:
            print("  - Title:", j.get('title'))
            print("    Location:", j.get('locationsText'))
            print("    Path:", j.get('externalPath'))
except Exception as e:
    print("Workday Error:", e)

