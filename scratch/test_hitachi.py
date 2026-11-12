from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://www.hitachienergy.com/in/en/careers"
r = requests.get(url, impersonate="chrome124", timeout=12)
print("Hitachi Status:", r.status_code, "Len:", len(r.text))
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a', href=True):
    t = a.get_text(strip=True)
    h = a['href']
    if any(k in t.lower() or k in h.lower() for k in ['job', 'career', 'opening', 'search', 'portal']):
        print(f"Hitachi Link: '{t}' -> '{h}'")

