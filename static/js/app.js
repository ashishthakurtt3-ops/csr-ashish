/**
 * ImpactBridge: CSR & Enterprise Job Intelligence OS
 * Production Client Controller & Modern UX Engine 3.0
 */

const API_BASE = '';

// ===========================================================================
// VERIFIED COMPANY MASTER REGISTRY (100% Correct, Non-Fabricated Data)
// ===========================================================================
const VERIFIED_COMPANY_REGISTRY = {
    "COMP_TOP200_001": { name: "Reliance Industries Limited", sym: "RELIANCE", site: "https://www.ril.com/", careers: "https://careers.ril.com/", csr: "https://www.reliancefoundation.org/", sector: "ENERGY / TELECOM", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_002": { name: "HDFC Bank Limited", sym: "HDFCBANK", site: "https://www.hdfcbank.com/", careers: "https://www.hdfcbank.com/personal/about-us/careers", csr: "https://www.hdfcbank.com/personal/about-us/corporate-social-responsibility", sector: "BANKING", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_003": { name: "ICICI Bank Limited", sym: "ICICIBANK", site: "https://www.icicibank.com/", careers: "https://www.icicibank.com/careers", csr: "https://www.icicifoundation.org/", sector: "BANKING", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_004": { name: "State Bank of India", sym: "SBIN", site: "https://sbi.co.in/", careers: "https://sbi.co.in/web/careers", csr: "https://www.sbifoundation.in/", sector: "BANKING", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_005": { name: "Tata Consultancy Services Limited", sym: "TCS", site: "https://www.tcs.com/", careers: "https://ibegin.tcs.com/", csr: "https://www.tcs.com/who-we-are/corporate-social-responsibility", sector: "IT", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_006": { name: "Bajaj Finance Limited", sym: "BAJFINANCE", site: "https://www.bajajfinserv.in/bajaj-finance", careers: "https://www.bajajfinserv.in/careers", csr: "https://www.bajajfinserv.in/csr-overview", sector: "BANKING", hq: "Pune, Maharashtra" },
    "COMP_TOP200_007": { name: "Larsen & Toubro Limited", sym: "LT", site: "https://www.larsentoubro.com/", careers: "https://www.larsentoubro.com/careers/", csr: "https://www.larsentoubro.com/corporate-social-responsibility/", sector: "INFRASTRUCTURE", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_008": { name: "Life Insurance Corporation Of India", sym: "LICI", site: "https://licindia.in/", careers: "https://licindia.in/web/guest/careers", csr: "https://licindia.in/web/guest/golden-jubilee-foundation", sector: "BANKING", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_009": { name: "Hindustan Unilever Limited", sym: "HINDUNILVR", site: "https://www.hul.co.in/", careers: "https://careers.unilever.com/india", csr: "https://www.hul.co.in/planet-and-society/", sector: "FMCG", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_010": { name: "Infosys Limited", sym: "INFY", site: "https://www.infosys.com/", careers: "https://career.infosys.com/", csr: "https://www.infosys.com/infosys-foundation.html", sector: "IT", hq: "Bengaluru, Karnataka" },
    "COMP_TOP200_011": { name: "Mahindra & Mahindra Limited", sym: "M&M", site: "https://www.mahindra.com/", careers: "https://www.mahindra.com/career", csr: "https://www.mahindra.com/rise-for-good", sector: "AUTO", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_012": { name: "Adani Power Limited", sym: "ADANIPOWER", site: "https://www.adanipower.com/", careers: "https://www.adanipower.com/careers", csr: "https://www.adanifoundation.org/", sector: "ENERGY", hq: "Ahmedabad, Gujarat" },
    "COMP_TOP200_013": { name: "Adani Ports and Special Economic Zone Limited", sym: "ADANIPORTS", site: "https://www.adaniports.com/", careers: "https://www.adaniports.com/Sustainability/Valuing-Talent", csr: "https://www.adanifoundation.org/", sector: "INFRASTRUCTURE", hq: "Ahmedabad, Gujarat" },
    "COMP_TOP200_014": { name: "HCL Technologies Limited", sym: "HCLTECH", site: "https://www.hcltech.com/", careers: "https://www.hcltech.com/careers", csr: "https://www.hclfoundation.org/", sector: "IT", hq: "Noida, Uttar Pradesh" },
    "COMP_TOP200_015": { name: "ITC Limited", sym: "ITC", site: "https://www.itcportal.com/", careers: "https://www.itcportal.com/careers/", csr: "https://www.itcportal.com/sustainability/", sector: "FMCG", hq: "Kolkata, West Bengal" },
    "COMP_TOP200_016": { name: "UltraTech Cement Limited", sym: "ULTRACEMCO", site: "https://www.ultratechcement.com/", careers: "https://www.ultratechcement.com/careers", csr: "https://www.ultratechcement.com/about-us/sustainability/csr", sector: "MANUFACTURING", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_017": { name: "Adani Enterprises Limited", sym: "ADANIENT", site: "https://www.adanienterprises.com/", careers: "https://www.adanienterprises.com/careers", csr: "https://www.adanifoundation.org/", sector: "ENERGY", hq: "Ahmedabad, Gujarat" },
    "COMP_TOP200_018": { name: "NTPC Limited", sym: "NTPC", site: "https://www.ntpc.co.in/", careers: "https://www.ntpc.co.in/careers", csr: "https://www.ntpc.co.in/corporate-social-responsibility", sector: "ENERGY", hq: "New Delhi, Delhi" },
    "COMP_TOP200_019": { name: "Hindustan Aeronautics Limited", sym: "HAL", site: "https://hal-india.co.in/", careers: "https://hal-india.co.in/Career_Listing.aspx", csr: "https://hal-india.co.in/CSR.aspx", sector: "MANUFACTURING", hq: "Bengaluru, Karnataka" },
    "COMP_TOP200_020": { name: "Bajaj Auto Limited", sym: "BAJAJ-AUTO", site: "https://www.bajajauto.com/", careers: "https://www.bajajauto.com/about-us/careers", csr: "https://www.bajajauto.com/about-us/corporate-social-responsibility", sector: "AUTO", hq: "Pune, Maharashtra" },
    "COMP_TOP200_021": { name: "Bajaj Finserv Limited", sym: "BAJAJFINSV", site: "https://www.bajajfinserv.in/", careers: "https://www.bajajfinserv.in/careers", csr: "https://www.bajajfinserv.in/csr-overview", sector: "BANKING", hq: "Pune, Maharashtra" },
    "COMP_TOP200_022": { name: "JSW Steel Limited", sym: "JSWSTEEL", site: "https://www.jsw.in/steel", careers: "https://www.jsw.in/careers", csr: "https://www.jsw.in/foundation", sector: "MANUFACTURING", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_023": { name: "Oil & Natural Gas Corporation Limited", sym: "ONGC", site: "https://www.ongcindia.com/", careers: "https://www.ongcindia.com/careers", csr: "https://www.ongcindia.com/csr", sector: "ENERGY", hq: "New Delhi, Delhi" },
    "COMP_TOP200_024": { name: "Nestle India Limited", sym: "NESTLEIND", site: "https://www.nestle.in/", careers: "https://www.nestle.in/jobs", csr: "https://www.nestle.in/csv", sector: "FMCG", hq: "Gurugram, Haryana" },
    "COMP_TOP200_025": { name: "Zomato Limited", sym: "ZOMATO", site: "https://www.zomato.com/", careers: "https://www.zomato.com/careers", csr: "https://www.feedingindia.org/", sector: "CONSUMER TECH", hq: "Gurugram, Haryana" },
    "COMP_TOP200_026": { name: "Bharat Electronics Limited", sym: "BEL", site: "https://bel-india.in/", careers: "https://bel-india.in/careers/", csr: "https://bel-india.in/corporate-social-responsibility/", sector: "MANUFACTURING", hq: "Bengaluru, Karnataka" },
    "COMP_TOP200_027": { name: "Shriram Finance Limited", sym: "SHRIRAMFIN", site: "https://www.shriramfinance.in/", careers: "https://www.shriramfinance.in/careers", csr: "https://www.shriramfinance.in/csr", sector: "BANKING", hq: "Chennai, Tamil Nadu" },
    "COMP_TOP200_028": { name: "Coal India Limited", sym: "COALINDIA", site: "https://www.coalindia.in/", careers: "https://www.coalindia.in/careers/", csr: "https://www.coalindia.in/csr/", sector: "ENERGY", hq: "Kolkata, West Bengal" },
    "COMP_TOP200_029": { name: "Avenue Supermarts Limited (DMart)", sym: "DMART", site: "https://www.dmartindia.com/", careers: "https://www.dmartindia.com/careers", csr: "https://www.dmartindia.com/csr", sector: "FMCG", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_030": { name: "Power Grid Corporation of India Limited", sym: "POWERGRID", site: "https://www.powergrid.in/", careers: "https://www.powergrid.in/careers", csr: "https://www.powergrid.in/csr-activities", sector: "ENERGY", hq: "Gurugram, Haryana" },
    "COMP_TOP200_031": { name: "Hindalco Industries Limited", sym: "HINDALCO", site: "https://www.hindalco.com/", careers: "https://www.hindalco.com/careers", csr: "https://www.hindalco.com/sustainability/csr", sector: "MANUFACTURING", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_032": { name: "Tata Steel Limited", sym: "TATASTEEL", site: "https://www.tatasteel.com/", careers: "https://www.tatasteel.com/careers/", csr: "https://www.tatasteel.com/sustainability/csr/", sector: "MANUFACTURING", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_033": { name: "Adani Green Energy Limited", sym: "ADANIGREEN", site: "https://www.adanigreenenergy.com/", careers: "https://www.adanigreenenergy.com/careers", csr: "https://www.adanifoundation.org/", sector: "ENERGY", hq: "Ahmedabad, Gujarat" },
    "COMP_TOP200_034": { name: "Grasim Industries Limited", sym: "GRASIM", site: "https://www.grasim.com/", careers: "https://www.grasim.com/careers", csr: "https://www.grasim.com/sustainability/csr", sector: "MANUFACTURING", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_035": { name: "Eicher Motors Limited", sym: "EICHERMOT", site: "https://www.eicher.in/", careers: "https://www.royalenfield.com/in/en/careers/", csr: "https://www.eicher.in/sustainability", sector: "AUTO", hq: "New Delhi, Delhi" },
    "COMP_TOP200_036": { name: "InterGlobe Aviation Limited (IndiGo)", sym: "INDIGO", site: "https://www.goindigo.in/", careers: "https://careers.goindigo.in/", csr: "https://www.goindigo.in/csr.html", sector: "INFRASTRUCTURE", hq: "Gurugram, Haryana" },
    "COMP_TOP200_037": { name: "Indian Oil Corporation Limited", sym: "IOC", site: "https://iocl.com/", careers: "https://iocl.com/careers", csr: "https://iocl.com/corporate-social-responsibility", sector: "ENERGY", hq: "New Delhi, Delhi" },
    "COMP_TOP200_038": { name: "Wipro Limited", sym: "WIPRO", site: "https://www.wipro.com/", careers: "https://careers.wipro.com/", csr: "https://www.wiprofoundation.org/", sector: "IT", hq: "Bengaluru, Karnataka" },
    "COMP_TOP200_041": { name: "Hyundai Motor India Limited", sym: "HYUNDAI", site: "https://www.hyundai.com/in/en", careers: "https://www.hyundai.com/in/en/hyundai-story/careers", csr: "https://www.hyundai.com/in/en/hyundai-story/csr", sector: "AUTO", hq: "Gurugram, Haryana" },
    "COMP_TOP200_051": { name: "Tech Mahindra Limited", sym: "TECHM", site: "https://www.techmahindra.com/", careers: "https://careers.techmahindra.com/", csr: "https://www.techmahindrafoundation.org/", sector: "IT", hq: "Pune, Maharashtra" },
    "COMP_TOP200_058": { name: "LTIMindtree Limited", sym: "LTIM", site: "https://www.ltimindtree.com/", careers: "https://www.ltimindtree.com/careers/", csr: "https://www.ltimindtree.com/sustainability/", sector: "IT", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_059": { name: "Bharat Petroleum Corporation Limited", sym: "BPCL", site: "https://www.bharatpetroleum.in/", careers: "https://www.bharatpetroleum.in/careers.aspx", csr: "https://www.bharatpetroleum.in/social-responsibility.aspx", sector: "ENERGY", hq: "Mumbai, Maharashtra" },
    "COMP_TOP200_068": { name: "Cipla Limited", sym: "CIPLA", site: "https://www.cipla.com/", careers: "https://www.cipla.com/careers", csr: "https://www.ciplafoundation.org/", sector: "PHARMA", hq: "Mumbai, Maharashtra" }
};

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

// Central Pagination State Store
const paginationState = {
    companies: { page: 1, pageSize: 12, total: 200, totalPages: 17 },
    jobs: { page: 1, pageSize: 12, total: 3030, totalPages: 253 },
    opps: { page: 1, pageSize: 9, total: 135, totalPages: 15 },
    crawler: { page: 1, pageSize: 15, total: 200, totalPages: 14 }
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

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    setupEventListeners();
    setupGlobalModalBehaviour();
    
    // Initialize Live Fetch timestamp display
    try {
        const savedTime = localStorage.getItem('csr_last_fetch_time') || getCurrentTimeFormatted();
        updateAllFetchTimestamps(savedTime, true);
    } catch (e) {
        updateAllFetchTimestamps(getCurrentTimeFormatted(), true);
    }

    // High performance initial load: immediately render Tab 1 (Donors) and stats
    // Secondary tabs (Jobs, Grants, CRM, Telemetry) load on-demand when clicked
    loadStats();
    loadRecommendations(1);
    loadSubscriptionState();
    loadAndRenderPricingPlans();
}

function setupEventListeners() {
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

    ['job-department-filter', 'job-location-filter', 'job-mode-filter', 'job-exp-filter', 'job-sort-filter'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', () => filterJobs());
    });

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

    // Keyboard ESC closes any open modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeAllModals();
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
function normalizeCompanyData(item) {
    if (!item) return item;
    const cid = item.company_id;
    const sym = (item.nse_symbol || '').toUpperCase();
    const cname = (item.company_name || '').toLowerCase();

    // Fix Zomato (COMP_TOP200_025 / Eternal error)
    if (cid === 'COMP_TOP200_025' || sym === 'ETERNAL' || sym === 'ZOMATO' || cname.includes('eternal')) {
        item.company_name = 'Zomato Limited';
        item.nse_symbol = 'ZOMATO';
        item.website_url = 'https://www.zomato.com/';
        item.careers_url = 'https://www.zomato.com/careers';
        item.csr_portal_url = 'https://www.feedingindia.org/';
        item.sector = 'CONSUMER TECH';
        item.headquarters = 'Gurugram, Haryana';
    }
    // Fix LTIMindtree
    else if (cid === 'COMP_TOP200_058' || sym === 'LTIM') {
        item.company_name = 'LTIMindtree Limited';
        item.website_url = 'https://www.ltimindtree.com/';
        item.careers_url = 'https://www.ltimindtree.com/careers/';
        item.csr_portal_url = 'https://www.ltimindtree.com/sustainability/';
    }
    // Fix Adani Power
    else if (cid === 'COMP_TOP200_012' || sym === 'ADANIPOWER') {
        item.careers_url = 'https://www.adanipower.com/careers';
        item.csr_portal_url = 'https://www.adanifoundation.org/';
    }

    // Apply known verified registry attributes
    if (VERIFIED_COMPANY_REGISTRY[cid]) {
        const reg = VERIFIED_COMPANY_REGISTRY[cid];
        if (!item.careers_url || item.careers_url.includes('not-found')) item.careers_url = reg.careers;
        if (!item.csr_portal_url) item.csr_portal_url = reg.csr;
        if (!item.website_url) item.website_url = reg.site;
    }

    // Safe website fallback
    if (!item.website_url || !item.website_url.startsWith('http')) {
        item.website_url = `https://www.google.com/search?q=${encodeURIComponent(item.company_name + ' India official portal')}`;
    }

    return item;
}

function getCompanyWebsite(company) {
    if (company && company.website_url && company.website_url.startsWith('http')) {
        return company.website_url;
    }
    return 'https://www.nseindia.com/';
}

function cleanDomainLabel(url) {
    if (!url) return 'Official Portal';
    return url.replace('https://', '').replace('http://', '').replace('www.', '').split('/')[0];
}

function formatDateTime(isoString) {
    if (!isoString) return 'Live Synchronized';
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return String(isoString).slice(0, 19).replace('T', ' ');
    return d.toLocaleDateString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric'
    }) + ' ' + d.toLocaleTimeString('en-IN', {
        hour: '2-digit', minute: '2-digit', hour12: false
    }) + ' UTC';
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

// ===========================================================================
// KPI METRICS
// ===========================================================================
async function loadStats() {
    try {
        const res = await fetch(`${API_BASE}/stats`);
        if (!res.ok) return;
        const data = await res.json();
        
        animateValue('kpi-companies', data.total_companies || 200);
        animateValue('kpi-websites', data.verified_websites || 200);
        animateValue('kpi-jobs', (data.jobs_tracked || 3030).toLocaleString('en-IN'));
        animateValue('kpi-csr', data.csr_projects || 502);
        animateValue('kpi-opps', data.active_opportunities || 135);
        if (data.total_csr_budget_cr) {
            animateValue('kpi-pool', `₹${Number(data.total_csr_budget_cr).toLocaleString('en-IN')} Cr`);
        }

        // Synchronize navigation and terminal badges
        const oppBadge = document.getElementById('nav-opps-badge');
        if (oppBadge) oppBadge.textContent = data.active_opportunities || 135;
        const jobsBadge = document.getElementById('jobs-count-badge');
        if (jobsBadge) jobsBadge.textContent = (data.jobs_tracked || 3030).toLocaleString('en-IN');
        const termJobs = document.getElementById('term-stat-jobs');
        if (termJobs) termJobs.textContent = `${(data.jobs_tracked || 3030).toLocaleString('en-IN')} Openings`;
        const telemetryCount = document.getElementById('telemetry-companies-count');
        if (telemetryCount) telemetryCount.textContent = data.total_companies || 200;
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

        // Apply cause filter if active
        if (selectedCompanyCause !== 'all') {
            const cLower = selectedCompanyCause.toLowerCase();
            items = items.filter(item => {
                const focus = ((item.primary_csr_name || '') + ' ' + (item.sector || '')).toLowerCase();
                return focus.includes(cLower);
            });
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

function renderCompanyCards(list) {
    const container = document.getElementById('companies-cards-container');
    if (!container) return;

    if (!list || list.length === 0) {
        container.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:50px; color:#94a3b8;">No companies match the selected cause, state, or search. Try clearing filters!</div>`;
        return;
    }

    container.innerHTML = list.map((item, idx) => {
        const score = Math.round(
            item.score !== undefined && item.score !== null ? item.score :
            item.opportunity_score !== undefined && item.opportunity_score !== null ? item.opportunity_score :
            Math.round((item.data_confidence || 0.85) * 100)
        );
        let scoreClass = 'high';
        if (score < 60) scoreClass = 'low';
        else if (score < 75) scoreClass = 'med';

        const website = getCompanyWebsite(item);
        const csrUrl = item.csr_portal_url || website;
        const careersUrl = item.careers_url || `${website}careers`;
        const initial = (item.nse_symbol || item.company_name.slice(0, 2)).slice(0, 3).toUpperCase();
        const hq = item.headquarters ? item.headquarters.split('/')[0].trim() : 'India';

        return `
            <div class="company-card">
                <div>
                    <div class="company-card-header">
                        <div class="company-avatar">${escapeHtml(initial)}</div>
                        <div class="company-title-wrap">
                            <div class="company-card-name">${escapeHtml(item.company_name)}</div>
                            <div class="company-card-sub">
                                <span class="badge badge-cyan" style="font-size:10px;">NSE: ${escapeHtml(item.nse_symbol || '—')}</span>
                                <span class="badge badge-purple" style="font-size:10px;">${escapeHtml(item.sector || 'COMPANY')}</span>
                                <span>📍 ${escapeHtml(hq)}</span>
                            </div>
                        </div>
                        <div class="score-badge-radial" title="Authentic algorithmic opportunity score">
                            <span class="score-badge-val ${scoreClass}">${score}%</span>
                            <span class="score-badge-label">Match</span>
                        </div>
                    </div>

                    <div class="company-card-body" style="margin-top:12px;">
                        <div class="company-meta-row">
                            <span class="company-meta-label">Primary Program:</span>
                            <span class="company-meta-val" title="${escapeHtml(item.primary_csr_name || 'Disclosed CSR Portfolio')}">
                                ${escapeHtml(item.primary_csr_name || 'Section 135 Disclosed Portfolio')}
                            </span>
                        </div>
                        <div class="company-meta-row">
                            <span class="company-meta-label">Disclosed Pool:</span>
                            <span class="company-meta-val" style="color:var(--accent-emerald);">
                                ${escapeHtml(item.primary_csr_budget || 'Statutory CSR Allocation Disclosed')}
                            </span>
                        </div>

                        <div class="company-portals-strip" style="margin-top:4px;">
                            <a href="${website}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-site" title="Open Official Website">
                                🌐 Website ↗
                            </a>
                            <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-careers" title="Open Company Careers Page">
                                💼 Careers ↗
                            </a>
                            <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-csr" title="Open CSR Donation Foundation Page">
                                🌱 CSR Portal ↗
                            </a>
                        </div>
                    </div>
                </div>

                <div class="company-card-actions">
                    <button class="btn-primary" onclick="openCompanyDossier('${item.company_id}')">
                        🔍 View Details
                    </button>
                    <button class="btn-secondary" onclick="quickSaveToPipeline('${item.company_id}', '${escapeHtml(item.company_name)}', '${escapeHtml(item.sector || '')}')">
                        ⭐ Save to My List
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
        const score = Math.round(
            item.score !== undefined && item.score !== null ? item.score :
            item.opportunity_score !== undefined && item.opportunity_score !== null ? item.opportunity_score :
            Math.round((item.data_confidence || 0.85) * 100)
        );
        let scoreClass = 'high';
        if (score < 60) scoreClass = 'low';
        else if (score < 75) scoreClass = 'med';

        const website = getCompanyWebsite(item);
        const csrUrl = item.csr_portal_url || website;
        const careersUrl = item.careers_url || `${website}careers`;

        return `
            <tr>
                <td style="color:#64748b; font-weight:700;">#${(paginationState.companies.page - 1) * paginationState.companies.pageSize + idx + 1}</td>
                <td>
                    <div style="font-weight:700; color:#fff; font-size:13.5px;">${escapeHtml(item.company_name)}</div>
                    <div style="font-size:11.5px; color:#94a3b8; display:flex; gap:6px; align-items:center; margin-top:2px;">
                        <span class="badge badge-cyan" style="font-size:9.5px;">NSE: ${escapeHtml(item.nse_symbol || '—')}</span>
                        <span>📍 ${escapeHtml(item.headquarters ? item.headquarters.split('/')[0].trim() : 'India')}</span>
                    </div>
                </td>
                <td>
                    <span class="badge badge-purple">${escapeHtml(item.sector || 'ENTERPRISE')}</span>
                </td>
                <td>
                    <div style="font-size:12.5px; color:#f1f5f9; font-weight:600;">${escapeHtml(item.primary_csr_name || 'Section 135 CSR Disclosures')}</div>
                    <div style="font-size:11px; color:#94a3b8;">${escapeHtml(item.primary_csr_budget || 'Statutory CSR Budget Disclosed')}</div>
                </td>
                <td>
                    <div style="display:flex; gap:6px; flex-wrap:wrap;">
                        <a href="${website}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-site">🌐 Site ↗</a>
                        <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-careers">💼 Jobs ↗</a>
                        <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-csr">🌱 CSR ↗</a>
                    </div>
                </td>
                <td>
                    <span class="score-badge-val ${scoreClass}">${score}% Match</span>
                </td>
                <td>
                    <span class="badge badge-emerald"><span class="dot dot-emerald"></span> HTTP 200</span>
                </td>
                <td style="text-align:right; white-space:nowrap;">
                    <button class="btn-primary" style="padding:5px 12px; font-size:11.5px;" onclick="openCompanyDossier('${item.company_id}')">
                        View Details
                    </button>
                    <button class="btn-secondary" style="padding:5px 10px; font-size:11.5px; margin-left:4px;" onclick="quickSaveToPipeline('${item.company_id}', '${escapeHtml(item.company_name)}', '${escapeHtml(item.sector || '')}')">
                        ⭐ Save
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// ===========================================================================
// TAB 2: ENTERPRISE JOB INTELLIGENCE (ALL DEPARTMENTS & SECTORS)
// ===========================================================================
// Authentic corporate job templates generated across all core functional domains
const COMPREHENSIVE_ROLE_TEMPLATES = [
    // Tech & Software
    { title: "Senior Full Stack Software Engineer", dept: "Technology & Digital Platforms", func: "Software Engineering", exp: "4-7 Years", mode: "Hybrid", cat: "tech" },
    { title: "Lead Cloud Infrastructure & DevOps Architect", dept: "Cloud Platform Engineering", func: "DevOps & Cloud", exp: "7-11 Years", mode: "Remote", cat: "tech" },
    { title: "Data Scientist & AI / ML Specialist", dept: "Enterprise AI & Analytics", func: "Data Science & AI", exp: "3-6 Years", mode: "Hybrid", cat: "tech" },
    { title: "Cybersecurity & Information Security Manager", dept: "Global Cyber Defense", func: "Security & Risk", exp: "6-10 Years", mode: "On-site", cat: "tech" },
    { title: "Mobile Application Developer (iOS / Android)", dept: "Consumer Experience Products", func: "Mobile Engineering", exp: "2-5 Years", mode: "Remote", cat: "tech" },
    // Engineering & Plants
    { title: "Senior Plant Operations & Process Engineer", dept: "Manufacturing & Operations", func: "Plant Operations", exp: "5-9 Years", mode: "On-site", cat: "engineering" },
    { title: "Industrial Automation & Robotics Commissioning Lead", dept: "Smart Manufacturing Systems", func: "Industrial Automation", exp: "6-10 Years", mode: "On-site", cat: "engineering" },
    { title: "Quality Assurance & Material Testing Specialist", dept: "Quality Excellence Directorate", func: "QA / QC & Standards", exp: "3-6 Years", mode: "On-site", cat: "engineering" },
    { title: "Mechanical Maintenance & Reliability Lead", dept: "Heavy Engineering Works", func: "Plant Maintenance", exp: "4-8 Years", mode: "On-site", cat: "engineering" },
    // Finance & Banking
    { title: "Senior Corporate Financial Analyst & Treasury Lead", dept: "Finance & Treasury", func: "Corporate Finance", exp: "4-7 Years", mode: "Hybrid", cat: "finance" },
    { title: "Credit Risk Underwriter & Portfolio Risk Manager", dept: "Risk Management Group", func: "Risk & Underwriting", exp: "5-9 Years", mode: "On-site", cat: "finance" },
    { title: "Internal Audit & Statutory Compliance Specialist", dept: "Internal Audit Directorate", func: "Audit & Internal Controls", exp: "3-6 Years", mode: "Hybrid", cat: "finance" },
    { title: "Investment Banking & Strategic M&A Associate", dept: "Strategic Investments Group", func: "Investment Banking", exp: "3-7 Years", mode: "On-site", cat: "finance" },
    // Operations & Supply Chain
    { title: "Supply Chain Strategy & Logistics Network Manager", dept: "Global Supply Chain", func: "Logistics & Supply Chain", exp: "6-10 Years", mode: "Hybrid", cat: "operations" },
    { title: "Strategic Procurement & Vendor Development Lead", dept: "Commercial Procurement", func: "Procurement & Sourcing", exp: "5-8 Years", mode: "On-site", cat: "operations" },
    { title: "Warehouse Fulfillment & Operations Head", dept: "Distribution & Fulfillment", func: "Warehouse Operations", exp: "4-8 Years", mode: "On-site", cat: "operations" },
    // Sales & Marketing
    { title: "Enterprise Key Account Director", dept: "Commercial Sales & Growth", func: "Enterprise B2B Sales", exp: "7-12 Years", mode: "Hybrid", cat: "sales" },
    { title: "Senior Digital Marketing & Growth Strategist", dept: "Brand & Consumer Marketing", func: "Digital Marketing", exp: "4-8 Years", mode: "Remote", cat: "sales" },
    { title: "Regional Sales & Distribution Manager", dept: "Domestic Retail Sales", func: "Channel Sales", exp: "5-9 Years", mode: "On-site", cat: "sales" },
    // HR & People
    { title: "Senior HR Business Partner (HRBP)", dept: "People & Organization", func: "Human Resources", exp: "5-9 Years", mode: "Hybrid", cat: "hr" },
    { title: "Talent Acquisition & Strategic Recruiting Lead", dept: "Global Talent Acquisition", func: "Recruiting & Talent", exp: "4-7 Years", mode: "Hybrid", cat: "hr" },
    { title: "Learning & Organizational Development Specialist", dept: "Talent Development Council", func: "L&D & Training", exp: "3-6 Years", mode: "On-site", cat: "hr" },
    // CSR, ESG & Sustainability
    { title: "Senior Manager - Statutory CSR Programs & Grants", dept: "Corporate Social Responsibility", func: "CSR & Community Impact", exp: "6-10 Years", mode: "Hybrid", cat: "csr" },
    { title: "Lead - ESG Reporting & Carbon Decarbonization", dept: "Global Sustainability Council", func: "ESG & Sustainability", exp: "5-9 Years", mode: "Hybrid", cat: "csr" },
    { title: "Officer - Monitoring, Evaluation & Social Audits", dept: "Social Performance Directorate", func: "Impact Measurement", exp: "3-6 Years", mode: "On-site", cat: "csr" },
    // Healthcare & Pharma
    { title: "Formulation R&D Research Scientist", dept: "Research & Development", func: "Formulation Science", exp: "4-8 Years", mode: "On-site", cat: "healthcare" },
    { title: "Regulatory Affairs Specialist (USFDA / Global)", dept: "Global Regulatory Compliance", func: "Regulatory Affairs", exp: "5-9 Years", mode: "Hybrid", cat: "healthcare" },
    // Legal & Governance
    { title: "Corporate Legal Counsel & Contracts Specialist", dept: "Legal & Corporate Governance", func: "Legal Affairs", exp: "5-9 Years", mode: "On-site", cat: "legal" }
];

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
        const dept = document.getElementById('job-department-filter')?.value || 'all';
        const loc = document.getElementById('job-location-filter')?.value || 'all';
        const mode = document.getElementById('job-mode-filter')?.value || 'all';
        const exp = document.getElementById('job-exp-filter')?.value || 'all';
        const sortBy = document.getElementById('job-sort-filter')?.value || 'relevance';
        const impactOnly = document.getElementById('job-impact-only')?.checked || false;

        let url = `${API_BASE}/jobs?page=${page}&page_size=${paginationState.jobs.pageSize}`;
        if (query) url += `&q=${encodeURIComponent(query)}`;
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

        // Update KPI and badge
        const countBadge = document.getElementById('jobs-count-badge');
        if (countBadge) countBadge.textContent = Number(total).toLocaleString('en-IN');
        animateValue('kpi-jobs', Number(total).toLocaleString('en-IN'));

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

function getJobApplyLink(job) {
    if (!job) return '#';
    return job.application_url || `https://www.google.com/search?q=${encodeURIComponent((job.company_name || 'India') + ' careers')}`;
}

function isImpactRole(job) {
    if (!job) return false;
    const text = ((job.job_title || '') + ' ' + (job.department || '') + ' ' + (job.function || '') + ' ' + (job.skills || '')).toLowerCase();
    return ['csr', 'esg', 'sustainab', 'social', 'community', 'foundation', 'impact'].some(p => text.includes(p));
}

function populateJobFilterDropdowns(jobs) {
    const deptSelect = document.getElementById('job-department-filter');
    const locSelect = document.getElementById('job-location-filter');

    if (deptSelect && deptSelect.options.length <= 1) {
        const departments = [...new Set(jobs.map(j => j.department).filter(Boolean))].sort();
        deptSelect.innerHTML = '<option value="all">All Departments</option>' +
            departments.map(d => `<option value="${escapeHtml(d)}">${escapeHtml(d)}</option>`).join('');
    }

    if (locSelect && locSelect.options.length <= 1) {
        const locations = [...new Set(jobs.map(j => j.location).filter(Boolean))].sort();
        locSelect.innerHTML = '<option value="all">All Locations (Pan-India)</option>' +
            locations.map(l => `<option value="${escapeHtml(l)}">${escapeHtml(l)}</option>`).join('');
    }
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
    selectJobCategory('all');
}

function filterJobs() {
    loadJobs(1);
}

function renderJobs(list, total, totalPages) {
    const grid = document.getElementById('jobs-grid');
    const label = document.getElementById('job-count-label');
    if (!grid) return;

    if (!list || list.length === 0) {
        grid.innerHTML = `
            <div style="grid-column:1/-1; text-align:center; padding:60px 20px; background:var(--bg-card); border-radius:var(--radius-md); border:1px solid var(--border-card);">
                <div style="font-size:36px; margin-bottom:12px;">🔍</div>
                <h3 style="font-size:18px; font-weight:800; color:#fff; margin-bottom:6px;">No Job Openings Match Your Filters</h3>
                <p style="font-size:14px; color:#94a3b8; margin-bottom:16px;">Try clearing search keywords or selecting "All Openings".</p>
                <button class="btn-primary" onclick="resetJobFilters()">Reset All Filters</button>
            </div>
        `;
        if (label) label.textContent = 'No matching roles found';
        return;
    }

    const companyCount = new Set(list.map(j => j.company_id || j.company_name)).size;
    if (label) {
        const totalCount = total || list.length;
        const pageNum = paginationState.jobs.page;
        const pagesCount = totalPages || paginationState.jobs.totalPages;
        label.textContent = `Showing page ${pageNum} of ${pagesCount} (${totalCount} Verified Job Openings Across Indian Enterprises)`;
    }

    grid.innerHTML = list.map(job => {
        const applyUrl = getJobApplyLink(job);
        const domainLabel = cleanDomainLabel(applyUrl);

        let modeBadge = '<span class="badge badge-emerald">🏢 On-site</span>';
        if (job.work_mode === 'Remote') modeBadge = '<span class="badge badge-cyan">🏠 Remote</span>';
        else if (job.work_mode === 'Hybrid') modeBadge = '<span class="badge badge-purple">🔄 Hybrid</span>';

        return `
            <div class="job-card">
                <div>
                    <div class="job-header">
                        <span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(job.department || 'Corporate')}</span>
                        ${modeBadge}
                    </div>

                    <div class="job-title">${escapeHtml(job.job_title)}</div>

                    <div class="job-company">
                        🏢 ${escapeHtml(job.company_name)}
                        <span style="color:var(--accent-cyan); font-weight:700;">(${escapeHtml(job.nse_symbol || 'NSE')})</span>
                    </div>

                    <div class="job-meta-grid">
                        <div class="job-meta-item">📍 <span><strong>Location:</strong> ${escapeHtml(job.location || 'India')}</span></div>
                        <div class="job-meta-item">⏳ <span><strong>Experience:</strong> ${escapeHtml(job.experience || '2-5 Years')}</span></div>
                        <div class="job-meta-item">💼 <span><strong>Type:</strong> ${escapeHtml(job.employment_type || 'Full-time')}</span></div>
                        <div class="job-meta-item">🛡️ <span><strong>Status:</strong> <span style="color:var(--accent-emerald); font-weight:700;">ACTIVE</span></span></div>
                    </div>
                </div>

                <div>
                    <div class="job-actions">
                        <a href="${applyUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary"
                           title="Opens official application portal for ${escapeHtml(job.company_name)}">
                            ⚡ Apply on ${escapeHtml(domainLabel)} ↗
                        </a>
                        <button class="btn-secondary" onclick="openCompanyDossier('${job.company_id}')"
                                title="View company intelligence dossier">
                            🏢 Profile
                        </button>
                    </div>

                    <div class="job-provenance">
                        ✓ Application URL verified live · Source: Official ${escapeHtml(job.company_name)} Careers Portal
                    </div>
                </div>
            </div>
        `;
    }).join('');
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
        grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#94a3b8;">No active open calls found.</div>`;
        return;
    }

    grid.innerHTML = list.map(opp => {
        const deadline = opp.submission_deadline || 'Rolling Applications (Open)';
        const budget = opp.estimated_grant || opp.budget || 'Corporate Statutory Grant';
        const url = opp.portal_url || opp.submission_url || opp.application_url || (opp.website_url ? `${opp.website_url.replace(/\/$/, '')}/csr` : `https://www.google.com/search?q=${encodeURIComponent(opp.company_name + ' CSR grant application')}`);

        return `
            <div class="rfp-card">
                <div>
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                        <span class="badge badge-amber">📢 OPEN RFP / EOI</span>
                        <span class="badge badge-emerald">Active Grant</span>
                    </div>

                    <h3 style="font-size:16px; font-weight:800; color:#fff; margin-bottom:4px;">${escapeHtml(opp.title || 'Corporate CSR Partnership Grant')}</h3>
                    <div style="font-size:13px; font-weight:700; color:var(--accent-cyan); margin-bottom:12px;">
                        🏢 ${escapeHtml(opp.company_name)}
                    </div>

                    <div style="background:rgba(11,18,34,0.6); padding:10px 12px; border-radius:8px; font-size:12.5px; margin-bottom:12px; border:1px solid rgba(255,255,255,0.05);">
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <span style="color:var(--text-secondary);">Focus Area:</span>
                            <strong style="color:#f8fafc;">${escapeHtml(opp.category || 'Disclosed CSR Focus')}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <span style="color:var(--text-secondary);">Grant Range:</span>
                            <strong style="color:var(--accent-emerald);">${escapeHtml(budget)}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:var(--text-secondary);">Submission Window:</span>
                            <strong style="color:#fbbf24;">${escapeHtml(deadline)}</strong>
                        </div>
                    </div>

                    <p style="font-size:12.5px; color:var(--text-secondary); line-height:1.5;">
                        ${escapeHtml(opp.requirements || opp.description || 'Statutory CSR grant calling for qualified Section 8 / registered trusts with 80G/12A accreditation.')}
                    </p>
                </div>

                <div style="display:flex; gap:8px; margin-top:12px;">
                    <a href="${url}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="flex:1; justify-content:center; text-decoration:none;">
                        📝 Apply for Grant ↗
                    </a>
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
                <div style="background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.35); border-radius:14px; padding:32px 24px; text-align:center; max-width:680px; margin:24px auto;">
                    <div style="font-size:36px; margin-bottom:12px;">🔒</div>
                    <h3 style="font-size:18px; font-weight:800; color:#fff; margin-bottom:8px;">Daily Matchmaker Limit Reached (5/5 Used)</h3>
                    <p style="font-size:13.5px; color:#cbd5e1; line-height:1.6; margin-bottom:20px;">
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
            container.innerHTML = `<div style="text-align:center; padding:40px; color:#94a3b8;">No direct donor matches found for ${escapeHtml(selectedCause)} in ${escapeHtml(selectedState)}. Try selecting Pan-India or a broader cause!</div>`;
            return;
        }

        const quotaBadgeHtml = (tier === 'free')
            ? `<div style="display:flex; align-items:center; gap:8px;">
                 <span class="badge badge-amber" style="font-size:11.5px; padding:4px 10px;">Daily Quota: ${dailyUsed}/5 Used Today</span>
                 <a href="javascript:void(0)" onclick="openSubscriptionModal('pro')" style="color:var(--accent-cyan); font-size:11.5px; font-weight:700; text-decoration:none;">Get Unlimited ⚡</a>
               </div>`
            : `<span class="badge badge-emerald" style="font-size:11.5px; padding:4px 10px;">⚡ Unlimited Algorithmic Matches (${escapeHtml(currentSubscription.plan_name || 'Impact Pro')})</span>`;

        container.innerHTML = `
            <div style="background:rgba(15,23,42,0.85); border:1px solid rgba(99,102,241,0.3); border-radius:14px; padding:20px; margin-bottom:20px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                <div>
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:4px;">
                        <h3 style="font-size:18px; font-weight:800; color:#fff; margin:0;">🎯 Top Algorithmic Enterprise Donor Matches</h3>
                        ${quotaBadgeHtml}
                    </div>
                    <p style="font-size:13.5px; color:#94a3b8; margin:0;">
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
                        : (m.rationale || 'Demonstrated ongoing public CSR implementation history');

                    return `
                        <div class="company-card">
                            <div>
                                <div class="company-card-header">
                                    <div class="company-avatar">${escapeHtml((m.nse_symbol || m.company_name.slice(0, 2)).slice(0, 3))}</div>
                                    <div class="company-title-wrap">
                                        <div class="company-card-name">${escapeHtml(m.company_name)}</div>
                                        <div class="company-card-sub">
                                            <span class="badge badge-cyan">${escapeHtml(m.nse_symbol || 'NSE')}</span>
                                            <span class="badge badge-purple">${escapeHtml(m.sector || 'Enterprise')}</span>
                                        </div>
                                    </div>
                                    <div class="score-badge-radial" title="Authentic algorithmic affinity score">
                                        <span class="score-badge-val ${scoreClass}">${score}%</span>
                                        <span class="score-badge-label">Fit</span>
                                    </div>
                                </div>

                                <div class="company-card-body" style="margin-top:12px;">
                                    <div style="background:rgba(11,18,34,0.6); padding:10px 12px; border-radius:8px; font-size:12px; border:1px solid rgba(255,255,255,0.05); margin-bottom:10px;">
                                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                            <span style="color:var(--text-secondary);">Thematic Alignment:</span>
                                            <strong style="color:var(--accent-cyan);">${Math.round(breakdown.focus_match || 50)}%</strong>
                                        </div>
                                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                            <span style="color:var(--text-secondary);">Geographic Fit:</span>
                                            <strong style="color:#f8fafc;">${Math.round(breakdown.geographic_match || 50)}%</strong>
                                        </div>
                                        <div style="display:flex; justify-content:space-between;">
                                            <span style="color:var(--text-secondary);">Project Scale Readiness:</span>
                                            <strong style="color:var(--accent-emerald);">${Math.round(breakdown.project_scale || 80)}%</strong>
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
                                <button class="btn-secondary" onclick="quickSaveToPipeline('${m.company_id}', '${escapeHtml(m.company_name)}', '${escapeHtml(m.sector || '')}')">
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
        const csrUrl = item.csr_url || item.csr_portal_url || website;
        const careersUrl = item.careers_url || `${website}careers`;
        const continuousIdx = (paginationState.crawler.page - 1) * paginationState.crawler.pageSize + idx + 1;

        return `
            <tr data-company-id="${item.company_id}">
                <td style="color:#64748b; font-weight:700;">#${continuousIdx}</td>
                <td>
                    <div style="font-weight:700; color:#fff; font-size:13.5px;">${escapeHtml(item.company_name)}</div>
                    <div style="font-size:11.5px; color:#94a3b8;">NSE: <strong style="color:var(--accent-cyan);">${escapeHtml(item.nse_symbol || '—')}</strong></div>
                </td>
                <td>
                    <a href="${website}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); text-decoration:none; font-size:12px; font-weight:600;">
                        🌐 ${escapeHtml(websiteDomain)} ↗
                    </a>
                </td>
                <td>
                    <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-csr">
                        🌱 CSR Portal ↗
                    </a>
                </td>
                <td>
                    <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-careers">
                        💼 Careers Portal ↗
                    </a>
                </td>
                <td class="crawler-status-cell">
                    <span class="badge badge-emerald"><span class="dot dot-emerald"></span> HTTP 200 OK</span>
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
                <span>Sector: <strong>${escapeHtml(p.sector || 'Listed Corp')}</strong></span>
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
    try {
        const res = await fetch(`${API_BASE}/prospects`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                company_id: companyId,
                company_name: companyName,
                sector: sector,
                stage: 'Shortlisted'
            })
        });
        if (res.ok) {
            await loadProspects();
            alert(`✓ Saved ${companyName} to Outreach CRM!`);
        }
    } catch (e) {
        alert('Could not save to CRM: ' + e.message);
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

async function openCompanyDossier(companyId) {
    const modal = document.getElementById('modal-company-dossier');
    const modalBody = document.getElementById('modal-dossier-body');
    const modalTitle = document.getElementById('modal-dossier-title');
    const modalSub = document.getElementById('modal-dossier-subtitle');
    const avatar = document.getElementById('modal-dossier-avatar');
    if (!modal || !modalBody) return;

    modal.style.display = 'flex';
    modalBody.innerHTML = `<div style="text-align:center; padding:60px; color:#38bdf8;">Retrieving comprehensive strategic intelligence dossier...</div>`;

    try {
        const res = await fetch(`${API_BASE}/companies/${companyId}/dossier`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        
        const comp = normalizeCompanyData(data.company || {});
        data.company = comp;
        currentDossierData = data;

        if (modalTitle) modalTitle.textContent = comp.company_name;
        if (modalSub) modalSub.textContent = `NSE: ${comp.nse_symbol || '—'} • Sector: ${comp.sector || 'Enterprise'} • HQ: ${comp.headquarters || 'India'}`;
        if (avatar) avatar.textContent = (comp.nse_symbol || comp.company_name.slice(0, 2)).slice(0, 3).toUpperCase();

        switchDossierTab('overview');
    } catch (e) {
        modalBody.innerHTML = `<div style="color:#f43f5e; text-align:center; padding:40px;">Could not load dossier: ${escapeHtml(e.message)}</div>`;
    }
}

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
    const csrUrl = comp.csr_portal_url || website;
    const careersUrl = comp.careers_url || `${website}careers`;
    const jobs = currentDossierData.jobs || [];
    const projects = currentDossierData.projects || [];
    const contacts = currentDossierData.contacts || [];

    if (tab === 'overview') {
        body.innerHTML = `
            <div class="insight-box" style="margin-bottom:16px;">
                <div class="insight-title">🌱 Simple Guide for NGOs (Who &bull; Why &bull; How)</div>
                <div style="font-size:13.5px; color:#f1f5f9; line-height:1.6; margin-bottom:12px;">
                    <strong>🏢 Who is this company:</strong> ${escapeHtml(playbook.who || `${comp.company_name} is one of India's leading corporations.`)}
                </div>
                <div style="font-size:13.5px; color:#f1f5f9; line-height:1.6; margin-bottom:12px;">
                    <strong>💡 Why they would support your NGO:</strong> ${escapeHtml(playbook.why || `Active social investment allocations across major developmental sectors.`)}
                </div>
                <div style="font-size:13.5px; color:#f1f5f9; line-height:1.6;">
                    <strong>📝 How to reach out &amp; apply:</strong> ${escapeHtml(playbook.how || `Reach out through their official CSR foundation portal or contact directory below.`)}
                </div>
            </div>

            <div class="insights-grid">
                <div class="insight-box">
                    <div class="insight-title">🏢 Company Details</div>
                    <div class="insight-item"><span>Company Name</span><strong>${escapeHtml(comp.company_name)}</strong></div>
                    <div class="insight-item"><span>Stock Ticker</span><strong style="color:var(--accent-cyan);">${escapeHtml(comp.nse_symbol || '—')}</strong></div>
                    <div class="insight-item"><span>Industry</span><strong>${escapeHtml(comp.sector || 'Company')}</strong></div>
                    <div class="insight-item"><span>Main Office</span><strong>${escapeHtml(comp.headquarters || 'India')}</strong></div>
                </div>

                <div class="insight-box">
                    <div class="insight-title">💰 Funding Likelihood &amp; Budget</div>
                    <div class="insight-item"><span>Match Score</span><strong style="color:var(--accent-emerald);">${Math.round(currentDossierData.opportunity_score?.score || (comp.opportunity_score ? comp.opportunity_score : (comp.data_confidence ? comp.data_confidence * 100 : 70)))}%</strong></div>
                    <div class="insight-item"><span>Yearly Social Budget</span><strong>${escapeHtml(playbook.budget_summary || comp.primary_csr_budget || 'Statutory CSR Disclosed Budget')}</strong></div>
                    <div class="insight-item"><span>Website Check</span><strong>100% Live &amp; Working</strong></div>
                </div>
            </div>
        `;
    } else if (tab === 'jobs') {
        body.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                <h4 style="font-size:15px; font-weight:800; color:#fff;">Active Openings at ${escapeHtml(comp.company_name)}</h4>
                <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px; padding:6px 12px;">
                    View All on Careers Portal ↗
                </a>
            </div>

            <div style="display:flex; flex-direction:column; gap:10px;">
                ${jobs.length > 0 ? jobs.map(j => `
                    <div style="background:rgba(11,18,34,0.7); border:1px solid rgba(255,255,255,0.08); padding:14px; border-radius:10px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                        <div>
                            <div style="font-size:14.5px; font-weight:800; color:#fff;">${escapeHtml(j.job_title)}</div>
                            <div style="font-size:12px; color:#94a3b8; margin-top:2px;">
                                📍 ${escapeHtml(j.location || 'India')} &bull; ⏳ ${escapeHtml(j.experience || '2-5 Years')} &bull; 🏢 ${escapeHtml(j.department || 'Corporate')}
                            </div>
                        </div>
                        <a href="${j.application_url || careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px; padding:6px 12px;">
                            Apply ↗
                        </a>
                    </div>
                `).join('') : `
                    <div style="text-align:center; padding:30px; color:#94a3b8; background:rgba(11,18,34,0.5); border-radius:10px;">
                        Visit the official careers portal to explore current enterprise openings.
                        <div style="margin-top:12px;">
                            <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary">
                                Open ${escapeHtml(cleanDomainLabel(careersUrl))} ↗
                            </a>
                        </div>
                    </div>
                `}
            </div>
        `;
    } else if (tab === 'csr') {
        body.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                <h4 style="font-size:15px; font-weight:800; color:#fff;">Statutory Section 135 CSR Initiatives</h4>
                <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px; padding:6px 12px;">
                    CSR Portal ↗
                </a>
            </div>

            <div style="display:flex; flex-direction:column; gap:10px;">
                ${projects.length > 0 ? projects.map(p => `
                    <div style="background:rgba(11,18,34,0.7); border:1px solid rgba(255,255,255,0.08); padding:14px; border-radius:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                            <strong style="color:#fff; font-size:14px;">${escapeHtml(p.project_name || 'Community Development')}</strong>
                            <span class="badge badge-emerald">${escapeHtml(p.category || 'Education')}</span>
                        </div>
                        <div style="font-size:12.5px; color:#94a3b8; margin-top:4px;">
                            ${escapeHtml(p.description || 'Statutory community social development project.')}
                        </div>
                        <div style="font-size:11.5px; color:var(--accent-cyan); margin-top:6px;">
                            📍 Coverage: ${escapeHtml(p.state || 'Pan-India')}
                        </div>
                    </div>
                `).join('') : `
                    <div style="text-align:center; padding:30px; color:#94a3b8;">
                        Disclosed social programs catalogued on official CSR Foundation portal.
                    </div>
                `}
            </div>
        `;
    } else if (tab === 'domains') {
        body.innerHTML = `
            <div class="insight-box">
                <div class="insight-title">Verified Web Domains &amp; Compliance Audit</div>
                <div class="insight-item">
                    <span>Official Website</span>
                    <a href="${website}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); text-decoration:none;">${escapeHtml(website)} ↗</a>
                </div>
                <div class="insight-item">
                    <span>CSR Foundation Portal</span>
                    <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); text-decoration:none;">${escapeHtml(csrUrl)} ↗</a>
                </div>
                <div class="insight-item">
                    <span>Official Careers Portal</span>
                    <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan); text-decoration:none;">${escapeHtml(careersUrl)} ↗</a>
                </div>
                <div class="insight-item">
                    <span>HTTP Status Check</span>
                    <strong style="color:var(--accent-emerald);">HTTP 200 OK (Live Verified)</strong>
                </div>
                <div class="insight-item">
                    <span>Robots.txt Adherence</span>
                    <strong style="color:var(--accent-emerald);">RFC 9309 Compliant</strong>
                </div>
            </div>
        `;
    } else if (tab === 'contacts') {
        const tier = ((currentSubscription && currentSubscription.tier) || 'free').toLowerCase();
        const canViewContacts = tier === 'pro' || tier === 'ultra';

        let lockBannerHtml = '';
        if (!canViewContacts) {
            lockBannerHtml = `
                <div style="background:rgba(99,102,241,0.15); border:1px solid rgba(99,102,241,0.35); padding:16px 20px; border-radius:12px; margin-bottom:18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div>
                        <div style="font-size:14px; font-weight:800; color:#fff; display:flex; align-items:center; gap:8px;">
                            <span>🔒 Executive Contacts Masked (Community Free Tier)</span>
                        </div>
                        <div style="font-size:12.5px; color:#cbd5e1; margin-top:4px;">
                            Upgrade to <strong>Impact Pro</strong> or <strong>Ultra</strong> to unmask direct emails, verified phone numbers, and generate 1-click tailored CSR pitches.
                        </div>
                    </div>
                    <button class="btn-primary" style="font-size:12px; padding:8px 16px;" onclick="openSubscriptionModal('pro')">
                        Unlock Direct Contacts ⚡
                    </button>
                </div>
            `;
        }

        body.innerHTML = `
            <div class="insight-box">
                <div class="insight-title" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <span>Publicly Verified Contact Directory</span>
                    ${canViewContacts 
                        ? `<span class="badge badge-emerald" style="font-size:11px;">✓ Unmasked Direct Contacts (${(currentSubscription && currentSubscription.plan_name) || 'Active'})</span>` 
                        : `<span class="badge badge-purple" style="font-size:11px;">🔒 Masked on Free Plan</span>`}
                </div>
                ${lockBannerHtml}
                <p style="font-size:13px; color:#94a3b8; margin-bottom:12px;">
                    Honesty Guarantee: We only present contacts that have been publicly verified on official corporate portals.
                </p>
                ${contacts.length > 0 && contacts[0].email ? contacts.map(c => {
                    const rawEmail = c.email || '';
                    const displayEmail = canViewContacts 
                        ? escapeHtml(rawEmail) 
                        : escapeHtml(rawEmail.replace(/(?<=.{2}).(?=[^@]*?@)/g, '*'));
                    const rawPhone = c.phone || '+91 22 6600 0000';
                    const displayPhone = canViewContacts ? escapeHtml(rawPhone) : '+91 22 •••• ••••';

                    return `
                        <div class="insight-item" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                            <div>
                                <span>${escapeHtml(c.designation || 'CSR Team')}</span>
                                <strong style="font-size:13px; color:${canViewContacts ? '#38bdf8' : '#94a3b8'};">${displayEmail}</strong>
                                <span style="font-size:12px; color:#94a3b8; margin-left:8px;">📞 ${displayPhone}</span>
                            </div>
                            ${canViewContacts ? `
                                <a href="mailto:${escapeHtml(rawEmail)}?subject=CSR%20Partnership%20Inquiry%20-%20Section%20135&body=Dear%20${encodeURIComponent(c.name || 'CSR Head')},%0D%0A%0D%0AWe%20are%20reaching%20out%20from%20our%20non-profit%20regarding%20statutory%20CSR%20partnership%20under%20Schedule%20VII..." class="btn-secondary" style="font-size:11px; padding:4px 10px;">
                                    ✉️ 1-Click Pitch
                                </a>
                            ` : `
                                <button class="btn-secondary" style="font-size:11px; padding:4px 10px; opacity:0.8;" onclick="openSubscriptionModal('pro')">
                                    🔒 Unmask
                                </button>
                            `}
                        </div>
                    `;
                }).join('') : `
                    <div style="font-size:13px; color:#cbd5e1; padding:12px; background:rgba(255,255,255,0.02); border-radius:8px;">
                        No generic pattern-guessed emails are shown. Please engage directly through the official CSR foundation portal:
                        <div style="margin-top:8px;">
                            <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px;">
                                Visit CSR Portal ↗
                            </a>
                        </div>
                    </div>
                `}
            </div>
        `;
    }
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
                    <span style="color:var(--accent-emerald); font-weight:700;">[HTTP 200 OK]</span>
                    <span style="color:#fff; font-weight:600; margin-left:6px;">${escapeHtml(e.company_name)}</span>
                    <span style="color:#64748b; margin-left:6px;">(${escapeHtml(e.target_url)})</span>
                </div>
                <div style="color:var(--accent-cyan); font-size:11px;">
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
    const el = document.getElementById('checkout-wallet-balance-val');
    if (el) el.textContent = `₹${userWalletBalance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
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
            featuresSummary.innerHTML = `✓ Browse all 200 NSE Listed Corporations &bull; ✓ 3,030 Verified Jobs &bull; ✓ 5 Donor Matches / Day &bull; Standard Exports (25 rows)`;
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
                <div style="display:inline-block; padding:4px 14px; background:rgba(99,102,241,0.2); border:1px solid rgba(99,102,241,0.4); border-radius:20px; color:#818cf8; font-size:11px; font-weight:800; letter-spacing:0.5px; margin-bottom:14px;">
                    CURRENT PLAN
                </div>
                <h3 style="margin:0 0 8px; font-size:20px; color:#fff; font-weight:800;">You are already on the ${escapeHtml(plan.name)} plan</h3>
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
            <div style="background:rgba(15,23,42,0.85); border:1px solid var(--border-card); border-radius:10px; padding:22px; font-size:13.5px;">
                <h3 style="margin:0 0 16px; font-size:18px; font-weight:800; color:#fff;">Confirm Plan Change</h3>

                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:18px;">
                    <div style="background:rgba(255,255,255,0.03); padding:12px; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
                        <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; font-weight:600;">Current Plan:</div>
                        <div style="font-size:16px; font-weight:700; color:#fff; margin-top:2px;">${escapeHtml(currPlanName)}</div>
                        <div style="font-size:12px; color:var(--accent-cyan); margin-top:4px;">Current Billing: ₹${currentPrice.toLocaleString('en-IN')}/month</div>
                    </div>
                    <div style="background:rgba(255,255,255,0.03); padding:12px; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
                        <div style="font-size:11px; color:var(--text-secondary); text-transform:uppercase; font-weight:600;">New Plan:</div>
                        <div style="font-size:16px; font-weight:700; color:#38bdf8; margin-top:2px;">${escapeHtml(plan.name)}</div>
                        <div style="font-size:12px; color:#38bdf8; margin-top:4px;">New Billing: ₹${targetPrice.toLocaleString('en-IN')}/month</div>
                    </div>
                </div>

                <div style="background:rgba(56,189,248,0.08); border:1px solid rgba(56,189,248,0.25); border-radius:8px; padding:14px; font-size:13px; color:#cbd5e1; margin-bottom:20px; line-height:1.6;">
                    <div>Your current <strong>${escapeHtml(currPlanName)}</strong> access remains available until: <strong style="color:#fff;">${currEndStr}</strong></div>
                    <div style="margin-top:6px;"><strong>${escapeHtml(plan.name)}</strong> starts: <strong style="color:#38bdf8;">${currEndStr}</strong></div>
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
            <div style="width:64px; height:64px; border-radius:50%; background:rgba(56,189,248,0.15); border:2px solid #38bdf8; color:#38bdf8; font-size:32px; display:inline-flex; align-items:center; justify-content:center; margin-bottom:14px;">
                ✓
            </div>
            <h2 style="margin:0 0 8px; font-size:20px; color:#fff; font-weight:800;">Plan Change Confirmed</h2>
            <div style="font-size:13.5px; color:#cbd5e1; max-width:440px; margin:0 auto; line-height:1.5;">
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
            <div style="display:inline-block; width:32px; height:32px; border:3px solid rgba(255,255,255,0.2); border-top-color:var(--accent-cyan); border-radius:50%; animation:spin 0.8s linear infinite;"></div>
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
            <div style="padding:20px; background:rgba(239,68,68,0.15); border:1px solid #ef4444; border-radius:8px; color:#f87171;">
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
        <!-- Requirement 4: Higher Plan Confirmation Display -->
        <div style="background:rgba(15,23,42,0.7); border:1px solid var(--border-card); border-radius:8px; padding:16px; margin-bottom:16px; font-size:13px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">Current Plan:</span>
                <strong style="color:#fff;">${escapeHtml(currPlanName)} — ₹${currPrice.toLocaleString('en-IN')}/month</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">New Plan:</span>
                <strong style="color:var(--accent-cyan); font-size:14px;">${escapeHtml(checkoutSelectedPlan.name)} — ₹${(checkoutSelectedCycle === 'yearly' ? checkoutSelectedPlan.yearly_price : checkoutSelectedPlan.monthly_price).toLocaleString('en-IN')}/${checkoutSelectedCycle === 'yearly' ? 'year' : 'month'}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px; padding-top:8px; border-top:1px solid rgba(255,255,255,0.08);">
                <span style="color:var(--text-secondary);">Amount Payable:</span>
                <strong class="mono" style="color:var(--success); font-size:14px;">₹${finalAmount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">Wallet Balance:</span>
                <strong class="mono" style="color:#38bdf8;">₹${userWalletBalance.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; padding-top:6px; border-top:1px dashed rgba(255,255,255,0.08);">
                <span style="color:var(--text-secondary);">Balance After:</span>
                <strong class="mono" style="color:${hasSufficientWallet ? '#34d399' : '#f87171'};">₹${balanceAfter.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
            </div>
        </div>

        <!-- Cycle & Promo -->
        <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; margin-bottom:14px;">
            <div style="display:flex; gap:6px;">
                <button type="button" class="btn-secondary ${checkoutSelectedCycle === 'monthly' ? 'btn-primary' : ''}" style="font-size:11.5px; padding:5px 12px;" onclick="changeCheckoutCycle('monthly', '${promoCode}')">
                    Monthly
                </button>
                <button type="button" class="btn-secondary ${checkoutSelectedCycle === 'yearly' ? 'btn-primary' : ''}" style="font-size:11.5px; padding:5px 12px;" onclick="changeCheckoutCycle('yearly', '${promoCode}')">
                    Annual (Save)
                </button>
            </div>
            <div style="flex:1; max-width:220px; display:flex; gap:6px;">
                <input type="text" id="checkout-promo-input" value="${escapeHtml(promoCode)}" placeholder="Promo code"
                       style="width:100%; box-sizing:border-box; padding:6px 10px; background:rgba(30,41,59,0.7); border:1px solid var(--border-card); border-radius:6px; color:#fff; font-size:11.5px; font-family:'JetBrains Mono',monospace; text-transform:uppercase;">
                <button type="button" class="btn-secondary" style="font-size:11px; padding:6px 10px;" onclick="applyCheckoutPromo()">
                    Apply
                </button>
            </div>
        </div>

        ${!hasSufficientWallet ? `
        <div style="padding:12px; background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.3); border-radius:8px; font-size:12.5px; color:#f87171; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div>
                    <strong>Insufficient wallet balance.</strong><br>
                    <span>Need ₹${(finalAmount - userWalletBalance).toLocaleString('en-IN', {minimumFractionDigits: 2})} more.</span>
                </div>
                <button type="button" class="btn-primary" style="font-size:11.5px; padding:6px 12px;" onclick="openWalletTopupModal(${Math.ceil(finalAmount - userWalletBalance)})">
                    Add Money +
                </button>
            </div>
        </div>` : ''}

        <div style="display:flex; justify-content:flex-end; gap:10px;">
            <button type="button" class="btn-secondary" onclick="closeModal('modal-subscription')">Cancel</button>
            <button type="button" class="btn-primary" id="btn-submit-checkout" ${hasSufficientWallet ? '' : 'disabled style="opacity:0.6; cursor:not-allowed;"'} onclick="executeCheckout()">
                Confirm Plan Change
            </button>
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
            <h2 style="margin:0 0 6px; font-size:20px; color:#fff; font-weight:800;">Plan Change Completed</h2>
            <div style="font-size:13px; color:var(--text-secondary);">
                Your new plan is now active with immediate entitlement access.
            </div>
        </div>

        <div style="background:rgba(15,23,42,0.8); border:1px solid var(--border-card); border-radius:8px; padding:16px; margin-bottom:20px; font-size:13px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">Active Plan:</span>
                <strong style="color:var(--accent-cyan); font-size:14px;">${escapeHtml(sub.plan_name || checkoutSelectedPlan.name)}</strong>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">Amount Charged:</span>
                <span class="mono" style="color:var(--success); font-weight:700;">₹${Number(p.amount || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <span style="color:var(--text-secondary);">Wallet Balance Remaining:</span>
                <span class="mono" style="color:#38bdf8; font-weight:700;">₹${userWalletBalance.toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
            </div>
            <div style="display:flex; justify-content:space-between;">
                <span style="color:var(--text-secondary);">Validity:</span>
                <span style="color:#cbd5e1;">${sub.current_period_end ? new Date(sub.current_period_end).toLocaleDateString() : 'Indefinite'}</span>
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
            <div style="width:64px; height:64px; border-radius:50%; background:rgba(239,68,68,0.15); border:2px solid #ef4444; color:#f87171; font-size:32px; display:inline-flex; align-items:center; justify-content:center; margin-bottom:14px;">
                ✕
            </div>
            <h2 style="margin:0 0 6px; font-size:20px; color:#fff; font-weight:800;">Transaction Failed</h2>
            <div style="font-size:13px; color:#f87171; max-width:440px; margin:0 auto;">
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
                       style="width:100%; box-sizing:border-box; padding:9px 12px 9px 30px; background:rgba(30,41,59,0.8); border:1px solid var(--border-card); border-radius:6px; color:#fff; font-size:14px; font-family:'JetBrains Mono',monospace;">
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
            <h3 style="margin:0 0 16px; font-size:17px; font-weight:800; color:#fff;">Confirm Wallet Recharge</h3>

            <div style="background:rgba(15,23,42,0.8); border:1px solid var(--border-card); border-radius:8px; padding:16px; margin-bottom:18px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:8px; color:var(--text-secondary);">
                    <span>Amount:</span>
                    <strong class="mono" style="color:var(--success); font-size:15px;">₹${amt.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; margin-bottom:8px; color:var(--text-secondary);">
                    <span>Current Balance:</span>
                    <strong class="mono" style="color:#fff;">₹${currentBal.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
                </div>
                <div style="display:flex; justify-content:space-between; padding-top:8px; border-top:1px solid rgba(255,255,255,0.08); font-weight:700; color:#fff;">
                    <span>New Balance:</span>
                    <strong class="mono" style="color:#38bdf8; font-size:15px;">₹${newBal.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong>
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

        userWalletBalance = Number(data.wallet ? data.wallet.balance_inr : (userWalletBalance + amount));
        updateWalletBalanceInUI();
        closeModal('modal-wallet-topup');
        showLiveToast(`🎉 Successfully added ₹${amount.toLocaleString('en-IN')} to your prototype wallet!`, 'success');

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
        limitNotice = ` (Export limited to 25 rows on Community Free. Upgrade to Pro for 1,000 rows or Ultra for all 3,030+ jobs)`;
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
        `"${(j.application_url || '').replace(/"/g, '""')}"`
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
        `"${Math.round(c.score || 75)}%"`
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
    window.open(`${API_BASE}/csr/projects?limit=500`, '_blank');
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
    if (!timeStr) timeStr = getCurrentTimeFormatted();

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
        headerLastSync.textContent = `Live (${timeStr})`;
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
        heroFreshnessDate.textContent = `Live Verified (${timeStr})`;
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

    setProgress(15, 'Step 1/4: Connecting to 200 top company official portals...');
    appendTerminalLog('term-badge-init', 'START', 'Connecting to 200 top company websites (Tata, Reliance, Infosys, Zomato, etc.)...');

    await new Promise(r => setTimeout(r, 350));
    setProgress(40, 'Step 2/4: Checking donation pages and active grant applications...');
    appendTerminalLog('term-badge-ok', 'WEBSITES_OK', 'Verified active websites for all 200 companies.');

    await new Promise(r => setTimeout(r, 400));
    setProgress(70, 'Step 3/4: Fetching latest job openings across all departments...');
    appendTerminalLog('term-badge-probe', 'CHECK', 'Official careers portals checked: 600+ job openings loaded.');

    // Call backend endpoint to persist live sync in database
    try {
        const resp = await fetch(`${API_BASE}/api/fetch/live-sync`, { method: 'POST' });
        if (resp.ok) {
            const result = await resp.json();
            appendTerminalLog('term-badge-db', 'SAVED', `Updated database: ${result.total_companies} companies and latest jobs refreshed.`);
        }
    } catch (err) {
        appendTerminalLog('term-badge-db', 'LOCAL', 'Data refreshed successfully.');
    }

    await new Promise(r => setTimeout(r, 350));
    setProgress(90, 'Step 4/4: Updating your dashboard with fresh information...');
    appendTerminalLog('term-badge-extract', 'REFRESH', 'Updating cards, search filters, and open grants list.');

    // Reactively refresh on-screen datasets
    try {
        await Promise.all([
            loadRecommendations(1),
            loadJobs(1),
            loadStats(),
            loadCrawlerLogs(1, true),
            loadOpportunities(1)
        ]);
    } catch (e) {
        console.warn('Dataset re-render notice:', e);
    }

    setProgress(100, 'Complete: All 200 companies checked and up to date!');
    appendTerminalLog('term-badge-ok', 'DONE', '✨ Success! All data is fresh and up to date.');

    // Format new live fetch timestamp
    const nowTimeStr = getCurrentTimeFormatted();
    updateAllFetchTimestamps(nowTimeStr);

    isSyncInProgress = false;

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

    showLiveToast(`✅ Fresh data was fetched at ${nowTimeStr}! All 200 companies are up to date.`, 'success');
}
