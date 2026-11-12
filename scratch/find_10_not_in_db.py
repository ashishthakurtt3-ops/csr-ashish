from curl_cffi import requests
import json

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

candidates = [
    {
        'company_name': 'KEC International Limited',
        'homepage_url': 'https://www.kecrpg.com',
        'careers_url': 'https://www.kecrpg.com/careers',
        'csr_url': 'https://www.kecrpg.com/csr'
    },
    {
        'company_name': 'Blue Star Limited',
        'homepage_url': 'https://www.bluestarindia.com',
        'careers_url': 'https://www.bluestarindia.com/careers',
        'csr_url': 'https://www.bluestarindia.com/corporate-social-responsibility'
    },
    {
        'company_name': 'Exide Industries Limited',
        'homepage_url': 'https://www.exideindustries.com',
        'careers_url': 'https://www.exideindustries.com/careers/overview.aspx',
        'csr_url': 'https://www.exideindustries.com/sustainability/csr-policy-and-projects.aspx'
    },
    {
        'company_name': 'Supreme Industries Limited',
        'homepage_url': 'https://www.supreme.co.in',
        'careers_url': 'https://www.supreme.co.in/careers',
        'csr_url': 'https://www.supreme.co.in/csr'
    },
    {
        'company_name': 'Balkrishna Industries Limited',
        'homepage_url': 'https://www.bkt-tires.com',
        'careers_url': 'https://www.bkt-tires.com/ww/en/careers',
        'csr_url': 'https://www.bkt-tires.com/ww/en/csr'
    },
    {
        'company_name': 'Finolex Cables Limited',
        'homepage_url': 'https://www.finolex.com',
        'careers_url': 'https://www.finolex.com/careers',
        'csr_url': 'https://www.finolex.com/csr'
    },
    {
        'company_name': 'Castrol India Limited',
        'homepage_url': 'https://www.castrol.com/en_in/india/home.html',
        'careers_url': 'https://www.castrol.com/en_in/india/home/careers.html',
        'csr_url': 'https://www.castrol.com/en_in/india/home/sustainability/corporate-social-responsibility.html'
    },
    {
        'company_name': 'Raymond Limited',
        'homepage_url': 'https://www.raymond.in',
        'careers_url': 'https://www.raymond.in/careers',
        'csr_url': 'https://www.raymond.in/csr'
    },
    {
        'company_name': 'Escorts Kubota Limited',
        'homepage_url': 'https://www.escortsgroup.com',
        'careers_url': 'https://www.escortsgroup.com/careers.html',
        'csr_url': 'https://www.escortsgroup.com/corporate-social-responsibility.html'
    },
    {
        'company_name': 'Kirloskar Brothers Limited',
        'homepage_url': 'https://www.kirloskarpumps.com',
        'careers_url': 'https://www.kirloskarpumps.com/careers/',
        'csr_url': 'https://www.kirloskarpumps.com/sustainability/csr/'
    },
    {
        'company_name': 'Apar Industries Limited',
        'homepage_url': 'https://apar.com',
        'careers_url': 'https://apar.com/careers/',
        'csr_url': 'https://apar.com/csr/'
    },
    {
        'company_name': 'V-Guard Industries Limited',
        'homepage_url': 'https://www.vguard.in',
        'careers_url': 'https://www.vguard.in/careers',
        'csr_url': 'https://www.vguard.in/csr'
    },
    {
        'company_name': 'VIP Industries Limited',
        'homepage_url': 'https://www.vipbags.com',
        'careers_url': 'https://www.vipbags.com/careers',
        'csr_url': 'https://www.vipbags.com/csr'
    },
    {
        'company_name': 'Kansai Nerolac Paints Limited',
        'homepage_url': 'https://www.nerolac.com',
        'careers_url': 'https://www.nerolac.com/careers',
        'csr_url': 'https://www.nerolac.com/csr'
    }
]

# Check against DB
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from modules.admin_panel.models import Company
db_companies = set(Company.objects.values_list('company_name', flat=True))

verified_10 = []
for c in candidates:
    if c['company_name'] in db_companies:
        print(f"SKIPPING (IN DB): {c['company_name']}", flush=True)
        continue
    
    print(f"Testing {c['company_name']}...", flush=True)
    all_ok = True
    results = {}
    for f in ['homepage_url', 'careers_url', 'csr_url']:
        url = c[f]
        try:
            resp = requests.get(url, impersonate='chrome124', timeout=6, headers=BROWSER_HEADERS, allow_redirects=True)
            results[f] = resp.status_code
            if resp.status_code != 200:
                all_ok = False
        except Exception as e:
            results[f] = str(e)[:30]
            all_ok = False
    print(f"  Result: {results} -> {'OK' if all_ok else 'FAIL'}", flush=True)
    if all_ok:
        verified_10.append(c)
    if len(verified_10) == 10:
        break

print(f"\nFOUND {len(verified_10)} VERIFIED COMPANIES NOT IN DB:", flush=True)
print(json.dumps(verified_10, indent=2), flush=True)
