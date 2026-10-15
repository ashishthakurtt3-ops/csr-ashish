import urllib.request
import re

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def check(url):
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8', errors='ignore')
            links = re.findall(r'href=["\']([^"\']+)["\']', content, re.I)
            career_links = [l for l in links if any(k in l.lower() for k in ['career', 'job', 'work-with-us', 'people'])]
            print(f"Results for {url} (status: {resp.status}):")
            for cl in set(career_links[:10]):
                print("  ", cl)
    except Exception as e:
        print(f"Error fetching {url}: {e}")

check("https://www.acclimited.com")
check("https://www.ambujacement.com")
