from curl_cffi import requests
from bs4 import BeautifulSoup
import re

url = "https://www.tcs.com/careers/india/lateral-hiring"
r = requests.get(url, impersonate="chrome124", timeout=12)
soup = BeautifulSoup(r.text, 'html.parser')
for tag in soup.find_all(['h2', 'h3', 'h4', 'h5', 'p', 'li']):
    txt = tag.get_text(' ', strip=True)
    if any(k in txt.lower() for k in ['hiring', 'role', 'experience', 'skill', 'apply', 'track', 'opening', 'specialist', 'engineer', 'developer']):
        if len(txt) < 150:
            print("FOUND:", txt)

