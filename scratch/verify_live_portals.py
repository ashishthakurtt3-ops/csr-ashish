from curl_cffi import requests

portals = {
    'TCS': 'https://www.tcs.com/careers/india',
    'Wipro': 'https://careers.wipro.com/search',
    'Tata Motors': 'https://careers.tatamotors.com/go/View-All-Opportunities/3505801/',
    'Infosys': 'https://career.infosys.com/',
    'SBI': 'https://sbi.co.in/web/careers/current-openings',
    'Reliance': 'https://careers.ril.com/rilcareers/frmjobsearch.Aspx',
    'Hitachi Energy': 'https://www.hitachienergy.com/careers/open-jobs',
    'Adani': 'https://careers.adani.com/',
    'Mahindra': 'https://jobs.mahindra.com/',
    'L&T': 'https://larsentoubrocareers.peoplestrong.com/portal/',
    'HCL': 'https://www.hcltech.com/careers',
    'ITC': 'https://www.itcportal.com/careers/',
    'Airtel': 'https://www.airtel.in/careers/'
}

for name, url in portals.items():
    try:
        r = requests.get(url, impersonate="chrome124", timeout=10)
        print(f"[{r.status_code}] {name}: {url}")
    except Exception as e:
        print(f"[ERR] {name}: {e}")
