import urllib.request, re, json
from bs4 import BeautifulSoup

url = 'https://careers.titan.in/in/en/search-results'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')

soup = BeautifulSoup(html, 'html.parser')
for s in soup.find_all('script'):
    txt = s.string or s.text or ''
    if 'phApp' in txt or 'eagerLoadRefineSearch' in txt or 'refineSearch' in txt or 'job' in txt.lower():
        if len(txt) > 200:
            print("FOUND SCRIPT:")
            for line in txt.splitlines():
                if any(k in line for k in ['title', 'jobTitle', 'applyUrl', 'data', 'refineSearch']):
                    print("  LINE:", line[:150])
                    break
