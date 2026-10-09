import requests, re
from bs4 import BeautifulSoup

resp = requests.get('https://careers.adani.com/', headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
print('Len:', len(resp.text))
soup = BeautifulSoup(resp.text, 'lxml')
for a in soup.find_all(['a', 'button', 'iframe'], href=True):
    href = a.get('href', '')
    print('Tag link:', a.text.strip()[:30], '->', href)

urls = set(re.findall(r'https?://[^\s"\'<>]+', resp.text))
for u in sorted(urls):
    if any(k in u.lower() for k in ['oracle', 'job', 'hcm', 'recruiting', 'apply']):
        print('Regex URL:', u)
