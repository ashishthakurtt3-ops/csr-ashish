import os

found = []
for root, dirs, files in os.walk('.'):
    if '.venv' in root or '.git' in root:
        continue
    for f in files:
        if f.endswith('.py') or f.endswith('.json'):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                    if 'Senior Sustainability Officer' in content or 'Environmental Stewardship & Clean Energy Mission' in content:
                        found.append(p)
            except Exception:
                pass

print("Files containing hallucinated strings:", found)
