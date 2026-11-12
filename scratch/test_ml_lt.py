from curl_cffi import requests

for name, url in [('Mahindra', 'https://www.mahindra.com/careers'), ('L&T', 'https://www.larsentoubro.com/corporate/careers/')]:
    try:
        r = requests.get(url, impersonate="chrome124", timeout=10)
        print(f"[{r.status_code}] {name}: {url}")
    except Exception as e:
        print(f"[ERR] {name}: {e}")

