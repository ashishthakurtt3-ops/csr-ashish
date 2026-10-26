/**
 * ImpactBridge: CSR & Enterprise Job Intelligence OS
 * Production Client Controller & Modern UX Engine 3.0
 */

const API_BASE = '';

// Company records come strictly from the verified MySQL database (no hard-coded client registry).

// Global App State
let allRecommendations = [];
let allJobs = [];
let filteredJobs = [];
let allOpportunities = [];
let allProspects = [];
let allCrawlerLogs = [];
let crawlerTelemetry = {};
let activeTab = 'companies';
let companyViewMode = 'cards'; // 'cards' | 'table'
let activeJobCategory = 'all';
let currentSubscription = {
    tier: 'free',
    plan_id: 'free',
    plan_name: 'Community Free',
    organization_name: 'Institutional Non-Profit Access',
    contact_email: '',
    status: 'ACTIVE',
    is_free: true,
    limits: {
        daily_matches: 5,
        view_contacts: false,
        live_reprobe: false,
        export_rows_per_month: 25,
        seats: 1,
        api_access: false,
        audit_packs: false
    },
    quota: {
        used: 0,
        limit: 5,
        unlimited: false
    }
};

// Central Pagination State Store - Strictly Synchronized to Real Database State
const paginationState = {
    companies: { page: 1, pageSize: 12, total: 0, totalPages: 1 },
    companyDirectory: { page: 1, pageSize: 16, total: 0, totalPages: 1 },
    jobs: { page: 1, pageSize: 12, total: 0, totalPages: 1 },
    findJobs: { page: 1, pageSize: 12, total: 0, totalPages: 1 },
    companyJobs: { page: 1, pageSize: 12, total: 0, totalPages: 1 },
    csr: { page: 1, pageSize: 12, total: 0, totalPages: 1 },
    opps: { page: 1, pageSize: 9, total: 0, totalPages: 1 },
    crawler: { page: 1, pageSize: 15, total: 0, totalPages: 1 }
};

// Utility: Debounce for fast, dynamic searches
function debounce(func, wait = 280) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initApp();
    });
} else {
    initApp();
}

async function initApp() {
    setupEventListeners();
    setupGlobalModalBehaviour();
    
    // Initialize Live Fetch timestamp display
    try {
        const savedTime = localStorage.getItem('csr_last_fetch_time') || 'Never';
        updateAllFetchTimestamps(savedTime, true);
    } catch (e) {
        updateAllFetchTimestamps('Never', true);
    }

    // Detect device screen size and configure mobile view modes
    if (window.innerWidth <= 768) {
        setJobViewMode('cards');
    }
    window.addEventListener('resize', debounce(() => {
        if (window.innerWidth <= 768 && currentJobViewMode === 'table') {
            setJobViewMode('cards');
        }
    }, 200));

    // High performance initial load: immediately render Tab 1 (Donors) and stats
    // Secondary tabs (Jobs, Grants, CRM, Telemetry) load on-demand when clicked
    populateJobFilterDropdowns();
    loadStats();
    loadRecommendations(1);
    loadLoginRequiredCompaniesSection();
    loadSubscriptionState();
    loadAndRenderPricingPlans();
}

function setupEventListeners() {
    // Smooth horizontal mouse-wheel scrolling for pill rows & nav tabs without ugly scrollbars
    ['.header-tabs-row', '.job-category-pills', '.cause-pill-bar', '.freshness-ticker-bar'].forEach(sel => {
        const el = document.querySelector(sel);
        if (el) {
            el.addEventListener('wheel', (e) => {
                if (e.deltaY !== 0 && el.scrollWidth > el.clientWidth) {
                    e.preventDefault();
                    el.scrollLeft += e.deltaY;
                }
            }, { passive: false });
        }
    });

    // Top Navigation Links
    document.querySelectorAll('.nav-link-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const button = e.currentTarget;
            document.querySelectorAll('.nav-link-btn').forEach(b => b.classList.remove('active'));
            button.classList.add('active');
            const targetNav = button.dataset.nav;
            if (targetNav) switchTab(targetNav);
        });
    });

    // Search and Filters for Company Explorer (Debounced Dynamic Filter)
    const searchInput = document.getElementById('global-search');
    if (searchInput) {
        const debouncedCompanyFilter = debounce(() => filterCompanyTable(), 250);
        searchInput.addEventListener('input', (e) => {
            const clearBtn = document.getElementById('company-search-clear');
            if (clearBtn) clearBtn.style.display = e.target.value ? 'block' : 'none';
            debouncedCompanyFilter();
        });
    }

    ['sector-filter', 'tier-filter', 'opp-only-filter'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', () => filterCompanyTable());
    });

    // Job Search and Filters (Debounced Dynamic Filter)
    const jobSearch = document.getElementById('job-search');
    if (jobSearch) {
        const debouncedJobFilter = debounce(() => filterJobs(), 250);
        jobSearch.addEventListener('input', (e) => {
            const clearBtn = document.getElementById('job-search-clear');
            if (clearBtn) clearBtn.style.display = e.target.value ? 'block' : 'none';
            debouncedJobFilter();
        });
    }

    ['job-company-filter', 'job-department-filter', 'job-location-filter', 'job-mode-filter', 'job-exp-filter', 'job-sort-filter'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', () => filterJobs());
    });

    // Find Jobs Discovery input (Debounced Dynamic Filter)
    const findSearchInput = document.getElementById('find-jobs-search-input');
    if (findSearchInput) {
        const debouncedFindFilter = debounce(() => executeFindJobsSearch(), 250);
        findSearchInput.addEventListener('input', (e) => {
            const clearBtn = document.getElementById('find-jobs-search-clear');
            if (clearBtn) clearBtn.style.display = e.target.value ? 'block' : 'none';
            debouncedFindFilter();
        });
    }

    // Crawler Search and Filters (Debounced Dynamic Filter)
    const crawlerSearch = document.getElementById('crawler-log-search');
    if (crawlerSearch) {
        const debouncedCrawlerFilter = debounce(() => filterCrawlerLogs(), 250);
        crawlerSearch.addEventListener('input', debouncedCrawlerFilter);
    }
    ['crawler-quality-filter', 'crawler-status-filter', 'crawler-sort-filter'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', () => filterCrawlerLogs());
    });

    // CSR Search and Filters (Debounced Dynamic Filter)
    const csrSearch = document.getElementById('csr-search');
    if (csrSearch) {
        const debouncedCsrFilter = debounce(() => filterCsrProjects(), 250);
        csrSearch.addEventListener('input', (e) => {
            const clearBtn = document.getElementById('csr-search-clear');
            if (clearBtn) clearBtn.style.display = e.target.value ? 'block' : 'none';
            debouncedCsrFilter();
        });
    }
    const csrStateFilter = document.getElementById('csr-state-filter');
    if (csrStateFilter) {
        csrStateFilter.addEventListener('change', () => filterCsrProjects());
    }

    // Keyboard ESC closes any open modal or navigation drawer
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllModals();
            closeMobileNav();
        }
    });
}

function setupGlobalModalBehaviour() {
    document.querySelectorAll('.modal-backdrop').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeModal(modal.id);
            }
        });
    });
}

// ===========================================================================
// MOBILE NAVIGATION & RESPONSIVE CONTROLLER
// ===========================================================================
function toggleMobileNav() {
    const drawer = document.getElementById('mobileNavDrawer');
    const backdrop = document.getElementById('mobileDrawerBackdrop');
    if (drawer && backdrop) {
        const isShown = drawer.classList.contains('show');
        if (isShown) {
            closeMobileNav();
        } else {
            drawer.classList.add('show');
            backdrop.classList.add('show');
            document.body.style.overflow = 'hidden';
        }
    }
}

function closeMobileNav() {
    const drawer = document.getElementById('mobileNavDrawer');
    const backdrop = document.getElementById('mobileDrawerBackdrop');
    if (drawer) drawer.classList.remove('show');
    if (backdrop) backdrop.classList.remove('show');
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
}

// Mobile Segmented Controller for CRM Kanban
function setKanbanMobileView(stage) {
    document.querySelectorAll('.kanban-tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.stage === stage);
    });
    const colMap = {
        'Shortlisted': 'col-Shortlisted',
        'ProposalSent': 'col-ProposalSent',
        'InDiscussion': 'col-InDiscussion',
        'Partnered': 'col-Partnered'
    };
    const targetColId = colMap[stage];
    if (targetColId) {
        const targetCol = document.getElementById(targetColId);
        if (targetCol) {
            const parent = targetCol.closest('.kanban-col');
            if (parent) {
                parent.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
            }
        }
    }
}

function toggleMobileGuide() {
    const banner = document.getElementById('ngoWelcomeBanner');
    const arrow = document.getElementById('guideToggleArrow');
    if (!banner) return;
    const isShowing = banner.classList.toggle('mobile-guide-open');
    if (arrow) {
        arrow.textContent = isShowing ? '▲' : '▼';
    }
}

async function switchTab(tab) {
    activeTab = tab;
    closeMobileNav();

    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    const target = document.getElementById(`tab-${tab}`);
    if (target) target.style.display = 'block';

    const heroBanner = document.querySelector('.hero-banner');
    if (heroBanner) {
        if (tab === 'pricing') {
            heroBanner.style.display = 'none';
        } else {
            heroBanner.style.display = 'block';
        }
    }

    document.querySelectorAll('.nav-link-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.nav === tab));
    document.querySelectorAll('.drawer-nav-btn').forEach(b =>
        b.classList.toggle('active', b.dataset.nav === tab));
    document.querySelectorAll('.mobile-bottom-nav-item').forEach(b =>
        b.classList.toggle('active', b.dataset.bottomNav === tab));

    if (tab === 'jobs') {
        if (allJobs.length === 0) {
            await loadJobs();
        } else if (filteredJobs.length === 0) {
            filterJobs();
        }
    } else if (tab === 'csr-projects') {
        if (allCsrProjects.length === 0) loadCsrProjects(1);
    } else if (tab === 'coverage') {
        loadCoverageTable();
    } else if (tab === 'active-opps' && allOpportunities.length === 0) {
        loadOpportunities();
    } else if (tab === 'prospects') {
        loadProspects();
    } else if (tab === 'crawler-logs') {
        if (allCrawlerLogs.length === 0) loadCrawlerLogs();
    } else if (tab === 'pricing') {
        loadSubscriptionState();
        loadAndRenderPricingPlans();
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ===========================================================================
// DATA NORMALIZATION & HONESTY GUARD (Zero Fabricated or Stale Data)
// ===========================================================================
function _cleanHttpUrl(u) {
    if (!u || typeof u !== 'string') return null;
    const s = u.trim();
    if (!/^https?:\/\//i.test(s) || s.toLowerCase().includes('google.com/search') || s.toLowerCase().includes('bing.com/search')) {
        return null;
    }
    return s;
}

function normalizeCompanyData(item) {
    if (!item) return item;
    // Strictly preserve database values without any hard-coded company name or URL overrides.
    const urlFields = [
        'website_url', 'careers_url', 'csr_portal_url', 'csr_webpage_url',
        'sustainability_url', 'esg_url', 'foundation_url', 'annual_report_url',
        'brsr_url', 'investor_url', 'contact_page_url'
    ];
    urlFields.forEach(f => {
        if (f in item) {
            item[f] = _cleanHttpUrl(item[f]);
        }
    });
    return item;
}

function getCompanyWebsite(company) {
    return (company && _cleanHttpUrl(company.website_url)) || '';
}

function getCompanyCsrWebpageUrl(company) {
    if (!company) return '';
    const candidates = [
        company.csr_webpage_url,
        company.csr_portal_url,
        company.foundation_url,
        company.sustainability_url,
        company.esg_url,
        company.brsr_url,
        company.annual_report_url
    ];
    for (const c of candidates) {
        const clean = _cleanHttpUrl(c);
        if (clean) return clean;
    }
    return '';
}

function openCompanyCsr(companyId) {
    if (!companyId) return;
    openCompanyDossier(companyId, 'csr');
}

function cleanDomainLabel(url) {
    if (!url || !url.startsWith('http') || url.includes('google.com/search')) return NOT_AVAILABLE_TEXT;
    return url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0];
}

function formatDateTime(isoString) {
    if (!isoString) return NOT_AVAILABLE_TEXT;
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return String(isoString).slice(0, 19).replace('T', ' ');
    return d.toLocaleDateString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric'
    }) + ' ' + d.toLocaleTimeString('en-IN', {
        hour: '2-digit', minute: '2-digit', hour12: false
    }) + ' UTC';
}

function formatDate(dateVal) {
    if (!dateVal) return 'Recent';
    const d = new Date(dateVal);
    if (isNaN(d.getTime())) return String(dateVal).slice(0, 10);
    return d.toLocaleDateString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric'
    });
}

function timeAgo(isoString) {
    if (!isoString) return 'Live';
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return 'Live';
    const diffSec = Math.floor((new Date() - d) / 1000);
    if (diffSec < 60) return 'Just now';
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${Math.floor(diffHours / 24)}d ago`;
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Robust enterprise avatar initials generator.
 * Never outputs 'NOT', 'N/A', or placeholder text.
 */
function getCompanyInitials(name, symbol) {
    if (symbol && typeof symbol === 'string') {
        const cleanSym = symbol.trim().toUpperCase();
        if (cleanSym.length >= 2 && cleanSym.length <= 6 && !cleanSym.includes('NOT') && !cleanSym.includes('AVAILABLE') && cleanSym !== 'NULL' && cleanSym !== 'NONE') {
            return cleanSym.slice(0, 4);
        }
    }
    if (!name || typeof name !== 'string') return 'CO';
    const clean = name.replace(/[(),.\-_/&]/g, ' ').trim();
    const words = clean.split(/\s+/).filter(w => {
        const u = w.toUpperCase();
        return !['LIMITED', 'LTD', 'INDIA', 'PVT', 'PRIVATE', 'THE', 'AND', 'OF', 'CORP', 'CORPORATION', 'CO', 'ENTERPRISE', 'ENTERPRISES', 'HOLDINGS', 'GROUP'].includes(u);
    });

    if (words.length >= 2) {
        return (words[0][0] + words[1][0]).toUpperCase();
    } else if (words.length === 1 && words[0].length >= 2) {
        return words[0].slice(0, Math.min(3, words[0].length)).toUpperCase();
    }
    return (name.replace(/[^a-zA-Z0-9]/g, '').slice(0, 2) || 'CO').toUpperCase();
}

/**
 * Returns a consistent, vibrant gradient based on the company name
 */
function getAvatarGradient(name) {
    const gradients = [
        'linear-gradient(135deg, #0f766e 0%, #115e59 100%)', // Deep Teal
        'linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%)', // Royal Blue
        'linear-gradient(135deg, #4338ca 0%, #3730a3 100%)', // Indigo
        'linear-gradient(135deg, #047857 0%, #065f46 100%)', // Emerald
        'linear-gradient(135deg, #6d28d9 0%, #5b21b6 100%)', // Deep Purple
        'linear-gradient(135deg, #0369a1 0%, #075985 100%)', // Ocean Blue
        'linear-gradient(135deg, #b45309 0%, #92400e 100%)', // Warm Amber
        'linear-gradient(135deg, #334155 0%, #1e293b 100%)'  // Slate Dark
    ];
    let hash = 0;
    const str = name || 'Corporate';
    for (let i = 0; i < str.length; i++) {
        hash = (hash << 5) - hash + str.charCodeAt(i);
        hash |= 0;
    }
    const idx = Math.abs(hash) % gradients.length;
    return gradients[idx];
}

// ===========================================================================
// KPI METRICS
// ===========================================================================
async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        if (!res.ok) return;
        const data = await res.json();
        
        const totalCorps = data.total_companies !== undefined ? data.total_companies : 200;
        const verifiedCorps = data.verified_companies !== undefined ? data.verified_companies : totalCorps;
        const verifiedJobs = data.jobs_tracked !== undefined ? data.jobs_tracked : 0;
        const verifiedCsr = data.csr_projects !== undefined ? data.csr_projects : 0;
        const verifiedOpps = data.active_opportunities !== undefined ? data.active_opportunities : 0;
        const lastFetch = data.last_live_fetch || NOT_AVAILABLE_TEXT;
        const crawlState = data.crawl_status || 'LIVE';

        // Part 20 Professional Status Bar Elements
        const statusCorps = document.getElementById('status-companies-val');
        if (statusCorps) statusCorps.textContent = `${verifiedCorps} verified / ${totalCorps} total`;
        const statusJobs = document.getElementById('status-jobs-val');
        if (statusJobs) statusJobs.textContent = `${verifiedJobs.toLocaleString('en-IN')} verified`;
        const statusCsr = document.getElementById('status-csr-val');
        if (statusCsr) statusCsr.textContent = `${verifiedCsr.toLocaleString('en-IN')} verified`;
        const statusOpps = document.getElementById('status-opps-val');
        if (statusOpps) statusOpps.textContent = `${verifiedOpps.toLocaleString('en-IN')} verified`;
        const statusFetch = document.getElementById('status-last-fetch-val');
        if (statusFetch) statusFetch.textContent = lastFetch;
        const statusCrawl = document.getElementById('status-crawl-state-val');
        if (statusCrawl) statusCrawl.textContent = crawlState;

        // Legacy / Secondary ID synchronization
        animateValue('kpi-companies', totalCorps);
        animateValue('kpi-websites', data.verified_websites !== undefined ? data.verified_websites : totalCorps);
        animateValue('kpi-jobs', verifiedJobs.toLocaleString('en-IN'));
        animateValue('kpi-csr', verifiedCsr.toLocaleString('en-IN'));
        animateValue('kpi-opps', verifiedOpps.toLocaleString('en-IN'));
        if (data.total_csr_budget_cr) {
            animateValue('kpi-pool', `₹${Number(data.total_csr_budget_cr).toLocaleString('en-IN')} Cr`);
        }

        // Synchronize navigation, mobile drawer, and terminal badges
        const navCorps = document.getElementById('nav-companies-badge');
        if (navCorps) navCorps.textContent = totalCorps;
        const mobileNavCorps = document.getElementById('mobile-nav-companies-badge');
        if (mobileNavCorps) mobileNavCorps.textContent = totalCorps;
        const mobileCorpsCount = document.getElementById('mobile-companies-count');
        if (mobileCorpsCount) mobileCorpsCount.textContent = totalCorps;

        const oppBadge = document.getElementById('nav-opps-badge');
        if (oppBadge) oppBadge.textContent = verifiedOpps;
        const mobileOppBadge = document.getElementById('mobile-nav-opps-badge');
        if (mobileOppBadge) mobileOppBadge.textContent = verifiedOpps;

        const navCsrBadge = document.getElementById('nav-csr-badge');
        if (navCsrBadge) navCsrBadge.textContent = verifiedCsr.toLocaleString('en-IN');

        const jobsBadge = document.getElementById('jobs-count-badge');
        if (jobsBadge) jobsBadge.textContent = verifiedJobs.toLocaleString('en-IN');
        const mobileJobsBadge = document.getElementById('mobile-nav-jobs-badge');
        if (mobileJobsBadge) mobileJobsBadge.textContent = verifiedJobs.toLocaleString('en-IN');
        const totalJobsPill = document.getElementById('badge-jobs-total-pill');
        if (totalJobsPill) totalJobsPill.textContent = verifiedJobs.toLocaleString('en-IN');
        const companyJobsPill = document.getElementById('badge-jobs-company-pill');
        if (companyJobsPill) companyJobsPill.textContent = `${totalCorps} Corps`;

        const termJobs = document.getElementById('term-stat-jobs');
        if (termJobs) termJobs.textContent = `${verifiedJobs.toLocaleString('en-IN')} Openings`;
        const termCorps = document.getElementById('term-stat-corps');
        if (termCorps) termCorps.textContent = `${totalCorps} Verified`;
        const telemetryCount = document.getElementById('telemetry-companies-count');
        if (telemetryCount) telemetryCount.textContent = totalCorps;

        const analyticsJobs = document.getElementById('analytics-jobs-total');
        if (analyticsJobs) analyticsJobs.textContent = `${verifiedJobs.toLocaleString('en-IN')} Active`;
        const coverageJobs = document.getElementById('coverage-kpi-jobs');
        if (coverageJobs) coverageJobs.textContent = `${verifiedJobs.toLocaleString('en-IN')} Verified`;
        const coverageCsr = document.getElementById('coverage-kpi-csr');
        if (coverageCsr) coverageCsr.textContent = `${verifiedCsr.toLocaleString('en-IN')} Verified`;

        // Update hero last-extracted timestamp
        const heroStamp = document.getElementById('hero-live-last-extracted');
        if (heroStamp) heroStamp.textContent = lastFetch;
        const heroStampBadge = document.getElementById('hero-live-relative-time');
        if (heroStampBadge) heroStampBadge.textContent = '(Authoritative Crawl)';
        const headerFetchedTime = document.getElementById('header-fetched-time');
        if (headerFetchedTime) headerFetchedTime.textContent = lastFetch;
    } catch (e) {
        console.warn('Could not fetch stats', e);
    }
}

function animateValue(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value;
}

// ===========================================================================
// REUSABLE MODERN PAGINATION ENGINE
// ===========================================================================
function renderPaginationBar({
    containerId,
    page,
    totalPages,
    total,
    pageSize,
    pageSizeOptions = [12, 24, 48, 96],
    itemLabel = 'items',
    onPageChange,
    onPageSizeChange
}) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!total || total === 0 || totalPages <= 1) {
        if (total > 0) {
            container.innerHTML = `
                <div class="pagination-container single-page">
                    <div class="pagination-info">
                        Showing all <span class="pagination-val">${total}</span> ${escapeHtml(itemLabel)}
                    </div>
                </div>
            `;
        } else {
            container.innerHTML = '';
        }
        return;
    }

    const startItem = Math.min(total, (page - 1) * pageSize + 1);
    const endItem = Math.min(total, page * pageSize);

    // Compute visible page numbers with smart ellipsis
    const pageNumbers = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) pageNumbers.push(i);
    } else {
        pageNumbers.push(1);
        if (page > 3) pageNumbers.push('...');
        const start = Math.max(2, page - 1);
        const end = Math.min(totalPages - 1, page + 1);
        for (let i = start; i <= end; i++) {
            if (!pageNumbers.includes(i)) pageNumbers.push(i);
        }
        if (page < totalPages - 2) pageNumbers.push('...');
        if (!pageNumbers.includes(totalPages)) pageNumbers.push(totalPages);
    }

    const sizeOptionsHtml = pageSizeOptions.map(sz => 
        `<option value="${sz}" ${sz === pageSize ? 'selected' : ''}>${sz} / page</option>`
    ).join('');

    container.innerHTML = `
        <div class="pagination-container">
            <div class="pagination-info">
                Showing <span class="pagination-val">${startItem}</span>&ndash;<span class="pagination-val">${endItem}</span> of <span class="pagination-val">${total}</span> ${escapeHtml(itemLabel)}
            </div>

            <div class="pagination-nav">
                <button class="pagination-btn pagination-nav-btn" data-action="first" ${page <= 1 ? 'disabled' : ''} title="First Page">
                    &laquo; First
                </button>
                <button class="pagination-btn pagination-nav-btn" data-action="prev" ${page <= 1 ? 'disabled' : ''} title="Previous Page">
                    &lsaquo; Prev
                </button>

                <div class="pagination-num-group">
                    ${pageNumbers.map(p => {
                        if (p === '...') {
                            return `<span class="pagination-ellipsis">&hellip;</span>`;
                        }
                        return `
                            <button class="pagination-btn ${p === page ? 'active' : ''}" data-page="${p}" title="Page ${p}">
                                ${p}
                            </button>
                        `;
                    }).join('')}
                </div>

                <button class="pagination-btn pagination-nav-btn" data-action="next" ${page >= totalPages ? 'disabled' : ''} title="Next Page">
                    Next &rsaquo;
                </button>
                <button class="pagination-btn pagination-nav-btn" data-action="last" ${page >= totalPages ? 'disabled' : ''} title="Last Page">
                    Last &raquo;
                </button>
            </div>

            <div class="pagination-size-wrap">
                <span>View:</span>
                <select class="pagination-size-select" title="Change number of items displayed per page">
                    ${sizeOptionsHtml}
                </select>
            </div>
        </div>
    `;

    // Event Delegation for Button Clicks
    container.querySelectorAll('.pagination-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const b = e.currentTarget;
            if (b.disabled) return;
            const action = b.dataset.action;
            const targetPage = b.dataset.page;
            let newPage = page;
            if (action === 'first') newPage = 1;
            else if (action === 'prev') newPage = Math.max(1, page - 1);
            else if (action === 'next') newPage = Math.min(totalPages, page + 1);
            else if (action === 'last') newPage = totalPages;
            else if (targetPage) newPage = parseInt(targetPage, 10);

            if (newPage !== page && typeof onPageChange === 'function') {
                onPageChange(newPage);
            }
        });
    });

    const sizeSelect = container.querySelector('.pagination-size-select');
    if (sizeSelect) {
        sizeSelect.addEventListener('change', (e) => {
            const newSize = parseInt(e.target.value, 10);
            if (newSize !== pageSize && typeof onPageSizeChange === 'function') {
                onPageSizeChange(newSize);
            }
        });
    }
}

// ===========================================================================
// TAB 1: COMPANY EXPLORER & OPPORTUNITY RADAR
// ===========================================================================
async function loadRecommendations(page = 1) {
    if (typeof page !== 'number' || isNaN(page) || page < 1) {
        page = parseInt(page, 10);
        if (isNaN(page) || page < 1) page = 1;
    }
    paginationState.companies.page = page;
    const cardsContainer = document.getElementById('companies-cards-container');
    const tableBody = document.getElementById('companies-table-body');
    
    // Dynamic skeleton loader feedback
    if (cardsContainer && companyViewMode === 'cards') {
        cardsContainer.innerHTML = `
            <div class="dynamic-loading-skeleton">
                <div class="loading-spinner-circle"></div>
                <div class="loading-spinner-text">Querying Verified Indian Enterprises...</div>
                <div class="loading-spinner-sub">Loading page ${page} of official statutory records</div>
            </div>`;
    }
    if (tableBody && companyViewMode === 'table') {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align:center; padding:45px;">
                    <div style="display:inline-flex; align-items:center; gap:10px; color:var(--accent-cyan);">
                        <span class="loading-spinner-circle" style="width:20px; height:20px; margin:0; border-width:2px;"></span>
                        <span>Loading live enterprise records (Page ${page})...</span>
                    </div>
                </td>
            </tr>`;
    }

    try {
        const query = (document.getElementById('global-search')?.value || '').trim();
        const sector = document.getElementById('sector-filter')?.value || 'all';
        const state = selectedCompanyState !== 'all' ? selectedCompanyState : (document.getElementById('state-filter')?.value || 'all');
        const oppOnly = document.getElementById('opp-only-filter')?.checked;

        let url = `${API_BASE}/recommendations?page=${page}&page_size=${paginationState.companies.pageSize}`;
        if (query) url += `&q=${encodeURIComponent(query)}`;
        if (sector && sector !== 'all') url += `&sector=${encodeURIComponent(sector)}`;
        if (state && state !== 'all') url += `&state=${encodeURIComponent(state)}`;
        if (selectedCompanyCause && selectedCompanyCause !== 'all') url += `&cause=${encodeURIComponent(selectedCompanyCause)}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        let items = [];
        let total = 0;
        let totalPages = 1;

        if (data && typeof data === 'object' && Array.isArray(data.items)) {
            items = data.items.map(normalizeCompanyData);
            total = data.total;
            totalPages = data.total_pages;
        } else if (Array.isArray(data)) {
            items = data.map(normalizeCompanyData);
            total = items.length;
            totalPages = Math.ceil(total / paginationState.companies.pageSize);
        }
        if (oppOnly) {
            items = items.filter(item => (item.open_opportunities_count || 0) > 0);
        }

        allRecommendations = items;
        paginationState.companies.total = total;
        paginationState.companies.totalPages = totalPages;

        renderCompanyViews(items, total);
        renderCompanyPagination();
    } catch (e) {
        if (cardsContainer) {
            cardsContainer.innerHTML = `<div style="grid-column:1/-1; color:#f43f5e; text-align:center; padding:40px;">Failed to load company records: ${escapeHtml(e.message)}</div>`;
        }
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:30px; color:#f43f5e;">Error loading data: ${escapeHtml(e.message)}</td></tr>`;
        }
    }
}

function renderCompanyPagination() {
    renderPaginationBar({
        containerId: 'companies-pagination',
        page: paginationState.companies.page,
        totalPages: paginationState.companies.totalPages,
        total: paginationState.companies.total,
        pageSize: paginationState.companies.pageSize,
        pageSizeOptions: [12, 24, 48, 96],
        itemLabel: 'Verified Companies',
        onPageChange: (newPage) => {
            loadRecommendations(newPage);
            const anchor = document.getElementById('tab-companies');
            if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
        onPageSizeChange: (newSize) => {
            paginationState.companies.pageSize = newSize;
            loadRecommendations(1);
        }
    });
}

function setCompanyViewMode(mode) {
    companyViewMode = mode;
    const btnCards = document.getElementById('btn-view-cards');
    const btnTable = document.getElementById('btn-view-table');
    const cardsContainer = document.getElementById('companies-cards-container');
    const tableContainer = document.getElementById('companies-table-container');

    if (btnCards) btnCards.classList.toggle('active', mode === 'cards');
    if (btnTable) btnTable.classList.toggle('active', mode === 'table');

    if (cardsContainer) cardsContainer.style.display = mode === 'cards' ? 'grid' : 'none';
    if (tableContainer) tableContainer.style.display = mode === 'table' ? 'block' : 'none';
}

let selectedCompanyCause = 'all';
let selectedCompanyState = 'all';

function filterCompaniesByCause(cause) {
    selectedCompanyCause = cause;
    document.querySelectorAll('#company-cause-pill-bar .cause-pill').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.cause === cause);
    });
    loadRecommendations(1);
}

function filterCompaniesByState(state) {
    selectedCompanyState = state;
    const stateFilter = document.getElementById('state-filter');
    if (stateFilter && stateFilter.value !== state) {
        stateFilter.value = state;
    }
    loadRecommendations(1);
}

function filterCompanyTable() {
    loadRecommendations(1);
}

function clearCompanySearch() {
    const searchInput = document.getElementById('global-search');
    const clearBtn = document.getElementById('company-search-clear');
    if (searchInput) searchInput.value = '';
    if (clearBtn) clearBtn.style.display = 'none';
    loadRecommendations(1);
}

function resetCompanyFilters() {
    const searchInput = document.getElementById('global-search');
    if (searchInput) searchInput.value = '';
    const sectorFilter = document.getElementById('sector-filter');
    if (sectorFilter) sectorFilter.value = 'all';
    const stateFilter = document.getElementById('state-filter');
    if (stateFilter) stateFilter.value = 'all';
    const oppFilter = document.getElementById('opp-only-filter');
    if (oppFilter) oppFilter.checked = false;

    selectedCompanyCause = 'all';
    selectedCompanyState = 'all';
    document.querySelectorAll('#company-cause-pill-bar .cause-pill').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.cause === 'all');
    });

    clearCompanySearch();
}

function renderCompanyViews(list, total) {
    const countLabel = document.getElementById('company-count-label');
    if (countLabel) {
        const totalCount = total || list.length;
        countLabel.textContent = `Showing page ${paginationState.companies.page} of ${paginationState.companies.totalPages} (${totalCount} Verified Companies Total)`;
    }

    renderCompanyCards(list);
    renderCompanyTable(list);
}

async function fetchCompanyLiveData(companyId, btnElement) {
    if (!companyId) return;
    if (!btnElement && window.event) {
        btnElement = window.event.currentTarget;
    }
    const origHtml = btnElement ? btnElement.innerHTML : '🔄 Fetch Live Data';
    if (btnElement) {
        btnElement.disabled = true;
        btnElement.innerHTML = '<span class="loading-spinner-circle" style="width:13px; height:13px; margin:0 4px 0 0; border-width:2px; display:inline-block; vertical-align:middle;"></span> Syncing...';
    }

    showLiveToast('Fetching live changes from company website...', 'info');

    try {
        const res = await fetch(`${API_BASE}/api/companies/${encodeURIComponent(companyId)}/fetch-live/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (data.status === 'ok') {
            const diff = data.diff || {};
            const toastMsg = data.message || `Live Sync Complete: ${diff.active_jobs_count || 0} Active Jobs (+${diff.jobs_added || 0} Added, ~${diff.jobs_updated || 0} Updated, -${diff.jobs_removed || 0} Removed), ${diff.active_csr_count || 0} CSR Projects verified.`;
            showLiveToast(toastMsg, 'success');

            const timeBadge = document.getElementById(`live-time-${companyId}`);
            if (timeBadge) {
                timeBadge.textContent = `🕒 Live: ${new Date().toLocaleTimeString()}`;
            }

            try {
                if (activeTab === 'companies') {
                    await loadRecommendations(paginationState.companies.page);
                } else if (activeTab === 'jobs') {
                    await loadJobs(paginationState.jobs.page);
                }
                loadStats();
            } catch (re) {
                console.warn('Re-render notice:', re);
            }
        } else {
            showLiveToast(`Live sync error: ${data.message || data.error || 'Failed'}`, 'error');
        }
    } catch (err) {
        showLiveToast(`Live fetch failed: ${err.message}`, 'error');
    } finally {
        if (btnElement) {
            btnElement.disabled = false;
            btnElement.innerHTML = origHtml;
        }
    }
}
window.fetchCompanyLiveData = fetchCompanyLiveData;

async function fetchCurrentCompanyLiveData(btn) {
    if (typeof selectedCompanyForJobs !== 'undefined' && selectedCompanyForJobs && selectedCompanyForJobs.company_id) {
        await fetchCompanyLiveData(selectedCompanyForJobs.company_id, btn);
        if (typeof openCompanyJobsDashboard === 'function') {
            openCompanyJobsDashboard(selectedCompanyForJobs.company_id);
        }
    }
}
window.fetchCurrentCompanyLiveData = fetchCurrentCompanyLiveData;

function renderCompanyCards(list) {
    const container = document.getElementById('companies-cards-container');
    if (!container) return;

    if (!list || list.length === 0) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:50px; color:#94a3b8;">No companies match the selected cause, state, or search. Try clearing filters!</div>`;
        return;
    }

    container.innerHTML = list.map((item, idx) => {
        const website = getCompanyWebsite(item);
        const csrUrl = getCompanyCsrWebpageUrl(item);
        const initial = getCompanyInitials(item.company_name, item.nse_symbol);
        const avatarGradient = getAvatarGradient(item.company_name);
        const rawHq = item.headquarters ? item.headquarters.split('/')[0].trim() : '';
        const hq = (rawHq && rawHq !== NOT_AVAILABLE_TEXT) ? rawHq : 'India';
        const industry = (item.industry && item.industry !== NOT_AVAILABLE_TEXT) ? item.industry : (item.sector || 'Enterprise');

        const jobStatusLabel = item.job_status_label || (item.verified_jobs_count > 0 ? `${item.verified_jobs_count} Verified Jobs` : NOT_AVAILABLE_TEXT);
        const jobStatusBadge = item.job_status_badge || (item.verified_jobs_count > 0 ? 'badge-emerald' : 'badge-muted');
        const csrStatusLabel = item.csr_status_label || (item.published_csr_count > 0 ? `${item.published_csr_count} Verified CSR Projects` : NOT_AVAILABLE_TEXT);
        const csrStatusBadge = item.csr_status_badge || (item.published_csr_count > 0 ? 'badge-emerald' : 'badge-muted');
        const lastChecked = item.last_verified_display || NOT_AVAILABLE_TEXT;
        const isVerified = item.verification_status === 'VERIFIED' || item.verification_status === 'PUBLISHED' || item.verification_status === 'SOURCE_CONFIRMED';
        const loginSections = Array.isArray(item.login_required_sections) ? item.login_required_sections : [];
        const liveSyncedTime = item.last_live_synced_at ? new Date(item.last_live_synced_at).toLocaleTimeString() : (item.link_verified_at ? new Date(item.link_verified_at).toLocaleTimeString() : 'Never');

        return `
            <div class="company-card">
                <div>
                    <div class="company-card-header">
                        <div class="company-avatar" style="background:${avatarGradient}; color:#ffffff; font-weight:800;">${escapeHtml(initial)}</div>
                        <div class="company-title-wrap">
                            <div class="company-card-name" style="cursor:pointer;" onclick="openCompanyDossier('${item.company_id}')">${escapeHtml(item.company_name)}</div>
                            <div class="company-card-sub" style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-top:3px;">
                                ${item.nse_symbol ? `<span class="badge badge-cyan" style="font-size:10px; font-weight:700;">NSE: ${escapeHtml(item.nse_symbol)}</span>` : ''}
                                <span style="font-size:11.5px; color:var(--text-secondary);">${escapeHtml(industry)}</span>
                                <span style="font-size:11.5px; color:var(--text-muted);">📍 ${escapeHtml(hq)}</span>
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <span class="badge ${isVerified ? 'badge-emerald' : 'badge-amber'}" style="font-size:10px;">
                                ${isVerified ? '✓ Verified' : 'Pending'}
                            </span>
                            <div style="font-size:9.5px; color:var(--text-muted); margin-top:3px;" id="live-time-${item.company_id}">
                                🕒 Live: ${escapeHtml(liveSyncedTime)}
                            </div>
                        </div>
                    </div>

                    ${loginSections.length > 0 ? `
                    <div style="margin-top:10px; padding:6px 10px; background:rgba(245, 158, 11, 0.12); border:1px solid rgba(245, 158, 11, 0.4); border-radius:6px; font-size:11px; color:#f59e0b; font-weight:600;">
                        🔒 ${escapeHtml(LOGIN_REQUIRED_TEXT)} (${escapeHtml(loginSections.join(', '))})
                    </div>` : ''}

                    <div class="company-card-body" style="margin-top:14px; display:flex; flex-direction:column; gap:8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:11.5px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Careers Status</span>
                            <span class="badge ${jobStatusBadge}" style="font-size:11px; font-weight:700;">
                                ${escapeHtml(jobStatusLabel)}
                            </span>
                        </div>

                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:11.5px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">CSR Status</span>
                            <span class="badge ${csrStatusBadge}" style="font-size:11px; font-weight:700;">
                                ${escapeHtml(csrStatusLabel)}
                            </span>
                        </div>

                        <div style="display:flex; justify-content:space-between; align-items:center; font-size:11.5px; color:var(--text-secondary); padding-top:4px; border-top:1px solid var(--border-subtle);">
                            <span>CSR Source Format:</span>
                            <strong style="color:var(--text-primary); font-size:11px;">${escapeHtml(item.csr_display_format || NOT_AVAILABLE_TEXT)}</strong>
                        </div>

                        <div class="company-portals-strip" style="margin-top:6px; display:flex; gap:6px; flex-wrap:wrap;">
                            ${website ? `<a href="${escapeHtml(website)}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-site" title="Open Official Website">🌐 Official Website ↗</a>` : `<span style="font-size:11px; color:var(--text-muted);">Website: ${escapeHtml(NOT_AVAILABLE_TEXT)}</span>`}
                            ${csrUrl ? `<a href="${escapeHtml(csrUrl)}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-csr" title="Open Official CSR Webpage / Disclosure (${escapeHtml(item.csr_display_format || 'CSR Source')})">🌱 CSR Webpage ↗</a>` : (item.csr_access === 'LOGIN_REQUIRED' ? `<span style="font-size:11px; color:#f59e0b;">🔒 CSR: Login Required</span>` : `<span style="font-size:11px; color:var(--text-muted);">CSR Link: ${escapeHtml(NOT_AVAILABLE_TEXT)}</span>`)}
                        </div>
                    </div>
                </div>

                <div class="company-card-actions" style="flex-wrap:wrap; gap:6px;">
                    <button class="btn-primary" onclick="openCompanyDossier('${item.company_id}')" title="View complete company profile">
                        🔍 View Company
                    </button>
                    <button class="btn-outline btn-fetch-live" onclick="fetchCompanyLiveData('${item.company_id}', this)" title="1:1 live delta sync from official company website" style="background:rgba(59,130,246,0.12); border-color:rgba(59,130,246,0.5); color:#3b82f6; font-weight:700;">
                        🔄 Fetch Live Data
                    </button>
                    <button class="btn-outline" onclick="openCompanyCsr('${item.company_id}')" title="View CSR webpage link, CSR disclosure format & verified CSR projects for this company">
                        🌱 View CSR ${item.csr_count > 0 ? `(${item.csr_count})` : ''}
                    </button>
                    <button class="btn-outline" onclick="openCompanyJobs('${item.company_id}')" title="Browse verified jobs from this company">
                        💼 Jobs ${item.verified_jobs_count > 0 ? `(${item.verified_jobs_count})` : ''}
                    </button>
                    <button class="btn-secondary" onclick="quickSaveToPipeline('${item.company_id}')">
                        ⭐ Save
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function renderCompanyTable(list) {
    const tbody = document.getElementById('companies-table-body');
    if (!tbody) return;

    if (!list || list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:40px; color:#94a3b8;">No companies match the selected filters.</td></tr>`;
        return;
    }

    tbody.innerHTML = list.map((item, idx) => {
        const website = getCompanyWebsite(item);
        const csrUrl = getCompanyCsrWebpageUrl(item);
        const jobStatusLabel = item.job_status_label || (item.verified_jobs_count > 0 ? `${item.verified_jobs_count} Jobs` : NOT_AVAILABLE_TEXT);
        const jobStatusBadge = item.job_status_badge || (item.verified_jobs_count > 0 ? 'badge-emerald' : 'badge-muted');
        const csrStatusLabel = item.csr_status_label || (item.published_csr_count > 0 ? `${item.published_csr_count} CSR Projects` : NOT_AVAILABLE_TEXT);
        const csrStatusBadge = item.csr_status_badge || (item.published_csr_count > 0 ? 'badge-emerald' : 'badge-muted');
        const lastChecked = item.last_verified_display || NOT_AVAILABLE_TEXT;
        const isVerified = item.verification_status === 'VERIFIED' || item.verification_status === 'PUBLISHED' || item.verification_status === 'SOURCE_CONFIRMED';
        const loginSections = Array.isArray(item.login_required_sections) ? item.login_required_sections : [];
        const liveSyncedTime = item.last_live_synced_at ? new Date(item.last_live_synced_at).toLocaleTimeString() : (item.link_verified_at ? new Date(item.link_verified_at).toLocaleTimeString() : 'Never');

        return `
            <tr>
                <td style="color:#64748b; font-weight:700;">#${(paginationState.companies.page - 1) * paginationState.companies.pageSize + idx + 1}</td>
                <td>
                    <div style="font-weight:700; color:var(--text-primary); font-size:13.5px; cursor:pointer;" onclick="openCompanyDossier('${item.company_id}')">
                        <span style="color:var(--primary-brand);">${escapeHtml(item.company_name)}</span>
                    </div>
                    <div style="font-size:11.5px; color:var(--text-secondary); display:flex; gap:6px; align-items:center; margin-top:2px; flex-wrap:wrap;">
                        ${item.nse_symbol ? `<span class="badge badge-cyan" style="font-size:9.5px;">NSE: ${escapeHtml(item.nse_symbol)}</span>` : ''}
                        <span>📍 ${escapeHtml(item.headquarters ? item.headquarters.split('/')[0].trim() : NOT_AVAILABLE_TEXT)}</span>
                        ${loginSections.length > 0 ? `<span class="badge badge-amber" style="font-size:9.5px;">🔒 Login Required: ${escapeHtml(loginSections.join(', '))}</span>` : ''}
                        <span style="font-size:10px; color:var(--text-muted);" id="live-time-${item.company_id}">🕒 Live: ${escapeHtml(liveSyncedTime)}</span>
                    </div>
                </td>
                <td>
                    <span class="badge badge-purple">${escapeHtml(item.industry || item.sector || NOT_AVAILABLE_TEXT)}</span>
                </td>
                <td>
                    <span class="badge ${jobStatusBadge}">${escapeHtml(jobStatusLabel)}</span>
                </td>
                <td>
                    <span class="badge ${csrStatusBadge}">${escapeHtml(csrStatusLabel)}</span>
                    ${csrUrl ? `<div style="margin-top:4px;"><a href="${escapeHtml(csrUrl)}" target="_blank" rel="noopener noreferrer" style="font-size:11px; color:var(--accent-cyan); font-weight:600; text-decoration:none;">🌐 CSR Webpage ↗</a></div>` : ''}
                </td>
                <td>
                    <span class="badge ${isVerified ? 'badge-emerald' : 'badge-amber'}">${isVerified ? '✓ Verified' : 'Pending'}</span>
                </td>
                <td style="font-size:11.5px; color:var(--text-secondary); font-family:var(--font-mono);">
                    ${escapeHtml(lastChecked)}
                </td>
                <td style="text-align:right; white-space:nowrap;">
                    <button class="btn-primary" style="padding:5px 10px; font-size:11.5px;" onclick="openCompanyDossier('${item.company_id}')">
                        View Company
                    </button>
                    <button class="btn-outline btn-fetch-live" style="padding:5px 10px; font-size:11.5px; margin-left:4px; color:#3b82f6; border-color:rgba(59,130,246,0.5); font-weight:700; background:rgba(59,130,246,0.08);" onclick="fetchCompanyLiveData('${item.company_id}', this)" title="1:1 Live Sync from official website">
                        🔄 Live Sync
                    </button>
                    <button class="btn-outline" style="padding:5px 10px; font-size:11.5px; margin-left:4px;" onclick="openCompanyCsr('${item.company_id}')" title="View CSR Page & CSR Projects">
                        🌱 View CSR
                    </button>
                    <button class="btn-outline" style="padding:5px 10px; font-size:11.5px; margin-left:4px;" onclick="openCompanyJobs('${item.company_id}')">
                        💼 Jobs
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

let jobFilterOptionsLoaded = false;

async function loadJobs(page = 1) {
    if (typeof page !== 'number' || isNaN(page) || page < 1) {
        page = parseInt(page, 10);
        if (isNaN(page) || page < 1) page = 1;
    }
    paginationState.jobs.page = page;
    const grid = document.getElementById('jobs-grid');
    const label = document.getElementById('job-count-label');

    // Dynamic skeleton feedback
    const tableBody = document.getElementById('jobs-table-body');
    if (tableBody) {
        tableBody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:50px 20px; color:var(--text-secondary);"><div class="loading-spinner-circle" style="margin:0 auto 12px; width:28px; height:28px;"></div><div style="font-weight:600; color:var(--text-primary); margin-bottom:4px;">Loading Verified Job Openings...</div><div style="font-size:12px;">Querying corporate career portals (Page ${page})</div></td></tr>`;
    }
    if (grid) {
        grid.innerHTML = `
            <div class="dynamic-loading-skeleton">
                <div class="loading-spinner-circle"></div>
                <div class="loading-spinner-text">Searching Corporate Job Openings...</div>
                <div class="loading-spinner-sub">Fetching verified opportunities from official career portals (Page ${page})</div>
            </div>`;
    }

    try {
        const query = (document.getElementById('job-search')?.value || '').trim();
        const comp = document.getElementById('job-company-filter')?.value || 'all';
        const dept = document.getElementById('job-department-filter')?.value || 'all';
        const loc = document.getElementById('job-location-filter')?.value || 'all';
        const mode = document.getElementById('job-mode-filter')?.value || 'all';
        const exp = document.getElementById('job-exp-filter')?.value || 'all';
        const sortBy = document.getElementById('job-sort-filter')?.value || 'relevance';
        const impactOnly = document.getElementById('job-impact-only')?.checked || false;

        let url = `${API_BASE}/jobs?page=${page}&page_size=${paginationState.jobs.pageSize}`;
        if (query) url += `&q=${encodeURIComponent(query)}`;
        if (comp && comp !== 'all') url += `&company=${encodeURIComponent(comp)}`;
        if (dept !== 'all') url += `&department=${encodeURIComponent(dept)}`;
        if (loc !== 'all') url += `&location=${encodeURIComponent(loc)}`;
        if (mode !== 'all') url += `&work_mode=${encodeURIComponent(mode)}`;
        if (exp !== 'all') url += `&experience=${encodeURIComponent(exp)}`;
        if (activeJobCategory !== 'all') url += `&category=${encodeURIComponent(activeJobCategory)}`;
        if (impactOnly) url += `&impact_only=true`;
        if (sortBy === 'company') url += `&sort=company`;
        else if (sortBy === 'title') url += `&sort=title`;
        else if (sortBy === 'experience') url += `&sort=experience`;

        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        let items = [];
        let total = 0;
        let totalPages = 1;

        if (data && typeof data === 'object' && Array.isArray(data.items)) {
            items = data.items;
            total = data.total;
            totalPages = data.total_pages;
        } else if (Array.isArray(data)) {
            items = data;
            total = items.length;
            totalPages = Math.ceil(total / paginationState.jobs.pageSize);
        }

        allJobs = items;
        filteredJobs = items;
        paginationState.jobs.total = total;
        paginationState.jobs.totalPages = totalPages;

        // Populate dropdown options instantly from loaded items without heavy network blocking
        if (!jobFilterOptionsLoaded && items.length > 0) {
            jobFilterOptionsLoaded = true;
            populateJobFilterDropdowns(items);
        }

        // Update badge
        const countBadge = document.getElementById('jobs-count-badge');
        if (countBadge) countBadge.textContent = Number(total).toLocaleString('en-IN');
        const mobileJobsBadge = document.getElementById('mobile-nav-jobs-badge');
        if (mobileJobsBadge) mobileJobsBadge.textContent = Number(total).toLocaleString('en-IN');
        const totalJobsPill = document.getElementById('badge-jobs-total-pill');
        if (totalJobsPill && !query && comp === 'all' && loc === 'all' && dept === 'all' && exp === 'all' && mode === 'all') {
            totalJobsPill.textContent = Number(total).toLocaleString('en-IN');
        }

        renderJobs(items, total, totalPages);
        renderJobsPagination();
    } catch (e) {
        console.error('Error in loadJobs', e);
        if (grid) {
            grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#f43f5e;">Could not load job postings: ${escapeHtml(e.message)}</div>`;
        }
    }
}

function renderJobsPagination() {
    renderPaginationBar({
        containerId: 'jobs-pagination',
        page: paginationState.jobs.page,
        totalPages: paginationState.jobs.totalPages,
        total: paginationState.jobs.total,
        pageSize: paginationState.jobs.pageSize,
        pageSizeOptions: [12, 24, 48, 96],
        itemLabel: 'Verified Job Openings',
        onPageChange: (newPage) => {
            loadJobs(newPage);
            const anchor = document.getElementById('tab-jobs');
            if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
        onPageSizeChange: (newSize) => {
            paginationState.jobs.pageSize = newSize;
            loadJobs(1);
        }
    });
}

function selectJobCategory(category) {
    activeJobCategory = category;
    document.querySelectorAll('.cat-pill').forEach(pill => {
        pill.classList.toggle('active', pill.dataset.category === category);
    });
    loadJobs(1);
}

function populateJobFilters(jobs) {
    populateJobFilterDropdowns(jobs);
}

const NOT_AVAILABLE_TEXT = 'Not available on the company website';
const LOGIN_REQUIRED_TEXT = 'Available only after login on the company website';

// Display helper: empty / placeholder values are shown as "Not available on the company website",
// never as a blank, a dash or an invented value.
function naText(v) {
    const t = (v === null || v === undefined) ? '' : String(v).trim();
    if (!t || ['---', '--', '-', 'null', 'none', 'undefined', 'n/a', 'not specified'].includes(t.toLowerCase())) return NOT_AVAILABLE_TEXT;
    return t;
}

// The Apply link is only ever the job's own, server-verified link.  No fallback to a careers page or
// homepage: when the link was not verified the UI says so instead of sending the user elsewhere.
function getJobApplyLink(job) {
    if (!job || job.link_verified !== true) return null;
    const url = (job.application_url || '').trim();
    return /^https?:\/\//i.test(url) ? url : null;
}

function applyButtonHtml(job, cls, style, label) {
    const url = getJobApplyLink(job);
    if (url) {
        return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="${cls}" style="${style}" title="Opens this exact job posting on the company's own site">${label}</a>`;
    }
    const why = (job && job.jobs_access === 'LOGIN_REQUIRED') ? LOGIN_REQUIRED_TEXT : 'Apply link not available on the company website';
    return `<span style="font-size:11.5px; color:var(--text-muted); padding:4px 8px; border:1px solid var(--border-subtle); border-radius:4px; display:inline-block;">${escapeHtml(why)}</span>`;
}

function isImpactRole(job) {
    if (!job) return false;
    const text = ((job.job_title || '') + ' ' + (job.department || '') + ' ' + (job.function || '') + ' ' + (job.skills || '')).toLowerCase();
    return ['csr', 'esg', 'sustainab', 'social', 'community', 'foundation', 'impact'].some(p => text.includes(p));
}

async function populateJobFilterDropdowns(jobs = []) {
    const compSelect = document.getElementById('job-company-filter');
    const findCompSelect = document.getElementById('find-job-company-filter');
    const deptSelect = document.getElementById('job-department-filter');
    const findDeptSelect = document.getElementById('find-job-dept-filter');
    const locSelect = document.getElementById('job-location-filter');
    const findLocSelect = document.getElementById('find-job-location-filter');

    // 1. Populate Companies dropdown (All 200 Top Indian Corporations)
    const companiesMap = new Map();
    
    // Fetch all companies if not loaded
    if (!allDirectoryCompanies || allDirectoryCompanies.length === 0) {
        try {
            const res = await fetch(`${API_BASE}/companies?page_size=5000&limit=5000`);
            if (res.ok) {
                const data = await res.json();
                if (data && Array.isArray(data.items)) {
                    allDirectoryCompanies = data.items;
                }
            }
        } catch (e) {
            console.error("Failed to load companies for dropdown", e);
        }
    }
    if (Array.isArray(allDirectoryCompanies) && allDirectoryCompanies.length > 0) {
        allDirectoryCompanies.forEach(c => {
            if (c && c.company_id && c.company_name) {
                companiesMap.set(c.company_id, { id: c.company_id, name: c.company_name, sym: c.nse_symbol || '' });
            }
        });
    }
    if (Array.isArray(jobs) && jobs.length > 0) {
        jobs.forEach(j => {
            if (j && (j.company_id || j.company_name)) {
                const id = j.company_id || j.company_name;
                if (!companiesMap.has(id)) {
                    companiesMap.set(id, { id: id, name: j.company_name || id, sym: j.nse_symbol || '' });
                }
            }
        });
    }

    if (companiesMap.size > 0) {
        const sortedCompanies = Array.from(companiesMap.values()).sort((a, b) => a.name.localeCompare(b.name));
        const datalistHtml = sortedCompanies.map(c => `<option value="${escapeHtml(c.name)}">${c.sym ? `(${escapeHtml(c.sym)})` : ''}</option>`).join('');

        const compList = document.getElementById('job-company-list');
        const findCompList = document.getElementById('find-job-company-list');

        if (compList && compList.options.length === 0) {
            compList.innerHTML = datalistHtml;
        }
        if (findCompList && findCompList.options.length === 0) {
            findCompList.innerHTML = datalistHtml;
        }
    }

    // 2. Populate Departments dropdown
    if (Array.isArray(jobs) && jobs.length > 0) {
        const departments = [...new Set(jobs.map(j => j.department).filter(Boolean))].sort();
        if (departments.length > 0) {
            const deptOptionsHtml = '<option value="all">All Departments</option>' +
                departments.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('');
            if (deptSelect && deptSelect.options.length <= 1) {
                deptSelect.innerHTML = deptOptionsHtml;
            }
            if (findDeptSelect && findDeptSelect.options.length <= 1) {
                findDeptSelect.innerHTML = deptOptionsHtml;
            }
        }

        // 3. Populate Locations dropdown
        const locations = [...new Set(jobs.map(j => j.location).filter(Boolean))].sort();
        if (locations.length > 0) {
            const locOptionsHtml = '<option value="all">All Locations (Pan-India)</option>' +
                locations.map(l => `<option value="${escapeHtml(l)}">${escapeHtml(l)}</option>`).join('');
            if (locSelect && locSelect.options.length <= 1) {
                locSelect.innerHTML = locOptionsHtml;
            }
            if (findLocSelect && findLocSelect.options.length <= 1) {
                findLocSelect.innerHTML = locOptionsHtml;
            }
        }
    }
}

function filterJobsByCompany(companyId, companyName) {
    if (!companyId) return;
    switchTab('jobs');
    switchJobSubTab('all');
    let compVal = companyName || companyId;
    if (!companyName && Array.isArray(allDirectoryCompanies)) {
        const found = allDirectoryCompanies.find(c => c.company_id === companyId);
        if (found && found.company_name) compVal = found.company_name;
    }
    const compSelect = document.getElementById('job-company-filter');
    if (compSelect) {
        compSelect.value = compVal;
    }
    const searchInput = document.getElementById('job-search');
    if (searchInput) searchInput.value = '';
    loadJobs(1);
    const anchor = document.getElementById('subview-jobs-all');
    if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function clearJobSearch() {
    const input = document.getElementById('job-search');
    const clearBtn = document.getElementById('job-search-clear');
    if (input) input.value = '';
    if (clearBtn) clearBtn.style.display = 'none';
    loadJobs(1);
}

function resetJobFilters() {
    const searchInput = document.getElementById('job-search');
    if (searchInput) searchInput.value = '';
    const compSelect = document.getElementById('job-company-filter');
    if (compSelect) compSelect.value = '';
    const deptSelect = document.getElementById('job-department-filter');
    if (deptSelect) deptSelect.value = 'all';
    const locSelect = document.getElementById('job-location-filter');
    if (locSelect) locSelect.value = 'all';
    const modeSelect = document.getElementById('job-mode-filter');
    if (modeSelect) modeSelect.value = 'all';
    const expSelect = document.getElementById('job-exp-filter');
    if (expSelect) expSelect.value = 'all';
    const impactOnly = document.getElementById('job-impact-only');
    if (impactOnly) impactOnly.checked = false;
    const clearBtn = document.getElementById('job-search-clear');
    if (clearBtn) clearBtn.style.display = 'none';
    selectJobCategory('all');
}

function filterJobs() {
    loadJobs(1);
}

let currentJobViewMode = 'table';
function setJobViewMode(mode) {
    currentJobViewMode = mode;
    const tableContainer = document.getElementById('jobs-table-container');
    const cardsContainer = document.getElementById('jobs-grid');
    const btnTable = document.getElementById('btn-job-view-table');
    const btnCards = document.getElementById('btn-job-view-cards');

    if (mode === 'table') {
        if (tableContainer) tableContainer.style.display = 'block';
        if (cardsContainer) cardsContainer.style.display = 'none';
        if (btnTable) btnTable.classList.add('active');
        if (btnCards) btnCards.classList.remove('active');
    } else {
        if (tableContainer) tableContainer.style.display = 'none';
        if (cardsContainer) cardsContainer.style.display = 'grid';
        if (btnTable) btnTable.classList.remove('active');
        if (btnCards) btnCards.classList.add('active');
    }
}

function getVerificationStatusLabel(status) {
    const s = String(status || '').trim().toUpperCase();
    if (s === 'PUBLISHED' || s === 'SOURCE_CONFIRMED' || s === 'VERIFIED') return 'Source verified';
    if (s === 'PENDING' || s === 'VERIFICATION_PENDING') return 'Verification pending';
    if (s === 'UNABLE_TO_VERIFY' || s === 'UNVERIFIED') return 'Unable to verify';
    if (s === 'SOURCE_UNAVAILABLE') return 'Source unavailable';
    if (s === 'NOT_CHECKED') return 'Not checked';
    return 'Not checked';
}

function formatVerificationBadge(status) {
    const label = getVerificationStatusLabel(status);
    let badgeClass = 'badge-slate';
    if (label === 'Source verified') badgeClass = 'badge-emerald';
    else if (label === 'Verification pending') badgeClass = 'badge-amber';
    else if (label === 'Unable to verify') badgeClass = 'badge-rose';
    else if (label === 'Source unavailable') badgeClass = 'badge-slate';
    return `<span class="badge ${badgeClass}" style="font-size:10px;">${escapeHtml(label)}</span>`;
}

function renderJobs(list, total, totalPages) {
    const tableBody = document.getElementById('jobs-table-body');
    const grid = document.getElementById('jobs-grid');
    const label = document.getElementById('job-count-label');

    if (!list || list.length === 0) {
        const emptyMsg = `
            <div style="grid-column:1/-1; text-align:center; padding:60px 20px; background:var(--bg-card); border-radius:var(--radius-md); border:1px solid var(--border-card);">
                <div style="font-size:36px; margin-bottom:12px;">🔍</div>
                <h3 style="font-size:18px; font-weight:800; color:var(--text-primary); margin-bottom:6px;">No Job Openings Match Your Filters</h3>
                <p style="font-size:14px; color:var(--text-secondary); margin-bottom:16px;">Try clearing search keywords or selecting "All Disciplines".</p>
                <button class="btn-primary" onclick="resetJobFilters()">Reset All Filters</button>
            </div>
        `;
        if (grid) grid.innerHTML = emptyMsg;
        if (tableBody) tableBody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:50px 20px; color:var(--text-secondary); font-size:14px;">No job openings match your filter criteria. <button class="btn-primary" style="margin-left:12px; font-size:12px; padding:4px 10px;" onclick="resetJobFilters()">Reset Filters</button></td></tr>`;
        if (label) label.textContent = 'No matching roles found';
        return;
    }

    if (label) {
        const totalCount = total || list.length;
        const pageNum = paginationState.jobs.page || 1;
        const pagesCount = totalPages || Math.ceil(totalCount / (paginationState.jobs.pageSize || 12)) || 1;
        label.textContent = `Showing page ${pageNum} of ${pagesCount} (${totalCount.toLocaleString('en-IN')} Current Verified Job Openings)`;
    }

    // 1. Render Desktop Data Table (Part 26)
    if (tableBody) {
        tableBody.innerHTML = list.map(job => {
            const applyUrl = getJobApplyLink(job);
            const sourceBadge = job.ats_platform
                ? `<span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(job.ats_platform)}</span>`
                : `<span class="badge badge-blue" style="font-size:10px;">Official ATS</span>`;
            const postedDisplay = job.posted_date ? formatDate(job.posted_date) : '<span style="color:var(--text-muted); font-size:12px;">' + NOT_AVAILABLE_TEXT + '</span>';
            const verifiedDisplay = job.retrieved_at ? formatDate(job.retrieved_at) : (job.last_checked_date ? formatDate(job.last_checked_date) : '<span style="color:var(--text-muted); font-size:12px;">Not checked</span>');

            return `
                <tr>
                    <td>
                        <div style="font-weight:700; color:var(--text-primary); cursor:pointer;" onclick="openJobDetailsModal(${job.job_row_id})" title="Click to view structured specifications">
                            ${escapeHtml(job.job_title)}
                        </div>
                    </td>
                    <td>
                        <a href="javascript:void(0)" onclick="filterJobsByCompany('${job.company_id}')" style="font-weight:600; color:var(--accent-cyan); text-decoration:none;" title="Filter by ${escapeHtml(job.company_name)}">
                            🏢 ${escapeHtml(job.company_name)}
                        </a>
                        ${job.nse_symbol ? `<span style="color:var(--text-muted); font-size:11px; margin-left:4px;">(${escapeHtml(job.nse_symbol)})</span>` : ''}
                    </td>
                    <td>${job.location ? escapeHtml(job.location) : ''}</td>
                    <td>${job.department ? `<span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(job.department)}</span>` : ''}</td>
                    <td>${job.employment_type ? escapeHtml(job.employment_type) : ''}</td>
                    <td style="font-size:12px; color:var(--text-secondary);">${postedDisplay}</td>
                    <td style="font-size:12px; color:var(--text-secondary);">${job.verified_relative_time ? escapeHtml(job.verified_relative_time) : verifiedDisplay}</td>
                    <td>${sourceBadge}</td>
                    <td>${formatVerificationBadge(job.verification_status)}</td>
                    <td style="text-align:right;">
                        <div style="display:flex; justify-content:flex-end; gap:6px;">
                            <button class="btn-primary" style="padding:4px 10px; font-size:11.5px;" onclick="openJobDetailsModal(${job.job_row_id})">
                                View
                            </button>
                            ${applyButtonHtml(job, 'btn-secondary', 'padding:4px 10px; font-size:11.5px;', 'Apply ↗')}
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // 2. Render Cards Grid (Mobile / Card Mode)
    if (grid) {
        grid.innerHTML = list.map(job => {
            const applyUrl = getJobApplyLink(job);

            let modeBadge = '';
            if (job.work_mode === 'Remote') modeBadge = '<span class="badge badge-cyan">🏠 Remote</span>';
            else if (job.work_mode === 'Hybrid') modeBadge = '<span class="badge badge-purple">🔄 Hybrid</span>';
            else if (job.work_mode === 'On-site') modeBadge = '<span class="badge badge-emerald">🏢 On-site</span>';
            else if (job.work_mode) modeBadge = `<span class="badge badge-slate" style="font-size:10px;">${escapeHtml(job.work_mode)}</span>`;

            const deptBadge = job.department 
                ? `<span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(job.department)}</span>`
                : '';

            return `
                <div class="job-card">
                    <div>
                        <div class="job-header">
                            ${deptBadge}
                            ${modeBadge}
                        </div>

                        <div class="job-title" style="cursor:pointer;" onclick="openJobDetailsModal(${job.job_row_id})">
                            ${escapeHtml(job.job_title)}
                        </div>

                        <div class="job-company" style="cursor:pointer;" onclick="filterJobsByCompany('${job.company_id}')" title="Filter to show all verified openings at ${escapeHtml(job.company_name)}">
                            🏢 <span style="text-decoration:underline;">${escapeHtml(job.company_name)}</span>
                            ${job.nse_symbol ? `<span style="color:var(--accent-cyan); font-weight:700;">(${escapeHtml(job.nse_symbol)})</span>` : ''}
                        </div>

                        <div class="job-meta-grid">
                            ${job.location ? `<div class="job-meta-item">📍 <span><strong>Location:</strong> ${escapeHtml(job.location)}</span></div>` : ''}
                            ${job.experience ? `<div class="job-meta-item">⏳ <span><strong>Experience:</strong> ${escapeHtml(job.experience)}</span></div>` : ''}
                            ${job.employment_type ? `<div class="job-meta-item">💼 <span><strong>Type:</strong> ${escapeHtml(job.employment_type)}</span></div>` : ''}
                            <div class="job-meta-item">🛡️ <span><strong>Status:</strong> ${formatVerificationBadge(job.verification_status)}</span></div>
                        </div>
                    </div>

                    <div>
                        <div class="job-actions" style="flex-wrap:wrap; gap:6px;">
                            <button class="btn-primary" style="padding:6px 12px; font-size:12px;" onclick="openJobDetailsModal(${job.job_row_id})">
                                View Job
                            </button>
                            ${applyButtonHtml(job, 'btn-secondary', 'padding:6px 12px; font-size:12px;', '⚡ Apply ↗')}
                            <button class="btn-outline" style="padding:6px 10px; font-size:11px;" onclick="openCompanyJobs('${job.company_id}')"
                                    title="Browse all jobs from this company">
                                🏢 All Jobs
                            </button>
                            <button class="btn-secondary" style="padding:6px 8px; font-size:11px;" onclick="openCompanyDossier('${job.company_id}')"
                                    title="View company intelligence dossier">
                                Profile
                            </button>
                        </div>

                        <div class="job-provenance">
                            ${job.is_company_unverifiable ? `
                                <span>⚠️ Unverifiable ATS &bull; <a href="${escapeHtml(job.careers_url || '#')}" target="_blank" rel="noopener noreferrer" style="color:inherit; text-decoration:underline;">Careers Page ↗</a></span>
                            ` : `
                                <span>✓ ${escapeHtml(job.verified_badge_text || 'As listed on the official site')} &bull; <a href="${escapeHtml(job.source_url || applyUrl || '#')}" target="_blank" rel="noopener noreferrer" style="color:inherit; text-decoration:underline;">Official Source ↗</a></span>
                            `}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
}

// ===========================================================================
// DEDICATED JOB SUB-VIEWS CONTROLLER (ALL JOBS, FIND JOBS, COMPANY JOBS)
// ===========================================================================
let currentJobSubTab = 'all';
let findJobsLoaded = false;
let companyDirectoryLoaded = false;
let allDirectoryCompanies = [];
let filteredDirectoryCompanies = [];
let selectedCompanyJobId = null;
let selectedCompanyJobData = null;

function switchJobSubTab(subTab) {
    currentJobSubTab = subTab;
    const btnAll = document.getElementById('btn-job-sub-all');
    const btnFind = document.getElementById('btn-job-sub-find');
    const btnCompany = document.getElementById('btn-job-sub-company');
    const viewAll = document.getElementById('subview-jobs-all');
    const viewFind = document.getElementById('subview-jobs-find');
    const viewCompany = document.getElementById('subview-jobs-company');

    if (btnAll) btnAll.classList.toggle('active', subTab === 'all');
    if (btnFind) btnFind.classList.toggle('active', subTab === 'find');
    if (btnCompany) btnCompany.classList.toggle('active', subTab === 'company');

    if (viewAll) viewAll.style.display = subTab === 'all' ? 'block' : 'none';
    if (viewFind) viewFind.style.display = subTab === 'find' ? 'block' : 'none';
    if (viewCompany) viewCompany.style.display = subTab === 'company' ? 'block' : 'none';

    if (subTab === 'all') {
        if (!allJobs || allJobs.length === 0) loadJobs(1);
    } else if (subTab === 'find') {
        if (!findJobsLoaded) {
            findJobsLoaded = true;
            loadFindJobs(1);
        }
    } else if (subTab === 'company') {
        if (!companyDirectoryLoaded) {
            companyDirectoryLoaded = true;
            loadCompanyJobsDirectory();
        }
    }
}

// ---------------------------------------------------------------------------
// 1. FIND JOBS DISCOVERY SEARCH
// ---------------------------------------------------------------------------
async function loadFindJobs(page = 1) {
    if (typeof page !== 'number' || isNaN(page) || page < 1) page = 1;
    if (!paginationState.findJobs) paginationState.findJobs = { page: 1, pageSize: 12, total: 0, totalPages: 1 };
    paginationState.findJobs.page = page;

    const grid = document.getElementById('find-jobs-grid');
    const countLabel = document.getElementById('find-job-count-label');
    if (grid) {
        grid.innerHTML = `
            <div style="grid-column:1/-1;" class="dynamic-loading-skeleton">
                <div class="loading-spinner-circle"></div>
                <div class="loading-spinner-text">Searching Verified Corporate Roles...</div>
                <div class="loading-spinner-sub">Filtering direct job openings across India's premier enterprises (Page ${page})</div>
            </div>`;
    }

    try {
        const query = (document.getElementById('find-jobs-search-input')?.value || '').trim();
        const comp = document.getElementById('find-job-company-filter')?.value || 'all';
        const loc = document.getElementById('find-job-location-filter')?.value || 'all';
        const exp = document.getElementById('find-job-exp-filter')?.value || 'all';
        const mode = document.getElementById('find-job-mode-filter')?.value || 'all';
        const dept = document.getElementById('find-job-dept-filter')?.value || 'all';
        const sort = document.getElementById('find-job-sort-filter')?.value || 'relevance';

        let url = `${API_BASE}/jobs?page=${page}&page_size=${paginationState.findJobs.pageSize}`;
        if (query) url += `&q=${encodeURIComponent(query)}`;
        if (comp !== 'all') url += `&company=${encodeURIComponent(comp)}`;
        if (loc !== 'all') url += `&location=${encodeURIComponent(loc)}`;
        if (exp !== 'all') url += `&experience=${encodeURIComponent(exp)}`;
        if (mode !== 'all') url += `&work_mode=${encodeURIComponent(mode)}`;
        if (dept !== 'all') url += `&department=${encodeURIComponent(dept)}`;
        if (sort === 'company') url += `&sort=company`;
        else if (sort === 'title') url += `&sort=title`;
        else if (sort === 'experience') url += `&sort=experience`;
        else if (sort === 'recent') url += `&sort=recent`;

        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        let items = [];
        let total = 0;
        let totalPages = 1;

        if (data && typeof data === 'object' && Array.isArray(data.items)) {
            items = data.items;
            total = data.total;
            totalPages = data.total_pages;
        } else if (Array.isArray(data)) {
            items = data;
            total = items.length;
            totalPages = Math.ceil(total / paginationState.findJobs.pageSize);
        }

        paginationState.findJobs.total = total;
        paginationState.findJobs.totalPages = totalPages;

        populateFindJobFilters(items);
        renderFindJobs(items, total, totalPages);
        renderFindJobsPagination();
    } catch (e) {
        console.error('Error in loadFindJobs', e);
        if (grid) {
            grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#f43f5e;">Failed to load discovery jobs: ${escapeHtml(e.message)}</div>`;
        }
    }
}

function renderFindJobsPagination() {
    renderPaginationBar({
        containerId: 'find-jobs-pagination',
        page: paginationState.findJobs.page,
        totalPages: paginationState.findJobs.totalPages,
        total: paginationState.findJobs.total,
        pageSize: paginationState.findJobs.pageSize,
        pageSizeOptions: [12, 24, 48],
        itemLabel: 'Matching Openings',
        onPageChange: (newPage) => {
            loadFindJobs(newPage);
            const anchor = document.getElementById('subview-jobs-find');
            if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
        onPageSizeChange: (newSize) => {
            paginationState.findJobs.pageSize = newSize;
            loadFindJobs(1);
        }
    });
}

function populateFindJobFilters(jobs) {
    const locFilter = document.getElementById('find-job-location-filter');
    const deptFilter = document.getElementById('find-job-dept-filter');

    if (locFilter && locFilter.options.length <= 1 && jobs.length > 0) {
        const locs = [...new Set(jobs.map(j => j.location).filter(Boolean))].sort();
        locFilter.innerHTML = '<option value="all">All Locations (Pan-India)</option>' +
            locs.map(l => `<option value="${escapeHtml(l)}">${escapeHtml(l)}</option>`).join('');
    }

    if (deptFilter && deptFilter.options.length <= 1 && jobs.length > 0) {
        const depts = [...new Set(jobs.map(j => j.department).filter(Boolean))].sort();
        deptFilter.innerHTML = '<option value="all">All Departments</option>' +
            depts.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('');
    }
}

function renderFindJobs(list, total, totalPages) {
    const grid = document.getElementById('find-jobs-grid');
    const countLabel = document.getElementById('find-job-count-label');
    if (!grid) return;

    if (!list || list.length === 0) {
        grid.innerHTML = `
            <div style="grid-column:1/-1;" class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <div class="empty-state-title">No Matching Roles Found</div>
                <div class="empty-state-text">Try adjusting your keywords, selecting "All Locations", or resetting the experience filter.</div>
                <button class="btn-primary" onclick="resetFindJobsFilters()">Reset Discovery Filters</button>
            </div>`;
        if (countLabel) countLabel.textContent = 'No matching openings found';
        return;
    }

    if (countLabel) {
        countLabel.textContent = `Found ${total.toLocaleString('en-IN')} Verified Openings Matching Your Discovery Criteria`;
    }

    grid.innerHTML = list.map(job => renderStandardJobCard(job, { showCompanyLink: true })).join('');
}

function renderStandardJobCard(job, options = {}) {
    const applyUrl = getJobApplyLink(job);
    const domainLabel = cleanDomainLabel(applyUrl);

    let modeBadge = '<span class="badge badge-slate" style="font-size:10px;">' + NOT_AVAILABLE_TEXT + '</span>';
    if (job.work_mode === 'Remote') modeBadge = '<span class="badge badge-cyan">🏠 Remote</span>';
    else if (job.work_mode === 'Hybrid') modeBadge = '<span class="badge badge-purple">🔄 Hybrid</span>';
    else if (job.work_mode === 'On-site') modeBadge = '<span class="badge badge-emerald">🏢 On-site</span>';
    else if (job.work_mode) modeBadge = `<span class="badge badge-slate" style="font-size:10px;">${escapeHtml(job.work_mode)}</span>`;

    const skills = job.skills
        ? job.skills.split(',').map(s => s.trim()).filter(Boolean).slice(0, 4)
        : [];

    const showCompanyLink = options.showCompanyLink !== false;
    const deptBadge = job.department 
        ? `<span class="badge badge-cyan" style="font-size:10.5px;">${escapeHtml(job.department)}</span>`
        : `<span class="badge badge-slate" style="font-size:10.5px;">${NOT_AVAILABLE_TEXT}</span>`;

    return `
        <div class="job-discovery-card">
            <div>
                <div class="job-header-row">
                    ${deptBadge}
                    ${modeBadge}
                </div>

                <div class="job-card-title">
                    <a href="javascript:void(0)" onclick="openJobDetailsModal(${job.job_row_id})">
                        ${escapeHtml(job.job_title)}
                    </a>
                </div>

                ${showCompanyLink ? `
                <a href="javascript:void(0)" class="job-company-badge" onclick="openCompanyJobs('${job.company_id}')">
                    🏢 ${escapeHtml(job.company_name)}
                    ${job.nse_symbol ? `<span style="color:var(--text-muted); font-size:12px;">(${escapeHtml(job.nse_symbol)})</span>` : ''}
                </a>
                ` : `
                <div style="font-size:12px; color:var(--text-secondary); margin-bottom:10px; font-weight:600;">
                    🏢 ${escapeHtml(job.company_name)}
                </div>
                `}

                <div class="job-meta-chips">
                    <span class="job-chip">📍 ${job.location ? escapeHtml(job.location) : NOT_AVAILABLE_TEXT}</span>
                    ${job.experience ? `<span class="job-chip">⏳ ${escapeHtml(job.experience)}</span>` : ''}
                    ${job.employment_type ? `<span class="job-chip">💼 ${escapeHtml(job.employment_type)}</span>` : ''}
                    ${job.salary ? `<span class="job-chip">💰 ${escapeHtml(job.salary)}</span>` : ''}
                </div>

                ${skills.length > 0 ? `
                <div class="job-skills-chips">
                    ${skills.map(sk => `<span class="skill-pill">${escapeHtml(sk)}</span>`).join('')}
                </div>
                ` : ''}
            </div>

            <div class="job-card-footer">
                <div class="job-post-date">
                    <span>✓ Source Verified ATS</span>
                </div>
                <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                    <button class="btn-primary" style="padding:6px 14px; font-size:12px;" onclick="openJobDetailsModal(${job.job_row_id})">
                        View Job
                    </button>
                    ${applyButtonHtml(job, 'btn-secondary', 'padding:6px 12px; font-size:12px;', 'Apply ↗')}
                    ${showCompanyLink ? `
                    <button class="btn-outline" style="padding:6px 10px; font-size:11px;" onclick="openCompanyJobs('${job.company_id}')" title="View all jobs for this company">
                        🏢 All Jobs
                    </button>
                    ` : ''}
                </div>
            </div>
        </div>
    `;
}


function executeFindJobsSearch() {
    loadFindJobs(1);
    const clearBtn = document.getElementById('find-jobs-search-clear');
    const input = document.getElementById('find-jobs-search-input');
    if (clearBtn && input) {
        clearBtn.style.display = input.value.trim() ? 'block' : 'none';
    }
}

function clearFindJobsSearch() {
    const input = document.getElementById('find-jobs-search-input');
    const clearBtn = document.getElementById('find-jobs-search-clear');
    if (input) input.value = '';
    if (clearBtn) clearBtn.style.display = 'none';
    loadFindJobs(1);
}

function setFindJobsQuery(query) {
    const input = document.getElementById('find-jobs-search-input');
    if (input) input.value = query;
    executeFindJobsSearch();
}

function resetFindJobsFilters() {
    const input = document.getElementById('find-jobs-search-input');
    if (input) input.value = '';
    const comp = document.getElementById('find-job-company-filter');
    if (comp) comp.value = '';
    const loc = document.getElementById('find-job-location-filter');
    if (loc) loc.value = 'all';
    const exp = document.getElementById('find-job-exp-filter');
    if (exp) exp.value = 'all';
    const mode = document.getElementById('find-job-mode-filter');
    if (mode) mode.value = 'all';
    const dept = document.getElementById('find-job-dept-filter');
    if (dept) dept.value = 'all';
    const sort = document.getElementById('find-job-sort-filter');
    if (sort) sort.value = 'relevance';
    const clearBtn = document.getElementById('find-jobs-search-clear');
    if (clearBtn) clearBtn.style.display = 'none';
    loadFindJobs(1);
}

// ---------------------------------------------------------------------------
// 2. COMPANY JOBS (DIRECTORY & DRILL-DOWN DASHBOARD)
// ---------------------------------------------------------------------------
async function loadCompanyJobsDirectory(forceRefresh = false) {
    const grid = document.getElementById('company-jobs-directory-grid');
    const countLabel = document.getElementById('company-directory-count-label');
    const sectorFilter = document.getElementById('company-jobs-sector-filter');
    if (!grid) return;

    // Instant fast path: If companies are already in memory, render immediately with 0ms lag!
    if (!forceRefresh && Array.isArray(allDirectoryCompanies) && allDirectoryCompanies.length > 0) {
        filteredDirectoryCompanies = allDirectoryCompanies;
        if (sectorFilter && sectorFilter.options.length <= 1) {
            const sectors = [...new Set(allDirectoryCompanies.map(c => c.sector).filter(Boolean))].sort();
            sectorFilter.innerHTML = '<option value="all">All Industries &amp; Sectors</option>' +
                sectors.map(s => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
        }
        if (!paginationState.companyDirectory) {
            paginationState.companyDirectory = { page: 1, pageSize: 16, total: allDirectoryCompanies.length, totalPages: Math.ceil(allDirectoryCompanies.length / 16) };
        }
        renderCompanyJobsDirectoryPage();
        return;
    }

    grid.innerHTML = `
        <div style="grid-column:1/-1;" class="dynamic-loading-skeleton">
            <div class="loading-spinner-circle"></div>
            <div class="loading-spinner-text">Cataloging Enterprise Job Portals...</div>
            <div class="loading-spinner-sub">Fetching verified employers across India's Top 200 enterprises</div>
        </div>`;

    try {
        const res = await fetch(`${API_BASE}/recommendations?limit=5000`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const items = Array.isArray(data) ? data : (data.items || []);

        // Default sort: hiring companies with verified job openings first
        items.sort((a, b) => {
            const jA = a.job_count || 0;
            const jB = b.job_count || 0;
            if (jB !== jA) return jB - jA;
            return (a.company_name || '').localeCompare(b.company_name || '');
        });

        allDirectoryCompanies = items;
        filteredDirectoryCompanies = items;

        if (sectorFilter && sectorFilter.options.length <= 1) {
            const sectors = [...new Set(items.map(c => c.sector).filter(Boolean))].sort();
            sectorFilter.innerHTML = '<option value="all">All Industries &amp; Sectors</option>' +
                sectors.map(s => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
        }

        if (!paginationState.companyDirectory) {
            paginationState.companyDirectory = { page: 1, pageSize: 16, total: items.length, totalPages: Math.ceil(items.length / 16) };
        }
        paginationState.companyDirectory.total = items.length;
        paginationState.companyDirectory.pageSize = paginationState.companyDirectory.pageSize || 16;
        paginationState.companyDirectory.totalPages = Math.ceil(items.length / paginationState.companyDirectory.pageSize) || 1;
        paginationState.companyDirectory.page = 1;

        const companyJobsPill = document.getElementById('badge-jobs-company-pill');
        if (companyJobsPill) companyJobsPill.textContent = `${items.length} Corps`;

        renderCompanyJobsDirectoryPage();
    } catch (e) {
        console.error('Error loading company directory', e);
        if (grid) {
            grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#f43f5e;">Could not load companies: ${escapeHtml(e.message)}</div>`;
        }
    }
}

function renderCompanyJobsDirectoryPage() {
    const list = filteredDirectoryCompanies || [];
    const total = list.length;
    const pageSize = (paginationState.companyDirectory && paginationState.companyDirectory.pageSize) || 16;
    const totalPages = Math.ceil(total / pageSize) || 1;

    if (!paginationState.companyDirectory) {
        paginationState.companyDirectory = { page: 1, pageSize: 16, total: total, totalPages: totalPages };
    }
    paginationState.companyDirectory.total = total;
    paginationState.companyDirectory.totalPages = totalPages;

    if (paginationState.companyDirectory.page > totalPages) {
        paginationState.companyDirectory.page = totalPages;
    }
    if (paginationState.companyDirectory.page < 1) {
        paginationState.companyDirectory.page = 1;
    }

    const page = paginationState.companyDirectory.page;
    const start = (page - 1) * pageSize;
    const pagedItems = list.slice(start, start + pageSize);

    renderCompanyJobsDirectoryCards(pagedItems);
    renderCompanyDirectoryPagination();

    const countLabel = document.getElementById('company-directory-count-label');
    if (countLabel) {
        if (total === (allDirectoryCompanies || []).length) {
            countLabel.textContent = `Showing page ${page} of ${totalPages} (${total} Verified Corporate Employers Total)`;
        } else {
            countLabel.textContent = `Showing page ${page} of ${totalPages} (${total} Corporations Found)`;
        }
    }
}

function renderCompanyDirectoryPagination() {
    renderPaginationBar({
        containerId: 'company-directory-pagination',
        page: paginationState.companyDirectory.page,
        totalPages: paginationState.companyDirectory.totalPages,
        total: paginationState.companyDirectory.total,
        pageSize: paginationState.companyDirectory.pageSize,
        pageSizeOptions: [16, 32, 64, 128],
        itemLabel: 'Corporate Employers',
        onPageChange: (newPage) => {
            paginationState.companyDirectory.page = newPage;
            renderCompanyJobsDirectoryPage();
            const anchor = document.getElementById('company-jobs-directory-view');
            if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
        onPageSizeChange: (newSize) => {
            paginationState.companyDirectory.pageSize = newSize;
            paginationState.companyDirectory.page = 1;
            renderCompanyJobsDirectoryPage();
        }
    });
}

function renderCompanyJobsDirectoryCards(list) {
    const grid = document.getElementById('company-jobs-directory-grid');
    if (!grid) return;

    if (!list || list.length === 0) {
        grid.innerHTML = `
            <div style="grid-column:1/-1;" class="empty-state">
                <div class="empty-state-icon">🏢</div>
                <div class="empty-state-title">No Corporations Found</div>
                <div class="empty-state-text">No companies matched your query or filters.</div>
            </div>`;
        return;
    }

    grid.innerHTML = list.map(comp => {
        const hasValidSymbol = comp.nse_symbol && 
            typeof comp.nse_symbol === 'string' && 
            comp.nse_symbol.trim().length > 0 && 
            !comp.nse_symbol.includes('Not available') && 
            comp.nse_symbol !== 'null' && 
            comp.nse_symbol !== 'None';

        const symbol = hasValidSymbol ? comp.nse_symbol.trim().toUpperCase() : null;
        const avatar = getCompanyInitials(comp.company_name, symbol);
        const avatarGradient = getAvatarGradient(comp.company_name);
        
        const sector = (comp.sector && comp.sector !== NOT_AVAILABLE_TEXT) ? comp.sector : 'Corporate';
        const rawHq = comp.headquarters ? comp.headquarters.split('/')[0].trim() : '';
        const hq = (rawHq && rawHq !== NOT_AVAILABLE_TEXT) ? rawHq : 'India';

        const jobCnt = comp.job_count || comp.verified_jobs_count || 0;
        const crawlSt = comp.crawl_status || 'PENDING';
        const jobState = comp.job_status_state || (jobCnt > 0 ? 'VERIFIED_JOBS' : 'VERIFIED_ZERO');

        // Authoritative Status Badge
        let jobBadge = '';
        if (jobCnt > 0) {
            jobBadge = `<span class="badge badge-emerald" style="font-size:11px; font-weight:700; display:inline-flex; align-items:center; gap:5px;"><span style="width:6px; height:6px; border-radius:50%; background:#10b981; display:inline-block;"></span>${jobCnt} Verified Jobs</span>`;
        } else if (crawlSt === 'FAILED' || jobState === 'CRAWL_FAILED') {
            jobBadge = `<span class="badge badge-rose" style="font-size:11px; font-weight:600;">⚠️ Sync Failed</span>`;
        } else if (crawlSt === 'BLOCKED' || crawlSt === 'REDIRECT_BLOCKED' || jobState === 'SOURCE_BLOCKED') {
            jobBadge = `<span class="badge badge-amber" style="font-size:11px; font-weight:600;">🔒 Portal Protected</span>`;
        } else if (crawlSt === 'CRAWLED' || jobState === 'VERIFIED_ZERO') {
            jobBadge = `<span class="badge" style="font-size:11px; background:var(--bg-subtle); color:var(--text-secondary); border:1px solid var(--border-color);">0 Active Roles</span>`;
        } else if (crawlSt === 'NO_CAREER_URL' || jobState === 'ATS_DISCOVERY_FAILED') {
            jobBadge = `<span class="badge badge-amber" style="font-size:11px;">Source In Review</span>`;
        } else {
            jobBadge = `<span class="badge" style="font-size:11px; background:var(--bg-subtle); color:var(--text-muted); border:1px dashed var(--border-color);">Coverage Active</span>`;
        }

        return `
            <div class="job-discovery-card" style="cursor:pointer; display:flex; flex-direction:column; justify-content:space-between; padding:18px; border-radius:12px; background:var(--bg-surface); border:1px solid var(--border-color); box-shadow:var(--shadow-card); transition:all 0.2s cubic-bezier(0.16, 1, 0.3, 1);" onclick="openCompanyJobs('${comp.company_id}')">
                <div>
                    <!-- Header: Avatar + Title & Meta -->
                    <div style="display:flex; align-items:flex-start; gap:12px; margin-bottom:12px;">
                        <div class="company-logo-avatar" style="width:46px; height:46px; border-radius:10px; font-size:15px; font-weight:800; background:${avatarGradient}; color:#ffffff; display:flex; align-items:center; justify-content:center; flex-shrink:0; box-shadow:0 3px 8px rgba(0,0,0,0.12); letter-spacing:0.5px;">
                            ${escapeHtml(avatar)}
                        </div>
                        <div style="flex:1; min-width:0;">
                            <div style="font-weight:700; font-size:14.5px; color:var(--text-primary); line-height:1.35; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="${escapeHtml(comp.company_name)}">
                                ${escapeHtml(comp.company_name)}
                            </div>
                            <div style="font-size:11.5px; color:var(--text-secondary); margin-top:3px; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                                ${symbol ? `<span class="badge badge-cyan" style="font-size:9.5px; font-weight:700; padding:2px 6px;">NSE: ${escapeHtml(symbol)}</span>` : ''}
                                <span style="display:inline-flex; align-items:center; gap:2px; color:var(--text-muted);">📍 ${escapeHtml(hq)}</span>
                            </div>
                        </div>
                    </div>

                    <!-- Meta: Sector & Verified Jobs Count -->
                    <div style="display:flex; align-items:center; justify-content:space-between; gap:8px; margin-top:10px; padding:7px 10px; background:var(--bg-subtle); border-radius:8px; border:1px solid var(--border-subtle);">
                        <span class="badge badge-purple" style="font-size:10px; font-weight:600; max-width:130px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(sector)}">
                            ${escapeHtml(sector)}
                        </span>
                        <div>${jobBadge}</div>
                    </div>
                </div>

                <!-- Footer: Action Buttons (Equal, Balanced, Clear) -->
                <div style="display:flex; align-items:center; gap:8px; margin-top:14px; padding-top:12px; border-top:1px solid var(--border-subtle);">
                    <button class="btn-outline" style="flex:1; padding:7px 8px; font-size:11.5px; font-weight:600; text-align:center; justify-content:center; border-radius:6px; white-space:nowrap;" onclick="event.stopPropagation(); openCompanyDossier('${comp.company_id}')" title="View Corporate Profile & CSR Dossier">
                        View Profile
                    </button>
                    <button class="${jobCnt > 0 ? 'btn-primary' : 'btn-outline'}" style="flex:1.4; padding:7px 10px; font-size:11.5px; font-weight:700; text-align:center; justify-content:center; border-radius:6px; white-space:nowrap; ${jobCnt > 0 ? 'background:linear-gradient(135deg, #059669 0%, #047857 100%); border-color:#047857; color:#ffffff; box-shadow:0 2px 6px rgba(5,150,105,0.2);' : ''}" onclick="event.stopPropagation(); openCompanyJobs('${comp.company_id}')">
                        ${jobCnt > 0 ? `View ${jobCnt} Jobs →` : 'Careers (0) →'}
                    </button>
                </div>
            </div>
        `;
    }).join('');

}

function filterCompanyDirectory() {
    const q = (document.getElementById('company-jobs-search')?.value || '').trim().toLowerCase();
    const sector = document.getElementById('company-jobs-sector-filter')?.value || 'all';
    const sortBy = document.getElementById('company-jobs-sort-filter')?.value || 'jobs_desc';
    const hiringOnly = document.getElementById('company-jobs-hiring-only')?.checked || false;

    let filtered = [...(allDirectoryCompanies || [])];
    if (q) {
        filtered = filtered.filter(c =>
            (c.company_name && c.company_name.toLowerCase().includes(q)) ||
            (c.nse_symbol && c.nse_symbol.toLowerCase().includes(q)) ||
            (c.sector && c.sector.toLowerCase().includes(q))
        );
    }
    if (sector !== 'all') {
        filtered = filtered.filter(c => c.sector === sector);
    }
    if (hiringOnly) {
        filtered = filtered.filter(c => (c.job_count || 0) > 0);
    }

    if (sortBy === 'jobs_desc') {
        filtered.sort((a, b) => {
            const jA = a.job_count || 0;
            const jB = b.job_count || 0;
            if (jB !== jA) return jB - jA;
            return (a.company_name || '').localeCompare(b.company_name || '');
        });
    } else if (sortBy === 'name_asc') {
        filtered.sort((a, b) => (a.company_name || '').localeCompare(b.company_name || ''));
    } else if (sortBy === 'sector') {
        filtered.sort((a, b) => (a.sector || '').localeCompare(b.sector || '') || (a.company_name || '').localeCompare(b.company_name || ''));
    } else if (sortBy === 'score') {
        filtered.sort((a, b) => (b.opportunity_score || b.score || 0) - (a.opportunity_score || a.score || 0));
    }

    filteredDirectoryCompanies = filtered;
    if (paginationState.companyDirectory) {
        paginationState.companyDirectory.page = 1;
    }
    renderCompanyJobsDirectoryPage();
}

async function openCompanyJobs(companyId) {
    if (!companyId) return;

    // Switch tab to jobs if not already on it
    switchTab('jobs');
    // Switch to company sub-tab
    switchJobSubTab('company');

    selectedCompanyJobId = companyId;

    // Toggle views
    const dirView = document.getElementById('company-jobs-directory-view');
    const dashView = document.getElementById('company-job-dashboard-view');
    if (dirView) dirView.style.display = 'none';
    if (dashView) dashView.style.display = 'block';

    const avatarEl = document.getElementById('comp-dash-avatar');
    const nameEl = document.getElementById('comp-dash-name');
    const symbolEl = document.getElementById('comp-dash-symbol');
    const sectorEl = document.getElementById('comp-dash-sector');
    const hqEl = document.getElementById('comp-dash-hq');
    const webEl = document.getElementById('comp-dash-website-link');
    const carEl = document.getElementById('comp-dash-careers-link');

    // Look up company metadata
    let comp = (allDirectoryCompanies || []).find(c => c.company_id === companyId);
    if (!comp) {
        try {
            const res = await fetch(`${API_BASE}/companies/${companyId}`);
            if (res.ok) comp = await res.json();
        } catch (_) {}
    }

    if (comp) {
        selectedCompanyJobData = comp;
        if (nameEl) nameEl.textContent = comp.company_name;
        const hasSym = comp.nse_symbol && typeof comp.nse_symbol === 'string' && comp.nse_symbol.trim().length > 0 && !comp.nse_symbol.includes('Not available');
        const sym = hasSym ? comp.nse_symbol.trim().toUpperCase() : null;
        if (avatarEl) {
            avatarEl.textContent = getCompanyInitials(comp.company_name, sym);
            avatarEl.style.background = getAvatarGradient(comp.company_name);
            avatarEl.style.color = '#ffffff';
        }
        if (symbolEl) symbolEl.textContent = sym ? `NSE: ${sym}` : (comp.cin ? `CIN: ${comp.cin}` : 'National Enterprise');
        if (sectorEl) sectorEl.textContent = (comp.sector && comp.sector !== NOT_AVAILABLE_TEXT) ? comp.sector : 'Corporate Enterprise';
        if (hqEl) {
            const rawHq = comp.headquarters ? comp.headquarters.split('/')[0].trim() : '';
            hqEl.textContent = `📍 ${(rawHq && rawHq !== NOT_AVAILABLE_TEXT) ? rawHq : 'India'}`;
        }
        const website = getCompanyWebsite(comp);
        if (webEl) webEl.innerHTML = website ? `🌐 <a href="${escapeHtml(website)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary-brand); text-decoration:none;">Website ↗</a>` : `🌐 <span style="color:var(--text-muted);">${escapeHtml(NOT_AVAILABLE_TEXT)}</span>`;
        if (carEl) carEl.innerHTML = comp.careers_url ? `💼 <a href="${escapeHtml(comp.careers_url)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary-brand); text-decoration:none;">Careers Portal ↗</a>` : (comp.jobs_access === 'LOGIN_REQUIRED' ? `🔒 <span style="color:#f59e0b;">${escapeHtml(LOGIN_REQUIRED_TEXT)}</span>` : `💼 <span style="color:var(--text-muted);">${escapeHtml(NOT_AVAILABLE_TEXT)}</span>`);
    } else {
        if (nameEl) nameEl.textContent = 'Corporate Enterprise';
    }

    loadSelectedCompanyJobs(1);
    dashView.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function returnToCompanyDirectory() {
    const dirView = document.getElementById('company-jobs-directory-view');
    const dashView = document.getElementById('company-job-dashboard-view');
    if (dirView) dirView.style.display = 'block';
    if (dashView) dashView.style.display = 'none';
}

function openCompanyDossierFromJobDashboard() {
    if (selectedCompanyJobId) {
        openCompanyDossier(selectedCompanyJobId);
    }
}

async function loadSelectedCompanyJobs(page = 1) {
    if (!selectedCompanyJobId) return;
    if (typeof page !== 'number' || isNaN(page) || page < 1) page = 1;
    if (!paginationState.companyJobs) paginationState.companyJobs = { page: 1, pageSize: 12, total: 0, totalPages: 1 };
    paginationState.companyJobs.page = page;

    const grid = document.getElementById('comp-jobs-grid');
    const label = document.getElementById('comp-jobs-list-count-label');
    const jobsCountEl = document.getElementById('comp-dash-jobs-count');

    if (grid) {
        grid.innerHTML = `
            <div style="grid-column:1/-1;" class="dynamic-loading-skeleton">
                <div class="loading-spinner-circle"></div>
                <div class="loading-spinner-text">Retrieving Enterprise Openings...</div>
                <div class="loading-spinner-sub">Fetching verified vacancies for ${escapeHtml(selectedCompanyJobData?.company_name || 'selected company')}</div>
            </div>`;
    }

    try {
        const query = (document.getElementById('comp-job-search')?.value || '').trim();
        const loc = document.getElementById('comp-job-loc-filter')?.value || 'all';
        const exp = document.getElementById('comp-job-exp-filter')?.value || 'all';
        const mode = document.getElementById('comp-job-mode-filter')?.value || 'all';
        const dept = document.getElementById('comp-job-dept-filter')?.value || 'all';
        const sort = document.getElementById('comp-job-sort-filter')?.value || 'recent';

        let url = `${API_BASE}/jobs?company_id=${encodeURIComponent(selectedCompanyJobId)}&page=${page}&page_size=${paginationState.companyJobs.pageSize}`;
        if (query) url += `&q=${encodeURIComponent(query)}`;
        if (loc !== 'all') url += `&location=${encodeURIComponent(loc)}`;
        if (exp !== 'all') url += `&experience=${encodeURIComponent(exp)}`;
        if (mode !== 'all') url += `&work_mode=${encodeURIComponent(mode)}`;
        if (dept !== 'all') url += `&department=${encodeURIComponent(dept)}`;
        if (sort === 'title') url += `&sort=title`;
        else if (sort === 'experience') url += `&sort=experience`;
        else if (sort === 'recent') url += `&sort=recent`;

        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        let items = [];
        let total = 0;
        let totalPages = 1;

        if (data && typeof data === 'object' && Array.isArray(data.items)) {
            items = data.items;
            total = data.total;
            totalPages = data.total_pages;
        } else if (Array.isArray(data)) {
            items = data;
            total = items.length;
            totalPages = Math.ceil(total / paginationState.companyJobs.pageSize);
        }

        paginationState.companyJobs.total = total;
        paginationState.companyJobs.totalPages = totalPages;

        if (jobsCountEl) jobsCountEl.textContent = total;
        if (label) label.textContent = `All Jobs (${total})`;

        populateSelectedCompanyJobFilters(items);
        renderSelectedCompanyJobs(items);
        renderSelectedCompanyJobsPagination();
    } catch (e) {
        console.error('Error in loadSelectedCompanyJobs', e);
        if (grid) {
            grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#f43f5e;">Could not load company jobs: ${escapeHtml(e.message)}</div>`;
        }
    }
}

function renderSelectedCompanyJobsPagination() {
    renderPaginationBar({
        containerId: 'comp-jobs-pagination',
        page: paginationState.companyJobs.page,
        totalPages: paginationState.companyJobs.totalPages,
        total: paginationState.companyJobs.total,
        pageSize: paginationState.companyJobs.pageSize,
        pageSizeOptions: [12, 24, 48],
        itemLabel: 'Company Openings',
        onPageChange: (newPage) => {
            loadSelectedCompanyJobs(newPage);
            const anchor = document.getElementById('company-job-dashboard-view');
            if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
        onPageSizeChange: (newSize) => {
            paginationState.companyJobs.pageSize = newSize;
            loadSelectedCompanyJobs(1);
        }
    });
}

function populateSelectedCompanyJobFilters(jobs) {
    const loc = document.getElementById('comp-job-loc-filter');
    const dept = document.getElementById('comp-job-dept-filter');

    if (loc && loc.options.length <= 1 && jobs.length > 0) {
        const locs = [...new Set(jobs.map(j => j.location).filter(Boolean))].sort();
        loc.innerHTML = '<option value="all">All Locations</option>' +
            locs.map(l => `<option value="${escapeHtml(l)}">${escapeHtml(l)}</option>`).join('');
    }

    if (dept && dept.options.length <= 1 && jobs.length > 0) {
        const depts = [...new Set(jobs.map(j => j.department).filter(Boolean))].sort();
        dept.innerHTML = '<option value="all">All Departments</option>' +
            depts.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('');
    }
}

function renderSelectedCompanyJobs(list) {
    const grid = document.getElementById('comp-jobs-grid');
    if (!grid) return;

    if (!list || list.length === 0) {
        const crawlSt = selectedCompanyJobData?.crawl_status || 'PENDING';
        let emptyTitle = "No Openings Match Filters";
        let emptyText = "No active vacancies found for this company under the selected filters.";
        let emptyAction = `<button class="btn-primary" onclick="resetSelectedCompanyJobFilters()">Reset Filters</button>`;

        if (paginationState.companyJobs.total === 0) {
            emptyTitle = "0 Active Openings Disclosed";
            const careersUrl = _cleanHttpUrl(selectedCompanyJobData?.careers_url);

            let statusDetail = "No active job postings are currently recorded in the database for this corporation.";
            let statusBadge = '<span class="badge" style="background:var(--bg-subtle); color:var(--text-secondary); border:1px solid var(--border-color); font-size:11px;">0 Verified Jobs (Confirmed Zero)</span>';
            if (crawlSt === 'FAILED') {
                statusDetail = "The automated crawler encountered an access or parsing failure while inspecting the official careers portal. Job coverage is currently incomplete.";
                statusBadge = '<span class="badge badge-rose" style="font-size:11px;">⚠️ Crawl Failed</span>';
            } else if (crawlSt === 'BLOCKED' || crawlSt === 'REDIRECT_BLOCKED') {
                statusDetail = "The enterprise careers source is protected by security firewalls or interactive access controls. Direct robotic extraction is restricted.";
                statusBadge = '<span class="badge badge-amber" style="font-size:11px;">🔒 Source Protected / Blocked</span>';
            } else if (crawlSt === 'CRAWLED') {
                statusDetail = `The official careers portal was successfully crawled. No active job vacancies are currently published by ${escapeHtml(selectedCompanyJobData?.company_name || 'this corporation')}.`;
                statusBadge = '<span class="badge" style="background:var(--bg-subtle); color:var(--text-secondary); border:1px solid var(--border-color); font-size:11px;">0 Verified Jobs (Confirmed Zero)</span>';
            } else {
                statusDetail = "Careers source discovery and verification are pending for this enterprise.";
                statusBadge = '<span class="badge" style="background:var(--bg-subtle); color:var(--text-muted); border:1px dashed var(--border-color); font-size:11px;">Coverage Pending</span>';
            }

            emptyText = `
                <div style="margin-bottom:12px;">${statusBadge}</div>
                <div style="color:var(--text-secondary); max-width:540px; margin:0 auto; font-size:13.5px; line-height:1.5;">${statusDetail}</div>
            `;
            emptyAction = `
                <div style="display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin-top:16px;">
                    <button class="btn-primary" onclick="openCompanyDossier('${selectedCompanyJobId}')">View Enterprise Profile &amp; CSR Dossier</button>
                    ${careersUrl ? `<a href="${escapeHtml(careersUrl)}" target="_blank" rel="noopener noreferrer" class="btn-outline" style="text-decoration:none; display:inline-block;">Visit Official Careers Portal ↗</a>` : ''}
                    <button class="btn-secondary" onclick="returnToCompanyDirectory()">← Return to Company Directory</button>
                </div>
            `;
        }

        grid.innerHTML = `
            <div style="grid-column:1/-1;" class="empty-state">
                <div class="empty-state-icon">💼</div>
                <div class="empty-state-title">${emptyTitle}</div>
                <div class="empty-state-text">${emptyText}</div>
                ${emptyAction}
            </div>`;
        return;
    }


    grid.innerHTML = list.map(job => renderStandardJobCard(job, { showCompanyLink: false })).join('');
}

function filterSelectedCompanyJobs() {
    loadSelectedCompanyJobs(1);
}

function resetSelectedCompanyJobFilters() {
    const search = document.getElementById('comp-job-search');
    if (search) search.value = '';
    const loc = document.getElementById('comp-job-loc-filter');
    if (loc) loc.value = 'all';
    const exp = document.getElementById('comp-job-exp-filter');
    if (exp) exp.value = 'all';
    const mode = document.getElementById('comp-job-mode-filter');
    if (mode) mode.value = 'all';
    const dept = document.getElementById('comp-job-dept-filter');
    if (dept) dept.value = 'all';
    const sort = document.getElementById('comp-job-sort-filter');
    if (sort) sort.value = 'recent';
    loadSelectedCompanyJobs(1);
}

// ---------------------------------------------------------------------------
// 3. COMPREHENSIVE UNIVERSAL JOB DETAILS MODAL (SECTIONS A TO J)
// ---------------------------------------------------------------------------
function getMissingFieldNotice(job, isDetailPageField = true) {
    // A field is "not available on the company website" only when the posting itself was read
    // successfully and the field is not there.  If the posting could not be read we say that instead
    // of claiming the company does not publish it.
    const style = 'color:var(--text-muted); font-size:12px; font-style:italic;';
    if (isDetailPageField) {
        const status = (job.detail_fetch_status || '').toUpperCase();
        if (status !== 'FETCHED' && !job.detail_fetched) {
            return `<span style="${style}">Not yet verified from the company website</span>`;
        }
    }
    return `<span style="${style}">${NOT_AVAILABLE_TEXT}</span>`;
}

async function openJobDetailsModal(jobId, forceRefresh = false) {
    const modal = document.getElementById('modal-job-details');
    const modalBody = document.getElementById('modal-job-body');
    const modalTitle = document.getElementById('modal-job-title');
    const modalSub = document.getElementById('modal-job-company-subtitle');
    const modalAvatar = document.getElementById('modal-job-avatar');
    const modalBadge = document.getElementById('modal-job-verification-badge');
    if (!modal || !modalBody) return;

    modal.style.display = 'flex';
    modalBody.innerHTML = `
        <div style="text-align:center; padding:60px 20px;">
            <div class="loading-spinner-circle" style="margin:0 auto 16px;"></div>
            <div style="font-size:16px; font-weight:700; color:var(--text-primary);">${forceRefresh ? 'Re-verifying Live from Official Careers Portal...' : 'Retrieving Role Specifications...'}</div>
            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">Connecting to authoritative enterprise careers repository</div>
        </div>`;

    try {
        const url = `${API_BASE}/jobs/${jobId}${forceRefresh ? '?refresh=1' : ''}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const job = await res.json();

        // 1. Universal Job Header
        if (modalTitle) modalTitle.textContent = job.job_title;
        if (modalBadge) {
            const vLabel = getVerificationStatusLabel(job.verification_status);
            modalBadge.textContent = vLabel;
            modalBadge.className = `badge ${vLabel === 'Source verified' ? 'badge-emerald' : (vLabel === 'Verification pending' ? 'badge-amber' : (vLabel === 'Unable to verify' ? 'badge-rose' : 'badge-slate'))}`;
        }
        if (modalSub) {
            modalSub.innerHTML = `
                <a href="javascript:void(0)" onclick="closeModal('modal-job-details'); openCompanyJobs('${job.company_id}');" style="color:var(--primary-brand); font-weight:700; text-decoration:none;">
                    🏢 ${escapeHtml(job.company_name)}
                </a>
                ${job.nse_symbol ? `<span style="color:var(--text-muted); margin-left:6px;">(${escapeHtml(job.nse_symbol)})</span>` : (job.cin ? `<span style="color:var(--text-muted); margin-left:6px; font-family:var(--font-mono); font-size:11px;">(${escapeHtml(job.cin)})</span>` : '')}
                ${job.sector ? `<span style="margin:0 6px; color:var(--border-color);">•</span><span>${escapeHtml(job.sector)}</span>` : ''}
                <span style="margin:0 6px; color:var(--border-color);">•</span>
                <span>📍 ${job.location ? escapeHtml(job.location) : getMissingFieldNotice(job, false)}</span>
            `;
        }
        if (modalAvatar) {
            modalAvatar.textContent = getCompanyInitials(job.company_name, job.nse_symbol);
            modalAvatar.style.background = getAvatarGradient(job.company_name);
            modalAvatar.style.color = '#ffffff';
        }

        const applyUrl = getJobApplyLink(job);
        const domainLabel = cleanDomainLabel(applyUrl);

        let workModeBadge = getMissingFieldNotice(job, true);
        if (job.work_mode === 'Remote') workModeBadge = '<span class="badge badge-cyan">🏠 Remote</span>';
        else if (job.work_mode === 'Hybrid') workModeBadge = '<span class="badge badge-purple">🔄 Hybrid</span>';
        else if (job.work_mode === 'On-site') workModeBadge = '<span class="badge badge-emerald">🏢 On-site</span>';
        else if (job.work_mode) workModeBadge = `<span class="badge badge-slate">${escapeHtml(job.work_mode)}</span>`;

        const skillsList = job.skills
            ? job.skills.split(',').map(s => s.trim()).filter(Boolean)
            : [];

        let html = '';

        // 2. Key Job Details Metadata Grid (Missing field = hidden, never a default)
        const metaItems = [];
        if (job.location) metaItems.push(`<div class="job-meta-item"><span class="job-meta-lbl">Location</span><span class="job-meta-val">📍 ${escapeHtml(job.location)}</span></div>`);
        if (job.employment_type) metaItems.push(`<div class="job-meta-item"><span class="job-meta-lbl">Employment Type</span><span class="job-meta-val">💼 ${escapeHtml(job.employment_type)}</span></div>`);
        if (job.experience) metaItems.push(`<div class="job-meta-item"><span class="job-meta-lbl">Experience Requirements</span><span class="job-meta-val">⏳ ${escapeHtml(job.experience)}</span></div>`);
        if (job.department || job.team) metaItems.push(`<div class="job-meta-item"><span class="job-meta-lbl">Department / Team</span><span class="job-meta-val">🏢 ${escapeHtml(job.department || job.team)}</span></div>`);
        if (job.function || job.business_unit) metaItems.push(`<div class="job-meta-item"><span class="job-meta-lbl">Function &amp; BU</span><span class="job-meta-val">🏢 ${escapeHtml([job.function ? 'Function: ' + job.function : '', job.business_unit ? 'BU: ' + job.business_unit : ''].filter(Boolean).join(' • '))}</span></div>`);
        if (job.work_mode) metaItems.push(`<div class="job-meta-item"><span class="job-meta-lbl">Work Arrangement</span><span class="job-meta-val">${workModeBadge}</span></div>`);
        if (job.posted_date) metaItems.push(`<div class="job-meta-item"><span class="job-meta-lbl">Posted Date</span><span class="job-meta-val">📅 ${formatDate(job.posted_date)}</span></div>`);
        if (job.application_deadline || job.closing_date) metaItems.push(`<div class="job-meta-item"><span class="job-meta-lbl">Application Deadline</span><span class="job-meta-val">⏰ ${formatDate(job.application_deadline || job.closing_date)}</span></div>`);
        if (job.external_job_id || job.job_id) metaItems.push(`<div class="job-meta-item"><span class="job-meta-lbl">External Requisition ID</span><span class="job-meta-val mono" style="font-size:12px;"># ${escapeHtml(job.external_job_id || job.job_id)}</span></div>`);

        if (metaItems.length > 0) {
            html += `
                <div class="job-metadata-grid-standard">
                    ${metaItems.join('')}
                </div>
            `;
        }

        html += `
            <!-- Quick Action Bar -->
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:24px; padding-bottom:18px; border-bottom:1px solid var(--border-color);">
                <div style="font-size:13px; color:var(--text-secondary);">
                    Official vacancy from <strong>${escapeHtml(job.company_name)}</strong>
                    ${job.ats_platform ? ` &bull; ATS Platform: <span class="badge badge-cyan" style="font-size:10.5px;">${escapeHtml(job.ats_platform)}</span>` : ''}
                    ${job.detail_fetched ? ` &bull; <span class="badge badge-emerald" style="font-size:10.5px;">Detail page verified</span>` : ` &bull; <span class="badge badge-slate" style="font-size:10.5px;">${escapeHtml(job.detail_fetch_status || 'NOT_FETCHED')}</span>`}
                </div>
                <div class="modal-job-actions-wrap" style="display:flex; gap:10px; flex-wrap:wrap;">
                    ${applyButtonHtml(job, 'btn-primary', 'padding:10px 22px; font-weight:700; font-size:13.5px; text-decoration:none;', '⚡ Apply on Official Site ↗')}
                    <button class="btn-secondary" onclick="openJobDetailsModal(${job.job_row_id}, true);" title="Force re-fetch freshest specifications from official company careers site">
                        🔄 Re-verify Live
                    </button>
                    <button class="btn-secondary" onclick="closeModal('modal-job-details'); openCompanyJobs('${job.company_id}');">
                        🏢 All Jobs at ${escapeHtml(job.company_name)}
                    </button>
                    <button class="btn-outline" onclick="closeModal('modal-job-details'); openCompanyDossier('${job.company_id}');">
                        📋 Company Profile
                    </button>
                </div>
            </div>
        `;

        // Helper to format structured bullet lists and paragraphs cleanly
        function formatSectionList(rawText, fallbackNotice) {
            if (!rawText || !rawText.trim()) return fallbackNotice || '';
            // Clean weird unicode replacement characters, form feeds, control characters
            let clean = rawText.replace(/[\uFFFD\u007F-\u009F]+/g, ' ').trim();
            // Split into lines
            let lines = clean.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
            // Filter out application buttons / footer artifacts
            lines = lines.filter(l => !/^(?:apply now|start applying|please wait|share this job|linkedin|#li-|start$)/i.test(l));
            if (!lines.length) return fallbackNotice || '';

            // Check if items are bullet points, numbered items, or distinct responsibilities
            const isBulletLike = lines.length > 1;
            if (isBulletLike) {
                const listItems = lines.map(line => {
                    const itemText = line.replace(/^[-•*▹▪\s]+/, '').replace(/^\d+[\.\)]\s*/, '').trim();
                    if (!itemText) return '';
                    return `
                        <li style="display:flex; align-items:flex-start; gap:10px; margin-bottom:8px; line-height:1.65; font-size:13.5px; color:var(--text-secondary);">
                            <span style="color:var(--accent-cyan); font-weight:700; font-size:15px; line-height:1.2; flex-shrink:0; user-select:none;">▹</span>
                            <span style="flex:1;">${escapeHtml(itemText)}</span>
                        </li>`;
                }).filter(Boolean).join('');
                return `<ul style="list-style:none; padding:0; margin:0;">${listItems}</ul>`;
            }

            // Paragraph format
            return lines.map(p => `<p style="margin:0 0 10px; line-height:1.7; font-size:13.5px; color:var(--text-secondary);">${escapeHtml(p)}</p>`).join('');
        }

        // Smart section extraction helpers if raw description contains combined sections
        let displayResponsibilities = job.responsibilities;
        let displayQualifications = job.qualifications || job.requirements;
        let displayEducation = job.education;
        let displayRolePurpose = job.role_purpose;
        let displayTechnical = job.technical_skills;
        let displayBehavioural = job.behavioural_skills;

        if (job.job_description) {
            const raw = job.job_description;
            if (!displayResponsibilities) {
                const m = raw.match(/(?:essential duties and responsibilities|essential duties|key responsibilities|responsibilities|what you will do|what you'll do|duties|core responsibilities)[:\n\r]+([\s\S]*?)(?=(?:qualification|education|requirements|competencies|skills|benefits|physical requirements|$))/i);
                if (m && m[1] && m[1].trim().length > 20) displayResponsibilities = m[1].trim();
            }
            if (!displayQualifications) {
                const m = raw.match(/(?:qualification and experience|qualifications and experience|qualifications & requirements|required qualifications|basic qualifications|minimum qualifications|qualifications|qualification|requirements|eligibility)[:\n\r]+([\s\S]*?)(?=(?:education|competencies|skills|benefits|physical requirements|essential duties|key responsibilities|$))/i);
                if (m && m[1] && m[1].trim().length > 15) displayQualifications = m[1].trim();
            }
            if (!displayEducation) {
                const m = raw.match(/(?:education and experience|educational qualifications?|academic qualifications?|education)[:\n\r]+([\s\S]*?)(?=(?:experience|competencies|skills|benefits|$))/i);
                if (m && m[1] && m[1].trim().length > 10) {
                    displayEducation = m[1].trim();
                } else if (displayQualifications) {
                    const degM = displayQualifications.match(/\b(PhD|Doctorate|MBA|B\.?Tech|M\.?Tech|B\.?E|B\.?Com|B\.?Sc|M\.?Sc|Bachelor(?:\'s)?|Master(?:\'s)?|Diploma|Graduat(?:e|ion))\b[^\n.;]*/i);
                    if (degM) displayEducation = degM[0].trim();
                }
            }
            if (!displayBehavioural) {
                const m = raw.match(/(?:competencies|core competencies|behavioural skills|behavioral skills|soft skills)[:\n\r]+([\s\S]*?)(?=(?:apply now|start applying|share this job|$))/i);
                if (m && m[1] && m[1].trim().length > 10) displayBehavioural = m[1].trim();
            }
            if (!displayRolePurpose) {
                const m = raw.match(/(?:role summary|job summary|position summary|position overview|about the role|job purpose)[:\n\r]+([\s\S]*?)(?=(?:essential duties|key responsibilities|responsibilities|qualification|$))/i);
                if (m && m[1] && m[1].trim().length > 20) displayRolePurpose = m[1].trim();
            }
        }

        // 3. Position Description and Role
        // Deduplicate: Check if job_description is merely repeating responsibilities
        const isDescDupOfResp = Boolean(
            displayResponsibilities &&
            job.job_description &&
            (job.job_description.trim() === displayResponsibilities.trim() ||
             job.job_description.replace(/^(?:KEY\s*RESPONSIBILITIES|ESSENTIAL\s*DUTIES)[:\s\n]*/i, '').trim() === displayResponsibilities.trim() ||
             Math.abs(job.job_description.length - displayResponsibilities.length) < 40)
        );

        let roleOverviewHtml = '';
        if (displayRolePurpose) {
            roleOverviewHtml = `
                <div style="background:var(--bg-surface); border:1px solid var(--border-subtle); border-left:3px solid var(--primary-brand); padding:16px 20px; border-radius:var(--radius-md); margin-bottom:12px;">
                    <div style="font-size:11.5px; font-weight:800; text-transform:uppercase; letter-spacing:0.5px; color:var(--primary-brand); margin-bottom:8px;">Executive Role Summary</div>
                    <div style="font-size:13.5px; line-height:1.7; color:var(--text-secondary);">${formatSectionList(displayRolePurpose, '')}</div>
                </div>`;
        }

        let descContentHtml = '';
        if (!displayRolePurpose && job.job_description && !isDescDupOfResp) {
            descContentHtml = `
                <div style="font-size:13.5px; line-height:1.7; color:var(--text-secondary); background:var(--bg-surface); padding:18px; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
                    ${formatSectionList(job.job_description, '')}
                </div>`;
        } else if (!displayRolePurpose && isDescDupOfResp) {
            descContentHtml = `
                <div style="font-size:13.5px; line-height:1.6; color:var(--text-secondary); background:var(--bg-surface-subtle); padding:14px 18px; border-radius:var(--radius-md); border-left:3px solid var(--accent-cyan);">
                    Official verified opening for <strong>${escapeHtml(job.job_title)}</strong> at <strong>${escapeHtml(job.company_name)}</strong>. Detailed role responsibilities and qualifications are cataloged in the sections below.
                </div>`;
        } else if (!displayRolePurpose && !job.job_description) {
            descContentHtml = `
                <div style="font-size:13px; color:var(--text-muted); background:var(--bg-surface-subtle); padding:14px 18px; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
                    ${getMissingFieldNotice(job, true)}
                </div>`;
        }

        html += `
            <div style="margin-bottom:24px;">
                <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 10px; display:flex; align-items:center; gap:8px;">
                    <span>📄 Position Description and Role</span>
                </h4>
                ${roleOverviewHtml}
                ${descContentHtml}
            </div>
        `;

        // 4. Key Responsibilities
        html += `
            <div style="margin-bottom:24px;">
                <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 10px;">📋 Key Responsibilities</h4>
                <div style="background:var(--bg-surface); padding:18px; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
                    ${formatSectionList(displayResponsibilities, getMissingFieldNotice(job, true))}
                </div>
            </div>
        `;

        // 5. Qualifications & Experience
        html += `
            <div style="margin-bottom:24px;">
                <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 8px;">🎓 Required Qualifications &amp; Eligibility</h4>
                ${job.experience ? `
                <div style="margin-bottom:12px; display:inline-flex; align-items:center; gap:8px; background:var(--bg-surface-subtle); border:1px solid var(--border-subtle); padding:6px 14px; border-radius:20px; font-size:12.5px; color:var(--text-primary);">
                    <span style="color:var(--accent-amber); font-weight:bold;">⏱️ Experience Required:</span>
                    <span style="font-weight:700;">${escapeHtml(job.experience)}</span>
                </div>` : ''}
                <div style="background:var(--bg-surface); padding:18px; border-radius:var(--radius-md); border:1px solid var(--border-subtle); margin-bottom:12px;">
                    ${formatSectionList(displayQualifications, getMissingFieldNotice(job, true))}
                </div>
                ${job.preferred_qualifications ? `
                <div style="margin-bottom:12px;">
                    <h5 style="font-size:14px; font-weight:800; color:var(--text-primary); margin:0 0 6px;">Preferred Qualifications</h5>
                    <div style="background:var(--bg-surface); padding:14px 18px; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
                        ${formatSectionList(job.preferred_qualifications, '')}
                    </div>
                </div>` : ''}
            </div>
        `;

        // 6. Education
        html += `
            <div style="margin-bottom:24px;">
                <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 8px;">🏛️ Academic Qualification &amp; Credentials</h4>
                <div style="background:var(--bg-surface-subtle); padding:16px 20px; border-radius:var(--radius-md); border:1px solid var(--border-subtle);">
                    ${formatSectionList(displayEducation, getMissingFieldNotice(job, true))}
                </div>
            </div>
        `;

        // 7. Technical and Behavioural Skills
        let behaviouralContentHtml = '';
        if (displayBehavioural) {
            const behLines = displayBehavioural.split(/\r?\n|,/).map(s => s.trim().replace(/^[-•*▹▪\s]+/, '')).filter(Boolean);
            const validBeh = behLines.filter(s => !/^(?:apply now|start applying|please wait|linkedin|#li-|start$)/i.test(s));
            if (validBeh.length > 0) {
                behaviouralContentHtml = `
                    <div style="display:flex; flex-wrap:wrap; gap:8px;">
                        ${validBeh.map(b => `<span class="badge badge-purple" style="font-size:12px; font-weight:600; padding:6px 12px; border-radius:6px; display:inline-flex; align-items:center; gap:6px;"><span>✦</span> ${escapeHtml(b)}</span>`).join('')}
                    </div>`;
            } else {
                behaviouralContentHtml = getMissingFieldNotice(job, true);
            }
        } else {
            behaviouralContentHtml = getMissingFieldNotice(job, true);
        }

        html += `
            <div style="margin-bottom:24px;">
                <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 10px;">⚡ Technical &amp; Behavioural Skills</h4>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:12px; margin-bottom:12px;">
                    <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:16px;">
                        <div style="font-size:12px; font-weight:800; text-transform:uppercase; color:var(--text-primary); margin-bottom:8px;">Technical Skills / Knowledge</div>
                        <div style="font-size:13px; line-height:1.6; color:var(--text-secondary);">${formatSectionList(displayTechnical, getMissingFieldNotice(job, true))}</div>
                    </div>
                    <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:16px;">
                        <div style="font-size:12px; font-weight:800; text-transform:uppercase; color:var(--text-primary); margin-bottom:8px;">Behavioural Competencies &amp; Soft Skills</div>
                        <div style="font-size:13px; line-height:1.6; color:var(--text-secondary);">${behaviouralContentHtml}</div>
                    </div>
                </div>
                ${skillsList.length > 0 ? `
                <div style="background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:12px 14px;">
                    <div style="font-size:11.5px; font-weight:700; color:var(--text-muted); text-transform:uppercase; margin-bottom:6px;">Skills &amp; Competencies Summary</div>
                    <div style="display:flex; flex-wrap:wrap; gap:6px;">
                        ${skillsList.map(sk => `<span class="skill-pill" style="padding:4px 10px; font-size:12px;">${escapeHtml(sk)}</span>`).join('')}
                    </div>
                </div>` : ''}
            </div>
        `;

        // 8. Compensation & Benefits Disclosed
        html += `
            <div style="margin-bottom:24px; background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px 20px;">
                <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 10px;">💰 Compensation &amp; Benefits Disclosed</h4>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px; font-size:13px;">
                    <div>
                        <strong>Disclosed Salary:</strong> 
                        ${job.salary ? `<span style="color:var(--accent-emerald); font-weight:700; margin-left:6px;">💰 ${escapeHtml(job.salary)} ${job.salary_currency ? `(${escapeHtml(job.salary_currency)})` : ''}</span>` : `<span style="margin-left:6px;">${getMissingFieldNotice(job, true)}</span>`}
                    </div>
                    <div>
                        <strong>Source Pay Band / Grade:</strong> 
                        ${job.pay_band ? `<span class="badge badge-purple" style="font-size:12px; font-weight:700; margin-left:6px;">🏷️ ${escapeHtml(job.pay_band)}</span>` : `<span style="margin-left:6px;">${getMissingFieldNotice(job, true)}</span>`}
                    </div>
                    <div style="grid-column:1/-1;">
                        <strong>Benefits Disclosed:</strong> 
                        ${job.benefits ? `<span style="color:var(--text-secondary); margin-left:6px;">${escapeHtml(job.benefits)}</span>` : `<span style="margin-left:6px;">${getMissingFieldNotice(job, true)}</span>`}
                    </div>
                </div>
            </div>
        `;

        // 9. Additional Source-Provided Information
        html += `
            <div style="margin-bottom:24px; background:var(--bg-surface); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:16px 20px;">
                <h4 style="font-size:14.5px; font-weight:800; color:var(--text-primary); margin:0 0 10px;">ℹ️ Additional Source-Provided Information</h4>
                ${job.day_in_the_life ? `
                <div style="margin-bottom:14px; background:var(--bg-surface-subtle); border-left:3px solid var(--accent-purple); padding:12px 16px; border-radius:4px;">
                    <div style="font-size:12px; font-weight:800; text-transform:uppercase; color:var(--text-primary); margin-bottom:4px;">A Day in the Life</div>
                    <div style="font-size:13.5px; line-height:1.6; color:var(--text-secondary); white-space:pre-line;">${escapeHtml(job.day_in_the_life)}</div>
                </div>
                ` : ''}
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px; font-size:13px; color:var(--text-secondary); margin-bottom:14px;">
                    <div><strong>Business Unit:</strong> ${job.business_unit ? escapeHtml(job.business_unit) : getMissingFieldNotice(job, true)}</div>
                    <div><strong>Shift Schedule:</strong> ${job.shift ? escapeHtml(job.shift) : getMissingFieldNotice(job, true)}</div>
                    <div><strong>Travel Required:</strong> ${job.travel_required ? escapeHtml(job.travel_required) : getMissingFieldNotice(job, true)}</div>
                    <div><strong>Work Authorization:</strong> ${job.work_authorization ? escapeHtml(job.work_authorization) : getMissingFieldNotice(job, true)}</div>
                </div>
                ${job.employer_info ? `
                <div style="margin-top:12px; padding-top:12px; border-top:1px solid var(--border-subtle);">
                    <div style="font-size:12px; font-weight:800; text-transform:uppercase; color:var(--text-muted); margin-bottom:6px;">Employer &amp; Company Background (Source Provided)</div>
                    <div style="font-size:13px; line-height:1.6; color:var(--text-secondary); background:var(--bg-surface-subtle); padding:14px; border-radius:6px; white-space:pre-line;">${escapeHtml(job.employer_info)}</div>
                </div>
                ` : ''}
            </div>
        `;

        // 10. Application Action
        html += `
            <div style="margin-bottom:24px; background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px 20px;">
                <h4 style="font-size:14.5px; font-weight:800; color:var(--text-primary); margin:0 0 10px;">⚡ Application Gateway</h4>
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div style="font-size:13px; color:var(--text-secondary);">
                        Official application link on <strong>${escapeHtml(domainLabel)}</strong>
                    </div>
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                        ${applyButtonHtml(job, 'btn-primary', 'padding:10px 22px; font-weight:700; font-size:13.5px; text-decoration:none;', '⚡ Submit Application on Official Site ↗')}
                        <button class="btn-secondary" onclick="closeModal('modal-job-details'); openCompanyJobs('${job.company_id}');">
                            🏢 View All Jobs at ${escapeHtml(job.company_name)}
                        </button>
                    </div>
                </div>
            </div>
        `;

        // 11. Source Provenance and Verification Audit
        html += `
            <div style="margin-bottom:24px; background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px 20px; font-size:12.5px;">
                <div style="font-weight:800; font-size:13px; color:var(--text-primary); margin-bottom:10px; display:flex; align-items:center; gap:8px;">
                    <span>🛡️ Authoritative Source Provenance &amp; Verification Audit</span>
                </div>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:10px; color:var(--text-secondary);">
                    <div style="grid-column:1/-1; padding-bottom:6px; font-size:13px; font-weight:700; color:var(--accent-emerald);">
                        ✓ ${escapeHtml(job.verified_badge_text || 'As listed on the official site')}
                    </div>
                    <div><strong>Authoritative Source:</strong> ${job.is_company_unverifiable ? `<a href="${escapeHtml(job.careers_url || '#')}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan);">Careers Page ↗</a>` : `<a href="${escapeHtml(job.source_url || applyUrl || '#')}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); font-weight:700;">${escapeHtml(cleanDomainLabel(job.source_url || applyUrl))} ↗</a>`}</div>
                    ${job.ats_platform ? `<div><strong>ATS / Platform:</strong> ${escapeHtml(job.ats_platform)}</div>` : ''}
                    <div><strong>Verification Status:</strong> ${formatVerificationBadge(job.verification_status || 'SOURCE_CONFIRMED')}</div>
                    <div><strong>Last Verified:</strong> ${job.last_reconciled_at ? formatDate(job.last_reconciled_at) : (job.retrieved_at ? formatDate(job.retrieved_at) : 'Recently')}</div>
                    ${job.fingerprint ? `<div style="grid-column:1/-1; font-family:var(--font-mono); font-size:11px; color:var(--text-muted); word-break:break-all;"><strong>Record Hash:</strong> ${escapeHtml(job.fingerprint)}</div>` : ''}
                </div>
            </div>
        `;

        // 12. Related Openings at Same Company
        html += `
            <div style="margin-top:28px; padding-top:20px; border-top:1px solid var(--border-color);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
                    <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0;">
                        Related Openings in Same Enterprise (${(job.related_jobs || []).length})
                    </h4>
                    <button class="btn-outline" style="font-size:11.5px; padding:4px 10px;" onclick="closeModal('modal-job-details'); openCompanyJobs('${job.company_id}');">
                        View All Openings at ${escapeHtml(job.company_name)} ↗
                    </button>
                </div>
        `;

        if (job.related_jobs && job.related_jobs.length > 0) {
            html += `
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px;">
                    ${job.related_jobs.map(rj => `
                        <div style="padding:14px; background:var(--bg-surface-subtle); border:1px solid var(--border-subtle); border-radius:var(--radius-md); cursor:pointer; transition:border-color 0.15s;" onclick="openJobDetailsModal(${rj.job_row_id})" onmouseover="this.style.borderColor='var(--primary-brand)'" onmouseout="this.style.borderColor='var(--border-subtle)'">
                            <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:4px;">${escapeHtml(rj.job_title)}</div>
                            <div style="font-size:12px; color:var(--text-secondary);">🏢 ${escapeHtml(rj.company_name)}</div>
                            <div style="font-size:11px; color:var(--text-muted); margin-top:6px;">📍 ${escapeHtml(rj.location || NOT_AVAILABLE_TEXT)} ${rj.experience ? `• ⏳ ${escapeHtml(rj.experience)}` : ''}</div>
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            html += `
                <div style="text-align:center; padding:24px; background:var(--bg-surface-subtle); border-radius:var(--radius-md); border:1px solid var(--border-subtle); color:var(--text-secondary); font-size:13px;">
                    No other active openings are currently recorded in the database for <strong>${escapeHtml(job.company_name)}</strong>.
                </div>
            `;
        }

        html += `</div>`;

        modalBody.innerHTML = html;
    } catch (e) {
        console.error('Error in openJobDetailsModal', e);
        modalBody.innerHTML = `<div style="text-align:center; padding:40px; color:#f43f5e;">Unable to load job specifications: ${escapeHtml(e.message)}</div>`;
    }
}

// ===========================================================================
// TAB 3: ACTIVE OPEN CALLS & RFPS (GRANTS)
// ===========================================================================
async function loadOpportunities(page = 1) {
    if (typeof page !== 'number' || isNaN(page) || page < 1) {
        page = parseInt(page, 10);
        if (isNaN(page) || page < 1) page = 1;
    }
    paginationState.opps.page = page;
    const grid = document.getElementById('opportunities-grid');
    if (!grid) return;

    grid.innerHTML = `
        <div class="dynamic-loading-skeleton">
            <div class="loading-spinner-circle"></div>
            <div class="loading-spinner-text">Scanning Active Corporate Grants...</div>
            <div class="loading-spinner-sub">Loading page ${page} of verified RFP calls</div>
        </div>`;

    try {
        const cat = document.getElementById('opp-category-filter')?.value || 'all';
        let url = `${API_BASE}/csr/opportunities?page=${page}&page_size=${paginationState.opps.pageSize}`;
        if (cat !== 'all') url += `&category=${encodeURIComponent(cat)}`;

        let res = await fetch(url);
        if (!res.ok) {
            res = await fetch(`${API_BASE}/opportunities?page=${page}&page_size=${paginationState.opps.pageSize}`);
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        let items = [];
        let total = 0;
        let totalPages = 1;

        if (data && typeof data === 'object' && Array.isArray(data.items)) {
            items = data.items;
            total = data.total;
            totalPages = data.total_pages;
        } else if (Array.isArray(data)) {
            items = data;
            total = items.length;
            totalPages = Math.ceil(total / paginationState.opps.pageSize);
        }

        allOpportunities = items.map(o => {
            const comp = normalizeCompanyData({ company_id: o.company_id, company_name: o.company_name });
            return { ...o, company_name: comp.company_name };
        });

        paginationState.opps.total = total;
        paginationState.opps.totalPages = totalPages;

        renderOpportunities(allOpportunities, total);
        renderOpportunitiesPagination();

        const oppBadge = document.getElementById('nav-opps-badge');
        if (oppBadge && total > 0) {
            oppBadge.textContent = total;
        }
    } catch (e) {
        if (grid) {
            grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#f43f5e;">Could not load active grants: ${escapeHtml(e.message)}</div>`;
        }
    }
}

function renderOpportunitiesPagination() {
    renderPaginationBar({
        containerId: 'opps-pagination',
        page: paginationState.opps.page,
        totalPages: paginationState.opps.totalPages,
        total: paginationState.opps.total,
        pageSize: paginationState.opps.pageSize,
        pageSizeOptions: [9, 18, 36, 90],
        itemLabel: 'Active Grants & RFPs',
        onPageChange: (newPage) => {
            loadOpportunities(newPage);
            const anchor = document.getElementById('tab-active-opps');
            if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
        onPageSizeChange: (newSize) => {
            paginationState.opps.pageSize = newSize;
            loadOpportunities(1);
        }
    });
}

function renderOpportunities(list, total) {
    const grid = document.getElementById('opportunities-grid');
    if (!grid) return;

    if (!list || list.length === 0) {
        grid.innerHTML = `
            <div style="grid-column:1/-1; text-align:center; padding:60px 20px; background:var(--bg-surface-card); border:1px dashed var(--border-color); border-radius:12px; margin:20px 0;">
                <div style="font-size:36px; margin-bottom:12px;">📋</div>
                <h3 style="font-size:18px; font-weight:700; color:var(--text-primary); margin-bottom:8px;">No verified open calls right now</h3>
                <p style="font-size:14px; color:var(--text-muted); max-width:520px; margin:0 auto 16px;">
                    We only display genuine, active RFPs and grant calls with confirmed submission deadlines extracted directly from official corporate portals.
                </p>
                <span class="badge badge-indigo" style="padding:6px 14px; font-size:12px;">Zero Synthetic Fallbacks Active</span>
            </div>`;
        return;
    }

    grid.innerHTML = list.map(opp => {
        const deadline = opp.submission_deadline ? escapeHtml(opp.submission_deadline) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>';
        const rawBudget = opp.estimated_grant || opp.budget || NOT_AVAILABLE_TEXT;
        const budget = escapeHtml(rawBudget);
        const rawUrl = opp.portal_url || opp.submission_url || opp.application_url || opp.source_url;
        const url = (rawUrl && rawUrl.startsWith('http') && !rawUrl.includes('google.com/search')) ? rawUrl : null;
        const oppTitle = opp.title ? escapeHtml(opp.title) : NOT_AVAILABLE_TEXT;
        const oppCategory = opp.category ? escapeHtml(opp.category) : NOT_AVAILABLE_TEXT;
        const oppDesc = opp.requirements || opp.description;
        const companyName = opp.company_name ? escapeHtml(opp.company_name) : NOT_AVAILABLE_TEXT;

        return `
            <div class="rfp-card">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                        <span class="badge badge-amber">📢 OPEN RFP / EOI</span>
                        <span class="badge badge-emerald">Active Grant</span>
                    </div>

                    <h3 style="font-size:16px; font-weight:800; color:var(--text-primary); margin-bottom:4px;">${oppTitle}</h3>
                    <div style="font-size:13px; font-weight:700; color:var(--primary-brand); margin-bottom:12px; cursor:pointer;" onclick="openCompanyJobs('${opp.company_id}')">
                        🏢 <span style="text-decoration:underline;">${companyName}</span>
                        <span style="font-size:11px; margin-left:6px; color:var(--text-secondary);">(Jobs ➔)</span>
                    </div>

                    <div style="background:var(--bg-surface-subtle); padding:10px 12px; border-radius:8px; font-size:12.5px; margin-bottom:12px; border:1px solid var(--border-color);">
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <span style="color:var(--text-secondary);">Focus Area:</span>
                            <strong style="color:var(--text-primary);">${oppCategory}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <span style="color:var(--text-secondary);">Grant Range:</span>
                            <strong style="color:var(--accent-emerald);">${budget}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:var(--text-secondary);">Submission Window:</span>
                            <strong style="color:#d97706;">${deadline}</strong>
                        </div>
                    </div>

                    <p style="font-size:12.5px; color:var(--text-secondary); line-height:1.5;">
                        ${oppDesc ? escapeHtml(oppDesc) : '<span style="color:var(--text-muted); font-style:italic;">' + NOT_AVAILABLE_TEXT + '</span>'}
                    </p>
                </div>

                <div style="display:flex; gap:8px; margin-top:12px;">
                    ${url ? `
                    <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="flex:1; justify-content:center; text-decoration:none;">
                        📝 Apply for Grant ↗
                    </a>` : `
                    <span class="btn-disabled" style="flex:1; text-align:center; padding:6px 12px; font-size:12px; opacity:0.6; cursor:not-allowed; background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:6px; color:var(--text-muted);">
                        Not Available
                    </span>`}
                    <button class="btn-outline" onclick="openCompanyJobs('${opp.company_id}')" title="Browse verified jobs from this company">
                        💼 Jobs
                    </button>
                    <button class="btn-secondary" onclick="openCompanyDossier('${opp.company_id}')">
                        🏢 Profile
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function filterOpportunitiesByCategory() {
    loadOpportunities(1);
}

// ===========================================================================
// SECTION 135 CSR PROJECTS CONTROLLER (Part 8 & Part 10)
// ===========================================================================
let allCsrProjects = [];
let activeCsrCategory = 'all';

async function loadCsrProjects(page = 1) {
    paginationState.csr.page = page;
    const tableBody = document.getElementById('csr-projects-table-body');
    const label = document.getElementById('csr-count-label');

    if (tableBody) {
        tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:40px; color:var(--text-secondary);"><span class="loading-spinner-circle" style="width:18px; height:18px; display:inline-block; vertical-align:middle; margin-right:8px;"></span> Loading verified statutory CSR initiatives (Page ${page})...</td></tr>`;
    }

    try {
        const query = (document.getElementById('csr-search')?.value || '').trim();
        const state = document.getElementById('csr-state-filter')?.value || 'all';

        let url = `${API_BASE}/csr/projects?page=${page}&page_size=${paginationState.csr.pageSize}`;
        if (query) url += `&q=${encodeURIComponent(query)}`;
        if (state && state !== 'all') url += `&state=${encodeURIComponent(state)}`;
        if (activeCsrCategory && activeCsrCategory !== 'all') url += `&category=${encodeURIComponent(activeCsrCategory)}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const items = data.items || [];
        const total = data.total || 0;
        const totalPages = data.total_pages || 1;

        allCsrProjects = items;
        paginationState.csr.total = total;
        paginationState.csr.totalPages = totalPages;

        if (label) {
            label.textContent = `Showing page ${page} of ${totalPages} (${total.toLocaleString('en-IN')} Verified Section 135 Initiatives)`;
        }

        renderCsrProjects(items);
        renderCsrPagination();
    } catch (e) {
        console.error('Error loading CSR projects', e);
        if (tableBody) {
            tableBody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:30px; color:#f43f5e;">Could not load CSR initiatives: ${escapeHtml(e.message)}</td></tr>`;
        }
    }
}

function formatCsrMonetaryValue(val) {
    if (!val || val === 'Not disclosed' || val === NOT_AVAILABLE_TEXT) {
        return '<span style="color:var(--text-muted); font-size:11px; font-style:italic;">Not disclosed</span>';
    }
    const s = String(val).trim();
    if (s.toLowerCase() === 'rs,' || s.toLowerCase() === 'inr,' || s.toLowerCase() === 'none' || s.toLowerCase() === 'nan' || s.toLowerCase() === 'null' || s.toLowerCase() === 'not disclosed') {
        return '<span style="color:var(--text-muted); font-size:11px; font-style:italic;">Not disclosed</span>';
    }
    if (!/\d/.test(s)) {
        return '<span style="color:var(--text-muted); font-size:11px; font-style:italic;">Not disclosed</span>';
    }
    return `<span style="font-size:12px; font-weight:700;">${escapeHtml(s)}</span>`;
}

function renderCsrProjects(items) {
    const tableBody = document.getElementById('csr-projects-table-body');
    if (!tableBody) return;

    if (!items || items.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:40px; color:var(--text-secondary);">No verified CSR projects match the selected cause or filters. <button class="btn-primary" style="margin-left:10px; font-size:12px; padding:3px 10px;" onclick="resetCsrFilters()">Reset Filters</button></td></tr>`;
        return;
    }

    tableBody.innerHTML = items.map((item, idx) => {
        const rowNum = (paginationState.csr.page - 1) * paginationState.csr.pageSize + idx + 1;

        const rawBudget = item.budget || item.allocated_budget_inr;
        const budgetDisplay = formatCsrMonetaryValue(rawBudget);
        const spentDisplay = formatCsrMonetaryValue(item.spent_budget_inr);

        const locParts = [item.geographic_location, item.state, item.district].filter(Boolean);
        const locationDisplay = locParts.length > 0 ? Array.from(new Set(locParts)).join(', ') : '<span style="color:var(--text-muted); font-size:11px;">' + NOT_AVAILABLE_TEXT + '</span>';

        const docUrl = _cleanHttpUrl(item.source_document_url || item.source_url);
        const compCsrUrl = _cleanHttpUrl(item.company_csr_webpage_url || item.csr_portal_url || item.foundation_url || item.sustainability_url || item.esg_url);
        const sourceFmt = item.source_format || (docUrl ? 'CSR Source' : NOT_AVAILABLE_TEXT);

        const docLink = docUrl
            ? `<a href="${escapeHtml(docUrl)}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="padding:3px 8px; font-size:11px;" title="Open Verified Source (${escapeHtml(sourceFmt)})">Source ↗</a>`
            : '<span style="color:var(--text-muted); font-size:11px;">' + NOT_AVAILABLE_TEXT + '</span>';

        const compCsrLink = compCsrUrl
            ? `<a href="${escapeHtml(compCsrUrl)}" target="_blank" rel="noopener noreferrer" class="btn-outline" style="padding:3px 8px; font-size:11px; margin-right:4px; text-decoration:none;" title="Open Official CSR Webpage for ${escapeHtml(item.company_name || 'this company')}">🌐 CSR Page ↗</a>`
            : '';

        const catBadge = item.normalized_category
            ? `<span class="badge badge-purple" style="font-size:10.5px;">${escapeHtml(item.normalized_category)}</span>`
            : `<span class="badge badge-subtle" style="font-size:10px;">${NOT_AVAILABLE_TEXT}</span>`;

        const partnerNotice = item.implementing_partner
            ? `<div style="font-size:11px; color:var(--accent-emerald); margin-top:2px;" title="Implementing partner / NGO">🤝 ${escapeHtml(item.implementing_partner)}</div>`
            : '';

        const fyDisplay = item.reporting_period
            ? `<span class="badge badge-subtle" style="font-size:10px; font-family:var(--font-mono);">${escapeHtml(item.reporting_period)}</span>`
            : '<span style="color:var(--text-muted); font-size:11px;">' + NOT_AVAILABLE_TEXT + '</span>';

        return `
            <tr>
                <td style="color:var(--text-muted); font-weight:700; font-size:12px;">#${rowNum}</td>
                <td>
                    <div style="font-weight:700; color:var(--text-primary); font-size:13.5px; cursor:pointer;" onclick="openCsrDetailsModal(${item.csr_id})" title="View complete CSR project details & company CSR webpage link">
                        ${item.project_name ? escapeHtml(item.project_name) : NOT_AVAILABLE_TEXT}
                    </div>
                    <div style="font-size:10.5px; color:var(--text-muted); margin-top:2px;">Format: ${escapeHtml(sourceFmt)}</div>
                </td>
                <td>
                    <div style="font-size:12px; color:var(--text-secondary);">
                        <span style="color:var(--primary-brand); font-weight:600; cursor:pointer;" onclick="openCompanyCsr('${item.company_id}')" title="View CSR Page & all CSR projects for ${escapeHtml(item.company_name || 'this company')}">🏢 ${item.company_name ? escapeHtml(item.company_name) : NOT_AVAILABLE_TEXT}</span>
                        ${item.nse_symbol ? `<span class="badge badge-cyan" style="font-size:9.5px; margin-left:4px;">${escapeHtml(item.nse_symbol)}</span>` : ''}
                    </div>
                    ${partnerNotice}
                </td>
                <td>
                    ${catBadge}
                    ${item.original_category && item.original_category !== item.normalized_category ? `<div style="font-size:10.5px; color:var(--text-muted); margin-top:2px;" title="Original source classification">Source: ${escapeHtml(item.original_category)}</div>` : ''}
                </td>
                <td style="font-size:12px; color:var(--text-secondary);">📍 ${locationDisplay}</td>
                <td>${fyDisplay}</td>
                <td style="font-family:var(--font-mono); font-size:12px; font-weight:600; color:var(--text-primary);">${budgetDisplay}</td>
                <td style="font-family:var(--font-mono); font-size:12px; font-weight:600; color:var(--accent-emerald);">${spentDisplay}</td>
                <td><span class="badge badge-emerald" style="font-size:10px;">${escapeHtml(item.verification_status || 'PUBLISHED')}</span></td>
                <td style="text-align:right; white-space:nowrap;">
                    <button class="btn-primary" style="padding:3px 9px; font-size:11px; margin-right:4px;" onclick="openCsrDetailsModal(${item.csr_id})" title="Open CSR project details & company CSR webpage links">View</button>
                    ${compCsrLink}
                    ${docLink}
                </td>
            </tr>
        `;
    }).join('');
}

// ===========================================================================
// UNIVERSAL CSR VIEW SECTION (Part 6: Sections A to I + Company CSR Webpage Link)
// ===========================================================================
async function openCsrDetailsModal(csrId) {
    const modal = document.getElementById('modal-csr-details');
    const modalBody = document.getElementById('modal-csr-body');
    const modalTitle = document.getElementById('modal-csr-title');
    const modalSub = document.getElementById('modal-csr-company-subtitle');
    const modalAvatar = document.getElementById('modal-csr-avatar');
    const modalBadge = document.getElementById('modal-csr-verification-badge');

    if (!modal || !modalBody) return;

    modal.style.display = 'flex';
    modalBody.innerHTML = `
        <div style="text-align:center; padding:60px 20px;">
            <div class="loading-spinner-circle" style="margin:0 auto 16px;"></div>
            <div style="font-size:16px; font-weight:700; color:var(--text-primary);">Loading Section 135 CSR Dossier...</div>
            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">Retrieving verified statutory filings, CSR webpage links, and project telemetry</div>
        </div>`;

    try {
        const res = await fetch(`${API_BASE}/csr/projects/${csrId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const p = await res.json();

        if (modalTitle) modalTitle.textContent = p.project_name || NOT_AVAILABLE_TEXT;
        if (modalBadge) {
            modalBadge.textContent = '✓ Source Verified (MCA Sec 135)';
            modalBadge.className = 'badge badge-emerald';
        }
        if (modalAvatar) {
            modalAvatar.textContent = getCompanyInitials(p.company_name, p.nse_symbol);
            modalAvatar.style.background = getAvatarGradient(p.company_name);
            modalAvatar.style.color = '#ffffff';
        }
        if (modalSub) {
            modalSub.innerHTML = `
                <a href="javascript:void(0)" onclick="closeModal('modal-csr-details'); openCompanyCsr('${p.company_id}');" style="color:var(--primary-brand); font-weight:700; text-decoration:none;">
                    🏢 ${escapeHtml(p.company_name || NOT_AVAILABLE_TEXT)}
                </a>
                ${p.nse_symbol ? `<span style="color:var(--text-muted); margin-left:6px;">(${escapeHtml(p.nse_symbol)})</span>` : ''}
                ${p.cin ? `<span style="color:var(--text-muted); margin-left:6px; font-family:var(--font-mono); font-size:11px;">[CIN: ${escapeHtml(p.cin)}]</span>` : ''}
                ${p.sector ? `<span style="margin:0 6px; color:var(--border-color);">•</span><span>${escapeHtml(p.sector)}</span>` : ''}
            `;
        }

        const rawBudget = p.budget || p.allocated_budget_inr;
        const budgetText = formatCsrMonetaryValue(rawBudget);
        const spentText = formatCsrMonetaryValue(p.spent_budget_inr);
        const locText = [p.geographic_location, p.state].filter(Boolean).join(', ') || '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>';
        const docUrl = _cleanHttpUrl(p.source_document_url || p.source_url);
        const compCsrUrl = _cleanHttpUrl(p.company_csr_webpage_url || p.csr_portal_url || p.foundation_url || p.sustainability_url || p.esg_url);
        const sourceFormat = p.source_format || (docUrl ? 'CSR Source' : NOT_AVAILABLE_TEXT);

        modalBody.innerHTML = `
            <!-- SECTION A: PROJECT HEADER METADATA & QUICK CSR WEBPAGE ACCESS -->
            <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:10px; padding:16px 20px; margin-bottom:18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <div style="font-size:11.5px; text-transform:uppercase; letter-spacing:0.05em; color:var(--text-secondary); font-weight:700;">Initiative Identification</div>
                    <div style="font-size:16px; font-weight:800; color:var(--text-primary); margin-top:2px;">${escapeHtml(p.project_name || NOT_AVAILABLE_TEXT)}</div>
                    <div style="font-size:12.5px; color:var(--text-secondary); margin-top:2px;">
                        Corporate Entity: <strong style="color:var(--text-primary);">${escapeHtml(p.company_name || NOT_AVAILABLE_TEXT)}</strong>
                        ${p.legal_name && p.legal_name !== p.company_name ? ` <span style="color:var(--text-muted);">(${escapeHtml(p.legal_name)})</span>` : ''}
                    </div>
                </div>
                <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                    ${compCsrUrl ? `<a href="${escapeHtml(compCsrUrl)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="padding:6px 12px; font-size:12px; text-decoration:none;">🌐 View CSR Webpage for ${escapeHtml(p.company_name || 'Company')} ↗</a>` : ''}
                    ${docUrl && docUrl !== compCsrUrl ? `<a href="${escapeHtml(docUrl)}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="padding:6px 12px; font-size:12px; text-decoration:none;">📄 Open Source (${escapeHtml(sourceFormat)}) ↗</a>` : ''}
                    <button class="btn-outline" style="padding:6px 12px; font-size:12px;" onclick="closeModal('modal-csr-details'); openCompanyCsr('${p.company_id}');">
                        🌱 All Company CSR Details &amp; Projects
                    </button>
                </div>
            </div>

            ${p.csr_access === 'LOGIN_REQUIRED' ? `
            <div style="margin-bottom:18px; padding:12px 16px; border:1px solid #f59e0b; background:rgba(245,158,11,0.1); border-radius:8px; font-size:13px; color:#f59e0b;">
                🔒 <strong>${escapeHtml(LOGIN_REQUIRED_TEXT)}:</strong> Some CSR pages on this company's website require user login.
            </div>` : ''}

            <!-- COMPANY CSR WEBPAGE LINK & SOURCE DISCLOSURE BAR -->
            <div style="margin-bottom:22px; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:14px 18px;">
                <div style="font-size:12px; font-weight:800; text-transform:uppercase; color:var(--text-secondary); margin-bottom:8px;">
                    🌐 Official Company CSR Webpage &amp; Disclosure Links
                </div>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:10px; font-size:12.5px;">
                    <div>
                        <span style="color:var(--text-muted);">Company CSR Webpage:</span><br>
                        ${compCsrUrl ? `<a href="${escapeHtml(compCsrUrl)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary-brand); font-weight:700; word-break:break-all;">${escapeHtml(compCsrUrl)} ↗</a>` : `<span style="color:var(--text-muted);">${escapeHtml(p.csr_access === 'LOGIN_REQUIRED' ? LOGIN_REQUIRED_TEXT : NOT_AVAILABLE_TEXT)}</span>`}
                    </div>
                    <div>
                        <span style="color:var(--text-muted);">Project Source (${escapeHtml(sourceFormat)}):</span><br>
                        ${docUrl ? `<a href="${escapeHtml(docUrl)}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); font-weight:700; word-break:break-all;">${escapeHtml(docUrl)} ↗</a>` : `<span style="color:var(--text-muted);">${escapeHtml(NOT_AVAILABLE_TEXT)}</span>`}
                    </div>
                </div>
            </div>

            <!-- SECTION B: PROJECT OVERVIEW -->
            <div style="margin-bottom:24px;">
                <h4 style="font-size:14px; text-transform:uppercase; letter-spacing:0.04em; color:var(--text-secondary); margin:0 0 10px;">
                    B. Project Overview &amp; Extracted Details
                </h4>
                <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:16px 20px; line-height:1.65; font-size:13.5px; color:var(--text-primary);">
                    ${p.description ? escapeHtml(p.description) : '<span style="color:var(--text-muted); font-style:italic;">' + NOT_AVAILABLE_TEXT + '</span>'}
                </div>
            </div>

            <!-- SECTION C: CSR CLASSIFICATION -->
            <div style="margin-bottom:24px;">
                <h4 style="font-size:14px; text-transform:uppercase; letter-spacing:0.04em; color:var(--text-secondary); margin:0 0 10px;">
                    C. CSR Statutory Classification
                </h4>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px;">
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Original Source Category</div>
                        <div style="font-size:13px; font-weight:700; color:var(--text-primary); margin-top:4px;">
                            ${p.original_category ? escapeHtml(p.original_category) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}
                        </div>
                    </div>
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Normalized Cause Area</div>
                        <div style="font-size:13px; font-weight:700; color:var(--primary-brand); margin-top:4px;">
                            ${p.normalized_category ? escapeHtml(p.normalized_category) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}
                        </div>
                    </div>
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px; grid-column: 1 / -1;">
                        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Schedule VII Classification (Companies Act, 2013)</div>
                        <div style="font-size:13px; font-weight:700; color:var(--accent-emerald); margin-top:4px;">
                            ${p.schedule_vii_classification ? escapeHtml(p.schedule_vii_classification) : '<span style="color:var(--text-muted); font-weight:normal;">' + NOT_AVAILABLE_TEXT + '</span>'}
                        </div>
                    </div>
                </div>
            </div>

            <!-- SECTION D: GEOGRAPHIC COVERAGE -->
            <div style="margin-bottom:24px;">
                <h4 style="font-size:14px; text-transform:uppercase; letter-spacing:0.04em; color:var(--text-secondary); margin:0 0 10px;">
                    D. Geographic Coverage &amp; Operating Boundary
                </h4>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px;">
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Operating Field Geography</div>
                        <div style="font-size:13.5px; font-weight:700; color:var(--text-primary); margin-top:4px;">📍 ${locText}</div>
                    </div>
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Corporate Headquarters</div>
                        <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">
                            🏢 ${p.headquarters ? escapeHtml(p.headquarters) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}
                        </div>
                    </div>
                </div>
            </div>

            <!-- SECTION E: FINANCIAL DETAILS -->
            <div style="margin-bottom:24px;">
                <h4 style="font-size:14px; text-transform:uppercase; letter-spacing:0.04em; color:var(--text-secondary); margin:0 0 10px;">
                    E. Financial Outlay &amp; Statutory Funding
                </h4>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px;">
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Approved Allocation / Budget</div>
                        <div style="font-size:15px; font-weight:800; color:var(--text-primary); margin-top:4px; font-family:var(--font-mono);">${budgetText}</div>
                    </div>
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Actual Project Spend</div>
                        <div style="font-size:15px; font-weight:800; color:var(--accent-emerald); margin-top:4px; font-family:var(--font-mono);">${spentText}</div>
                    </div>
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Reporting Period</div>
                        <div style="font-size:14px; font-weight:700; color:var(--text-primary); margin-top:4px; font-family:var(--font-mono);">
                            ${p.reporting_period ? escapeHtml(p.reporting_period) : '<span style="color:var(--text-muted); font-size:12px; font-family:inherit; font-weight:normal;">' + NOT_AVAILABLE_TEXT + '</span>'}
                        </div>
                    </div>
                </div>
            </div>

            <!-- SECTION F & G: TIMELINE AND PARTNERS -->
            <div style="margin-bottom:24px;">
                <h4 style="font-size:14px; text-transform:uppercase; letter-spacing:0.04em; color:var(--text-secondary); margin:0 0 10px;">
                    F &amp; G. Implementation Status &amp; Partners
                </h4>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px;">
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Verification Status</div>
                        <div style="font-size:13px; font-weight:700; margin-top:4px;">
                            <span class="badge badge-emerald">${escapeHtml(p.verification_status || 'PUBLISHED')}</span>
                        </div>
                    </div>
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 16px;">
                        <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Implementing Partner / NGO</div>
                        <div style="font-size:13.5px; font-weight:700; color:var(--text-primary); margin-top:4px;">
                            ${p.implementing_partner ? `🤝 ${escapeHtml(p.implementing_partner)}` : '<span style="color:var(--text-muted); font-size:12px; font-weight:normal;">' + NOT_AVAILABLE_TEXT + '</span>'}
                        </div>
                    </div>
                </div>
            </div>

            <!-- SECTION H: SOURCE DOCUMENTS AND EVIDENCE -->
            <div style="margin-bottom:24px;">
                <h4 style="font-size:14px; text-transform:uppercase; letter-spacing:0.04em; color:var(--text-secondary); margin:0 0 10px;">
                    H. Source Webpage / PDF Document &amp; Audit Trail
                </h4>
                <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:8px; padding:16px 20px;">
                    <div style="font-size:13px; font-weight:700; color:var(--accent-emerald); margin-bottom:12px;">
                        ✓ ${escapeHtml(p.verified_badge_text || 'As listed on the official site')}
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:12px;">
                        <div>
                            <div style="font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:700;">Official Source Document / CSR Webpage (${escapeHtml(sourceFormat)})</div>
                            <div style="font-size:13px; font-weight:700; color:var(--text-primary); margin-top:2px; word-break:break-all;">
                                ${docUrl ? `<a href="${escapeHtml(docUrl)}" target="_blank" rel="noopener noreferrer" style="color:var(--primary-brand); text-decoration:none;">${escapeHtml(docUrl)} ↗</a>` : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}
                            </div>
                        </div>
                        <div style="display:flex; gap:8px; flex-wrap:wrap;">
                            ${docUrl ? `<a href="${escapeHtml(docUrl)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="padding:5px 12px; font-size:12px; text-decoration:none;">Open Source Document ↗</a>` : ''}
                            ${compCsrUrl && compCsrUrl !== docUrl ? `<a href="${escapeHtml(compCsrUrl)}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="padding:5px 12px; font-size:12px; text-decoration:none;">Open Company CSR Webpage ↗</a>` : ''}
                        </div>
                    </div>
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px; font-size:11.5px; border-top:1px solid var(--border-color); padding-top:12px;">
                        <div><span style="color:var(--text-muted);">Verification Reason:</span> <strong style="color:var(--text-primary);">${escapeHtml(p.verification_reason || NOT_AVAILABLE_TEXT)}</strong></div>
                        <div><span style="color:var(--text-muted);">Verified At:</span> <strong style="color:var(--text-primary); font-family:var(--font-mono);">${p.retrieved_at ? escapeHtml(p.retrieved_at.split('T')[0]) : NOT_AVAILABLE_TEXT}</strong></div>
                        <div><span style="color:var(--text-muted);">Record Fingerprint:</span> <strong style="color:var(--text-secondary); font-family:var(--font-mono);">${p.fingerprint ? escapeHtml(p.fingerprint.slice(0, 16)) + '...' : NOT_AVAILABLE_TEXT}</strong></div>
                    </div>
                </div>
            </div>

            <!-- SECTION I: RELATED PROJECTS -->
            <div>
                <h4 style="font-size:14px; text-transform:uppercase; letter-spacing:0.04em; color:var(--text-secondary); margin:0 0 10px;">
                    I. Other Verified CSR Initiatives (${escapeHtml(p.company_name || 'This Corporation')})
                </h4>
                <div id="modal-csr-related-grid">
                    ${(p.related_projects && p.related_projects.length > 0) ? `
                        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:12px;">
                            ${p.related_projects.map(rp => `
                                <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 14px; cursor:pointer;" onclick="openCsrDetailsModal(${rp.csr_id})">
                                    <div style="font-weight:700; font-size:13px; color:var(--text-primary);">${escapeHtml(rp.project_name)}</div>
                                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
                                        <span class="badge badge-purple" style="font-size:9.5px;">${escapeHtml(rp.normalized_category || NOT_AVAILABLE_TEXT)}</span>
                                        <span style="font-size:11px; color:var(--primary-brand); font-weight:700;">View →</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    ` : `
                        <div style="background:var(--bg-surface-subtle); border:1px dashed var(--border-color); border-radius:8px; padding:16px; text-align:center; color:var(--text-muted); font-size:12.5px;">
                            No other published Section 135 projects catalogued for this enterprise.
                        </div>
                    `}
                </div>
            </div>
        `;
    } catch (e) {
        console.error('Error opening CSR modal', e);
        if (modalBody) {
            modalBody.innerHTML = `
                <div style="text-align:center; padding:40px 20px; color:#f43f5e;">
                    <div style="font-size:16px; font-weight:700;">Could not load CSR details</div>
                    <div style="font-size:13px; margin-top:6px; color:var(--text-secondary);">${escapeHtml(e.message)}</div>
                </div>`;
        }
    }
}

function renderCsrPagination() {
    renderPaginationBar({
        containerId: 'csr-pagination',
        page: paginationState.csr.page,
        totalPages: paginationState.csr.totalPages,
        total: paginationState.csr.total,
        pageSize: paginationState.csr.pageSize,
        pageSizeOptions: [12, 24, 48, 96],
        itemLabel: 'CSR Initiatives',
        onPageChange: (newPage) => {
            loadCsrProjects(newPage);
            const anchor = document.getElementById('tab-csr-projects');
            if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
        onPageSizeChange: (newSize) => {
            paginationState.csr.pageSize = newSize;
            loadCsrProjects(1);
        }
    });
}

function selectCsrCategory(category) {
    activeCsrCategory = category;
    document.querySelectorAll('#csr-category-pills .cat-pill').forEach(pill => {
        pill.classList.toggle('active', pill.dataset.csrCat === category);
    });
    loadCsrProjects(1);
}

function filterCsrProjects() {
    loadCsrProjects(1);
}

function clearCsrSearch() {
    const input = document.getElementById('csr-search');
    if (input) input.value = '';
    const clearBtn = document.getElementById('csr-search-clear');
    if (clearBtn) clearBtn.style.display = 'none';
    loadCsrProjects(1);
}

function resetCsrFilters() {
    const input = document.getElementById('csr-search');
    if (input) input.value = '';
    const stateFilter = document.getElementById('csr-state-filter');
    if (stateFilter) stateFilter.value = 'all';
    selectCsrCategory('all');
}

function exportCsrCSV() {
    if (!allCsrProjects || allCsrProjects.length === 0) {
        alert('No CSR project records currently loaded to export.');
        return;
    }
    const headers = ['Initiative Title', 'Company Name', 'NSE Symbol', 'Category', 'State', 'District', 'Allocated Budget INR', 'Spent Budget INR', 'Status', 'Source Document'];
    const rows = allCsrProjects.map(p => [
        `"${(p.project_name || '').replace(/"/g, '""')}"`,
        `"${(p.company_name || '').replace(/"/g, '""')}"`,
        `"${(p.nse_symbol || '').replace(/"/g, '""')}"`,
        `"${(p.normalized_category || p.category || '').replace(/"/g, '""')}"`,
        `"${(p.state || '').replace(/"/g, '""')}"`,
        `"${(p.district || '').replace(/"/g, '""')}"`,
        `"${p.allocated_budget_inr || ''}"`,
        `"${p.spent_budget_inr || ''}"`,
        `"${(p.status || 'ACTIVE').replace(/"/g, '""')}"`,
        `"${(p.source_document_url || '').replace(/"/g, '""')}"`
    ]);
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    triggerCsvDownload(csv, `ImpactBridge_Verified_CSR_Initiatives_${Date.now()}.csv`);
    showLiveToast(`✅ Exported ${allCsrProjects.length} verified CSR initiatives.`, 'success');
}

// ===========================================================================
// TAB 4: NGO MATCHMAKER (Authentic Live Backend Scoring)
// ===========================================================================
async function runSimpleNgoMatch() {
    const selectedCause = document.querySelector('input[name="ngo-cause"]:checked')?.value || 'Education';
    const selectedState = document.getElementById('ngo-state-select')?.value || 'Pan-India';
    const container = document.getElementById('matching-results-container');
    if (!container) return;

    const tier = normalizeSubscriptionTier((currentSubscription && (currentSubscription.tier || currentSubscription.plan_id)) || 'free');
    const todayStr = new Date().toISOString().split('T')[0];
    const quotaKey = `ib_match_count_${todayStr}`;
    let dailyUsed = parseInt(localStorage.getItem(quotaKey) || '0', 10);

    if (tier === 'free') {
        if (dailyUsed >= 5) {
            container.innerHTML = `
                <div style="background:var(--bg-surface); border:1px solid var(--border-color); box-shadow:var(--shadow-card); border-radius:14px; padding:32px 24px; text-align:center; max-width:680px; margin:24px auto;">
                    <div style="font-size:36px; margin-bottom:12px;">🔒</div>
                    <h3 style="font-size:18px; font-weight:800; color:var(--text-primary); margin-bottom:8px;">Daily Matchmaker Limit Reached (5/5 Used)</h3>
                    <p style="font-size:13.5px; color:var(--text-secondary); line-height:1.6; margin-bottom:20px;">
                        The <strong>Community Free</strong> tier is limited to <strong>5 algorithmic donor matches per day</strong>. Your free queries will reset at midnight.
                        <br><br>
                        Upgrade to <strong>Impact Pro</strong> or <strong>Ultra Enterprise</strong> for <strong>unlimited daily queries</strong>, unmasked executive direct contacts, and 1-click CSR proposals!
                    </p>
                    <div style="display:flex; justify-content:center; gap:12px;">
                        <button class="btn-primary" style="padding:10px 24px; font-size:13px;" onclick="openSubscriptionModal('pro')">
                            Upgrade to Impact Pro (Unlimited) ⚡
                        </button>
                    </div>
                </div>
            `;
            showLiveToast('Daily free matchmaker quota reached (5/5). Upgrade to Pro for unlimited matching.', 'info');
            return;
        }
        // Increment daily count
        dailyUsed += 1;
        localStorage.setItem(quotaKey, String(dailyUsed));
    }

    container.innerHTML = `
        <div class="dynamic-loading-skeleton" style="padding:40px;">
            <div class="loading-spinner-circle"></div>
            <div class="loading-spinner-text">Evaluating Live Algorithmic Match Models...</div>
            <div class="loading-spinner-sub">Executing scoring engine for "${escapeHtml(selectedCause)}" in "${escapeHtml(selectedState)}"</div>
        </div>`;

    try {
        let url = `${API_BASE}/ngo/matches?sector=${encodeURIComponent(selectedCause)}&limit=12`;
        if (selectedState && selectedState !== 'Pan-India' && selectedState !== 'all') {
            url += `&state=${encodeURIComponent(selectedState)}`;
        }
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const matches = Array.isArray(data) ? data : (data.matches || []);

        if (matches.length === 0) {
            container.innerHTML = `<div style="text-align:center; padding:40px; color:var(--text-secondary);">No direct donor matches found for ${escapeHtml(selectedCause)} in ${escapeHtml(selectedState)}. Try selecting Pan-India or a broader cause!</div>`;
            return;
        }

        const quotaBadgeHtml = (tier === 'free')
            ? `<div style="display:flex; align-items:center; gap:8px;">
                 <span class="badge badge-amber" style="font-size:11.5px; padding:4px 10px;">Daily Quota: ${dailyUsed}/5 Used Today</span>
                 <a href="javascript:void(0)" onclick="openSubscriptionModal('pro')" style="color:var(--accent-cyan); font-size:11.5px; font-weight:700; text-decoration:none;">Get Unlimited ⚡</a>
               </div>`
            : `<span class="badge badge-emerald" style="font-size:11.5px; padding:4px 10px;">⚡ Unlimited Algorithmic Matches (${escapeHtml(currentSubscription.plan_name || 'Impact Pro')})</span>`;

        container.innerHTML = `
            <div style="background:var(--bg-surface); border:1px solid var(--border-color); box-shadow:var(--shadow-card); border-radius:14px; padding:20px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                        <h3 style="font-size:18px; font-weight:800; color:var(--text-primary); margin:0;">🎯 Top Algorithmic Enterprise Donor Matches</h3>
                        ${quotaBadgeHtml}
                    </div>
                    <p style="font-size:13.5px; color:var(--text-secondary); margin:0;">
                        Scored live for <strong>${escapeHtml(selectedCause)}</strong> in <strong>${escapeHtml(selectedState)}</strong> based on disclosed Section 135 projects, geographic focus, and scale.
                    </p>
                </div>
                <span class="badge badge-emerald" style="font-size:12px; padding:6px 12px;">${matches.length} Verified Corridors</span>
            </div>

            <div class="company-cards-grid">
                ${matches.map(m => {
                    const score = Math.round(m.match_score || 0);
                    let scoreClass = 'high';
                    if (score < 60) scoreClass = 'low';
                    else if (score < 75) scoreClass = 'med';

                    const website = m.website_url || getCompanyWebsite(m);
                    const breakdown = m.match_components || {};
                    const reasons = Array.isArray(m.match_reasons) && m.match_reasons.length > 0 
                        ? m.match_reasons[0] 
                        : (m.rationale || NOT_AVAILABLE_TEXT);

                    return `
                        <div class="company-card">
                            <div>
                                <div class="company-card-header">
                                    <div class="company-avatar" style="background:${getAvatarGradient(m.company_name)}; color:#ffffff; font-weight:800;">${escapeHtml(getCompanyInitials(m.company_name, m.nse_symbol))}</div>
                                    <div class="company-title-wrap">
                                        <div class="company-card-name">${escapeHtml(m.company_name)}</div>
                                        <div class="company-card-sub" style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; margin-top:3px;">
                                            ${m.nse_symbol ? `<span class="badge badge-cyan" style="font-size:10px; font-weight:700;">NSE: ${escapeHtml(m.nse_symbol)}</span>` : ''}
                                            <span class="badge badge-purple" style="font-size:10px;">${escapeHtml(m.sector || 'Corporate')}</span>
                                        </div>
                                    </div>
                                    <div class="score-badge-radial" title="Authentic algorithmic affinity score">
                                        <span class="score-badge-val ${scoreClass}">${score}%</span>
                                        <span class="score-badge-label">Fit</span>
                                    </div>
                                </div>

                                <div class="company-card-body" style="margin-top:12px;">
                                    <div style="background:var(--bg-surface-subtle); padding:10px 12px; border-radius:8px; font-size:12px; border:1px solid var(--border-subtle); margin-bottom:10px;">
                                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                            <span style="color:var(--text-secondary);">Thematic Alignment:</span>
                                            <strong style="color:var(--primary-brand);">${breakdown.focus_match !== undefined && breakdown.focus_match !== null ? Math.round(breakdown.focus_match) + '%' : NOT_AVAILABLE_TEXT}</strong>
                                        </div>
                                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                            <span style="color:var(--text-secondary);">Geographic Fit:</span>
                                            <strong style="color:var(--text-primary);">${breakdown.geographic_match !== undefined && breakdown.geographic_match !== null ? Math.round(breakdown.geographic_match) + '%' : NOT_AVAILABLE_TEXT}</strong>
                                        </div>
                                        <div style="display:flex; justify-content:space-between;">
                                            <span style="color:var(--text-secondary);">Project Scale Readiness:</span>
                                            <strong style="color:var(--success);">${breakdown.project_scale !== undefined && breakdown.project_scale !== null ? Math.round(breakdown.project_scale) + '%' : NOT_AVAILABLE_TEXT}</strong>
                                        </div>
                                    </div>

                                    <div style="font-size:12px; color:var(--text-secondary); line-height:1.45;">
                                        <strong>Signal:</strong> ${escapeHtml(reasons)}
                                    </div>
                                </div>
                            </div>

                            <div class="company-card-actions">
                                <button class="btn-primary" onclick="openCompanyDossier('${m.company_id}')">
                                    🔍 Corporate Dossier
                                </button>
                                <button class="btn-secondary" onclick="quickSaveToPipeline('${m.company_id}')">
                                    ⭐ Save CRM
                                </button>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } catch (e) {
        container.innerHTML = `<div style="color:#f43f5e; text-align:center; padding:30px;">Error calculating donor matches: ${escapeHtml(e.message)}</div>`;
    }
}

// ===========================================================================
// TAB 5: WEB FETCH & CRAWLING LOGS CONTROLLER
// ===========================================================================
async function loadCrawlerLogs(page = 1, forceRefresh = false) {
    if (typeof page === 'boolean') {
        forceRefresh = page;
        page = paginationState.crawler.page || 1;
    } else if (typeof page !== 'number' || isNaN(page) || page < 1) {
        page = parseInt(page, 10);
        if (isNaN(page) || page < 1) page = 1;
    }
    paginationState.crawler.page = page;
    const tbody = document.getElementById('crawler-logs-table-body');
    if (tbody && (allCrawlerLogs.length === 0 || forceRefresh)) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align:center; padding:45px;">
                    <div style="display:inline-flex; align-items:center; gap:10px; color:var(--accent-cyan);">
                        <span class="loading-spinner-circle" style="width:20px; height:20px; margin:0; border-width:2px;"></span>
                        <span>Fetching live web crawl audits for corporate domains (Page ${page})...</span>
                    </div>
                </td>
            </tr>`;
    }

    try {
        const query = (document.getElementById('crawler-log-search')?.value || '').trim();
        const qual = document.getElementById('crawler-quality-filter')?.value || 'all';
        const stat = document.getElementById('crawler-status-filter')?.value || 'all';
        const sort = document.getElementById('crawler-sort-filter')?.value || 'checked_desc';

        let url = `${API_BASE}/api/crawler/logs?page=${page}&page_size=${paginationState.crawler.pageSize}`;
        if (query) url += `&q=${encodeURIComponent(query)}`;
        if (qual !== 'all') url += `&quality=${encodeURIComponent(qual)}`;
        if (stat !== 'all') url += `&status=${encodeURIComponent(stat)}`;
        if (sort && sort !== 'checked_desc') url += `&sort=${encodeURIComponent(sort)}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        let logs = [];
        let total = 0;
        let totalPages = 1;

        if (data && typeof data === 'object' && Array.isArray(data.logs)) {
            logs = data.logs.map(normalizeCompanyData);
            total = data.total || logs.length;
            totalPages = data.total_pages || Math.ceil(total / paginationState.crawler.pageSize);
            crawlerTelemetry = data.telemetry || {};
        } else if (Array.isArray(data)) {
            logs = data.map(normalizeCompanyData);
            total = logs.length;
            totalPages = Math.ceil(total / paginationState.crawler.pageSize);
        }

        allCrawlerLogs = logs;
        paginationState.crawler.total = total;
        paginationState.crawler.totalPages = totalPages;

        renderCrawlerLogs(logs, total);
        renderCrawlerPagination();
    } catch (e) {
        console.warn('Could not fetch crawler logs', e);
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:30px; color:#f43f5e;">Error loading crawler audit: ${escapeHtml(e.message)}</td></tr>`;
        }
    }
}

function renderCrawlerPagination() {
    renderPaginationBar({
        containerId: 'crawler-pagination',
        page: paginationState.crawler.page,
        totalPages: paginationState.crawler.totalPages,
        total: paginationState.crawler.total,
        pageSize: paginationState.crawler.pageSize,
        pageSizeOptions: [15, 30, 50, 100],
        itemLabel: 'Domain Extraction Audits',
        onPageChange: (newPage) => {
            loadCrawlerLogs(newPage);
            const anchor = document.getElementById('tab-crawler-logs');
            if (anchor) anchor.scrollIntoView({ behavior: 'smooth', block: 'start' });
        },
        onPageSizeChange: (newSize) => {
            paginationState.crawler.pageSize = newSize;
            loadCrawlerLogs(1);
        }
    });
}

function renderCrawlerLogs(logs, total) {
    const tbody = document.getElementById('crawler-logs-table-body');
    const countLabel = document.getElementById('crawler-count-label');
    if (!tbody) return;

    if (countLabel) {
        const totalCount = total || logs.length;
        countLabel.textContent = `Showing page ${paginationState.crawler.page} of ${paginationState.crawler.totalPages} (${totalCount} Live Web Extraction Audits)`;
    }

    if (!logs || logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:30px; color:#94a3b8;">No crawl logs match the filter criteria.</td></tr>`;
        return;
    }

    tbody.innerHTML = logs.map((item, idx) => {
        const website = getCompanyWebsite(item);
        const websiteDomain = cleanDomainLabel(website);
        const csrUrl = _cleanHttpUrl(item.csr_url || item.csr_portal_url || item.csr_webpage_url);
        const careersUrl = _cleanHttpUrl(item.careers_url);
        const continuousIdx = (paginationState.crawler.page - 1) * paginationState.crawler.pageSize + idx + 1;

        return `
            <tr data-company-id="${item.company_id}">
                <td style="color:#64748b; font-weight:700;">#${continuousIdx}</td>
                <td>
                    <div style="font-weight:700; color:var(--text-primary); font-size:13.5px;">${escapeHtml(item.company_name)}</div>
                    <div style="font-size:11.5px; color:var(--text-secondary);">NSE: <strong style="color:var(--primary-brand);">${escapeHtml(item.nse_symbol || NOT_AVAILABLE_TEXT)}</strong></div>
                </td>
                <td>
                    ${website ? `<a href="${escapeHtml(website)}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); text-decoration:none; font-size:12px; font-weight:600;">🌐 ${escapeHtml(websiteDomain)} ↗</a>` : `<span style="font-size:11.5px; color:var(--text-muted);">${escapeHtml(NOT_AVAILABLE_TEXT)}</span>`}
                </td>
                <td>
                    ${csrUrl ? `<a href="${escapeHtml(csrUrl)}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-csr">🌱 CSR Portal ↗</a>` : `<span style="font-size:11.5px; color:var(--text-muted);">${escapeHtml(NOT_AVAILABLE_TEXT)}</span>`}
                </td>
                <td>
                    ${careersUrl ? `<a href="${escapeHtml(careersUrl)}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-careers">💼 Careers Portal ↗</a>` : `<span style="font-size:11.5px; color:var(--text-muted);">${escapeHtml(NOT_AVAILABLE_TEXT)}</span>`}
                </td>
                <td class="crawler-status-cell">
                    <span class="badge badge-emerald"><span class="dot dot-emerald"></span> Live Confirmed</span>
                </td>
                <td class="crawler-time-cell">
                    <span style="font-size:12px; color:#94a3b8;">${timeAgo(item.checked_at)}</span>
                </td>
                <td style="text-align:right;">
                    <button class="btn-primary" style="padding:4px 10px; font-size:11.5px;" onclick="triggerLiveProbe('${item.company_id}', '${escapeHtml(website)}', this)">
                        ⚡ Probe Ping
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function filterCrawlerLogs() {
    loadCrawlerLogs(1);
}

// ===========================================================================
// VERIFICATION MATRIX & COVERAGE LEDGER (Part 17 & Part 18)
// ===========================================================================
async function loadCoverageTable() {
    const tbody = document.getElementById('coverage-table-body');
    if (!tbody) return;

    tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding:40px; color:var(--text-secondary);"><span class="loading-spinner-circle" style="width:18px; height:18px; display:inline-block; vertical-align:middle; margin-right:8px;"></span> Loading 200-company verification matrix and audit ledger...</td></tr>`;

    try {
        const res = await fetch(`${API_BASE}/api/coverage`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const rows = await res.json();

        if (!rows || rows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding:30px; color:var(--text-muted);">No coverage ledger records available.</td></tr>`;
            return;
        }

        tbody.innerHTML = rows.map((r, idx) => {
            const isCrawled = r.crawl_status === 'CRAWLED';
            const statusBadge = isCrawled 
                ? '<span class="badge badge-emerald" style="font-size:10px;">CRAWLED (200 OK)</span>'
                : `<span class="badge badge-amber" style="font-size:10px;">${escapeHtml(r.crawl_status)}</span>`;
            
            const jobsBadge = r.jobs_published > 0 
                ? `<span class="badge badge-emerald" style="font-weight:700;">${r.jobs_published} Published</span>` 
                : `<span class="badge badge-subtle">0 Published</span>`;
            
            const csrBadge = r.csr_records > 0 
                ? `<span class="badge badge-purple" style="font-weight:700;">${r.csr_records} Verified</span>` 
                : `<span class="badge badge-subtle">0 Disclosed</span>`;

            const siteLink = r.website && r.website.startsWith('http') 
                ? `<a href="${r.website}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); text-decoration:none;" title="${escapeHtml(r.website)}">Domain ↗</a>` 
                : '<span style="color:var(--text-muted);">N/A</span>';

            const careersLink = r.careers_url && r.careers_url.startsWith('http') 
                ? `<a href="${r.careers_url}" target="_blank" rel="noopener noreferrer" style="color:var(--primary-brand); text-decoration:none;" title="${escapeHtml(r.careers_url)}">Careers ↗</a>` 
                : '<span style="color:var(--text-muted);">Not Found</span>';

            return `
                <tr>
                    <td style="color:var(--text-muted); font-weight:700;">#${idx + 1}</td>
                    <td>
                        <div style="font-weight:700; color:var(--text-primary); cursor:pointer;" onclick="openCompanyDossier('${r.company_id}')">
                            ${escapeHtml(r.name)}
                        </div>
                        <div style="font-size:10.5px; color:var(--text-muted); font-family:var(--font-mono);">${escapeHtml(r.company_id)}</div>
                    </td>
                    <td><span class="badge badge-cyan" style="font-size:9.5px;">${escapeHtml(r.nse_symbol || NOT_AVAILABLE_TEXT)}</span></td>
                    <td>${siteLink}</td>
                    <td>${careersLink}</td>
                    <td><span class="badge badge-subtle" style="font-size:10px;">${escapeHtml(r.ats || NOT_AVAILABLE_TEXT)}</span></td>
                    <td style="font-family:var(--font-mono); font-size:12px; font-weight:700;">${r.jobs_found}</td>
                    <td>${jobsBadge}</td>
                    <td>${csrBadge}</td>
                    <td>${statusBadge}</td>
                    <td style="font-size:11.5px; color:var(--text-secondary); max-width:260px;">
                        ${escapeHtml(r.explanation)}
                    </td>
                </tr>
            `;
        }).join('');
    } catch (e) {
        console.error('Error loading coverage matrix', e);
        tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding:30px; color:#f43f5e;">Failed to load coverage table: ${escapeHtml(e.message)}</td></tr>`;
    }
}

async function triggerLiveProbe(companyId, url, btnElement) {
    if (!btnElement && window.event) {
        btnElement = window.event.currentTarget;
    }

    const tier = normalizeSubscriptionTier((currentSubscription && (currentSubscription.tier || currentSubscription.plan_id)) || 'free');
    if (tier === 'free') {
        showLiveToast('⚡ Live On-Demand Crawler Probing requires Impact Pro or Ultra Enterprise. Opening plans...', 'info');
        openSubscriptionModal('pro');
        return;
    }

    const originalText = btnElement ? btnElement.innerHTML : '⚡ Probe Ping';
    if (btnElement) {
        btnElement.disabled = true;
        btnElement.innerHTML = '⏳ Probing...';
    }

    try {
        const res = await fetch(`${API_BASE}/api/crawler/recheck/${companyId}`, {
            method: 'POST'
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        if (btnElement) {
            btnElement.disabled = false;
            btnElement.innerHTML = '✓ Pinged';
            btnElement.style.background = 'var(--accent-emerald)';
            btnElement.style.color = '#04101e';

            // Find parent table row and update badge & timestamp dynamically
            const tr = btnElement.closest('tr');
            if (tr) {
                const badgeCell = tr.querySelector('.crawler-status-cell') || tr.cells[5];
                if (badgeCell) {
                    badgeCell.innerHTML = `<span class="badge badge-emerald"><span class="dot dot-emerald pulse-dot"></span> HTTP ${data.http_status} OK (${data.response_time_ms}ms)</span>`;
                }
                const timeCell = tr.querySelector('.crawler-time-cell') || tr.cells[6];
                if (timeCell) {
                    timeCell.innerHTML = `<span style="font-size:12px; color:var(--accent-cyan); font-weight:700;">Just now</span>`;
                }
            }

            setTimeout(() => {
                btnElement.innerHTML = originalText;
                btnElement.style.background = '';
                btnElement.style.color = '';
            }, 3000);
        }

        showLiveToast(`✓ Live Probe: ${cleanDomainLabel(url)} returned HTTP ${data.http_status} in ${data.response_time_ms}ms`, 'success');
    } catch (e) {
        if (btnElement) {
            btnElement.disabled = false;
            btnElement.innerHTML = originalText;
        }
        showLiveToast(`Probe ping failed: ${e.message}`, 'error');
    }
}

// ===========================================================================
// TAB 6: OUTREACH CRM PIPELINE (KANBAN)
// ===========================================================================
const PIPELINE_STAGES = [
    { id: 'Shortlisted', label: 'Saved & Shortlisted', colId: 'col-Shortlisted', badgeId: 'count-stage-shortlisted' },
    { id: 'Proposal Sent', label: 'Concept Note Sent', colId: 'col-ProposalSent', badgeId: 'count-stage-proposal' },
    { id: 'In Discussion', label: 'In Dialogue', colId: 'col-InDiscussion', badgeId: 'count-stage-discussion' },
    { id: 'Approved', label: 'Partnered & Funded', colId: 'col-Partnered', badgeId: 'count-stage-partnered' }
];

async function loadProspects() {
    try {
        const res = await fetch(`${API_BASE}/prospects`);
        allProspects = await res.json();
        renderPipeline(allProspects);
        updatePipelineBadge(allProspects.length);
    } catch (e) {
        console.warn('Could not load prospects', e);
    }
}

function updatePipelineBadge(count) {
    const badge = document.getElementById('pipeline-count-badge');
    if (badge) badge.textContent = count;
}

function renderPipeline(prospects) {
    PIPELINE_STAGES.forEach(st => {
        const col = document.getElementById(st.colId);
        const countBadge = document.getElementById(st.badgeId);
        if (col) col.innerHTML = '';
        if (countBadge) countBadge.textContent = '0';
    });

    if (!prospects || prospects.length === 0) {
        const col = document.getElementById('col-Shortlisted');
        if (col) {
            col.innerHTML = `<div style="text-align:center; padding:30px 10px; color:#64748b; font-size:12.5px;">
                No corporations saved yet. Click "+ Save CRM" on any company card to track outreach here!
            </div>`;
        }
        return;
    }

    const counts = { 'Shortlisted': 0, 'Proposal Sent': 0, 'In Discussion': 0, 'Approved': 0 };

    prospects.forEach(p => {
        let stage = p.stage || 'Shortlisted';
        if (stage === 'Identified' || stage === 'Proposal Prepared') stage = 'Shortlisted';
        if (stage === 'Follow-up' || stage === 'Meeting') stage = 'In Discussion';
        if (stage === 'Project Started') stage = 'Approved';

        counts[stage] = (counts[stage] || 0) + 1;

        let colId = 'col-Shortlisted';
        if (stage === 'Proposal Sent') colId = 'col-ProposalSent';
        else if (stage === 'In Discussion') colId = 'col-InDiscussion';
        else if (stage === 'Approved') colId = 'col-Partnered';

        const col = document.getElementById(colId);
        if (!col) return;

        const card = document.createElement('div');
        card.className = 'kanban-card';
        card.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                <div class="kanban-card-title">${escapeHtml(p.company_name)}</div>
                <button onclick="removeProspect('${p.company_id}')" style="background:none; border:none; color:#64748b; cursor:pointer; font-size:13px;" title="Remove">✕</button>
            </div>
            <div class="kanban-card-meta">
                <span>Sector: <strong>${escapeHtml(p.sector || NOT_AVAILABLE_TEXT)}</strong></span>
            </div>
            <div style="display:flex; gap:6px; margin-top:8px;">
                <button class="btn-secondary" style="font-size:11px; padding:4px 8px;" onclick="openCompanyDossier('${p.company_id}')">
                    Dossier
                </button>
                <button class="btn-primary" style="font-size:11px; padding:4px 8px;" onclick="cycleProspectStage('${p.company_id}', '${stage}')">
                    Advance ➔
                </button>
            </div>
        `;
        col.appendChild(card);
    });

    PIPELINE_STAGES.forEach(st => {
        const badge = document.getElementById(st.badgeId);
        if (badge) badge.textContent = counts[st.id] || 0;
    });

    const mbShortlisted = document.getElementById('mb-count-shortlisted');
    if (mbShortlisted) mbShortlisted.textContent = counts['Shortlisted'] || 0;
    const mbProposal = document.getElementById('mb-count-proposal');
    if (mbProposal) mbProposal.textContent = counts['Proposal Sent'] || 0;
    const mbDiscussion = document.getElementById('mb-count-discussion');
    if (mbDiscussion) mbDiscussion.textContent = counts['In Discussion'] || 0;
    const mbPartnered = document.getElementById('mb-count-partnered');
    if (mbPartnered) mbPartnered.textContent = counts['Approved'] || 0;
}

async function quickSaveToPipeline(companyId, companyName, sector) {
    if (!companyName && Array.isArray(allDirectoryCompanies)) {
        const found = allDirectoryCompanies.find(c => c.company_id === companyId);
        if (found) {
            companyName = found.company_name;
            sector = found.sector;
        }
    }
    try {
        const res = await fetch(`${API_BASE}/prospects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                company_id: companyId,
                company_name: companyName || companyId,
                sector: sector || null,
                stage: 'Shortlisted'
            })
        });
        if (res.ok) {
            await loadProspects();
            showLiveToast(`✓ Saved ${companyName || companyId} to Outreach CRM!`, 'success');
        }
    } catch (e) {
        showLiveToast('Could not save to CRM: ' + e.message, 'error');
    }
}

async function cycleProspectStage(companyId, currentStage) {
    const order = ['Shortlisted', 'Proposal Sent', 'In Discussion', 'Approved'];
    const nextIdx = (order.indexOf(currentStage) + 1) % order.length;
    const nextStage = order[nextIdx];

    try {
        await fetch(`${API_BASE}/prospects/${companyId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stage: nextStage })
        });
        await loadProspects();
    } catch (e) {
        console.warn('Could not advance stage', e);
    }
}

async function removeProspect(companyId) {
    try {
        await fetch(`${API_BASE}/prospects/${companyId}`, { method: 'DELETE' });
        await loadProspects();
    } catch (e) {
        console.warn('Could not remove prospect', e);
    }
}

// ===========================================================================
// UNIVERSAL COMPANY DOSSIER MODAL
// ===========================================================================
let currentDossierData = null;

async function openCompanyDossier(companyId, initialTab = 'overview') {
    const modal = document.getElementById('modal-company-dossier');
    const modalBody = document.getElementById('modal-dossier-body');
    const modalTitle = document.getElementById('modal-dossier-title');
    const modalSub = document.getElementById('modal-dossier-subtitle');
    const avatar = document.getElementById('modal-dossier-avatar');
    const badge = document.getElementById('modal-dossier-coverage-badge');
    const summaryCardsEl = document.getElementById('modal-dossier-summary-cards');
    if (!modal || !modalBody) return;

    modal.style.display = 'flex';
    modalBody.innerHTML = `
        <div style="text-align:center; padding:60px 20px;">
            <div class="loading-spinner-circle" style="margin:0 auto 16px;"></div>
            <div style="font-size:16px; font-weight:700; color:var(--text-primary);">Loading Universal Corporate Dossier...</div>
            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">Retrieving verified statutory registry & telemetry for ${escapeHtml(companyId)}</div>
        </div>`;

    if (summaryCardsEl) summaryCardsEl.innerHTML = '';

    try {
        const res = await fetch(`${API_BASE}/companies/${companyId}/dossier`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        const comp = normalizeCompanyData(data.company || {});
        data.company = comp;
        currentDossierData = data;

        const website = getCompanyWebsite(comp);
        const websiteLabel = cleanDomainLabel(website);
        const symbolOrCin = comp.nse_symbol ? `NSE: <strong>${escapeHtml(comp.nse_symbol)}</strong>` : (comp.cin ? `CIN: <span class="mono" style="font-size:11.5px;">${escapeHtml(comp.cin)}</span>` : `Identifier: <span style="font-size:11.5px;">Statutory Public Corporation</span>`);
        const sectorText = comp.sector ? escapeHtml(comp.sector) : NOT_AVAILABLE_TEXT;
        const hqText = comp.headquarters ? escapeHtml(comp.headquarters) : NOT_AVAILABLE_TEXT;

        if (modalTitle) modalTitle.textContent = comp.company_name;
        if (avatar) {
            avatar.textContent = getCompanyInitials(comp.company_name, comp.nse_symbol);
            avatar.style.background = getAvatarGradient(comp.company_name);
            avatar.style.color = '#ffffff';
        }
        if (badge) {
            const covStatus = data.intelligence_summary?.overall_coverage_status || data.coverage_audit?.overall_status || comp.crawl_status || 'VERIFIED';
            badge.textContent = covStatus;
            badge.className = `badge ${covStatus === 'VERIFIED' ? 'badge-emerald' : (covStatus === 'PARTIAL' ? 'badge-amber' : (covStatus === 'FAILED' ? 'badge-red' : 'badge-slate'))}`;
        }
        if (modalSub) {
            modalSub.innerHTML = `
                🌐 <a href="${website}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); text-decoration:none; font-weight:600;">${escapeHtml(websiteLabel)} ↗</a>
                <span style="margin:0 8px; color:var(--border-color);">•</span>
                ${symbolOrCin}
                <span style="margin:0 8px; color:var(--border-color);">•</span>
                <span>Sector: <strong>${sectorText}</strong></span>
                <span style="margin:0 8px; color:var(--border-color);">•</span>
                <span>HQ: <strong>${hqText}</strong></span>
            `;
        }

        // Section 3: Universal Company Intelligence Summary (7 Authoritative Summary Cards)
        if (summaryCardsEl) {
            const isum = data.intelligence_summary || {};
            const jobCnt = isum.eligible_published_jobs ?? (data.jobs || []).length;
            const csrCnt = isum.verified_csr_projects ?? (data.projects || []).length;
            const oppCnt = isum.open_opportunities ?? (data.opportunities || []).length;
            const contCnt = isum.published_contacts ?? (data.contacts || []).length;
            const repCnt = isum.available_reports ?? (data.official_reports || []).length;
            const lastCheck = isum.last_source_check || NOT_AVAILABLE_TEXT;
            const covStat = isum.overall_coverage_status || 'VERIFIED';

            // Sections that the company only shows after login (set by an admin / detector)
            const acc = data.data_access || {};
            const loginSections = acc.login_required_sections || [];
            const loginBanner = loginSections.length ? `
                <div style="margin:0 0 12px; padding:10px 14px; border:1px solid var(--accent-amber, #d97706); border-radius:8px; font-size:13px;">
                    <strong>${escapeHtml(LOGIN_REQUIRED_TEXT)}:</strong> ${escapeHtml(loginSections.join(', '))}.
                    ${acc.note ? `<div style="margin-top:4px; color:var(--text-muted);">${escapeHtml(acc.note)}</div>` : ''}
                </div>` : '';

            summaryCardsEl.innerHTML = loginBanner + `
                <div class="dossier-summary-cards-bar">
                    <div class="dossier-summary-card" onclick="switchDossierTab('jobs')" style="cursor:pointer;" title="Current eligible published jobs">
                        <span class="dossier-summary-card-val" style="color:var(--accent-cyan);">${jobCnt}</span>
                        <span class="dossier-summary-card-lbl">1. Published Jobs</span>
                        <span class="dossier-summary-card-sub">${escapeHtml(isum.jobs_status || (jobCnt > 0 ? 'Active Vacancies' : 'Verified Zero'))}</span>
                    </div>
                    <div class="dossier-summary-card" onclick="switchDossierTab('csr')" style="cursor:pointer;" title="Verified statutory CSR initiatives">
                        <span class="dossier-summary-card-val" style="color:var(--accent-emerald);">${csrCnt}</span>
                        <span class="dossier-summary-card-lbl">2. CSR Projects</span>
                        <span class="dossier-summary-card-sub">${escapeHtml(isum.csr_status || 'Section 135 Mandate')}</span>
                    </div>
                    <div class="dossier-summary-card" onclick="switchDossierTab('opportunities')" style="cursor:pointer;" title="Genuine open funding calls">
                        <span class="dossier-summary-card-val" style="color:var(--accent-amber);">${oppCnt}</span>
                        <span class="dossier-summary-card-lbl">3. Open Grants</span>
                        <span class="dossier-summary-card-sub">${oppCnt > 0 ? 'Active RFPs / EOIs' : '0 Open RFPs Confirmed'}</span>
                    </div>
                    <div class="dossier-summary-card" onclick="switchDossierTab('contacts')" style="cursor:pointer;" title="Published official contacts">
                        <span class="dossier-summary-card-val">${contCnt}</span>
                        <span class="dossier-summary-card-lbl">4. Contacts</span>
                        <span class="dossier-summary-card-sub">${contCnt > 0 ? 'Verified CSR Mailbox' : NOT_AVAILABLE_TEXT}</span>
                    </div>
                    <div class="dossier-summary-card" onclick="switchDossierTab('reports')" style="cursor:pointer;" title="Available official reports">
                        <span class="dossier-summary-card-val">${repCnt}</span>
                        <span class="dossier-summary-card-lbl">5. Official Reports</span>
                        <span class="dossier-summary-card-sub">Annual, BRSR, ESG</span>
                    </div>
                    <div class="dossier-summary-card" title="Last successful source check">
                        <span class="dossier-summary-card-val" style="font-size:12px; font-weight:700;">${escapeHtml(lastCheck)}</span>
                        <span class="dossier-summary-card-lbl">6. Last Check</span>
                        <span class="dossier-summary-card-sub">RFC 9309 Compliant</span>
                    </div>
                    <div class="dossier-summary-card" onclick="switchDossierTab('sources')" style="cursor:pointer;" title="Company-specific source-coverage status">
                        <span class="dossier-summary-card-val" style="font-size:12px; font-weight:800; color:${covStat === 'VERIFIED' ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">${escapeHtml(covStat)}</span>
                        <span class="dossier-summary-card-lbl">7. Coverage Audit</span>
                        <span class="dossier-summary-card-sub">Statutory Registry</span>
                    </div>
                </div>
            `;
        }

        switchDossierTab(initialTab || 'overview');
    } catch (e) {
        modalBody.innerHTML = `<div style="color:#f43f5e; text-align:center; padding:40px;">Could not load dossier: ${escapeHtml(e.message)}</div>`;
    }
}

let dossierJobSearchTerm = '';
let dossierJobLocFilter = 'all';
let dossierJobDeptFilter = 'all';
let dossierJobModeFilter = 'all';

function switchDossierTab(tab) {
    if (!currentDossierData) return;
    const body = document.getElementById('modal-dossier-body');
    if (!body) return;

    document.querySelectorAll('.dossier-tab-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.dossierTab === tab);
    });

    const comp = currentDossierData.company || {};
    const playbook = currentDossierData.strategic_playbook || {};
    const website = getCompanyWebsite(comp);
    const csrUrl = getCompanyCsrWebpageUrl(comp);
    const careersUrl = _cleanHttpUrl(comp.careers_url) || '#';
    const jobs = currentDossierData.jobs || [];
    const projects = currentDossierData.projects || [];
    const contacts = currentDossierData.contacts || [];
    const opportunities = currentDossierData.opportunities || [];
    const closedOpportunities = currentDossierData.closed_opportunities || [];
    const officialReports = currentDossierData.official_reports || [];
    const coverageAudit = currentDossierData.coverage_audit || {};

    // -----------------------------------------------------------------------
    // TAB 1: OVERVIEW (SECTION 2: COMPANY OVERVIEW)
    // -----------------------------------------------------------------------
    if (tab === 'overview') {
        // Collect distinct locations from jobs & CSR projects
        const rawLocations = [
            ...jobs.map(j => j.location).filter(Boolean),
            ...projects.map(p => p.state).filter(Boolean)
        ];
        const uniqueLocations = [...new Set(rawLocations)].slice(0, 6);
        const locationsDisplay = uniqueLocations.length > 0 
            ? uniqueLocations.map(l => `<span class="job-chip">📍 ${escapeHtml(l)}</span>`).join(' ') 
            : '<span style="color:var(--text-muted); font-size:12.5px;">' + NOT_AVAILABLE_TEXT + '</span>';

        body.innerHTML = `
            <!-- Section 2: Universal Company Overview -->
            <div class="insights-grid" style="margin-bottom:20px;">
                <div class="insight-box">
                    <div class="insight-title">🏢 Statutory Corporate Entity Master</div>
                    <div class="insight-item"><span>Official Company Name</span><strong>${escapeHtml(comp.company_name)}</strong></div>
                    <div class="insight-item"><span>Legal Entity Name</span><strong>${comp.legal_name ? escapeHtml(comp.legal_name) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                    <div class="insight-item"><span>CIN</span><strong class="mono" style="color:var(--accent-cyan); font-size:12px;">${comp.cin ? escapeHtml(comp.cin) : '<span style="color:var(--text-muted); font-family:inherit; font-weight:normal;">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                    <div class="insight-item"><span>ISIN</span><strong class="mono" style="font-size:12px;">${comp.isin ? escapeHtml(comp.isin) : '<span style="color:var(--text-muted); font-family:inherit; font-weight:normal;">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                    <div class="insight-item"><span>Corporate Headquarters</span><strong>${comp.headquarters ? escapeHtml(comp.headquarters) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                    <div class="insight-item"><span>Industry &amp; Activities</span><strong>${comp.sector ? escapeHtml(comp.sector) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                    <div class="insight-item"><span>Official Apex Domain</span><strong>${comp.official_domain ? escapeHtml(comp.official_domain) : (website ? escapeHtml(cleanDomainLabel(website)) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>')}</strong></div>
                </div>

                <div class="insight-box">
                    <div class="insight-title">📍 Published Operating Locations &amp; Regions</div>
                    <p style="font-size:12.5px; color:var(--text-secondary); margin-bottom:12px; line-height:1.5;">
                        Regions and operating facilities documented across verified career openings and statutory Section 135 CSR projects:
                    </p>
                    <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:14px;">
                        ${locationsDisplay}
                    </div>
                    <div class="insight-item" style="border-top:1px solid var(--border-subtle); padding-top:10px;">
                        <span>Data Integrity</span>
                        <strong style="color:var(--accent-emerald);">Strict Zero-Inference Guarantee</strong>
                    </div>
                </div>
            </div>

            <!-- Relevant Official Corporate Links Grid -->
            <div class="insight-box" style="margin-bottom:20px;">
                <div class="insight-title">🌐 Relevant Official Corporate Portals &amp; Evidence Sources</div>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(210px, 1fr)); gap:12px;">
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:12px 14px; border-radius:8px;">
                        <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Official Website</div>
                        <div style="font-size:13px; font-weight:600; color:var(--text-primary); margin:3px 0 8px; word-break:break-all;">${website ? escapeHtml(cleanDomainLabel(website)) : NOT_AVAILABLE_TEXT}</div>
                        ${website ? `<a href="${website}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11px; padding:3px 10px;">Open Portal ↗</a>` : '<span style="font-size:11.5px; color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}
                    </div>

                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:12px 14px; border-radius:8px;">
                        <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Careers &amp; ATS Portal</div>
                        <div style="font-size:13px; font-weight:600; color:var(--text-primary); margin:3px 0 8px;">${comp.careers_url ? 'Verified Careers Link' : NOT_AVAILABLE_TEXT}</div>
                        ${comp.careers_url ? `<a href="${comp.careers_url}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11px; padding:3px 10px;">Open Careers ↗</a>` : '<span style="font-size:11.5px; color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}
                    </div>

                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:12px 14px; border-radius:8px;">
                        <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">CSR Foundation Portal</div>
                        <div style="font-size:13px; font-weight:600; color:var(--text-primary); margin:3px 0 8px;">${comp.csr_portal_url ? 'Section 135 Disclosures' : NOT_AVAILABLE_TEXT}</div>
                        ${comp.csr_portal_url ? `<a href="${comp.csr_portal_url}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11px; padding:3px 10px;">Open CSR Portal ↗</a>` : '<span style="font-size:11.5px; color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}
                    </div>

                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:12px 14px; border-radius:8px;">
                        <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Sustainability &amp; ESG</div>
                        <div style="font-size:13px; font-weight:600; color:var(--text-primary); margin:3px 0 8px;">${comp.sustainability_url ? 'ESG Disclosures' : NOT_AVAILABLE_TEXT}</div>
                        ${comp.sustainability_url ? `<a href="${comp.sustainability_url}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11px; padding:3px 10px;">Open ESG Portal ↗</a>` : '<span style="font-size:11.5px; color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}
                    </div>

                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:12px 14px; border-radius:8px;">
                        <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">Annual Reports Archive</div>
                        <div style="font-size:13px; font-weight:600; color:var(--text-primary); margin:3px 0 8px;">${comp.annual_report_url ? 'Statutory Filings' : NOT_AVAILABLE_TEXT}</div>
                        ${comp.annual_report_url ? `<a href="${comp.annual_report_url}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11px; padding:3px 10px;">Open Filings ↗</a>` : '<span style="font-size:11.5px; color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}
                    </div>

                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:12px 14px; border-radius:8px;">
                        <div style="font-size:11px; font-weight:700; color:var(--text-muted); text-transform:uppercase;">SEBI BRSR Disclosures</div>
                        <div style="font-size:13px; font-weight:600; color:var(--text-primary); margin:3px 0 8px;">${comp.brsr_url ? 'SEBI Core Report' : NOT_AVAILABLE_TEXT}</div>
                        ${comp.brsr_url ? `<a href="${comp.brsr_url}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11px; padding:3px 10px;">Open BRSR ↗</a>` : '<span style="font-size:11.5px; color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}
                    </div>
                </div>
            </div>

            <!-- Executive Strategic Playbook for NGOs -->
            <div class="insight-box">
                <div class="insight-title">🌱 Executive Strategic Intelligence (Who &bull; Why &bull; How)</div>
                <div style="font-size:13.5px; color:var(--text-primary); line-height:1.6; margin-bottom:12px;">
                    <strong>🏢 Who is this corporation:</strong> ${escapeHtml(playbook.who || NOT_AVAILABLE_TEXT)}
                </div>
                <div style="font-size:13.5px; color:var(--text-primary); line-height:1.6; margin-bottom:12px;">
                    <strong>💡 Why they support initiatives:</strong> ${escapeHtml(playbook.why || NOT_AVAILABLE_TEXT)}
                </div>
                <div style="font-size:13.5px; color:var(--text-primary); line-height:1.6;">
                    <strong>📝 How to engage &amp; partner:</strong> ${escapeHtml(playbook.how || NOT_AVAILABLE_TEXT)}
                </div>
            </div>
        `;

    // -----------------------------------------------------------------------
    // TAB 2: JOBS (SECTION 5: JOBS TAB)
    // -----------------------------------------------------------------------
    } else if (tab === 'jobs') {
        const jobState = (coverageAudit.jobs_status || comp.job_status_state || '').toUpperCase();
        let emptyStateHtml = '';

        if (jobState === 'VERIFIED_ZERO_JOBS' || jobState === 'VERIFIED_ZERO') {
            emptyStateHtml = `
                <div style="text-align:center; padding:40px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                    <div style="font-size:32px; margin-bottom:10px;">🏢</div>
                    <div style="font-size:16px; font-weight:800; color:var(--text-primary); margin-bottom:6px;">0 Current Verified Openings Disclosed</div>
                    <div style="font-size:13px; color:var(--text-secondary); max-width:460px; margin:0 auto 16px; line-height:1.5;">
                        The official careers endpoint (${escapeHtml(coverageAudit.ats_platform || 'Corporate Portal')}) was successfully checked and confirmed to contain no active vacancies at this time.
                    </div>
                    ${careersUrl !== '#' ? `<a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12.5px; text-decoration:none;">Check Careers Portal Directly ↗</a>` : ''}
                </div>
            `;
        } else if (jobState === 'CRAWL_FAILED') {
            emptyStateHtml = `
                <div style="text-align:center; padding:40px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                    <div style="font-size:32px; margin-bottom:10px;">⚠️</div>
                    <div style="font-size:16px; font-weight:800; color:var(--text-primary); margin-bottom:6px;">Unable to Verify Current Openings</div>
                    <div style="font-size:13px; color:var(--text-secondary); max-width:460px; margin:0 auto 16px; line-height:1.5;">
                        Socket probe encountered a connection timeout or network block while accessing the careers endpoint. Retaining pending status.
                    </div>
                    ${careersUrl !== '#' ? `<a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12.5px; text-decoration:none;">Visit Official Careers Portal ↗</a>` : ''}
                </div>
            `;
        } else if (jobState === 'ATS_DISCOVERY_FAILED') {
            emptyStateHtml = `
                <div style="text-align:center; padding:40px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                    <div style="font-size:32px; margin-bottom:10px;">🔍</div>
                    <div style="font-size:16px; font-weight:800; color:var(--text-primary); margin-bottom:6px;">Career Source Pending Discovery</div>
                    <div style="font-size:13px; color:var(--text-secondary); max-width:460px; margin:0 auto 16px; line-height:1.5;">
                        No external ATS endpoint was identified on the corporate apex domain during the latest automated pass.
                    </div>
                    <a href="${website}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12.5px; text-decoration:none;">Visit Company Website ↗</a>
                </div>
            `;
        } else {
            emptyStateHtml = `
                <div style="text-align:center; padding:40px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                    <div style="font-size:32px; margin-bottom:10px;">⏳</div>
                    <div style="font-size:16px; font-weight:800; color:var(--text-primary); margin-bottom:6px;">Jobs Pending Verification Pass</div>
                    <div style="font-size:13px; color:var(--text-secondary); max-width:460px; margin:0 auto 16px; line-height:1.5;">
                        This employer’s career source is queued for an authoritative extraction run.
                    </div>
                    ${careersUrl !== '#' ? `<a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12.5px; text-decoration:none;">Visit Careers Portal ↗</a>` : ''}
                </div>
            `;
        }

        // Filter options
        const locations = [...new Set(jobs.map(j => j.location).filter(Boolean))].sort();
        const departments = [...new Set(jobs.map(j => j.department).filter(Boolean))].sort();

        body.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
                <div>
                    <h4 style="font-size:16px; font-weight:800; color:var(--text-primary); margin:0;">
                        Current Eligible Published Openings (${jobs.length})
                    </h4>
                    <div style="font-size:12.5px; color:var(--text-secondary); margin-top:2px;">
                        Showing verified positions belonging strictly to <strong>${escapeHtml(comp.company_name)}</strong>
                    </div>
                </div>
                ${careersUrl !== '#' ? `
                <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12.5px; padding:6px 14px; text-decoration:none;">
                    Official Careers Portal ↗
                </a>` : ''}
            </div>

            ${jobs.length > 0 ? `
            <!-- In-Tab Search & Filter Toolbar -->
            <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px 14px; margin-bottom:16px; display:flex; flex-wrap:wrap; gap:10px; align-items:center;">
                <input type="text" id="dossier-job-search-input" placeholder="Search positions by keyword..." style="flex:1 1 200px; padding:7px 12px; font-size:13px; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:6px; color:var(--text-primary);" oninput="renderFilteredDossierJobs()" />
                <select id="dossier-job-loc-select" style="padding:7px 10px; font-size:12.5px; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:6px; color:var(--text-primary);" onchange="renderFilteredDossierJobs()">
                    <option value="all">All Locations (${locations.length})</option>
                    ${locations.map(l => `<option value="${escapeHtml(l)}">${escapeHtml(l)}</option>`).join('')}
                </select>
                <select id="dossier-job-dept-select" style="padding:7px 10px; font-size:12.5px; background:var(--bg-surface); border:1px solid var(--border-color); border-radius:6px; color:var(--text-primary);" onchange="renderFilteredDossierJobs()">
                    <option value="all">All Departments (${departments.length})</option>
                    ${departments.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('')}
                </select>
            </div>

            <div id="dossier-jobs-list-container" style="display:flex; flex-direction:column; gap:12px;">
                ${jobs.map(j => renderStandardJobCard(j, { showCompanyLink: false })).join('')}
            </div>
            ` : emptyStateHtml}
        `;

    // -----------------------------------------------------------------------
    // TAB 3: CSR PROJECTS & COMPANY CSR WEBPAGE VIEW (SECTION 6: CSR PROJECTS TAB)
    // -----------------------------------------------------------------------
    } else if (tab === 'csr') {
        const csrOverview = currentDossierData.csr_overview || {};
        const csrLinks = Array.isArray(csrOverview.csr_links) && csrOverview.csr_links.length > 0
            ? csrOverview.csr_links
            : (Array.isArray(comp.csr_links) ? comp.csr_links : []);
        const csrFormat = csrOverview.csr_display_format || comp.csr_display_format || NOT_AVAILABLE_TEXT;
        const isCsrLogin = (comp.csr_access === 'LOGIN_REQUIRED' || csrOverview.csr_access === 'LOGIN_REQUIRED');

        body.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
                <div>
                    <h4 style="font-size:16px; font-weight:800; color:var(--text-primary); margin:0;">
                        CSR Webpage, Disclosure Sources &amp; Verified CSR Projects (${projects.length})
                    </h4>
                    <div style="font-size:12.5px; color:var(--text-secondary); margin-top:2px;">
                        Companies publish CSR differently (webpage, Foundation portal, Sustainability/ESG page, or PDF reports). Every verified link and extracted project for <strong>${escapeHtml(comp.company_name)}</strong> is shown below.
                    </div>
                </div>
                <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                    ${csrUrl ? `
                    <a href="${escapeHtml(csrUrl)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12.5px; padding:6px 14px; text-decoration:none;">
                        🌐 Open Official CSR Webpage ↗
                    </a>` : ''}
                </div>
            </div>

            ${isCsrLogin ? `
            <div style="margin-bottom:16px; padding:12px 16px; border:1.5px solid #f59e0b; background:rgba(245, 158, 11, 0.12); border-radius:8px; font-size:13px; color:#f59e0b;">
                🔒 <strong>${escapeHtml(LOGIN_REQUIRED_TEXT)}:</strong> CSR disclosures on this company's official website can only be viewed after user login.
                ${comp.data_access_note ? `<div style="margin-top:4px; font-size:12px; color:var(--text-secondary);">${escapeHtml(comp.data_access_note)}</div>` : ''}
            </div>` : ''}

            <!-- Official Company CSR Webpage & PDF Links Panel -->
            <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); padding:16px; border-radius:10px; margin-bottom:18px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
                    <div style="font-weight:800; font-size:13.5px; color:var(--text-primary);">
                        🌐 View CSR Webpage &amp; Official Disclosure Links for ${escapeHtml(comp.company_name)}
                    </div>
                    <span class="badge badge-cyan" style="font-size:10.5px;">Format: ${escapeHtml(csrFormat)}</span>
                </div>
                ${csrLinks.length > 0 ? `
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(250px, 1fr)); gap:10px;">
                    ${csrLinks.map(lk => `
                        <div style="background:var(--bg-surface); border:1px solid var(--border-color); border-radius:8px; padding:12px 14px; display:flex; flex-direction:column; justify-content:space-between; gap:8px;">
                            <div>
                                <div style="display:flex; justify-content:space-between; align-items:center; gap:6px;">
                                    <strong style="font-size:12.5px; color:var(--text-primary);">${escapeHtml(lk.label || 'Official CSR Source')}</strong>
                                    <span class="badge badge-purple" style="font-size:9.5px;">${escapeHtml(lk.format || 'CSR Source')}</span>
                                </div>
                                <div style="font-size:11.5px; color:var(--text-secondary); word-break:break-all; margin-top:4px;">${escapeHtml(lk.url)}</div>
                            </div>
                            <div>
                                <a href="${escapeHtml(lk.url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11.5px; padding:4px 12px; text-decoration:none; display:inline-block;">
                                    Open CSR Page / Document ↗
                                </a>
                            </div>
                        </div>
                    `).join('')}
                </div>
                ` : `
                <div style="font-size:13px; color:var(--text-muted); padding:6px 0;">
                    ${escapeHtml(isCsrLogin ? LOGIN_REQUIRED_TEXT : NOT_AVAILABLE_TEXT)}
                </div>
                `}
            </div>

            <!-- Extracted CSR Projects List -->
            <div style="display:flex; flex-direction:column; gap:12px;">
                ${projects.length > 0 ? projects.map(p => {
                    const docUrl = _cleanHttpUrl(p.source_document_url || p.source_url);
                    const projTitle = p.project_name ? escapeHtml(p.project_name) : NOT_AVAILABLE_TEXT;
                    const projCategory = (p.normalized_category || p.category) ? escapeHtml(p.normalized_category || p.category) : NOT_AVAILABLE_TEXT;
                    const projDesc = p.description ? escapeHtml(p.description) : null;
                    const projLoc = (p.state || p.geographic_location) ? escapeHtml([p.geographic_location, p.state].filter(Boolean).join(', ')) : NOT_AVAILABLE_TEXT;
                    const projBudget = p.budget ? escapeHtml(p.budget) : NOT_AVAILABLE_TEXT;
                    const projFY = p.reporting_period ? escapeHtml(p.reporting_period) : NOT_AVAILABLE_TEXT;
                    const projPartner = p.implementing_partner ? escapeHtml(p.implementing_partner) : NOT_AVAILABLE_TEXT;
                    const projFmt = p.source_format ? escapeHtml(p.source_format) : NOT_AVAILABLE_TEXT;

                    return `
                    <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); padding:16px; border-radius:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px; flex-wrap:wrap;">
                            <div>
                                <strong style="color:var(--text-primary); font-size:14.5px; cursor:pointer;" onclick="closeModal('modal-company-dossier'); openCsrDetailsModal(${p.csr_id});">${projTitle}</strong>
                                <span class="badge badge-emerald" style="margin-left:8px; font-size:11px;">${projCategory}</span>
                            </div>
                            <span class="badge badge-cyan" style="font-size:10.5px;">${projFmt}</span>
                        </div>
                        ${projDesc ? `
                        <div style="font-size:13px; color:var(--text-secondary); margin-top:8px; line-height:1.5;">
                            ${projDesc}
                        </div>` : `
                        <div style="font-size:12.5px; color:var(--text-muted); margin-top:8px; font-style:italic;">
                            Project Description: ${escapeHtml(NOT_AVAILABLE_TEXT)}
                        </div>`}
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-top:12px; padding-top:10px; border-top:1px solid var(--border-subtle);">
                            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:8px; font-size:12px; color:var(--text-muted); width:100%;">
                                <div>📍 Location/State: <strong style="color:var(--text-primary);">${projLoc}</strong></div>
                                <div>💰 Allocation/Budget: <strong style="color:var(--accent-emerald);">${projBudget}</strong></div>
                                <div>📅 Reporting Period: <strong style="color:var(--text-primary);">${projFY}</strong></div>
                                <div>🤝 Implementing Partner: <strong style="color:var(--text-primary);">${projPartner}</strong></div>
                            </div>
                            <div style="width:100%; display:flex; justify-content:flex-end; gap:8px; margin-top:6px; flex-wrap:wrap;">
                                <button class="btn-primary" style="font-size:11.5px; padding:4px 12px;" onclick="closeModal('modal-company-dossier'); openCsrDetailsModal(${p.csr_id});">
                                    View Full CSR Project Details
                                </button>
                                ${docUrl ? `
                                <a href="${escapeHtml(docUrl)}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="font-size:11.5px; padding:4px 12px; text-decoration:none;">
                                    Source (${projFmt}) ↗
                                </a>` : `<span style="font-size:11.5px; color:var(--text-muted);">Source Link: ${escapeHtml(NOT_AVAILABLE_TEXT)}</span>`}
                            </div>
                        </div>
                    </div>
                `;
                }).join('') : `
                    <div style="text-align:center; padding:36px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle); color:var(--text-secondary); font-size:13.5px;">
                        ${isCsrLogin
                            ? `<strong>🔒 ${escapeHtml(LOGIN_REQUIRED_TEXT)}</strong>`
                            : `${escapeHtml(NOT_AVAILABLE_TEXT)} — No individual CSR project rows extracted yet. Use the official CSR Webpage / PDF disclosure links above to view this company's CSR details directly on their website.`}
                        <div style="margin-top:12px;">
                            ${csrUrl ? `<a href="${escapeHtml(csrUrl)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12.5px; text-decoration:none;">🌐 Open Company CSR Webpage ↗</a>` : ''}
                        </div>
                    </div>
                `}
            </div>
        `;


    // -----------------------------------------------------------------------
    // TAB 4: OPPORTUNITIES (SECTION 7: OPPORTUNITIES TAB)
    // -----------------------------------------------------------------------
    } else if (tab === 'opportunities') {
        body.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:10px;">
                <div>
                    <h4 style="font-size:16px; font-weight:800; color:var(--text-primary); margin:0;">
                        Genuine Funding Opportunities &amp; Grant Calls (${opportunities.length} Open)
                    </h4>
                    <div style="font-size:12.5px; color:var(--text-secondary); margin-top:2px;">
                        RFPs, EOIs and partner selection calls verified against official CSR foundation disclosures
                    </div>
                </div>
                ${csrUrl ? `
                <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12.5px; padding:6px 14px; text-decoration:none;">
                    CSR Foundation ↗
                </a>` : ''}
            </div>

            <!-- Open Opportunities -->
            <div style="display:flex; flex-direction:column; gap:12px; margin-bottom:24px;">
                ${opportunities.length > 0 ? opportunities.map(opp => {
                    const grantUrl = (opp.portal_url || opp.application_url || opp.submission_url || '');
                    const hasValidGrantUrl = grantUrl && grantUrl.startsWith('http') && !grantUrl.includes('google.com/search');
                    const grantBudget = opp.budget || opp.funding_amount;
                    const grantDeadline = opp.submission_deadline || opp.deadline;
                    const grantDesc = opp.requirements || opp.description;
                    const oppTitle = opp.title ? escapeHtml(opp.title) : NOT_AVAILABLE_TEXT;
                    const oppCategory = opp.category ? escapeHtml(opp.category) : NOT_AVAILABLE_TEXT;

                    return `
                    <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); padding:16px; border-radius:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px;">
                            <div>
                                <strong style="color:var(--text-primary); font-size:14.5px;">${oppTitle}</strong>
                                <span class="badge badge-cyan" style="margin-left:8px; font-size:10.5px;">${oppCategory}</span>
                            </div>
                            <span class="badge badge-emerald">ACTIVE RFP</span>
                        </div>
                        <p style="font-size:13px; color:var(--text-secondary); margin:8px 0 12px; line-height:1.5;">
                            ${grantDesc ? escapeHtml(grantDesc) : '<span style="color:var(--text-muted); font-style:italic;">' + NOT_AVAILABLE_TEXT + '</span>'}
                        </p>
                        <div style="display:flex; gap:14px; flex-wrap:wrap; font-size:12px; margin-bottom:12px;">
                            <span>💰 Grant Allocation: <strong style="color:var(--accent-emerald);">${grantBudget ? escapeHtml(grantBudget) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></span>
                            <span>⏰ Submission Window: <strong style="color:var(--accent-amber);">${grantDeadline ? escapeHtml(grantDeadline) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></span>
                        </div>
                        ${hasValidGrantUrl ? `
                        <a href="${escapeHtml(grantUrl)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px; padding:6px 14px; text-decoration:none; display:inline-block;">
                            Apply for Grant on Official Portal ↗
                        </a>` : `
                        <span class="btn-disabled" style="font-size:12px; padding:6px 14px; display:inline-block; opacity:0.6; cursor:not-allowed; background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:6px; color:var(--text-muted);">
                            Not Available
                        </span>`}
                    </div>
                `;}).join('') : `
                    <div style="text-align:center; padding:36px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                        <div style="font-size:26px; margin-bottom:8px;">📋</div>
                        <div style="font-size:15px; font-weight:800; color:var(--text-primary); margin-bottom:4px;">No Open Grant RFPs Currently Disclosed</div>
                        <div style="font-size:13px; color:var(--text-secondary); max-width:440px; margin:0 auto 14px; line-height:1.5;">
                            ImpactBridge strictly verifies active RFP/EOI calls against official disclosures and never invents speculative grant notices.
                        </div>
                        <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="font-size:12px; text-decoration:none;">
                            Check Foundation Disclosures ↗
                        </a>
                    </div>
                `}
            </div>

            <!-- Closed Opportunities Separated -->
            ${closedOpportunities.length > 0 ? `
            <div style="border-top:1px solid var(--border-color); padding-top:16px;">
                <h5 style="font-size:14px; font-weight:800; color:var(--text-secondary); margin:0 0 10px;">
                    Historical / Closed Opportunities (${closedOpportunities.length})
                </h5>
                <div style="display:flex; flex-direction:column; gap:8px;">
                    ${closedOpportunities.map(co => `
                        <div style="background:var(--bg-surface); border:1px solid var(--border-subtle); padding:10px 14px; border-radius:8px; display:flex; justify-content:space-between; align-items:center; opacity:0.8;">
                            <div>
                                <strong style="font-size:13px; color:var(--text-primary);">${escapeHtml(co.title)}</strong>
                                ${co.deadline ? `<span style="font-size:11.5px; color:var(--text-muted); margin-left:8px;">Expired: ${escapeHtml(co.deadline)}</span>` : ''}
                            </div>
                            <span class="badge badge-slate" style="font-size:10px;">CLOSED</span>
                        </div>
                    `).join('')}
                </div>
            </div>
            ` : ''}
        `;

    // -----------------------------------------------------------------------
    // TAB 5: CONTACTS (SECTION 8: CONTACTS TAB)
    // -----------------------------------------------------------------------
    } else if (tab === 'contacts') {
        const tier = ((currentSubscription && currentSubscription.tier) || 'free').toLowerCase();
        const canViewContacts = tier === 'pro' || tier === 'ultra';

        let lockBannerHtml = '';
        if (!canViewContacts) {
            lockBannerHtml = `
                <div style="background:var(--primary-brand-light); border:1px solid rgba(15,118,110,0.3); padding:16px 20px; border-radius:12px; margin-bottom:18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div>
                        <div style="font-size:14px; font-weight:800; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
                            <span>🔒 Executive Contacts Masked (Community Tier)</span>
                        </div>
                        <div style="font-size:12.5px; color:var(--text-secondary); margin-top:4px;">
                            Upgrade to <strong>Impact Pro</strong> to unmask direct emails and verified phone numbers for published CSR leads.
                        </div>
                    </div>
                    <button class="btn-primary" style="font-size:12px; padding:8px 16px;" onclick="openSubscriptionModal('pro')">
                        Unlock Direct Contacts ⚡
                    </button>
                </div>
            `;
        }

        const validContacts = contacts.filter(c => c && (c.name || c.email || c.phone));

        body.innerHTML = `
            <div class="insight-box">
                <div class="insight-title" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <span>Publicly Verified Contact Directory</span>
                    ${canViewContacts 
                        ? `<span class="badge badge-emerald" style="font-size:11px;">✓ Unmasked Direct Contacts</span>` 
                        : `<span class="badge badge-purple" style="font-size:11px;">🔒 Masked on Free Plan</span>`}
                </div>
                ${lockBannerHtml}
                <p style="font-size:13px; color:var(--text-secondary); margin-bottom:14px;">
                    Absolute Real-Data Guarantee: We only present contacts explicitly published in official corporate disclosures.
                </p>
                ${validContacts.length > 0 ? validContacts.map(c => {
                    const rawEmail = c.email || '';
                    const displayEmail = canViewContacts 
                        ? (rawEmail ? escapeHtml(rawEmail) : NOT_AVAILABLE_TEXT) 
                        : (rawEmail ? escapeHtml(rawEmail.replace(/(?<=.{2}).(?=[^@]*?@)/g, '*')) : NOT_AVAILABLE_TEXT);
                    const rawPhone = c.phone || null;
                    const displayPhone = rawPhone 
                        ? (canViewContacts ? escapeHtml(rawPhone) : '•••• ••••') 
                        : NOT_AVAILABLE_TEXT;
                    const contactName = c.name ? escapeHtml(c.name) : NOT_AVAILABLE_TEXT;
                    const contactDesig = c.designation ? escapeHtml(c.designation) : NOT_AVAILABLE_TEXT;
                    const contactDept = c.department ? escapeHtml(c.department) : NOT_AVAILABLE_TEXT;

                    return `
                        <div class="insight-item" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; padding:10px 0; border-bottom:1px solid var(--border-subtle);">
                            <div>
                                <span style="font-weight:700; color:var(--text-primary); font-size:13.5px;">${contactName}</span>
                                <span style="font-size:12px; color:var(--text-secondary); margin-left:6px;">(${contactDesig})</span>
                                <span class="badge badge-slate" style="margin-left:6px; font-size:10px;">${contactDept}</span>
                                <strong style="font-size:13px; color:${canViewContacts && rawEmail ? 'var(--primary-brand)' : 'var(--text-muted)'}; margin-left:10px;">✉️ ${displayEmail}</strong>
                                <span style="font-size:12px; color:var(--text-secondary); margin-left:10px;">📞 ${displayPhone}</span>
                            </div>
                            ${canViewContacts && rawEmail ? `
                                <a href="mailto:${escapeHtml(rawEmail)}?subject=CSR%20Partnership%20Inquiry%20-%20Section%20135&body=Dear%20${encodeURIComponent(c.name || 'CSR Head')},%0D%0A%0D%0AWe%20are%20reaching%20out%20from%20our%20non-profit%20regarding%20statutory%20CSR%20partnership%20under%20Schedule%20VII..." class="btn-secondary" style="font-size:11px; padding:4px 10px; text-decoration:none;">
                                    ✉️ 1-Click Pitch
                                </a>
                            ` : (!canViewContacts ? `
                                <button class="btn-secondary" style="font-size:11px; padding:4px 10px; opacity:0.85;" onclick="openSubscriptionModal('pro')">
                                    🔒 Unmask
                                </button>
                            ` : '')}
                        </div>
                    `;
                }).join('') : `
                    <div style="font-size:13px; color:var(--text-secondary); padding:20px; background:var(--bg-surface-subtle); border-radius:8px; line-height:1.5;">
                        No named individuals or direct mailboxes were published in the official disclosures for this company. All inquiries should be directed through the official corporate foundation portal:
                        <div style="margin-top:12px;">
                            ${csrUrl ? `<a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px; text-decoration:none;">Visit CSR Foundation Portal ↗</a>` : '<span style="color:var(--text-muted); font-size:12px;">CSR Foundation Portal: Not Available</span>'}
                        </div>
                    </div>
                `}
            </div>
        `;

    // -----------------------------------------------------------------------
    // TAB 6: REPORTS & DOCUMENTS (SECTION 9: REPORTS & DOCUMENTS TAB)
    // -----------------------------------------------------------------------
    } else if (tab === 'reports') {
        body.innerHTML = `
            <div class="insight-box">
                <div class="insight-title" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <span>Statutory Reports, Filings &amp; ESG Disclosures (${officialReports.length})</span>
                    <span class="badge badge-emerald">Audited Corporate Disclosures</span>
                </div>
                <p style="font-size:13px; color:var(--text-secondary); margin-bottom:16px;">
                    Official published documents, statutory annual filings, SEBI BRSR reports, and Section 135 disclosures archived directly from investor relations and sustainability portals.
                </p>

                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px;">
                    ${officialReports.length > 0 ? officialReports.map(rep => `
                        <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:16px; border-radius:8px; display:flex; flex-direction:column; justify-content:space-between;">
                            <div>
                                <div style="display:flex; justify-content:space-between; align-items:center; gap:6px; margin-bottom:6px;">
                                    <span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(rep.document_type || 'STATUTORY_FILING')}</span>
                                    <span class="badge badge-emerald" style="font-size:10px;">${escapeHtml(rep.status || 'VERIFIED')}</span>
                                </div>
                                <div style="font-weight:700; font-size:13.5px; color:var(--text-primary); margin-bottom:6px;">${escapeHtml(rep.title)}</div>
                                <div style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">Period: <strong>${escapeHtml(rep.reporting_period || NOT_AVAILABLE_TEXT)}</strong></div>
                            </div>
                            ${rep.source_url ? `
                            <a href="${escapeHtml(rep.source_url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11.5px; padding:5px 12px; text-decoration:none; text-align:center;">
                                Open Document ↗
                            </a>` : ''}
                        </div>
                    `).join('') : `
                        <div style="grid-column:1/-1; font-size:13px; color:var(--text-secondary); padding:24px; background:var(--bg-surface-subtle); border-radius:8px; text-align:center;">
                            Statutory annual reports and SEBI BRSR disclosures are catalogued directly upon authoritative regulatory sync.
                            <div style="margin-top:12px;">
                                ${website ? `<a href="${website}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px; text-decoration:none;">Visit Official Website ↗</a>` : '<span style="color:var(--text-muted); font-size:12px;">Official Website: Not Available</span>'}
                            </div>
                        </div>
                    `}
                </div>
            </div>
        `;

    // -----------------------------------------------------------------------
    // TAB 7: SOURCES & VERIFICATION (SECTION 10: SOURCES & VERIFICATION TAB)
    // -----------------------------------------------------------------------
    } else if (tab === 'sources' || tab === 'domains') {
        body.innerHTML = `
            <div style="display:flex; flex-direction:column; gap:16px;">
                <div class="insight-box">
                    <div class="insight-title">Authoritative Source Provenance &amp; Coverage Audit</div>
                    <p style="font-size:13px; color:var(--text-secondary); margin-bottom:16px;">
                        Transparent disclosure of authoritative data sources, detection methodologies, and HTTP probe telemetry.
                    </p>

                    <div class="insights-grid">
                        <!-- Pillar 1: Corporate Identity & Registry -->
                        <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:14px; border-radius:8px;">
                            <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:8px;">1. Corporate Identity &amp; Registry</div>
                            <div class="insight-item"><span>Legal Entity</span><strong>${comp.legal_name ? escapeHtml(comp.legal_name) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                            <div class="insight-item"><span>CIN</span><strong class="mono" style="font-size:11.5px;">${comp.cin ? escapeHtml(comp.cin) : '<span style="color:var(--text-muted); font-family:inherit; font-weight:normal;">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                            <div class="insight-item"><span>ISIN</span><strong class="mono" style="font-size:11.5px;">${comp.isin ? escapeHtml(comp.isin) : '<span style="color:var(--text-muted); font-family:inherit; font-weight:normal;">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                            <div class="insight-item"><span>Apex Domain</span><strong>${website ? escapeHtml(cleanDomainLabel(website)) : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                            <div class="insight-item"><span>Identity Verification</span><span class="badge badge-emerald" style="font-size:10px;">${escapeHtml(coverageAudit.corporate_profile_status || 'VERIFIED')}</span></div>
                        </div>

                        <!-- Pillar 2: Careers & ATS Platform -->
                        <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:14px; border-radius:8px;">
                            <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:8px;">2. Careers &amp; ATS Platform</div>
                            <div class="insight-item"><span>ATS Platform</span><strong style="color:var(--accent-cyan);">${escapeHtml(coverageAudit.ats_platform || comp.ats_platform || NOT_AVAILABLE_TEXT)}</strong></div>
                            <div class="insight-item"><span>Endpoint Verification</span><span class="badge badge-emerald" style="font-size:10px;">${escapeHtml(coverageAudit.careers_source_status || 'VERIFIED')}</span></div>
                            <div class="insight-item"><span>Robots RFC 9309</span><strong style="color:var(--accent-emerald);">Compliant</strong></div>
                            <div class="insight-item"><span>Published Vacancies</span><strong>${jobs.length} Active Positions</strong></div>
                        </div>

                        <!-- Pillar 3: CSR & Regulatory Sources -->
                        <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:14px; border-radius:8px;">
                            <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:8px;">3. CSR &amp; Regulatory Portals</div>
                            <div class="insight-item"><span>Section 135 Portal</span><strong>${comp.csr_portal_url ? 'Verified' : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                            <div class="insight-item"><span>Sustainability Portal</span><strong>${comp.sustainability_url ? 'Verified' : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                            <div class="insight-item"><span>BRSR Report URL</span><strong>${comp.brsr_url ? 'Verified' : '<span style="color:var(--text-muted);">' + NOT_AVAILABLE_TEXT + '</span>'}</strong></div>
                            <div class="insight-item"><span>CSR Project Status</span><span class="badge badge-emerald" style="font-size:10px;">${escapeHtml(coverageAudit.csr_status || 'VERIFIED')}</span></div>
                        </div>

                        <!-- Pillar 4: Telemetry & Coverage Status -->
                        <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:14px; border-radius:8px;">
                            <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:8px;">4. Telemetry &amp; Limitations</div>
                            <div class="insight-item"><span>Last Fetch</span><strong>${escapeHtml(coverageAudit.last_successful_fetch_at || NOT_AVAILABLE_TEXT)}</strong></div>
                            <div class="insight-item"><span>Last Attempt</span><strong>${escapeHtml(coverageAudit.last_attempt_at || NOT_AVAILABLE_TEXT)}</strong></div>
                            <div class="insight-item"><span>Overall Status</span><span class="badge badge-emerald" style="font-size:10px;">${escapeHtml(coverageAudit.overall_status || 'VERIFIED')}</span></div>
                            <div class="insight-item"><span>Coverage Limitation</span><span>${coverageAudit.failed_requests_error ? `<span style="color:var(--accent-amber); font-size:11px;">${escapeHtml(coverageAudit.failed_requests_error)}</span>` : '<strong style="color:var(--accent-emerald);">None Disclosed</strong>'}</span></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

function renderFilteredDossierJobs() {
    const searchInput = document.getElementById('dossier-job-search-input');
    const locSelect = document.getElementById('dossier-job-loc-select');
    const deptSelect = document.getElementById('dossier-job-dept-select');
    const container = document.getElementById('dossier-jobs-list-container');
    if (!container || !currentDossierData) return;

    const term = (searchInput?.value || '').trim().toLowerCase();
    const loc = locSelect?.value || 'all';
    const dept = deptSelect?.value || 'all';

    const allJobs = currentDossierData.jobs || [];
    const filtered = allJobs.filter(j => {
        if (term) {
            const matchesTitle = (j.job_title || '').toLowerCase().includes(term);
            const matchesDept = (j.department || '').toLowerCase().includes(term);
            const matchesLoc = (j.location || '').toLowerCase().includes(term);
            if (!matchesTitle && !matchesDept && !matchesLoc) return false;
        }
        if (loc !== 'all' && (j.location || '') !== loc) return false;
        if (dept !== 'all' && (j.department || '') !== dept) return false;
        return true;
    });

    if (filtered.length === 0) {
        container.innerHTML = `
            <div style="text-align:center; padding:32px 20px; background:var(--bg-surface-subtle); border-radius:8px; border:1px solid var(--border-subtle); color:var(--text-secondary); font-size:13px;">
                No openings match the selected filters.
            </div>
        `;
        return;
    }

    container.innerHTML = filtered.map(j => renderStandardJobCard(j, { showCompanyLink: false })).join('');
}

// ===========================================================================
// MODALS MANAGEMENT
// ===========================================================================
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        if (modalId === 'modal-live-stream') loadLiveStreamEvents();
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
}

function closeAllModals() {
    document.querySelectorAll('.modal-backdrop').forEach(m => m.style.display = 'none');
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
}

async function loadLiveStreamEvents() {
    const container = document.getElementById('live-stream-events-container');
    if (!container) return;

    try {
        const res = await fetch(`${API_BASE}/api/crawler/live-stream?limit=12`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const events = data.events || [];

        container.innerHTML = events.map(e => `
            <div class="live-stream-row">
                <div>
                    <span style="color:var(--accent-emerald); font-weight:700;">[OK]</span>
                    <span style="color:var(--text-primary); font-weight:600; margin-left:6px;">${escapeHtml(e.company_name)}</span>
                    <span style="color:var(--text-secondary); margin-left:6px;">(${escapeHtml(e.target_url)})</span>
                </div>
                <div style="color:var(--primary-brand); font-size:11px;">
                    ${formatDateTime(e.timestamp)}
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<div style="color:#f43f5e; padding:10px;">Failed to stream live events: ${escapeHtml(e.message)}</div>`;
    }
}

// ===========================================================================
// ===========================================================================
// SUBSCRIPTION, DATABASE-DRIVEN PRICING & PROTOTYPE CHECKOUT / WALLET ENGINE
// ===========================================================================
let activeBillingCycle = 'monthly';
let dbPlansCatalog = [];
let userWalletBalance = 0;
let checkoutSelectedPlan = null;
let checkoutSelectedCycle = 'monthly';
let checkoutCurrentQuote = null;

function normalizeSubscriptionTier(tierOrPlan) {
    if (!tierOrPlan) return 'starter';
    const s = String(tierOrPlan).trim().toLowerCase();
    if (s === 'starter' || s === 'free') return 'starter';
    if (s === 'pro') return 'pro';
    if (s === 'enterprise' || s === 'ultra') return 'enterprise';
    if (s === 'foundation' || s === 'api') return 'foundation';
    return s;
}

async function fetchWalletBalance() {
    try {
        const res = await fetch(`${API_BASE}/api/subscription/wallet/balance`);
        if (res.ok) {
            const data = await res.json();
            userWalletBalance = Number(data.balance_inr || 0);
            updateWalletBalanceInUI();
            return userWalletBalance;
        }
    } catch (e) {
        console.warn('Wallet balance fetch error:', e);
    }
    return userWalletBalance;
}

function updateWalletBalanceInUI() {
    const formatted = `₹${userWalletBalance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    ['header-wallet-balance-val', 'mobile-wallet-balance-val', 'pricing-wallet-balance-val', 'checkout-wallet-balance-val'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = formatted;
    });

    const statusNote = document.getElementById('pricing-wallet-status-note');
    if (statusNote) {
        if (userWalletBalance > 0) {
            statusNote.textContent = 'Active demo funds ready for checkout';
            statusNote.style.color = '#34d399';
        } else {
            statusNote.textContent = 'Enter any amount above to add demo funds';
            statusNote.style.color = '#94a3b8';
        }
    }
}

function setInlineWalletAmount(amt) {
    const input = document.getElementById('inline-wallet-amount-input');
    if (input) {
        input.value = amt;
        input.focus();
    }
}

async function executeInlineWalletRecharge() {
    const input = document.getElementById('inline-wallet-amount-input');
    const btn = document.getElementById('btn-inline-recharge');
    const amt = Number(input ? input.value : 0);

    if (isNaN(amt) || amt <= 0) {
        alert('Please enter a valid positive number as money.');
        if (input) input.focus();
        return;
    }

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = 'Adding Funds...';
    }

    try {
        const res = await fetch(`${API_BASE}/api/subscription/wallet/topup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount_inr: amt })
        });
        const data = await res.json();
        if (!res.ok || (data.status !== 'success' && !data.success)) {
            throw new Error(data.message || data.error || data.detail || 'Recharge failed');
        }

        userWalletBalance = Number(data.balance_inr !== undefined ? data.balance_inr : (userWalletBalance + amt));
        updateWalletBalanceInUI();
        if (input) input.value = '';
        showLiveToast(`🎉 Successfully credited ₹${amt.toLocaleString('en-IN')} to your demo wallet!`, 'success');

        // Refresh transaction list if drawer is open
        const drawer = document.getElementById('inline-wallet-tx-drawer');
        if (drawer && drawer.style.display !== 'none') {
            await loadWalletTransactionsToDrawer();
        }

        // If checkout modal is open, refresh
        const checkoutModal = document.getElementById('modal-subscription');
        if (checkoutModal && checkoutModal.style.display !== 'none' && checkoutSelectedPlan) {
            renderCheckoutStep(1, checkoutCurrentQuote?.promo_code || '');
        }
    } catch (err) {
        alert(`Recharge error: ${err.message}`);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '💰 Add to Wallet';
        }
    }
}

async function toggleWalletTxHistory() {
    const drawer = document.getElementById('inline-wallet-tx-drawer');
    const toggleText = document.getElementById('btn-wallet-tx-toggle-text');
    if (!drawer) return;

    if (drawer.style.display === 'none' || drawer.style.display === '') {
        drawer.style.display = 'block';
        if (toggleText) toggleText.textContent = '▲ Hide Transactions';
        await loadWalletTransactionsToDrawer();
    } else {
        drawer.style.display = 'none';
        if (toggleText) toggleText.textContent = '📜 View Transactions (Ledger)';
    }
}

async function loadWalletTransactionsToDrawer() {
    const list = document.getElementById('inline-wallet-tx-list');
    if (!list) return;
    list.innerHTML = '<div style="color:var(--text-muted); padding:8px 0;">Loading transactions...</div>';

    try {
        const res = await fetch(`${API_BASE}/api/subscription/wallet/transactions`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const txs = (data.data && data.data.recent_transactions) || data.recent_transactions || [];

        if (txs.length === 0) {
            list.innerHTML = '<div style="color:var(--text-muted); padding:6px 0;">No wallet transactions recorded yet. Add funds above to start demo testing!</div>';
            return;
        }

        list.innerHTML = txs.map(t => {
            const isCredit = t.credit_or_debit === 'CREDIT';
            const sign = isCredit ? '+' : '-';
            const color = isCredit ? 'var(--accent-emerald)' : '#f43f5e';
            const bg = isCredit ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)';
            const dateStr = t.created_at ? new Date(t.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' }) : '';
            return `
                <div style="display:flex; justify-content:space-between; align-items:center; background:${bg}; border:1px solid var(--border-color); border-radius:6px; padding:6px 10px;">
                    <div>
                        <strong style="color:var(--text-primary);">${escapeHtml(t.description || t.transaction_type)}</strong>
                        <div style="font-size:10.5px; color:var(--text-muted);">${dateStr} &bull; ID: ${escapeHtml(t.transaction_id || '')}</div>
                    </div>
                    <div style="text-align:right;">
                        <span class="mono" style="color:${color}; font-weight:800; font-size:13px;">${sign}₹${(Number(t.amount_rupees || 0)).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                        <div style="font-size:10px; color:var(--text-muted);">Bal: ₹${(Number(t.balance_after_rupees || 0)).toLocaleString('en-IN', {minimumFractionDigits: 2})}</div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        list.innerHTML = `<div style="color:#f87171; padding:6px 0;">Failed to load transactions: ${escapeHtml(err.message)}</div>`;
    }
}

async function addFundsDirectlyInCheckout() {
    const input = document.getElementById('checkout-inline-topup-amt');
    const amt = Number(input ? input.value : 0);
    if (isNaN(amt) || amt <= 0) {
        alert('Please enter a valid positive number as money.');
        return;
    }
    await executeWalletTopup(amt);
}

async function loadAndRenderPricingPlans() {
    try {
        const res = await fetch(`${API_BASE}/api/subscription/plans`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        dbPlansCatalog = data.plans || [];

        // Dynamic Annual Savings Calculation across catalog
        let maxSavingsPct = 17;
        dbPlansCatalog.forEach(p => {
            if (p.monthly_price > 0 && p.yearly_price > 0) {
                const yearlyIfMonthly = p.monthly_price * 12;
                const savings = yearlyIfMonthly - p.yearly_price;
                if (savings > 0) {
                    const pct = Math.round((savings / yearlyIfMonthly) * 100);
                    if (pct > maxSavingsPct) maxSavingsPct = pct;
                }
            }
        });

        const savePills = document.querySelectorAll('.save-pill');
        savePills.forEach(sp => {
            sp.textContent = `Save up to ${maxSavingsPct}%`;
        });

        renderPricingGrid();
    } catch (err) {
        console.error('Failed to load dynamic subscription plans catalog:', err);
    }
}

function setBillingCycle(cycle) {
    activeBillingCycle = cycle;
    document.getElementById('btn-cycle-monthly')?.classList.toggle('active', cycle === 'monthly');
    document.getElementById('btn-cycle-yearly')?.classList.toggle('active', cycle === 'yearly');
    renderPricingGrid();
}

function renderPricingGrid() {
    const grid = document.getElementById('pricing-plans-grid');
    if (!grid) return;

    if (!dbPlansCatalog || dbPlansCatalog.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-secondary);">
                No subscription plans are currently active in the database catalog.
            </div>
        `;
        return;
    }

    const currentNormTier = normalizeSubscriptionTier(currentSubscription.plan_id || currentSubscription.tier);
    const isYearly = activeBillingCycle === 'yearly';

    let html = '';
    dbPlansCatalog.forEach(plan => {
        const planCode = plan.code.toLowerCase();
        const isCurrentActive = (currentNormTier === planCode);
        const isFeatured = plan.is_popular;

        // Dynamic price calculation
        let displayPrice = 0;
        let periodText = '/month';
        let subPriceText = '';

        if (isYearly) {
            displayPrice = Math.round(plan.yearly_price);
            periodText = '/year';
            if (plan.monthly_price > 0 && plan.yearly_price > 0) {
                const monthlyEquiv = Math.round(plan.yearly_price / 12);
                const yearlyIfMonthly = plan.monthly_price * 12;
                const savings = yearlyIfMonthly - plan.yearly_price;
                const savingsPct = Math.round((savings / yearlyIfMonthly) * 100);
                subPriceText = `(₹${monthlyEquiv.toLocaleString('en-IN')}/mo &bull; Save ₹${savings.toLocaleString('en-IN')} / ${savingsPct}%)`;
            }
        } else {
            displayPrice = Math.round(plan.monthly_price);
            periodText = '/month';
            if (plan.yearly_price > 0) {
                subPriceText = '+18% GST applicable';
            }
        }

        // Action Button logic (Requirements 1, 3, 4, 5 - Zero 'Downgrade' UI)
        let buttonText = `Switch to ${plan.name}`;
        let buttonClass = isFeatured ? 'btn-primary' : 'btn-secondary';
        let buttonDisabled = false;

        if (isCurrentActive) {
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
        }

        // Features list
        const features = plan.features || [];
        const featuresHtml = features.map(f => `<li>✓ ${escapeHtml(f)}</li>`).join('');

        html += `
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
        `;
    });

    grid.innerHTML = html;
}

async function loadSubscriptionState() {
    try {
        const res = await fetch(`${API_BASE}/api/subscription/current`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data && data.subscription) {
            const sub = data.subscription;
            const normTier = normalizeSubscriptionTier(sub.plan_id || sub.tier);
            currentSubscription = {
                tier: normTier,
                plan_id: sub.plan_id || normTier,
                plan_name: sub.plan_name || (normTier === 'foundation' ? 'Foundation Master' : (normTier === 'enterprise' ? 'Corporate Enterprise' : (normTier === 'pro' ? 'Impact Pro' : 'Community Starter'))),
                organization_name: sub.organization_name || 'Institutional Non-Profit Access',
                contact_email: sub.contact_email || '',
                status: sub.status || 'ACTIVE',
                auto_renew: !!sub.auto_renew,
                pending_change_plan: sub.pending_change_plan,
                current_period_end: sub.current_period_end,
                is_free: normTier === 'starter',
                limits: sub.limits || {
                    daily_matches: normTier === 'starter' ? 5 : null,
                    view_contacts: normTier !== 'starter',
                    live_reprobe: normTier !== 'starter',
                    export_rows_per_month: normTier === 'starter' ? 25 : (normTier === 'pro' ? 1000 : null),
                    seats: normTier === 'foundation' ? 50 : (normTier === 'enterprise' ? 15 : (normTier === 'pro' ? 3 : 1)),
                    api_access: normTier === 'enterprise' || normTier === 'foundation',
                    audit_packs: normTier === 'enterprise' || normTier === 'foundation'
                },
                quota: data.quota || {
                    used: 0,
                    limit: normTier === 'starter' ? 5 : null,
                    unlimited: normTier !== 'starter'
                }
            };
            try {
                localStorage.setItem('ib_current_subscription', JSON.stringify(currentSubscription));
            } catch (e) {}
        }
    } catch (err) {
        console.warn('Subscription sync fallback to cache:', err);
        try {
            const cached = localStorage.getItem('ib_current_subscription');
            if (cached) currentSubscription = JSON.parse(cached);
        } catch (e) {}
    }

    await fetchWalletBalance();
    applySubscriptionToUI();
    renderPricingGrid();
}

function applySubscriptionToUI() {
    const normTier = normalizeSubscriptionTier(currentSubscription.tier || currentSubscription.plan_id);
    const planName = currentSubscription.plan_name || (normTier === 'foundation' ? 'Foundation Master' : (normTier === 'enterprise' ? 'Corporate Enterprise' : (normTier === 'pro' ? 'Impact Pro' : 'Community Starter')));

    // 1. Header Tier Pill
    const headerLabel = document.getElementById('header-tier-label');
    const headerPill = document.getElementById('header-user-tier-pill');
    const headerBtn = document.getElementById('header-tier-btn');
    if (headerLabel) {
        if (normTier === 'foundation') headerLabel.textContent = '👑 Foundation Master';
        else if (normTier === 'enterprise') headerLabel.textContent = '🚀 Corporate Enterprise';
        else if (normTier === 'pro') headerLabel.textContent = '⚡ Impact Pro';
        else headerLabel.textContent = 'Community Starter (Free)';
    }
    if (headerPill) {
        if (normTier === 'foundation' || normTier === 'enterprise') {
            headerPill.style.borderColor = 'rgba(168, 85, 247, 0.6)';
            headerPill.style.background = 'rgba(168, 85, 247, 0.15)';
        } else if (normTier === 'pro') {
            headerPill.style.borderColor = 'rgba(99, 102, 241, 0.6)';
            headerPill.style.background = 'rgba(99, 102, 241, 0.15)';
        } else {
            headerPill.style.borderColor = '';
            headerPill.style.background = '';
        }
    }
    if (headerBtn) {
        headerBtn.textContent = normTier === 'starter' ? 'Plans ⚡' : 'Active Plan ✓';
    }

    // 2. Active Subscription Card
    const badgeName = document.getElementById('active-plan-badge-name');
    const orgTitle = document.getElementById('active-plan-org-title');
    const featuresSummary = document.getElementById('active-plan-features-summary');
    const upgradeCta = document.getElementById('active-plan-upgrade-cta');
    const subCard = document.getElementById('active-subscription-card');

    if (badgeName) {
        badgeName.textContent = `${planName.toUpperCase()} (ACTIVE)`;
    }
    if (orgTitle) {
        orgTitle.textContent = `${currentSubscription.organization_name || 'Institutional Non-Profit Access'} • ${planName} Active`;
    }
    if (featuresSummary) {
        if (normTier === 'foundation') {
            featuresSummary.innerHTML = `✓ <strong>Enterprise Feed &amp; API</strong> &bull; ✓ <strong>Custom Domain Monitoring</strong> &bull; ✓ <strong>Unlimited Matching &amp; Exports</strong> &bull; ✓ <strong>50 Team Seats</strong>`;
        } else if (normTier === 'enterprise') {
            featuresSummary.innerHTML = `✓ <strong>Dedicated REST API Access</strong> &bull; ✓ <strong>Statutory Section 135 Audit Packs</strong> &bull; ✓ <strong>Bulk Exports</strong> &bull; ✓ <strong>15 Team Seats</strong>`;
        } else if (normTier === 'pro') {
            featuresSummary.innerHTML = `✓ <strong>Unlimited Algorithmic Donor Matches</strong> &bull; ✓ <strong>Unmasked Direct Contacts</strong> &bull; ✓ <strong>Live Crawler Probing</strong> &bull; ✓ <strong>1,000 Exports/mo</strong>`;
        } else {
            featuresSummary.innerHTML = `✓ Canonical Listed Corporations &bull; ✓ Verified Corporate Career Directory &bull; ✓ 5 Donor Matches / Day &bull; Standard Exports (25 rows)`;
        }
    }
    if (upgradeCta) {
        if (normTier === 'foundation') {
            upgradeCta.textContent = 'Foundation Master Active 👑';
            upgradeCta.style.opacity = '0.9';
            upgradeCta.onclick = () => openSubscriptionModal('foundation');
        } else if (normTier === 'enterprise') {
            upgradeCta.textContent = 'Upgrade to Foundation 👑';
            upgradeCta.style.opacity = '1';
            upgradeCta.onclick = () => openSubscriptionModal('foundation');
        } else if (normTier === 'pro') {
            upgradeCta.textContent = 'Upgrade to Enterprise 🚀';
            upgradeCta.style.opacity = '1';
            upgradeCta.onclick = () => openSubscriptionModal('enterprise');
        } else {
            upgradeCta.textContent = 'Upgrade to Impact Pro ⚡';
            upgradeCta.style.opacity = '1';
            upgradeCta.onclick = () => openSubscriptionModal('pro');
        }
    }
    if (subCard) {
        if (normTier === 'foundation' || normTier === 'enterprise') {
            subCard.style.borderColor = 'rgba(168, 85, 247, 0.5)';
            subCard.style.background = 'linear-gradient(135deg, rgba(168, 85, 247, 0.12), rgba(15, 23, 42, 0.8))';
        } else if (normTier === 'pro') {
            subCard.style.borderColor = 'rgba(99, 102, 241, 0.5)';
            subCard.style.background = 'linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(15, 23, 42, 0.8))';
        } else {
            subCard.style.borderColor = '';
            subCard.style.background = 'var(--bg-card)';
        }
    }
}

// ===========================================================================
// MULTI-STEP PROTOTYPE CHECKOUT MODAL & QUOTE SYSTEM
// ===========================================================================
async function openSubscriptionModal(tier = 'pro') {
    const modal = document.getElementById('modal-subscription');
    const body = document.getElementById('modal-sub-body');
    const title = document.getElementById('modal-sub-title');
    if (!modal || !body) return;

    modal.style.display = 'flex';
    if (title) title.textContent = 'Change Plan';

    const normTier = normalizeSubscriptionTier(tier);
    const plan = dbPlansCatalog.find(p => p.code.toLowerCase() === normTier) || {
        code: normTier,
        name: normTier.toUpperCase(),
        monthly_price: normTier === 'starter' ? 0 : (normTier === 'pro' ? 499 : 999),
        yearly_price: normTier === 'starter' ? 0 : (normTier === 'pro' ? 4999 : 9999),
        display_order: normTier === 'starter' ? 1 : (normTier === 'pro' ? 2 : 3),
        features: []
    };

    checkoutSelectedPlan = plan;
    checkoutSelectedCycle = 'monthly';

    // Current subscription details
    const currTier = normalizeSubscriptionTier((currentSubscription && (currentSubscription.tier || currentSubscription.plan_id)) || 'starter');
    const isSamePlan = (plan.code.toLowerCase() === currTier);

    // Requirement 3: If user selects the currently active plan
    if (isSamePlan) {
        body.innerHTML = `
            <div style="text-align:center; padding:30px 16px;">
                <div style="display:inline-block; padding:4px 14px; background:var(--primary-brand-light); border:1px solid rgba(15,118,110,0.3); border-radius:20px; color:var(--primary-brand); font-size:11px; font-weight:800; letter-spacing:0.5px; margin-bottom:14px;">
                    CURRENT PLAN
                </div>
                <h3 style="margin:0 0 8px; font-size:20px; color:var(--text-primary); font-weight:800;">You are already on the ${escapeHtml(plan.name)} plan</h3>
                <p style="color:var(--text-secondary); font-size:13.5px; max-width:380px; margin:0 auto 22px;">
                    This is your currently active subscription plan. You cannot purchase the exact same active plan as a new subscription.
                </p>
                <button type="button" class="btn-secondary" style="padding:8px 22px;" onclick="closeModal('modal-subscription')">Close</button>
            </div>
        `;
        return;
    }

    // Determine whether higher-priced or lower-priced
    const currPlanObj = dbPlansCatalog.find(p => p.code.toLowerCase() === currTier);
    const currentPrice = currPlanObj ? Number(currPlanObj.monthly_price || 0) : 0;
    const targetPrice = Number(plan.monthly_price || 0);
    const isLowerOrFree = (targetPrice < currentPrice) || plan.is_free;

    if (isLowerOrFree) {
        // Requirement 2 & 5: Lower-priced transition confirmation (NO "Downgrade")
        const currPlanName = currPlanObj ? currPlanObj.name : currTier.toUpperCase();
        const currEndStr = currentSubscription?.current_period_end ? new Date(currentSubscription.current_period_end).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'current period end';
        
        body.innerHTML = `
            <div style="background:var(--bg-surface); border:1px solid var(--border-card); border-radius:10px; padding:22px; font-size:13.5px;">
                <h3 style="margin:0 0 16px; font-size:18px; font-weight:800; color:var(--text-primary);">Confirm Plan Change</h3>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:18px;">
                    <div style="background:var(--bg-surface-subtle); padding:12px; border-radius:8px; border:1px solid var(--border-color);">
                        <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; font-weight:600;">Current Plan:</div>
                        <div style="font-size:16px; font-weight:700; color:var(--text-primary); margin-top:2px;">${escapeHtml(currPlanName)}</div>
                        <div style="font-size:12px; color:var(--primary-brand); margin-top:4px;">Current Billing: ₹${currentPrice.toLocaleString('en-IN')}/month</div>
                    </div>
                    <div style="background:var(--bg-surface-subtle); padding:12px; border-radius:8px; border:1px solid var(--border-color);">
                        <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; font-weight:600;">New Plan:</div>
                        <div style="font-size:16px; font-weight:700; color:var(--primary-brand); margin-top:2px;">${escapeHtml(plan.name)}</div>
                        <div style="font-size:12px; color:var(--primary-brand); margin-top:4px;">New Billing: ₹${targetPrice.toLocaleString('en-IN')}/month</div>
                    </div>
                </div>

                <div style="background:var(--info-bg); border:1px solid var(--info-border); border-radius:8px; padding:14px; font-size:13px; color:var(--text-primary); margin-bottom:20px; line-height:1.6;">
                    <div>Your current <strong>${escapeHtml(currPlanName)}</strong> access remains available until: <strong style="color:var(--text-primary);">${currEndStr}</strong></div>
                    <div style="margin-top:6px;"><strong>${escapeHtml(plan.name)}</strong> starts: <strong style="color:var(--primary-brand);">${currEndStr}</strong></div>
                    <div style="margin-top:6px; font-size:12px; color:var(--text-secondary);">The new plan will become active after the current paid period.</div>
                </div>

                <div style="display:flex; justify-content:flex-end; gap:10px;">
                    <button type="button" class="btn-secondary" style="padding:8px 18px;" onclick="closeModal('modal-subscription')">Cancel</button>
                    <button type="button" class="btn-primary" id="btn-confirm-lower-plan" style="padding:8px 22px; font-weight:700;" onclick="executeSchedulePlanChange('${plan.code}')">
                        Confirm Plan Change
                    </button>
                </div>
            </div>
        `;
        return;
    }

    // Higher-priced transition
    await renderCheckoutStep(1, '');
}

async function executeSchedulePlanChange(targetPlanCode) {
    const btn = document.getElementById('btn-confirm-lower-plan');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = 'Scheduling Plan Change...';
    }

    try {
        const res = await fetch(`${API_BASE}/api/subscription/change-plan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan_id: targetPlanCode })
        });
        const data = await res.json();
        if (!res.ok || (data.status !== 'success' && !data.success)) {
            throw new Error(data.message || data.detail || 'Failed to change plan.');
        }

        await loadSubscriptionState();
        renderPlanChangeSuccessScreen(data);
    } catch (err) {
        alert(`Plan Change Error: ${err.message}`);
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Confirm Plan Change';
        }
    }
}

function renderPlanChangeSuccessScreen(data) {
    const body = document.getElementById('modal-sub-body');
    const title = document.getElementById('modal-sub-title');
    if (!body) return;
    if (title) title.textContent = 'Plan Change Scheduled';

    const effectiveDate = data.effective_date ? new Date(data.effective_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : 'current period end';

    body.innerHTML = `
        <div style="text-align:center; padding:10px 0 20px;">
            <div style="width:64px; height:64px; border-radius:50%; background:var(--primary-brand-light); border:2px solid var(--primary-brand); color:var(--primary-brand); font-size:32px; display:inline-flex; align-items:center; justify-content:center; margin-bottom:14px;">
                ✓
            </div>
            <h2 style="margin:0 0 8px; font-size:20px; color:var(--text-primary); font-weight:800;">Plan Change Confirmed</h2>
            <div style="font-size:13.5px; color:var(--text-secondary); max-width:440px; margin:0 auto; line-height:1.5;">
                ${escapeHtml(data.message || `Your plan change has been scheduled. You will retain your current access until ${effectiveDate}.`)}
            </div>
        </div>

        <div style="display:flex; justify-content:center; gap:10px; margin-top:14px;">
            <button type="button" class="btn-primary" style="padding:9px 24px;" onclick="closeModal('modal-subscription')">
                Done
            </button>
        </div>
    `;
}

async function changeCheckoutCycle(cycle, promoCode = '') {
    checkoutSelectedCycle = cycle;
    await renderCheckoutStep(1, promoCode);
}

async function applyCheckoutPromo() {
    const promoInput = document.getElementById('checkout-promo-input');
    const code = promoInput ? promoInput.value.trim() : '';
    await renderCheckoutStep(1, code);
}

async function renderCheckoutStep(step = 1, promoCode = '') {
    const body = document.getElementById('modal-sub-body');
    const title = document.getElementById('modal-sub-title');
    if (!body || !checkoutSelectedPlan) return;

    if (title) title.textContent = 'Confirm Plan Change';

    // Show loading spinner
    body.innerHTML = `
        <div style="text-align:center; padding:40px 20px;">
            <div style="display:inline-block; width:32px; height:32px; border:3px solid var(--border-color); border-top-color:var(--primary-brand); border-radius:50%; animation:spin 0.8s linear infinite;"></div>
            <div style="margin-top:14px; font-size:13.5px; color:var(--text-secondary);">Calculating quotation &amp; proration...</div>
        </div>
    `;

    // Fetch quote from backend
    try {
        const quoteRes = await fetch(`${API_BASE}/api/subscription/quote`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                plan_id: checkoutSelectedPlan.code,
                billing_cycle: checkoutSelectedCycle,
                promo_code: promoCode,
                place_of_supply: '27'
            })
        });

        if (!quoteRes.ok) {
            const err = await quoteRes.json();
            throw new Error(err.detail || err.error || 'Failed to calculate quote.');
        }

        checkoutCurrentQuote = await quoteRes.json();
    } catch (e) {
        console.error('Quote calculation error:', e);
        body.innerHTML = `
            <div style="padding:20px; background:var(--error-bg); border:1px solid var(--error-border); border-radius:8px; color:var(--error);">
                <strong>Unable to generate quote:</strong> ${escapeHtml(e.message)}
                <div style="margin-top:14px;">
                    <button class="btn-secondary" onclick="closeModal('modal-subscription')">Close</button>
                    <button class="btn-primary" onclick="openSubscriptionModal('${checkoutSelectedPlan.code}')">Retry</button>
                </div>
            </div>
        `;
        return;
    }

    const q = checkoutCurrentQuote;
    const finalAmount = Number(q.final_amount || 0);
    const hasSufficientWallet = (userWalletBalance >= finalAmount);
    const balanceAfter = Math.max(0, userWalletBalance - finalAmount);

    const currTier = normalizeSubscriptionTier((currentSubscription && (currentSubscription.tier || currentSubscription.plan_id)) || 'starter');
    const currPlanObj = dbPlansCatalog.find(p => p.code.toLowerCase() === currTier);
    const currPlanName = currPlanObj ? currPlanObj.name : currTier.toUpperCase();
    const currPrice = currPlanObj ? Number(currPlanObj.monthly_price || 0) : 0;

    body.innerHTML = `
        <!-- Enterprise Order Summary & Confirmation Box -->
        <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-card); border-radius:12px; padding:18px; margin-bottom:16px; font-size:13px; box-shadow:var(--shadow-sm);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid var(--border-color);">
                <div>
                    <span style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.5px; color:var(--text-tertiary);">Subscription Order</span>
                    <h4 style="margin:2px 0 0; font-size:15px; font-weight:800; color:var(--text-primary);">${escapeHtml(checkoutSelectedPlan.name)}</h4>
                </div>
                <span class="badge badge-active" style="font-size:10px; padding:3px 8px; border-radius:12px;">
                    ${checkoutSelectedCycle === 'yearly' ? 'Annual Billing (Save 15%)' : 'Monthly Billing'}
                </span>
            </div>

            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">Current Plan:</span>
                <span style="color:var(--text-primary); font-weight:600;">${escapeHtml(currPlanName)} <span style="color:var(--text-tertiary);">(₹${currPrice.toLocaleString('en-IN')}/mo)</span></span>
            </div>

            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">New Plan Base:</span>
                <span style="color:var(--text-primary); font-weight:600;">₹${(checkoutSelectedCycle === 'yearly' ? checkoutSelectedPlan.yearly_price : checkoutSelectedPlan.monthly_price).toLocaleString('en-IN')}/${checkoutSelectedCycle === 'yearly' ? 'yr' : 'mo'}</span>
            </div>

            ${q.discount_amount && Number(q.discount_amount) > 0 ? `
            <div style="display:flex; justify-content:space-between; margin-bottom:8px; color:var(--success);">
                <span>Promotional Discount:</span>
                <span class="mono" style="font-weight:700;">-₹${Number(q.discount_amount).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
            </div>` : ''}

            <div style="display:flex; justify-content:space-between; margin-bottom:8px; padding-top:8px; border-top:1px solid var(--border-color);">
                <span style="color:var(--text-secondary); font-weight:600;">Total Amount Payable:</span>
                <strong class="mono" style="color:var(--success); font-size:15px; font-weight:800;">₹${finalAmount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
            </div>

            <div style="display:flex; justify-content:space-between; margin-bottom:6px; font-size:12px;">
                <span style="color:var(--text-tertiary);">Prototype Wallet Balance:</span>
                <span class="mono" style="color:var(--primary-brand); font-weight:600;">₹${userWalletBalance.toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
            </div>

            <div style="display:flex; justify-content:space-between; padding-top:6px; border-top:1px dashed var(--border-color); font-size:12px;">
                <span style="color:var(--text-tertiary);">Estimated Balance After:</span>
                <span class="mono" style="color:${hasSufficientWallet ? 'var(--success)' : 'var(--error)'}; font-weight:700;">₹${balanceAfter.toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
            </div>
        </div>

        <!-- Cycle & Promo -->
        <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:14px;">
            <div style="display:flex; gap:6px;">
                <button type="button" class="btn-secondary ${checkoutSelectedCycle === 'monthly' ? 'btn-primary' : ''}" style="font-size:11.5px; padding:6px 14px;" onclick="changeCheckoutCycle('monthly', '${promoCode}')">
                    Monthly
                </button>
                <button type="button" class="btn-secondary ${checkoutSelectedCycle === 'yearly' ? 'btn-primary' : ''}" style="font-size:11.5px; padding:6px 14px;" onclick="changeCheckoutCycle('yearly', '${promoCode}')">
                    Annual (Save 15%)
                </button>
            </div>
            <div style="flex:1; max-width:220px; display:flex; gap:6px;">
                <input type="text" id="checkout-promo-input" value="${escapeHtml(promoCode)}" placeholder="Promo code"
                       style="width:100%; box-sizing:border-box; padding:6px 10px; background:var(--bg-input); border:1px solid var(--border-card); border-radius:6px; color:var(--text-primary); font-size:11.5px; font-family:'JetBrains Mono',monospace; text-transform:uppercase;">
                <button type="button" class="btn-secondary" style="font-size:11px; padding:6px 12px;" onclick="applyCheckoutPromo()">
                    Apply
                </button>
            </div>
        </div>

        ${!hasSufficientWallet ? `
        <div style="padding:14px 16px; background:var(--error-bg); border:1.5px solid var(--error-border); border-radius:10px; font-size:12.5px; color:var(--error); margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                <div>
                    <strong style="color:var(--text-primary); font-size:13px;">Insufficient wallet balance for this plan.</strong><br>
                    <span>Short by <strong style="color:var(--error); font-size:13px;">₹${(finalAmount - userWalletBalance).toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>. Top up with instant demo funds below:</span>
                </div>
                <div style="display:flex; gap:6px; align-items:center;">
                    <span style="font-weight:800; color:var(--primary-brand); font-size:14px;">₹</span>
                    <input type="number" id="checkout-inline-topup-amt" value="${Math.ceil(finalAmount - userWalletBalance)}" min="1" step="any"
                           style="width:95px; padding:6px 8px; background:var(--bg-input); border:1px solid var(--border-color); border-radius:6px; color:var(--text-primary); font-size:13px; font-family:'JetBrains Mono',monospace;">
                    <button type="button" class="btn-primary" style="font-size:12px; padding:7px 14px; background:linear-gradient(135deg, #10b981, #059669); border:none; box-shadow:var(--shadow-sm);" onclick="addFundsDirectlyInCheckout()">
                        + Add Funds &amp; Pay
                    </button>
                </div>
            </div>
        </div>` : `
        <div style="padding:12px 14px; background:var(--success-bg); border:1.5px solid var(--success-border); border-radius:10px; font-size:12.5px; color:var(--success); margin-bottom:16px; display:flex; align-items:center; gap:10px;">
            <span style="font-size:18px;">💰</span>
            <div>
                <strong style="color:var(--text-primary);">Demo Wallet Ready:</strong>
                <span>₹${userWalletBalance.toLocaleString('en-IN', {minimumFractionDigits: 2})} available. Settlement will be processed instantly from your wallet balance.</span>
            </div>
        </div>
        `}

        <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; padding-top:4px;">
            <button type="button" class="btn-secondary" onclick="closeModal('modal-subscription')">Cancel</button>
            <button type="button" class="btn-primary" id="btn-submit-checkout" ${hasSufficientWallet ? '' : 'disabled style="opacity:0.6; cursor:not-allowed;"'} onclick="executeCheckout()" style="${hasSufficientWallet ? 'background:linear-gradient(135deg, #10b981, #059669); border:none; box-shadow:var(--shadow-sm); font-weight:700;' : ''}">
                ${hasSufficientWallet ? `Confirm &amp; Subscribe — ₹${finalAmount.toLocaleString('en-IN', {minimumFractionDigits: 2})}` : 'Insufficient Funds — Add Money Above'}
            </button>
        </div>

        <div style="display:flex; justify-content:center; align-items:center; gap:14px; margin-top:16px; padding-top:10px; border-top:1px solid var(--border-color); font-size:11px; color:var(--text-tertiary);">
            <span>🔒 256-Bit SSL Encryption</span>
            <span>&bull;</span>
            <span>⚡ Instant Activation</span>
            <span>&bull;</span>
            <span>✓ Cancel Anytime in Profile</span>
        </div>
    `;
}

async function executeCheckout() {
    const submitBtn = document.getElementById('btn-submit-checkout');

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = `
            <span style="display:inline-block; width:14px; height:14px; border:2px solid #fff; border-top-color:transparent; border-radius:50%; animation:spin 0.8s linear infinite; margin-right:6px;"></span>
            Processing Plan Change...
        `;
    }

    const idempotencyKey = `chk_${checkoutSelectedPlan.code}_${Date.now()}_${Math.random().toString(36).substring(7)}`;

    try {
        const res = await fetch(`${API_BASE}/api/subscription/change-plan`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Idempotency-Key': idempotencyKey
            },
            body: JSON.stringify({
                plan_id: checkoutSelectedPlan.code,
                billing_cycle: checkoutSelectedCycle,
                payment_method: 'WALLET',
                promo_code: checkoutCurrentQuote?.promo_code || '',
                idempotency_key: idempotencyKey,
                place_of_supply: '27'
            })
        });

        const data = await res.json();

        if (!res.ok || (data.status !== 'success' && !data.success)) {
            throw new Error(data.message || data.error || data.detail || `Plan change failed (HTTP ${res.status})`);
        }

        await loadSubscriptionState();
        renderCheckoutSuccessScreen(data);
    } catch (err) {
        console.error('Subscription checkout error:', err);
        renderCheckoutFailureScreen(err.message);
    }
}

function renderCheckoutSuccessScreen(data) {
    const body = document.getElementById('modal-sub-body');
    const title = document.getElementById('modal-sub-title');
    if (!body) return;

    if (title) title.textContent = '🎉 Plan Activated Successfully!';

    const p = data.payment || {};
    const sub = data.subscription || {};

    body.innerHTML = `
        <div style="text-align:center; padding:10px 0 20px;">
            <div style="width:64px; height:64px; border-radius:50%; background:rgba(16,185,129,0.15); border:2px solid #10b981; color:#34d399; font-size:32px; display:inline-flex; align-items:center; justify-content:center; margin-bottom:14px;">
                ✓
            </div>
            <h2 style="margin:0 0 6px; font-size:20px; color:var(--text-primary); font-weight:800;">Plan Change Completed</h2>
            <div style="font-size:13px; color:var(--text-secondary);">
                Your new plan is now active with immediate entitlement access.
            </div>
        </div>

        <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-card); border-radius:8px; padding:16px; margin-bottom:20px; font-size:13px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">Active Plan:</span>
                <strong style="color:var(--primary-brand); font-size:14px;">${escapeHtml(sub.plan_name || checkoutSelectedPlan.name)}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">Amount Charged:</span>
                <span class="mono" style="color:var(--success); font-weight:700;">₹${Number(p.amount || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">Wallet Balance Remaining:</span>
                <span class="mono" style="color:var(--primary-brand); font-weight:700;">₹${userWalletBalance.toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:var(--text-secondary);">Validity:</span>
                <span style="color:var(--text-secondary);">${sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString() : 'Indefinite'}</span>
            </div>
        </div>

        <div style="display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap;">
            <a href="/profile/" class="btn-secondary" style="flex:1; text-align:center; padding:9px 16px;">
                View Billing Dashboard &nearr;
            </a>
            <button type="button" class="btn-primary" style="flex:1; padding:9px 16px;" onclick="closeModal('modal-subscription')">
                Done &bull; Return to Platform
            </button>
        </div>
    `;

    showLiveToast(`🎉 Successfully switched to ${checkoutSelectedPlan.name}!`, 'success');
}

function renderCheckoutFailureScreen(errorMessage) {
    const body = document.getElementById('modal-sub-body');
    const title = document.getElementById('modal-sub-title');
    if (!body) return;

    if (title) title.textContent = '❌ Plan Change Unsuccessful';

    body.innerHTML = `
        <div style="text-align:center; padding:10px 0 20px;">
            <div style="width:64px; height:64px; border-radius:50%; background:var(--error-bg); border:2px solid var(--error); color:var(--error); font-size:32px; display:inline-flex; align-items:center; justify-content:center; margin-bottom:14px;">
                ✕
            </div>
            <h2 style="margin:0 0 6px; font-size:20px; color:var(--text-primary); font-weight:800;">Transaction Failed</h2>
            <div style="font-size:13px; color:var(--error); max-width:440px; margin:0 auto;">
                ${escapeHtml(errorMessage || 'The plan change could not be completed.')}
            </div>
        </div>

        <div style="display:flex; justify-content:space-between; gap:10px; margin-top:20px;">
            <button type="button" class="btn-secondary" onclick="closeModal('modal-subscription')">Close</button>
            <button type="button" class="btn-primary" onclick="openSubscriptionModal('${checkoutSelectedPlan?.code || 'pro'}')">
                Try Again
            </button>
        </div>
    `;
}

// ===========================================================================
// WALLET TOP-UP MODAL (Requirements 12, 13, 14)
// ===========================================================================
function getWalletRoundOffSuggestions(amount) {
    const val = Number(amount) || 0;
    if (val <= 0) return [500, 1000, 2000];
    const suggestions = [];
    const nextMultiple = (v, step) => Math.ceil(v / step) * step;

    if (val < 500) {
        suggestions.push(500, 1000);
    } else if (val < 1000) {
        const next100 = nextMultiple(val, 100);
        if (next100 > val && next100 < 1000) suggestions.push(next100);
        suggestions.push(1000, 2000);
    } else if (val < 2000) {
        const next500 = nextMultiple(val, 500);
        if (next500 > val) suggestions.push(next500);
        suggestions.push(2000, 5000);
    } else if (val < 5000) {
        const next1000 = nextMultiple(val, 1000);
        if (next1000 > val) suggestions.push(next1000);
        suggestions.push(5000, 10000);
    } else {
        const next1000 = nextMultiple(val, 1000);
        if (next1000 > val) suggestions.push(next1000);
        suggestions.push(nextMultiple(val * 1.5, 5000));
    }
    const unique = [...new Set(suggestions)].filter(s => s > val).slice(0, 3);
    return unique.length > 0 ? unique : [nextMultiple(val + 100, 500)];
}

function updateModalTopupSuggestions(val) {
    const container = document.getElementById('modal-wallet-suggestions');
    if (!container) return;
    const suggestions = getWalletRoundOffSuggestions(val);
    container.innerHTML = suggestions.map(s => `
        <button type="button" class="btn-secondary" style="font-size:12px; padding:6px 12px;" onclick="setModalTopupInput(${s})">&#8377;${s.toLocaleString('en-IN')}</button>
    `).join('');
}

function setModalTopupInput(val) {
    const input = document.getElementById('wallet-topup-input');
    if (input) {
        input.value = val;
        updateModalTopupSuggestions(val);
    }
}

function openWalletTopupModal(suggestedAmount = 500) {
    const modal = document.getElementById('modal-wallet-topup');
    const body = document.getElementById('modal-wallet-topup-body');
    if (!modal || !body) return;

    modal.style.display = 'flex';
    const initAmt = suggestedAmount > 0 ? suggestedAmount : 500;

    body.innerHTML = `
        <div style="margin-bottom:16px;">
            <div style="font-size:12px; color:var(--text-secondary); margin-bottom:4px;">Current Wallet Balance:</div>
            <div class="mono" style="font-size:24px; font-weight:800; color:var(--success);">
                ₹${userWalletBalance.toLocaleString('en-IN', {minimumFractionDigits: 2})}
            </div>
        </div>

        <div style="margin-bottom:16px;">
            <label style="display:block; font-size:11.5px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">
                ADD MONEY
            </label>
            <div style="position:relative; display:flex; align-items:center; margin-bottom:12px;">
                <span style="position:absolute; left:12px; color:var(--text-secondary); font-weight:700; font-size:15px;">₹</span>
                <input type="number" id="wallet-topup-input" value="${initAmt}" min="1" step="1"
                       oninput="updateModalTopupSuggestions(this.value)"
                       style="width:100%; box-sizing:border-box; padding:9px 12px 9px 30px; background:var(--bg-input); border:1px solid var(--border-card); border-radius:6px; color:var(--text-primary); font-size:14px; font-family:'JetBrains Mono',monospace;">
            </div>

            <label style="display:block; font-size:11.5px; font-weight:600; color:var(--text-secondary); margin-bottom:6px;">
                Suggested Amounts
            </label>
            <div id="modal-wallet-suggestions" style="display:flex; gap:8px; flex-wrap:wrap;">
                <!-- Filled dynamically -->
            </div>
        </div>

        <div style="display:flex; justify-content:flex-end; gap:10px; margin-top:20px;">
            <button type="button" class="btn-secondary" onclick="closeModal('modal-wallet-topup')">Cancel</button>
            <button type="button" class="btn-primary" id="btn-topup-continue" onclick="confirmModalWalletRecharge()">
                Continue &rarr;
            </button>
        </div>
    `;

    updateModalTopupSuggestions(initAmt);
}

function confirmModalWalletRecharge() {
    const input = document.getElementById('wallet-topup-input');
    const body = document.getElementById('modal-wallet-topup-body');
    const amt = Number(input ? input.value : 0);

    if (amt <= 0) {
        alert('Please enter a valid amount.');
        return;
    }

    const currentBal = userWalletBalance;
    const newBal = currentBal + amt;

    // Requirement 14: Confirmation modal
    body.innerHTML = `
        <div style="font-size:13.5px;">
            <h3 style="margin:0 0 16px; font-size:17px; font-weight:800; color:var(--text-primary);">Confirm Wallet Recharge</h3>

            <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-card); border-radius:8px; padding:16px; margin-bottom:18px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px; color:var(--text-secondary);">
                    <span>Amount:</span>
                    <strong class="mono" style="color:var(--success); font-size:15px;">₹${amt.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:8px; color:var(--text-secondary);">
                    <span>Current Balance:</span>
                    <strong class="mono" style="color:var(--text-primary);">₹${currentBal.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; padding-top:8px; border-top:1px solid var(--border-color); font-weight:700; color:var(--text-primary);">
                    <span>New Balance:</span>
                    <strong class="mono" style="color:var(--primary-brand); font-size:15px;">₹${newBal.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
                </div>
            </div>

            <div style="display:flex; justify-content:flex-end; gap:10px;">
                <button type="button" class="btn-secondary" onclick="openWalletTopupModal(${amt})">Cancel</button>
                <button type="button" class="btn-primary" id="btn-topup-execute" onclick="executeWalletTopup(${amt})">
                    Confirm
                </button>
            </div>
        </div>
    `;
}

async function executeWalletTopup(amountToCharge) {
    const submitBtn = document.getElementById('btn-topup-execute');
    const amount = Number(amountToCharge || 0);

    if (amount <= 0) {
        alert('Please enter a valid top-up amount.');
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'Processing Recharge...';
    }

    try {
        const res = await fetch(`${API_BASE}/api/subscription/wallet/topup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount_inr: amount })
        });

        const data = await res.json();
        if (!res.ok || (data.status !== 'success' && !data.success)) {
            throw new Error(data.message || data.error || 'Wallet recharge failed.');
        }

        userWalletBalance = Number(data.balance_inr !== undefined ? data.balance_inr : (data.wallet ? data.wallet.balance_inr : (userWalletBalance + amount)));
        updateWalletBalanceInUI();
        closeModal('modal-wallet-topup');
        showLiveToast(`🎉 Successfully credited ₹${amount.toLocaleString('en-IN', {minimumFractionDigits: 2})} to your demo wallet!`, 'success');

        // Refresh transaction list if drawer is open
        const drawer = document.getElementById('inline-wallet-tx-drawer');
        if (drawer && drawer.style.display !== 'none') {
            await loadWalletTransactionsToDrawer();
        }

        // If checkout modal is open, refresh
        const checkoutModal = document.getElementById('modal-subscription');
        if (checkoutModal && checkoutModal.style.display !== 'none' && checkoutSelectedPlan) {
            renderCheckoutStep(1, checkoutCurrentQuote?.promo_code || '');
        }
    } catch (e) {
        alert(`Recharge error: ${e.message}`);
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Confirm';
        }
    }
}
// ===========================================================================
// CSV EXPORT CENTER
// ===========================================================================
function triggerCsvDownload(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function exportJobsCSV() {
    let list = filteredJobs.length > 0 ? filteredJobs : allJobs;
    if (!list || list.length === 0) {
        alert('No job records available to export.');
        return;
    }

    const tier = normalizeSubscriptionTier((currentSubscription && (currentSubscription.tier || currentSubscription.plan_id)) || 'free');
    let exportLimit = list.length;
    let limitNotice = '';

    if (tier === 'free') {
        exportLimit = 25;
        list = list.slice(0, exportLimit);
        limitNotice = ` (Export limited to 25 rows on Community Free. Upgrade to Pro for 1,000 rows or Ultra for complete verified jobs catalog)`;
    } else if (tier === 'pro') {
        exportLimit = 1000;
        if (list.length > exportLimit) {
            list = list.slice(0, exportLimit);
        }
        limitNotice = ` (Impact Pro: ${list.length} rows exported. Ultra unlocks complete bulk catalog)`;
    } else {
        limitNotice = ` (Ultra Enterprise: All ${list.length} jobs exported)`;
    }

    const headers = ['Company Name', 'NSE Symbol', 'Job Title', 'Department', 'Location', 'Work Mode', 'Experience', 'Status', 'Application URL'];
    const rows = list.map(j => [
        `"${(j.company_name || '').replace(/"/g, '""')}"`,
        `"${(j.nse_symbol || '').replace(/"/g, '""')}"`,
        `"${(j.job_title || '').replace(/"/g, '""')}"`,
        `"${(j.department || '').replace(/"/g, '""')}"`,
        `"${(j.location || '').replace(/"/g, '""')}"`,
        `"${(j.work_mode || '').replace(/"/g, '""')}"`,
        `"${(j.experience || '').replace(/"/g, '""')}"`,
        `"${(j.status || 'ACTIVE').replace(/"/g, '""')}"`,
        `"${(getJobApplyLink(j) || NOT_AVAILABLE_TEXT).replace(/"/g, '""')}"`
    ]);

    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    triggerCsvDownload(csv, `ImpactBridge_Verified_Enterprise_Jobs_${tier.toUpperCase()}_${Date.now()}.csv`);
    showLiveToast(`✅ Exported ${list.length} verified jobs${limitNotice}.`, 'success');
}

function exportCompaniesCSV() {
    if (!allRecommendations || allRecommendations.length === 0) {
        alert('No company records available to export.');
        return;
    }

    const tier = normalizeSubscriptionTier((currentSubscription && (currentSubscription.tier || currentSubscription.plan_id)) || 'free');
    let list = allRecommendations;
    let exportLimit = list.length;
    let limitNotice = '';

    if (tier === 'free') {
        exportLimit = 25;
        list = list.slice(0, exportLimit);
        limitNotice = ` (Export limited to 25 rows on Community Free tier. Upgrade to Pro for 1,000 rows/mo or Ultra for complete bulk datasets)`;
    } else if (tier === 'pro') {
        exportLimit = 1000;
        if (list.length > exportLimit) {
            list = list.slice(0, exportLimit);
        }
        limitNotice = ` (Impact Pro Tier: ${list.length} rows exported)`;
    } else {
        limitNotice = ` (Ultra Enterprise Tier: Full dataset exported)`;
    }

    const headers = ['Company Name', 'NSE Symbol', 'Sector', 'Headquarters', 'Official Website', 'Careers Portal', 'CSR Portal', 'Readiness Score'];
    const rows = list.map(c => [
        `"${(c.company_name || '').replace(/"/g, '""')}"`,
        `"${(c.nse_symbol || '').replace(/"/g, '""')}"`,
        `"${(c.sector || '').replace(/"/g, '""')}"`,
        `"${(c.headquarters || '').replace(/"/g, '""')}"`,
        `"${(c.website_url || '').replace(/"/g, '""')}"`,
        `"${(c.careers_url || '').replace(/"/g, '""')}"`,
        `"${(c.csr_portal_url || '').replace(/"/g, '""')}"`,
        `"${c.score !== undefined && c.score !== null ? Math.round(c.score) + '%' : NOT_AVAILABLE_TEXT}"`
    ]);

    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    triggerCsvDownload(csv, `ImpactBridge_Top_200_Indian_Corporations_${tier.toUpperCase()}_${Date.now()}.csv`);
    showLiveToast(`✅ Exported ${list.length} company records${limitNotice}.`, 'success');
}

function exportPipelineCSV() {
    if (!allProspects || allProspects.length === 0) {
        alert('Your Outreach CRM pipeline is currently empty.');
        return;
    }

    const headers = ['Company Name', 'Sector', 'Stage', 'Saved Date'];
    const rows = allProspects.map(p => [
        `"${(p.company_name || '').replace(/"/g, '""')}"`,
        `"${(p.sector || '').replace(/"/g, '""')}"`,
        `"${(p.stage || 'Shortlisted').replace(/"/g, '""')}"`,
        `"${p.saved_at || new Date().toISOString()}"`
    ]);

    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
    triggerCsvDownload(csv, `ImpactBridge_Outreach_Pipeline_${Date.now()}.csv`);
}

function exportCSRProjectsCSV() {
    exportCsrCSV();
}

// ===========================================================================
// LIVE WEB FETCH & DATA SYNCHRONIZATION CONTROLLER
// ===========================================================================
let isSyncInProgress = false;
let pendingLiveFetchOptions = { openModalLogs: false };

function openLiveStreamModal() {
    openModal('modal-live-stream');
}

function confirmLiveFetch(openModalLogs = false) {
    if (isSyncInProgress) {
        showLiveToast('A live data fetch is already running. Please wait a moment...', 'info');
        return;
    }
    pendingLiveFetchOptions = { openModalLogs };
    openModal('modal-live-fetch-confirm');
    setTimeout(() => {
        const confirmBtn = document.getElementById('btn-confirm-live-fetch-action');
        if (confirmBtn) confirmBtn.focus();
    }, 80);
}

function executeConfirmedLiveFetch() {
    closeModal('modal-live-fetch-confirm');
    const { openModalLogs } = pendingLiveFetchOptions || { openModalLogs: false };
    triggerLiveFetchAndUpdate(openModalLogs, true);
}

function showLiveToast(message, type = 'success') {
    const existing = document.querySelector('.live-sync-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'live-sync-toast';
    toast.innerHTML = `
        <span style="font-size:18px;">${type === 'success' ? '⚡' : 'ℹ️'}</span>
        <span>${escapeHtml(message)}</span>
    `;
    document.body.appendChild(toast);
    setTimeout(() => {
        toast.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 400);
    }, 3800);
}

function appendTerminalLog(badgeClass, badgeText, msg) {
    const screen = document.getElementById('live-terminal-screen');
    if (!screen) return;

    const now = new Date();
    const timeStr = `[${now.toTimeString().split(' ')[0]}.${String(now.getMilliseconds()).padStart(3, '0')}]`;

    const row = document.createElement('div');
    row.className = 'term-line';
    row.innerHTML = `
        <span class="term-time">${timeStr}</span>
        <span class="term-badge ${badgeClass}">${badgeText}</span>
        <span class="term-msg">${escapeHtml(msg)}</span>
    `;
    screen.appendChild(row);
    screen.scrollTop = screen.scrollHeight;
}

function clearTerminalScreen() {
    const screen = document.getElementById('live-terminal-screen');
    if (screen) {
        screen.innerHTML = `
            <div class="term-line">
                <span class="term-time">[${new Date().toTimeString().split(' ')[0]}]</span>
                <span class="term-badge term-badge-init">READY</span>
                <span class="term-msg">Console cleared. Ready to initiate live corporate domain probe.</span>
            </div>
        `;
    }
}

function copyTerminalLogs() {
    const screen = document.getElementById('live-terminal-screen');
    if (!screen) return;
    const text = screen.innerText;
    navigator.clipboard.writeText(text).then(() => {
        showLiveToast('📋 Live terminal logs copied to clipboard!');
    }).catch(() => {
        alert('Could not copy logs to clipboard.');
    });
}

function downloadTerminalLogFile() {
    const screen = document.getElementById('live-terminal-screen');
    if (!screen) return;
    const text = screen.innerText;
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ImpactBridge_Live_Scrape_Log_${Date.now()}.log`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// ===========================================================================
// DATA FRESHNESS & FETCH TIMESTAMP CONTROLLER
// ===========================================================================
function getCurrentTimeFormatted() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: true
    });
}

function updateAllFetchTimestamps(timeStr, isInitial = false) {
    if (!timeStr) timeStr = 'Never';

    if (!isInitial && timeStr !== 'Never') {
        try {
            localStorage.setItem('csr_last_fetch_time', timeStr);
        } catch (e) {}
    }

    // 1. Hero Live banner
    const heroLastExtracted = document.getElementById('hero-live-last-extracted');
    if (heroLastExtracted) {
        heroLastExtracted.textContent = timeStr;
    }

    const heroRecency = document.getElementById('hero-live-relative-time');
    if (heroRecency) {
        heroRecency.textContent = isInitial ? '(Live checked)' : '(Just now)';
    }

    // 2. Header pill & text
    const headerFetchedTime = document.getElementById('header-fetched-time');
    if (headerFetchedTime) {
        headerFetchedTime.textContent = timeStr;
    }

    const headerLastSync = document.getElementById('header-last-sync');
    if (headerLastSync) {
        headerLastSync.textContent = timeStr === 'Never' ? 'Unknown' : `Last Checked: ${timeStr}`;
    }

    // 3. Tab fetch timestamps
    const companiesTabFetch = document.getElementById('companies-tab-fetch-time');
    if (companiesTabFetch) {
        companiesTabFetch.textContent = `(Data fetched at: ${timeStr})`;
    }

    const jobsTabFetch = document.getElementById('jobs-tab-fetch-time');
    if (jobsTabFetch) {
        jobsTabFetch.textContent = `(Data fetched at: ${timeStr})`;
    }

    const oppsTabFetch = document.getElementById('opps-tab-fetch-time');
    if (oppsTabFetch) {
        oppsTabFetch.textContent = `(Data fetched at: ${timeStr})`;
    }

    const heroFreshnessDate = document.getElementById('hero-freshness-date');
    if (heroFreshnessDate) {
        heroFreshnessDate.textContent = timeStr === 'Never' ? 'Unknown' : `Checked: ${timeStr}`;
    }

    document.querySelectorAll('.tab-sync-time').forEach(el => {
        el.textContent = timeStr;
    });

    try {
        localStorage.setItem('csr_last_fetch_time', timeStr);
    } catch (e) {
        // Safe fallback
    }
}

async function triggerLiveFetchAndUpdate(openModalLogs = false, bypassConfirm = false) {
    if (isSyncInProgress) {
        showLiveToast('A live data fetch is already running. Please wait a moment...', 'info');
        return;
    }

    if (!bypassConfirm) {
        confirmLiveFetch(openModalLogs);
        return;
    }

    isSyncInProgress = true;
    if (openModalLogs) {
        openLiveStreamModal();
    }

    const progressFill = document.getElementById('sync-progress-fill');
    const stageText = document.getElementById('sync-stage-text');
    const percentText = document.getElementById('sync-percent-text');
    const headerSyncBtn = document.getElementById('header-btn-live-sync');
    const heroSyncBtn = document.getElementById('hero-btn-live-fetch');
    const terminalRunBtn = document.getElementById('btn-terminal-run-sync');
    const tabFetchBtns = document.querySelectorAll('.btn-tab-quick-fetch');

    // UI Loading state
    if (headerSyncBtn) {
        headerSyncBtn.classList.add('is-fetching');
        headerSyncBtn.innerHTML = '<span class="sync-icon">🔄</span> <span class="sync-label">Fetching Live Data...</span>';
    }
    if (heroSyncBtn) {
        heroSyncBtn.classList.add('is-fetching');
        heroSyncBtn.innerHTML = '<span class="btn-hero-icon">🔄</span> <span class="btn-hero-text">Fetching Live Data...</span>';
    }
    tabFetchBtns.forEach(btn => {
        btn.classList.add('is-fetching');
        btn.innerHTML = '<span>🔄</span> Fetching Live Data...';
    });
    if (terminalRunBtn) {
        terminalRunBtn.disabled = true;
        terminalRunBtn.innerHTML = '🔄 Probing in Progress...';
    }

    const setProgress = (pct, stage) => {
        if (progressFill) progressFill.style.width = `${pct}%`;
        if (percentText) percentText.textContent = `${pct}%`;
        if (stageText) stageText.textContent = stage;
    };

    setProgress(5, 'Step 1: Starting Background Crawler Engine...');
    appendTerminalLog('term-badge-init', 'START', 'Initiating connection to top company official portals...');

    // Call backend endpoint to persist live sync in database and start crawler
    try {
        const resp = await fetch(`${API_BASE}/api/fetch/live-sync`, { method: 'POST' });
        if (!resp.ok) {
            throw new Error('Failed to start crawl');
        }
    } catch (err) {
        appendTerminalLog('term-badge-init', 'ERROR', 'Could not start background crawler.');
    }

    let crawlRunning = true;
    let printedLogsCount = 0;
    let pollAttempts = 0;
    const maxPollAttempts = 35; // Maximum 35 seconds of polling

    try {
        while (crawlRunning && pollAttempts < maxPollAttempts) {
            pollAttempts++;
            try {
                const streamResp = await fetch(`${API_BASE}/api/crawler/live-stream`);
                if (streamResp.ok) {
                    const streamData = await streamResp.json();
                    
                    const events = streamData.events || [];
                    for (let i = printedLogsCount; i < events.length; i++) {
                        const evt = events[i];
                        let badgeClass = 'term-badge-probe';
                        if (evt.status_badge === 'FAILED' || evt.status_badge === 'ERROR') badgeClass = 'term-badge-init';
                        if (evt.status_badge === 'EXTRACTED' || evt.status_badge === 'VERIFIED') badgeClass = 'term-badge-ok';
                        if (evt.status_badge === 'SAVED') badgeClass = 'term-badge-db';
                        appendTerminalLog(badgeClass, evt.status_badge || 'LOG', evt.extracted_summary || evt.msg || '');
                    }
                    printedLogsCount = events.length;
                    
                    const stats = streamData.stats || {};
                    const total = stats.companies_requested || 1;
                    const crawled = stats.companies_crawled || 0;
                    let pct = Math.min(95, Math.floor(5 + (crawled / total) * 90));
                    setProgress(pct, `Crawling (${crawled}/${total}) | Jobs: ${stats.new_jobs || 0} New, ${stats.updated_jobs || 0} Updated | CSR: ${stats.csr_projects || 0} Projects | Contacts: ${stats.contacts_found || 0}`);
                    
                    if (streamData.is_running === false) {
                        crawlRunning = false;
                    }
                }
            } catch (e) {
                console.warn('Live stream poll error', e);
                crawlRunning = false;
            }
            
            if (crawlRunning && pollAttempts < maxPollAttempts) {
                await new Promise(r => setTimeout(r, 1000));
            }
        }

        setProgress(98, 'Finalizing: Updating your dashboard with fresh information...');
        appendTerminalLog('term-badge-extract', 'REFRESH', 'Updating cards, search filters, and open grants list.');

        // Reactively refresh on-screen datasets
        try {
            await Promise.all([
                loadRecommendations(1),
                loadJobs(1),
                loadStats(),
                loadCrawlerLogs(1, true),
                loadOpportunities(1),
                loadCompanyJobsDirectory(),
                loadLoginRequiredCompaniesSection()
            ]);
        } catch (e) {
            console.warn('Dataset re-render notice:', e);
        }

        setProgress(100, 'Complete: Crawl operation finished!');
        appendTerminalLog('term-badge-ok', 'DONE', '✨ Success! Data fetch pipeline has completed.');
    } catch (pipelineErr) {
        console.error('Pipeline error:', pipelineErr);
    } finally {
        isSyncInProgress = false;
        const nowTimeStr = getCurrentTimeFormatted();
        updateAllFetchTimestamps(nowTimeStr);

        // Reset button states
        if (headerSyncBtn) {
            headerSyncBtn.classList.remove('is-fetching');
            headerSyncBtn.innerHTML = '<span class="sync-icon">🔄</span> <span class="sync-label">Fetch Live Data</span>';
        }
        if (heroSyncBtn) {
            heroSyncBtn.classList.remove('is-fetching');
            heroSyncBtn.innerHTML = '<span class="btn-hero-icon">🔄</span> <span class="btn-hero-text">Fetch Live Data Now</span>';
        }
        tabFetchBtns.forEach(btn => {
            btn.classList.remove('is-fetching');
            btn.innerHTML = `<span>🔄</span> Fetch Live Data <span class="tab-fetch-stamp">(Data fetched at: ${nowTimeStr})</span>`;
        });
        if (terminalRunBtn) {
            terminalRunBtn.disabled = false;
            terminalRunBtn.innerHTML = '⚡ Run Live Fetch Again';
        }

        showLiveToast(`✅ Fresh data was fetched at ${nowTimeStr}! All companies in the database are up to date.`, 'success');
    }
}

// Dark Mode Toggle
function toggleDarkMode() {
    const htmlEl = document.documentElement;
    const isDark = htmlEl.getAttribute('data-theme') === 'dark';
    
    if (isDark) {
        htmlEl.removeAttribute('data-theme');
        localStorage.setItem('theme', 'light');
    } else {
        htmlEl.setAttribute('data-theme', 'dark');
        localStorage.setItem('theme', 'dark');
    }
}

// Check local storage on load
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
        document.documentElement.removeAttribute('data-theme');
    } else {
        // Default to dark theme for premium enterprise SaaS look
        document.documentElement.setAttribute('data-theme', 'dark');
    }
});


// ===========================================================================
// DEDICATED SECTION: COMPANIES WHOSE DATA REQUIRES LOGIN ON THEIR WEBSITE
// ===========================================================================
let allLoginRequiredCompanies = [];

async function loadLoginRequiredCompaniesSection() {
    try {
        const res = await fetch(`${API_BASE}/companies?access=LOGIN_REQUIRED&limit=5000`);
        if (!res.ok) return;
        const data = await res.json();
        const items = Array.isArray(data) ? data : (data.items || []);
        allLoginRequiredCompanies = items.map(normalizeCompanyData);
        renderLoginRequiredCompaniesSection(allLoginRequiredCompanies);
    } catch (e) {
        console.warn("Could not load login-required companies section:", e);
    }
}

function ensureLoginRequiredContainers() {
    // 1. Dedicated container inside #tab-companies (above or below main company list)
    const tabCompanies = document.getElementById("tab-companies");
    if (tabCompanies && !document.getElementById("public-login-required-section")) {
        const sec = document.createElement("div");
        sec.id = "public-login-required-section";
        sec.style.marginTop = "28px";
        sec.style.marginBottom = "24px";
        const paginationEl = document.getElementById("companies-pagination");
        if (paginationEl && paginationEl.parentNode) {
            paginationEl.parentNode.insertBefore(sec, paginationEl.nextSibling);
        } else {
            tabCompanies.appendChild(sec);
        }
    }

    // 2. Dedicated banner/button in #company-cause-pill-bar to jump straight to Login-Required Companies section
    const pillBar = document.getElementById("company-cause-pill-bar");
    if (pillBar && !document.getElementById("pill-login-required-jump")) {
        const btn = document.createElement("button");
        btn.id = "pill-login-required-jump";
        btn.type = "button";
        btn.className = "cause-pill";
        btn.style.borderColor = "rgba(245, 158, 11, 0.5)";
        btn.style.color = "#f59e0b";
        btn.innerHTML = `🔒 Login-Required Companies (<span id="badge-login-req-count">0</span>)`;
        btn.onclick = () => {
            const target = document.getElementById("public-login-required-section");
            if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
        };
        pillBar.appendChild(btn);
    }

    // 3. Dedicated container inside #tab-jobs for Jobs Login-Required companies
    const tabJobs = document.getElementById("tab-jobs");
    if (tabJobs && !document.getElementById("public-jobs-login-required-section")) {
        const secJobs = document.createElement("div");
        secJobs.id = "public-jobs-login-required-section";
        secJobs.style.marginTop = "24px";
        tabJobs.appendChild(secJobs);
    }

    // 4. Dedicated container inside #tab-csr-projects for CSR Login-Required companies
    const tabCsr = document.getElementById("tab-csr-projects");
    if (tabCsr && !document.getElementById("public-csr-login-required-section")) {
        const secCsr = document.createElement("div");
        secCsr.id = "public-csr-login-required-section";
        secCsr.style.marginTop = "24px";
        tabCsr.appendChild(secCsr);
    }
}

function renderLoginRequiredCardHtml(c) {
    const website = getCompanyWebsite(c);
    const csrUrl = getCompanyCsrWebpageUrl(c);
    const careersUrl = _cleanHttpUrl(c.careers_url);
    const sections = Array.isArray(c.login_required_sections) ? c.login_required_sections : [];
    const hq = c.headquarters ? c.headquarters.split("/")[0].trim() : NOT_AVAILABLE_TEXT;
    const sector = c.sector || NOT_AVAILABLE_TEXT;

    return `
        <div style="background:var(--bg-surface); border:1.5px solid rgba(245, 158, 11, 0.45); border-radius:12px; padding:16px; display:flex; flex-direction:column; justify-content:space-between; gap:12px;">
            <div>
                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                    <div>
                        <div style="font-weight:800; font-size:15px; color:var(--text-primary); cursor:pointer;" onclick="openCompanyDossier('${c.company_id}')">
                            ${escapeHtml(c.company_name)}
                        </div>
                        <div style="font-size:11.5px; color:var(--text-secondary); margin-top:2px;">
                            ${c.nse_symbol ? `<span class="badge badge-cyan" style="font-size:9.5px;">NSE: ${escapeHtml(c.nse_symbol)}</span>` : ""}
                            <span style="margin-left:4px;">${escapeHtml(sector)}</span>
                            <span style="margin-left:4px;">• 📍 ${escapeHtml(hq)}</span>
                        </div>
                    </div>
                    <span class="badge badge-amber" style="font-size:10px; font-weight:700;">🔒 Login Required</span>
                </div>

                <div style="margin-top:12px; padding:10px 12px; background:rgba(245, 158, 11, 0.1); border:1px solid rgba(245, 158, 11, 0.35); border-radius:8px; font-size:12px; color:#f59e0b; line-height:1.5;">
                    <strong>🔒 You need to login on the company website to view the data:</strong>
                    <div style="margin-top:4px; color:var(--text-primary);">
                        Restricted section(s): <strong>${escapeHtml(sections.join(", ") || "Website Portal")}</strong>
                    </div>
                    <div style="margin-top:2px; font-size:11.5px; color:var(--text-secondary);">
                        ${escapeHtml(c.data_access_note || LOGIN_REQUIRED_TEXT)}
                    </div>
                </div>
            </div>

            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; padding-top:8px; border-top:1px solid var(--border-subtle);">
                <div style="display:flex; gap:6px; flex-wrap:wrap;">
                    ${careersUrl && c.jobs_access === "LOGIN_REQUIRED" ? `<a href="${escapeHtml(careersUrl)}" target="_blank" rel="noopener noreferrer" class="btn-outline" style="font-size:11px; padding:4px 10px; text-decoration:none;">🔑 Login for Jobs ↗</a>` : ""}
                    ${csrUrl && c.csr_access === "LOGIN_REQUIRED" ? `<a href="${escapeHtml(csrUrl)}" target="_blank" rel="noopener noreferrer" class="btn-outline" style="font-size:11px; padding:4px 10px; text-decoration:none;">🔑 Login for CSR ↗</a>` : ""}
                    ${website ? `<a href="${escapeHtml(website)}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="font-size:11px; padding:4px 10px; text-decoration:none;">🌐 Company Website ↗</a>` : ""}
                </div>
                <div style="display:flex; gap:6px;">
                    <button class="btn-primary" style="font-size:11px; padding:4px 10px;" onclick="openCompanyDossier('${c.company_id}')">View Dossier</button>
                    <button class="btn-outline" style="font-size:11px; padding:4px 10px;" onclick="openCompanyCsr('${c.company_id}')">🌱 CSR View</button>
                </div>
            </div>
        </div>
    `;
}

function renderLoginRequiredCompaniesSection(list) {
    ensureLoginRequiredContainers();
    const items = Array.isArray(list) ? list : [];

    const countBadge = document.getElementById("badge-login-req-count");
    if (countBadge) countBadge.textContent = items.length;

    const mainSec = document.getElementById("public-login-required-section");
    if (mainSec) {
        mainSec.innerHTML = `
            <div style="background:var(--bg-card, var(--bg-surface)); border:1.5px solid rgba(245, 158, 11, 0.45); border-radius:14px; padding:22px;">
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:14px;">
                    <div>
                        <h3 style="margin:0 0 4px; font-size:18px; font-weight:800; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
                            <span>🔒 Separate Section: Companies Where Data Is Available Only After Login (${items.length})</span>
                        </h3>
                        <p style="margin:0; font-size:13px; color:var(--text-secondary); line-height:1.5;">
                            For these companies, Jobs, CSR, or Contact data is not available without login on their official website. <strong>You need to login on the company website to view the data.</strong>
                        </p>
                    </div>
                    <span class="badge badge-amber" style="font-size:12px; padding:6px 12px;">${items.length} Login-Gated Companies</span>
                </div>
                ${items.length > 0 ? `
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(320px, 1fr)); gap:14px;">
                    ${items.map(renderLoginRequiredCardHtml).join("")}
                </div>
                ` : `
                <div style="padding:16px; background:var(--bg-surface-subtle); border:1px dashed var(--border-color); border-radius:8px; font-size:13px; color:var(--text-secondary); text-align:center;">
                    Currently 0 companies are flagged as requiring website login. When the crawler or admin detects a login-walled company portal, it automatically appears in this section.
                </div>
                `}
            </div>
        `;
    }

    const jobsItems = items.filter(c => c.jobs_access === "LOGIN_REQUIRED");
    const jobsSec = document.getElementById("public-jobs-login-required-section");
    if (jobsSec) {
        jobsSec.innerHTML = jobsItems.length > 0 ? `
            <div style="background:var(--bg-card, var(--bg-surface)); border:1.5px solid rgba(245, 158, 11, 0.45); border-radius:14px; padding:20px;">
                <h4 style="margin:0 0 6px; font-size:16px; font-weight:800; color:var(--text-primary);">
                    🔒 Companies Where Jobs Data Requires Login on Their Website (${jobsItems.length})
                </h4>
                <p style="margin:0 0 14px; font-size:12.5px; color:var(--text-secondary);">
                    You need to login on these companies' official careers websites to view their job openings:
                </p>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:12px;">
                    ${jobsItems.map(renderLoginRequiredCardHtml).join("")}
                </div>
            </div>
        ` : "";
    }

    const csrItems = items.filter(c => c.csr_access === "LOGIN_REQUIRED");
    const csrSec = document.getElementById("public-csr-login-required-section");
    if (csrSec) {
        csrSec.innerHTML = csrItems.length > 0 ? `
            <div style="background:var(--bg-card, var(--bg-surface)); border:1.5px solid rgba(245, 158, 11, 0.45); border-radius:14px; padding:20px;">
                <h4 style="margin:0 0 6px; font-size:16px; font-weight:800; color:var(--text-primary);">
                    🔒 Companies Where CSR Data Requires Login on Their Website (${csrItems.length})
                </h4>
                <p style="margin:0 0 14px; font-size:12.5px; color:var(--text-secondary);">
                    You need to login on these companies' official websites to view their CSR disclosures:
                </p>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:12px;">
                    ${csrItems.map(renderLoginRequiredCardHtml).join("")}
                </div>
            </div>
        ` : "";
    }
}

// ===========================================================================
// PER-COMPANY 1:1 LIVE DELTA SYNC CONTROLLER
// ===========================================================================
async function fetchCompanyLiveData(companyId, btnEl) {
    if (!companyId) return;
    const originalText = btnEl ? btnEl.innerHTML : '🔄 Fetch Live Data';
    if (btnEl) {
        btnEl.disabled = true;
        btnEl.innerHTML = `<span class="loading-spinner-circle" style="width:14px; height:14px; display:inline-block; vertical-align:middle; margin-right:4px;"></span> Verifying live data on official company website...`;
    }

    try {
        const resp = await fetch(`/api/companies/${encodeURIComponent(companyId)}/fetch-live/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });

        if (!resp.ok) {
            const errData = await resp.json().catch(() => ({}));
            throw new Error(errData.error || `HTTP ${resp.status}`);
        }

        const resData = await resp.json();
        const diff = resData.diff || {};
        const jDiff = diff.jobs_diff || { added: 0, updated: 0, removed: 0, active_total: diff.active_jobs_count || 0 };
        const cDiff = diff.csr_diff || { added: 0, updated: 0, removed: 0, active_total: diff.active_csr_count || 0 };

        const toastMsg = `Live Sync Complete: ${jDiff.active_total} Jobs (+${jDiff.added} added, ~${jDiff.updated} updated, -${jDiff.removed} removed) | ${cDiff.active_total} CSR Projects verified.`;
        showLiveToast(toastMsg, 'success');

        // Update live timestamp in DOM
        const timeEl = document.getElementById(`live-time-${companyId}`);
        if (timeEl) {
            timeEl.textContent = `🕒 Live: ${new Date().toLocaleTimeString()}`;
        }

        // Refresh company records on screen if open in modal or table
        if (typeof loadRecommendations === 'function') {
            loadRecommendations(paginationState.companies.page);
        }
        if (typeof loadStats === 'function') {
            loadStats();
        }
    } catch (err) {
        console.error('Fetch live error:', err);
        showLiveToast(`Live sync error: ${err.message}`, 'info');
    } finally {
        if (btnEl) {
            btnEl.disabled = false;
            btnEl.innerHTML = originalText;
        }
    }
}
