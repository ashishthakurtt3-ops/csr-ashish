import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('static/css/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

# 1. Update :root variables
root_start = css.find(':root {')
root_end = css.find('}', root_start)

daanveda_root = """:root {
  /* DaanVeda Design System Light Palette */
  --bg-canvas: #FAFBFC;
  --bg-surface: #FFFFFF;
  --bg-surface-elevated: #FFFFFF;
  --bg-surface-subtle: #F8FAFC;
  --bg-card: #FFFFFF;
  --bg-card-hover: #FFFFFF;
  --bg-input: #FFFFFF;
  --bg-input-focus: #FFFFFF;
  --bg-glass: rgba(255, 255, 255, 0.88);

  /* Precise DaanVeda Borders */
  --border-color: #E0E4EE;
  --border-subtle: #ECEEF4;
  --border-card: #E0E4EE;
  --border-card-hover: #0A6CFF;
  --border-focus: #0A6CFF;

  /* Typography */
  --text-white: #0B1020;
  --text-primary: #0B1020;
  --text-secondary: #465478;
  --text-muted: #8A91A6;
  --text-link: #0A6CFF;
  --text-link-hover: #005CE0;

  /* Sidebar Design Token (Deep Navy) */
  --sidebar-bg: #0B1020;
  --sidebar-border: #E0E4EE;
  --sidebar-text: #0B1020;
  --sidebar-muted: #8A91A6;
  --sidebar-hover: rgba(10, 108, 255, 0.06);
  --sidebar-active-bg: #EFF6FF;
  --sidebar-active-text: #0A6CFF;
  --sidebar-active-border: #0A6CFF;

  /* DaanVeda Brand Accents & Gradient Tokens */
  --primary-brand: #0A6CFF;
  --primary-brand-hover: #005CE0;
  --primary-brand-light: #EFF6FF;
  --brand-purple: #9E0DFF;
  --brand-gradient: linear-gradient(93.75deg, #0A6CFF 0%, #9E0DFF 100%);
  --brand-gradient-hover: linear-gradient(93.75deg, #005CE0 0%, #8800E6 100%);
  --brand-gradient-subtle: linear-gradient(135deg, rgba(10, 108, 255, 0.07) 0%, rgba(158, 13, 255, 0.07) 100%);
  --brand-gradient-border: linear-gradient(93.75deg, rgba(10, 108, 255, 0.4) 0%, rgba(158, 13, 255, 0.4) 100%);

  --accent: #0A6CFF;
  --accent-light: #EFF6FF;
  --accent-hover: #005CE0;
  --accent-cyan: #0A6CFF;
  --accent-cyan-light: #EFF6FF;
  --accent-indigo: #4F46E5;
  --accent-indigo-hover: #4338CA;

  --success: #059669;
  --success-bg: #ECFDF5;
  --success-border: #A7F3D0;
  --accent-emerald: #059669;
  --accent-emerald-dark: #047857;

  --warning: #D97706;
  --warning-bg: #FFFBEB;
  --warning-border: #FDE68A;
  --accent-amber: #D97706;

  --error: #DC2626;
  --error-bg: #FEF2F2;
  --error-border: #FECACA;
  --accent-rose: #DC2626;

  --info: #0284C7;
  --info-bg: #F0F9FF;
  --info-border: #BAE6FD;

  --ai-purple: #9E0DFF;
  --ai-purple-bg: #FAF5FF;
  --ai-purple-border: #E9D5FF;
  --accent-purple: #9E0DFF;

  /* Typography Families */
  --font-heading: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, Menlo, monospace;

  /* DaanVeda Radii & Geometry (Pills + Generous Curves) */
  --radius-xs: 6px;
  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 18px;
  --radius-xl: 20px;
  --radius-2xl: 24px;
  --radius-3xl: 32px;
  --radius-card: 20px;
  --radius-card-lg: 32px;
  --radius-pill: 999px;
  --radius-full: 9999px;

  /* DaanVeda Shadows & Elevation */
  --shadow-xs: 0 1px 2px 0 rgba(16, 24, 40, 0.05);
  --shadow-sm: 0 1px 3px 0 rgba(16, 24, 40, 0.06), 0 1px 2px -1px rgba(16, 24, 40, 0.04);
  --shadow-card: 0px 2px 7px 0px rgba(16, 24, 40, 0.05), 0px 12px 28px -12px rgba(16, 24, 40, 0.08);
  --shadow-card-hover: 0px 4px 14px 0px rgba(16, 24, 40, 0.08), 0px 20px 40px -16px rgba(10, 108, 255, 0.16);
  --shadow-elevated: 0px 12px 32px -8px rgba(16, 24, 40, 0.12), 0px 20px 48px -16px rgba(10, 108, 255, 0.18);
  --shadow-modal: 0 20px 40px -10px rgba(11, 16, 32, 0.18), 0 10px 18px -6px rgba(11, 16, 32, 0.1);
  --shadow-btn-glow: 0px 12px 26px -12px rgba(11, 85, 255, 0.8);

  /* Content-Width & Layout Standards */
  --content-max-width: 1360px;
  --content-padding-x: clamp(20px, 2.5vw, 36px);
  --content-reading-width: 760px;
  --content-form-width: 860px;
  --modal-width-standard: 620px;
  --modal-width-large: 880px;
  --modal-width-xlarge: 1080px;

  /* Transitions */
  --transition-fast: 0.18s cubic-bezier(0.16, 1, 0.3, 1);
  --transition-smooth: 0.28s cubic-bezier(0.16, 1, 0.3, 1);

  /* Admin Compat Tokens */
  --admin-bg: var(--bg-canvas);
  --admin-surface: var(--bg-surface);
  --admin-surface-elevated: var(--bg-surface-elevated);
  --admin-card: var(--bg-card);
  --admin-border: var(--border-color);
  --admin-primary: var(--primary-brand);
  --admin-primary-hover: var(--primary-brand-hover);
  --admin-accent: var(--accent);
  --admin-success: var(--success);
  --admin-warning: var(--warning);
  --admin-danger: var(--error);
  --admin-text: var(--text-primary);
  --admin-muted: var(--text-secondary);
}"""

css = css[:root_start] + daanveda_root + css[root_end+1:]

# 2. Add Gradient text and check badge utility right after :root
utility_rules = """

/* DaanVeda Signature Gradient & Utility Classes */
.gradient-text {
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-block;
}

.daanveda-pill-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(10, 108, 255, 0.06);
  border: 1px solid rgba(10, 108, 255, 0.18);
  padding: 6px 18px;
  border-radius: var(--radius-pill);
  font-size: 12.5px;
  font-weight: 700;
  color: var(--primary-brand);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 14px;
}

.daanveda-check-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #EFF6FF;
  color: #0A6CFF;
  flex-shrink: 0;
  box-shadow: 0 1px 3px rgba(10, 108, 255, 0.15);
}
.daanveda-check-badge svg {
  width: 12px;
  height: 12px;
  stroke: #0A6CFF;
}
.daanveda-check-badge.sm {
  width: 18px;
  height: 18px;
}
.daanveda-check-badge.sm svg {
  width: 10px;
  height: 10px;
}
"""
css = css[:root_start + len(daanveda_root)] + utility_rules + css[root_start + len(daanveda_root):]

# 3. Update Buttons
btn_section_old = """.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 40px;
  padding: 0 16px;
  background: var(--primary-brand);
  color: #FFFFFF;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-fast);
}
.btn-primary:hover {
  background: var(--primary-brand-hover);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 40px;
  padding: 0 14px;
  background: var(--bg-surface);
  color: var(--text-primary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-fast);
}
.btn-secondary:hover {
  background: var(--bg-surface-subtle);
  border-color: #CBD5E1;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: transparent;
  color: var(--primary-brand);
  border: 1px solid var(--primary-brand);
  border-radius: var(--radius-sm);
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.btn-outline:hover {
  background: var(--primary-brand-light);
}"""

btn_section_new = """.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 42px;
  padding: 0 24px;
  background: var(--brand-gradient);
  color: #FFFFFF;
  border: none;
  border-radius: var(--radius-pill);
  font-family: var(--font-body);
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
  box-shadow: 0px 8px 20px -6px rgba(11, 85, 255, 0.65);
  transition: all var(--transition-fast);
}
.btn-primary:hover {
  background: var(--brand-gradient-hover);
  box-shadow: 0px 12px 28px -6px rgba(158, 13, 255, 0.45);
  transform: translateY(-1px);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 42px;
  padding: 0 20px;
  background: #FFFFFF;
  color: var(--text-primary);
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-pill);
  font-family: var(--font-body);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-fast);
}
.btn-secondary:hover {
  background: var(--primary-brand-light);
  border-color: var(--primary-brand);
  color: var(--primary-brand);
  transform: translateY(-1px);
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 18px;
  background: transparent;
  color: var(--primary-brand);
  border: 1.5px solid var(--primary-brand);
  border-radius: var(--radius-pill);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.btn-outline:hover {
  background: var(--primary-brand-light);
  transform: translateY(-1px);
}"""

if btn_section_old in css:
    css = css.replace(btn_section_old, btn_section_new)
    print("Replaced button section successfully.")
else:
    print("WARNING: Button section not matched exactly.")

# 4. Update Header Nav Link styles
old_nav_link = """.nav-link-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-fast);
}
.nav-link-btn:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.05);
}
.nav-link-btn.active {
  color: var(--primary-brand);
  background: var(--primary-brand-light);
}"""

new_nav_link = """.nav-link-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13.5px;
  font-weight: 600;
  border-radius: var(--radius-pill);
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-fast);
}
.nav-link-btn:hover {
  color: var(--primary-brand);
  background: rgba(10, 108, 255, 0.06);
}
.nav-link-btn.active {
  color: var(--primary-brand);
  background: var(--primary-brand-light);
  font-weight: 700;
  box-shadow: inset 0 0 0 1px rgba(10, 108, 255, 0.16);
}"""

if old_nav_link in css:
    css = css.replace(old_nav_link, new_nav_link)
    print("Replaced nav link button style.")
else:
    print("WARNING: nav_link_btn not matched exactly.")

# 5. Update Pricing Section CSS
pricing_start = css.find('.pricing-hero {')
pricing_end = css.find('/* ==========================================================================\n   MODAL ARCHITECTURE', pricing_start)

daanveda_pricing_css = """.pricing-hero {
  text-align: center;
  max-width: 760px;
  margin: 0 auto 36px;
}
.pricing-pill-tag {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(10, 108, 255, 0.06);
  border: 1px solid rgba(10, 108, 255, 0.18);
  padding: 6px 18px;
  border-radius: var(--radius-pill);
  font-size: 12.5px;
  font-weight: 700;
  color: var(--primary-brand);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 14px;
}
.pricing-headline {
  font-size: 38px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -1.2px;
  line-height: 1.15;
  margin-bottom: 12px;
}
.pricing-subtext {
  font-size: 16px;
  color: var(--text-secondary);
  line-height: 1.6;
  max-width: 640px;
  margin: 0 auto;
}
.billing-cycle-wrap {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}
.billing-toggle-pill {
  display: inline-flex;
  align-items: center;
  background: #F1F3F7;
  border: 1px solid #ECEEF4;
  border-radius: var(--radius-pill);
  padding: 5px;
  gap: 4px;
}
.cycle-btn {
  padding: 9px 24px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13.5px;
  font-weight: 600;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.cycle-btn.active {
  background: #FFFFFF;
  color: var(--text-primary);
  font-weight: 700;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.save-pill {
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  font-weight: 800;
  background: #ECFDF5;
  color: #059669;
  letter-spacing: 0.2px;
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 380px));
  gap: 28px;
  justify-content: center;
  max-width: 1240px;
  margin-inline: auto;
  margin-bottom: 48px;
}
.pricing-card {
  background: #FFFFFF;
  border: 1.5px solid var(--border-color);
  border-radius: 32px;
  padding: 36px 30px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.pricing-card:hover {
  box-shadow: var(--shadow-elevated);
  border-color: var(--primary-brand);
  transform: translateY(-4px);
}
.pricing-card.featured {
  border: 1.5px solid rgba(10, 108, 255, 0.4);
  box-shadow: 0px 4px 16px 0px rgba(16, 24, 40, 0.08), 0px 20px 44px -12px rgba(10, 108, 255, 0.18);
}
.pricing-card.featured::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 6px;
  background: var(--brand-gradient);
}
.featured-badge {
  position: absolute;
  top: 16px;
  right: 24px;
  background: var(--brand-gradient);
  color: #FFFFFF;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 4px 14px;
  border-radius: var(--radius-pill);
  box-shadow: 0 4px 12px rgba(10, 108, 255, 0.3);
}
.plan-name {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
  margin-bottom: 6px;
}
.plan-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 22px;
  min-height: 42px;
}
.plan-price {
  margin-bottom: 20px;
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.plan-price .currency {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
}
.plan-price .amount {
  font-family: var(--font-heading);
  font-size: 46px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -1.2px;
  line-height: 1;
}
.plan-price .period {
  font-size: 14px;
  color: var(--text-muted);
  font-weight: 600;
}
.plan-features {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 28px;
  font-size: 14px;
  color: var(--text-secondary);
  border-top: 1px solid var(--border-color);
  padding-top: 22px;
}
.plan-features li {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  line-height: 1.45;
}
.plan-features li svg {
  width: 18px;
  height: 18px;
  color: var(--primary-brand);
  flex-shrink: 0;
  margin-top: 2px;
}

/* User Active Subscription & Wallet Cards */
.active-subscription-card {
  background: #FFFFFF;
  border: 1.5px solid var(--border-color);
  border-radius: 20px;
  padding: 22px 28px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 28px;
  box-shadow: var(--shadow-card);
}
.active-sub-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.active-sub-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.portal-wallet-section-card {
  background: #FFFFFF;
  border: 1.5px solid var(--border-color);
  border-radius: 24px;
  padding: 28px;
  margin-bottom: 28px;
  box-shadow: var(--shadow-card);
  position: relative;
  overflow: hidden;
}
.portal-wallet-section-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 6px;
  height: 100%;
  background: var(--brand-gradient);
}

"""

css = css[:pricing_start] + daanveda_pricing_css + css[pricing_end:]
print("Updated pricing section CSS successfully.")

# 6. Update Cards styling (.company-card, .job-card, .rfp-card, etc.)
cards_old = """.company-card, .job-card, .rfp-card, .esg-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-card);
  transition: all var(--transition-fast);
  display: flex;
  flex-direction: column;
}
.company-card:hover, .job-card:hover, .rfp-card:hover, .esg-card:hover {
  box-shadow: var(--shadow-card-hover);
  border-color: var(--accent);
  transform: translateY(-2px);
}"""

cards_new = """.company-card, .job-card, .rfp-card, .esg-card {
  background: #FFFFFF;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  padding: 22px 24px;
  box-shadow: var(--shadow-card);
  transition: all var(--transition-fast);
  display: flex;
  flex-direction: column;
}
.company-card:hover, .job-card:hover, .rfp-card:hover, .esg-card:hover {
  box-shadow: var(--shadow-card-hover);
  border-color: var(--primary-brand);
  transform: translateY(-2px);
}"""

if cards_old in css:
    css = css.replace(cards_old, cards_new)
    print("Replaced card styles successfully.")
else:
    print("WARNING: cards_old not found.")

# 7. Update Inputs and Pill Styling for search bars & subnav
search_inputs_daanveda = """
/* DaanVeda Pill Search & Filter Controls */
.search-input-pill, input[type="text"].search-box, .filter-select-pill {
  border-radius: var(--radius-pill) !important;
  border: 1.5px solid var(--border-color) !important;
  background: #FFFFFF !important;
  color: var(--text-primary) !important;
  padding: 10px 20px !important;
  font-size: 13.5px !important;
  transition: all var(--transition-fast) !important;
}
.search-input-pill:focus, input[type="text"].search-box:focus, .filter-select-pill:focus {
  border-color: var(--primary-brand) !important;
  box-shadow: 0 0 0 3px rgba(10, 108, 255, 0.15) !important;
  outline: none !important;
}

.jobs-nav-pills {
  display: flex;
  gap: 8px;
  background: #F1F3F7;
  padding: 4px;
  border-radius: var(--radius-pill);
  width: fit-content;
}
.jobs-nav-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.jobs-nav-pill.active {
  background: #FFFFFF;
  color: var(--text-primary);
  font-weight: 700;
  box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}
"""
css += "\n" + search_inputs_daanveda

with open('static/css/style.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("static/css/style.css updated and saved successfully.")

