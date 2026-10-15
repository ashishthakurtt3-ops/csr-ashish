import urllib.request, re, xml.etree.ElementTree as ET

headers = {'User-Agent': 'Mozilla/5.0'}

# Check sitemap or robots.txt
for u in ["https://www.acclimited.com/robots.txt", "https://www.acclimited.com/sitemap.xml", "https://www.acclimited.com/about-acc"]:
    try:
        req = urllib.request.Request(u, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            txt = r.read().decode('utf-8', errors='ignore')
            print(f"--- {u} (status {r.status}) ---")
            for line in txt.splitlines()[:15]:
                print(line)
    except Exception as e:
        print(f"Error {u}: {e}")
