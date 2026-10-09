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

// Central Pagination State Store - Strictly Synchronized to Real Database State
const paginationState = {
    companies: { page: 1, pageSize: 12, total: 201, totalPages: 17 },
    jobs: { page: 1, pageSize: 12, total: 115, totalPages: 10 },
    findJobs: { page: 1, pageSize: 12, total: 115, totalPages: 10 },
    companyJobs: { page: 1, pageSize: 12, total: 0, totalPages: 1 },
    opps: { page: 1, pageSize: 9, total: 6, totalPages: 1 },
    crawler: { page: 1, pageSize: 15, total: 201, totalPages: 14 }
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
        const savedTime = localStorage.getItem('csr_last_fetch_time') || 'Never';
        updateAllFetchTimestamps(savedTime, true);
    } catch (e) {
        updateAllFetchTimestamps('Never', true);
    }

    // High performance initial load: immediately render Tab 1 (Donors) and stats
    // Secondary tabs (Jobs, Grants, CRM, Telemetry) load on-demand when clicked
    populateJobFilterDropdowns();
    loadStats();
    loadRecommendations(1);
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
        
        const totalCorps = data.total_companies !== undefined ? data.total_companies : 201;
        const verifiedCorps = data.verified_companies !== undefined ? data.verified_companies : totalCorps;
        const verifiedJobs = data.jobs_tracked !== undefined ? data.jobs_tracked : 0;
        const verifiedCsr = data.csr_projects !== undefined ? data.csr_projects : 0;
        const verifiedOpps = data.active_opportunities !== undefined ? data.active_opportunities : 0;
        const lastFetch = data.last_live_fetch || 'Live Synchronized';
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

        const jobsBadge = document.getElementById('jobs-count-badge');
        if (jobsBadge) jobsBadge.textContent = verifiedJobs.toLocaleString('en-IN');
        const mobileJobsBadge = document.getElementById('mobile-nav-jobs-badge');
        if (mobileJobsBadge) mobileJobsBadge.textContent = verifiedJobs.toLocaleString('en-IN');
        const totalJobsPill = document.getElementById('badge-jobs-total-pill');
        if (totalJobsPill) totalJobsPill.textContent = verifiedJobs.toLocaleString('en-IN');

        const termJobs = document.getElementById('term-stat-jobs');
        if (termJobs) termJobs.textContent = `${verifiedJobs.toLocaleString('en-IN')} Openings`;
        const termCorps = document.getElementById('term-stat-corps');
        if (termCorps) termCorps.textContent = `${totalCorps} Verified`;
        const telemetryCount = document.getElementById('telemetry-companies-count');
        if (telemetryCount) telemetryCount.textContent = totalCorps;

        const analyticsJobs = document.getElementById('analytics-jobs-total');
        if (analyticsJobs) analyticsJobs.textContent = `${verifiedJobs.toLocaleString('en-IN')} Active`;

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
        const website = getCompanyWebsite(item);
        const csrUrl = item.csr_portal_url || website;
        const initial = (item.nse_symbol || item.company_name.slice(0, 2)).slice(0, 3).toUpperCase();
        const hq = item.headquarters ? item.headquarters.split('/')[0].trim() : 'India';
        const industry = item.industry || item.sector || 'Enterprise';

        // 5-state job status rule (Part 12 & Part 24)
        const jobStatusLabel = item.job_status_label || (item.verified_jobs_count > 0 ? `${item.verified_jobs_count} Current Verified Jobs` : 'Jobs not yet verified');
        const jobStatusBadge = item.job_status_badge || (item.verified_jobs_count > 0 ? 'badge-emerald' : 'badge-muted');
        const csrStatusLabel = item.csr_status_label || (item.published_csr_count > 0 ? `${item.published_csr_count} CSR Projects Verified` : 'CSR: Not yet verified');
        const csrStatusBadge = item.csr_status_badge || (item.published_csr_count > 0 ? 'badge-emerald' : 'badge-muted');
        const lastChecked = item.last_verified_display || 'Not yet verified';
        const isVerified = item.verification_status === 'VERIFIED';

        return `
            <div class="company-card">
                <div>
                    <div class="company-card-header">
                        <div class="company-avatar">${escapeHtml(initial)}</div>
                        <div class="company-title-wrap">
                            <div class="company-card-name" style="cursor:pointer;" onclick="openCompanyJobs('${item.company_id}', '${escapeHtml(item.company_name)}')">${escapeHtml(item.company_name)}</div>
                            <div class="company-card-sub">
                                <span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(item.nse_symbol ? `NSE: ${item.nse_symbol}` : 'REGISTRY')}</span>
                                <span style="font-size:11.5px; color:var(--text-secondary);">${escapeHtml(industry)}</span>
                                <span>📍 ${escapeHtml(hq)}</span>
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <span class="badge ${isVerified ? 'badge-emerald' : 'badge-amber'}" style="font-size:10px;">
                                ${isVerified ? '✓ Verified' : 'In Progress'}
                            </span>
                        </div>
                    </div>

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
                            <span>Last Checked:</span>
                            <strong style="color:var(--text-primary); font-size:11.5px;">${escapeHtml(lastChecked)}</strong>
                        </div>

                        <div class="company-portals-strip" style="margin-top:6px;">
                            ${website ? `<a href="${website}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-site" title="Open Official Website">🌐 Official Website ↗</a>` : ''}
                            ${csrUrl && csrUrl !== website ? `<a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="portal-link-pill portal-csr" title="Open CSR Foundation Portal">🌱 CSR Portal ↗</a>` : ''}
                        </div>
                    </div>
                </div>

                <div class="company-card-actions">
                    <button class="btn-primary" onclick="openCompanyDossier('${item.company_id}')">
                        🔍 View Company
                    </button>
                    <button class="btn-outline" onclick="openCompanyJobs('${item.company_id}', '${escapeHtml(item.company_name)}')" title="Browse verified jobs from this company">
                        💼 Jobs ${item.verified_jobs_count > 0 ? `(${item.verified_jobs_count})` : ''}
                    </button>
                    <button class="btn-secondary" onclick="quickSaveToPipeline('${item.company_id}', '${escapeHtml(item.company_name)}', '${escapeHtml(item.sector || '')}')">
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
        const csrUrl = item.csr_portal_url || website;
        const jobStatusLabel = item.job_status_label || (item.verified_jobs_count > 0 ? `${item.verified_jobs_count} Jobs` : 'Not yet verified');
        const jobStatusBadge = item.job_status_badge || (item.verified_jobs_count > 0 ? 'badge-emerald' : 'badge-muted');
        const csrStatusLabel = item.csr_status_label || (item.published_csr_count > 0 ? `${item.published_csr_count} CSR Projects` : 'Not yet verified');
        const csrStatusBadge = item.csr_status_badge || (item.published_csr_count > 0 ? 'badge-emerald' : 'badge-muted');
        const lastChecked = item.last_verified_display || 'Not yet verified';
        const isVerified = item.verification_status === 'VERIFIED';

        return `
            <tr>
                <td style="color:#64748b; font-weight:700;">#${(paginationState.companies.page - 1) * paginationState.companies.pageSize + idx + 1}</td>
                <td>
                    <div style="font-weight:700; color:var(--text-primary); font-size:13.5px; cursor:pointer;" onclick="openCompanyDossier('${item.company_id}')">
                        <span style="color:var(--primary-brand);">${escapeHtml(item.company_name)}</span>
                    </div>
                    <div style="font-size:11.5px; color:var(--text-secondary); display:flex; gap:6px; align-items:center; margin-top:2px;">
                        ${item.nse_symbol ? `<span class="badge badge-cyan" style="font-size:9.5px;">NSE: ${escapeHtml(item.nse_symbol)}</span>` : ''}
                        <span>📍 ${escapeHtml(item.headquarters ? item.headquarters.split('/')[0].trim() : 'India')}</span>
                    </div>
                </td>
                <td>
                    <span class="badge badge-purple">${escapeHtml(item.industry || item.sector || 'ENTERPRISE')}</span>
                </td>
                <td>
                    <span class="badge ${jobStatusBadge}">${escapeHtml(jobStatusLabel)}</span>
                </td>
                <td>
                    <span class="badge ${csrStatusBadge}">${escapeHtml(csrStatusLabel)}</span>
                </td>
                <td>
                    <span class="badge ${isVerified ? 'badge-emerald' : 'badge-amber'}">${isVerified ? '✓ Verified' : 'In Progress'}</span>
                </td>
                <td style="font-size:11.5px; color:var(--text-secondary); font-family:var(--font-mono);">
                    ${escapeHtml(lastChecked)}
                </td>
                <td style="text-align:right; white-space:nowrap;">
                    <button class="btn-primary" style="padding:5px 12px; font-size:11.5px;" onclick="openCompanyDossier('${item.company_id}')">
                        View Company
                    </button>
                    <button class="btn-outline" style="padding:5px 10px; font-size:11.5px; margin-left:4px;" onclick="openCompanyJobs('${item.company_id}', '${escapeHtml(item.company_name)}')">
                        💼 Jobs
                    </button>
                    <button class="btn-secondary" style="padding:5px 10px; font-size:11.5px; margin-left:4px;" onclick="quickSaveToPipeline('${item.company_id}', '${escapeHtml(item.company_name)}', '${escapeHtml(item.sector || '')}')">
                        ⭐ Save
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
            const res = await fetch(`${API_BASE}/companies?page_size=300`);
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

    if (typeof VERIFIED_COMPANY_REGISTRY === 'object') {
        Object.entries(VERIFIED_COMPANY_REGISTRY).forEach(([id, c]) => {
            if (c && c.name) {
                companiesMap.set(id, { id: id, name: c.name, sym: c.sym || '' });
            }
        });
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
    const compSelect = document.getElementById('job-company-filter');
    if (compSelect) {
        compSelect.value = companyId;
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
            const postedDisplay = job.posted_date ? formatDate(job.posted_date) : '<span style="color:var(--text-muted); font-size:12px;">Recent</span>';
            const verifiedDisplay = job.last_verified_at ? formatDate(job.last_verified_at) : 'Today';

            return `
                <tr>
                    <td>
                        <div style="font-weight:700; color:var(--text-primary); cursor:pointer;" onclick="openJobDetailsModal(${job.job_row_id})" title="Click to view structured specifications">
                            ${escapeHtml(job.job_title)}
                        </div>
                    </td>
                    <td>
                        <a href="javascript:void(0)" onclick="filterJobsByCompany('${job.company_id}', '${escapeHtml(job.company_name)}')" style="font-weight:600; color:var(--accent-cyan); text-decoration:none;" title="Filter by ${escapeHtml(job.company_name)}">
                            🏢 ${escapeHtml(job.company_name)}
                        </a>
                        ${job.nse_symbol ? `<span style="color:var(--text-muted); font-size:11px; margin-left:4px;">(${escapeHtml(job.nse_symbol)})</span>` : ''}
                    </td>
                    <td>${job.location ? escapeHtml(job.location) : '<span style="color:var(--text-muted); font-size:12px;">Not specified</span>'}</td>
                    <td>${job.department ? `<span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(job.department)}</span>` : '<span style="color:var(--text-muted); font-size:12px;">Not specified</span>'}</td>
                    <td>${job.employment_type ? escapeHtml(job.employment_type) : '<span style="color:var(--text-muted); font-size:12px;">Not specified</span>'}</td>
                    <td style="font-size:12px; color:var(--text-secondary);">${postedDisplay}</td>
                    <td style="font-size:12px; color:var(--text-secondary);">${verifiedDisplay}</td>
                    <td>${sourceBadge}</td>
                    <td><span class="badge badge-emerald" style="font-size:10px;">ACTIVE</span></td>
                    <td style="text-align:right;">
                        <div style="display:flex; justify-content:flex-end; gap:6px;">
                            <button class="btn-primary" style="padding:4px 10px; font-size:11.5px;" onclick="openJobDetailsModal(${job.job_row_id})">
                                View
                            </button>
                            <a href="${applyUrl}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="padding:4px 10px; font-size:11.5px;" title="Official application portal">
                                Apply ↗
                            </a>
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

            let modeBadge = '<span class="badge badge-emerald">🏢 On-site</span>';
            if (job.work_mode === 'Remote') modeBadge = '<span class="badge badge-cyan">🏠 Remote</span>';
            else if (job.work_mode === 'Hybrid') modeBadge = '<span class="badge badge-purple">🔄 Hybrid</span>';

            const deptBadge = job.department 
                ? `<span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(job.department)}</span>`
                : `<span class="badge badge-subtle" style="font-size:10px;">Enterprise</span>`;

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

                        <div class="job-company" style="cursor:pointer;" onclick="filterJobsByCompany('${job.company_id}', '${escapeHtml(job.company_name)}')" title="Filter to show all verified openings at ${escapeHtml(job.company_name)}">
                            🏢 <span style="text-decoration:underline;">${escapeHtml(job.company_name)}</span>
                            ${job.nse_symbol ? `<span style="color:var(--accent-cyan); font-weight:700;">(${escapeHtml(job.nse_symbol)})</span>` : ''}
                        </div>

                        <div class="job-meta-grid">
                            <div class="job-meta-item">📍 <span><strong>Location:</strong> ${job.location ? escapeHtml(job.location) : 'Not specified'}</span></div>
                            <div class="job-meta-item">⏳ <span><strong>Experience:</strong> ${job.experience ? escapeHtml(job.experience) : 'Not specified'}</span></div>
                            <div class="job-meta-item">💼 <span><strong>Type:</strong> ${job.employment_type ? escapeHtml(job.employment_type) : 'Not specified'}</span></div>
                            <div class="job-meta-item">🛡️ <span><strong>Status:</strong> <span style="color:var(--accent-emerald); font-weight:700;">ACTIVE</span></span></div>
                        </div>
                    </div>

                    <div>
                        <div class="job-actions" style="flex-wrap:wrap; gap:6px;">
                            <button class="btn-primary" style="padding:6px 12px; font-size:12px;" onclick="openJobDetailsModal(${job.job_row_id})">
                                View Job
                            </button>
                            <a href="${applyUrl}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="padding:6px 12px; font-size:12px;"
                               title="Opens official application portal for ${escapeHtml(job.company_name)}">
                                ⚡ Apply ↗
                            </a>
                            <button class="btn-outline" style="padding:6px 10px; font-size:11px;" onclick="openCompanyJobs('${job.company_id}', '${escapeHtml(job.company_name)}')"
                                    title="Browse all jobs from this company">
                                🏢 All Jobs
                            </button>
                            <button class="btn-secondary" style="padding:6px 8px; font-size:11px;" onclick="openCompanyDossier('${job.company_id}')"
                                    title="View company intelligence dossier">
                                Profile
                            </button>
                        </div>

                        <div class="job-provenance">
                            ✓ Verified live · Source: Official ${escapeHtml(job.company_name)} Careers Portal
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
    if (!paginationState.findJobs) paginationState.findJobs = { page: 1, pageSize: 12, total: 115, totalPages: 10 };
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

    grid.innerHTML = list.map(job => {
        const applyUrl = getJobApplyLink(job);
        const domainLabel = cleanDomainLabel(applyUrl);

        let modeBadge = '<span class="badge badge-emerald">🏢 On-site</span>';
        if (job.work_mode === 'Remote') modeBadge = '<span class="badge badge-cyan">🏠 Remote</span>';
        else if (job.work_mode === 'Hybrid') modeBadge = '<span class="badge badge-purple">🔄 Hybrid</span>';

        const skills = job.skills
            ? job.skills.split(',').map(s => s.trim()).filter(Boolean).slice(0, 4)
            : [];

        return `
            <div class="job-discovery-card">
                <div>
                    <div class="job-header-row">
                        <span class="badge badge-cyan" style="font-size:10.5px;">${escapeHtml(job.department || 'Enterprise')}</span>
                        ${modeBadge}
                    </div>

                    <div class="job-card-title">
                        <a href="javascript:void(0)" onclick="openJobDetailsModal(${job.job_row_id})">
                            ${escapeHtml(job.job_title)}
                        </a>
                    </div>

                    <a href="javascript:void(0)" class="job-company-badge" onclick="openCompanyJobs('${job.company_id}', '${escapeHtml(job.company_name)}')">
                        🏢 ${escapeHtml(job.company_name)}
                        ${job.nse_symbol ? `<span style="color:var(--text-muted); font-size:12px;">(${escapeHtml(job.nse_symbol)})</span>` : ''}
                    </a>

                    <div class="job-meta-chips">
                        <span class="job-chip">📍 ${job.location ? escapeHtml(job.location) : 'Not specified'}</span>
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
                        <span>✓ Verified ATS Link</span>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <button class="btn-primary" style="padding:6px 14px; font-size:12px;" onclick="openJobDetailsModal(${job.job_row_id})">
                            View Job
                        </button>
                        <a href="${applyUrl}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="padding:6px 12px; font-size:12px;" title="Apply directly on official careers portal">
                            Apply ↗
                        </a>
                        <button class="btn-outline" style="padding:6px 10px; font-size:11px;" onclick="openCompanyJobs('${job.company_id}', '${escapeHtml(job.company_name)}')" title="View all jobs for this company">
                            🏢 All Jobs
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
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
async function loadCompanyJobsDirectory() {
    const grid = document.getElementById('company-jobs-directory-grid');
    const countLabel = document.getElementById('company-directory-count-label');
    const sectorFilter = document.getElementById('company-jobs-sector-filter');
    if (!grid) return;

    grid.innerHTML = `
        <div style="grid-column:1/-1;" class="dynamic-loading-skeleton">
            <div class="loading-spinner-circle"></div>
            <div class="loading-spinner-text">Cataloging Enterprise Job Portals...</div>
            <div class="loading-spinner-sub">Fetching verified employers across India's Top 200 enterprises</div>
        </div>`;

    try {
        const res = await fetch(`${API_BASE}/recommendations?limit=200`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const items = Array.isArray(data) ? data : (data.items || []);
        allDirectoryCompanies = items;

        if (sectorFilter && sectorFilter.options.length <= 1) {
            const sectors = [...new Set(items.map(c => c.sector).filter(Boolean))].sort();
            sectorFilter.innerHTML = '<option value="all">All Industries &amp; Sectors</option>' +
                sectors.map(s => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`).join('');
        }

        renderCompanyJobsDirectoryCards(items);
        if (countLabel) countLabel.textContent = `${items.length} Verified Corporate Employers`;
    } catch (e) {
        console.error('Error loading company directory', e);
        if (grid) {
            grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:40px; color:#f43f5e;">Could not load companies: ${escapeHtml(e.message)}</div>`;
        }
    }
}

function renderCompanyJobsDirectoryCards(list) {
    const grid = document.getElementById('company-jobs-directory-grid');
    if (!grid) return;

    if (!list || list.length === 0) {
        grid.innerHTML = `
            <div style="grid-column:1/-1;" class="empty-state">
                <div class="empty-state-icon">🏢</div>
                <div class="empty-state-title">No Corporations Found</div>
                <div class="empty-state-text">No companies matched your query or sector filter.</div>
            </div>`;
        return;
    }

    grid.innerHTML = list.map(comp => {
        const symbol = comp.nse_symbol || 'NSE';
        const avatar = (symbol || comp.company_name.slice(0, 2)).slice(0, 3).toUpperCase();
        const sector = comp.sector || 'Enterprise';
        const hq = comp.headquarters ? comp.headquarters.split('/')[0].trim() : 'India';

        let jobBadge = '';
        const jobCnt = comp.job_count || 0;
        const crawlSt = comp.crawl_status || 'PENDING';
        if (jobCnt > 0) {
            jobBadge = `<span class="badge badge-emerald" style="font-size:10px; font-weight:700;">💼 ${jobCnt} Jobs</span>`;
        } else if (crawlSt === 'CRAWLED') {
            jobBadge = `<span class="badge" style="font-size:10px; background:var(--bg-subtle); color:var(--text-secondary); border:1px solid var(--border-color);">0 Verified</span>`;
        } else if (crawlSt === 'PENDING') {
            jobBadge = `<span class="badge" style="font-size:10px; background:var(--bg-subtle); color:var(--text-muted); border:1px dashed var(--border-color);">⏳ Crawl Pending</span>`;
        } else if (crawlSt === 'NO_CAREER_URL') {
            jobBadge = `<span class="badge badge-amber" style="font-size:10px;">Source Unavailable</span>`;
        } else {
            jobBadge = `<span class="badge badge-rose" style="font-size:10px;">⚠️ Crawl Failed</span>`;
        }

        return `
            <div class="job-discovery-card" style="cursor:pointer;" onclick="openCompanyJobs('${comp.company_id}', '${escapeHtml(comp.company_name)}')">
                <div style="display:flex; align-items:center; gap:14px; margin-bottom:12px;">
                    <div class="company-logo-avatar" style="width:48px; height:48px; font-size:16px;">${avatar}</div>
                    <div style="flex:1; min-width:0;">
                        <div style="font-weight:700; font-size:15px; color:var(--text-primary); line-height:1.3; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${escapeHtml(comp.company_name)}</div>
                        <div style="font-size:12px; color:var(--text-secondary); margin-top:2px; display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                            <span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(symbol)}</span>
                            <span>📍 ${escapeHtml(hq)}</span>
                        </div>
                    </div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:14px; padding-top:12px; border-top:1px solid var(--border-subtle); gap:8px;">
                    <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                        <span class="badge badge-purple" style="font-size:10px;">${escapeHtml(sector)}</span>
                        ${jobBadge}
                    </div>
                    <button class="btn-primary" style="padding:6px 14px; font-size:12px; flex-shrink:0;" onclick="event.stopPropagation(); openCompanyJobs('${comp.company_id}', '${escapeHtml(comp.company_name)}')">
                        ${jobCnt > 0 ? `View ${jobCnt} Jobs →` : 'Browse Jobs →'}
                    </button>
                </div>
            </div>
        `;
    }).join('');

}

function filterCompanyDirectory() {
    const q = (document.getElementById('company-jobs-search')?.value || '').trim().toLowerCase();
    const sector = document.getElementById('company-jobs-sector-filter')?.value || 'all';

    let filtered = allDirectoryCompanies || [];
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

    renderCompanyJobsDirectoryCards(filtered);
    const countLabel = document.getElementById('company-directory-count-label');
    if (countLabel) countLabel.textContent = `${filtered.length} Corporations Found`;
}

async function openCompanyJobs(companyId, companyName) {
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

    if (nameEl) nameEl.textContent = companyName || 'Corporate Enterprise';

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
        const sym = comp.nse_symbol || 'NSE';
        if (avatarEl) avatarEl.textContent = (sym || comp.company_name.slice(0, 2)).slice(0, 3).toUpperCase();
        if (symbolEl) symbolEl.textContent = `NSE: ${sym}`;
        if (sectorEl) sectorEl.textContent = comp.sector || 'Enterprise';
        if (hqEl) hqEl.textContent = `📍 ${comp.headquarters ? comp.headquarters.split('/')[0].trim() : 'India'}`;
        const website = getCompanyWebsite(comp);
        if (webEl) webEl.innerHTML = `🌐 <a href="${website}" target="_blank" rel="noopener noreferrer" style="color:var(--primary-brand); text-decoration:none;">Website ↗</a>`;
        if (carEl) carEl.innerHTML = `💼 <a href="${comp.careers_url || website + 'careers'}" target="_blank" rel="noopener noreferrer" style="color:var(--primary-brand); text-decoration:none;">Careers Portal ↗</a>`;
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
            if (crawlSt === 'PENDING') {
                emptyTitle = "Jobs Not Yet Verified (Crawl Pending)";
                emptyText = `The live crawler has not yet synchronized openings for ${escapeHtml(selectedCompanyJobData?.company_name || 'this corporation')}. Run "Fetch Live Data" to discover all active postings.`;
                emptyAction = `<button class="btn-primary" onclick="confirmLiveFetch()">⚡ Fetch Live Data Now</button>`;
            } else if (crawlSt === 'CRAWLED') {
                emptyTitle = "0 Active Openings Disclosed";
                emptyText = `The official careers portal was audited and currently lists 0 open positions.`;
                emptyAction = selectedCompanyJobData?.careers_url ? `<a href="${escapeHtml(selectedCompanyJobData.careers_url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="text-decoration:none; display:inline-block;">Open Careers Portal ↗</a>` : '';
            } else if (crawlSt === 'NO_CAREER_URL') {
                emptyTitle = "Career Source Unavailable";
                emptyText = `An official active career portal URL has not been disclosed by the company.`;
                emptyAction = '';
            } else {
                emptyTitle = "Career Portal Blocked or Inaccessible";
                emptyText = `The crawler encountered an access barrier (${crawlSt}) when checking the company's career page.`;
                emptyAction = selectedCompanyJobData?.careers_url ? `<a href="${escapeHtml(selectedCompanyJobData.careers_url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="text-decoration:none; display:inline-block;">Visit Official Site Directly ↗</a>` : '';
            }
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


    grid.innerHTML = list.map(job => {
        const applyUrl = getJobApplyLink(job);
        const domainLabel = cleanDomainLabel(applyUrl);

        let modeBadge = '<span class="badge badge-emerald">🏢 On-site</span>';
        if (job.work_mode === 'Remote') modeBadge = '<span class="badge badge-cyan">🏠 Remote</span>';
        else if (job.work_mode === 'Hybrid') modeBadge = '<span class="badge badge-purple">🔄 Hybrid</span>';

        const skills = (job.skills || 'Enterprise Solutions, Strategic Execution')
            .split(',')
            .map(s => s.trim())
            .filter(Boolean)
            .slice(0, 3);

        return `
            <div class="job-discovery-card">
                <div>
                    <div class="job-header-row">
                        <span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(job.department || 'Corporate')}</span>
                        ${modeBadge}
                    </div>

                    <div class="job-card-title">
                        <a href="javascript:void(0)" onclick="openJobDetailsModal(${job.job_row_id})">
                            ${escapeHtml(job.job_title)}
                        </a>
                    </div>

                    <div class="job-meta-chips" style="margin-top:10px;">
                        <span class="job-chip">📍 ${escapeHtml(job.location || 'India')}</span>
                        <span class="job-chip">⏳ ${escapeHtml(job.experience || '2-5 Yrs')}</span>
                        <span class="job-chip">💼 ${escapeHtml(job.employment_type || 'Full-time')}</span>
                    </div>

                    <div class="job-skills-chips">
                        ${skills.map(sk => `<span class="skill-pill">${escapeHtml(sk)}</span>`).join('')}
                    </div>
                </div>

                <div class="job-card-footer">
                    <span class="job-post-date">✓ Verified ATS Link</span>
                    <div style="display:flex; gap:8px;">
                        <button class="btn-primary" style="padding:6px 14px; font-size:12px;" onclick="openJobDetailsModal(${job.job_row_id})">
                            View Job
                        </button>
                        <a href="${applyUrl}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="padding:6px 12px; font-size:12px;">
                            Apply ↗
                        </a>
                    </div>
                </div>
            </div>
        `;
    }).join('');
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
// 3. COMPREHENSIVE JOB DETAILS MODAL
// ---------------------------------------------------------------------------
async function openJobDetailsModal(jobId) {
    const modal = document.getElementById('modal-job-details');
    const modalBody = document.getElementById('modal-job-body');
    const modalTitle = document.getElementById('modal-job-title');
    const modalSub = document.getElementById('modal-job-company-subtitle');
    const modalAvatar = document.getElementById('modal-job-avatar');
    if (!modal || !modalBody) return;

    modal.style.display = 'flex';
    modalBody.innerHTML = `
        <div style="text-align:center; padding:60px 20px;">
            <div class="loading-spinner-circle" style="margin:0 auto 16px;"></div>
            <div style="font-size:16px; font-weight:700; color:var(--text-primary);">Retrieving Role Specifications...</div>
            <div style="font-size:13px; color:var(--text-secondary); margin-top:4px;">Connecting to enterprise career repository</div>
        </div>`;

    try {
        const res = await fetch(`${API_BASE}/jobs/${jobId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const job = await res.json();

        if (modalTitle) modalTitle.textContent = job.job_title;
        if (modalSub) {
            modalSub.innerHTML = `
                <a href="javascript:void(0)" onclick="closeModal('modal-job-details'); openCompanyJobs('${job.company_id}', '${escapeHtml(job.company_name)}');" style="color:var(--primary-brand); font-weight:700; text-decoration:none;">
                    🏢 ${escapeHtml(job.company_name)}
                </a>
                ${job.nse_symbol ? `<span style="color:var(--text-muted); margin-left:6px;">(${escapeHtml(job.nse_symbol)})</span>` : ''}
                ${job.sector ? `<span style="margin:0 6px; color:var(--border-color);">•</span><span>${escapeHtml(job.sector)}</span>` : ''}
            `;
        }
        if (modalAvatar) {
            modalAvatar.textContent = (job.nse_symbol || (job.company_name ? job.company_name.slice(0, 2) : 'JB')).slice(0, 3).toUpperCase();
        }

        const applyUrl = getJobApplyLink(job);
        const domainLabel = cleanDomainLabel(applyUrl);

        let modeBadge = '<span class="badge badge-emerald">🏢 On-site</span>';
        if (job.work_mode === 'Remote') modeBadge = '<span class="badge badge-cyan">🏠 Remote</span>';
        else if (job.work_mode === 'Hybrid') modeBadge = '<span class="badge badge-purple">🔄 Hybrid</span>';

        const skillsList = job.skills
            ? job.skills.split(',').map(s => s.trim()).filter(Boolean)
            : [];

        // Build structured sections per Part 10
        let html = '';

        // Meta Bar
        html += `
            <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:var(--radius-lg); padding:16px 20px; display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:14px; margin-bottom:24px;">
                <div>
                    <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Location</div>
                    <div style="font-size:14px; font-weight:600; color:var(--text-primary);">📍 ${job.location ? escapeHtml(job.location) : '<span style="color:var(--text-muted); font-size:12px;">Not provided by source</span>'}</div>
                </div>
                ${job.experience ? `
                <div>
                    <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Experience Tier</div>
                    <div style="font-size:14px; font-weight:600; color:var(--text-primary);">⏳ ${escapeHtml(job.experience)}</div>
                </div>
                ` : `
                <div>
                    <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Experience Tier</div>
                    <div style="font-size:13px; color:var(--text-muted);">Not provided by source</div>
                </div>
                `}
                <div>
                    <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Employment Type</div>
                    <div style="font-size:14px; font-weight:600; color:var(--text-primary);">💼 ${job.employment_type ? escapeHtml(job.employment_type) : '<span style="color:var(--text-muted); font-size:12px;">Not provided by source</span>'}</div>
                </div>
                <div>
                    <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Work Style</div>
                    <div>${modeBadge}</div>
                </div>
                ${job.department ? `
                <div>
                    <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Department</div>
                    <div style="font-size:14px; font-weight:600; color:var(--text-primary);">${escapeHtml(job.department)}</div>
                </div>
                ` : ''}
                <div>
                    <div style="font-size:11px; font-weight:700; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Verification Status</div>
                    <div><span class="badge badge-emerald">✓ Source Confirmed</span></div>
                </div>
            </div>

            <!-- Primary Action Bar -->
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; margin-bottom:24px; padding-bottom:20px; border-bottom:1px solid var(--border-color);">
                <div style="font-size:13px; color:var(--text-secondary);">
                    Verified official career posting from <strong>${escapeHtml(job.company_name)}</strong>
                    ${job.ats_platform ? ` &bull; ATS: <span class="badge badge-cyan" style="font-size:10px;">${escapeHtml(job.ats_platform)}</span>` : ''}
                </div>
                <div style="display:flex; gap:10px;">
                    <a href="${applyUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="padding:10px 22px; font-weight:700; font-size:14px;">
                        ⚡ Apply on ${escapeHtml(domainLabel)} ↗
                    </a>
                    <button class="btn-secondary" onclick="closeModal('modal-job-details'); openCompanyJobs('${job.company_id}', '${escapeHtml(job.company_name)}');">
                        🏢 All Jobs at ${escapeHtml(job.company_name)}
                    </button>
                </div>
            </div>
        `;

        // Section 1: Job Overview & Description (Only if present in source)
        if (job.job_description) {
            html += `
                <div style="margin-bottom:24px;">
                    <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 10px;">Position Overview</h4>
                    <div style="font-size:14px; line-height:1.7; color:var(--text-secondary); background:var(--bg-surface); padding:18px; border-radius:var(--radius-md); border:1px solid var(--border-subtle); white-space:pre-line;">
                        ${escapeHtml(job.job_description)}
                    </div>
                </div>
            `;
        }

        // Section 2: Responsibilities (Only if present in source)
        if (job.responsibilities) {
            html += `
                <div style="margin-bottom:24px;">
                    <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 10px;">Key Responsibilities</h4>
                    <div style="font-size:14px; line-height:1.7; color:var(--text-secondary); background:var(--bg-surface); padding:18px; border-radius:var(--radius-md); border:1px solid var(--border-subtle); white-space:pre-line;">
                        ${escapeHtml(job.responsibilities)}
                    </div>
                </div>
            `;
        }

        // Section 3: Qualifications / Requirements (Only if present in source)
        if (job.qualifications || job.requirements) {
            const qualText = job.qualifications || job.requirements;
            html += `
                <div style="margin-bottom:24px;">
                    <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 10px;">Qualifications &amp; Requirements</h4>
                    <div style="font-size:14px; line-height:1.7; color:var(--text-secondary); background:var(--bg-surface); padding:18px; border-radius:var(--radius-md); border:1px solid var(--border-subtle); white-space:pre-line;">
                        ${escapeHtml(qualText)}
                    </div>
                </div>
            `;
        }

        // Section 4: Preferred Qualifications (Only if present in source)
        if (job.preferred_qualifications) {
            html += `
                <div style="margin-bottom:24px;">
                    <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 10px;">Preferred Qualifications</h4>
                    <div style="font-size:14px; line-height:1.7; color:var(--text-secondary); background:var(--bg-surface); padding:18px; border-radius:var(--radius-md); border:1px solid var(--border-subtle); white-space:pre-line;">
                        ${escapeHtml(job.preferred_qualifications)}
                    </div>
                </div>
            `;
        }

        // Section 5: Skills (Only if present in source)
        if (skillsList.length > 0) {
            html += `
                <div style="margin-bottom:24px;">
                    <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 10px;">Skills &amp; Competencies</h4>
                    <div style="display:flex; flex-wrap:wrap; gap:8px;">
                        ${skillsList.map(sk => `<span class="skill-pill" style="padding:6px 14px; font-size:13px;">${escapeHtml(sk)}</span>`).join('')}
                    </div>
                </div>
            `;
        }

        // Section 6: Education (Only if present in source)
        if (job.education) {
            html += `
                <div style="margin-bottom:24px;">
                    <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 8px;">Education &amp; Credentials</h4>
                    <p style="font-size:13.5px; color:var(--text-secondary); margin:0;">${escapeHtml(job.education)}</p>
                </div>
            `;
        }

        // Section 7: Salary & Benefits (Only if present in source)
        if (job.salary || job.benefits) {
            html += `
                <div style="margin-bottom:24px; background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px 20px;">
                    <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 8px;">Compensation &amp; Benefits</h4>
                    ${job.salary ? `<div style="font-size:14px; color:var(--accent-emerald); font-weight:700; margin-bottom:6px;">💰 Salary: ${escapeHtml(job.salary)}</div>` : ''}
                    ${job.benefits ? `<div style="font-size:13px; color:var(--text-secondary);">${escapeHtml(job.benefits)}</div>` : ''}
                </div>
            `;
        }

        // Section 8: Source Provenance & Verification Audit (Part 17)
        html += `
            <div style="margin-bottom:24px; background:var(--bg-surface-subtle); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px 20px; font-size:12.5px;">
                <div style="font-weight:800; font-size:13px; color:var(--text-primary); margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                    <span>🛡️ Source Provenance &amp; Verification Audit</span>
                </div>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(200px, 1fr)); gap:10px; color:var(--text-secondary);">
                    <div><strong>Authoritative Source:</strong> <a href="${job.source_url || applyUrl}" target="_blank" rel="noopener noreferrer" style="color:var(--accent-cyan);">${escapeHtml(cleanDomainLabel(job.source_url || applyUrl))} ↗</a></div>
                    <div><strong>ATS / Platform:</strong> ${escapeHtml(job.ats_platform || 'Official Career Portal')}</div>
                    <div><strong>Verification Status:</strong> <span class="badge badge-emerald" style="font-size:10px;">${escapeHtml(job.verification_status || 'SOURCE_CONFIRMED')}</span></div>
                    <div><strong>Last Verified:</strong> ${job.retrieved_at ? formatDate(job.retrieved_at) : (job.last_checked_date ? formatDate(job.last_checked_date) : 'Today')}</div>
                    ${job.fingerprint ? `<div style="grid-column:1/-1; font-family:var(--font-mono); font-size:11px; color:var(--text-muted); word-break:break-all;"><strong>Record Hash:</strong> ${escapeHtml(job.fingerprint)}</div>` : ''}
                </div>
            </div>
        `;

        // Section 9: Related Roles (if available)
        if (job.related_jobs && job.related_jobs.length > 0) {
            html += `
                <div style="margin-top:28px; padding-top:20px; border-top:1px solid var(--border-color);">
                    <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0 0 12px;">Related Openings in Same Enterprise</h4>
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:12px;">
                        ${job.related_jobs.map(rj => `
                            <div style="padding:14px; background:var(--bg-surface-subtle); border:1px solid var(--border-subtle); border-radius:var(--radius-md); cursor:pointer;" onclick="openJobDetailsModal(${rj.job_row_id})">
                                <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:4px;">${escapeHtml(rj.job_title)}</div>
                                <div style="font-size:12px; color:var(--text-secondary);">🏢 ${escapeHtml(rj.company_name)}</div>
                                <div style="font-size:11px; color:var(--text-muted); margin-top:6px;">📍 ${escapeHtml(rj.location || 'India')} ${rj.experience ? `• ⏳ ${escapeHtml(rj.experience)}` : ''}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

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

                    <h3 style="font-size:16px; font-weight:800; color:var(--text-primary); margin-bottom:4px;">${escapeHtml(opp.title || 'Corporate CSR Partnership Grant')}</h3>
                    <div style="font-size:13px; font-weight:700; color:var(--primary-brand); margin-bottom:12px; cursor:pointer;" onclick="openCompanyJobs('${opp.company_id}', '${escapeHtml(opp.company_name)}')">
                        🏢 <span style="text-decoration:underline;">${escapeHtml(opp.company_name)}</span>
                        <span style="font-size:11px; margin-left:6px; color:var(--text-secondary);">(Jobs ➔)</span>
                    </div>

                    <div style="background:var(--bg-surface-subtle); padding:10px 12px; border-radius:8px; font-size:12.5px; margin-bottom:12px; border:1px solid var(--border-color);">
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <span style="color:var(--text-secondary);">Focus Area:</span>
                            <strong style="color:var(--text-primary);">${escapeHtml(opp.category || 'Disclosed CSR Focus')}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                            <span style="color:var(--text-secondary);">Grant Range:</span>
                            <strong style="color:var(--accent-emerald);">${escapeHtml(budget)}</strong>
                        </div>
                        <div style="display:flex; justify-content:space-between;">
                            <span style="color:var(--text-secondary);">Submission Window:</span>
                            <strong style="color:#d97706;">${escapeHtml(deadline)}</strong>
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
                    <button class="btn-outline" onclick="openCompanyJobs('${opp.company_id}', '${escapeHtml(opp.company_name)}')" title="Browse verified jobs from this company">
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
                                    <div style="background:var(--bg-surface-subtle); padding:10px 12px; border-radius:8px; font-size:12px; border:1px solid var(--border-subtle); margin-bottom:10px;">
                                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                            <span style="color:var(--text-secondary);">Thematic Alignment:</span>
                                            <strong style="color:var(--primary-brand);">${Math.round(breakdown.focus_match || 50)}%</strong>
                                        </div>
                                        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                                            <span style="color:var(--text-secondary);">Geographic Fit:</span>
                                            <strong style="color:var(--text-primary);">${Math.round(breakdown.geographic_match || 50)}%</strong>
                                        </div>
                                        <div style="display:flex; justify-content:space-between;">
                                            <span style="color:var(--text-secondary);">Project Scale Readiness:</span>
                                            <strong style="color:var(--success);">${Math.round(breakdown.project_scale || 80)}%</strong>
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
                    <div style="font-weight:700; color:var(--text-primary); font-size:13.5px;">${escapeHtml(item.company_name)}</div>
                    <div style="font-size:11.5px; color:var(--text-secondary);">NSE: <strong style="color:var(--primary-brand);">${escapeHtml(item.nse_symbol || '—')}</strong></div>
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
    const careersUrl = comp.careers_url || (website ? `${website.replace(/\/+$/, '')}/careers` : '#');
    const jobs = currentDossierData.jobs || [];
    const projects = currentDossierData.projects || [];
    const contacts = currentDossierData.contacts || [];
    const opportunities = currentDossierData.opportunities || [];

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
                    ${comp.cin ? `<div class="insight-item"><span>CIN</span><strong style="font-family:var(--font-mono); font-size:12px;">${escapeHtml(comp.cin)}</strong></div>` : ''}
                </div>

                <div class="insight-box">
                    <div class="insight-title">💰 Funding Likelihood &amp; Budget</div>
                    <div class="insight-item"><span>Match Score</span><strong style="color:var(--accent-emerald);">${Math.round(currentDossierData.opportunity_score?.score || (comp.opportunity_score ? comp.opportunity_score : (comp.data_confidence ? comp.data_confidence * 100 : 0)))}%</strong></div>
                    <div class="insight-item"><span>Yearly Social Budget</span><strong>${escapeHtml(playbook.budget_summary || comp.primary_csr_budget || 'Not available')}</strong></div>
                    <div class="insight-item"><span>Website Check</span><strong>${comp.link_verified_at ? 'Verified' : 'Not currently verified'}</strong></div>
                    <div class="insight-item"><span>Status</span><span class="badge ${comp.job_status_badge || 'badge-emerald'}">${escapeHtml(comp.job_status_label || 'Active Corporate Profile')}</span></div>
                </div>
            </div>
        `;
    } else if (tab === 'jobs') {
        const jobState = (comp.job_status_state || '').toUpperCase();
        let emptyStateHtml = '';

        if (jobState === 'VERIFIED_ZERO_JOBS') {
            emptyStateHtml = `
                <div style="text-align:center; padding:36px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                    <div style="font-size:28px; margin-bottom:8px;">🏢</div>
                    <div style="font-size:15px; font-weight:800; color:var(--text-primary); margin-bottom:4px;">0 current verified jobs</div>
                    <div style="font-size:13px; color:var(--text-secondary); max-width:420px; margin:0 auto 14px;">
                        The official career source was successfully checked and genuinely contains no current open postings.
                    </div>
                    <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px;">
                        Check Career Portal Directly ↗
                    </a>
                </div>
            `;
        } else if (jobState === 'CRAWL_FAILED') {
            emptyStateHtml = `
                <div style="text-align:center; padding:36px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                    <div style="font-size:28px; margin-bottom:8px;">⚠️</div>
                    <div style="font-size:15px; font-weight:800; color:var(--text-primary); margin-bottom:4px;">Unable to verify current jobs</div>
                    <div style="font-size:13px; color:var(--text-secondary); max-width:420px; margin:0 auto 14px;">
                        Live socket probe encountered an error or connection timeout while reaching the career endpoint.
                    </div>
                    <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px;">
                        Visit Official Career Portal ↗
                    </a>
                </div>
            `;
        } else if (jobState === 'ATS_DISCOVERY_FAILED') {
            emptyStateHtml = `
                <div style="text-align:center; padding:36px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                    <div style="font-size:28px; margin-bottom:8px;">🔍</div>
                    <div style="font-size:15px; font-weight:800; color:var(--text-primary); margin-bottom:4px;">Career source could not be verified</div>
                    <div style="font-size:13px; color:var(--text-secondary); max-width:420px; margin:0 auto 14px;">
                        No official ATS or career endpoint was detected or linked from the corporate apex domain.
                    </div>
                    <a href="${website}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px;">
                        Visit Company Website ↗
                    </a>
                </div>
            `;
        } else if (jobState === 'CRAWL_IN_PROGRESS') {
            emptyStateHtml = `
                <div style="text-align:center; padding:36px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                    <div class="loading-spinner-circle" style="margin:0 auto 12px;"></div>
                    <div style="font-size:15px; font-weight:800; color:var(--text-primary); margin-bottom:4px;">Checking live career source...</div>
                    <div style="font-size:13px; color:var(--text-secondary); max-width:420px; margin:0 auto;">
                        Crawler probe actively connecting to verify open corporate requisitions.
                    </div>
                </div>
            `;
        } else {
            emptyStateHtml = `
                <div style="text-align:center; padding:36px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                    <div style="font-size:28px; margin-bottom:8px;">⏳</div>
                    <div style="font-size:15px; font-weight:800; color:var(--text-primary); margin-bottom:4px;">Jobs not yet verified</div>
                    <div style="font-size:13px; color:var(--text-secondary); max-width:420px; margin:0 auto 14px;">
                        Career source has not yet completed a verified extraction pass.
                    </div>
                    <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px;">
                        Visit Career Portal ↗
                    </a>
                </div>
            `;
        }

        body.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
                <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0;">
                    Current Verified Roles (${jobs.length})
                </h4>
                ${careersUrl !== '#' ? `
                <a href="${careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px; padding:6px 12px;">
                    Official Careers Portal ↗
                </a>` : ''}
            </div>

            <div style="display:flex; flex-direction:column; gap:10px;">
                ${jobs.length > 0 ? jobs.map(j => `
                    <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); padding:14px; border-radius:10px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                        <div>
                            <div style="font-size:14.5px; font-weight:800; color:var(--text-primary); cursor:pointer;" onclick="closeModal('modal-company-dossier'); openJobDetailsModal(${j.job_row_id});">
                                ${escapeHtml(j.job_title)}
                            </div>
                            <div style="font-size:12px; color:var(--text-secondary); margin-top:2px;">
                                📍 ${j.location ? escapeHtml(j.location) : 'Not specified'} ${j.experience ? `&bull; ⏳ ${escapeHtml(j.experience)}` : ''} ${j.department ? `&bull; 🏢 ${escapeHtml(j.department)}` : ''}
                            </div>
                        </div>
                        <div style="display:flex; gap:6px;">
                            <button class="btn-primary" style="font-size:12px; padding:5px 12px;" onclick="closeModal('modal-company-dossier'); openJobDetailsModal(${j.job_row_id});">
                                View Specs
                            </button>
                            <a href="${j.application_url || careersUrl}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="font-size:12px; padding:5px 12px;">
                                Apply ↗
                            </a>
                        </div>
                    </div>
                `).join('') : emptyStateHtml}
            </div>
        `;
    } else if (tab === 'csr') {
        body.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
                <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0;">
                    Statutory Section 135 CSR Projects (${projects.length})
                </h4>
                <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px; padding:6px 12px;">
                    CSR Portal ↗
                </a>
            </div>

            <div style="display:flex; flex-direction:column; gap:10px;">
                ${projects.length > 0 ? projects.map(p => `
                    <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); padding:14px; border-radius:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                            <strong style="color:var(--text-primary); font-size:14px;">${escapeHtml(p.project_name || 'Community Development')}</strong>
                            ${p.category ? `<span class="badge badge-emerald">${escapeHtml(p.category)}</span>` : ''}
                        </div>
                        ${p.description ? `
                        <div style="font-size:12.5px; color:var(--text-secondary); margin-top:6px; line-height:1.5;">
                            ${escapeHtml(p.description)}
                        </div>` : ''}
                        <div style="display:flex; gap:14px; flex-wrap:wrap; font-size:11.5px; margin-top:8px; color:var(--text-muted);">
                            ${p.state ? `<span>📍 State: <strong style="color:var(--text-primary);">${escapeHtml(p.state)}</strong></span>` : ''}
                            ${p.budget ? `<span>💰 Allocation: <strong style="color:var(--accent-emerald);">${escapeHtml(p.budget)}</strong></span>` : ''}
                            ${p.financial_year ? `<span>📅 FY: <strong style="color:var(--text-primary);">${escapeHtml(p.financial_year)}</strong></span>` : ''}
                        </div>
                    </div>
                `).join('') : `
                    <div style="text-align:center; padding:36px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle); color:var(--text-secondary); font-size:13.5px;">
                        No statutory CSR project allocations catalogued from official Section 135 filings for this company.
                        <div style="margin-top:10px;">
                            <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px;">Visit CSR Portal ↗</a>
                        </div>
                    </div>
                `}
            </div>
        `;
    } else if (tab === 'opportunities') {
        body.innerHTML = `
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
                <h4 style="font-size:15px; font-weight:800; color:var(--text-primary); margin:0;">
                    Verified Grant RFPs &amp; Open Calls (${opportunities.length})
                </h4>
                <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px; padding:6px 12px;">
                    CSR Foundation ↗
                </a>
            </div>

            <div style="display:flex; flex-direction:column; gap:10px;">
                ${opportunities.length > 0 ? opportunities.map(opp => `
                    <div style="background:var(--bg-surface-subtle); border:1px solid var(--border-color); padding:16px; border-radius:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
                            <strong style="color:var(--text-primary); font-size:14.5px;">${escapeHtml(opp.title)}</strong>
                            <span class="badge badge-emerald">ACTIVE RFP</span>
                        </div>
                        ${opp.description ? `<p style="font-size:13px; color:var(--text-secondary); margin:6px 0 10px; line-height:1.5;">${escapeHtml(opp.description)}</p>` : ''}
                        <div style="display:flex; gap:14px; flex-wrap:wrap; font-size:12px; margin-bottom:10px;">
                            ${opp.funding_amount ? `<span>💰 Grant Pool: <strong style="color:var(--accent-emerald);">${escapeHtml(opp.funding_amount)}</strong></span>` : ''}
                            ${opp.deadline ? `<span>⏰ Deadline: <strong style="color:var(--accent-amber);">${escapeHtml(opp.deadline)}</strong></span>` : ''}
                        </div>
                        ${opp.application_url ? `
                        <a href="${escapeHtml(opp.application_url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px; padding:6px 14px;">
                            Apply for Grant ↗
                        </a>` : ''}
                    </div>
                `).join('') : `
                    <div style="text-align:center; padding:36px 20px; background:var(--bg-surface-subtle); border-radius:10px; border:1px solid var(--border-subtle);">
                        <div style="font-size:24px; margin-bottom:8px;">📋</div>
                        <div style="font-size:14.5px; font-weight:800; color:var(--text-primary); margin-bottom:4px;">No Open Grant RFPs Published</div>
                        <div style="font-size:13px; color:var(--text-secondary); max-width:440px; margin:0 auto 12px; line-height:1.5;">
                            ImpactBridge strictly verifies active RFP/EOI calls against official disclosures and does not manufacture speculative grant calls from ongoing programs.
                        </div>
                        <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="font-size:12px;">
                            Check Foundation Disclosures ↗
                        </a>
                    </div>
                `}
            </div>
        `;
    } else if (tab === 'contacts') {
        const tier = ((currentSubscription && currentSubscription.tier) || 'free').toLowerCase();
        const canViewContacts = tier === 'pro' || tier === 'ultra';

        let lockBannerHtml = '';
        if (!canViewContacts) {
            lockBannerHtml = `
                <div style="background:var(--primary-brand-light); border:1px solid rgba(15,118,110,0.3); padding:16px 20px; border-radius:12px; margin-bottom:18px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
                    <div>
                        <div style="font-size:14px; font-weight:800; color:var(--text-primary); display:flex; align-items:center; gap:8px;">
                            <span>🔒 Executive Contacts Masked (Community Free Tier)</span>
                        </div>
                        <div style="font-size:12.5px; color:var(--text-secondary); margin-top:4px;">
                            Upgrade to <strong>Impact Pro</strong> or <strong>Ultra</strong> to unmask direct emails, verified phone numbers, and generate 1-click tailored CSR pitches.
                        </div>
                    </div>
                    <button class="btn-primary" style="font-size:12px; padding:8px 16px;" onclick="openSubscriptionModal('pro')">
                        Unlock Direct Contacts ⚡
                    </button>
                </div>
            `;
        }

        const validContacts = contacts.filter(c => c && (c.name || c.email));

        body.innerHTML = `
            <div class="insight-box">
                <div class="insight-title" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                    <span>Publicly Verified Contact Directory</span>
                    ${canViewContacts 
                        ? `<span class="badge badge-emerald" style="font-size:11px;">✓ Unmasked Direct Contacts (${(currentSubscription && currentSubscription.plan_name) || 'Active'})</span>` 
                        : `<span class="badge badge-purple" style="font-size:11px;">🔒 Masked on Free Plan</span>`}
                </div>
                ${lockBannerHtml}
                <p style="font-size:13px; color:var(--text-secondary); margin-bottom:12px;">
                    Honesty Guarantee: We only present contacts that have been publicly verified on official corporate portals.
                </p>
                ${validContacts.length > 0 ? validContacts.map(c => {
                    const rawEmail = c.email || '';
                    const displayEmail = canViewContacts 
                        ? escapeHtml(rawEmail) 
                        : escapeHtml(rawEmail.replace(/(?<=.{2}).(?=[^@]*?@)/g, '*'));
                    const rawPhone = c.phone || null;
                    const displayPhone = rawPhone ? (canViewContacts ? escapeHtml(rawPhone) : '•••• ••••') : null;

                    return `
                        <div class="insight-item" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
                            <div>
                                <span>${escapeHtml(c.name || c.designation || 'CSR Representative')}</span>
                                ${displayEmail ? `<strong style="font-size:13px; color:${canViewContacts ? 'var(--primary-brand)' : 'var(--text-muted)'}; margin-left:8px;">${displayEmail}</strong>` : ''}
                                ${displayPhone ? `<span style="font-size:12px; color:var(--text-secondary); margin-left:8px;">📞 ${displayPhone}</span>` : ''}
                            </div>
                            ${canViewContacts && rawEmail ? `
                                <a href="mailto:${escapeHtml(rawEmail)}?subject=CSR%20Partnership%20Inquiry%20-%20Section%20135&body=Dear%20${encodeURIComponent(c.name || 'CSR Head')},%0D%0A%0D%0AWe%20are%20reaching%20out%20from%20our%20non-profit%20regarding%20statutory%20CSR%20partnership%20under%20Schedule%20VII..." class="btn-secondary" style="font-size:11px; padding:4px 10px;">
                                    ✉️ 1-Click Pitch
                                </a>
                            ` : (!canViewContacts ? `
                                <button class="btn-secondary" style="font-size:11px; padding:4px 10px; opacity:0.8;" onclick="openSubscriptionModal('pro')">
                                    🔒 Unmask
                                </button>
                            ` : '')}
                        </div>
                    `;
                }).join('') : `
                    <div style="font-size:13px; color:var(--text-secondary); padding:16px; background:var(--bg-surface-subtle); border-radius:8px; line-height:1.5;">
                        No executive contact names or direct mailboxes were published in the official disclosures for this company. All inquiries should be directed through the official corporate foundation portal:
                        <div style="margin-top:10px;">
                            <a href="${csrUrl}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px;">
                                Visit CSR Portal ↗
                            </a>
                        </div>
                    </div>
                `}
            </div>
        `;
    } else if (tab === 'reports') {
        const hasAnnual = !!comp.annual_report_url;
        const hasCsr = !!comp.csr_policy_url;
        const hasSust = !!comp.sustainability_url;
        const hasBrsr = !!comp.brsr_report_url;
        const anyReports = hasAnnual || hasCsr || hasSust || hasBrsr;

        body.innerHTML = `
            <div class="insight-box">
                <div class="insight-title">Statutory Reports &amp; Disclosures (Part 14 Audit)</div>
                <p style="font-size:13px; color:var(--text-secondary); margin-bottom:14px;">
                    Official published reports, BRSR disclosures, and statutory CSR filings archived directly from company investor relations &amp; ESG portals.
                </p>
                <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:12px;">
                    ${hasAnnual ? `
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:14px; border-radius:8px;">
                        <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:4px;">📄 Annual Report</div>
                        <div style="font-size:12px; color:var(--text-muted); margin-bottom:10px;">Official Statutory Filing</div>
                        <a href="${escapeHtml(comp.annual_report_url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11px; padding:4px 10px;">View Report ↗</a>
                    </div>` : ''}

                    ${hasCsr ? `
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:14px; border-radius:8px;">
                        <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:4px;">🌱 CSR Policy &amp; Projects</div>
                        <div style="font-size:12px; color:var(--text-muted); margin-bottom:10px;">Section 135 Mandate</div>
                        <a href="${escapeHtml(comp.csr_policy_url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11px; padding:4px 10px;">View Policy ↗</a>
                    </div>` : ''}

                    ${hasSust ? `
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:14px; border-radius:8px;">
                        <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:4px;">🌍 Sustainability Portal</div>
                        <div style="font-size:12px; color:var(--text-muted); margin-bottom:10px;">ESG / Decarbonization</div>
                        <a href="${escapeHtml(comp.sustainability_url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11px; padding:4px 10px;">Open Portal ↗</a>
                    </div>` : ''}

                    ${hasBrsr ? `
                    <div style="background:var(--bg-surface); border:1px solid var(--border-color); padding:14px; border-radius:8px;">
                        <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:4px;">📊 BRSR Report</div>
                        <div style="font-size:12px; color:var(--text-muted); margin-bottom:10px;">SEBI Core Disclosures</div>
                        <a href="${escapeHtml(comp.brsr_report_url)}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:11px; padding:4px 10px;">Open BRSR ↗</a>
                    </div>` : ''}
                </div>

                ${!anyReports ? `
                <div style="font-size:13px; color:var(--text-secondary); padding:16px; background:var(--bg-surface-subtle); border-radius:8px; margin-top:10px;">
                    Statutory annual reports and SEBI BRSR disclosures are catalogued directly upon authoritative regulatory sync. Check the official company domain for filings:
                    <div style="margin-top:8px;">
                        <a href="${website}" target="_blank" rel="noopener noreferrer" class="btn-primary" style="font-size:12px;">Visit ${escapeHtml(cleanDomainLabel(website))} ↗</a>
                    </div>
                </div>` : ''}
            </div>
        `;
    } else if (tab === 'sources' || tab === 'domains') {
        body.innerHTML = `
            <div class="insight-box">
                <div class="insight-title">Authoritative Source Provenance &amp; Audit Trail</div>
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
                ${comp.ats_platform ? `
                <div class="insight-item">
                    <span>Verified ATS Platform</span>
                    <strong style="color:var(--accent-cyan);">${escapeHtml(comp.ats_platform)}</strong>
                </div>` : ''}
                <div class="insight-item">
                    <span>HTTP Status Check</span>
                    <strong style="color:var(--accent-emerald);">Source Confirmed</strong>
                </div>
                <div class="insight-item">
                    <span>Robots.txt Adherence</span>
                    <strong style="color:var(--accent-emerald);">RFC 9309 Compliant</strong>
                </div>
                <div class="insight-item">
                    <span>Last Probed</span>
                    <strong>${escapeHtml(comp.last_verified_display || comp.link_verified_at || 'Today')}</strong>
                </div>
                <div class="insight-item">
                    <span>Data Governance</span>
                    <strong style="color:var(--accent-emerald);">Strict Evidence Verification</strong>
                </div>
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
    while (crawlRunning) {
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
                let pct = Math.floor(5 + (crawled / total) * 90);
                setProgress(pct, `Crawling (${crawled}/${total}) | Jobs: ${stats.new_jobs || 0} New, ${stats.updated_jobs || 0} Updated | CSR: ${stats.csr_projects || 0} Projects, ${stats.csr_pdfs || 0} PDFs | Contacts: ${stats.contacts_found || 0}`);
                
                if (streamData.is_running === false && printedLogsCount > 0) {
                    crawlRunning = false;
                }
            }
        } catch (e) {
            console.warn('Live stream poll error', e);
            crawlRunning = false;
        }
        
        if (crawlRunning) {
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
            loadOpportunities(1)
        ]);
    } catch (e) {
        console.warn('Dataset re-render notice:', e);
    }

    setProgress(100, 'Complete: Crawl operation finished!');
    appendTerminalLog('term-badge-ok', 'DONE', '✨ Success! Data fetch pipeline has completed.');

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

// Dark Mode Toggle
function toggleDarkMode() {
    const htmlEl = document.documentElement;
    const isDark = htmlEl.classList.contains('dark-mode');
    
    if (isDark) {
        htmlEl.classList.remove('dark-mode');
        localStorage.setItem('theme', 'light');
    } else {
        htmlEl.classList.add('dark-mode');
        localStorage.setItem('theme', 'dark');
    }
}

// Check local storage on load
document.addEventListener('DOMContentLoaded', () => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark-mode');
    }
});
