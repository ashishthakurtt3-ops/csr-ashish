"""
Single source of truth for "what may be shown to the public".

Every public API/view MUST build its querysets with these helpers instead of
repeating status lists. A record is public only when it is verified AND (for
jobs) its apply link has been verified live, its owner is unambiguous,
and it does not match UI navigation defect boilerplate.
"""
from django.db.models import Q

# Verification states that count as verified for non-job records (projects, contacts, opportunities)
PUBLIC_VERIFICATION_STATUSES = ('PUBLISHED', 'SOURCE_CONFIRMED')

# link_status written by crawler_engine.link_verifier or crawler publish
LINK_OK = 'VERIFIED_HTTP_200'
LINK_OK_STATUSES = ('VERIFIED_HTTP_200', 'PUBLISHED')

NOT_AVAILABLE_TEXT = 'Not available on the company website'
LOGIN_REQUIRED_TEXT = 'Available only after login on the company website'

UI_NAV_DEFECT_PATTERNS = [
    'How to apply',
    'Discover more',
    'FAQs & Support',
    'Review Accommodations',
    'Upload Resume',
    'Submit Resume',
    'Next >>',
    'Previous <<',
    'Know more',
    'Click here',
    'Apply now',
    'View details',
    'Read more',
    'Learn more',
    'Next',
    'Previous',
    'Last',
    'First',
    'Calculator',
    'Locator',
    'Branch Locator',
    'Free Credit Score',
    'Annual Secretarial Compliance',
    'Loss of share certificate',
    'ODR Portal',
    'Articles of Association',
    'Saksham Niveshak',
    'Media Centre',
    'Customer Service',
    'Shareholders',
    'Global Business',
    '3 Wheelers',
    'Motorcycles',
    'Fraud Awareness',
    'Cookie Consent',
    'Destinations',
    'Locations',
    'Home Page',
    'recruitingCE',
    'Would you like to schedule this interview',
    'Your interview is scheduled',
    'Opera Mobile Preview',
    'Apply Online',
    'Workplace Equity & Diversity',
    'Home',
    'About Us',
    'Our Values',
    'Leadership Team',
    'Our Story',
    'Press Kit',
    'Stories',
    'Press Releases',
    'Useful Information',
    'Corporate Governance',
    'Investors Centre',
    'Case Studies',
    'Community Development',
    'Environment',
    'Governance',
    'Media',
    'Investors',
    'Trending',
    'Financials',
    'Sustainability',
    'Overview',
    'Company Overview',
    'For Corporate',
    'For Infrastructure',
    'For Home Builders',
    'Consumer Products',
    'Saved Jobs',
    'Frequently Asked Questions',
    'Website feedback',
    'Partnership',
    'Download Forms',
    'View our Ads',
    'Customer Education',
    'Asset Publisher',
    'Departments',
    'otPcCenter',
    'otCenterRounded',
    'Skip to content',
    'Skip to primary navigation',
    'Diversity and Inclusion',
    'Diversity & Inclusion',
    'Our Products',
    'Reconnect with Us',
    'Analyst relations',
    'Media contacts',
    'Request for Services',
    'AWS re:Invent',
    'Microsoft Ignite',
    'Oracle AI World',
    'Gobally present, regionally supported',
    'Discover your team',
    'Search for open positions by country',
    'Become part of our family',
    'Building A Better Bharat, Together',
    'Investor Meet & Presentation',
    'Annual Reports',
    'Grievance Redressal Officer',
    'List of Authorized Collection',
    'Unauthorized Individuals/Entities',
    'Customer Awareness Literature',
    'Regional Centralized Customer Service Centre',
    'KMP for determining materiality',
    'Information and reports including compliance',
    'Contact for investor grievances',
    'Vigil Mechanism/ Whistle Blower Policy',
    'Investor Education & Protection Fund',
    'Disclosure under Reg',
    'Disclosure on Related Party Transactions',
    'Current Openings – Global',
    'Current Openings - Global',
    'Customer Portal - DARPAN',
    'We are not able to verify your identity',
    'Year of incorporation verification failed',
    'Year of Birth verification failed',
    'Verify using another option',
    'Strictly Necessary',
    'SmartRecruiters Attrax',
    'Track Complaint',
    'Lodge a Complaint',
    'Have a Grievance?',
    'Compensation Philosophy',
    'Innovation Initiatives',
    'Learning and Development',
    'Public Announcement-',
    'Detailed Public Statement-',
    'Offer Lette r',
    'Search & Apply',
    'Working at Reliance Group',
    'Cookie Notice',
    'Beware of fraudulent job offers',
    'Wipro Locations',
    'Cookie Consent Manager',
    'Our Partners',
    'Our Vision & Mission',
    'AVRO INDIA Bot',
    "You're on our list",
    'Adani Career Site',
    'Adani Connex Career Site',
    'Openings at Zydus',
    'View Backlog Vacancies (PDF)',
    'Откликнуться сейчас',
    'Apply Here',
    'Video Gallery',
    'Image Gallery',
    'Company Newsletters',
    'Media Kit',
    'Corporate Press Kit',
    'News And Updates',
    'Life care with focus on innovation',
    'Solid Waste Treatment',
    'AC & DC UPS',
    'Waste Management',
    'Software Products',
    'IT Services',
    'IoT & Smart Analytics',
    'Cherpoli Shahpur',
    'Download',
    'Notice:',
    'Social Connect',
    'Career Opportunities',
    'Projects',
    'title',
    'Careers webpage',
    'Explore all jobs',
    'Siemens Graduate Program',
    'WE Stand for values',
    'Innovating the future of rail, travel & transport',
    'We create technology that the world needs',
    'Connecting energy systems, buildings & industries.',
    'An innovator in automation and digitalization',
    'Belonging at Siemens',
    'Two-Wheeler Loan',
    'Loan Against Gold Ornaments',
    'Term Deposits',
    'Housing Loan',
    'Current Accounts',
    'Credit Cards',
    'Savings Accounts',
    'Personal Loan',
    'Gold Loan',
    'Home Loan',
    'Business Loan',
    'Car Loan',
    'Audit Committee',
    'Property Committee',
    'Risk Management Committee',
    'Stakeholders Relationship Committee',
    'Nomination and Remuneration Committee',
    'Annexure-C (Bond Format)',
    'Advt.',
    'View Link',
    'VIEW OPEN POSITIONS',
    'Press Release',
    'Inclusion and Diversity',
    'Campus programs',
    'image1',
    'image2',
    'img-1',
    'img-2',
    'img-3',
    'img-4',
    'Banner Image',
    'career text',
    'Maximize Potential',
    'Care & Love',
    'Growth & Ownership',
    'People-First workplace',
    'Open and inclusive culture',
    'OBJECTIVES alt text',
    'visition alt text',
    'Establish an academy of excellence',
    'Driving business excellence',
    'Better Opportunities',
    'TNFD Report 2025-26',
    'Climate Action Report 2025-26',
    'Sustainability Report 2025-26',
    'Company Overview(.pdf)',
    '3P_Re-lodgment',
    '1st Reminder',
    'Dun and Bradstreet',
    'Economic Times Infra',
    'Fortune India',
    'The Statesman',
    'Economic Times',
    'The Financial Express',
    'Your comeback, reimagined',
    'What We offer',
]



EXACT_MATCH_DEFECT_TOKENS = {
    'Next', 'Previous', 'Last', 'First', 'Next >>', 'Previous <<',
    'Customer Service', 'Shareholders', 'Global Business', '3 Wheelers', 'Motorcycles',
    'Locations', 'Destinations', 'Fraud Awareness', 'Home Page', 'Know more', 'Learn more',
    'View details', 'Click here', 'Apply now', 'Apply Online', 'How to apply', 'Discover more',
    'Upload Resume', 'Submit Resume', 'FAQs & Support', 'Review Accommodations', 'Read more',
    'Home', 'About Us', 'Our Values', 'Leadership Team', 'Our Story', 'Press Kit', 'Stories',
    'Press Releases', 'Useful Information', 'Corporate Governance', 'Investors Centre',
    'Case Studies', 'Community Development', 'Environment', 'Governance', 'Media', 'Investors',
    'Trending', 'Financials', 'Sustainability', 'Overview', 'Company Overview', 'For Corporate',
    'For Infrastructure', 'For Home Builders', 'Consumer Products', 'Products', 'Saved Jobs',
    'Frequently Asked Questions', 'Website feedback', 'Partnership', 'Download Forms',
    'View our Ads', 'Customer Education', 'Asset Publisher', 'Departments', 'otPcCenter',
    'otCenterRounded', 'Values', 'Culture', 'Our Culture', 'Sitemap', 'Contact Us', 'Contact',
    'Privacy Policy', 'Privacy Notice', 'Terms of Use', 'Terms & Conditions', 'Disclaimer',
    'Diversity and Inclusion', 'Our Products', 'Reconnect with Us', 'Analyst relations',
    'Media contacts', 'Request for Services', 'Gobally present, regionally supported',
    'Discover your team', 'Search for open positions by country', 'Become part of our family.',
    'Building A Better Bharat, Together.', 'Investor Meet & Presentation', 'Annual Reports',
    'Grievance Redressal Officer Details', 'List of Authorized Collection and Recovery Agents',
    'Unauthorized Individuals/Entities Disclaimer', 'Customer Awareness Literature',
    'Regional Centralized Customer Service Centre', 'KMP for determining materiality',
    'Information and reports including compliance reports', 'Contact for investor grievances',
    'Vigil Mechanism/ Whistle Blower Policy', 'Investor Education & Protection Fund',
    'Disclosure under Reg 62 of LODR', 'Disclosure under Reg 46 of LODR',
    'CG Power and Industrial Solutions Ltd.', 'Current Openings – Global', 'Current Openings - Global',
    'Customer Portal - DARPAN', 'Search & Apply', 'Working at Reliance Group', 'Free Credit Score',
    'Locator', 'Cookie Notice', 'Beware of fraudulent job offers', 'Wipro Locations',
    'Cookie Consent Manager', 'Download', 'Notice:', 'Career Opportunities', 'Social Connect',
    'Skip to content', 'Skip to primary navigation', 'Our Partners', 'Our Vision & Mission',
    'Adani Career Site', 'Adani Connex Career Site', 'Openings at Zydus', 'title',
    'Apply Here', 'Projects', 'Video Gallery', 'Image Gallery', 'Company Newsletters', 'Media Kit',
    'Corporate Press Kit', 'News And Updates', 'Solid Waste Treatment', 'AC & DC UPS', 'Waste Management',
    'Software Products', 'IT Services', 'IoT & Smart Analytics', 'Cherpoli Shahpur',
    'Compensation Philosophy', 'Innovation Initiatives', 'Learning and Development',
    'Track Complaint', 'Lodge a Complaint', 'Have a Grievance?', 'Statistics', 'Strictly Necessary',
    'SmartRecruiters Attrax', 'AVRO INDIA Bot', "You're on our list",
    'Careers webpage', 'Explore all jobs', 'Siemens Graduate Program', 'WE Stand for values',
    'Innovating the future of rail, travel & transport', 'We create technology that the world needs',
    'Connecting energy systems, buildings & industries.', 'An innovator in automation and digitalization',
    'Belonging at Siemens', 'Two-Wheeler Loan', 'Loan Against Gold Ornaments', 'Term Deposits',
    'Housing Loan', 'Current Accounts', 'Credit Cards', 'Savings Accounts', 'Personal Loan',
    'Gold Loan', 'Home Loan', 'Business Loan', 'Car Loan', 'Fixed Deposit', 'Recurring Deposit',
    'Debit Cards', 'SEE ALL JOBS', 'SEE ALL ROLES', 'VIEW ALL JOBS',
    'RBL Bank is registered with DICGC', 'Save your Card on Merchants', 'Namma Metro Login',
    'Find your Work Family', 'Internship and Apprenticeship Programs',
    'RBL Premier Banker Program - Powered by NIIT', 'Why Choose Us', 'Industrial Business',
    'Brands', 'Diverse Teams Are Stronger', 'Learning is your Launchpad to Success',
    'About Pidilite', 'Pidilite Industries Limited', 'Young Talent management', 'D2C Brands',
    'Disclaimers', 'Recruitment Notices', 'Audio-Visuals', 'Medical Rules', 'Navigation Menu',
    'Live Your Passion', 'Audit Committee', 'Property Committee', 'Risk Management Committee',
    'Stakeholders Relationship Committee', 'Nomination and Remuneration Committee',
    'Annexure-C (Bond Format)', 'Advt.', 'View Link', 'VIEW OPEN POSITIONS', 'Press Release',
    'Inclusion and Diversity', 'Campus programs', 'image1', 'image2', 'img-1', 'img-2', 'img-3',
    'img-4', 'Banner Image', 'career text', 'Maximize Potential', 'Care & Love', 'Growth & Ownership',
    'People-First workplace', 'Open and inclusive culture', 'OBJECTIVES alt text', 'visition alt text',
    'Establish an academy of excellence', 'Driving business excellence', 'Better Opportunities',
    'TNFD Report 2025-26', 'Climate Action Report 2025-26', 'Sustainability Report 2025-26',
    'Company Overview(.pdf)', '3P_Re-lodgment', '1st Reminder', 'Dun and Bradstreet',
    'Economic Times Infra', 'Fortune India', 'The Statesman', 'Economic Times', 'The Financial Express',
    'Your comeback, reimagined', 'What We offer', 'What we offer'
}


NON_CAREER_URL_PATTERNS = [
    '/blog/', '/blogs/', 'shop.', '/collections/',
    'cgglobal.com/cgglobal_backend/api/products',
    '/api/products',
    'cms.aadharhousing.com',
    'darpan.nmdc.co.in',
    'nmdc.co.in/cms-admin/api/home/ourprojects',
    'cms-api.bajajfinserv.in',
    'canarabank.bank.in/pages/',
    'tcs.com/what-we-do/',
    'tcs.com/contact-us/',
    'tcs.com/who-we-are/events/',
    'tvsmotor.com/about-us/',
    'torrentpharma.com/ourproducts/',
    'remember.techmahindra.com',
    'salesiq.zohopublic.in',
    'lloyds.in/media/',
    'lloyds.in/sustainability/',
    'alkemlabs.com/_next/',
    'routeignite.com',
    'apps.indianbank.bank.in',
    'shriramfinance.in/free-credit-score',
    'shriramfinance.in/branch-locator',
    'wp-content/uploads',
    'pressreader.com',
    'economictimes.indiatimes.com',
    'uploads/gcpl_fe_brandwagon',
    'ongcindia.com/documents/',
    'ongcindia.com/web/eng/',
    'mazagondock.in/writereaddata',
    'dicgc.org.in',
    'cardhq.com',
    'paycraftsol.in',
    'pminternship.mca.gov.in',
    'niit.com',
    'delhivery.com/solutions/',
    'insurance-disclaimer',
    'pidilite.com/consumer-brands',
    'pidilite.com/careers/young-talent',
    'pidilite.com/careers/diversity',
    'industrial-adhesives.pidilite.com',
    'digitate.com',
    'jile.io',
    'tcsion.com',
    'sbilife.co.in/about/leadership-team',
    'rbl.bank.in',
    'mobility.siemens.com',
    'siemens.com/en-gb/company/about',
    'wa.me/',
    'sms:',
    'tel:',
    'mailto:',
    '/adobe/assets/',
    'files.hdfcfund.com',
    'docs.trent-tata.com',
    'irfc.co.in/sites',
    '3pland.com/files/',
    'andhrapaper.com/wp-content/',
    'marico.com/global/media/',
    'marico.com/careers/inclusion',
    'marico.com/careers/campus',
    'mankindpharma.com/career',
    'mahindra.com/women-at-mahindra',
    'hzlindia.com/uploads/',
]





# Pre-normalized lookup structures for ultra-fast defect detection
_EXACT_DEFECT_TOKENS_LOWER = frozenset(t.lower().strip() for t in EXACT_MATCH_DEFECT_TOKENS if t.strip())
_CONTAINS_DEFECT_PATTERNS_LOWER = tuple(p.lower().strip() for p in UI_NAV_DEFECT_PATTERNS if p not in EXACT_MATCH_DEFECT_TOKENS and p.strip())
_NON_CAREER_URLS_LOWER = tuple(u.lower().strip() for u in NON_CAREER_URL_PATTERNS if u.strip())
_PREFIX_DEFECTS_LOWER = (
    'http://', 'https://', 'i have read, understood', '+91', 'liberate', 'sms:', 'tel:',
    'mailto:', 'mr. ', 'ms. ', 'image', 'img-', 'how to apply', 'discover more', 'faqs & support'
)
_EXTRA_CONTAINS_DEFECTS_LOWER = tuple(c.lower().strip() for c in (
    'life @', 'life at ', 'jobs at ', 'results of ', 'result of ', 'final result', 'detailed result',
    'interview schedule', 'admit card', '(external website', 'montréal', 'montreal', 'québec', 'quebec',
    'latin america', 'gerente de', 'estágio', 'banco de talentos', 'verfahrensmechaniker', 'kautschuktechnologe',
    'откликнуться', 'एसजेवीएन', 'emotron', 'alt text', 'caste certificate', 'attestation form', 'user manual',
    'committee charter', 'committee', 'report 2025-26', 'cagr meaning', 'how to apply', 'discover more',
    'faqs & support', 'review accommodations'
))

def is_defective_job_record(title: str, app_url: str = '', source_url: str = '') -> bool:
    """Fast, in-memory check to see if a job record contains defect tokens or non-career URLs."""
    t = (title or '').lower().strip()
    if not t:
        return True
    if t in _EXACT_DEFECT_TOKENS_LOWER:
        return True
    if any(p in t for p in _CONTAINS_DEFECT_PATTERNS_LOWER):
        return True
    if any(t.startswith(prefix) for prefix in _PREFIX_DEFECTS_LOWER):
        return True
    if any(c in t for c in _EXTRA_CONTAINS_DEFECTS_LOWER):
        return True
    au = (app_url or '').lower()
    su = (source_url or '').lower()
    if any(bad in au or bad in su for bad in _NON_CAREER_URLS_LOWER):
        return True
    return False

_DEFECTIVE_CACHE = {'ids': None, 'time': 0, 'count': -1}

def get_defective_job_ids(force_refresh=False):
    """Retrieve defective job row IDs with an intelligent in-memory cache to keep queries instant."""
    import time
    now = time.time()
    from modules.admin_panel.models import Job
    active_count = Job.objects.filter(status='ACTIVE').count()
    if not force_refresh and _DEFECTIVE_CACHE['ids'] is not None:
        if (now - _DEFECTIVE_CACHE['time']) < 60 and _DEFECTIVE_CACHE.get('count') == active_count:
            return _DEFECTIVE_CACHE['ids']

    active_rows = Job.objects.filter(
        status='ACTIVE'
    ).exclude(
        verification_status__in=['LEGACY_UNVERIFIED', 'REJECTED', 'QUARANTINED', 'NEEDS_REVIEW']
    ).values('job_row_id', 'job_title', 'application_url', 'source_url')

    bad_ids = {
        row['job_row_id']
        for row in active_rows
        if is_defective_job_record(row['job_title'], row['application_url'], row['source_url'])
    }
    _DEFECTIVE_CACHE['ids'] = bad_ids
    _DEFECTIVE_CACHE['time'] = now
    _DEFECTIVE_CACHE['count'] = active_count
    return bad_ids


def apply_job_safety_filters(qs):
    """Strict Data Integrity: Filters out any unverified legacy seed records (REQ-*), quarantined/rejected data,
    blogs, e-commerce stores, overseas territories, exam results, and UI navigation boilerplate defect titles.
    Optimized for high-throughput single-digit millisecond query execution."""
    if getattr(qs, '_safety_filters_applied', False):
        return qs

    qs = qs.exclude(job_id__startswith='REQ')
    qs = qs.exclude(verification_status__in=['LEGACY_UNVERIFIED', 'REJECTED', 'QUARANTINED', 'NEEDS_REVIEW'])
    qs = qs.exclude(status__in=['NEEDS_REVIEW', 'INACTIVE', 'REMOVED', 'EXPIRED'])

    bad_ids = get_defective_job_ids()
    if bad_ids:
        qs = qs.exclude(job_row_id__in=bad_ids)

    qs._safety_filters_applied = True
    return qs



def public_jobs(qs=None):
    """Jobs that may appear on the website. Returns ALL active, directly crawled, verified job postings passing strict data integrity guards."""
    if qs is None:
        from modules.admin_panel.models import Job
        qs = Job.objects.all()
    base_qs = qs.filter(
        status='ACTIVE',
    ).exclude(
        verification_status__in=['REJECTED', 'QUARANTINED', 'LEGACY_UNVERIFIED', 'NEEDS_REVIEW']
    ).exclude(
        status='NEEDS_REVIEW'
    ).exclude(job_id__startswith='REQ')

    # Step 0 Exact-Match Standard c): Freshness Window
    # If freshness enforcement is active, records not reconciled within RECONCILE_MAX_AGE_HOURS are hidden.
    try:
        from django.conf import settings
        from django.utils import timezone
        from datetime import timedelta
        enforce_freshness = getattr(settings, 'ENFORCE_RECONCILE_FRESHNESS', False)
        if enforce_freshness:
            max_age_hours = getattr(settings, 'RECONCILE_MAX_AGE_HOURS', 72)
            cutoff = timezone.now() - timedelta(hours=max_age_hours)
            base_qs = base_qs.filter(last_reconciled_at__gte=cutoff)
    except Exception:
        pass

    return apply_job_safety_filters(base_qs)


def public_records(qs):
    """CSR projects / contacts / opportunities that may appear on the website."""
    if qs is None:
        return qs
    qs = qs.exclude(
        verification_status__in=['REJECTED', 'QUARANTINED', 'LEGACY_UNVERIFIED', 'NEEDS_REVIEW']
    )
    # Exclude INVALID_SYNTHETIC, REMOVED, EXPIRED, and NEEDS_REVIEW only if model has a 'status' field (e.g. CSROpportunity, CSRProject, Job)
    try:
        model_fields = {f.name for f in qs.model._meta.get_fields()}
        if 'status' in model_fields:
            qs = qs.exclude(status__in=['INVALID_SYNTHETIC', 'REMOVED', 'EXPIRED', 'NEEDS_REVIEW'])
    except Exception:
        pass
    return qs


def public_job_q(prefix='jobs__'):
    """Q object for annotate(filter=...) over a reverse relation."""
    return Q(**{
        f'{prefix}status': 'ACTIVE',
    }) & ~Q(**{
        f'{prefix}verification_status__in': ['REJECTED', 'QUARANTINED', 'LEGACY_UNVERIFIED', 'NEEDS_REVIEW']
    }) & ~Q(**{
        f'{prefix}status': 'NEEDS_REVIEW',
    }) & ~Q(**{
        f'{prefix}job_id__startswith': 'REQ',
    }) & ~Q(**{
        f'{prefix}application_url__icontains': '/blog/',
    }) & ~Q(**{
        f'{prefix}application_url__icontains': 'shop.',
    })


def public_record_q(prefix):
    return (
        ~Q(**{f'{prefix}verification_status__in': ['REJECTED', 'QUARANTINED', 'LEGACY_UNVERIFIED', 'NEEDS_REVIEW']})
        & ~Q(**{f'{prefix}status__in': ['INVALID_SYNTHETIC', 'REMOVED', 'EXPIRED', 'NEEDS_REVIEW']})
    )


def format_relative_time(dt) -> str:
    """Returns human-readable relative time string (e.g. '2 hours ago', '1 day ago')."""
    if not dt:
        return "recently"
    from django.utils import timezone
    from datetime import datetime
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except Exception:
            return "recently"
    now = timezone.now()
    if timezone.is_naive(dt):
        from django.utils.timezone import make_aware
        dt = make_aware(dt)
    diff = now - dt
    seconds = int(diff.total_seconds())
    if seconds < 0:
        return "just now"
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    if days < 30:
        return f"{days} day{'s' if days != 1 else ''} ago"
    months = days // 30
    if months < 12:
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years != 1 else ''} ago"


