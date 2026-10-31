import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

import re
matches = [m.start() for m in re.finditer(r'pricing-comparison-container', html)]
for i, pos in enumerate(matches):
    print(f"--- Occurrence {i+1} at {pos} ---")
    print(html[max(0, pos-100):min(len(html), pos+150)])

