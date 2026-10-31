with open('templates/admin/ai_config/index.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = re.finditer(r'<div id="(view[^"]+)"', text)
for m in matches:
    pos = m.start()
    line = text[:pos].count('\n') + 1
    print(f"{m.group(1)}: line {line}")
