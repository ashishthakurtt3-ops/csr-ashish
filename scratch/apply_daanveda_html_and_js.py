import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. Update templates/website/index.html
with open('templates/website/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace pricing hero
old_pricing_hero = """            <div class="pricing-hero">
                <div class="pricing-pill-tag">
                    Institutional Tier Management
                </div>
                <h2 class="pricing-headline">Transparent Access for Non-Profits &amp; Institutions</h2>
                <p class="pricing-subtext">
                    Authoritative intelligence tracking verified corporate donation budgets, Section 135 projects, and active career openings directly from corporate ATS portals.
                </p>"""

new_pricing_hero = """            <div class="pricing-hero">
                <div class="pricing-pill-tag">
                    Plan and Pricing
                </div>
                <h2 class="pricing-headline">All CSR &amp; Job Intelligence, <span class="gradient-text">One honest price</span></h2>
                <p class="pricing-subtext">
                    Choose the plan that fits your growth. Scale up seamlessly as your team and intelligence needs expand.
                </p>"""

if old_pricing_hero in html:
    html = html.replace(old_pricing_hero, new_pricing_hero)
    print("Replaced pricing hero in index.html.")
else:
    print("WARNING: old_pricing_hero not found.")

# Replace portal-wallet-section-card styling
old_wallet_card_head = '<div class="portal-wallet-section-card" id="portal-wallet-section-card" style="background:linear-gradient(135deg, rgba(16,185,129,0.14), rgba(15,23,42,0.92)); border:1.5px solid rgba(16,185,129,0.38); border-radius:var(--radius-lg); padding:22px 24px; margin-bottom:24px; box-shadow:0 8px 32px -4px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08);">'
new_wallet_card_head = '<div class="portal-wallet-section-card" id="portal-wallet-section-card" style="background:#FFFFFF; border:1.5px solid var(--border-color); border-radius:24px; padding:28px 32px; margin-bottom:28px; box-shadow:var(--shadow-card);">'

if old_wallet_card_head in html:
    html = html.replace(old_wallet_card_head, new_wallet_card_head)
    print("Replaced portal-wallet-section-card head in index.html.")
else:
    print("WARNING: old_wallet_card_head not found.")

# Update wallet balance box and inline recharge input in index.html
old_wallet_box = """                    <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:12px; padding:12px 22px; text-align:right; min-width:190px;">
                        <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:var(--primary-brand); font-weight:700;">Available Wallet Balance</div>
                        <div class="mono" id="pricing-wallet-balance-val" style="font-size:26px; font-weight:900; color:var(--accent-emerald); margin-top:2px;">₹0.00</div>
                        <div style="font-size:11px; color:var(--text-muted); margin-top:2px;" id="pricing-wallet-status-note">Ready for immediate checkout</div>
                    </div>"""

new_wallet_box = """                    <div style="background:#FAFBFF; border:1.5px solid var(--border-color); border-radius:18px; padding:14px 24px; text-align:right; min-width:200px;">
                        <div style="font-size:11.5px; text-transform:uppercase; letter-spacing:0.8px; color:var(--primary-brand); font-weight:700;">Available Wallet Balance</div>
                        <div class="mono" id="pricing-wallet-balance-val" style="font-size:28px; font-weight:900; color:var(--text-primary); margin-top:3px;">₹0.00</div>
                        <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;" id="pricing-wallet-status-note">Ready for immediate checkout</div>
                    </div>"""

if old_wallet_box in html:
    html = html.replace(old_wallet_box, new_wallet_box)
    print("Replaced wallet balance box in index.html.")
else:
    print("WARNING: old_wallet_box not found.")

# Update wallet input & recharge button
old_recharge_row = """                        <input type="number" id="inline-wallet-amount-input" min="1" step="any" placeholder="Enter number as money (e.g. 5000)"
                               style="width:100%; box-sizing:border-box; padding:10px 14px 10px 32px; background:var(--bg-input); border:1.5px solid var(--border-color); border-radius:8px; color:var(--text-primary); font-size:14.5px; font-family:'JetBrains Mono',monospace; outline:none;"
                               onkeydown="if(event.key==='Enter') executeInlineWalletRecharge();">
                    </div>
                    <button type="button" class="btn-primary" id="btn-inline-recharge" onclick="executeInlineWalletRecharge()"
                            style="padding:10px 22px; font-size:13.5px; font-weight:700; background:linear-gradient(135deg, #10b981, #059669); border:none; box-shadow:var(--shadow-sm);">
                        💰 Add to Wallet
                    </button>"""

new_recharge_row = """                        <input type="number" id="inline-wallet-amount-input" min="1" step="any" placeholder="Enter number as money (e.g. 5000)"
                               style="width:100%; box-sizing:border-box; padding:10px 16px 10px 32px; background:var(--bg-input); border:1.5px solid var(--border-color); border-radius:var(--radius-pill); color:var(--text-primary); font-size:14px; font-family:'JetBrains Mono',monospace; outline:none;"
                               onkeydown="if(event.key==='Enter') executeInlineWalletRecharge();">
                    </div>
                    <button type="button" class="btn-primary" id="btn-inline-recharge" onclick="executeInlineWalletRecharge()"
                            style="padding:10px 24px; font-size:13.5px; font-weight:700;">
                        💰 Add to Wallet
                    </button>"""

if old_recharge_row in html:
    html = html.replace(old_recharge_row, new_recharge_row)
    print("Replaced recharge input and button in index.html.")
else:
    print("WARNING: old_recharge_row not found.")

# Update active-subscription-card styling
old_active_sub = '<div class="active-subscription-card" id="active-subscription-card" style="background:var(--bg-card); border:1px solid var(--border-card); border-radius:var(--radius-lg); padding:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom:28px;">'
new_active_sub = '<div class="active-subscription-card" id="active-subscription-card" style="background:#FFFFFF; border:1.5px solid var(--border-color); border-radius:20px; padding:22px 28px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom:28px; box-shadow:var(--shadow-card);">'

if old_active_sub in html:
    html = html.replace(old_active_sub, new_active_sub)
    print("Replaced active-subscription-card in index.html.")
else:
    print("WARNING: old_active_sub not found.")

with open('templates/website/index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Saved templates/website/index.html successfully.")


# 2. Update static/js/app.js
with open('static/js/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Update renderPricingGrid features list checkmark
old_feat_map = "const featuresHtml = features.map(f => `<li>✓ ${escapeHtml(f)}</li>`).join('');"
new_feat_map = """const featuresHtml = features.map(f => `
            <li>
                <span class="daanveda-check-badge">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                </span>
                <span>${escapeHtml(f)}</span>
            </li>
        `).join('');"""

if old_feat_map in js:
    js = js.replace(old_feat_map, new_feat_map)
    print("Replaced featuresHtml checkmarks in renderPricingGrid.")
else:
    print("WARNING: old_feat_map not found in app.js.")

# Update pricing card active border and badge in renderPricingGrid
old_pricing_card_markup = """        html += `
            <div class="pricing-card ${isFeatured ? 'featured' : ''}" id="card-plan-${planCode}" style="${isCurrentActive ? 'border: 2px solid var(--accent-cyan);' : ''}">
                ${isFeatured ? `<div class="featured-badge">${plan.badge || 'MOST POPULAR'}</div>` : (plan.badge ? `<div style="font-size:10.5px; font-weight:700; color:var(--accent-cyan); text-transform:uppercase; margin-bottom:4px;">${plan.badge}</div>` : '')}
                <div class="plan-header">
                    <h3 class="plan-name">${escapeHtml(plan.name)}</h3>
                    <p class="plan-desc">${escapeHtml(plan.description || '')}</p>
                </div>
                <div class="plan-price">
                    <span class="currency">₹</span>
                    <span class="amount">${displayPrice.toLocaleString('en-IN')}</span>
                    <span class="period">${periodText}</span>
                </div>
                ${subPriceText ? `<div style="font-size:11.5px; color:var(--accent-cyan); margin:-8px 0 14px 0; font-weight:600;">${subPriceText}</div>` : ''}
                <ul class="plan-features">
                    ${featuresHtml}
                </ul>
                <button class="${buttonClass}" style="width:100%;" ${buttonDisabled ? 'disabled style="opacity:0.75; cursor:default;"' : ''} onclick="openSubscriptionModal('${planCode}')">
                    ${buttonText}
                </button>
            </div>
        `;"""

new_pricing_card_markup = """        html += `
            <div class="pricing-card ${isFeatured ? 'featured' : ''}" id="card-plan-${planCode}" style="${isCurrentActive ? 'border: 2px solid var(--primary-brand);' : ''}">
                ${isFeatured ? `<div class="featured-badge">${plan.badge || 'MOST POPULAR'}</div>` : (plan.badge ? `<div style="font-size:11px; font-weight:700; color:var(--primary-brand); text-transform:uppercase; letter-spacing:0.8px; margin-bottom:6px;">${escapeHtml(plan.badge)}</div>` : '')}
                <div class="plan-header">
                    <h3 class="plan-name">${escapeHtml(plan.name)}</h3>
                    <p class="plan-desc">${escapeHtml(plan.description || '')}</p>
                </div>
                <div class="plan-price">
                    <span class="currency">₹</span>
                    <span class="amount">${displayPrice.toLocaleString('en-IN')}</span>
                    <span class="period">${periodText}</span>
                </div>
                ${subPriceText ? `<div style="font-size:12px; color:var(--primary-brand); margin:-8px 0 16px 0; font-weight:700;">${subPriceText}</div>` : ''}
                <ul class="plan-features">
                    ${featuresHtml}
                </ul>
                <button class="${buttonClass}" style="width:100%;" ${buttonDisabled ? 'disabled style="opacity:0.75; cursor:default;"' : ''} onclick="openSubscriptionModal('${planCode}')">
                    ${buttonText}
                </button>
            </div>
        `;"""

if old_pricing_card_markup in js:
    js = js.replace(old_pricing_card_markup, new_pricing_card_markup)
    print("Replaced pricing card markup in renderPricingGrid.")
else:
    print("WARNING: old_pricing_card_markup not found.")

# Update renderUserQuotaWidget
old_quota_widget_start = """            <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:18px 22px; margin-bottom:28px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:10px;">
                    <div>
                        <span style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--text-muted); letter-spacing:0.5px;">Account Quotas</span>
                        <h4 style="margin:2px 0 0; font-size:15px; color:var(--text-primary); font-weight:700;">
                            Active Tier: <span style="color:var(--accent-cyan);">${escapeHtml(q.plan_name)}</span>
                        </h4>
                    </div>"""

new_quota_widget_start = """            <div style="background:#FFFFFF; border:1.5px solid var(--border-color); border-radius:20px; padding:22px 28px; margin-bottom:32px; box-shadow:var(--shadow-card);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
                    <div>
                        <span style="font-size:11.5px; font-weight:700; text-transform:uppercase; color:var(--text-muted); letter-spacing:1px;">Account Quotas</span>
                        <h4 style="margin:3px 0 0; font-size:16px; color:var(--text-primary); font-weight:800;">
                            Active Tier: <span style="color:var(--primary-brand);">${escapeHtml(q.plan_name)}</span>
                        </h4>
                    </div>"""

if old_quota_widget_start in js:
    js = js.replace(old_quota_widget_start, new_quota_widget_start)
    print("Replaced user quota widget start in app.js.")
else:
    print("WARNING: old_quota_widget_start not found.")

# Update progress bar background and fill in renderUserQuotaWidget
old_bar_fill = 'background:var(--accent-cyan);'
new_bar_fill = 'background:var(--brand-gradient);'

# Replace progress bar tracks in renderUserQuotaWidget
old_bar_track = 'background:rgba(255,255,255,0.08);'
new_bar_track = 'background:#F1F3F7;'

if old_bar_track in js:
    js = js.replace(old_bar_track, new_bar_track)
    print("Replaced bar tracks in quota widget.")

# Update renderPlanComparisonTable styling
old_comp_start = """            <div style="margin-top:54px; border-top:1px solid var(--border-color); padding-top:40px;">
                <div style="text-align:center; margin-bottom:32px;">
                    <span style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--accent-cyan); letter-spacing:1px;">Complete Capability Matrix</span>
                    <h3 style="font-size:22px; font-weight:800; color:var(--text-primary); margin:6px 0 10px;">Compare Plan Features</h3>
                    <p style="font-size:13.5px; color:var(--text-secondary); max-width:640px; margin:0 auto;">
                        Every feature and quota is dynamically synchronized with our authoritative subscription engine.
                    </p>
                </div>

                <div style="overflow-x:auto; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:var(--radius-lg); box-shadow:var(--shadow-sm);">
                    <table style="width:100%; border-collapse:collapse; text-align:left; font-size:13px;">
                        <thead>
                            <tr style="background:var(--bg-surface-subtle); border-bottom:2px solid var(--border-color);">
                                <th style="padding:18px 22px; font-weight:700; color:var(--text-primary); width:35%;">Feature &amp; Quota</th>
                                ${plans.map(p => `
                                    <th style="padding:18px 16px; text-align:center; width:21%; ${p.is_recommended ? 'background:rgba(15,118,110,0.08);' : ''}">
                                        <div style="font-size:15px; font-weight:800; color:var(--text-primary);">${escapeHtml(p.name)}</div>
                                        ${p.badge ? `<span style="display:inline-block; font-size:10px; font-weight:700; padding:2px 8px; border-radius:10px; background:rgba(6,182,212,0.15); color:var(--accent-cyan); margin-top:4px;">${escapeHtml(p.badge)}</span>` : ''}
                                    </th>
                                `).join('')}
                            </tr>
                        </thead>"""

new_comp_start = """            <div style="margin-top:64px; border-top:1px solid var(--border-color); padding-top:48px;">
                <div style="text-align:center; margin-bottom:36px;">
                    <span class="daanveda-pill-eyebrow">Complete Capability Matrix</span>
                    <h3 style="font-size:28px; font-weight:800; color:var(--text-primary); letter-spacing:-0.7px; margin:8px 0 12px;">Compare Plan Features</h3>
                    <p style="font-size:15px; color:var(--text-secondary); max-width:640px; margin:0 auto; line-height:1.5;">
                        Every feature and quota is dynamically synchronized with our authoritative subscription engine.
                    </p>
                </div>

                <div style="overflow-x:auto; background:#FFFFFF; border:1px solid var(--border-color); border-radius:24px; box-shadow:var(--shadow-card);">
                    <table style="width:100%; border-collapse:collapse; text-align:left; font-size:13.5px;">
                        <thead>
                            <tr style="background:#FAFBFF; border-bottom:2px solid var(--border-color);">
                                <th style="padding:22px 24px; font-weight:700; color:var(--text-primary); width:35%;">Feature &amp; Quota</th>
                                ${plans.map(p => `
                                    <th style="padding:22px 18px; text-align:center; width:21%; ${p.is_recommended ? 'background:rgba(10,108,255,0.035);' : ''}">
                                        <div style="font-size:17px; font-weight:800; color:var(--text-primary); letter-spacing:-0.3px;">${escapeHtml(p.name)}</div>
                                        ${p.badge ? `<span style="display:inline-block; font-size:11px; font-weight:700; padding:3px 10px; border-radius:999px; background:rgba(10,108,255,0.08); color:var(--primary-brand); margin-top:4px;">${escapeHtml(p.badge)}</span>` : ''}
                                    </th>
                                `).join('')}
                            </tr>
                        </thead>"""

if old_comp_start in js:
    js = js.replace(old_comp_start, new_comp_start)
    print("Replaced comparison table start in app.js.")
else:
    print("WARNING: old_comp_start not found.")

# Update boolean checkmark inside renderPlanComparisonTable
old_bool_check = """                                                if (val.type === 'boolean') {
                                                    cellContent = val.value
                                                        ? '<span style="color:#10b981; font-weight:800; font-size:16px;">✓</span>'
                                                        : '<span style="color:var(--text-muted); opacity:0.4;">—</span>';
                                                } else if (val.type === 'unlimited') {
                                                    cellContent = '<span style="color:var(--accent-cyan); font-weight:700;">Unlimited</span>';"""

new_bool_check = """                                                if (val.type === 'boolean') {
                                                    cellContent = val.value
                                                        ? '<span class="daanveda-check-badge sm"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></span>'
                                                        : '<span style="color:var(--text-muted); opacity:0.35; font-size:16px;">—</span>';
                                                } else if (val.type === 'unlimited') {
                                                    cellContent = '<span style="color:var(--primary-brand); font-weight:700; font-size:13.5px;">Unlimited</span>';"""

if old_bool_check in js:
    js = js.replace(old_bool_check, new_bool_check)
    print("Replaced boolean checkmark in app.js.")
else:
    print("WARNING: old_bool_check not found.")

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(js)
print("Saved static/js/app.js successfully.")

