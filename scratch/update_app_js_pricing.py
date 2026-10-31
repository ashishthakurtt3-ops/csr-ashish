with open('static/js/app.js', 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Update normalizeSubscriptionTier to support free, pro, ultra
old_norm = """function normalizeSubscriptionTier(tier) {
    if (!tier) return 'starter';
    const t = String(tier).toLowerCase().trim();
    if (t === 'enterprise') return 'enterprise';
    if (t === 'foundation') return 'foundation';
    if (t === 'pro') return 'pro';
    return 'starter';
}"""

new_norm = """function normalizeSubscriptionTier(tier) {
    if (!tier) return 'free';
    const t = String(tier).toLowerCase().trim();
    if (t === 'free' || t === 'starter' || t === 'community_free') return 'free';
    if (t === 'pro') return 'pro';
    if (t === 'ultra' || t === 'enterprise' || t === 'foundation' || t === 'api') return 'ultra';
    return 'free';
}"""

for le in ['\r\n', '\n']:
    tgt = old_norm.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_norm.replace('\n', le))
        print("Updated normalizeSubscriptionTier in app.js")
        break
else:
    print("WARNING: Could not update normalizeSubscriptionTier in app.js")

# 2. Update button logic in renderPricingGrid
old_button_logic = """        if (isCurrentActive) {
            buttonText = 'CURRENT PLAN';
            buttonDisabled = true;
            buttonClass = 'btn-secondary';
        } else if (plan.is_contact_sales) {
            buttonText = 'Contact Sales Team ↗';
        } else {
            const currentPlanObj = dbPlansCatalog.find(p => p.code.toLowerCase() === currentNormTier);
            const currentOrder = currentPlanObj ? currentPlanObj.display_order : 10;
            if (plan.display_order < currentOrder) {
                buttonText = `Switch to ${plan.name}`;
            } else {
                buttonText = `Change to ${plan.name}`;
            }
        }"""

new_button_logic = """        if (isCurrentActive) {
            buttonText = 'CURRENT PLAN';
            buttonDisabled = true;
            buttonClass = 'btn-secondary';
        } else if (plan.is_contact_sales) {
            buttonText = 'Contact Sales Team ↗';
        } else {
            const currentPlanObj = dbPlansCatalog.find(p => p.code.toLowerCase() === currentNormTier);
            const currentOrder = currentPlanObj ? currentPlanObj.display_order : 1;
            if (plan.display_order < currentOrder) {
                // Rule 7: Customers must not see downgrade options.
                buttonText = 'Included with your plan';
                buttonDisabled = true;
                buttonClass = 'btn-secondary';
            } else {
                buttonText = `Upgrade to ${plan.name}`;
                buttonClass = plan.code === 'pro' ? 'btn-primary' : 'btn-primary';
            }
        }"""

for le in ['\r\n', '\n']:
    tgt = old_button_logic.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_button_logic.replace('\n', le))
        print("Updated button logic in renderPricingGrid")
        break
else:
    print("WARNING: Could not update button logic in renderPricingGrid")

# 3. Add call to renderPlanComparisonTable and renderUserQuotaWidget inside renderPricingGrid
old_end_grid = """    grid.innerHTML = html;
}"""

new_end_grid = """    grid.innerHTML = html;
    renderUserQuotaWidget();
    renderPlanComparisonTable();
}"""

for le in ['\r\n', '\n']:
    tgt = old_end_grid.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_end_grid.replace('\n', le))
        print("Hooked comparison table and quota widget into renderPricingGrid")
        break
else:
    print("WARNING: Could not hook comparison table into renderPricingGrid")

# 4. Add the implementation of renderPlanComparisonTable and renderUserQuotaWidget
functions_to_add = """

// ── THREE-TIER USER QUOTA & USAGE WIDGET ─────────────────────────────────────
async function renderUserQuotaWidget() {
    const container = document.getElementById('user-quota-widget');
    if (!container) return;

    try {
        const res = await fetch(`${API_BASE}/api/user/quotas`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data || !data.quota) return;
        const q = data.quota;

        const srUsed = q.saved_records.used || 0;
        const srLimit = q.saved_records.unlimited ? 'Unlimited' : (q.saved_records.limit || 10);
        const srPct = q.saved_records.unlimited ? 15 : Math.min(100, Math.round((srUsed / (q.saved_records.limit || 1)) * 100));

        const ssUsed = q.saved_searches.used || 0;
        const ssLimit = q.saved_searches.limit || 1;
        const ssPct = Math.min(100, Math.round((ssUsed / ssLimit) * 100));

        const exUsed = q.monthly_exports.used || 0;
        const exLimit = q.monthly_exports.limit || 0;
        const exPct = exLimit > 0 ? Math.min(100, Math.round((exUsed / exLimit) * 100)) : 0;

        container.innerHTML = `
            <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:18px 22px; margin-bottom:28px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:10px;">
                    <div>
                        <span style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--text-muted); letter-spacing:0.5px;">Account Quotas</span>
                        <h4 style="margin:2px 0 0; font-size:15px; color:var(--text-primary); font-weight:700;">
                            Active Tier: <span style="color:var(--accent-cyan);">${escapeHtml(q.plan_name)}</span>
                        </h4>
                    </div>
                    <div style="font-size:12px; color:var(--text-secondary);">
                        Period: <strong>${q.monthly_exports.period || ''}</strong>
                    </div>
                </div>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:18px;">
                    <div>
                        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:5px;">
                            <span style="color:var(--text-secondary);">Saved Jobs &amp; CSR:</span>
                            <strong style="color:var(--text-primary);">${srUsed} / ${srLimit}</strong>
                        </div>
                        <div style="height:6px; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden;">
                            <div style="width:${srPct}%; height:100%; background:var(--accent-cyan); border-radius:3px;"></div>
                        </div>
                    </div>
                    <div>
                        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:5px;">
                            <span style="color:var(--text-secondary);">Saved Searches:</span>
                            <strong style="color:var(--text-primary);">${ssUsed} / ${ssLimit}</strong>
                        </div>
                        <div style="height:6px; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden;">
                            <div style="width:${ssPct}%; height:100%; background:#818cf8; border-radius:3px;"></div>
                        </div>
                    </div>
                    <div>
                        <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:5px;">
                            <span style="color:var(--text-secondary);">Monthly Exports:</span>
                            <strong style="color:var(--text-primary);">${exUsed} / ${exLimit > 0 ? exLimit : '0 (Upgrade)'}</strong>
                        </div>
                        <div style="height:6px; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden;">
                            <div style="width:${exPct}%; height:100%; background:#10b981; border-radius:3px;"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    } catch (e) {
        console.warn('Could not load user quota widget:', e);
    }
}

// ── DYNAMIC THREE-TIER PLAN COMPARISON TABLE ──────────────────────────────────
async function renderPlanComparisonTable() {
    const container = document.getElementById('pricing-comparison-container');
    if (!container) return;

    try {
        const res = await fetch(`${API_BASE}/api/subscription/comparison`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data || !data.plans || !data.features) return;

        const plans = data.plans;
        const features = data.features;
        const currentNormTier = normalizeSubscriptionTier(currentSubscription.plan_id || currentSubscription.tier);

        let tableHtml = `
            <div style="margin-top:54px; border-top:1px solid var(--border-color); padding-top:40px;">
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
                        </thead>
                        <tbody>
                            ${features.map((f, idx) => {
                                const isEven = idx % 2 === 0;
                                return `
                                    <tr style="border-bottom:1px solid var(--border-color); background:${isEven ? 'transparent' : 'rgba(255,255,255,0.015)'};">
                                        <td style="padding:14px 22px; font-weight:600; color:var(--text-primary);">
                                            ${escapeHtml(f.display_name || f.feature_key)}
                                        </td>
                                        ${plans.map(p => {
                                            const val = f.values[p.code];
                                            let cellContent = '—';
                                            if (val) {
                                                if (val.type === 'boolean') {
                                                    cellContent = val.value
                                                        ? '<span style="color:#10b981; font-weight:800; font-size:16px;">✓</span>'
                                                        : '<span style="color:var(--text-muted); opacity:0.4;">—</span>';
                                                } else if (val.type === 'unlimited') {
                                                    cellContent = '<span style="color:var(--accent-cyan); font-weight:700;">Unlimited</span>';
                                                } else {
                                                    cellContent = `<span style="color:var(--text-primary); font-weight:600;">${escapeHtml(val.display)}</span>`;
                                                }
                                            }
                                            return `
                                                <td style="padding:14px 16px; text-align:center; ${p.is_recommended ? 'background:rgba(15,118,110,0.04);' : ''}">
                                                    ${cellContent}
                                                </td>
                                            `;
                                        }).join('')}
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                        <tfoot>
                            <tr style="background:var(--bg-surface-subtle); border-top:2px solid var(--border-color);">
                                <td style="padding:18px 22px; font-weight:700; color:var(--text-secondary);">Select Plan</td>
                                ${plans.map(p => {
                                    const isCurrent = currentNormTier === p.code.toLowerCase();
                                    const currentPlanObj = plans.find(x => x.code.toLowerCase() === currentNormTier);
                                    const currentOrder = currentPlanObj ? (currentPlanObj.display_order || (currentNormTier==='free'?1:(currentNormTier==='pro'?2:3))) : 1;
                                    const pOrder = p.code.toLowerCase() === 'free' ? 1 : (p.code.toLowerCase() === 'pro' ? 2 : 3);

                                    let btnLabel = `Upgrade to ${p.name}`;
                                    let btnDis = false;
                                    let btnCls = p.is_recommended ? 'btn-primary' : 'btn-secondary';

                                    if (isCurrent) {
                                        btnLabel = 'Current Plan';
                                        btnDis = true;
                                        btnCls = 'btn-secondary';
                                    } else if (pOrder < currentOrder) {
                                        btnLabel = 'Included';
                                        btnDis = true;
                                        btnCls = 'btn-secondary';
                                    }

                                    return `
                                        <td style="padding:16px; text-align:center; ${p.is_recommended ? 'background:rgba(15,118,110,0.08);' : ''}">
                                            <button class="${btnCls}" style="padding:8px 16px; font-size:12px; width:90%;" ${btnDis ? 'disabled style="opacity:0.6; cursor:default;"' : ''} onclick="openSubscriptionModal('${p.code.toLowerCase()}')">
                                                ${btnLabel}
                                            </button>
                                        </td>
                                    `;
                                }).join('')}
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>
        `;

        container.innerHTML = tableHtml;
    } catch (e) {
        console.warn('Could not render dynamic comparison table:', e);
    }
}
"""

if 'function renderPlanComparisonTable()' not in c:
    c += functions_to_add
    print("Appended renderPlanComparisonTable and renderUserQuotaWidget to app.js")

with open('static/js/app.js', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done updating app.js")

