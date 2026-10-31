import socket
import requests

test_domains = [
    "unionbankofindia.bank",
    "jindalsteel.com",
    "bankofindia.co.in",
    "centralbankofindia.co.in"
]

for d in test_domains:
    try:
        ip = socket.gethostbyname(d)
        print(f"{d} -> resolves to {ip}")
    except Exception as e:
        print(f"{d} -> DNS fail: {e}")
        
    try:
        resp = requests.get(f"https://{d}", timeout=8, allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"})
        print(f"  HTTP: {resp.status_code}, final URL: {resp.url}")
    except Exception as e:
        print(f"  HTTP error: {e}")

