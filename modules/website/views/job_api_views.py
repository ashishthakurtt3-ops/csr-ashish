from django.http import JsonResponse
from django.core.cache import cache
from django.db.models import Q, Count
from modules.admin_panel.models import Job, Company
from modules.website.utils.pagination import paginate_queryset
from modules.website.utils.entitlement_service import EntitlementService, EntitlementError

from modules.admin_panel.verification import (
    PUBLIC_VERIFICATION_STATUSES, public_jobs, public_job_q, NOT_AVAILABLE_TEXT, LOGIN_REQUIRED_TEXT, LINK_OK,
    apply_job_safety_filters, UI_NAV_DEFECT_PATTERNS
)

IMPACT_ROLE_FILTER = (
    Q(job_title__icontains='CSR') | Q(job_title__icontains='ESG') |
    Q(job_title__icontains='Sustainability') | Q(job_title__icontains='Community') |
    Q(job_title__icontains='Foundation') | Q(job_title__icontains='Social') |
    Q(job_title__icontains='Environmental Impact') | Q(job_title__icontains='Impact') |
    Q(department__icontains='CSR') | Q(department__icontains='Social') |
    Q(department__icontains='Sustainab') | Q(function__icontains='Impact') |
    Q(function__icontains='Sustainability')
)

STANDARD_JOB_CATEGORIES = [
    'Technology & Digital',
    'Engineering & Manufacturing',
    'Finance, Banking & Audit',
    'Supply Chain & Operations',
    'Sales, Commercial & Marketing',
    'Human Resources & Talent',
    'CSR, ESG & Sustainability',
    'Healthcare, Clinical & Pharma',
    'Legal, Governance & Regulatory',
]

# Uncategorized condition: source did not provide a category/department
UNCATEGORIZED_JOB_Q = (
    Q(department__isnull=True) | Q(department='') |
    Q(department__iexact='uncategorized') | Q(department__iexact='unspecified') |
    Q(department__iexact='none') | Q(department__iexact='null')
)

# Standard category queries apply strictly to records with a defined source department/function
# Priorities ensure 100% mutually exclusive membership
TECH_Q = ~UNCATEGORIZED_JOB_Q & (
    Q(department__icontains='technology') | Q(department__icontains='tech') |
    Q(department__icontains='software') | Q(department__icontains='data') |
    Q(department__icontains='analytics') | Q(department__icontains='product') |
    Q(department__icontains='design') | Q(department__icontains='paytm labs') |
    Q(department__iexact='IT') | Q(function__icontains='information technology')
)

ENGINEERING_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & (
    Q(department__icontains='engineering') | Q(department__icontains='manufacturing') |
    Q(department__icontains='automation') | Q(department__icontains='maintenance') |
    Q(department__icontains='plant') | Q(department__icontains='process') |
    Q(function__icontains='engineering')
)

FINANCE_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & (
    Q(department__icontains='finance') | Q(department__icontains='banking') |
    Q(department__icontains='accounts') | Q(department__icontains='treasury') |
    Q(department__icontains='audit') | Q(department__icontains='tax') |
    Q(function__icontains='finance')
)

OPERATIONS_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & (
    Q(department__icontains='operation') | Q(department__icontains='supply') |
    Q(department__icontains='logistics') | Q(department__icontains='procurement') |
    Q(department__icontains='purchase') | Q(department__icontains='support') |
    Q(function__icontains='supply chain')
)

SALES_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & ~OPERATIONS_Q & (
    Q(department__icontains='sales') | Q(department__icontains='marketing') |
    Q(department__icontains='commercial') | Q(department__icontains='brand') |
    Q(function__icontains='sales') | Q(function__icontains='marketing')
)

HR_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & ~OPERATIONS_Q & ~SALES_Q & (
    Q(department__icontains='hr') | Q(department__icontains='human resources') |
    Q(department__icontains='people') | Q(department__icontains='talent') |
    Q(function__icontains='human resources')
)

CSR_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & ~OPERATIONS_Q & ~SALES_Q & ~HR_Q & (
    Q(department__icontains='csr') | Q(department__icontains='sustainability') |
    Q(department__icontains='esg') | Q(department__icontains='community') |
    Q(function__icontains='sustainability')
)

HEALTHCARE_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & ~OPERATIONS_Q & ~SALES_Q & ~HR_Q & ~CSR_Q & (
    Q(department__icontains='health') | Q(department__icontains='pharma') |
    Q(department__icontains='medical') | Q(department__icontains='clinical') |
    Q(function__icontains='healthcare')
)

LEGAL_Q = ~UNCATEGORIZED_JOB_Q & ~TECH_Q & ~ENGINEERING_Q & ~FINANCE_Q & ~OPERATIONS_Q & ~SALES_Q & ~HR_Q & ~CSR_Q & ~HEALTHCARE_Q & (
    Q(department__icontains='legal') | Q(department__icontains='compliance') |
    Q(department__icontains='regulatory') | Q(department__icontains='secretarial') |
    Q(department__icontains='governance') | Q(function__icontains='legal')
)

ALL_STANDARD_JOB_CATEGORIES_Q = (
    TECH_Q | ENGINEERING_Q | FINANCE_Q | OPERATIONS_Q | SALES_Q | HR_Q | CSR_Q | HEALTHCARE_Q | LEGAL_Q
)

OTHERS_JOB_Q = ~UNCATEGORIZED_JOB_Q & ~ALL_STANDARD_JOB_CATEGORIES_Q

JOB_CATEGORY_MAP = {
    'tech': TECH_Q,
    'technology': TECH_Q,
    'technology_&_digital': TECH_Q,
    'engineering': ENGINEERING_Q,
    'engineering_&_manufacturing': ENGINEERING_Q,
    'finance': FINANCE_Q,
    'banking': FINANCE_Q,
    'finance,_banking_&_audit': FINANCE_Q,
    'operations': OPERATIONS_Q,
    'supply_chain': OPERATIONS_Q,
    'supply_chain_&_operations': OPERATIONS_Q,
    'sales': SALES_Q,
    'marketing': SALES_Q,
    'sales,_commercial_&_marketing': SALES_Q,
    'hr': HR_Q,
    'human_resources': HR_Q,
    'human_resources_&_talent': HR_Q,
    'csr': CSR_Q,
    'esg': CSR_Q,
    'sustainability': CSR_Q,
    'csr,_esg_&_sustainability': CSR_Q,
    'healthcare': HEALTHCARE_Q,
    'pharma': HEALTHCARE_Q,
    'healthcare,_clinical_&_pharma': HEALTHCARE_Q,
    'legal': LEGAL_Q,
    'compliance': LEGAL_Q,
    'legal,_governance_&_regulatory': LEGAL_Q,
}

JOB_SORT_OPTIONS = {
    'recent': ['-last_checked_date', '-job_row_id'],
    'company': ['company__company_name', 'job_title'],
    'title': ['job_title'],
    'seniority': ['-experience', '-job_row_id'],
    'experience': ['-experience', '-job_row_id'],
}

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
]

def apply_job_safety_filters(qs):
    """Strict Data Integrity: Delegates directly to the single source of truth in modules.admin_panel.verification."""
    from modules.admin_panel.verification import apply_job_safety_filters as authoritative_filter
    return authoritative_filter(qs)




def get_normalized_job_category(dept: str, title: str, func: str) -> str:
    """Assign mutually exclusive normalized category matching query definitions."""
    if not dept or dept.strip().lower() in ('', 'unspecified', 'uncategorized', 'none', 'null'):
        return 'Uncategorized'
    combined = f"{dept or ''} {func or ''}".strip().lower()
    if any(k in combined for k in ('technology', 'tech', 'software', 'data', 'analytics', 'product', 'design', 'paytm labs', 'it')):
        return 'Technology & Digital'
    if any(k in combined for k in ('engineering', 'manufacturing', 'automation', 'maintenance', 'plant', 'process')):
        return 'Engineering & Manufacturing'
    if any(k in combined for k in ('finance', 'banking', 'accounts', 'treasury', 'audit', 'tax')):
        return 'Finance, Banking & Audit'
    if any(k in combined for k in ('operation', 'supply', 'logistics', 'procurement', 'purchase', 'support')):
        return 'Supply Chain & Operations'
    if any(k in combined for k in ('sales', 'marketing', 'commercial', 'brand')):
        return 'Sales, Commercial & Marketing'
    if any(k in combined for k in ('hr', 'human resources', 'people', 'talent')):
        return 'Human Resources & Talent'
    if any(k in combined for k in ('csr', 'sustainability', 'esg', 'community')):
        return 'CSR, ESG & Sustainability'
    if any(k in combined for k in ('health', 'pharma', 'medical', 'clinical')):
        return 'Healthcare, Clinical & Pharma'
    if any(k in combined for k in ('legal', 'compliance', 'regulatory', 'secretarial', 'governance')):
        return 'Legal, Governance & Regulatory'
    return 'Other / Company-specific'


def _clean_field_val(val):
    if not val:
        return None
    s = str(val).strip()
    if not s or s.lower() in ('unspecified', 'none', 'null', 'not specified', 'uncategorized', '---', '--', '-', 'not provided by source', 'undefined'):
        return None
    return s


def serialize_job_item(j: Job, is_detail: bool = True):
    c = j.company
    from modules.crawler_engine.normalizers import normalize_application_url
    from modules.admin_panel.verification import format_relative_time
    app_url = normalize_application_url(j.application_url) or j.application_url or None

    cname = c.company_name
    sym = c.nse_symbol
    careers_url = c.careers_url if (c.careers_url or '').startswith('http') else None
    website_url = c.website_url if (c.website_url or '').startswith('http') else None

    # Step 0 Exact-Match Standard a): Verbatim fields only.
    raw_title = _clean_field_val(getattr(j, 'raw_title', None) or j.job_title)

    raw_loc = _clean_field_val(getattr(j, 'raw_location', None) or j.location)
    if raw_loc and any(bad in raw_loc.lower() for bad in ["refer official", "not available", "none", "n/a", "null"]):
        raw_loc = None

    city_val = _clean_field_val(j.city)
    if city_val and any(bad in city_val.lower() for bad in ["refer official", "not available", "none", "n/a", "null"]):
        city_val = None

    state_val = _clean_field_val(j.state)
    if state_val and any(bad in state_val.lower() for bad in ["refer official", "not available", "none", "n/a", "null"]):
        state_val = None

    # Synthesize rich location: ensure scraped cities/states are prominently displayed
    loc_display = raw_loc
    if city_val:
        if not raw_loc or raw_loc.strip().lower() in ('india', 'in'):
            if state_val and state_val.lower() not in city_val.lower():
                loc_display = f"{city_val}, {state_val}"
            else:
                loc_display = city_val
        elif city_val.lower() not in raw_loc.lower():
            loc_display = f"{city_val}, {raw_loc}"
    elif state_val and (not raw_loc or raw_loc.strip().lower() in ('india', 'in')):
        loc_display = state_val

    if not loc_display:
        loc_display = raw_loc or city_val or state_val or "India"

    raw_dept = _clean_field_val(getattr(j, 'raw_department', None) or j.department)
    if raw_dept and any(bad in raw_dept.lower() for bad in ["refer official", "not available", "none", "n/a", "null"]):
        raw_dept = None

    raw_emp_type = _clean_field_val(getattr(j, 'raw_employment_type', None) or j.employment_type)
    if raw_emp_type and any(bad in raw_emp_type.lower() for bad in ["refer official", "not available", "none", "n/a", "null"]):
        raw_emp_type = None

    raw_work_mode = _clean_field_val(j.work_mode)
    if raw_work_mode and any(bad in raw_work_mode.lower() for bad in ["refer official", "not available", "none", "n/a", "null"]):
        raw_work_mode = None

    norm_cat = get_normalized_job_category(raw_dept, raw_title, j.function)

    # Verification timestamp and provenance
    verified_dt = getattr(j, 'last_reconciled_at', None) or j.link_verified_at or j.retrieved_at
    rel_time = format_relative_time(verified_dt)
    if j.status in ('EXPIRED', 'STALE'):
        verified_badge_text = "Expired - Listing archived on official site"
    elif j.status == 'UNVERIFIED' or j.verification_status == 'UNVERIFIED':
        verified_badge_text = "Unverified - Sourced from company career portal"
    else:
        verified_badge_text = f"As listed on the official site - verified {rel_time}"

    is_company_unverifiable = bool(
        (c.jobs_access in ('LOGIN_REQUIRED', 'NOT_PUBLISHED')) or 
        (c.verification_status not in ('VERIFIED', 'SOURCE_CONFIRMED'))
    )

    # Short summary calculation for list & card views
    raw_summary_source = (
        getattr(j, 'summary', None) or
        getattr(j, 'about_role', None) or
        getattr(j, 'role_purpose', None) or
        getattr(j, 'job_description', None)
    )
    clean_summary_text = _clean_field_val(raw_summary_source)
    short_summary = (clean_summary_text[:250] + '...') if (clean_summary_text and len(clean_summary_text) > 250) else clean_summary_text

    item = {
        'job_row_id': j.job_row_id,
        'company_id': j.company_id,
        'company_name': cname,
        'nse_symbol': sym,
        'website_url': website_url,
        'sector': c.sector,
        'careers_url': careers_url,
        'job_id': j.job_id,
        'external_job_id': _clean_field_val(j.external_job_id),
        'ats_platform': _clean_field_val(j.ats_platform),
        'job_title': raw_title,
        'raw_title': raw_title,
        'department': raw_dept,
        'raw_department': raw_dept,
        'original_category': raw_dept,
        'normalized_category': norm_cat,
        'team': _clean_field_val(j.team),
        'business_unit': _clean_field_val(j.business_unit),
        'location': loc_display,
        'raw_location': loc_display,
        'city': city_val,
        'state': _clean_field_val(j.state),
        'country': _clean_field_val(j.country),
        'work_mode': raw_work_mode,
        'employment_type': raw_emp_type,
        'raw_employment_type': raw_emp_type,
        'experience': _clean_field_val(j.experience),
        'education': _clean_field_val(j.education),
        'skills': _clean_field_val(j.skills),
        'salary': _clean_field_val(j.salary),
        'salary_min': str(j.salary_min) if j.salary_min else None,
        'salary_max': str(j.salary_max) if j.salary_max else None,
        'salary_currency': _clean_field_val(j.salary_currency),
        'pay_band': _clean_field_val(getattr(j, 'pay_band', None)),
        'summary': short_summary,
        'detail_fetched': bool(getattr(j, 'detail_fetched', False)),
        'detail_fetch_status': getattr(j, 'detail_fetch_status', None) or ('FETCHED' if getattr(j, 'detail_fetched', False) else 'NOT_FETCHED'),
        'detail_fetched_at': getattr(j, 'detail_fetched_at', None),
        'posted_date': j.posted_date,
        'closing_date': j.closing_date,
        'application_deadline': j.application_deadline,
        'travel_required': _clean_field_val(j.travel_required),
        'shift': _clean_field_val(j.shift),
        'work_authorization': _clean_field_val(j.work_authorization),
        'legal_name': c.legal_name,
        'headquarters': c.headquarters,
        'cin': c.cin,
        'application_url': app_url,
        'canonical_url': j.canonical_url or (j.application_url.split('#')[0] if j.application_url else None),
        'link_quality': getattr(j, 'link_quality', 'UNVERIFIED') or 'UNVERIFIED',
        'link_check_note': getattr(j, 'link_check_note', None),
        'apply_button_label': 'Archived Opening' if j.status in ('EXPIRED', 'STALE') else ('Apply Directly' if getattr(j, 'link_quality', None) == 'DIRECT' else 'Find this role on the company careers page'),
        'apply_button_url': (j.canonical_url or app_url) if getattr(j, 'link_quality', None) == 'DIRECT' else app_url,
        'link_verified': bool(app_url),
        'not_available_text': NOT_AVAILABLE_TEXT,
        'jobs_access': c.jobs_access,
        'jobs_access_text': LOGIN_REQUIRED_TEXT if c.jobs_access == 'LOGIN_REQUIRED' else None,
        'source_url': j.source_url or app_url,
        'source_domain': j.source_domain,
        'retrieved_at': (j.retrieved_at.isoformat() if hasattr(j.retrieved_at, 'isoformat') else str(j.retrieved_at)) if j.retrieved_at else None,
        'last_checked_date': j.last_checked_date,
        'status': j.status,
        'verification_status': j.verification_status,
        'confidence': j.confidence,
        'link_status': j.link_status,
        'link_verified_at': (j.link_verified_at.isoformat() if hasattr(j.link_verified_at, 'isoformat') else str(j.link_verified_at)) if j.link_verified_at else None,
        'data_provenance': j.data_provenance,
        'fingerprint': j.fingerprint,
        'verified_badge_text': verified_badge_text,
        'verified_relative_time': rel_time,
        'is_company_unverifiable': is_company_unverifiable,
        'last_reconciled_at': (j.last_reconciled_at.isoformat() if hasattr(j.last_reconciled_at, 'isoformat') else str(j.last_reconciled_at)) if getattr(j, 'last_reconciled_at', None) else None,
        'mismatch_reason': getattr(j, 'mismatch_reason', None),
        'seniority_level': _clean_field_val(getattr(j, 'seniority_level', None)),
        'details_status': getattr(j, 'details_status', 'MISSING') or 'MISSING',
        'salary_text': _clean_field_val(getattr(j, 'salary_text', None)) or _clean_field_val(j.salary),
        'currency': _clean_field_val(getattr(j, 'currency', None)) or _clean_field_val(j.salary_currency),
    }

    if is_detail:
        item.update({
            'job_description': _clean_field_val(j.job_description),
            'role_purpose': _clean_field_val(getattr(j, 'role_purpose', None)),
            'responsibilities': _clean_field_val(j.responsibilities),
            'day_in_the_life': _clean_field_val(getattr(j, 'day_in_the_life', None)),
            'requirements': _clean_field_val(j.requirements),
            'qualifications': _clean_field_val(j.qualifications),
            'preferred_qualifications': _clean_field_val(j.preferred_qualifications),
            'technical_skills': _clean_field_val(getattr(j, 'technical_skills', None)),
            'behavioural_skills': _clean_field_val(getattr(j, 'behavioural_skills', None)),
            'benefits': _clean_field_val(j.benefits),
            'employer_info': _clean_field_val(getattr(j, 'employer_info', None)),
            'structured_details': getattr(j, 'structured_details', None) or {},
            'evidence_text': j.evidence_text,
            'field_source': getattr(j, 'field_source', None) or {},
            'mismatch_diff': getattr(j, 'mismatch_diff', None),
            'description_raw': _clean_field_val(getattr(j, 'description_raw', None)) or _clean_field_val(j.job_description),
            'description_html': getattr(j, 'description_html', None),
            'about_role': _clean_field_val(getattr(j, 'about_role', None)) or _clean_field_val(getattr(j, 'role_purpose', None)),
            'responsibilities_list': getattr(j, 'responsibilities_list', None) or [],
            'qualifications_education': getattr(j, 'qualifications_education', None) or [],
            'qualifications_experience': _clean_field_val(getattr(j, 'qualifications_experience', None)) or _clean_field_val(j.experience),
            'required_skills': getattr(j, 'required_skills', None) or [],
            'preferred_skills': getattr(j, 'preferred_skills', None) or [],
            'details_missing_fields': getattr(j, 'details_missing_fields', None) or [],
            'details_scraped_at': (j.details_scraped_at.isoformat() if hasattr(j.details_scraped_at, 'isoformat') else str(j.details_scraped_at)) if getattr(j, 'details_scraped_at', None) else None,
        })

    return item



def jobs_list_api(request):
    from modules.website.utils.entitlement_service import user_has_active_plan
    # RequestFactory-built requests have no AuthenticationMiddleware, so
    # `request.user` may not exist at all.
    user = getattr(request, 'user', None)
    is_authenticated = bool(user and user.is_authenticated)
    if not user_has_active_plan(user):
        from modules.admin_panel.models import GuestPreviewSettings
        from modules.website.views.preview_api_views import get_public_preview_jobs
        cfg = GuestPreviewSettings.get_settings()
        # Authoritative public inventory, using the same filter as /stats.
        public_total = public_jobs(Job.objects.all()).count()
        if not cfg.preview_enabled:
            return JsonResponse({
                'is_preview': True,
                'preview_enabled': False,
                'preview_limit': 0,
                'preview_message': 'Please select a subscription plan to access vacancies.' if is_authenticated else 'Guest preview is currently disabled. Please sign in or register to access vacancies.',
                'plan_required': is_authenticated,
                'items': [],
                'total': 0,
                'page': 1,
                'total_pages': 1,
                'has_more': False
            })
        items = get_public_preview_jobs()
        return JsonResponse({
            'is_preview': True,
            'preview_enabled': True,
            'preview_limit': cfg.preview_limit,
            'preview_message': 'Subscription plan required. Please choose a subscription plan to search, filter, and save all vacancies.' if is_authenticated else f'You are viewing a limited public preview of {public_total} active job openings. Sign in or register to search, filter, and save all vacancies.',
            'plan_required': is_authenticated,
            'login_url': '/login/?next=/jobs/',
            'register_url': '/register/?next=/jobs/',
            'pricing_url': '/?tab=pricing',
            'total': public_total,
            'page': 1,
            'total_pages': 1,
            'has_more': True,
            'items': items
        })

    if request.META.get('HTTP_ACCEPT', '').find('text/html') != -1 and request.GET.get('format') != 'json':
        from modules.website.views.home_views import index_view
        return index_view(request)

    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    sort = request.GET.get('sort', 'recent')

    is_unfiltered = not any([
        request.GET.get('q'), request.GET.get('company_id'), request.GET.get('company'),
        request.GET.get('location'), request.GET.get('state'), request.GET.get('department'),
        request.GET.get('work_mode'), request.GET.get('status'), request.GET.get('impact_only'),
        request.GET.get('category'), request.GET.get('experience'), request.GET.get('format'),
        request.GET.get('export')
    ])
    if is_unfiltered and str(page) in ('1', 'None', '') and str(page_size) in ('12', '24') and sort == 'recent':
        from django.http import HttpResponse
        cached_json = cache.get(f"jobs_list_json_p{page}_ps{page_size}")
        if cached_json:
            return HttpResponse(cached_json, content_type='application/json')

    q = request.GET.get('q', '').strip()
    company_id = request.GET.get('company_id', '').strip()
    company = request.GET.get('company', '').strip()
    location = request.GET.get('location', '').strip()
    state = request.GET.get('state', '').strip()
    department = request.GET.get('department', '').strip()
    work_mode = request.GET.get('work_mode', '').strip()
    status = request.GET.get('status', '').strip()
    impact_only = request.GET.get('impact_only', '').lower() in ('true', '1')
    category = request.GET.get('category', '').strip()
    experience = request.GET.get('experience', '').strip()
    limit = int(request.GET.get('limit', 2000))

    # Authoritative eligible jobs: strictly ACTIVE and verified/published with official source evidence
    qs = public_jobs(Job.objects.select_related('company'))
    qs = apply_job_safety_filters(qs)
    qs = qs.defer(
        'description_raw', 'description_html', 'job_description',
        'responsibilities', 'responsibilities_list', 'requirements',
        'qualifications', 'preferred_qualifications', 'qualifications_education',
        'qualifications_experience', 'required_skills', 'preferred_skills',
        'benefits', 'employer_info', 'structured_details',
        'evidence_text', 'field_source'
    )

    if q:
        qs = qs.filter(
            Q(job_title__icontains=q) |
            Q(company__company_name__icontains=q) |
            Q(department__icontains=q) |
            Q(function__icontains=q) |
            Q(location__icontains=q) |
            Q(skills__icontains=q) |
            Q(company__nse_symbol__icontains=q)
        )
    if company_id and company_id != 'all':
        qs = qs.filter(company_id=company_id)
    elif company and company != 'all':
        qs = qs.filter(
            Q(company_id=company) |
            Q(company__company_name__iexact=company) |
            Q(company__company_name__icontains=company) |
            Q(company__nse_symbol__iexact=company)
        )
    if location and location != 'all':
        qs = qs.filter(
            Q(location__icontains=location) |
            Q(city__icontains=location) |
            Q(state__icontains=location) |
            Q(country__icontains=location)
        )
    if state and state != 'all':
        qs = qs.filter(Q(state__icontains=state) | Q(location__icontains=state))
    if department and department != 'all':
        qs = qs.filter(department__icontains=department)
    if work_mode and work_mode != 'all':
        qs = qs.filter(work_mode=work_mode)
    if status and status != 'all':
        s_up = status.upper()
        if s_up == 'ACTIVE':
            qs = qs.filter(status='ACTIVE')
        elif s_up in ('EXPIRED', 'STALE'):
            qs = qs.filter(Q(status__in=['EXPIRED', 'STALE']) | Q(verification_status='STALE'))
        elif s_up == 'UNVERIFIED':
            qs = qs.filter(Q(status='UNVERIFIED') | Q(verification_status='UNVERIFIED'))
        else:
            qs = qs.filter(status=status)
    if impact_only:
        qs = qs.filter(IMPACT_ROLE_FILTER)

    # ── Entitlement: advanced filter gate ────────────────────────────
    _advanced_filter_params = [experience, category, department]
    if any(p and p.lower() != 'all' for p in _advanced_filter_params):
        try:
            from modules.admin_panel.models import User as _User
            if getattr(request, 'user', None) and request.user.is_authenticated:
                _ent_user = request.user
            else:
                _ent_user = _User.objects.filter(is_active=True).order_by('id').first()
            if _ent_user:
                _svc = EntitlementService(_ent_user)
                _svc.check_advanced_filters()
        except EntitlementError as _af_err:
            return JsonResponse({
                'error': _af_err.message,
                'feature': _af_err.feature,
                'upgrade_to': _af_err.upgrade_to,
                'code': 'entitlement_exceeded',
            }, status=403)

    if experience and experience != 'all':
        exp_l = experience.lower()
        if exp_l == 'entry':
            qs = qs.filter(
                Q(experience__icontains='0-') | Q(experience__icontains='1-') |
                Q(experience__icontains='2-') | Q(experience__icontains='0 to') |
                Q(job_title__icontains='Associate') | Q(job_title__icontains='Analyst') |
                Q(job_title__icontains='Trainee') | Q(job_title__icontains='Graduate') |
                Q(job_title__icontains='Junior')
            )
        elif exp_l == 'mid':
            qs = qs.filter(
                Q(experience__icontains='3-') | Q(experience__icontains='4-') | Q(experience__icontains='5-')
            )
        elif exp_l == 'senior':
            qs = qs.filter(
                Q(experience__icontains='6-') | Q(experience__icontains='7-') |
                Q(experience__icontains='8-') | Q(experience__icontains='9-')
            )
        elif exp_l == 'lead':
            qs = qs.filter(
                Q(experience__icontains='10-') | Q(experience__icontains='11-') |
                Q(experience__icontains='12-') | Q(experience__icontains='15-') |
                Q(job_title__icontains='Lead') | Q(job_title__icontains='Head') |
                Q(job_title__icontains='Director') | Q(job_title__icontains='Principal') |
                Q(job_title__icontains='Chief')
            )
        else:
            qs = qs.filter(experience__icontains=experience)

    # PART 10: Flexible Category Filtering (All, Standard, Others, Uncategorized)
    if category and category.lower() != 'all':
        cat_l = category.lower().replace('-', '_').replace(' ', '_')
        if cat_l in ('uncategorized', 'none', 'null'):
            qs = qs.filter(UNCATEGORIZED_JOB_Q)
        elif cat_l in ('others', 'other', 'company_specific', 'other_/_company_specific'):
            qs = qs.filter(OTHERS_JOB_Q)
        elif cat_l in JOB_CATEGORY_MAP:
            qs = qs.filter(JOB_CATEGORY_MAP[cat_l])
        else:
            qs = qs.filter(Q(department__icontains=category) | Q(function__icontains=category))

    order_by_fields = JOB_SORT_OPTIONS.get(sort, JOB_SORT_OPTIONS['recent'])
    qs = qs.order_by(*order_by_fields)

    if request.GET.get('format') == 'csv' or request.GET.get('export') == 'csv':
        import io, csv
        from django.http import HttpResponse
        # Calculate capped rows for export
        _req_limit = int(request.GET.get('limit', 2000))
        _export_count = min(qs.count(), _req_limit)
        # ── Entitlement: export quota check ──────────────────────────
        if not (getattr(request, 'user', None) and request.user.is_authenticated):
            return JsonResponse({
                'error': 'Authentication required. Please sign in or choose an institutional plan to export data.',
                'code': 'unauthorized'
            }, status=401)
        _export_user = request.user
        _export_svc = EntitlementService(_export_user)
        try:
            _export_svc.check_export_quota(count=_export_count)
        except EntitlementError as _ex_err:
            return JsonResponse({
                'error': _ex_err.message,
                'feature': _ex_err.feature,
                'limit': _ex_err.limit,
                'current': _ex_err.current,
                'upgrade_to': _ex_err.upgrade_to,
                'code': 'entitlement_exceeded',
            }, status=403)
        # ── End entitlement check ────────────────────────────────────
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Job Row ID', 'Job ID', 'Company ID', 'Company Name', 'NSE Symbol', 'Sector', 'Job Title', 'Department', 'Location', 'Work Mode', 'Employment Type', 'Experience', 'ATS Platform', 'Application URL', 'Source URL', 'Status'])
        _rows_written = 0
        for j in qs[:_export_count]:
            item = serialize_job_item(j)
            writer.writerow([
                item['job_row_id'], item['job_id'], item['company_id'], item['company_name'],
                item['nse_symbol'], item['sector'], item['job_title'], item['department'],
                item['location'], item['work_mode'], item['employment_type'], item['experience'],
                item['ats_platform'], item['application_url'], item['source_url'], item['status']
            ])
            _rows_written += 1
        # ── Entitlement: record export usage ─────────────────────────
        if _export_user and _rows_written > 0:
            _export_svc.record_export_usage(count=_rows_written)
        # ── End record usage ─────────────────────────────────────────
        resp = HttpResponse(output.getvalue(), content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="impactbridge_verified_jobs.csv"'
        return resp

    has_filter = bool(
        q or company_id or company or location or state or department or
        work_mode or status or impact_only or
        (category and category.lower() != 'all') or
        (experience and experience.lower() != 'all')
    )
    cache_key = None
    if not has_filter and str(page) in ('1', 'None', '') and str(page_size) in ('12', '24') and sort == 'recent':
        cache_key = f"jobs_list_p{page}_ps{page_size}"
        cached_res = cache.get(cache_key)
        if cached_res is not None:
            return JsonResponse(cached_res, safe=False)

    total_count = None
    if not has_filter:
        from modules.admin_panel.snapshot_service import get_current_stats_snapshot
        stats_data, _, _, _ = get_current_stats_snapshot()
        total_count = stats_data.get('jobs_tracked')

    data = paginate_queryset(
        queryset=qs,
        serialize_func=lambda j: serialize_job_item(j, is_detail=False),
        page=page,
        page_size=page_size,
        fallback_limit=limit,
        total_count=total_count
    )
    resp = JsonResponse(data, safe=False)
    if is_unfiltered and str(page) in ('1', 'None', '') and str(page_size) in ('12', '24') and sort == 'recent':
        cache.set(f"jobs_list_json_p{page}_ps{page_size}", resp.content.decode('utf-8'), 60)
    return resp


def jobs_summary_api(request):
    """Job intelligence dashboard facets — served via precomputed authoritative snapshot."""
    from modules.admin_panel.snapshot_service import get_current_job_summary_snapshot
    if request.GET.get('refresh'):
        cache.delete('jobs_summary_snapshot_cache')
    data, is_stale, audit_run_id, data_as_of = get_current_job_summary_snapshot()
    return JsonResponse(data)


def job_detail_api(request, job_id):
    from modules.admin_panel.models import PreviewDummyJob
    is_dummy = str(job_id).startswith('DUMMY_') or str(job_id).startswith('dummy_')
    dummy_j = None
    if is_dummy:
        dummy_j = PreviewDummyJob.objects.filter(job_row_id=job_id).first()
    if not dummy_j and PreviewDummyJob.objects.filter(job_row_id=job_id).exists():
        dummy_j = PreviewDummyJob.objects.filter(job_row_id=job_id).first()
        is_dummy = True
    if is_dummy:
        if not dummy_j:
            dummy_j = PreviewDummyJob.objects.first()
        if dummy_j:
            return JsonResponse(dummy_j.as_preview_dict())
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'Authentication required. Please sign in or register for a free account to view complete job descriptions and application links.',
            'code': 'UNAUTHENTICATED',
            'login_url': f'/login/?next=/jobs/{job_id}/',
            'register_url': f'/register/?next=/jobs/{job_id}/'
        }, status=401)
    from modules.website.utils.entitlement_service import user_has_active_plan
    if not user_has_active_plan(request.user):
        return JsonResponse({
            'error': 'Subscription plan required. Please select a subscription plan to view complete job descriptions and application links.',
            'code': 'PLAN_REQUIRED',
            'plan_required': True,
            'pricing_url': '/?tab=pricing'
        }, status=403)
    """Retrieve detailed information for a specific job along with related openings.
    If details have not been fetched from the official portal yet, perform live on-demand extraction
    via UniversalJobDetailExtractor and persist the enriched fields.
    """
    force_refresh = request.GET.get('refresh', '').lower() in ('1', 'true', 'yes')
    cache_key = f"job_detail_data_{job_id}"
    if not force_refresh:
        cached_job = cache.get(cache_key)
        if cached_job is not None:
            return JsonResponse(cached_job)

    try:
        job = None
        if str(job_id).isdigit():
            job = Job.objects.select_related('company').filter(Q(job_row_id=int(job_id)) | Q(job_id=str(job_id))).first()
        else:
            job = Job.objects.select_related('company').filter(job_id=str(job_id)).first()

        if not job or not public_jobs(Job.objects.filter(pk=job.pk)).exists():
            return JsonResponse({'error': 'Job opening not found or unverified'}, status=404)

        # On-demand live extraction queued off the request path with 10-min rate limiting
        refresh_status = "IDLE"
        if force_refresh and job.application_url and job.application_url.startswith('http'):
            rate_key = f"job_refresh_ratelimit_{job.job_row_id}"
            status_key = f"job_refresh_status_{job.job_row_id}"

            if cache.get(rate_key):
                refresh_status = cache.get(status_key) or "RATE_LIMITED"
            else:
                cache.set(rate_key, True, 600)
                cache.set(status_key, "PENDING", 600)
                refresh_status = "PENDING"

                def _background_extract(job_pk, app_url):
                    try:
                        from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor
                        from django.utils import timezone
                        extracted = UniversalJobDetailExtractor.extract_from_url(app_url)
                        j = Job.objects.filter(pk=job_pk).first()
                        if not j:
                            cache.set(status_key, "FAILED", 600)
                            return
                        status = extracted.get('detail_fetch_status', 'EXTRACTION_FAILED')
                        updated_fields = ['detail_fetch_status', 'detail_fetched', 'detail_fetched_at']
                        j.detail_fetch_status = status
                        j.detail_fetched = (status == 'FETCHED')
                        j.detail_fetched_at = timezone.now().isoformat()

                        if j.detail_fetched:
                            for field_name in [
                                'job_description', 'description_raw', 'description_html', 'about_role',
                                'responsibilities', 'responsibilities_list', 'qualifications', 'requirements',
                                'preferred_qualifications', 'role_purpose', 'day_in_the_life',
                                'education', 'qualifications_education', 'experience', 'qualifications_experience',
                                'skills', 'required_skills', 'preferred_skills', 'technical_skills', 'behavioural_skills',
                                'benefits', 'employer_info', 'pay_band', 'salary', 'salary_text', 'salary_currency', 'currency',
                                'work_mode', 'employment_type', 'seniority_level', 'location', 'city', 'state', 'country',
                                'travel_required', 'shift', 'work_authorization', 'details_status', 'details_missing_fields'
                            ]:
                                val = extracted.get(field_name)
                                if val is not None and hasattr(j, field_name):
                                    setattr(j, field_name, val)
                                    updated_fields.append(field_name)

                            if extracted.get('structured_details'):
                                j.structured_details = extracted.get('structured_details')
                                updated_fields.append('structured_details')
                            j.details_scraped_at = timezone.now()
                            updated_fields.append('details_scraped_at')

                        j.save(update_fields=list(set(updated_fields)))
                        cache.set(status_key, "COMPLETE" if j.detail_fetched else "FAILED", 600)
                    except Exception as extract_err:
                        import logging
                        logging.getLogger(__name__).warning("Background job extraction failed for %s: %s", job_pk, extract_err)
                        cache.set(status_key, "FAILED", 600)

                import threading
                t = threading.Thread(target=_background_extract, args=(job.pk, job.application_url), daemon=True)
                t.start()

        data = serialize_job_item(job, is_detail=True)
        data['refresh_status'] = refresh_status
        related_qs = public_jobs(Job.objects.select_related('company').filter(
            company_id=job.company_id)).exclude(job_row_id=job.job_row_id).exclude(verification_status='LEGACY_UNVERIFIED')

        related_jobs_list = []
        if job.department:
            dept_related = list(related_qs.filter(department__icontains=job.department)[:4])
            related_jobs_list.extend(dept_related)

        if len(related_jobs_list) < 4:
            more_needed = 4 - len(related_jobs_list)
            existing_ids = [j.job_row_id for j in related_jobs_list]
            other_related = list(related_qs.exclude(job_row_id__in=existing_ids)[:more_needed])
            related_jobs_list.extend(other_related)

        data['related_jobs'] = [serialize_job_item(j, is_detail=False) for j in related_jobs_list]
        if not force_refresh:
            cache.set(cache_key, data, 60)
        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def job_refresh_status_api(request, job_id):
    if not request.user.is_authenticated:
        return JsonResponse({
            'error': 'Authentication required.',
            'code': 'UNAUTHENTICATED',
            'login_url': f'/login/?next=/jobs/{job_id}/',
            'register_url': f'/register/?next=/jobs/{job_id}/'
        }, status=401)
    """Returns background enrichment and scraping status for a job opening."""
    job = None
    if str(job_id).isdigit():
        job = Job.objects.filter(Q(job_row_id=int(job_id)) | Q(job_id=str(job_id))).first()
    else:
        job = Job.objects.filter(job_id=str(job_id)).first()

    if not job:
        return JsonResponse({'error': 'Job not found'}, status=404)

    status_key = f"job_refresh_status_{job.job_row_id}"
    st = cache.get(status_key) or ("COMPLETE" if job.detail_fetched else "IDLE")
    return JsonResponse({
        'job_row_id': job.job_row_id,
        'job_id': job.job_id,
        'status': st,
        'refresh_status': st,
        'detail_fetched': job.detail_fetched,
        'detail_fetched_at': job.detail_fetched_at,
        'details_status': getattr(job, 'details_status', 'MISSING')
    })


def jobs_filters_api(request):
    """
    Returns distinct locations, cities, states, countries, departments, and hiring companies
    extracted across all verified jobs for dynamic filter dropdown population.
    """
    cache_key = "job_filter_options_cache"
    if not request.GET.get('refresh'):
        cached = cache.get(cache_key)
        if cached is not None:
            return JsonResponse(cached)

    base_qs = public_jobs(Job.objects.all())

    # Locations
    raw_locs = (
        base_qs.exclude(location__isnull=True)
        .exclude(location='')
        .values('location')
        .annotate(cnt=Count('job_row_id'))
        .order_by('-cnt')
    )
    locations = [r['location'] for r in raw_locs if r['location']]

    # Cities
    raw_cities = (
        base_qs.exclude(city__isnull=True)
        .exclude(city='')
        .values('city')
        .annotate(cnt=Count('job_row_id'))
        .order_by('-cnt')
    )
    cities = [r['city'] for r in raw_cities if r['city']]

    # States
    raw_states = (
        base_qs.exclude(state__isnull=True)
        .exclude(state='')
        .values('state')
        .annotate(cnt=Count('job_row_id'))
        .order_by('-cnt')
    )
    states = [r['state'] for r in raw_states if r['state']]

    # Countries
    raw_countries = (
        base_qs.exclude(country__isnull=True)
        .exclude(country='')
        .values('country')
        .annotate(cnt=Count('job_row_id'))
        .order_by('-cnt')
    )
    countries = [r['country'] for r in raw_countries if r['country']]

    # Departments
    raw_depts = (
        base_qs.exclude(department__isnull=True)
        .exclude(department='')
        .values('department')
        .annotate(cnt=Count('job_row_id'))
        .order_by('-cnt')
    )
    departments = [r['department'] for r in raw_depts if r['department']]

    # Companies
    companies = list(
        Company.objects.filter(jobs__in=base_qs)
        .distinct()
        .values('company_id', 'company_name', 'nse_symbol')
        .order_by('company_name')
    )

    data = {
        'locations': locations,
        'cities': cities,
        'states': states,
        'countries': countries,
        'departments': departments,
        'companies': companies,
    }
    cache.set(cache_key, data, 120)
    return JsonResponse(data)



