from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://careers.wipro.com/go/India/9649255/"
r = requests.get(url, impersonate="chrome124", timeout=12)
soup = BeautifulSoup(r.text, 'html.parser')
for table in soup.find_all(['table', 'ul', 'div']):
    if 'job' in table.get('class', '') or 'search' in table.get('class', ''):
        print("Found container:", table.name, table.get('class'))
        print(table.get_text(' ', strip=True)[:300])
        break

