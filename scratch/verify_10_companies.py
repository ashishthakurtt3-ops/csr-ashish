import urllib.request
import urllib.error
import ssl

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

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
        'company_name': 'Thermax Limited',
        'homepage_url': 'https://www.thermaxglobal.com',
        'careers_url': 'https://www.thermaxglobal.com/careers/',
        'csr_url': 'https://www.thermaxglobal.com/corporate-social-responsibility/'
    },
    {
        'company_name': 'Deepak Nitrite Limited',
        'homepage_url': 'https://www.godeepak.com',
        'careers_url': 'https://www.godeepak.com/careers/',
        'csr_url': 'https://www.godeepak.com/csr/'
    },
    {
        'company_name': 'Exide Industries Limited',
        'homepage_url': 'https://www.exideindustries.com',
        'careers_url': 'https://www.exideindustries.com/careers/overview.aspx',
        'csr_url': 'https://www.exideindustries.com/sustainability/csr-policy-and-projects.aspx'
    },
    {
        'company_name': 'Apollo Tyres Limited',
        'homepage_url': 'https://www.apollotyres.com',
        'careers_url': 'https://www.apollotyres.com/en-in/careers/',
        'csr_url': 'https://www.apollotyres.com/en-in/sustainability/csr/'
    },
    {
        'company_name': 'Supreme Industries Limited',
        'homepage_url': 'https://www.supreme.co.in',
        'careers_url': 'https://www.supreme.co.in/careers',
        'csr_url': 'https://www.supreme.co.in/csr'
    },
    {
        'company_name': 'Godrej Properties Limited',
        'homepage_url': 'https://www.godrejproperties.com',
        'careers_url': 'https://www.godrejproperties.com/careers',
        'csr_url': 'https://www.godrejproperties.com/sustainability/csr'
    },
    {
        'company_name': 'Bata India Limited',
        'homepage_url': 'https://www.bata.com/in/',
        'careers_url': 'https://www.bata.com/in/careers.html',
        'csr_url': 'https://www.bata.com/in/csr.html'
    },
    {
        'company_name': 'Castrol India Limited',
        'homepage_url': 'https://www.castrol.com/en_in/india/home.html',
        'careers_url': 'https://www.castrol.com/en_in/india/home/careers.html',
        'csr_url': 'https://www.castrol.com/en_in/india/home/sustainability/corporate-social-responsibility.html'
    }
]

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'}

for c in candidates:
    print(f"Testing {c['company_name']}...", flush=True)
    for field in ['homepage_url', 'careers_url', 'csr_url']:
        url = c[field]
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=5) as resp:
                print(f"  {field}: HTTP {resp.getcode()}", flush=True)
        except urllib.error.HTTPError as he:
            print(f"  {field}: HTTP {he.code}", flush=True)
        except Exception as e:
            print(f"  {field}: ERROR {e}", flush=True)
