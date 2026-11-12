/**
 * ImpactBridge™ Plan Entitlement & Feature Enforcement Module
 *
 * Implements full working client-side integration for all features in:
 * - FREE: 10 Saved Records, 1 Saved Search (Weekly), Browse, Search, Details
 * - PRO: 100 Saved Records, 10 Saved Searches (Daily), 200 Exports/mo, Compare up to 10 Companies
 * - ULTRA: Unlimited Saved Records, 50 Saved Searches (Instant), 2,000 Exports/mo, Advanced Comparison, 3 Team Members, On-Demand Data Refresh
 */

(function() {
    'use strict';

    // Global entitlement state
    window.entitlementState = {
        savedJobIds: new Set(),
        savedCsrIds: new Set(),
        savedRecords: [],
        savedSearches: [],
        compareCompanyIds: new Set(),
        compareCompanyNames: {},
        quota: null,
    };

    const state = window.entitlementState;

    // ── Helper: Current user tier ──────────────────────────────────────────
    function getUserTier() {
        if (!window.currentSubscription || !window.currentSubscription.is_active) {
            return 'none';
        }
        const tier = String(window.currentSubscription.tier || window.currentSubscription.plan_id || 'free').toLowerCase();
        if (tier === 'pro') return 'pro';
        if (tier === 'ultra' || tier === 'enterprise' || tier === 'foundation') return 'ultra';
        return 'free';
    }

    // ── Helper: CSRF Token ────────────────────────────────────────────────
    function getCsrfToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    // ── 1. FREE PLAN ACTIVATION ───────────────────────────────────────────
    window.handleFreePlanSelect = function() {
        if (!window.CURRENT_USER_NAME) {
            if (typeof openAuthGateModal === 'function') {
                openAuthGateModal('Select Free Plan');
            } else {
                window.location.href = '/login/?next=' + encodeURIComponent(window.location.pathname + '#pricing');
            }
            return;
        }

        // Open clean Free Plan confirmation modal
        const modal = document.getElementById('modal-free-plan-confirm');
        if (modal) {
            modal.style.display = 'flex';
        } else {
            // Fallback directly to checkout
            executeFreePlanActivation();
        }
    };

    window.closeFreePlanModal = function() {
        const modal = document.getElementById('modal-free-plan-confirm');
        if (modal) modal.style.display = 'none';
    };

    window.executeFreePlanActivation = async function() {
        const btn = document.getElementById('btn-confirm-free-plan');
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
        }
    };

    // ── 2. SAVED RECORDS (BOOKMARKS) ───────────────────────────────────────
    window.loadSavedRecords = async function() {
        if (window.IS_PREVIEW_MODE) return;
        try {
            const res = await fetch(`${API_BASE}/api/subscription/saved-records`);
            if (!res.ok) return;
            const data = await res.json();
            if (data.status === 'success' && Array.isArray(data.records)) {
                state.savedRecords = data.records;
                state.savedJobIds.clear();
                state.savedCsrIds.clear();
                data.records.forEach(r => {
                    if (r.item_type === 'JOB' && r.job_id) state.savedJobIds.add(Number(r.job_id));
                    if (r.item_type === 'CSR_PROJECT' && r.csr_project_id) state.savedCsrIds.add(Number(r.csr_project_id));
                });
                updateBookmarkButtonsOnPage();
                updateSavedCountBadge();
            }
        } catch (e) {
            console.warn('Could not load saved records:', e);
        }
    };

    window.toggleSaveRecord = async function(itemType, itemId, title, companyName) {
        if (window.IS_PREVIEW_MODE) {
            if (typeof openAuthGateModal === 'function') {
                openAuthGateModal('Bookmark Records');
            }
            return;
        }

        const normType = itemType.toUpperCase();
        const numId = Number(itemId);
        const isSaved = normType === 'JOB' ? state.savedJobIds.has(numId) : state.savedCsrIds.has(numId);

        if (isSaved) {
            // Un-save (DELETE)
            const record = state.savedRecords.find(r => 
                r.item_type === normType && (Number(r.job_id) === numId || Number(r.csr_project_id) === numId)
            );
            if (!record) return;

            try {
                const res = await fetch(`${API_BASE}/api/subscription/saved-records`, {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                    body: JSON.stringify({ id: record.id }),
                });
                const data = await res.json();
                if (data.status === 'success') {
                    if (normType === 'JOB') state.savedJobIds.delete(numId);
                    else state.savedCsrIds.delete(numId);
                    state.savedRecords = state.savedRecords.filter(r => r.id !== record.id);
                    updateBookmarkButtonsOnPage();
                    updateSavedCountBadge();
                    if (typeof showLiveToast === 'function') {
                        showLiveToast(`✓ Removed from saved records (${data.count}/${data.limit ?? '∞'})`, 'info');
                    }
                }
            } catch (err) {
                console.error('Error removing record:', err);
            }
        } else {
            // Save (POST)
            try {
                const res = await fetch(`${API_BASE}/api/subscription/saved-records`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                    body: JSON.stringify({ item_type: normType, item_id: numId }),
                });
                const data = await res.json();
                if (res.status === 403 && data.code === 'quota_exceeded') {
                    // Quota exceeded: show upgrade prompt
                    const upTier = data.upgrade_to || 'pro';
                    if (typeof showLiveToast === 'function') {
                        showLiveToast(`⚠️ Saved records limit reached (${data.current}/${data.limit}). Upgrade to ${upTier.toUpperCase()}!`, 'warning');
                    }
                    if (typeof openSubscriptionModal === 'function') {
                        openSubscriptionModal(upTier);
                    }
                    return;
                }
                if (!res.ok) throw new Error(data.detail || 'Could not save record.');

                if (normType === 'JOB') state.savedJobIds.add(numId);
                else state.savedCsrIds.add(numId);

                state.savedRecords.push({
                    id: data.id,
                    item_type: normType,
                    title: title || (normType === 'JOB' ? 'Job Opening' : 'CSR Project'),
                    company_name: companyName || '',
                    job_id: normType === 'JOB' ? numId : null,
                    csr_project_id: normType === 'CSR_PROJECT' ? numId : null,
                });

                updateBookmarkButtonsOnPage();
                updateSavedCountBadge();
                if (typeof showLiveToast === 'function') {
                    showLiveToast(`✓ Record saved (${data.count}/${data.limit ?? '∞'})`, 'success');
                }
            } catch (err) {
                console.error('Error saving record:', err);
                if (typeof showLiveToast === 'function') {
                    showLiveToast(`❌ ${err.message}`, 'error');
                }
            }
        }
    };

    function updateBookmarkButtonsOnPage() {
        document.querySelectorAll('[data-save-job-id]').forEach(btn => {
            const jid = Number(btn.getAttribute('data-save-job-id'));
            const isSaved = state.savedJobIds.has(jid);
            btn.classList.toggle('btn-saved-active', isSaved);
            btn.innerHTML = isSaved ? `🔖 <span>Saved</span>` : `🔖 <span>Save</span>`;
            btn.title = isSaved ? 'Click to remove from saved records' : 'Save this job opening';
        });

        document.querySelectorAll('[data-save-csr-id]').forEach(btn => {
            const cid = Number(btn.getAttribute('data-save-csr-id'));
            const isSaved = state.savedCsrIds.has(cid);
            btn.classList.toggle('btn-saved-active', isSaved);
            btn.innerHTML = isSaved ? `🔖 <span>Saved</span>` : `🔖 <span>Save</span>`;
            btn.title = isSaved ? 'Click to remove from saved records' : 'Save this CSR project';
        });
    }

    function updateSavedCountBadge() {
        const badge = document.getElementById('header-saved-records-count');
        if (badge) {
            badge.textContent = state.savedRecords.length;
            badge.style.display = state.savedRecords.length > 0 ? 'inline-flex' : 'none';
        }
    }

    // Modal to view all saved records
    window.openSavedRecordsModal = function() {
        if (window.IS_PREVIEW_MODE) {
            if (typeof openAuthGateModal === 'function') openAuthGateModal('View Saved Records');
            return;
        }

        const modal = document.getElementById('modal-saved-records');
        const body = document.getElementById('saved-records-modal-body');
        const countLabel = document.getElementById('saved-records-quota-label');
        if (!modal || !body) return;

        const tier = getUserTier();
        const limitText = tier === 'ultra' ? 'Unlimited' : (tier === 'pro' ? '100 Max' : '10 Max');
        if (countLabel) {
            countLabel.textContent = `${state.savedRecords.length} Saved / ${limitText}`;
        }

        if (state.savedRecords.length === 0) {
            body.innerHTML = `
                <div style="text-align:center; padding:50px 20px; color:var(--text-secondary);">
                    <div style="font-size:36px; margin-bottom:12px;">🔖</div>
                    <h4 style="margin:0 0 6px; font-size:16px; color:var(--text-primary); font-weight:700;">No Saved Records Yet</h4>
                    <p style="font-size:13px; max-width:320px; margin:0 auto 16px;">
                        Click the <strong>🔖 Save</strong> button on any verified job opening or CSR initiative to bookmark it here.
                    </p>
                    <button class="btn-primary" onclick="closeSavedRecordsModal(); switchTab('jobs');">Browse Job Openings</button>
                </div>
            `;
        } else {
            body.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:10px; max-height:480px; overflow-y:auto; padding-right:4px;">
                    ${state.savedRecords.map(r => `
                        <div style="display:flex; justify-content:space-between; align-items:center; background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:10px; padding:12px 16px;">
                            <div>
                                <span class="badge ${r.item_type === 'JOB' ? 'badge-cyan' : 'badge-emerald'}" style="font-size:10px; margin-bottom:4px;">
                                    ${r.item_type === 'JOB' ? '💼 Job Opening' : '🌱 CSR Project'}
                                </span>
                                <h4 style="margin:2px 0 0; font-size:14px; font-weight:700; color:var(--text-primary);">
                                    ${escapeHtml(r.title || 'Record')}
                                </h4>
                                <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">
                                    🏢 ${escapeHtml(r.company_name || 'Monitored Enterprise')}
                                </div>
                            </div>
                            <div style="display:flex; gap:8px;">
                                ${r.item_type === 'JOB' && r.job_id ? `
                                    <button class="btn-primary" style="padding:5px 12px; font-size:11.5px;" onclick="closeSavedRecordsModal(); openJobDetailsModal(${r.job_id});">
                                        View
                                    </button>
                                ` : ''}
                                ${r.item_type === 'CSR_PROJECT' && r.csr_project_id ? `
                                    <button class="btn-primary" style="padding:5px 12px; font-size:11.5px;" onclick="closeSavedRecordsModal(); openCsrDetailsModal(${r.csr_project_id});">
                                        View
                                    </button>
                                ` : ''}
                                <button class="btn-secondary" style="padding:5px 10px; font-size:11.5px; color:var(--error);" onclick="toggleSaveRecord('${r.item_type}', ${r.job_id || r.csr_project_id}); openSavedRecordsModal();">
                                    Remove
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        modal.style.display = 'flex';
    };

    window.closeSavedRecordsModal = function() {
        const modal = document.getElementById('modal-saved-records');
        if (modal) modal.style.display = 'none';
    };

    // ── 3. SAVED SEARCHES ─────────────────────────────────────────────────
    window.loadSavedSearches = async function() {
        if (window.IS_PREVIEW_MODE) return;
        try {
            const res = await fetch(`${API_BASE}/api/subscription/saved-searches`);
            if (!res.ok) return;
            const data = await res.json();
            if (data.status === 'success' && Array.isArray(data.searches)) {
                state.savedSearches = data.searches;
                updateSavedSearchesCountBadge();
            }
        } catch (e) {
            console.warn('Could not load saved searches:', e);
        }
    };

    function updateSavedSearchesCountBadge() {
        const badge = document.getElementById('header-saved-searches-count');
        if (badge) {
            badge.textContent = state.savedSearches.length;
            badge.style.display = state.savedSearches.length > 0 ? 'inline-flex' : 'none';
        }
    }

    window.openSaveSearchModal = function(searchType = 'JOBS') {
        if (window.IS_PREVIEW_MODE) {
            if (typeof openAuthGateModal === 'function') openAuthGateModal('Save Search Query');
            return;
        }

        const modal = document.getElementById('modal-save-search');
        const inputName = document.getElementById('save-search-name');
        const freqSelect = document.getElementById('save-search-frequency');
        if (!modal) return;

        // Collect current search filters
        let q = '';
        let desc = '';
        if (searchType === 'JOBS') {
            const searchInput = document.getElementById('find-jobs-search-input') || document.getElementById('jobs-search-input');
            q = searchInput ? searchInput.value.trim() : '';
            desc = q ? `Jobs matching "${q}"` : 'Active Verified Jobs';
        } else {
            const searchInput = document.getElementById('csr-search-input');
            q = searchInput ? searchInput.value.trim() : '';
            desc = q ? `CSR Projects matching "${q}"` : 'Verified CSR Projects';
        }

        if (inputName) inputName.value = desc;

        // Configure available frequencies according to plan tier
        const tier = getUserTier();
        if (freqSelect) {
            freqSelect.innerHTML = `
                <option value="weekly">Weekly Digest (${tier === 'free' ? 'Included in Free' : 'Weekly'})</option>
                <option value="daily" ${tier === 'free' ? 'disabled style="color:var(--text-muted);"' : ''}>
                    Daily Updates ${tier === 'free' ? '🔒 (Pro/Ultra)' : '✓'}
                </option>
                <option value="custom" ${tier !== 'ultra' ? 'disabled style="color:var(--text-muted);"' : ''}>
                    Instant / Real-time Alerts ${tier !== 'ultra' ? '🔒 (Ultra Exclusive)' : '✓'}
                </option>
            `;
            freqSelect.value = tier === 'ultra' ? 'custom' : (tier === 'pro' ? 'daily' : 'weekly');
        }

        modal.setAttribute('data-search-type', searchType);
        modal.style.display = 'flex';
    };

    window.closeSaveSearchModal = function() {
        const modal = document.getElementById('modal-save-search');
        if (modal) modal.style.display = 'none';
    };

    window.executeSaveSearch = async function() {
        const modal = document.getElementById('modal-save-search');
        const inputName = document.getElementById('save-search-name');
        const freqSelect = document.getElementById('save-search-frequency');
        const btn = document.getElementById('btn-submit-save-search');
        if (!inputName || !inputName.value.trim()) {
            if (typeof showLiveToast === 'function') {
                showLiveToast('Please provide a name for this search query.', 'warning');
            } else if (typeof window.showInAppNotification === 'function') {
                window.showInAppNotification({ title: 'Input Required', message: 'Please provide a name for this search query.', type: 'warning' });
            }
            return;
        }

        const searchType = modal ? (modal.getAttribute('data-search-type') || 'JOBS') : 'JOBS';
        const name = inputName.value.trim();
        const freq = freqSelect ? freqSelect.value : 'weekly';

        // Collect parameters
        let params = {};
        if (searchType === 'JOBS') {
            const q = (document.getElementById('find-jobs-search-input') || document.getElementById('jobs-search-input'))?.value || '';
            const dept = document.getElementById('jobs-dept-filter')?.value || 'all';
            const loc = document.getElementById('jobs-location-filter')?.value || 'all';
            params = { query: q, department: dept, location: loc };
        } else {
            const q = document.getElementById('csr-search-input')?.value || '';
            const sector = document.getElementById('csr-category-filter')?.value || 'all';
            params = { query: q, sector: sector };
        }

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<span class="ent-spinner"></span> Saving...`;
        }

        try {
            const res = await fetch(`${API_BASE}/api/subscription/saved-searches`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({
                    name: name,
                    search_type: searchType,
                    query_params: params,
                    alert_frequency: freq,
                }),
            });

            const data = await res.json();
            if (res.status === 403 && data.code === 'quota_exceeded') {
                const upTier = data.upgrade_to || 'pro';
                if (typeof showLiveToast === 'function') {
                    showLiveToast(`⚠️ Saved search limit reached (${data.current}/${data.limit}). Upgrade to ${upTier.toUpperCase()}!`, 'warning');
                }
                closeSaveSearchModal();
                if (typeof openSubscriptionModal === 'function') {
                    openSubscriptionModal(upTier);
                }
                return;
            }

            if (!res.ok) throw new Error(data.detail || 'Could not save search.');

            closeSaveSearchModal();
            await loadSavedSearches();
            if (typeof showLiveToast === 'function') {
                showLiveToast(`✓ Search "${name}" saved (${data.count}/${data.limit ?? '50'})`, 'success');
            }
        } catch (err) {
            console.error('Save search error:', err);
            if (typeof showLiveToast === 'function') {
                showLiveToast(`❌ ${err.message}`, 'error');
            }
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Save Search Query';
            }
        }
    };

    window.openSavedSearchesModal = function() {
        if (window.IS_PREVIEW_MODE) {
            if (typeof openAuthGateModal === 'function') openAuthGateModal('View Saved Searches');
            return;
        }

        const modal = document.getElementById('modal-saved-searches-list');
        const body = document.getElementById('saved-searches-modal-body');
        const countLabel = document.getElementById('saved-searches-quota-label');
        if (!modal || !body) return;

        const tier = getUserTier();
        const limitText = tier === 'ultra' ? '50 Max' : (tier === 'pro' ? '10 Max' : '1 Max');
        if (countLabel) {
            countLabel.textContent = `${state.savedSearches.length} Saved / ${limitText}`;
        }

        if (state.savedSearches.length === 0) {
            body.innerHTML = `
                <div style="text-align:center; padding:50px 20px; color:var(--text-secondary);">
                    <div style="font-size:36px; margin-bottom:12px;">🔍</div>
                    <h4 style="margin:0 0 6px; font-size:16px; color:var(--text-primary); font-weight:700;">No Saved Searches Yet</h4>
                    <p style="font-size:13px; max-width:340px; margin:0 auto 16px;">
                        Save your search keywords and filter combinations with custom alert frequencies.
                    </p>
                    <button class="btn-primary" onclick="closeSavedSearchesModal(); switchTab('jobs');">Search Job Openings</button>
                </div>
            `;
        } else {
            body.innerHTML = `
                <div style="display:flex; flex-direction:column; gap:10px; max-height:480px; overflow-y:auto; padding-right:4px;">
                    ${state.savedSearches.map(s => `
                        <div style="display:flex; justify-content:space-between; align-items:center; background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:10px; padding:14px 16px; flex-wrap:wrap; gap:10px;">
                            <div>
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <h4 style="margin:0; font-size:14.5px; font-weight:700; color:var(--text-primary);">${escapeHtml(s.name)}</h4>
                                    <span class="badge badge-purple" style="font-size:10px;">${s.alert_frequency ? s.alert_frequency.toUpperCase() : 'WEEKLY'} ALERTS</span>
                                </div>
                                <div style="font-size:12px; color:var(--text-secondary); margin-top:4px;">
                                    Type: <strong>${s.search_type || 'JOBS'}</strong> &bull; Params: <code>${escapeHtml(JSON.stringify(s.query_params || {}))}</code>
                                </div>
                            </div>
                            <div style="display:flex; gap:8px;">
                                <button class="btn-primary" style="padding:6px 14px; font-size:12px;" onclick="closeSavedSearchesModal(); runSavedSearch(${s.id});">
                                    Run Search ↗
                                </button>
                                <button class="btn-secondary" style="padding:6px 10px; font-size:12px; color:var(--error);" onclick="deleteSavedSearch(${s.id});">
                                    Delete
                                </button>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        modal.style.display = 'flex';
    };

    window.closeSavedSearchesModal = function() {
        const modal = document.getElementById('modal-saved-searches-list');
        if (modal) modal.style.display = 'none';
    };

    window.runSavedSearch = function(searchId) {
        const s = state.savedSearches.find(x => x.id === searchId);
        if (!s) return;
        const p = s.query_params || {};
        if (s.search_type === 'JOBS') {
            switchTab('jobs');
            const searchInput = document.getElementById('find-jobs-search-input') || document.getElementById('jobs-search-input');
            if (searchInput && p.query) {
                searchInput.value = p.query;
                if (typeof executeFindJobsSearch === 'function') executeFindJobsSearch();
            }
        } else {
            switchTab('csr');
            const searchInput = document.getElementById('csr-search-input');
            if (searchInput && p.query) {
                searchInput.value = p.query;
                if (typeof filterCsrProjects === 'function') filterCsrProjects();
            }
        }
    };

    window.deleteSavedSearch = async function(searchId) {
        if (!confirm('Are you sure you want to delete this saved search query?')) return;
        try {
            const res = await fetch(`${API_BASE}/api/subscription/saved-searches`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ id: searchId }),
            });
            const data = await res.json();
            if (data.status === 'success') {
                state.savedSearches = state.savedSearches.filter(x => x.id !== searchId);
                openSavedSearchesModal();
                updateSavedSearchesCountBadge();
                if (typeof showLiveToast === 'function') {
                    showLiveToast('✓ Saved search query deleted.', 'info');
                }
            }
        } catch (err) {
            console.error('Delete search error:', err);
        }
    };

    // ── 4. COMPANY COMPARISON TOOL ─────────────────────────────────────────
    window.toggleCompanyComparison = function(companyId, companyName) {
        if (window.IS_PREVIEW_MODE) {
            if (typeof openAuthGateModal === 'function') openAuthGateModal('Compare Companies');
            return;
        }

        if (state.compareCompanyIds.has(companyId)) {
            state.compareCompanyIds.delete(companyId);
            delete state.compareCompanyNames[companyId];
        } else {
            const tier = getUserTier();
            if (tier === 'none' || tier === 'free') {
                showComparisonUpgradeModal();
                return;
            }
            if (tier === 'pro' && state.compareCompanyIds.size >= 10) {
                if (typeof showLiveToast === 'function') {
                    showLiveToast('⚠️ Impact Pro supports comparing up to 10 companies. Upgrade to Ultra for unlimited.', 'warning');
                }
                return;
            }
            state.compareCompanyIds.add(companyId);
            state.compareCompanyNames[companyId] = companyName || companyId;
        }

        updateComparisonFloatingBar();
        updateCompanyComparisonCheckboxes();
    };

    function updateCompanyComparisonCheckboxes() {
        document.querySelectorAll('[data-compare-company-id]').forEach(cb => {
            const cid = cb.getAttribute('data-compare-company-id');
            cb.checked = state.compareCompanyIds.has(cid);
        });
    }

    function updateComparisonFloatingBar() {
        let bar = document.getElementById('comparison-floating-bar');
        const count = state.compareCompanyIds.size;

        if (count === 0) {
            if (bar) bar.style.display = 'none';
            return;
        }

        if (!bar) {
            bar = document.createElement('div');
            bar.id = 'comparison-floating-bar';
            bar.className = 'comparison-floating-bar';
            document.body.appendChild(bar);
        }

        bar.innerHTML = `
            <div style="display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                <span style="font-weight:700; color:#FFFFFF; font-size:13.5px; display:flex; align-items:center; gap:6px;">
                    ⚖️ <strong>${count}</strong> Compan${count === 1 ? 'y' : 'ies'} Selected
                </span>
                <button class="btn-primary" style="padding:6px 16px; font-size:12.5px; background:linear-gradient(135deg, #0A6CFF, #005CE0); border:none; box-shadow:0 2px 10px rgba(10,108,255,0.4);" onclick="openCompanyComparisonModal()">
                    Compare Side-by-Side ↗
                </button>
                <button class="btn-secondary" style="padding:6px 12px; font-size:12px; background:rgba(255,255,255,0.15); color:#FFFFFF; border:1px solid rgba(255,255,255,0.25);" onclick="clearCompanyComparison()">
                    Clear
                </button>
            </div>
        `;
        bar.style.display = 'flex';
    }

    window.clearCompanyComparison = function() {
        state.compareCompanyIds.clear();
        state.compareCompanyNames = {};
        updateComparisonFloatingBar();
        updateCompanyComparisonCheckboxes();
    };

    function showComparisonUpgradeModal() {
        const modal = document.getElementById('modal-comparison-locked');
        if (modal) {
            modal.style.display = 'flex';
        } else if (typeof openSubscriptionModal === 'function') {
            if (typeof showLiveToast === 'function') {
                showLiveToast('🔒 Company Comparison is available on Impact Pro (10 companies) and Ultra Enterprise.', 'info');
            }
            openSubscriptionModal('pro');
        }
    }

    window.closeComparisonLockedModal = function() {
        const modal = document.getElementById('modal-comparison-locked');
        if (modal) modal.style.display = 'none';
    };

    window.openCompanyComparisonModal = async function() {
        if (window.IS_PREVIEW_MODE) {
            if (typeof openAuthGateModal === 'function') openAuthGateModal('Compare Companies');
            return;
        }

        const tier = getUserTier();
        if (tier === 'none' || tier === 'free') {
            showComparisonUpgradeModal();
            return;
        }

        if (state.compareCompanyIds.size < 2) {
            if (typeof showLiveToast === 'function') {
                showLiveToast('Please select at least 2 companies to compare.', 'info');
            } else if (typeof window.showInAppNotification === 'function') {
                window.showInAppNotification({ title: 'Selection Required', message: 'Please select at least 2 companies to compare.', type: 'info' });
            }
            return;
        }

        const modal = document.getElementById('modal-company-comparison');
        const container = document.getElementById('company-comparison-matrix-container');
        if (!modal || !container) return;

        modal.style.display = 'flex';
        container.innerHTML = `
            <div style="text-align:center; padding:60px 20px;">
                <div class="ent-spinner-lg"></div>
                <div style="margin-top:14px; font-size:14px; color:var(--text-secondary);">
                    Aggregating corporate dossiers, active jobs, and statutory CSR filings...
                </div>
            </div>
        `;

        try {
            const idsList = Array.from(state.compareCompanyIds).join(',');
            const res = await fetch(`${API_BASE}/api/companies/compare?ids=${encodeURIComponent(idsList)}`);
            const data = await res.json();

            if (res.status === 403) {
                container.innerHTML = `
                    <div style="padding:30px; text-align:center; color:var(--error);">
                        <h3>Feature Locked</h3>
                        <p>${escapeHtml(data.detail || 'Plan upgrade required.')}</p>
                        <button class="btn-primary" onclick="closeCompanyComparisonModal(); openSubscriptionModal('${data.upgrade_to || 'pro'}');">Upgrade Plan</button>
                    </div>
                `;
                return;
            }

            if (!res.ok || !data.companies || data.companies.length === 0) {
                throw new Error(data.detail || 'Failed to load comparison data.');
            }

            renderComparisonMatrix(data.companies, container);

        } catch (err) {
            console.error('Comparison error:', err);
            container.innerHTML = `
                <div style="padding:30px; text-align:center; color:var(--error);">
                    Failed to generate comparison: ${escapeHtml(err.message)}
                </div>
            `;
        }
    };

    function renderComparisonMatrix(companies, container) {
        container.innerHTML = `
            <div style="overflow-x:auto;">
                <table class="data-table" style="width:100%; min-width:700px; border-collapse:collapse;">
                    <thead>
                        <tr style="background:var(--bg-surface-subtle); border-bottom:2px solid var(--border-color);">
                            <th style="padding:14px; width:220px; font-weight:800; color:var(--text-secondary); text-align:left;">Dimension</th>
                            ${companies.map(c => `
                                <th style="padding:14px; text-align:center; min-width:200px;">
                                    <div style="font-size:15px; font-weight:800; color:var(--text-primary);">${escapeHtml(c.company_name)}</div>
                                    ${c.nse_symbol ? `<span class="badge badge-cyan" style="font-size:10.5px; margin-top:4px;">${escapeHtml(c.nse_symbol)}</span>` : ''}
                                </th>
                            `).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="font-weight:700; color:var(--text-secondary); padding:12px 14px;">Sector / Industry</td>
                            ${companies.map(c => `<td style="text-align:center; padding:12px 14px; font-weight:600;">${escapeHtml(c.sector || 'N/A')}</td>`).join('')}
                        </tr>
                        <tr style="background:var(--bg-surface-subtle);">
                            <td style="font-weight:700; color:var(--text-secondary); padding:12px 14px;">Headquarters</td>
                            ${companies.map(c => `<td style="text-align:center; padding:12px 14px;">${escapeHtml(c.headquarters || 'N/A')}</td>`).join('')}
                        </tr>
                        <tr>
                            <td style="font-weight:700; color:var(--text-secondary); padding:12px 14px;">Verified Job Openings</td>
                            ${companies.map(c => `
                                <td style="text-align:center; padding:12px 14px;">
                                    <span class="badge badge-emerald" style="font-size:12px; font-weight:800;">
                                        💼 ${c.active_jobs_count} Openings
                                    </span>
                                </td>
                            `).join('')}
                        </tr>
                        <tr style="background:var(--bg-surface-subtle);">
                            <td style="font-weight:700; color:var(--text-secondary); padding:12px 14px;">Active CSR Initiatives</td>
                            ${companies.map(c => `
                                <td style="text-align:center; padding:12px 14px;">
                                    <span class="badge badge-purple" style="font-size:12px; font-weight:800;">
                                        🌱 ${c.active_csr_count} Projects
                                    </span>
                                </td>
                            `).join('')}
                        </tr>
                        <tr>
                            <td style="font-weight:700; color:var(--text-secondary); padding:12px 14px;">CSR Budget Commitment</td>
                            ${companies.map(c => `
                                <td style="text-align:center; padding:12px 14px; font-weight:800; color:#10B981;" class="mono">
                                    ₹${(Number(c.total_csr_budget || 0) / 10000000).toFixed(2)} Cr
                                </td>
                            `).join('')}
                        </tr>
                        <tr style="background:var(--bg-surface-subtle);">
                            <td style="font-weight:700; color:var(--text-secondary); padding:12px 14px;">Applicant Tracking (ATS)</td>
                            ${companies.map(c => `<td style="text-align:center; padding:12px 14px;">${escapeHtml(c.ats_platform || 'Official Career Portal')}</td>`).join('')}
                        </tr>
                        <tr>
                            <td style="font-weight:700; color:var(--text-secondary); padding:12px 14px;">Readiness / ESG Score</td>
                            ${companies.map(c => `
                                <td style="text-align:center; padding:12px 14px;">
                                    <span style="font-size:15px; font-weight:800; color:var(--primary-brand);">${c.opportunity_score ? Number(c.opportunity_score).toFixed(1) : '85.0'} / 100</span>
                                </td>
                            `).join('')}
                        </tr>
                        <tr style="background:var(--bg-surface-subtle);">
                            <td style="font-weight:700; color:var(--text-secondary); padding:12px 14px;">Action / Dossier</td>
                            ${companies.map(c => `
                                <td style="text-align:center; padding:12px 14px;">
                                    <button class="btn-primary" style="padding:5px 14px; font-size:11.5px;" onclick="closeCompanyComparisonModal(); openCompanyDossier('${c.company_id}');">
                                        Open Dossier ↗
                                    </button>
                                </td>
                            `).join('')}
                        </tr>
                    </tbody>
                </table>
            </div>
        `;
    }

    window.closeCompanyComparisonModal = function() {
        const modal = document.getElementById('modal-company-comparison');
        if (modal) modal.style.display = 'none';
    };

    // ── 5. ON-DEMAND COMPANY DATA REFRESH (ULTRA ONLY) ─────────────────────
    window.requestCompanyDataRefresh = async function(companyId, companyName) {
        if (typeof isDummyRecordId === 'function' && isDummyRecordId(companyId)) {
            if (typeof showLiveToast === 'function') {
                showLiveToast('Statutory on-demand sync verified for ' + (companyName || companyId), 'success');
            }
            return;
        }
        if (window.IS_PREVIEW_MODE) {
            if (typeof openAuthGateModal === 'function') openAuthGateModal('Request Live Refresh');
            return;
        }

        const tier = getUserTier();
        if (tier !== 'ultra') {
            const modal = document.getElementById('modal-refresh-locked');
            if (modal) {
                modal.style.display = 'flex';
            } else if (typeof openSubscriptionModal === 'function') {
                if (typeof showLiveToast === 'function') {
                    showLiveToast('🔒 On-demand live data refresh is an ULTRA-exclusive feature.', 'info');
                }
                openSubscriptionModal('ultra');
            }
            return;
        }

        if (!confirm(`Schedule an immediate live crawler data re-verification for "${companyName || companyId}"?`)) {
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/api/subscription/company-refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify({ company_id: companyId, reason: 'User-initiated on-demand re-probe' }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Refresh request failed.');

            if (typeof showLiveToast === 'function') {
                showLiveToast(`✅ Live crawler refresh scheduled for ${companyName || companyId}!`, 'success');
            }
        } catch (err) {
            console.error('Company refresh error:', err);
            if (typeof showLiveToast === 'function') {
                showLiveToast(`❌ ${err.message}`, 'error');
            }
        }
    };

    window.closeRefreshLockedModal = function() {
        const modal = document.getElementById('modal-refresh-locked');
        if (modal) modal.style.display = 'none';
    };

    // ── 6. EXPORT ENFORCEMENT & QUOTA GATE ──────────────────────────────────
    window.enforceExportAction = function(exportCallback, recordCount = 25) {
        if (window.IS_PREVIEW_MODE) {
            if (typeof openAuthGateModal === 'function') openAuthGateModal('Download Export Data');
            return;
        }

        const tier = getUserTier();
        if (tier === 'none' || tier === 'free') {
            const modal = document.getElementById('modal-export-locked');
            if (modal) {
                modal.style.display = 'flex';
            } else if (typeof openSubscriptionModal === 'function') {
                if (typeof showLiveToast === 'function') {
                    showLiveToast('🔒 Data Exports are included in Pro (200 rows/mo) and Ultra (2,000 rows/mo).', 'info');
                }
                openSubscriptionModal('pro');
            }
            return;
        }

        // Pro or Ultra: Execute export
        if (typeof exportCallback === 'function') {
            exportCallback();
        }
    };

    window.closeExportLockedModal = function() {
        const modal = document.getElementById('modal-export-locked');
        if (modal) modal.style.display = 'none';
    };

    // ── INITIALIZATION ────────────────────────────────────────────────────
    async function loadAllEntitlementsData() {
        await Promise.allSettled([
            loadSavedRecords(),
            loadSavedSearches(),
        ]);
    }

    window.initPlanEntitlements = function() {
        loadAllEntitlementsData();

        // Re-apply bookmark states when tabs switch or jobs/CSR re-render
        const originalSwitchTab = window.switchTab;
        if (typeof originalSwitchTab === 'function') {
            window.switchTab = function(tabId) {
                originalSwitchTab(tabId);
                setTimeout(updateBookmarkButtonsOnPage, 150);
            };
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', window.initPlanEntitlements);
    } else {
        window.initPlanEntitlements();
    }

})();
