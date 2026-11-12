from curl_cffi import requests
try:
    r = requests.get('https://www.hcltech.com/careers', impersonate="chrome124", timeout=20)
    print("HCL status:", r.status_code)
except Exception as e:
    print("HCL err:", e)

