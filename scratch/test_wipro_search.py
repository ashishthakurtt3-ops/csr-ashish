from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://careers.wipro.com/search"
r = requests.get(url, impersonate="chrome124", timeout=12)
print("Wipro Search status:", r.status_code, "Len:", len(r.text))
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a', href=True):
    h = a['href']
    t = a.get_text(' ', strip=True)
    if '/job/' in h or 'job' in h.lower() and len(t) > 3:
        print(f"  Wipro job link: {t[:50]} -> {h}")
