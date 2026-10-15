import urllib.request, re

headers = {'User-Agent': 'Mozilla/5.0'}
req = urllib.request.Request('https://www.acclimited.com', headers=headers)
html = urllib.request.urlopen(req).read().decode('utf-8', errors='ignore')
matches = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*)</a>', html)
for href, text in matches:
    if any(k in href.lower() or k in text.lower() for k in ['career', 'job', 'people', 'work', 'contact']):
        print(f"Text: '{text.strip()}' -> Href: {href}")
