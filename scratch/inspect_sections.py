import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open('static/css/style.css', 'r', encoding='utf-8') as f:
    text = f.read()

sections = []
for m in re.finditer(r'/\* ==+[\r\n]+(?:\s*\*?\s*(.*?))[\r\n]+\s*==+ \*/', text):
    title = m.group(1).strip()
    pos = m.start()
    sections.append((pos, title))

print(f"Total sections found: {len(sections)}")
for pos, title in sections:
    print(f"Pos {pos:6d}: {title}")

