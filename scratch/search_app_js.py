import re

with open('static/js/app.js', encoding='utf-8') as f:
    text = f.read()

# Search for functions fetching or rendering jobs, csr, opps
functions = re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', text)
print("Matching functions in app.js:")
for fn in functions:
    if any(k in fn.lower() for k in ['job', 'csr', 'opp', 'proj']):
        print(' ', fn)

# Search for fetch calls inside app.js
fetch_lines = [line.strip() for line in text.splitlines() if 'fetch(' in line]
print(f"\nTotal fetch lines in app.js: {len(fetch_lines)}")
for fl in fetch_lines[:25]:
    print(' ', fl[:100])
