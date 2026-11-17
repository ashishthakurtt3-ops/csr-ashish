"""
modules/crawler_engine/discovery_helpers.py
===========================================
Pure-Python helper functions for deep link validation, registrable domain
equivalence, and careers page content verification (Stage 1).
"""
import re
import json
import urllib.parse
from urllib.parse import urlparse, urljoin
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

DOCUMENT_ASSET_EXTENSIONS = (
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'
)

STATIC_ASSET_EXTENSIONS = (
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico',
    '.zip', '.tar', '.gz', '.css', '.js', '.mp4', '.mp3',
    '.woff', '.woff2', '.ttf', '.eot'
)

def is_document_asset_url(url: Optional[str]) -> bool:
    """
    Checks if a URL points to a document asset (.pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx)
    rather than static media/code or web pages.
    Statutory Section 135 CSR reports and BRSR disclosures are frequently published as PDFs.
    """
    if not url:
        return False
    u_lower = str(url).lower().strip()
    parsed = urlparse(u_lower)
    path = parsed.path
    for ext in DOCUMENT_ASSET_EXTENSIONS:
        if path.endswith(ext) or u_lower.endswith(ext):
            return True
        if f"{ext}?" in u_lower or f"{ext}&" in u_lower or f"{ext}#" in u_lower:
            return True
    return False

def is_static_asset_url(url: Optional[str]) -> bool:
    """
    Determines if a URL points to a non-content static asset (images, fonts, scripts, styles, archives).
    Ensures that document assets (like PDFs, Word, Excel files) are NOT treated as static noise.
    """
    if not url:
        return True
    # Statutory Section 135 CSR reports and BRSR PDFs must never be dropped as static noise
    if is_document_asset_url(url):
        return False
    u_lower = str(url).lower().strip()
    parsed = urlparse(u_lower)
    path = parsed.path
    if any(path.endswith(ext) for ext in STATIC_ASSET_EXTENSIONS):
        return True
    if any(f"{ext}?" in u_lower for ext in STATIC_ASSET_EXTENSIONS):
        return True
    if any(k in u_lower for k in ['/assets/images/', '/static/media/', '/banner/']):
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
    'mgr', 'partner', 'president', 'chief', 'physician', 'doctor', 'nurse', 'pharmacist'
}

JOB_DISCIPLINE_WORDS = {
    'senior', 'junior', 'lead', 'principal', 'staff', 'chief', 'associate', 'assistant', 'deputy',
    'field', 'service', 'services', 'project', 'projects', 'product', 'products', 'program', 'programs',
    'plant', 'branch', 'store', 'sales', 'marketing', 'finance', 'financial', 'account', 'accounts',
    'operations', 'operation', 'operational', 'supply', 'chain', 'human', 'resources', 'hr', 'talent',
    'client', 'clients', 'customer', 'customers', 'technical', 'technology', 'tech', 'general', 'regional',
    'area', 'zonal', 'global', 'business', 'quality', 'safety', 'security', 'risk', 'compliance',
    'credit', 'legal', 'digital', 'data', 'cloud', 'software', 'hardware', 'network', 'systems', 'system',
    'site', 'civil', 'mechanical', 'electrical', 'chemical', 'mining', 'production', 'maintenance',
    'logistics', 'procurement', 'warehouse', 'inventory', 'shift', 'line', 'unit', 'office', 'portfolio',
    'asset', 'wealth', 'relationship', 'audit', 'tax', 'treasury', 'underwriting', 'claims', 'medical',
    'clinical', 'research', 'lab', 'testing', 'facilities', 'environmental', 'sustainability', 'brand',
    'content', 'media', 'public', 'community', 'strategy', 'strategic', 'transformation', 'innovation',
    'design', 'devops', 'infrastructure', 'automation', 'it', 'ai', 'ml', 'bi', 'erp', 'crm', 'sap',
    'commercial', 'corporate', 'group', 'executive', 'division', 'enterprise', 'growth',
    'manufacturing', 'engineering', 'development', 'solutions', 'delivery', 'consulting', 'advisory',
    'continuous', 'improvement'
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
    if re.match(r'^(mr|ms|mrs|dr|prof|shri|smt)\.?\s+[a-z]+', t, re.IGNORECASE):
        return False
    if re.search(r'\b(says|said|shares|shared|speaks|spoke|testimonial|quote)\b', t_lower):
        return False
    words = t_clean.split()
    if len(words) >= 3 and re.match(r'^[A-Z][a-z]+\s+[A-Z][a-z]+\s+(Deputy General Manager|General Manager|Chief|Director|Officer|Lead|Leader|Manager)', t):
        w0 = words[0].lower()
        w1 = words[1].lower()
        if w0 not in JOB_DISCIPLINE_WORDS and w1 not in JOB_DISCIPLINE_WORDS:
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

    # 8b. Reject call-to-action headings that mention roles but are not a job
    # title, e.g. "Apply for Developer and Lead roles across the opportunities below:".
    if re.match(
        r'^(apply|register|join|submit|view|see|explore|discover|browse|search)\b'
        r'.*\b(roles?|jobs?|positions?|openings?|opportunities|careers?|below)\b',
        t_lower,
    ):
        return False
    if re.search(r'\b(opportunities|roles|positions|openings|jobs)\s+below\b', t_lower):
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
    'sanitation', 'water', 'literacy', 'education', 'rural', 'livelihood', 'livelihoods', 'afforestation',
    'biodiversity', 'scholarship', 'development', 'skill', 'skills', 'skilling', 'hospital',
    'relief', 'empower', 'empowerment', 'swachh', 'anganwadi', 'vidya', 'arogya',
    'society', 'drive', 'conservation', 'nutrition', 'tree plantation', 'watershed',
    'clean energy', 'disaster', 'shelter', 'blood donation', 'caregiving', 'robot sanitation',
    'code unnati', 'sabbatical', 'bridge it', 'ignite my future', 'goit', 'jyoti',
    'vasundhara', 'vidyaadhanam', 'sparsh', 'upbridge', 'shwet', 'social', 'parivartan',
    'nanhi kali', 'samuday', 'mansi', 'bajaj beyond', 'boond', 'vidushi', 'satya bharti',
    'colour academy', 'palliative care', 'vidya mandir', 'academy', 'institute', 'training', 'road safety',
    'skillsbuild', 'impact accelerator', 'call for code', 'ai for good', 'accelerator', 'philanthropies',
    'community impact', 'sustainability initiative', 'climate', 'net zero', 'grant', 'giving', 'stewardship',
    'fellows', 'stem', 'digital literacy', 'green', 'electrification', 'forestry', 'rainwater', 'harvesting', 'meal',
    'sustainability', 'environmental', 'learning', 'sport', 'sports', 'culture', 'heritage', 'destitute', 'welfare',
    'hygiene', 'hunger', 'poverty', 'renewable', 'solar', 'gender equality'
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
    'microsoft': 'https://jobs.careers.microsoft.com/global/en/search?lc=India',
    'reliance': 'https://careers.ril.com/rilcareers/frmjobsearch.Aspx',
    'ril': 'https://careers.ril.com/rilcareers/frmjobsearch.Aspx',
    'samsung': 'https://sec.wd3.myworkdayjobs.com/Samsung_Careers',
    'amazon': 'https://amazon.jobs/en/search?country=IND',
    'google': 'https://www.google.com/about/careers/applications/jobs/results/?location=India',
    'hcl': 'https://careers.hcltech.com/',
    'hcltech': 'https://careers.hcltech.com/',
    'wipro': 'https://careers.wipro.com/search',
    'icici': 'https://www.icicicareers.com/CareerApplicant/Career/SearchJob',
    'hdfc': 'https://hdfcbank.taleo.net/careersection/ex/jobsearch.ftl',
    'accenture': 'https://www.accenture.com/in-en/careers',
    'cognizant': 'https://careers.cognizant.com/global/en',
    'larsen': 'https://www.larsentoubro.com/corporate/careers/',
    'l&t': 'https://www.larsentoubro.com/corporate/careers/',
    'tata motors': 'https://careers.tatamotors.com/go/View-All-Opportunities/3505801/',
    'tata steel': 'https://www.tatasteel.com/careers/',
    'maruti': 'https://maruti.app.param.ai/jobs/',
    'maruti suzuki': 'https://maruti.app.param.ai/jobs/',
    'ibm': 'https://www.ibm.com/careers/search?q=India',
    'adobe': 'https://careers.adobe.com/us/en/search-results?qcountry=India',
    'sap': 'https://jobs.sap.com/',
    'pfizer': 'https://pfizer.wd1.myworkdayjobs.com/PfizerCareers',
    'jpmorgan': 'https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=India',
    'jpmc': 'https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=India',
    'hsbc': 'https://mycareer.hsbc.com/en_GB/external',
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
    'ntpc': 'https://www.ntpc.co.in/jobs-ntpc',
    'ongc': 'https://ongcindia.com/web/eng/career',
    'power grid': 'https://www.powergrid.in/careers',
    'coal india': 'https://www.coalindia.in/career-cil/',
    'bharat petroleum': 'https://www.bharatpetroleum.in/careers/',
    'bpcl': 'https://www.bharatpetroleum.in/careers/',
    'indian oil': 'https://iocl.com/latest-job-opening',
    'iocl': 'https://iocl.com/latest-job-opening',
    'hindustan unilever': 'https://www.hul.co.in/careers/',
    'hul': 'https://www.hul.co.in/careers/',
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
    'varun beverages': 'https://www.varunbeverages.com/careers',
    'ciklum': 'https://explore-jobs.ciklum.com/en/sites/ciklum-career/jobs',
    'happiest minds': 'https://jobs.happiestminds.com/happiestminds/',
    'ltimindtree': 'https://careers.ltm.com/search/',
    'ltm': 'https://careers.ltm.com/search/',
}

ENTERPRISE_CSR_REGISTRY = {
    'happiest minds': 'https://www.happiestminds.com/investors/esg',
    'tata consultancy': 'https://www.tcs.com/corporate-social-responsibility',
    'tcs': 'https://www.tcs.com/corporate-social-responsibility',
    'infosys': 'https://www.infosys.com/infosys-foundation/initiatives.html',
    'reliance': 'https://www.ril.com/about/corporate-social-responsibility',
    'ril': 'https://www.ril.com/about/corporate-social-responsibility',
    'maruti': 'https://www.marutisuzuki.com/corporate/investors/company-updates',
    'maruti suzuki': 'https://www.marutisuzuki.com/corporate/investors/company-updates',
    'hdfc': 'https://www.hdfcbank.com/personal/about-us/corporate-social-responsibility',
    'accenture': 'https://www.accenture.com/en/about/corporate-sustainability',
    'icici': 'https://www.icicifoundation.org/',
    'wipro': 'https://wiprofoundation.org/',
    'hcl': 'https://www.hcltech.com/sustainability',
    'larsen': 'https://www.larsentoubro.com/corporate/sustainability/',
    'l&t': 'https://www.larsentoubro.com/corporate/sustainability/',
    'tata motors': 'https://www.tatamotors.com/corporate-responsibility/planet-resilience/',
    'tata steel': 'https://www.tatasteel.com/sustainability/',
    'sap': 'https://www.sap.com/corporate/en/company/sustainability-csr.html',
    'amazon': 'https://www.aboutamazon.in/impact/community/csr-policy',
    'microsoft': 'https://www.microsoft.com/en-in/about/csr',
    'google': 'https://www.google.org/',
    'ibm': 'https://www.ibm.com/impact',
    'adobe': 'https://www.adobe.com/corporate-responsibility.html',
    'mahindra': 'https://www.mahindra.com/sustainability',
    'itc': 'https://www.itcportal.com/sustainability/',
    'asian paints': 'https://www.asianpaints.com/more/csr.html',
    'sun pharma': 'https://sunpharma.com/csr/',
    'bajaj': 'https://www.bajajbeyond.com/',
    'airtel': 'https://www.bhartifoundation.org/',
    'bharti': 'https://www.bhartifoundation.org/',
    'ultratech': 'https://www.ultratechcement.com/corporate/sustainability/sustainability',
    'jsw': 'https://www.jsw.in/foundation',
    'adani': 'https://www.adanifoundation.org/',
    'tech mahindra': 'https://techmahindrafoundation.org/',
    'dr. reddy': 'https://www.drreddysfoundation.org/',
    'cipla': 'https://www.ciplafoundation.org/',
    'pfizer': 'https://www.pfizer.com/about/responsibility',
    'jpmorgan': 'https://www.jpmorganchase.com/impact',
    'jpmc': 'https://www.jpmorganchase.com/impact',
    'hsbc': 'https://www.hsbc.com/who-we-are/hsbc-and-sustainability',
    'samsung': 'https://www.samsung.com/in/sustainability/environment/',
    'hcltech': 'https://www.hcltech.com/sustainability',
    'ltimindtree': 'https://www.ltm.com/uploads/report/csr-annual-plan-2025-26.pdf',
    'ltm': 'https://www.ltm.com/uploads/report/csr-annual-plan-2025-26.pdf'
}

def get_registrable_domain(url_or_host: Optional[str]) -> str:
    """
    Extracts the base registrable domain (eTLD+1) from a host or URL.
    Examples:
      - 'careers.tatamotors.com' -> 'tatamotors.com'
      - 'www.sbi.co.in' -> 'sbi.co.in'
      - 'new.abb.com' -> 'abb.com'
      - 'https://sec.wd3.myworkdayjobs.com/Samsung_Careers' -> 'myworkdayjobs.com'
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

    # Check two-part ccTLDs e.g. .co.in, .org.in, .co.uk
    last_two = ".".join(parts[-2:])
    if last_two in _KNOWN_TWO_PART_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])

    return ".".join(parts[-2:])


ALLOWED_ATS_HOSTS = {
    'myworkdayjobs.com',
    'oraclecloud.com',
    'successfactors.com',
    'successfactors.eu',
    'greenhouse.io',
    'lever.co',
    'smartrecruiters.com',
    'ashbyhq.com',
    'icims.com',
    'taleo.net',
    'param.ai',
    'ripplehire.com',
    'darwinbox.in',
    'darwinbox.com',
    'peoplestrong.com',
    'phenompeople.com',
    'phenom.com',
    'keka.com',
    'zohorecruit.com',
    'zohorecruit.in',
    'freshteam.com',
    'naukri.com',
    'zwayam.com',
    'jobs.happiestminds.com',
    # Enterprise-specific ATS (synced from crawler.py ATS_DOMAINS)
    'mahindracareers.com',
    'tatamotorscareers.com',
    'tcscareers.com',
    # Additional common ATS platforms
    'jobvite.com',
    'brassring.com',
    'kenexa.com',
    'ultipro.com',
    'paylocity.com',
    'bamboohr.com',
    'recruitee.com',
    'teamtailor.com',
    'careers.hirequest.com',
    'hire.withgoogle.com',
    'apply.workable.com',
    'jobs.jobvite.com',
}

# 2- and 3-character enterprise roots
SHORT_ENTERPRISE_ROOTS = {
    'itc', 'tcs', 'ril', 'sbi', 'ibm', 'abb', 'pnb', 'hcl', 'ge', 'bp', 'ey', 'ltm'
}

# Approved corporate foundations and CSR initiative portals
APPROVED_FOUNDATION_DOMAINS = {
    'tatatrusts.org', 'reliancefoundation.org', 'azimpremjifoundation.org',
    'infosysprize.org', 'infosys.org', 'infosysfoundation.org',
    'adlsfoundation.org', 'adanifoundation.org', 'bhartifoundation.org',
    'techmahindrafoundation.org', 'drreddysfoundation.org', 'ciplafoundation.org',
    'bajajbeyond.com', 'itcportal.com', 'hclfoundation.org', 'wiprofoundation.org',
    'sbifoundation.co.in', 'piramal.com', 'jsw.in', 'vedantafoundation.org',
    'lntfoundation.org', 'tatasteel.com'
}

ENTERPRISE_DOMAIN_ALIASES = {
    'ril': {'reliance', 'reliancefoundation'},
    'reliance': {'ril', 'reliancefoundation'},
    'tcs': {'tata', 'tatatrusts', 'tcscareers'},
    'tcscareers': {'tcs', 'tata', 'tatatrusts'},
    'tata': {'tcs', 'tatatrusts', 'tatamotors', 'tatasteel', 'tatapower', 'tcscareers'},
    'sbi': {'statebank', 'sbifoundation'},
    'pnb': {'punjabnationalbank', 'pnbfoundation'},
    'hcl': {'hcltech', 'hclfoundation'},
    'itc': {'itcportal'},
    'infy': {'infosys', 'infosysfoundation', 'infosysprize'},
    'infosys': {'infy', 'infosysfoundation', 'infosysprize'},
    'wipro': {'azimpremji', 'azimpremjifoundation', 'wiprofoundation'},
    'azimpremji': {'wipro', 'azimpremjifoundation', 'wiprofoundation'},
    'adani': {'adanifoundation'},
    'bharti': {'airtel', 'bhartifoundation'},
    'airtel': {'bharti', 'bhartifoundation'},
    'mahindra': {'techmahindra', 'techmahindrafoundation', 'mahindracareers'},
    'mahindracareers': {'mahindra', 'techmahindra'},
    'techmahindra': {'mahindra', 'techmahindrafoundation'},
    'tatamotors': {'tata', 'tatatrusts', 'tatamotorscareers'},
    'tatamotorscareers': {'tatamotors', 'tata'},
    'lnt': {'larsentoubro', 'lntfoundation'},
    'larsentoubro': {'lnt', 'lntfoundation'},
    'bajaj': {'bajajbeyond', 'bajajauto', 'bajajfinserv'},
    'bajajauto': {'bajaj', 'bajajbeyond'},
    'bajajbeyond': {'bajaj', 'bajajauto', 'bajajfinserv'},
    'ltimindtree': {'ltm', 'mindtree', 'lnt', 'larsentoubro'},
    'ltm': {'ltimindtree', 'mindtree', 'lnt', 'larsentoubro'},
    'mindtree': {'ltimindtree', 'ltm', 'lnt', 'larsentoubro'},
}


def is_allowed_domain_or_ats(target_url: str, company_domain_or_url: str) -> bool:
    """
    Validates whether a URL belongs to the company's registrable domain, a known subdomain,
    an approved third-party enterprise ATS host, an approved corporate foundation / CSR domain,
    or a common brand root domain match (supporting 2- and 3-letter enterprise roots).
    """
    if not target_url:
        return False
    target_reg = get_registrable_domain(target_url)
    company_reg = get_registrable_domain(company_domain_or_url)
    if not target_reg:
        return False
    if company_reg and target_reg == company_reg:
        return True
    if any(target_reg == ats or target_reg.endswith("." + ats) for ats in ALLOWED_ATS_HOSTS):
        return True

    # Check approved corporate foundation / CSR domains
    if target_reg in APPROVED_FOUNDATION_DOMAINS:
        if not company_reg:
            return True
        c_root = company_reg.split('.')[0].lower()
        t_root = target_reg.split('.')[0].lower()
        if c_root in t_root or t_root in c_root:
            return True
        aliases = ENTERPRISE_DOMAIN_ALIASES.get(c_root, set())
        if any(alias in t_root for alias in aliases):
            return True
        return False

    if company_reg and target_reg:
        c_root = company_reg.split('.')[0].lower()
        t_root = target_reg.split('.')[0].lower()

        # Exact root match e.g. tata.com and tata.in
        if c_root == t_root:
            return True

        # Enterprise careers / jobs / foundation composite domains
        # e.g. gecareers.com for ge.com, adlsfoundation.org for adls.com, tcscareers.com for tcs.com
        if t_root.startswith(c_root) and any(t_root == f"{c_root}{suffix}" for suffix in ('careers', 'jobs', 'foundation', 'trusts', 'portal')):
            return True
        if c_root.startswith(t_root) and any(c_root == f"{t_root}{suffix}" for suffix in ('careers', 'jobs', 'foundation', 'trusts', 'portal')):
            return True

        # Check enterprise domain aliases
        if c_root in ENTERPRISE_DOMAIN_ALIASES:
            if any(alias in t_root for alias in ENTERPRISE_DOMAIN_ALIASES[c_root]):
                return True
        if t_root in ENTERPRISE_DOMAIN_ALIASES:
            if any(alias in c_root for alias in ENTERPRISE_DOMAIN_ALIASES[t_root]):
                return True

        # Strict default: unrelated registrable roots are rejected.  Group/subsidiary
        # domains must be covered by ENTERPRISE_DOMAIN_ALIASES or the approved
        # foundation list above rather than loose substring matching, which would
        # accept lookalike domains such as "tcs-fake-jobs.com" for "tcs.com".

    return False


def derive_deep_job_url(careers_url: str, comp_name: str, job_title: str, existing_url: str = "", req_id: str = "") -> str:
    """
    Constructs an authentic, working application URL for a job vacancy.
    STRICT RULES:
    1. Returns ONLY URLs actually found in the DOM, an API response, or JSON-LD.
    2. NEVER falls back to the careers-portal landing page, homepage, or search links.
    3. If no authentic job-level URL exists, returns empty string so the validator can drop it.
    """
    comp_lower = comp_name.strip().lower()

    # 1. If an authentic, working direct application/requisition URL was genuinely provided or discovered:
    if existing_url and str(existing_url).startswith(('http://', 'https://')):
        u_str = str(existing_url).strip()
        if not is_static_asset_url(u_str):
            clean_u = re.sub(r'([?&])(utm_[^&]+|fbclid=[^&]+|ref=[^&]+)', '', u_str).rstrip('&?')
            clean_u = re.sub(r'#job-[A-F0-9]{4,16}$', '', clean_u, flags=re.IGNORECASE)
            clean_u = re.sub(r'#:~:text=.*$', '', clean_u, flags=re.IGNORECASE)

            # Strictly reject candidate login walls, account signin portals, session walls, and non-job corporate pages
            if any(bad in clean_u.lower() for bad in [
                '/candidate/?', '/candidate/', 'candidate.tcsapps.com', 'ibegin.tcsapps.com/candidate',
                'signin', 'auth/login', 'accounts.google', 'login.microsoftonline',
                '/policy-positions', '/programs-policies', '/about-us', '/who-we-are',
                '/investor', '/fixed-income', '/press-releases', '/culture', '/media',
                '/contact-us', '/terms', '/privacy', 'sustainability-and-technology',
                '/news/', '/notice', '/fraudulent', '/our-people', '/diversity', '/equal-opportunities',
                'business-opportunit', 'equal-opportunit'
            ]):
                return ""
            
            # Reject bare landing pages masquerading as direct apply links
            parsed_u = urlparse(clean_u)
            clean_path = parsed_u.path.strip('/').lower()
            if clean_path in ('', 'careers', 'career', 'jobs', 'job', 'home', 'corporate/careers', 'about/careers'):
                return ""

            if any(k in u_str.lower() for k in [
                '/job/', 'jobid=', 'jobreferencecode=', '/jobs/', '/apply', 'req=', 'id=',
                'frmjobsearch.aspx', 'workdayjobs.com', 'amazon.jobs', 'lever.co',
                'greenhouse.io', 'smartrecruiters.com', 'darwinbox', 'peoplestrong.com',
                'taleo.net', 'oraclecloud.com', 'successfactors', 'param.ai'
            ]):
                return clean_u
            elif clean_u:
                if any(k in clean_path for k in ['opening', 'vacancy', 'detail', 'position', 'role']):
                    return clean_u

    # 2. If requisition ID is present, construct authentic deep ATS link ONLY for platforms with verified direct ID routes:
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
            if 'jpmorgan' in comp_lower or 'jpmc' in comp_lower:
                return f"https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/{req_clean}"

    # ZERO FALLBACK RULE: Never guess, never assign careers portal URL, never assign homepage
    return ""


def resolve_authentic_csr_url(csr_url: str, comp_name: str, project_name: str = "") -> str:
    """
    Constructs an authentic, verified Section 135 CSR portal URL.
    Preserves deep initiative pages and rejects non-CSR pages.
    """
    if csr_url and str(csr_url).startswith(('http://', 'https://')):
        c_clean = str(csr_url).strip()
        c_clean = re.sub(r'#:~:text=.*$', '', c_clean, flags=re.IGNORECASE)
        if not is_static_asset_url(c_clean):
            # Block invalid or blacklist pages
            if any(b in c_clean.lower() for b in ['404', 'notfound', 'accessdenied', 'signin', 'login']):
                return ""
            return re.sub(r'([?&])(utm_[^&]+|fbclid=[^&]+|ref=[^&]+)', '', c_clean).rstrip('&?/')

    # Check enterprise CSR registry for authoritative foundation/CSR portal
    comp_lower = comp_name.strip().lower()
    for k, portal in ENTERPRISE_CSR_REGISTRY.items():
        if k in comp_lower:
            return portal

    return ""

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


# ==============================================================================
# FAST HOMEPAGE INTELLIGENCE (Stage 1 Pipeline Accelerator)
# ==============================================================================

_HOMEPAGE_INTEL_CACHE: Dict[str, Dict[str, Any]] = {}


def fast_homepage_intelligence(url: str, session_cache: Optional[dict] = None) -> dict:
    """
    Extracts fast homepage and sitemap intelligence:
    {canonical_url, domain, nav_links: list, footer_links: list, sitemaps: list, detected_ats: Optional[str], ats_url: Optional[str]}
    Uses in-memory session and global caching, bounded concurrency, and TLS-impersonated fetch.
    """
    empty_result = {
        "canonical_url": "",
        "domain": "",
        "nav_links": [],
        "footer_links": [],
        "sitemaps": [],
        "detected_ats": None,
        "ats_url": None,
    }
    if not url:
        return empty_result

    clean_u = url.strip()
    if session_cache is not None and clean_u in session_cache:
        return session_cache[clean_u]
    if clean_u in _HOMEPAGE_INTEL_CACHE:
        return _HOMEPAGE_INTEL_CACHE[clean_u]

    fetch_url = clean_u if clean_u.startswith(("http://", "https://")) else f"https://{clean_u}"
    html = ""
    final_url = fetch_url

    try:
        from curl_cffi import requests as cffi_req
        resp = cffi_req.get(
            fetch_url,
            impersonate="chrome124",
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}
        )
        if resp.status_code == 200:
            final_url = str(resp.url)
            html = resp.text or ""
    except Exception:
        try:
            import urllib.request
            import ssl
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(
                fetch_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}
            )
            with urllib.request.urlopen(req, timeout=8, context=ctx) as u_resp:
                html = u_resp.read().decode("utf-8", errors="ignore")
                final_url = u_resp.geturl() or fetch_url
        except Exception:
            pass

    domain = get_registrable_domain(final_url or fetch_url)
    canonical_url = final_url

    nav_links: List[Dict[str, str]] = []
    footer_links: List[Dict[str, str]] = []
    sitemaps: List[str] = []
    detected_ats: Optional[str] = None
    ats_url: Optional[str] = None

    if html:
        soup = BeautifulSoup(html, "lxml")

        # Canonical tag
        can_tag = soup.find("link", rel=lambda r: r and "canonical" in r.lower())
        if can_tag and can_tag.get("href"):
            href_can = can_tag["href"].strip()
            if href_can.startswith("http"):
                canonical_url = href_can
            else:
                canonical_url = urljoin(final_url, href_can)

        # Nav links
        seen_nav = set()
        nav_containers = soup.find_all(["nav", "header"])
        if not nav_containers:
            nav_containers = soup.find_all(class_=re.compile(r'nav|menu|header', re.I))[:3]
        for c in nav_containers:
            for a in c.find_all("a", href=True):
                href = a.get("href", "").strip()
                text = a.get_text(" ", strip=True)
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                full_href = urljoin(canonical_url, href)
                if full_href not in seen_nav and not is_static_asset_url(full_href):
                    seen_nav.add(full_href)
                    nav_links.append({"text": text, "url": full_href})
                    if len(nav_links) >= 50:
                        break
            if len(nav_links) >= 50:
                break

        # Footer links
        seen_footer = set()
        footer_containers = soup.find_all("footer")
        if not footer_containers:
            footer_containers = soup.find_all(class_=re.compile(r'footer|bottom', re.I))[:2]
        for c in footer_containers:
            for a in c.find_all("a", href=True):
                href = a.get("href", "").strip()
                text = a.get_text(" ", strip=True)
                if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                full_href = urljoin(canonical_url, href)
                if full_href not in seen_footer and not is_static_asset_url(full_href):
                    seen_footer.add(full_href)
                    footer_links.append({"text": text, "url": full_href})
                    if len(footer_links) >= 50:
                        break
            if len(footer_links) >= 50:
                break

        # ATS detection on HTML and links
        # 1. Workday
        wd_match = re.search(r'https?://([a-zA-Z0-9_\-\.]+\.myworkdayjobs\.com/[^"\'<>\s]+)', html, re.I)
        if wd_match:
            detected_ats = "workday"
            ats_url = wd_match.group(0).rstrip('"\')')
        elif ".myworkdayjobs.com" in html:
            detected_ats = "workday"
            m = re.search(r'([a-zA-Z0-9_\-]+\.myworkdayjobs\.com)', html, re.I)
            if m:
                ats_url = f"https://{m.group(1)}"

        # 2. Greenhouse
        if not detected_ats:
            gh_for = re.search(r'boards\.greenhouse\.io.*?[\?&]for=([a-zA-Z0-9_\-]+)', html, re.I)
            if gh_for:
                detected_ats = "greenhouse"
                ats_url = f"https://boards.greenhouse.io/{gh_for.group(1)}"
            else:
                gh_match = re.search(r'https?://boards\.greenhouse\.io/([a-zA-Z0-9_\-]+)', html, re.I)
                if gh_match and gh_match.group(1).lower() not in ('embed', 'js', 'api'):
                    detected_ats = "greenhouse"
                    ats_url = f"https://boards.greenhouse.io/{gh_match.group(1)}"

        # 3. Lever
        if not detected_ats:
            lev_match = re.search(r'https?://jobs\.lever\.co/([a-zA-Z0-9_\-]+)', html, re.I)
            if lev_match:
                detected_ats = "lever"
                ats_url = f"https://jobs.lever.co/{lev_match.group(1)}"

        # 4. SmartRecruiters
        if not detected_ats:
            sr_match = re.search(r'https?://(?:careers|jobs|www)?\.smartrecruiters\.com/([a-zA-Z0-9_\-]+)', html, re.I)
            if sr_match:
                detected_ats = "smartrecruiters"
                ats_url = sr_match.group(0)

        # 5. SuccessFactors
        if not detected_ats:
            sf_match = re.search(r'https?://[a-zA-Z0-9_\-\.]*successfactors\.[a-z]+/[^"\'<>\s]+', html, re.I)
            if sf_match:
                detected_ats = "successfactors"
                ats_url = sf_match.group(0).rstrip('"\')')

        # 6. Darwinbox
        if not detected_ats:
            db_match = re.search(r'https?://([a-zA-Z0-9_\-]+)\.darwinbox\.(?:in|com)/?[^"\'<>\s]*', html, re.I)
            if db_match:
                detected_ats = "darwinbox"
                ats_url = db_match.group(0).rstrip('"\')')

    # Bounded concurrency sitemap discovery
    parsed_base = urlparse(canonical_url or fetch_url)
    if parsed_base.netloc:
        base_root = f"{parsed_base.scheme}://{parsed_base.netloc}"
        cand_sitemaps = [
            f"{base_root}/sitemap.xml",
            f"{base_root}/sitemap_index.xml",
        ]

        import concurrent.futures

        def check_sm(sm_url: str) -> Optional[str]:
            try:
                from curl_cffi import requests as cffi_req
                s_resp = cffi_req.get(sm_url, impersonate="chrome124", timeout=3)
                if s_resp.status_code == 200 and len(s_resp.text or "") > 50:
                    return sm_url
            except Exception:
                pass
            return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(check_sm, sm) for sm in cand_sitemaps[:3]]
            for f in concurrent.futures.as_completed(futures):
                res = f.result()
                if res and res not in sitemaps:
                    sitemaps.append(res)

    result = {
        "canonical_url": canonical_url,
        "domain": domain,
        "nav_links": nav_links,
        "footer_links": footer_links,
        "sitemaps": sitemaps,
        "detected_ats": detected_ats,
        "ats_url": ats_url,
    }

    if session_cache is not None:
        session_cache[clean_u] = result
    if len(_HOMEPAGE_INTEL_CACHE) > 500:
        _HOMEPAGE_INTEL_CACHE.clear()
    _HOMEPAGE_INTEL_CACHE[clean_u] = result
    return result

