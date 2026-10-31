import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('static/js/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Make backup of app.js
with open('static/js/app.js.bak', 'w', encoding='utf-8') as f:
    f.write(js)
print("Backup created: static/js/app.js.bak")

# Check position of renderPricingGrid
grid_pos = js.find('function renderPricingGrid() {')
print("renderPricingGrid at:", grid_pos)

# Check position of renderPlanComparisonTable
comp_pos = js.find('function renderPlanComparisonTable() {')
print("renderPlanComparisonTable at:", comp_pos)

# Check position of renderUserQuotaWidget
quota_pos = js.find('function renderUserQuotaWidget() {')
print("renderUserQuotaWidget at:", quota_pos)

