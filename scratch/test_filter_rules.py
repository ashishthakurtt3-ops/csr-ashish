import re
from typing import Optional

bad_job_samples = [
    "fraud alert", "fraud alert - global", "Equal Opportunity Policy",
    "Frequently Asked Questions", "Know more about Loans Against Assets",
    "Types of Loan Against Assets", "VIEW ALL", "Download App", "Video Library",
    "Website feedback", "Partnership", "CSR", "Senior Citizen Account Banking comfort",
    "Senior Citizen Premium offerings for y", "Senior Citizen",
    "Mitika Bajpai Deputy General Manager",
    "Mr. Gopikrishna Shenoy Chief Investment Officer",
    "Analyst relations",
    "MyState Limited selects TCS BaNCS™ to transform core banking operations",
    "Boondh: Blending Creativity with Corporate Life",
    "Privacy Policy", "Copyright & Terms", "View our Ads", "Download Forms",
    "Customer Education", "Saved Jobs", "HSBC Championships",
    "Brand Ambassador - Iga Świątek", "Brand Ambassador - Carlos Alcaraz",
    "Leadership", "Our History", "Careers", "Adani Career Site", "Culture",
    "Can’t find what you are looking for?", "Apply at ITC", "Home",
    "Jobs At UltraTech", "Our Values", "Adani Connex Career Site", "Advt.",
    "Advt. No. 08/21", "Cookie Notice", "Privacy Notice",
    "Beware of fraudulent job offers", "Srinagar, Jammu and Kashmir",
    "Pune, Maharashtra", "Mumbai, Maharashtra", "Wipro Locations",
    "+91 8750633334", "LIBERATE to 56161", "Gobally present, regionally supported",
    "Discover your team", "Search for open positions by country",
    "Our Products", "Our Story", "Borrowing And Investment Committee",
    "Property Committee", "Risk Management Committee", "SME Loans",
    "Consumer & Small Enterprise Loans", "Loan Against Property",
    "Explore Opportunities on cummins.jobs", "About Cummins", "Accommodations",
    "jobCategoryLinks", "Would you like to cancel this interview?",
    "Request additional interview slots", "Follow us to know #LifeAtInfy",
    "Hear From Our Employees", "Life At Infy", "Graduates", "DISCOVER MORE",
    "Stay in the loop.", "Launch your career here.", "How we hire.",
    "Everything at Adobe starts with our people.", "Find your team.",
    "Our Purpose Fuels Our Business", "Life at Wipro", "Inclusion and Belonging"
]

good_job_samples = [
    "Assistant - HR", "Senior Customer Executive", "Customer Executive",
    "Trainee - Quality", "Associate", "Sr. Executive - Stores", "Brand Manager",
    "Executive-Sales", "Assistant Manager - Business Development",
    "Senior Cloud Infrastructure Engineer",
    "Full Stack Software Engineer - React & Node.js",
    "Lead Financial Analyst - Corporate Finance", "QA Automation Lead",
    "DevOps Transformation Engineer", "Lab Analyst",
    "Associate Manager - Finance (Audit)",
    "Post of Director (Finance) in NTPC limited",
    "Estágio em Engenharias (Banco de Talentos) – Guarulhos",
    "ID - Rack Lifecycle Tech , Rack Lifecycle Team",
    "SDE II, Global Trade Foundations",
    "Senior Financial Analyst, Customer Service Finance",
    "Case Mgr, MLOA [S], Disability and Leave Services",
    "DCO Tech 3, BOM NORTH - DCO", "CTL-Quick Commerce Last Mile,  GSF Prime Now"
]

bad_csr_samples = [
    "Veterinary professionals provide world",
    "Women empowered through livelihood and entrepreneurial initiatives across programmes*",
    "Corporate CSR Initiative",
    "CSR provisions don't apply to companies whose net worth is not more than ₹500 crore or mor",
    "You may refuse to accept cookies by activating the setter on your browser, which allows yo",
    "We will keep the information we collect about you on our systems or with third parties for",
    "No single organization can create a sustainable future",
    "Business sustainability is linked to the planet’s sustainability",
    "Enhancing access to education, ensuring attendance in local schools and community learning",
    "Waste management is a material topic and a key focus area for L&T due to the volume and ty",
    "Projects range from scholarships, health initiatives, rural education programmes and provi",
    "LIC Golden Jubilee Foundation was established on 20",
    "The impacts of inequality go far beyond income",
    "In a rapidly changing business environment, the need for stable and reliable core operatio",
    "Agentic commerce", "Download",
    "Adani Power Limited (APL) is deeply committed to sustainability and the ecosystem in which",
    "We aim to continuously improve our climate governance",
    "Our Environmental Policy guides environmental management across all sites",
    "Our commitment to the Environment, Social and Governance norms is an inextricable componen",
    "Beyond India, we deliver CSR initiatives across the regions where we operate by focusing o",
    "Driven by a 500+ strong team, HCLFoundation implements flagship programs such as Samuday a",
    "ITC is one of India's foremost private sector companies with a Gross Revenue of ₹ 80,867 c",
    "The world today is confronted with daunting global challenges emerging from the existentia",
    "Our commitment to sustainable and responsible business practices is anchored in a comprehe",
    "We currently reach out to more than 1",
    "At AEL, we are committed to pursuing ESG goals and targets that are aligned with advancing",
    "Sustainability is a strategic focus area for Adani Enterprises Limited",
    "NTPC is India’s largest power conglomerate with roots planted way back in 1975 to accelera",
    "With one of the best environmental policies in the business, the chemicals business follow",
    "To achieve its green goals, the viscose business employs a 360 degree sustainability appro",
    "Work started in 1996 by providing support to an initiative based in Rai Bareilly district ",
    "We understand how to reframe the traditional tech stack of an IT department starting with ",
    "Wipro helps our clients transform business models, decarbonize value chains, and embark on",
    "All efforts are made to execute projects in an environment",
    "At Adani Energy Solutions Limited (AESL), while we are totally and consistently committed ",
    "HMIF provides apprenticeship training to over 2500+ youth at its manufacturing facility in",
    "Motherson is proud to support the principles of the United Nations Global Compact across h",
    "This commitment goes beyond compliance",
    "The information contained in this website is for general information purpose only",
    "mobile device you are using, or the version of the operating system your computer or devic",
    "Torrent Pharma is committed towards “Not just healthcare but lifecare”",
    "The acquisition of Elder Pharma's Indian branded business in 2014, Dermaceutical business ",
    "We endeavour to replace use of fossil fuel",
    "We aim to assess all merchandise vendors on SEDEX SMETA 4 pillar comprising Labour, Health",
    "Research & Development Research & Development on Solar based devices for rural areas and i",
    "Environment & Sustainability Initiative",
    "Cummins continues to extend environmental initiatives across the company’s supply chain",
    "Sustainability Report CY2022", "Sustainability Report for CY2023",
    "The EPD provides transparent, verified data on environmental impact across its lifecycle",
    "Strategic Account Services", "Amazon Business",
    "Outsource your supply chain Get end-to-end supply chain management for multiple sales channels",
    "Sell B2B Connect with business customers",
    "Fulfilled by Merchant (FBM) Get faster, cheaper, and more accurate deliveries",
    "Get product reviews Get high-quality reviews with Amazon Vine",
    "Programs to help you grow", "Technology to Transform",
    "Creativity for All", "Adobe for All"
]

good_csr_samples = [
    "TCS Adult Literacy Programme",
    "TCS BridgeIT Youth Employment Program",
    "Project Shakti (Rural Women Micro-Enterprises)",
    "Hindustan Unilever Foundation Water Conservation Mission",
    "SBI Youth for India Fellowship",
    "ICICI Academy for Skills",
    "Reliance Foundation Health & Nutrition Outreach",
    "Project Nanhi Kali for Girl Child Education",
    "Code Unnati Digital Skilling Initiative",
    "L&T Construction Skills Training Institute (CSTI)",
    "Samuday Village Transformation Initiative",
    "Vidya Vahini Science Laboratories Program",
    "Tata Steel MANSI Maternal and Newborn Health Mission",
    "Bajaj Beyond Skilling Programme",
    "Maruti Suzuki Road Safety Training Institute",
    "NTPC Girl Child Empowerment Mission (GEM)",
    "Project BOOND Water Conservation & Rainwater Harvesting",
    "IndianOil Vidushi Super 30 Coaching for Girls",
    "Satya Bharti School Quality Support Program",
    "Asian Paints Colour Academy",
    "Cipla Palliative Care & Training Centre",
    "Adani Vidya Mandir Initiative"
]

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
    'engineer', 'engineering', 'developer', 'programmer', 'coder', 'architect',
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
    'tech', 'mgr', 'ctl', 'lead', 'leader'
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
        # If junk is a multi-word phrase like "privacy policy" or "frequently asked questions"
        if len(junk.split()) >= 2 and (junk in t_lower) and not any(r in t_lower for r in ['engineer', 'developer', 'manager', 'lead', 'analyst', 'consultant', 'officer', 'associate', 'executive', 'director']):
            return False

    # 3. Reject personal names with salutations or executive quotes (e.g., "Mitika Bajpai Deputy General Manager", "Mr. Gopikrishna Shenoy...")
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

    # 7. Reject press releases, deal wins, sponsorships, brand ambassadors
    if re.search(r'\b(selects\b.*to transform|wins contract|announces financial|reports q[1-4]|signs mou|partners with|brand ambassador|championships|selects tcs)\b', t_lower):
        return False

    # 8. Reject action prompts & UI forms
    if re.search(r'\b(would you like to cancel|cancel this interview|request additional|interview slots?|jobcategorylinks|saved jobs|can’t find|cant find|stay in the loop|launch your career|how we hire|everything at|find your team|our purpose|our values|our story|our history|our products|culture at|life at|inclusion and belonging)\b', t_lower):
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


print("\n--- TESTING BAD JOBS ---")
bad_job_accepted = [j for j in bad_job_samples if is_valid_job_title(j)]
print(f"Bad jobs accepted (should be 0): {len(bad_job_accepted)}")
if bad_job_accepted:
    print("ACCEPTED BAD JOBS:", bad_job_accepted)

print("\n--- TESTING GOOD JOBS ---")
good_job_rejected = [j for j in good_job_samples if not is_valid_job_title(j)]
print(f"Good jobs rejected (should be 0): {len(good_job_rejected)}")
if good_job_rejected:
    print("REJECTED GOOD JOBS:", good_job_rejected)

print("\n--- TESTING BAD CSR ---")
bad_csr_accepted = [c for c in bad_csr_samples if is_valid_csr_project(c)]
print(f"Bad CSR accepted (should be 0): {len(bad_csr_accepted)}")
if bad_csr_accepted:
    print("ACCEPTED BAD CSR:", bad_csr_accepted)

print("\n--- TESTING GOOD CSR ---")
good_csr_rejected = [c for c in good_csr_samples if not is_valid_csr_project(c)]
print(f"Good CSR rejected (should be 0): {len(good_csr_rejected)}")
if good_csr_rejected:
    print("REJECTED GOOD CSR:", good_csr_rejected)
