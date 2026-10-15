import re
import urllib.request
import json

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all fetch calls
fetch_patterns = re.findall(r'fetch\((.*?)\)', content)
endpoints = set()
for p in fetch_patterns:
    # Look for ${API_BASE}/something or '/api/something' or '/something'
    urls = re.findall(r'[`\'\"](?:\${API_BASE})?(/[^`\'\"?]+)', p)
    for u in urls:
        endpoints.add(u)

print("Unique endpoints called by frontend JS:")
for ep in sorted(endpoints):
    # Test if it returns 200 or 404
    test_url = f"http://127.0.0.1:8000{ep}"
    status = "UNKNOWN"
    try:
        req = urllib.request.urlopen(test_url)
        status = f"200 OK ({len(req.read())} bytes)"
    except urllib.error.HTTPError as e:
        status = f"HTTP {e.code}"
    except Exception as e:
        status = f"ERR: {e}"
    print(f"  {ep:<35} -> {status}")
