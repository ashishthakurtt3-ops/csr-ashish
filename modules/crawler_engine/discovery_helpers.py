"""
modules/crawler_engine/discovery_helpers.py
===========================================
Pure-Python helper functions for deep link validation, registrable domain
equivalence, and careers page content verification (Stage 1).
"""
import re
import json
from urllib.parse import urlparse
from typing import Optional, Tuple, List, Dict, Any
from bs4 import BeautifulSoup

from .normalizers import clean_text, match_ats_pattern, load_ats_patterns

# Known multi-part Indian and international public suffixes for base domain resolution
_KNOWN_TWO_PART_SUFFIXES = {
    "co.in", "net.in", "org.in", "gov.in", "ac.in", "res.in",
    "co.uk", "org.uk", "me.uk", "ltd.uk", "plc.uk",
    "com.au", "net.au", "org.au", "edu.au",
    "co.za", "co.jp", "com.sg", "com.my", "com.br"
}

STATIC_ASSET_EXTENSIONS = (
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico',
    '.pdf', '.zip', '.tar', '.gz', '.css', '.js', '.mp4', '.mp3',
    '.woff', '.woff2', '.ttf', '.eot', '.doc', '.docx', '.xls', '.xlsx'
)

def is_static_asset_url(url: Optional[str]) -> bool:
    if not url:
        return True
    u_lower = str(url).lower().strip()
    parsed = urlparse(u_lower)
    path = parsed.path
    if any(path.endswith(ext) for ext in STATIC_ASSET_EXTENSIONS):
        return True
    if any(f"{ext}?" in u_lower for ext in STATIC_ASSET_EXTENSIONS):
        return True
    if any(k in u_lower for k in ['/adobe/assets/', '/wp-content/uploads/', '/assets/images/', '/static/media/', '/banner/']):
        return True
    return False

NAV_BLACKLIST = {
    'fraud alert', 'fraud alert - global', 'equal opportunity', 'equal opportunity policy',
    'frequently asked questions', 'faq', 'faqs', 'view all', 'download app', 'video library',
    'privacy policy', 'terms of use', 'terms & conditions', 'terms and conditions', 'know more',
    'click here', 'apply now', 'read more', 'all rights reserved', 'disclaimer', 'sitemap',
    'cookie policy', 'cookie settings', 'login', 'sign in', 'sign-in', 'register',
    'types of loan against assets', 'know more about loans', 'types of loan',
    'see all jobs', 'view all jobs', 'explore jobs', 'search jobs', 'job search',
    'open positions', 'current openings', 'careers', 'career', 'home', 'about',
    'about us', 'contact', 'contact us', 'skip to main content', 'skip to content',
    'investor relations', 'media', 'newsroom', 'press release', 'press releases',
    'our impact', 'follow us', 'download', 'future ready', 'performance driven',
    'purpose led', 'leadership', 'values', 'our history', 'our brands', 'calculator',
    'branch locator', 'locator', 'free credit score', 'annual secretarial compliance',
    'shareholders', 'investor services', 'media centre', 'customer service',
    'loss of share certificates', 'odr portal', 'centre for excellence', 'sports',
    'procurement', 'tata steel group companies', 'group companies', 'awards & recognitions',
    'heritage', 'policies', 'ethics', 'vision, mission & values', 'company profile',
    'tata group profile', 'group profile', 'professionals', 'entry-level roles',
    'academies', 'students', 'overview', 'case studies', 'menu', 'typed', 'our products',
    'our story', 'discover your team', 'become part of our family.', 'become part of',
    'learn', 'browse job by', 'browse job', 'initiatives', 'campus connect',
    'rewards and recognition', 'culture at tata steel', 'culture at', 'talent management for enterprises',
    'talent management', 'statewide multidisciplinary skilling transformation',
    'skilling transformation', 'scaling ai learning for enterprise retail',
    'scaling ai learning', 'bridging enterprise skill set with industry expertise',
    'bridging enterprise', 'bridging academia and industry through real-world projects',
    'bridging academia', 'digital academy for driving talent transformation',
    'digital academy', 'learning management system', 'work with us', 'why join us',
    'why join', 'life at', 'who we are', 'what we do', 'events', 'webinars',
    'brochure', 'help centre', 'we are hiring', 'more details', 'details', 'join us',
    'join our team', 'search openings', 'view all roles', 'explore all roles',
    'see all roles', 'submit resume', 'job alert', 'see openings', 'soar',
    'stay in the loop', 'launch your career here', 'how we hire', 'find your team',
    'everything at adobe starts with our people', 'our purpose fuels our business',
    'life at wipro', 'inclusion and belonging', 'hear from our employees',
    'follow us to know #lifeatinfy', 'life at infy', 'graduates', 'discover more',
    'saved jobs', 'view our ads', 'download forms', 'customer education',
    'adani career site', 'adani connex career site', 'culture', 'jobs at ultratech',
    'our values', 'beware of fraudulent job offers', 'wipro locations',
    'explore opportunities on cummins.jobs', 'about cummins', 'accommodations',
    'jobcategorylinks', 'would you like to cancel this interview', 'request additional interview slots',
    'can’t find what you are looking for', "can't find what you are looking for",
    'apply at itc', 'boondh: blending creativity with corporate life', 'copyright & terms',
    'analyst relations', 'website feedback', 'partnership', 'csr',
    'gobally present, regionally supported', 'search for open positions by country'
}

CORE_ROLE_NOUNS = {
    'engineer', 'developer', 'programmer', 'coder', 'architect',
    'specialist', 'manager', 'lead', 'leader', 'analyst', 'consultant',
    'officer', 'associate', 'executive', 'administrator', 'coordinator',
    'director', 'designer', 'scientist', 'technician', 'operator',
    'representative', 'trainee', 'intern', 'head', 'supervisor', 'advisor',
    'controller', 'auditor', 'planner', 'strategist', 'recruiter', 'accountant',
    'buyer', 'trader', 'assistant', 'deputy', 'vp', 'avp', 'gm', 'agm', 'dgm',
    'clerk', 'teller', 'artisan', 'welder', 'fitter', 'machinist', 'electrician',
    'mechanic', 'driver', 'chemist', 'biologist', 'toxicologist', 'counsel',
    'attorney', 'advocate', 'paralegal', 'underwriter', 'actuary', 'instructor',
    'trainer', 'inspector', 'writer', 'expert', 'fellow', 'worker', 'helper',
    'agent', 'qa', 'devops', 'sre', 'dba', 'sde', 'post of director', 'estágio',
    'mgr', 'partner', 'president', 'chief'
}

INDIAN_STATES_CITIES = {
    'mumbai', 'pune', 'nagpur', 'nashik', 'aurangabad', 'thane', 'navi mumbai', 'maharashtra',
    'bengaluru', 'bangalore', 'mysore', 'mysuru', 'mangalore', 'mangaluru', 'karnataka',
    'hyderabad', 'secunderabad', 'telangana', 'visakhapatnam', 'vijayawada', 'andhra pradesh',
    'chennai', 'coimbatore', 'madurai', 'salem', 'tiruchirappalli', 'tamil nadu',
    'delhi', 'new delhi', 'noida', 'greater noida', 'gurugram', 'gurgaon', 'faridabad', 'haryana',
    'kolkata', 'howrah', 'west bengal', 'ahmedabad', 'vadodara', 'surat', 'rajkot', 'jamnagar', 'gujarat',
    'jaipur', 'jodhpur', 'udaipur', 'kota', 'rajasthan', 'lucknow', 'kanpur', 'agra', 'varanasi', 'prayagraj', 'uttar pradesh',
    'bhopal', 'indore', 'gwalior', 'jabalpur', 'madhya pradesh', 'patna', 'bihar', 'ranchi', 'dhanbad', 'jharkhand',
    'bhubaneswar', 'odisha', 'guwahati', 'assam', 'chandigarh', 'punjab', 'amritsar', 'ludhiana',
    'dehradun', 'uttarakhand', 'shimla', 'himachal pradesh', 'srinagar', 'jammu', 'jammu and kashmir', 'kashmir',
    'pan-india', 'pan india', 'india'
}

def is_valid_job_title(title: Optional[str]) -> bool:
    if not title:
        return False
    t = str(title).strip()
    if len(t) < 4 or len(t) > 100:
        return False

    t_clean = re.sub(r'[\.\,\:\;\-\–\—\(\)\[\]\{\}\'\"\#\*\!\?]+', ' ', t).strip()
    t_lower = t_clean.lower()

    # 1. Reject phone numbers, shortcodes, dialing prompts (+91, 56161, dial, sms)
    if re.search(r'(\+91|\b\d{5,}\b|dial\b|sms\b|toll[\s-]?free)', t_lower):
        return False

    # 2. Reject exact or boundary blacklist matches (only if the title does NOT contain a real job role)
    for junk in NAV_BLACKLIST:
        if junk == t_lower:
            return False
        if len(junk.split()) >= 2 and (junk in t_lower) and not any(r in t_lower for r in ['engineer', 'developer', 'manager', 'lead', 'analyst', 'consultant', 'officer', 'associate', 'executive', 'director']):
            return False

    # 3. Reject personal names with salutations or executive quotes (e.g. "Mitika Bajpai Deputy General Manager", "Mr. Gopikrishna Shenoy...")
    if re.match(r'^(mr|ms|mrs|dr|prof)\.?\s+[a-z]+', t, re.IGNORECASE):
        return False
    if re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+(Deputy General Manager|General Manager|Chief|Director|Officer|Lead|Manager)', t):
        return False

    # 4. Reject banking/financial products, account types, and loan categories
    if re.search(r'\b(senior citizen account|senior citizen|loan against|loans against|sme loan|sme loans|business loan|home loan|personal loan|gold loan|demat account|savings account|current account|credit card|debit card|fixed deposit|recurring deposit|banking comfort|premium offerings)\b', t_lower):
        return False

    # 5. Reject Board of Directors / Corporate Governance Committees
    if re.search(r'\b(committee|board of directors|audit committee|risk management committee|nomination and remuneration|stakeholders relationship|borrowing and investment|property committee)\b', t_lower):
        return False

    # 6. Reject pure locations (e.g. "Srinagar, Jammu and Kashmir", "Pune, Maharashtra")
    parts = [p.strip().lower() for p in re.split(r'[,/–—\-]+', t) if p.strip()]
    if parts and all(p in INDIAN_STATES_CITIES for p in parts):
        return False

    # 7. Reject press releases, deal wins, sponsorships, brand ambassadors, awards
    if re.search(r'\b(selects\b.*to transform|wins contract|announces financial|reports q[1-4]|signs mou|partners with|brand ambassador|championships|selects tcs|analyst recognition|guardrails products|industrial autonomy)\b', t_lower):
        return False

    # 8. Reject action prompts & UI forms
    if re.search(r'\b(would you like to cancel|cancel this interview|request additional|interview slots?|jobcategorylinks|saved jobs|can’t find|cant find|stay in the loop|launch your career|how we hire|everything at|find your team|our purpose|our values|our story|our history|our products|culture at|life at|inclusion and belonging|website feedback|partnership|feedback|disclaimer|copyright|all rights reserved)\b', t_lower):
        return False

    # 9. Reject advertisement notices alone
    if re.match(r'^(advt|advertisement|notice)\.?\s*(\bno\.?|\b0\d|\b[0-9/]+)?$', t_lower):
        return False

    # 10. Must contain at least one CORE_ROLE_NOUN
    has_role = any(re.search(r'\b' + re.escape(w) + r'\b', t_lower) for w in CORE_ROLE_NOUNS)
    return has_role


JUNK_CSR_PATTERNS = [
    r'\b(information contained in this website|for general information|general information purpose)\b',
    r'\b(setter on your browser|refuse to accept cookies|accept cookies|cookie policy)\b',
    r'\b(we will keep the information|information we collect about you)\b',
    r'\b(all rights reserved|terms and conditions|terms of use|privacy policy|disclaimer)\b',
    r'\b(strategic account services|amazon business|outsource your supply chain|sell b2b|fulfilled by merchant|\bfbm\b|amazon vine|get product reviews|paid services|programs to help you grow)\b',
    r'\b(agentic commerce|merchandise vendors on sedex|acquisition of elder pharma|elder pharma)\b',
    r'\b(sustainability report for|sustainability report cy|sustainability report 20)\b',
    r'\b(the epd provides|mobile device you are using|version of the operating system)\b',
    r'\b(technology to transform|creativity for all|adobe for all)\b',
    r'^(download|download forms|corporate csr initiative|csr initiative|csr partnership|environment & sustainability initiative)$'
]

CSR_SENTENCE_STARTER_REGEX = re.compile(
    r'^(the impacts of|in a rapidly changing|no single organization|business sustainability is|'
    r'itc is one of|ntpc is india|waste management is a material|enhancing access to education|'
    r'our environmental policy|our commitment to|we aim to continuously|with one of the best|'
    r'to achieve its green|all efforts are made|motherson is proud|this commitment goes|'
    r'torrent pharma is committed|the acquisition of|we endeavour to|we currently reach out|'
    r'beyond india|driven by a 500\+|to plant our vast|at adani|projects range from|'
    r'lic golden jubilee foundation was established|the information contained|mobile device you are using|'
    r'we understand how to reframe|wipro helps our clients|cummins continues to extend|'
    r'work started in 1996|hmif provides apprenticeship|research & development research & development|'
    r'veterinary professionals provide|women empowered through livelihood)',
    re.IGNORECASE
)

CSR_PROGRAM_INDICATORS = {
    'program', 'programme', 'initiative', 'project', 'foundation', 'fellowship',
    'campaign', 'outreach', 'mission', 'trust', 'school', 'health', 'healthcare',
    'sanitation', 'water', 'literacy', 'education', 'rural', 'livelihood', 'afforestation',
    'biodiversity', 'scholarship', 'development', 'skill', 'skills', 'skilling', 'hospital',
    'relief', 'empower', 'empowerment', 'swachh', 'anganwadi', 'vidya', 'arogya',
    'society', 'drive', 'conservation', 'nutrition', 'tree plantation', 'watershed',
    'clean energy', 'disaster', 'shelter', 'blood donation', 'caregiving', 'robot sanitation',
    'code unnati', 'sabbatical', 'bridge it', 'ignite my future', 'goit', 'jyoti',
    'vasundhara', 'vidyaadhanam', 'sparsh', 'upbridge', 'shwet', 'social', 'parivartan',
    'nanhi kali', 'samuday', 'mansi', 'bajaj beyond', 'boond', 'vidushi', 'satya bharti',
    'colour academy', 'palliative care', 'vidya mandir', 'academy', 'institute', 'training', 'road safety'
}

def is_valid_csr_project(name: Optional[str]) -> bool:
    if not name:
        return False
    n = str(name).strip()
    if len(n) < 5 or len(n) > 130:
        return False
    n_lower = n.lower()

    if CSR_SENTENCE_STARTER_REGEX.match(n):
        return False

    if re.search(r'(\.{3,}|…|\*)$', n):
        return False

    for pat in JUNK_CSR_PATTERNS:
        if re.search(pat, n_lower):
            return False

    has_indicator = any(re.search(r'\b' + re.escape(w) + r'\b', n_lower) for w in CSR_PROGRAM_INDICATORS)
    return has_indicator

ENTERPRISE_PORTAL_REGISTRY = {
    'tata consultancy': 'https://www.tcs.com/careers/india',
    'tcs': 'https://www.tcs.com/careers/india',
    'infosys': 'https://career.infosys.com/',
    'microsoft': 'https://careers.microsoft.com/professionals/us/en/search-results?q=India',
    'reliance': 'https://careers.ril.com/rilcareers/frmjobsearch.Aspx',
    'ril': 'https://careers.ril.com/rilcareers/frmjobsearch.Aspx',
    'samsung': 'https://sec.wd3.myworkdayjobs.com/Samsung_Careers',
    'amazon': 'https://amazon.jobs/en/search?country=IND',
    'google': 'https://www.google.com/about/careers/applications/jobs/results/?location=India',
    'hcl': 'https://www.hcltech.com/careers',
    'wipro': 'https://careers.wipro.com/search',
    'icici': 'https://www.icicicareers.com/CareerApplicant/Career/SearchJob',
    'hdfc': 'https://hdfcbank.taleo.net/careersection/ex/jobsearch.ftl',
    'accenture': 'https://www.accenture.com/in-en/careers',
    'cognizant': 'https://careers.cognizant.com/global/en',
    'larsen': 'https://www.larsentoubro.com/corporate/careers/',
    'l&t': 'https://www.larsentoubro.com/corporate/careers/',
    'tata motors': 'https://careers.tatamotors.com/go/View-All-Opportunities/3505801/',
    'tata steel': 'https://tslhr.tatasteel.co.in/recruit/',
    'maruti': 'https://www.marutisuzuki.com/corporate/careers',
    'sap': 'https://jobs.sap.com/',
    'axis bank': 'https://www.axisbank.com/careers',
    'state bank': 'https://sbi.co.in/web/careers/current-openings',
    'sbi': 'https://sbi.co.in/web/careers/current-openings',
    'kotak': 'https://www.kotak.com/en/about-us/careers.html',
    'itc': 'https://www.itcportal.com/careers/',
    'mahindra': 'https://www.mahindra.com/careers',
    'sun pharma': 'https://sunpharma.com/careers/',
    'airtel': 'https://www.airtel.in/careers/',
    'bharti': 'https://www.airtel.in/careers/',
    'asian paints': 'https://www.asianpaints.com/careers.html',
    'bajaj': 'https://www.bajajauto.com/careers',
    'hindalco': 'https://www.hindalco.com/careers',
    'ntpc': 'https://careers.ntpc.co.in/recruitment/',
    'ongc': 'https://ongcindia.com/web/eng/career',
    'power grid': 'https://www.powergrid.in/careers',
    'coal india': 'https://www.coalindia.in/career-cil/',
    'bharat petroleum': 'https://www.bharatpetroleum.in/careers/',
    'bpcl': 'https://www.bharatpetroleum.in/careers/',
    'indian oil': 'https://iocl.com/latest-job-opening',
    'iocl': 'https://iocl.com/latest-job-opening',
    'hindustan unilever': 'https://www.unilever.com/careers/',
    'hul': 'https://www.unilever.com/careers/',
    'nestle': 'https://www.nestle.in/jobs',
    'ultratech': 'https://www.ultratechcement.com/careers',
    'jsw': 'https://www.jsw.in/careers',
    'adani': 'https://careers.adani.com/',
    'tech mahindra': 'https://careers.techmahindra.com/',
    'dr. reddy': 'https://careers.drreddys.com/',
    'cipla': 'https://www.cipla.com/careers',
    'zomato': 'https://www.zomato.com/careers',
    'swiggy': 'https://careers.swiggy.com/',
    'paytm': 'https://paytm.com/careers/',
    'razorpay': 'https://razorpay.com/jobs/',
    'hitachi energy': 'https://www.hitachienergy.com/careers/open-jobs',
    'varun beverages': 'https://www.varunbeverages.com/careers'
}

ENTERPRISE_CSR_REGISTRY = {
    'tata consultancy': 'https://www.tcs.com/corporate-social-responsibility',
    'tcs': 'https://www.tcs.com/corporate-social-responsibility',
    'infosys': 'https://www.infosys.com/infosys-foundation/',
    'reliance': 'https://www.reliancefoundation.org/',
    'ril': 'https://www.reliancefoundation.org/',
    'maruti': 'https://www.marutisuzuki.com/corporate/sustainability/csr',
    'hdfc': 'https://www.hdfcbank.com/personal/about-us/corporate-social-responsibility',
    'icici': 'https://www.icicifoundation.org/',
    'wipro': 'https://wiprofoundation.org/',
    'hcl': 'https://www.hclfoundation.org/',
    'larsen': 'https://www.larsentoubro.com/corporate-social-responsibility/',
    'l&t': 'https://www.larsentoubro.com/corporate-social-responsibility/',
    'tata motors': 'https://www.tatamotors.com/sustainability/csr/',
    'tata steel': 'https://www.tatasteel.com/corporate/sustainability/corporate-social-responsibility/',
    'sap': 'https://www.sap.com/about/company/corporate-social-responsibility.html',
    'amazon': 'https://www.aboutamazon.in/impact/community/csr-policy',
    'microsoft': 'https://www.microsoft.com/en-in/about/csr',
    'mahindra': 'https://www.mahindra.com/sustainability/corporate-social-responsibility',
    'itc': 'https://www.itcportal.com/sustainability/',
    'asian paints': 'https://www.asianpaints.com/more/csr.html',
    'sun pharma': 'https://sunpharma.com/csr/',
    'bajaj': 'https://www.bajajauto.com/about-us/corporate-social-responsibility',
    'airtel': 'https://www.bhartifoundation.org/',
    'bharti': 'https://www.bhartifoundation.org/',
    'ultratech': 'https://www.ultratechcement.com/sustainability/corporate-social-responsibility',
    'jsw': 'https://www.jsw.in/foundation',
    'adani': 'https://www.adanifoundation.org/',
    'tech mahindra': 'https://techmahindrafoundation.org/',
    'dr. reddy': 'https://www.drreddysfoundation.org/',
    'cipla': 'https://www.ciplafoundation.org/'
}

def derive_deep_job_url(careers_url: str, comp_name: str, job_title: str, existing_url: str = "", req_id: str = "") -> str:
    """
    Constructs an authentic, working application URL for a job vacancy.
    Preserves real ATS/portal deep links, maps known enterprises to their live recruitment portals,
    and never fabricates fake MD5 hash parameters or broken image URLs.
    """
    comp_lower = comp_name.strip().lower()

    # 1. If an authentic, working direct application/requisition URL was genuinely provided or discovered:
    if existing_url and str(existing_url).startswith(('http://', 'https://')):
        u_str = str(existing_url).strip()
        if not is_static_asset_url(u_str):
            clean_u = re.sub(r'([?&])(utm_[^&]+|fbclid=[^&]+|ref=[^&]+)', '', u_str).rstrip('&?')
            clean_u = re.sub(r'#job-[A-F0-9]{4,16}$', '', clean_u, flags=re.IGNORECASE)
            clean_u = re.sub(r'#:~:text=.*$', '', clean_u, flags=re.IGNORECASE)

            # Strictly reject candidate login walls, account signin portals, and session walls
            if any(bad in clean_u.lower() for bad in [
                '/candidate/?', '/candidate/', 'candidate.tcsapps.com', 'ibegin.tcsapps.com/candidate',
                'signin', 'auth/login', 'accounts.google', 'login.microsoftonline'
            ]):
                clean_u = ""
            elif any(k in u_str.lower() for k in [
                '/job/', 'jobid=', 'jobreferencecode=', '/jobs/', '/apply', 'req=', 'id=',
                'frmjobsearch.aspx', 'workdayjobs.com', 'amazon.jobs', 'lever.co',
                'greenhouse.io', 'smartrecruiters.com', 'darwinbox', 'peoplestrong.com',
                'taleo.net', 'oraclecloud.com', 'successfactors'
            ]):
                return clean_u
            elif clean_u:
                parsed_u = urlparse(clean_u)
                if parsed_u.path.strip('/') not in ('', 'careers', 'career', 'jobs', 'job', 'home'):
                    return clean_u

    # 2. If requisition ID is present, construct authentic deep ATS link ONLY for platforms with direct ID routes:
    if req_id and str(req_id).strip():
        req_clean = str(req_id).strip()
        # Strictly reject synthetic AI-hallucinated pattern IDs
        if not any(req_clean.startswith(prefix) for prefix in ['TCS/IND/', 'WIP-IND-', 'INFY-REQ-', 'FAKE-', 'REQ-9', 'REQ-8']):
            if 'amazon' in comp_lower and req_clean.isdigit():
                return f"https://amazon.jobs/en/jobs/{req_clean}"
            if ('reliance' in comp_lower or 'ril' in comp_lower) and req_clean.isdigit():
                return f"https://careers.ril.com/rilcareers/frmJobSearch.aspx?jbID={req_clean}"
            if 'samsung' in comp_lower:
                return f"https://sec.wd3.myworkdayjobs.com/Samsung_Careers/job/{req_clean}"

    # 3. Check enterprise verified portal registry for targeted deep job search:
    for k, portal in ENTERPRISE_PORTAL_REGISTRY.items():
        if k in comp_lower:
            return portal

    # 4. Fallback: Clean and return the company's verified careers_url
    if careers_url and str(careers_url).startswith(('http://', 'https://')):
        c_clean = str(careers_url).strip()
        if not is_static_asset_url(c_clean):
            return re.sub(r'\?.*$', '', c_clean).rstrip('/')

    return f"https://www.google.com/search?q={urllib.parse.quote_plus(comp_name + ' careers jobs apply')}"

def resolve_authentic_csr_url(csr_url: str, comp_name: str, project_name: str = "") -> str:
    """
    Constructs an authentic, verified Section 135 CSR portal URL.
    Preserves deep initiative pages and avoids degrading them to generic portals.
    """
    # 1. If an explicit, valid project-level URL was discovered, PRESERVE IT!
    if csr_url and str(csr_url).startswith(('http://', 'https://')):
        c_clean = str(csr_url).strip()
        c_clean = re.sub(r'#:~:text=.*$', '', c_clean, flags=re.IGNORECASE)
        if not is_static_asset_url(c_clean):
            parsed = urlparse(c_clean)
            path_clean = parsed.path.strip('/')
            if path_clean and path_clean not in ('', 'csr', 'sustainability', 'about-us'):
                return re.sub(r'([?&])(utm_[^&]+|fbclid=[^&]+|ref=[^&]+)', '', c_clean).rstrip('&?/')

    # 2. Check enterprise CSR registry for authoritative foundation/CSR portal
    comp_lower = comp_name.strip().lower()
    for k, portal in ENTERPRISE_CSR_REGISTRY.items():
        if k in comp_lower:
            return portal

    if csr_url and str(csr_url).startswith(('http://', 'https://')):
        c_clean = str(csr_url).strip()
        if not is_static_asset_url(c_clean):
            return re.sub(r'\?.*$', '', c_clean).rstrip('/')

    return f"https://www.google.com/search?q={urllib.parse.quote_plus(comp_name + ' corporate social responsibility CSR Section 135')}"

JOB_ACTION_PHRASES = re.compile(
    r'\b(apply\s+now|apply\s+for\s+this\s+job|view\s+job|view\s+openings|search\s+jobs|open\s+positions|explore\s+roles|current\s+openings|submit\s+application|job\s+details)\b',
    re.IGNORECASE
)

JOB_URL_PATTERNS = re.compile(
    r'(/job/|/jobs/|/career[s]?/[^/?#]+|jobid=|job_id=|requisition|opening[s]?/[^/?#]+|vacancy/[^/?#]+|vacancies/[^/?#]+|positions?/[^/?#]+)',
    re.IGNORECASE
)

REPEATED_CARD_CLASSES = re.compile(
    r'(job-card|jobcard|job-item|jobitem|job-listing|joblisting|job-row|jobrow|career-item|position-item|opening-card|search-result-item)',
    re.IGNORECASE
)


def normalize_url_for_comparison(url: Optional[str]) -> Tuple[str, str]:
    """
    Normalizes a URL into (clean_host, clean_path) for equivalence checking.
    Strips protocol, port, user info, 'www.' prefix, and trailing slashes.
    """
    cleaned = clean_text(url)
    if not cleaned:
        return "", ""

    if "://" not in cleaned:
        cleaned = f"https://{cleaned}"

    parsed = urlparse(cleaned)
    host = (parsed.netloc or "").lower().split(":")[0].strip()
    if host.startswith("www."):
        host = host[4:]

    path = (parsed.path or "").strip().rstrip("/")
    return host, path


def get_registrable_domain(url_or_host: Optional[str]) -> str:
    """
    Extracts the base registrable domain from a host or URL.
    Examples:
      - 'careers.tatamotors.com' -> 'tatamotors.com'
      - 'www.sbi.co.in' -> 'sbi.co.in'
      - 'new.abb.com' -> 'abb.com'
    """
    cleaned = clean_text(url_or_host)
    if not cleaned:
        return ""

    if "://" in cleaned:
        parsed = urlparse(cleaned)
        host = (parsed.netloc or "").lower().split(":")[0].strip()
    else:
        host = cleaned.lower().split("/")[0].split(":")[0].strip()

    if host.startswith("www."):
        host = host[4:]

    parts = host.split(".")
    if len(parts) <= 2:
        return host

    # Check two-part ccTLDs e.g. .co.in
    last_two = ".".join(parts[-2:])
    if last_two in _KNOWN_TWO_PART_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])

    return ".".join(parts[-2:])


def is_real_deep_url(url: Optional[str], website_url: Optional[str]) -> bool:
    """
    Determines if candidate URL is a genuine deep link rather than a root homepage.
    Returns False if:
      - url is empty or None
      - path is '' or '/' AND the host is the same root host as website_url
      - url equals website_url (ignoring protocol, www, and trailing slash)
    Returns True if:
      - url has a distinct path (e.g. /careers, /jobs, /csr)
      - url has a distinct subdomain (e.g. careers.company.com vs company.com)
      - url is on an external ATS or portal domain
    """
    c_host, c_path = normalize_url_for_comparison(url)
    w_host, w_path = normalize_url_for_comparison(website_url)

    if not c_host:
        return False

    # Check if host and path exactly match the website URL
    if f"{c_host}{c_path}" == f"{w_host}{w_path}":
        return False

    # If the candidate path is root/empty
    if c_path in ("", "/"):
        # If the candidate host is identical to website host (or same registrable with no subdomain)
        if c_host == w_host:
            return False
        # If candidate host is just a www variant of website host
        c_reg = get_registrable_domain(c_host)
        w_reg = get_registrable_domain(w_host)
        if c_host == c_reg and w_host == w_reg:
            return False

    return True


def is_same_registrable_domain_or_ats(cand_url: Optional[str], base_url: Optional[str]) -> bool:
    """
    Validates whether cand_url belongs to:
    1. The same registrable root domain as base_url (including any subdomains)
    2. OR any known enterprise ATS domain (Workday, Lever, Greenhouse, etc.)
    """
    if not cand_url or not base_url:
        return False

    c_host, _ = normalize_url_for_comparison(cand_url)
    w_host, _ = normalize_url_for_comparison(base_url)

    if not c_host or not w_host:
        return False

    # Check if registrable domain matches
    c_reg = get_registrable_domain(c_host)
    w_reg = get_registrable_domain(w_host)
    if c_reg and w_reg and c_reg == w_reg:
        return True

    # Check known ATS domains from ats_domains.json / pattern matcher
    if match_ats_pattern(cand_url) is not None:
        return True

    common_ats = (
        "myworkdayjobs.com", "lever.co", "greenhouse.io", "smartrecruiters.com",
        "darwinbox.in", "darwinbox.com", "successfactors.com", "successfactors.eu",
        "oraclecloud.com", "taleo.net", "keka.com", "icims.com", "ashbyhq.com",
        "zohorecruit.com", "zohorecruit.in", "freshteam.com"
    )
    if any(ats in c_host for ats in common_ats):
        return True

    return False


def verify_careers_url_content(html: Optional[str], url: str = "") -> Tuple[bool, float, List[str]]:
    """
    Verifies whether a discovered careers page contains authentic job-like signals:
    1. schema.org/JobPosting in JSON-LD or microdata
    2. Link (<a href>) or iframe (<iframe src>) pointing to a known ATS domain
    3. Repeated job listing card elements (jobCard, job-item, etc.)
    4. Actionable apply/job links ('Apply Now', '/job/12345')

    Returns:
        (has_signals: bool, confidence_score: float, detected_signals: List[str])
    """
    signals: List[str] = []
    if not html or not html.strip():
        return False, 0.1, ["empty_page_content"]

    soup = BeautifulSoup(html, "lxml")

    # 1. JSON-LD JobPosting check
    for s_tag in soup.find_all("script", type="application/ld+json"):
        try:
            content = s_tag.string or ""
            if '"JobPosting"' in content or '"@type":"JobPosting"' in content:
                signals.append("jsonld_job_posting")
                break
        except Exception:
            pass

    # 2. Check ATS links & iframes
    for tag in soup.find_all(["a", "iframe"], src=True) + soup.find_all("a", href=True):
        target = tag.get("src") or tag.get("href") or ""
        if target and match_ats_pattern(target) is not None:
            signals.append(f"ats_reference:{urlparse(target).netloc}")
            break

    # 3. Repeated job listing elements
    cards = soup.find_all(class_=REPEATED_CARD_CLASSES)
    if len(cards) >= 2:
        signals.append(f"repeated_job_cards_count_{len(cards)}")

    # 4. Actionable apply / job links
    apply_links = 0
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = a.get_text(" ", strip=True)
        if JOB_ACTION_PHRASES.search(text) or JOB_URL_PATTERNS.search(href):
            apply_links += 1
            if apply_links >= 2:
                signals.append(f"job_action_links_count_{apply_links}")
                break

    has_signals = len(signals) > 0
    if has_signals:
        confidence = min(0.95, 0.65 + (len(signals) * 0.10))
    else:
        confidence = 0.25

    return has_signals, round(confidence, 2), signals
