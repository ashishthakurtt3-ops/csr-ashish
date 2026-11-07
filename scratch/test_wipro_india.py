from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://careers.wipro.com/content/India/?locale=en_US"
r = requests.get(url, impersonate="chrome124", timeout=12)
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a', href=True):
    h = a['href']
    t = a.get_text(' ', strip=True)
    if any(k in h.lower() or k in t.lower() for k in ['job', 'apply', 'openings', 'explore', 'search', 'view', 'opportunities']):
        print(f"  Link: '{t}' -> '{h}'")
