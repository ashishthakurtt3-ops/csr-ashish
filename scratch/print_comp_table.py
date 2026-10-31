import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/js/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

comp_pos = js.find('function renderPlanComparisonTable() {')
next_func = js.find('\nfunction ', comp_pos + 50)
if next_func == -1:
    next_func = comp_pos + 6000
print(js[comp_pos:next_func])

