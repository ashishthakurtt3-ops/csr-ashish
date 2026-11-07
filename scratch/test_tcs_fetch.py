from curl_cffi import requests
from bs4 import BeautifulSoup

urls = [
    'https://www.tcs.com/careers/india/lateral-hiring',
    'https://www.tcs.com/careers/india/tcs-cloud-hiring',
    'https://www.tcs.com/careers/india/tcs-cybersecurity-hiring',
    'https://ibegin.tcs.com/iBegin/jobs/search'
]

for u in urls:
    try:
        r = requests.get(u, impersonate="chrome124", timeout=10)
        print(f"URL: {u} -> Status: {r.status_code}, Length: {len(r.text)}")
        soup = BeautifulSoup(r.text, 'html.parser')
        headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3', 'h4'])[:8]]
        print(f"  Headings: {headings}")
    except Exception as e:
        print(f"URL: {u} -> Error: {e}")
