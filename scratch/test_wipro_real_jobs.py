from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://careers.wipro.com/go/India/9649255/"
r = requests.get(url, impersonate="chrome124", timeout=12)
print("Wipro India jobs status:", r.status_code, "Len:", len(r.text))
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a', href=True):
    h = a['href']
    t = a.get_text(' ', strip=True)
    if '/job/' in h:
        print(f"  Wipro real job: {t} -> {h}")

