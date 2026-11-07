from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://careers.tatamotors.com/go/View-All-Opportunities/3505801/"
r = requests.get(url, impersonate="chrome124", timeout=12)
print("Tata Motors View All status:", r.status_code, "Len:", len(r.text))
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a', href=True):
    h = a['href']
    t = a.get_text(' ', strip=True)
    if '/job/' in h or 'jobid' in h.lower() or 'opportunity' in h.lower():
        print(f"  {t} -> {h}")
