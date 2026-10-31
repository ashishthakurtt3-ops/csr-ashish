import re

with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

tabs = set(re.findall(r"switchTab\(['\"]([^'\"]+)['\"]\)", text))
print("Defined Tabs in index.html:")
for t in sorted(list(tabs)):
    print(f" - {t}")

