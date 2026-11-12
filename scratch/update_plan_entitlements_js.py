path = 'static/js/plan_entitlements.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

target = """        const btn = document.getElementById('btn-confirm-free-plan');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<span class="ent-spinner"></span> Activating Free Plan...`;
        }

        try {
            const res = await fetch(`${API_BASE}/api/subscription/change-plan`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({
                    plan_id: 'free',
                    billing_cycle: 'monthly',
                    payment_method: 'WALLET',
                }),
            });

            const data = await res.json();
            if (!res.ok || (data.status !== 'success' && !data.success)) {
                throw new Error(data.message || data.detail || 'Free plan activation failed.');
            }

            closeFreePlanModal();

            if (typeof loadSubscriptionState === 'function') {
                await loadSubscriptionState();
            }

            if (typeof showLiveToast === 'function') {
                showLiveToast('Free Forever plan successfully activated! You now have active access.', 'success');
            }

            // Reload entitlements state
            await loadAllEntitlementsData();

        } catch (err) {
            console.error('Free plan activation error:', err);
            if (typeof showLiveToast === 'function') {
                showLiveToast(`❌ ${err.message}`, 'error');
            } else if (typeof window.showInAppNotification === 'function') {
                window.showInAppNotification({ title: 'Activation Error', message: err.message, type: 'error' });
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Confirm & Activate Free Plan';
            }
        }"""

replacement = """        const btn = document.getElementById('btn-confirm-free-plan');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<span class="ent-spinner"></span> Starting 14-Day Free Trial...`;
        }

        try {
            const res = await fetch(`${API_BASE}/api/subscription/change-plan`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify({
                    plan_id: 'free',
                    billing_cycle: 'monthly',
                    payment_method: 'WALLET',
                }),
            });

            const data = await res.json();
            if (!res.ok || (data.status !== 'success' && !data.success)) {
                throw new Error(data.message || data.detail || 'Free trial activation failed.');
            }

            closeFreePlanModal();

            if (typeof loadSubscriptionState === 'function') {
                await loadSubscriptionState();
            }

            if (typeof showLiveToast === 'function') {
                showLiveToast('14-Day Free Trial activated! You now have full access for 14 days.', 'success');
            }

            // Reload entitlements state and reload page to reflect active access
            await loadAllEntitlementsData();
            setTimeout(() => { window.location.href = '/?tab=companies'; }, 1000);

        } catch (err) {
            console.error('Free plan activation error:', err);
            if (typeof showLiveToast === 'function') {
                showLiveToast(`❌ ${err.message}`, 'error');
            } else if (typeof window.showInAppNotification === 'function') {
                window.showInAppNotification({ title: 'Activation Error', message: err.message, type: 'error' });
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Start 14-Day Free Trial';
            }
        }"""

assert target in content, 'target not found in plan_entitlements.js'
content = content.replace(target, replacement, 1)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully updated plan_entitlements.js")

