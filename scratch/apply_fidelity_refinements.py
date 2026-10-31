import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Update static/css/style.css
with open('static/css/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Add Instrument Serif import at top if not present
if 'family=Instrument+Serif' not in css:
    css = "@import url('https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@1&display=swap');\n" + css
    print("Added Instrument Serif font import to style.css.")

# Update body background with DaanVeda dotted canvas
body_rule = """
/* DaanVeda Canvas Dotted Grid System */
body {
  background-color: #FFFFFF !important;
  background-image: radial-gradient(rgba(10, 108, 255, 0.08) 1.2px, transparent 1.2px) !important;
  background-size: 26px 26px !important;
  background-attachment: fixed !important;
}
"""
css += "\n" + body_rule

# Update pricing headline and em serif styling
heading_fidelity_rules = """
/* DaanVeda Signature Heading Typography (Sans + Italic Serif Accent) */
.pricing-headline {
  font-family: var(--font-heading) !important;
  font-size: 44px !important;
  font-weight: 700 !important;
  letter-spacing: -1.15px !important;
  line-height: 1.15 !important;
  color: #0B1020 !important;
  margin-bottom: 12px !important;
}

.pricing-headline em,
.hero-title em,
.section-title em {
  font-family: "Instrument Serif", Georgia, Cambria, "Times New Roman", serif !important;
  font-style: italic !important;
  font-weight: 400 !important;
  letter-spacing: -0.5px !important;
  background: var(--brand-gradient) !important;
  -webkit-background-clip: text !important;
  -webkit-text-fill-color: transparent !important;
  display: inline-block !important;
}

/* DaanVeda Eyebrow with Flanking Dashes */
.pricing-pill-tag {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  color: #005CE0 !important;
  text-transform: uppercase !important;
  letter-spacing: 2px !important;
  margin-bottom: 14px !important;
}
.pricing-pill-tag::before {
  content: '—' !important;
  color: #005CE0 !important;
  opacity: 0.6 !important;
  margin-right: 8px !important;
}
.pricing-pill-tag::after {
  content: '—' !important;
  color: #005CE0 !important;
  opacity: 0.6 !important;
  margin-left: 8px !important;
}

.pricing-subtext {
  font-family: var(--font-body) !important;
  font-size: 16px !important;
  font-weight: 300 !important;
  color: #8A91A6 !important;
  line-height: 1.6 !important;
  max-width: 640px !important;
  margin: 0 auto 24px !important;
}

/* DaanVeda Pill Billing Toggle with Gradient Discount Tag */
.billing-toggle-pill {
  background: #F1F3F7 !important;
  border: 1px solid #ECEEF4 !important;
  border-radius: 999px !important;
  padding: 4px !important;
  gap: 4px !important;
}
.cycle-btn {
  padding: 8px 22px !important;
  border-radius: 999px !important;
  font-size: 13.5px !important;
  font-weight: 500 !important;
  color: #0B1020 !important;
  transition: all var(--transition-fast) !important;
}
.cycle-btn.active {
  background: #FFFFFF !important;
  color: #0B1020 !important;
  font-weight: 600 !important;
  box-shadow: 0 2px 6px rgba(16, 24, 40, 0.08) !important;
}
.save-pill {
  background: linear-gradient(93.75deg, #0A6CFF 0%, #9E0DFF 100%) !important;
  color: #FFFFFF !important;
  font-size: 10.5px !important;
  font-weight: 700 !important;
  padding: 2px 8px !important;
  border-radius: 999px !important;
  letter-spacing: 0.2px !important;
}
"""
css += "\n" + heading_fidelity_rules

with open('static/css/style.css', 'w', encoding='utf-8') as f:
    f.write(css)
print("Updated static/css/style.css with DaanVeda typography and canvas pattern.")


# 2. Update templates/website/index.html
with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace headline in tab-pricing
old_h2 = '<h2 class="pricing-headline">All CSR &amp; Job Intelligence, <span class="gradient-text">One honest price</span></h2>'
new_h2 = '<h2 class="pricing-headline">All CSR &amp; Job Intelligence, <em>One honest price</em></h2>'

if old_h2 in html:
    html = html.replace(old_h2, new_h2)
    print("Replaced pricing headline in index.html with signature <em> styling.")
else:
    print("WARNING: old_h2 not found in index.html.")

# Update subtext in tab-pricing to match DaanVeda's crisp rhythm
old_sub = '<p class="pricing-subtext">\n                    Choose the plan that fits your growth. Scale up seamlessly as your team and intelligence needs expand.\n                </p>'
new_sub = '<p class="pricing-subtext">\n                    5× more verified corporate &amp; CSR intelligence than a typical stack — for less than 1/20th the cost.\n                </p>'

if old_sub in html:
    html = html.replace(old_sub, new_sub)
    print("Updated pricing subtext in index.html.")
else:
    print("WARNING: old_sub not found in index.html.")

with open('templates/website/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Saved templates/website/index.html.")


# 3. Update static/js/app.js for Comparison Table heading
with open('static/js/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

old_comp_heading = """                    <span class="daanveda-pill-eyebrow">Complete Capability Matrix</span>
                    <h3 style="font-size:28px; font-weight:800; color:var(--text-primary); letter-spacing:-0.7px; margin:8px 0 12px;">Compare Plan Features</h3>"""

new_comp_heading = """                    <span class="pricing-pill-tag">Complete Capability Matrix</span>
                    <h3 class="pricing-headline" style="font-size:32px !important; margin:6px 0 12px !important;">Compare Plan Features, <em>Side by Side</em></h3>"""

if old_comp_heading in js:
    js = js.replace(old_comp_heading, new_comp_heading)
    print("Updated comparison table heading in app.js with DaanVeda signature <em> styling.")
else:
    print("WARNING: old_comp_heading not found in app.js.")

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("Saved static/js/app.js.")

