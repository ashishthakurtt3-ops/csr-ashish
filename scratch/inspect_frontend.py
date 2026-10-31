import re

with open('templates/website/index.html', encoding='utf-8') as f:
    text = f.read()

print('Length of index.html:', len(text))
print('\nRelevant IDs in index.html:')
ids = re.findall(r'id=["\']([\w\-]+)["\']', text)
for i in sorted(set(ids)):
    if any(k in i.lower() for k in ['job', 'csr', 'opp', 'proj', 'tab', 'stat', 'count', 'total', 'card']):
        print(' ', i)

with open('static/js/app.js', encoding='utf-8') as f:
    js_text = f.read()

print('\nLength of static/js/app.js:', len(js_text))
print('\nAPI calls in app.js:')
for m in re.finditer(r'fetch\(["\']([^"\']+)["\']', js_text):
    print(' ', m.group(1))

print('\nEndpoints called via template strings in app.js:')
for m in re.finditer(r'fetch\(`([^`]+)`', js_text):
    print(' ', m.group(1)[:80])
