with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Add user-quota-widget above active-subscription-card
old_banner = """            <!-- Active User Subscription Status Banner -->
            <div class="active-subscription-card" id="active-subscription-card\""""

new_banner = """            <!-- User Quotas & Progress Widget -->
            <div id="user-quota-widget"></div>

            <!-- Active User Subscription Status Banner -->
            <div class="active-subscription-card" id="active-subscription-card\""""

for le in ['\r\n', '\n']:
    tgt = old_banner.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_banner.replace('\n', le))
        print("Added user-quota-widget to index.html")
        break
else:
    print("WARNING: Could not add user-quota-widget")

# Add pricing-comparison-container below pricing-plans-grid
old_grid_end = """            </div>
        </section>"""

new_grid_end = """            </div>

            <!-- Dynamic Three-Tier Feature Comparison Matrix -->
            <div id="pricing-comparison-container"></div>
        </section>"""

for le in ['\r\n', '\n']:
    tgt = old_grid_end.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_grid_end.replace('\n', le))
        print("Added pricing-comparison-container to index.html")
        break
else:
    print("WARNING: Could not add pricing-comparison-container")

with open('templates/website/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done")

