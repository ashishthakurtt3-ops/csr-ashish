from curl_cffi import requests
from bs4 import BeautifulSoup
import re

url = "https://www.tcs.com/careers/india"
r = requests.get(url, impersonate="chrome124", timeout=12)
print("Status:", r.status_code, "Len:", len(r.text))
soup = BeautifulSoup(r.text, 'html.parser')

links = []
for a in soup.find_all('a', href=True):
    href = a['href']
    txt = a.get_text(strip=True)
    if any(k in href.lower() or k in txt.lower() for k in ['job', 'career', 'opening', 'lateral', 'apply', 'hiring']):
        links.append((txt, href))

print(f"Total relevant links found: {len(links)}")
for txt, href in links[:20]:
    print(f"  {txt} -> {href}")
