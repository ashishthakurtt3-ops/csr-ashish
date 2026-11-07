from curl_cffi import requests

r = requests.get("https://hitachi.wd1.myworkdayjobs.com/en-US/hitachi", impersonate="chrome124", timeout=12)
print("Hitachi Workday GET status:", r.status_code, "Length:", len(r.text))
print("First 300 chars:", r.text[:300])
