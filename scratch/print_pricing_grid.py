import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/js/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

grid_pos = js.find('function renderPricingGrid() {')
next_func = js.find('async function loadSubscriptionState()', grid_pos)
print(js[grid_pos:next_func])

