from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://www.hitachienergy.com/careers/open-jobs"
r = requests.get(url, impersonate="chrome124", timeout=12)
print("Hitachi open jobs Status:", r.status_code, "Len:", len(r.text))
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a', href=True):
    h = a['href']
    if 'job' in h.lower() or 'workday' in h.lower() or 'careers' in h.lower():
        print("Link:", a.get_text(strip=True)[:40], "->", h)

