from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://www.tcs.com/careers/india/lateral-hiring"
r = requests.get(url, impersonate="chrome124", timeout=12)
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a', href=True):
    t = a.get_text(strip=True)
    h = a['href']
    if any(k in t.lower() or k in h.lower() for k in ['explore', 'role', 'job', 'apply', 'career', 'search', 'portal']):
        print(f"Text: '{t}' -> Href: '{h}'")

