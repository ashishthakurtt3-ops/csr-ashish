from curl_cffi import requests
from bs4 import BeautifulSoup

url = "https://careers.wipro.com/go/India/9649255/"
r = requests.get(url, impersonate="chrome124", timeout=12)
soup = BeautifulSoup(r.text, 'html.parser')
lines = [l.strip() for l in soup.get_text('\n').split('\n') if l.strip()]
print("Total text lines:", len(lines))
print("\n".join(lines[30:80]))
