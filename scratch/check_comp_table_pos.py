import sys
sys.stdout.reconfigure(encoding='utf-8')
with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

target = 'id="pricing-comparison-container"'
pos = html.find(target)
print("=== AROUND PRICING COMPARISON CONTAINER ===")
print(html[pos-300:pos+300])

# Find where tab-pricing opens and closes
pricing_open = html.find('id="tab-pricing"')
print("tab-pricing starts at:", pricing_open)
# Find closing section tag after tab-pricing
pricing_close = html.find('</section>', pricing_open)
print("tab-pricing closes at:", pricing_close)
print("pricing-comparison-container is at:", pos)
if pos > pricing_close:
    print("ALERT: pricing-comparison-container is OUTSIDE tab-pricing!")
else:
    print("OK: pricing-comparison-container is INSIDE tab-pricing")

