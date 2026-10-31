import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/js/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

comp_pos = js.find('function renderPlanComparisonTable() {')
print(js[comp_pos+5300:comp_pos+6800])

