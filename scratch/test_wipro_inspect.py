from curl_cffi import requests
from bs4 import BeautifulSoup
import re

url = "https://careers.wipro.com/go/India/9649255/"
r = requests.get(url, impersonate="chrome124", timeout=12)
soup = BeautifulSoup(r.text, 'html.parser')
for a in soup.find_all('a', href=True):
    h = a['href']
    t = a.get_text(' ', strip=True)
    if not h.startswith(('#', 'javascript:', 'mailto:')) and len(t) > 3:
        if any(k in h.lower() or k in t.lower() for k in ['developer', 'engineer', 'lead', 'manager', 'consultant', 'analyst', 'specialist', 'architect', 'executive']):
            print(f"Role: '{t}' -> '{h}'")
