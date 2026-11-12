path = 'templates/website/index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Top banner
target1 = """    {% if plan_required %}
    <!-- ===== PLAN SELECTION REQUIRED BANNER (LOGGED IN USER WITHOUT PLAN) ===== -->
    <div id="plan-selection-required-banner" style="background: linear-gradient(90deg, #1E1B4B 0%, #312E81 100%); border-bottom: 2px solid #6366F1; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; z-index: 860; position: relative; box-shadow: 0 4px 14px rgba(99,102,241,0.25);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: rgba(99, 102, 241, 0.35); color: #C7D2FE; font-size: 14px; font-weight: 800; border: 1px solid rgba(99, 102, 241, 0.6);">⚡</span>
            <span style="color: #F8FAFC; font-size: 13.5px; font-weight: 500;">
                <strong>Subscription Plan Required:</strong> You are signed in as <strong>{{ user.username }}</strong>, but haven't selected an active subscription plan yet. Please select a plan to unlock all verified corporate profiles, Section 135 CSR projects, and active job openings.
            </span>
        </div>
        <button onclick="switchTab('pricing')" class="btn-primary" style="padding: 7px 18px; font-size: 12.5px; font-weight: 700; background: #6366F1; border: none; border-radius: 8px; color: white; cursor: pointer; display: flex; align-items: center; gap: 6px;">
            <span>Select a Plan to Unlock</span> &rarr;
        </button>
    </div>
    {% elif is_preview_mode and preview_settings.banner_enabled and preview_settings.preview_enabled %}"""

replacement1 = """    {% if plan_required %}
    <!-- ===== PLAN SELECTION REQUIRED / TRIAL EXPIRED BANNER ===== -->
    <div id="plan-selection-required-banner" style="background: {% if sub_status == 'EXPIRED' %}linear-gradient(90deg, #450A0A 0%, #7F1D1D 100%){% else %}linear-gradient(90deg, #1E1B4B 0%, #312E81 100%){% endif %}; border-bottom: 2px solid {% if sub_status == 'EXPIRED' %}#EF4444{% else %}#6366F1{% endif %}; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; z-index: 860; position: relative; box-shadow: 0 4px 14px rgba(0,0,0,0.25);">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: {% if sub_status == 'EXPIRED' %}rgba(239, 68, 68, 0.35){% else %}rgba(99, 102, 241, 0.35){% endif %}; color: {% if sub_status == 'EXPIRED' %}#FCA5A5{% else %}#C7D2FE{% endif %}; font-size: 14px; font-weight: 800; border: 1px solid {% if sub_status == 'EXPIRED' %}rgba(239, 68, 68, 0.6){% else %}rgba(99, 102, 241, 0.6){% endif %};">{% if sub_status == 'EXPIRED' %}⚠️{% else %}⚡{% endif %}</span>
            <span style="color: #F8FAFC; font-size: 13.5px; font-weight: 500;">
                {% if sub_status == 'EXPIRED' %}
                <strong>14-Day Free Trial Expired:</strong> Your evaluation access has ended. Full company profiles, Section 135 CSR projects, and active job links are currently locked. Please select a subscription plan to unlock full access.
                {% else %}
                <strong>Subscription Plan Required:</strong> You are signed in as <strong>{{ user.username }}</strong>, but haven't selected an active subscription plan yet. Please select a plan to unlock all verified corporate profiles, Section 135 CSR projects, and active job openings.
                {% endif %}
            </span>
        </div>
        <button onclick="switchTab('pricing')" class="btn-primary" style="padding: 7px 18px; font-size: 12.5px; font-weight: 700; background: {% if sub_status == 'EXPIRED' %}#EF4444{% else %}#6366F1{% endif %}; border: none; border-radius: 8px; color: white; cursor: pointer; display: flex; align-items: center; gap: 6px;">
            <span>Select a Plan to Unlock</span> &rarr;
        </button>
    </div>
    {% elif is_sub_active and sub_status == 'TRIALING' %}
    <!-- ===== 14-DAY FREE TRIAL ACTIVE BANNER ===== -->
    <div id="free-trial-active-banner" style="background: linear-gradient(90deg, #064E3B 0%, #065F46 100%); border-bottom: 2px solid #10B981; padding: 10px 24px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; z-index: 860; position: relative;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <span style="display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 50%; background: rgba(16, 185, 129, 0.35); color: #A7F3D0; font-size: 13px; font-weight: 800; border: 1px solid rgba(16, 185, 129, 0.6);">⏳</span>
            <span style="color: #F8FAFC; font-size: 13px; font-weight: 500;">
                <strong>14-Day Free Trial Active:</strong> You have <strong>{{ trial_days_remaining|default:14 }} day{{ trial_days_remaining|default:14|pluralize }} remaining</strong> in your trial. All verified companies, live openings, and Section 135 filings are accessible.
            </span>
        </div>
        <button onclick="switchTab('pricing')" class="btn-primary" style="padding: 6px 16px; font-size: 12px; font-weight: 700; background: #10B981; border: none; border-radius: 8px; color: white; cursor: pointer; display: flex; align-items: center; gap: 6px;">
            <span>Upgrade to Pro</span> &rarr;
        </button>
    </div>
    {% elif is_preview_mode and preview_settings.banner_enabled and preview_settings.preview_enabled %}"""

assert target1 in content, 'target1 not found in index.html'
content = content.replace(target1, replacement1, 1)

# 2. Active Subscription Card
target2 = """            <!-- Active User Subscription Status Banner -->
            <div class="active-subscription-card" id="active-subscription-card" style="background:var(--bg-card); border:1.5px solid var(--border-color); border-radius:20px; padding:22px 28px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom:28px; box-shadow:var(--shadow-card);">
                <div class="active-sub-left">
                    <div style="font-size:11px; font-weight:800; color:var(--accent-cyan); letter-spacing:0.04em;">TIER STATUS: <strong id="active-plan-badge-name">{% if is_sub_active %}{{ plan_tier }} (ACTIVE){% elif sub_status == 'EXPIRED' %}{{ plan_tier }} (EXPIRED){% elif sub_status == 'CANCELED' %}{{ plan_tier }} (CANCELLED){% else %}NO ACTIVE PLAN{% endif %}</strong></div>
                    <div style="font-size:16px; font-weight:800; color:var(--text-primary); margin:4px 0;" id="active-plan-org-title">{% if is_sub_active %}{{ user_subscription.organization_name|default:'Institutional Non-Profit Access' }} &bull; {{ plan_tier }} Active{% elif sub_status == 'EXPIRED' %}{{ user_subscription.organization_name|default:'Account' }} &bull; Subscription Expired{% elif sub_status == 'CANCELED' %}{{ user_subscription.organization_name|default:'Account' }} &bull; Subscription Cancelled{% else %}No Subscription Active{% endif %}</div>
                    <div style="font-size:12.5px; color:var(--text-secondary);" id="active-plan-features-summary">
                        ✓ Canonical Listed Corporations &bull; ✓ Live Verified Job Listings &bull; ✓ Real-Time HTTP Verification Audits
                    </div>
                </div>
                <div class="active-sub-right" style="display:flex; gap:10px;">
                    <button class="btn-primary" onclick="openSubscriptionModal('pro')" id="active-plan-upgrade-cta">
                        {% if is_sub_active %}Upgrade Plan ⚡{% elif sub_status == 'EXPIRED' %}Renew Plan ⚡{% else %}Select Plan ⚡{% endif %}
                    </button>
                    <button class="btn-secondary" onclick="openSubscriptionModal()" id="active-plan-manage-btn">
                        Manage Plan
                    </button>
                </div>
            </div>"""

replacement2 = """            <!-- Active User Subscription Status Banner -->
            <div class="active-subscription-card" id="active-subscription-card" style="background:var(--bg-card); border:1.5px solid var(--border-color); border-radius:20px; padding:22px 28px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom:28px; box-shadow:var(--shadow-card);">
                <div class="active-sub-left">
                    <div style="font-size:11px; font-weight:800; color:var(--accent-cyan); letter-spacing:0.04em;">TIER STATUS: <strong id="active-plan-badge-name">{% if is_sub_active and sub_status == 'TRIALING' %}14-DAY FREE TRIAL (ACTIVE){% elif is_sub_active %}{{ plan_tier }} (ACTIVE){% elif sub_status == 'EXPIRED' %}{{ plan_tier }} (EXPIRED){% elif sub_status == 'CANCELED' %}{{ plan_tier }} (CANCELLED){% else %}NO ACTIVE PLAN{% endif %}</strong></div>
                    <div style="font-size:16px; font-weight:800; color:var(--text-primary); margin:4px 0;" id="active-plan-org-title">{% if is_sub_active and sub_status == 'TRIALING' %}{{ user_subscription.organization_name|default:'Account' }} &bull; 14-Day Free Trial ({{ trial_days_remaining|default:14 }} days remaining){% elif is_sub_active %}{{ user_subscription.organization_name|default:'Institutional Non-Profit Access' }} &bull; {{ plan_tier }} Active{% elif sub_status == 'EXPIRED' %}{{ user_subscription.organization_name|default:'Account' }} &bull; 14-Day Free Trial Expired{% elif sub_status == 'CANCELED' %}{{ user_subscription.organization_name|default:'Account' }} &bull; Subscription Cancelled{% else %}No Subscription Active{% endif %}</div>
                    <div style="font-size:12.5px; color:var(--text-secondary);" id="active-plan-features-summary">
                        {% if is_sub_active and sub_status == 'TRIALING' %}
                        ✓ Full access to company dossiers, live jobs &amp; CSR initiatives during your 14-day evaluation period.
                        {% elif sub_status == 'EXPIRED' %}
                        ⚠️ Free trial period ended. Full company dossiers, contact details, and application URLs are locked. Select a plan to unlock.
                        {% else %}
                        ✓ Canonical Listed Corporations &bull; ✓ Live Verified Job Listings &bull; ✓ Real-Time HTTP Verification Audits
                        {% endif %}
                    </div>
                </div>
                <div class="active-sub-right" style="display:flex; gap:10px;">
                    <button class="btn-primary" onclick="openSubscriptionModal('pro')" id="active-plan-upgrade-cta">
                        {% if is_sub_active and sub_status == 'TRIALING' %}Upgrade to Pro ⚡{% elif is_sub_active %}Upgrade Plan ⚡{% elif sub_status == 'EXPIRED' %}⚡ Select a Plan to Unlock{% else %}Select Plan ⚡{% endif %}
                    </button>
                    <button class="btn-secondary" onclick="openSubscriptionModal()" id="active-plan-manage-btn">
                        Manage Plan
                    </button>
                </div>
            </div>"""

assert target2 in content, 'target2 not found in index.html'
content = content.replace(target2, replacement2, 1)

# 3. Free Plan Modal
target3 = """                <h3 style="font-size:21px; font-weight:800; color:#0F172A; margin:0 0 6px 0;">Activate Free Forever Plan</h3>
                <div style="font-size:13.5px; color:#64748B;">No credit card required &bull; ₹0.00 / month &bull; Immediate activation</div>
            </div>

            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:14px; padding:16px; margin-bottom:20px; font-size:13px;">
                <div style="font-weight:700; color:#0F172A; margin-bottom:10px; font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">Included Capabilities:</div>
                <ul style="margin:0; padding-left:18px; color:#334155; display:flex; flex-direction:column; gap:6px; line-height:1.45;">
                    <li><strong>200 Verified Corporations</strong> &amp; MCA statutory profiles</li>
                    <li><strong>Live Job Openings &amp; CSR Projects</strong> with direct ATS/portal links</li>
                    <li><strong>Save up to 10</strong> combined jobs &amp; CSR project bookmarks</li>
                    <li><strong>1 Custom Saved Search</strong> query with weekly email updates</li>
                    <li><strong>Single User Account</strong> with prototype wallet</li>
                </ul>
            </div>

            <div style="display:flex; justify-content:space-between; gap:12px;">
                <button type="button" class="btn-secondary" style="flex:1; padding:11px;" onclick="closeFreePlanModal()">Cancel</button>
                <button type="button" class="btn-primary" id="btn-confirm-free-plan" style="flex:2; padding:11px; background:linear-gradient(135deg, #10B981, #059669); border:none; box-shadow:0 4px 14px rgba(16,185,129,0.35); font-weight:700;" onclick="executeFreePlanActivation()">
                    Confirm &amp; Activate Free Plan
                </button>"""

replacement3 = """                <h3 style="font-size:21px; font-weight:800; color:#0F172A; margin:0 0 6px 0;">Activate 14-Day Free Trial</h3>
                <div style="font-size:13.5px; color:#64748B;">No credit card required &bull; 14 Days Full Evaluation &bull; Immediate activation</div>
            </div>

            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:14px; padding:16px; margin-bottom:20px; font-size:13px;">
                <div style="font-weight:700; color:#0F172A; margin-bottom:10px; font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">Included In Your 14-Day Free Trial:</div>
                <ul style="margin:0; padding-left:18px; color:#334155; display:flex; flex-direction:column; gap:6px; line-height:1.45;">
                    <li><strong>14 Days Full Access</strong> to explore all verified companies &amp; dossiers</li>
                    <li><strong>Live Job Openings &amp; CSR Projects</strong> with direct ATS &amp; portal links</li>
                    <li><strong>Save up to 10</strong> combined jobs &amp; CSR project bookmarks</li>
                    <li><strong>1 Custom Saved Search</strong> query with weekly email updates</li>
                    <li><strong>Single User Account</strong> with demo wallet</li>
                </ul>
                <div style="margin-top:12px; padding-top:10px; border-top:1px dashed #CBD5E1; color:#D97706; font-size:12px; font-weight:600;">
                    ⚠️ Access to company details and application links expires automatically after 14 days unless upgraded.
                </div>
            </div>

            <div style="display:flex; justify-content:space-between; gap:12px;">
                <button type="button" class="btn-secondary" style="flex:1; padding:11px;" onclick="closeFreePlanModal()">Cancel</button>
                <button type="button" class="btn-primary" id="btn-confirm-free-plan" style="flex:2; padding:11px; background:linear-gradient(135deg, #10B981, #059669); border:none; box-shadow:0 4px 14px rgba(16,185,129,0.35); font-weight:700;" onclick="executeFreePlanActivation()">
                    Start 14-Day Free Trial
                </button>"""

assert target3 in content, 'target3 not found in index.html'
content = content.replace(target3, replacement3, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated index.html")

