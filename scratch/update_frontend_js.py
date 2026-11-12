import os

js_path = os.path.join('static', 'js', 'app.js')
with open(js_path, 'r', encoding='utf-8') as f:
    code = f.read().replace('\r\n', '\n')

# 1. Add isDummyRecordId at top of app.js
top_helper = '''// Helper to identify Dummy Preview entities
window.isDummyRecordId = function(id) {
    if (!id) return false;
    const s = String(id).trim();
    if (s.startsWith('DUMMY_') || s.startsWith('dummy_')) return true;
    if (window.PREVIEW_COMPANY_IDS && window.PREVIEW_COMPANY_IDS.includes(s)) return true;
    return false;
};
function isDummyRecordId(id) {
    return window.isDummyRecordId(id);
}
'''

if 'window.isDummyRecordId =' not in code:
    code = top_helper + '\n' + code

# 2. openCompanyCsr
old_csr = '''function openCompanyCsr(companyId) {
    if (!companyId) return;
    if (window.IS_PREVIEW_MODE || window.PLAN_REQUIRED) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('csr', companyId, window.PLAN_REQUIRED ? '/?tab=pricing' : `/companies/${companyId}/csr`);
        }
        return;
    }
    openCompanyDossier(companyId, 'csr');
}'''

new_csr = '''function openCompanyCsr(companyId) {
    if (!companyId) return;
    const isDummy = isDummyRecordId(companyId);
    if (!isDummy && (window.IS_PREVIEW_MODE || window.PLAN_REQUIRED)) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('csr', companyId, window.PLAN_REQUIRED ? '/?tab=pricing' : `/companies/${companyId}/csr`);
        }
        return;
    }
    openCompanyDossier(companyId, 'csr');
}'''

code = code.replace(old_csr, new_csr)

# 3. openCompanyJobs
old_jobs = '''async function openCompanyJobs(companyId) {
    if (!companyId) return;
    if (window.IS_PREVIEW_MODE || window.PLAN_REQUIRED) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('job', companyId, window.PLAN_REQUIRED ? '/?tab=pricing' : `/companies/${companyId}/jobs`);
        }
        return;
    }'''

new_jobs = '''async function openCompanyJobs(companyId) {
    if (!companyId) return;
    const isDummy = isDummyRecordId(companyId);
    if (isDummy) {
        openCompanyDossier(companyId, 'jobs');
        return;
    }
    if (window.IS_PREVIEW_MODE || window.PLAN_REQUIRED) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('job', companyId, window.PLAN_REQUIRED ? '/?tab=pricing' : `/companies/${companyId}/jobs`);
        }
        return;
    }'''

code = code.replace(old_jobs, new_jobs)

# 4. openCompanyDossier
old_dossier = '''async function openCompanyDossier(companyId, initialTab = 'overview') {
    if (window.IS_PREVIEW_MODE || window.PLAN_REQUIRED) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('company', companyId, window.PLAN_REQUIRED ? '/?tab=pricing' : `/companies/${companyId}`);
        }
        return;
    }'''

new_dossier = '''async function openCompanyDossier(companyId, initialTab = 'overview') {
    const isDummy = isDummyRecordId(companyId);
    if (!isDummy && (window.IS_PREVIEW_MODE || window.PLAN_REQUIRED)) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('company', companyId, window.PLAN_REQUIRED ? '/?tab=pricing' : `/companies/${companyId}`);
        }
        return;
    }'''

code = code.replace(old_dossier, new_dossier)

# Inside openCompanyDossier 401 check
old_dossier_fetch = '''        const res = await fetch(`${API_BASE}/companies/${companyId}/dossier`);
        if (res.status === 401 || res.status === 403) {
            if (modal) modal.style.display = 'none';
            document.body.style.overflow = '';
            if (typeof openAuthGateModal === 'function') {
                openAuthGateModal('company', companyId, `/companies/${companyId}/dossier`);
            }
            return;
        }'''

new_dossier_fetch = '''        const res = await fetch(`${API_BASE}/companies/${companyId}/dossier`);
        if (res.status === 401 || res.status === 403) {
            if (!isDummy) {
                if (modal) modal.style.display = 'none';
                document.body.style.overflow = '';
                if (typeof openAuthGateModal === 'function') {
                    openAuthGateModal('company', companyId, `/companies/${companyId}/dossier`);
                }
                return;
            }
        }'''

code = code.replace(old_dossier_fetch, new_dossier_fetch)

# 5. openJobDetailsModal
old_job_modal = '''async function openJobDetailsModal(jobId, forceRefresh = false) {
    if (window.IS_PREVIEW_MODE || window.PLAN_REQUIRED) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('job', 'Job Vacancy Specifications', window.PLAN_REQUIRED ? '/?tab=pricing' : `/jobs/${jobId}`);
        }
        return;
    }'''

new_job_modal = '''async function openJobDetailsModal(jobId, forceRefresh = false) {
    const isDummy = isDummyRecordId(jobId);
    if (!isDummy && (window.IS_PREVIEW_MODE || window.PLAN_REQUIRED)) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('job', 'Job Vacancy Specifications', window.PLAN_REQUIRED ? '/?tab=pricing' : `/jobs/${jobId}`);
        }
        return;
    }'''

code = code.replace(old_job_modal, new_job_modal)

old_job_fetch = '''        const res = await fetch(url);
        if (res.status === 401 || res.status === 403) {
            if (modal) modal.style.display = 'none';
            document.body.style.overflow = '';
            if (typeof openAuthGateModal === 'function') {
                openAuthGateModal('job', 'Job Vacancy Specifications', window.PLAN_REQUIRED ? '/?tab=pricing' : `/jobs/${jobId}`);
            }
            return;
        }'''

new_job_fetch = '''        const res = await fetch(url);
        if (res.status === 401 || res.status === 403) {
            if (!isDummy) {
                if (modal) modal.style.display = 'none';
                document.body.style.overflow = '';
                if (typeof openAuthGateModal === 'function') {
                    openAuthGateModal('job', 'Job Vacancy Specifications', window.PLAN_REQUIRED ? '/?tab=pricing' : `/jobs/${jobId}`);
                }
                return;
            }
        }'''

code = code.replace(old_job_fetch, new_job_fetch)

# 6. openCsrDetailsModal
old_csr_modal = '''async function openCsrDetailsModal(csrId) {
    if (window.IS_PREVIEW_MODE || window.PLAN_REQUIRED) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('csr', 'Section 135 CSR Dossier', window.PLAN_REQUIRED ? '/?tab=pricing' : `/csr/projects/${csrId}`);
        }
        return;
    }'''

new_csr_modal = '''async function openCsrDetailsModal(csrId) {
    const isDummy = isDummyRecordId(csrId);
    if (!isDummy && (window.IS_PREVIEW_MODE || window.PLAN_REQUIRED)) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('csr', 'Section 135 CSR Dossier', window.PLAN_REQUIRED ? '/?tab=pricing' : `/csr/projects/${csrId}`);
        }
        return;
    }'''

code = code.replace(old_csr_modal, new_csr_modal)

old_csr_fetch = '''        const res = await fetch(`${API_BASE}/csr/projects/${csrId}`);
        if (res.status === 401 || res.status === 403) {
            if (modal) modal.style.display = 'none';
            document.body.style.overflow = '';
            if (typeof openAuthGateModal === 'function') {
                openAuthGateModal('csr', 'Section 135 CSR Dossier', window.PLAN_REQUIRED ? '/?tab=pricing' : `/csr/projects/${csrId}`);
            }
            return;
        }'''

new_csr_fetch = '''        const res = await fetch(`${API_BASE}/csr/projects/${csrId}`);
        if (res.status === 401 || res.status === 403) {
            if (!isDummy) {
                if (modal) modal.style.display = 'none';
                document.body.style.overflow = '';
                if (typeof openAuthGateModal === 'function') {
                    openAuthGateModal('csr', 'Section 135 CSR Dossier', window.PLAN_REQUIRED ? '/?tab=pricing' : `/csr/projects/${csrId}`);
                }
                return;
            }
        }'''

code = code.replace(old_csr_fetch, new_csr_fetch)

# 7. fetchCompanyLiveData
old_fetch_live = '''async function fetchCompanyLiveData(companyId, btnElement) {
    if (!companyId) return;
    if (window.IS_PREVIEW_MODE) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('company', companyId, `/companies/${companyId}`);
        }
        return;
    }'''

new_fetch_live = '''async function fetchCompanyLiveData(companyId, btnElement) {
    if (!companyId) return;
    if (isDummyRecordId(companyId)) {
        if (typeof showLiveToast === 'function') showLiveToast('Statutory live verification refreshed for ' + companyId, 'success');
        return;
    }
    if (window.IS_PREVIEW_MODE) {
        if (typeof openAuthGateModal === 'function') {
            openAuthGateModal('company', companyId, `/companies/${companyId}`);
        }
        return;
    }'''

code = code.replace(old_fetch_live, new_fetch_live)

# 8. Overview tab operating locations
old_overview_locations = '''        // Collect distinct locations from jobs & CSR projects
        const rawLocations = [
            ...jobs.map(j => j.location).filter(Boolean),
            ...projects.map(p => p.state).filter(Boolean)
        ];
        const uniqueLocations = [...new Set(rawLocations)].slice(0, 6);'''

new_overview_locations = '''        // Collect distinct locations from company master, jobs & CSR projects
        const rawLocations = [
            ...(currentDossierData.operating_locations || []),
            ...(comp.operating_locations ? comp.operating_locations.replace(/;/g, ',').split(',') : []),
            ...jobs.map(j => j.location).filter(Boolean),
            ...projects.map(p => p.state).filter(Boolean)
        ];
        const uniqueLocations = [...new Set(rawLocations.map(s => String(s).trim()).filter(Boolean))].slice(0, 8);'''

code = code.replace(old_overview_locations, new_overview_locations)

with open(js_path, 'w', encoding='utf-8') as f:
    f.write(code)

# Also write to app.min.js
min_js_path = os.path.join('static', 'js', 'app.min.js')
with open(min_js_path, 'w', encoding='utf-8') as f:
    f.write(code)

print("Updated app.js and app.min.js successfully")

# Update plan_entitlements.js requestCompanyDataRefresh
pe_path = os.path.join('static', 'js', 'plan_entitlements.js')
with open(pe_path, 'r', encoding='utf-8') as f:
    pe_code = f.read().replace('\r\n', '\n')

old_pe_refresh = '''    window.requestCompanyDataRefresh = async function(companyId, companyName) {
        if (window.IS_PREVIEW_MODE) {
            if (typeof openAuthGateModal === 'function') openAuthGateModal('Request Live Refresh');
            return;
        }'''

new_pe_refresh = '''    window.requestCompanyDataRefresh = async function(companyId, companyName) {
        if (typeof isDummyRecordId === 'function' && isDummyRecordId(companyId)) {
            if (typeof showLiveToast === 'function') {
                showLiveToast('Statutory on-demand sync verified for ' + (companyName || companyId), 'success');
            }
            return;
        }
        if (window.IS_PREVIEW_MODE) {
            if (typeof openAuthGateModal === 'function') openAuthGateModal('Request Live Refresh');
            return;
        }'''

if old_pe_refresh in pe_code:
    pe_code = pe_code.replace(old_pe_refresh, new_pe_refresh)
    with open(pe_path, 'w', encoding='utf-8') as f:
        f.write(pe_code)
    print("Updated plan_entitlements.js successfully")
else:
    print("Warning: old_pe_refresh not found in plan_entitlements.js")

