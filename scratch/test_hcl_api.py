from curl_cffi import requests
from bs4 import BeautifulSoup
import re

url = 'https://careers.hcltech.com/search/?q=&locationsearch=India'
r = requests.get(url, impersonate='chrome124')
soup = BeautifulSoup(r.text, 'html.parser')

print("Page Title:", soup.title.string if soup.title else "None")

# Check all links
links = []
for a in soup.find_all('a', href=True):
    href = a['href']
    txt = a.get_text(' ', strip=True)
    if '/job/' in href or 'jobid' in href.lower() or 'requisition' in href.lower():
        links.append((txt, href))

print(f"Found {len(links)} job links:")
for txt, href in links[:10]:
    print(f"  * {txt} -> {href}")

# Check tables or cards
rows = soup.find_all('tr')
print(f"Found {len(rows)} table rows")
for tr in rows[:5]:
    print("  TR:", tr.get_text(' | ', strip=True)[:100])

