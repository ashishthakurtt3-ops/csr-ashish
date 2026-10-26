import requests
from bs4 import BeautifulSoup
import json

url = 'https://jobs.heromotocorp.com/job/Raipur-TERRITORY-MANAGER-SALES-CT-492001/1368423366/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

try:
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {resp.status_code}")
    print(f"Final URL: {resp.url}")
    print(f"Length: {len(resp.text)}")
    
    soup = BeautifulSoup(resp.text, 'lxml')
    print("Page Title:", soup.title.string.strip() if soup.title and soup.title.string else "No title")
    
    # Save raw html for analysis
    with open('scripts/hero_job_detail.html', 'w', encoding='utf-8') as f:
        f.write(resp.text)
    print("Saved raw HTML to scripts/hero_job_detail.html")

    terms = [
        'Territory Manager', '6 Oct 2026', 'Raipur', '492001', 'India BU', 'E4 to M2',
        'Role and purpose', 'responsibilities', 'Day in the Life', 'Academic Qualification',
        'Technical Skills', 'Behavioural Skills', 'Hero MotoCorp'
    ]
    print("\n--- Checking Terms in Raw HTML ---")
    for t in terms:
        found = t.lower() in resp.text.lower()
        print(f"'{t}': {found}")

    scripts = soup.find_all('script', type='application/ld+json')
    print(f"\nJSON-LD scripts found: {len(scripts)}")
    for i, s in enumerate(scripts):
        raw = s.string or ''
        print(f"Script {i} (len {len(raw)}): {raw[:300]}")

except Exception as e:
    print(f"Error fetching: {e}")
