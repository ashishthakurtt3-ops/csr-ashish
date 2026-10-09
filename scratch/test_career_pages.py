import sys, requests, re, json
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

headers = {'User-Agent': 'CSRIntelligenceResearchBot/1.0 (+public-data; respectful crawling)'}

test_urls = [
    ('Wipro', 'https://careers.wipro.com/'),
    ('Infosys', 'https://www.infosys.com/careers/'),
    ('Reliance', 'https://careers.ril.com/'),
    ('Tata Motors', 'https://www.tatamotors.com/careers/'),
    ('L&T', 'https://www.larsentoubro.com/careers/'),
    ('HCL Tech', 'https://www.hcltech.com/careers'),
    ('ICICI Bank', 'https://www.icicicareers.com/'),
]

for name, url in test_urls:
    try:
        r = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        soup = BeautifulSoup(r.text, 'lxml')
        ats_found = []
        ats_sigs = ['greenhouse', 'lever', 'workday', 'smartrecruiters', 'ashby', 'successfactors', 'taleo', 'oraclecloud', 'icims', 'eightfold', 'darwinbox']
        for a in soup.find_all('a', href=True):
            h = a['href'].lower()
            for s in ats_sigs:
                if s in h:
                    ats_found.append((s, a['href']))
        for iframe in soup.find_all('iframe', src=True):
            s = iframe['src'].lower()
            for sig in ats_sigs:
                if sig in s:
                    ats_found.append(('iframe_' + sig, iframe['src']))
        
        # Check script tags
        for sc in soup.find_all('script', src=True):
            src = sc['src'].lower()
            for sig in ats_sigs:
                if sig in src:
                    ats_found.append(('script_' + sig, sc['src']))
        
        # Check ld+json
        json_lds = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or '')
                if isinstance(data, dict) and data.get('@type') == 'JobPosting':
                    json_lds.append(data.get('title'))
                elif isinstance(data, list):
                    for it in data:
                        if isinstance(it, dict) and it.get('@type') == 'JobPosting':
                            json_lds.append(it.get('title'))
            except Exception:
                pass

        print(f"[{name}] Status: {r.status_code} | Final: {r.url[:60]} | ATS links: {len(ats_found)} | JSON-LD Jobs: {len(json_lds)}")
        if ats_found:
            for at in ats_found[:3]:
                print(f"   -> ATS: {at[0]}: {at[1][:80]}")
    except Exception as e:
        print(f"[{name}] Error: {e}")
