with open('static/js/app.js', encoding='utf-8') as f:
    text = f.read()

import re

for fn in ['loadJobs', 'loadOpportunities', 'loadCsrProjects']:
    m = re.search(r'async function ' + fn + r'\(.*?\n\}', text, re.DOTALL)
    if not m:
        m = re.search(r'function ' + fn + r'\(.*?\n\}', text, re.DOTALL)
    print(f"=== {fn} ===")
    if m:
        print(m.group(0)[:1500])
    else:
        print("Not found with simple regex, searching definition...")
        idx = text.find(f"function {fn}")
        if idx != -1:
            print(text[idx:idx+1500])
