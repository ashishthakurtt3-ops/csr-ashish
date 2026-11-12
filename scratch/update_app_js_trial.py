path = 'static/js/app.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Card button logic
target1 = """        } else if (!hasActiveSub) {
            buttonText = plan.is_free ? 'Select Free Plan' : `Select ${plan.name}`;
            buttonClass = 'btn-primary';
            buttonDisabled = false;
        }"""

replacement1 = """        } else if (plan.is_free && (currentSubscription.status === 'EXPIRED' || (currentSubscription.plan_id === 'free' && !hasActiveSub))) {
            buttonText = 'Trial Expired';
            buttonDisabled = true;
            buttonClass = 'btn-secondary';
        } else if (!hasActiveSub) {
            buttonText = plan.is_free ? 'Start 14-Day Free Trial' : `Select ${plan.name}`;
            buttonClass = 'btn-primary';
            buttonDisabled = false;
        }"""

assert target1 in content, 'target1 not found in app.js'
content = content.replace(target1, replacement1, 1)

# 2. Header label & active subscription card in applySubscriptionToUI
target2 = """            if (normTier === 'foundation') headerLabel.textContent = '👑 Foundation Master';
            else if (normTier === 'enterprise') headerLabel.textContent = '🚀 Corporate Enterprise';
            else if (normTier === 'pro') headerLabel.textContent = '⚡ Impact Pro';
            else headerLabel.textContent = 'Community Free (Active)';"""

replacement2 = """            if (normTier === 'foundation') headerLabel.textContent = '👑 Foundation Master';
            else if (normTier === 'enterprise') headerLabel.textContent = '🚀 Corporate Enterprise';
            else if (normTier === 'pro') headerLabel.textContent = '⚡ Impact Pro';
            else if (subStatus === 'TRIALING') headerLabel.textContent = '⏳ 14-Day Free Trial';
            else headerLabel.textContent = '14-Day Free Trial (Active)';"""

assert target2 in content, 'target2 not found in app.js'
content = content.replace(target2, replacement2, 1)

# 3. Badge name and org title
target3 = """    if (badgeName) {
        if (!isActive) {
            if (subStatus === 'EXPIRED') {
                badgeName.textContent = `${planName.toUpperCase()} (EXPIRED)`;
                badgeName.style.color = '#ef4444';
            } else if (subStatus === 'CANCELED' || subStatus === 'CANCELLED') {
                badgeName.textContent = `${planName.toUpperCase()} (CANCELLED)`;
                badgeName.style.color = '#f97316';
            } else {
                badgeName.textContent = 'NO ACTIVE PLAN';
                badgeName.style.color = 'var(--text-secondary)';
            }
        } else {
            badgeName.textContent = `${planName.toUpperCase()} (ACTIVE)`;
            badgeName.style.color = 'var(--accent-cyan)';
        }
    }
    if (orgTitle) {
        if (!isActive) {
            if (subStatus === 'EXPIRED') {
                orgTitle.textContent = `${currentSubscription.organization_name || 'Account'} • Subscription Expired`;
            } else if (subStatus === 'CANCELED' || subStatus === 'CANCELLED') {
                orgTitle.textContent = `${currentSubscription.organization_name || 'Account'} • Subscription Cancelled`;
            } else {
                orgTitle.textContent = `${currentSubscription.organization_name || 'Account'} • No Subscription Active`;
            }
        } else {
            orgTitle.textContent = `${currentSubscription.organization_name || 'Institutional Non-Profit Access'} • ${planName} Active`;
        }
    }"""

replacement3 = """    if (badgeName) {
        if (!isActive) {
            if (subStatus === 'EXPIRED') {
                badgeName.textContent = `${normTier === 'starter' || normTier === 'free' ? '14-DAY FREE TRIAL' : planName.toUpperCase()} (EXPIRED)`;
                badgeName.style.color = '#ef4444';
            } else if (subStatus === 'CANCELED' || subStatus === 'CANCELLED') {
                badgeName.textContent = `${planName.toUpperCase()} (CANCELLED)`;
                badgeName.style.color = '#f97316';
            } else {
                badgeName.textContent = 'NO ACTIVE PLAN';
                badgeName.style.color = 'var(--text-secondary)';
            }
        } else if (subStatus === 'TRIALING') {
            badgeName.textContent = '14-DAY FREE TRIAL (ACTIVE)';
            badgeName.style.color = '#10B981';
        } else {
            badgeName.textContent = `${planName.toUpperCase()} (ACTIVE)`;
            badgeName.style.color = 'var(--accent-cyan)';
        }
    }
    if (orgTitle) {
        if (!isActive) {
            if (subStatus === 'EXPIRED') {
                orgTitle.textContent = `${currentSubscription.organization_name || 'Account'} • 14-Day Free Trial Expired`;
            } else if (subStatus === 'CANCELED' || subStatus === 'CANCELLED') {
                orgTitle.textContent = `${currentSubscription.organization_name || 'Account'} • Subscription Cancelled`;
            } else {
                orgTitle.textContent = `${currentSubscription.organization_name || 'Account'} • No Subscription Active`;
            }
        } else if (subStatus === 'TRIALING') {
            orgTitle.textContent = `${currentSubscription.organization_name || 'Account'} • 14-Day Free Trial Active`;
        } else {
            orgTitle.textContent = `${currentSubscription.organization_name || 'Institutional Non-Profit Access'} • ${planName} Active`;
        }
    }"""

assert target3 in content, 'target3 not found in app.js'
content = content.replace(target3, replacement3, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated app.js")

