from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://careers.wipro.com/search"
r = requests.get(url, impersonate="chrome124", timeout=12)
soup = BeautifulSoup(r.text, 'html.parser')
print("All a tags:", len(soup.find_all('a')))
for a in soup.find_all('a')[:30]:
    print(a.get_text(strip=True), "->", a.get('href'))
