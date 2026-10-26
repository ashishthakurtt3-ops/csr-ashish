import csv
import io
import re
import urllib.parse
from typing import Optional
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from modules.admin_panel.models import CSRProject, CSROpportunity
from modules.website.utils.pagination import paginate_queryset

from modules.admin_panel.verification import (
    PUBLIC_VERIFICATION_STATUSES, public_records, NOT_AVAILABLE_TEXT, LOGIN_REQUIRED_TEXT, LINK_OK,
)
from modules.crawler_engine.normalizers import (
    clean_text, detect_csr_source_format, is_page_title_not_csr_project,
)

STANDARD_CSR_CATEGORIES = [
    'Healthcare & Sanitation',
    'Education & Skill Development',
    'Rural Development & Infrastructure',
    'Environment & Sustainability',
    'Women Empowerment & Livelihood',
    'Disaster Relief & Community Support',
    'Sports, Heritage & Culture',
]

UNCATEGORIZED_CSR_Q = (
    Q(category__isnull=True) | Q(category='') |
    Q(category__iexact='uncategorized') | Q(category__iexact='none') | Q(category__iexact='null')
)

HEALTHCARE_CSR_RAW_Q = Q(category__icontains='health') | Q(category__icontains='medic') | Q(category__icontains='sanitat') | Q(category__icontains='hospit')
EDUCATION_CSR_RAW_Q = Q(category__icontains='educat') | Q(category__icontains='school') | Q(category__icontains='skill') | Q(category__icontains='literacy')
RURAL_CSR_RAW_Q = Q(category__icontains='rural') | Q(category__icontains='infrastruct') | Q(category__icontains='communit') | Q(category__icontains='water')
ENVIRONMENT_CSR_RAW_Q = Q(category__icontains='environ') | Q(category__icontains='sustainab') | Q(category__icontains='renewab') | Q(category__icontains='green') | Q(category__icontains='tree')
WOMEN_CSR_RAW_Q = Q(category__icontains='women') | Q(category__icontains='gender') | Q(category__icontains='empower') | Q(category__icontains='livelihood')
RELIEF_CSR_RAW_Q = Q(category__icontains='relief') | Q(category__icontains='disaster') | Q(category__icontains='rehabilitat')
SPORTS_CSR_RAW_Q = Q(category__icontains='sport') | Q(category__icontains='culture') | Q(category__icontains='heritage') | Q(category__icontains='art')

HEALTHCARE_CSR_Q = ~UNCATEGORIZED_CSR_Q & HEALTHCARE_CSR_RAW_Q
EDUCATION_CSR_Q = ~UNCATEGORIZED_CSR_Q & ~HEALTHCARE_CSR_Q & EDUCATION_CSR_RAW_Q
RURAL_CSR_Q = ~UNCATEGORIZED_CSR_Q & ~HEALTHCARE_CSR_Q & ~EDUCATION_CSR_Q & RURAL_CSR_RAW_Q
ENVIRONMENT_CSR_Q = ~UNCATEGORIZED_CSR_Q & ~HEALTHCARE_CSR_Q & ~EDUCATION_CSR_Q & ~RURAL_CSR_Q & ENVIRONMENT_CSR_RAW_Q
WOMEN_CSR_Q = ~UNCATEGORIZED_CSR_Q & ~HEALTHCARE_CSR_Q & ~EDUCATION_CSR_Q & ~RURAL_CSR_Q & ~ENVIRONMENT_CSR_Q & WOMEN_CSR_RAW_Q
RELIEF_CSR_Q = ~UNCATEGORIZED_CSR_Q & ~HEALTHCARE_CSR_Q & ~EDUCATION_CSR_Q & ~RURAL_CSR_Q & ~ENVIRONMENT_CSR_Q & ~WOMEN_CSR_Q & RELIEF_CSR_RAW_Q
SPORTS_CSR_Q = ~UNCATEGORIZED_CSR_Q & ~HEALTHCARE_CSR_Q & ~EDUCATION_CSR_Q & ~RURAL_CSR_Q & ~ENVIRONMENT_CSR_Q & ~WOMEN_CSR_Q & ~RELIEF_CSR_Q & SPORTS_CSR_RAW_Q

STANDARD_CSR_FILTER_MAP = {
    'healthcare': HEALTHCARE_CSR_Q,
    'education': EDUCATION_CSR_Q,
    'rural': RURAL_CSR_Q,
    'environment': ENVIRONMENT_CSR_Q,
    'women': WOMEN_CSR_Q,
    'relief': RELIEF_CSR_Q,
    'sports': SPORTS_CSR_Q,
}

ALL_STANDARD_CSR_Q = (
    HEALTHCARE_CSR_Q | EDUCATION_CSR_Q | RURAL_CSR_Q | ENVIRONMENT_CSR_Q | WOMEN_CSR_Q | RELIEF_CSR_Q | SPORTS_CSR_Q
)
OTHERS_CSR_Q = ~UNCATEGORIZED_CSR_Q & ~ALL_STANDARD_CSR_Q


def get_normalized_csr_category(cat: str) -> Optional[str]:
    s = clean_text(cat)
    if not s:
        return None
    c_lower = s.lower()
    if any(k in c_lower for k in ('health', 'medic', 'sanitat', 'hospit')):
        return 'Healthcare & Sanitation'
    if any(k in c_lower for k in ('educat', 'school', 'skill', 'literacy')):
        return 'Education & Skill Development'
    if any(k in c_lower for k in ('rural', 'infrastruct', 'communit', 'water')):
        return 'Rural Development & Infrastructure'
    if any(k in c_lower for k in ('environ', 'sustainab', 'renewab', 'green', 'tree')):
        return 'Environment & Sustainability'
    if any(k in c_lower for k in ('women', 'gender', 'empower', 'livelihood')):
        return 'Women Empowerment & Livelihood'
    if any(k in c_lower for k in ('relief', 'disaster', 'rehabilitat')):
        return 'Disaster Relief & Community Support'
    if any(k in c_lower for k in ('sport', 'culture', 'heritage', 'art')):
        return 'Sports, Heritage & Culture'
    return s


def get_schedule_vii_classification(category: str, description: str = '') -> Optional[str]:
    """Maps explicit source category/description to Schedule VII item, or returns None if not stated."""
    cat_lower = (clean_text(category) or '').lower()
    desc_lower = (clean_text(description) or '').lower()
    if not cat_lower and not desc_lower:
        return None

    combined = f"{cat_lower} {desc_lower}"
    if any(k in combined for k in ['educat', 'school', 'skill', 'literacy', 'scholarship', 'vocational']):
        return 'Schedule VII, Item (ii): Promoting education, special education & employment enhancing vocational skills'
    if any(k in combined for k in ['health', 'medic', 'sanitat', 'hospit', 'malnutrition', 'hunger', 'nutrition']):
        return 'Schedule VII, Item (i): Promoting health care, preventive health care & sanitation'
    if any(k in combined for k in ['women', 'gender', 'empower']):
        return 'Schedule VII, Item (iii): Promoting gender equality & women empowerment'
    if any(k in combined for k in ['environ', 'sustainab', 'renewab', 'green', 'tree', 'ecological', 'biodiversity']):
        return 'Schedule VII, Item (iv): Ensuring environmental sustainability & ecological balance'
    if any(k in combined for k in ['sport', 'olympic', 'paralympic', 'athlete']):
        return 'Schedule VII, Item (vii): Training to promote rural sports & nationally recognised sports'
    if any(k in combined for k in ['rural', 'infrastruct', 'village', 'watershed', 'farmer', 'livelihood']):
        return 'Schedule VII, Item (x): Rural development projects'
    if any(k in combined for k in ['relief', 'disaster', 'rehabilitat']):
        return 'Schedule VII, Item (xii): Disaster management, relief, rehabilitation & reconstruction'
    if any(k in combined for k in ['art', 'culture', 'heritage']):
        return 'Schedule VII, Item (v): Protection of national heritage, art and culture'
    return None


def extract_implementing_partner(project_name: str, description: str = '') -> Optional[str]:
    combined = f"{project_name or ''} {description or ''}"
    partners = [
        'Akshaya Patra Foundation', 'Christel House India', 'Christel House',
        'The Apollo Foundation', 'Apollo Foundation', 'Teach for India',
        'Avanti Fellows', 'Jaljeevika', 'Dakshana Foundation', 'Dakshana',
        'SEARCH', 'Agami', 'Foundation for Economic Development',
        'Project Baala', 'IIMA', 'Indian Institute of Management Ahmedabad',
        'Billion Hearts Beating Foundation', 'SACHi'
    ]
    for p in partners:
        if p.lower() in combined.lower():
            return p
    return None


def extract_reporting_period(discovered_date: str, text: str = '') -> Optional[str]:
    """Extracts FY reporting period ONLY when explicitly present in source text or date; never guesses."""
    for candidate in (text or '', str(discovered_date or '')):
        if not candidate:
            continue
        m = re.search(r'\b(FY\s*20\d{2}\s*[-–]\s*\d{2,4}|20\d{2}\s*[-–]\s*\d{2,4})\b', candidate, re.IGNORECASE)
        if m:
            val = re.sub(r'\s+', ' ', m.group(1)).upper()
            return val if val.startswith('FY') else f"FY {val}"
    return None


def _valid_http_url(u: Optional[str]) -> Optional[str]:
    s = clean_text(u)
    if not s or not s.lower().startswith(('http://', 'https://')) or 'google.com/search' in s.lower():
        return None
    if ' ' in s:
        s = urllib.parse.quote(s, safe=':/?&=#%')
    return s


def _company_best_csr_webpage(c) -> Optional[str]:
    if not c:
        return None
    for field in ('csr_portal_url', 'foundation_url', 'sustainability_url', 'esg_url', 'brsr_url', 'annual_report_url'):
        u = _valid_http_url(getattr(c, field, None))
        if u:
            return u
    return None


def get_verbatim_csr_budget_display(p: CSRProject) -> str:
    """Exact-Match Standard d): A budget is displayed only if the same figure appears verbatim in the project's own source page/PDF, shown exactly as written with its source link. Otherwise show 'Not disclosed'. Never display a parsed or totalled number."""
    candidate = clean_text(getattr(p, 'raw_budget_text', None) or p.budget)
    if not candidate:
        return "Not disclosed"
    cand_lower = candidate.lower()
    if cand_lower in ('rs,', 'inr,', 'nan', 'none', 'null', 'verified on official portal', 'statutory annual filing', 'not available', 'refer official'):
        return "Not disclosed"
    if not any(char.isdigit() for char in candidate):
        return "Not disclosed"

    evidence = (p.evidence_text or '')
    if evidence:
        import re
        norm_candidate = re.sub(r'\s+', ' ', candidate).strip()
        norm_evidence = re.sub(r'\s+', ' ', evidence).strip()
        if norm_candidate.lower() in norm_evidence.lower():
            return candidate
        m = re.search(r'[\d,\.]+\s*(?:crore|cr|lakh|lac|k|million|billion)?', norm_candidate, re.IGNORECASE)
        if m and m.group(0).strip() and len(m.group(0).strip()) > 1:
            if m.group(0).strip().lower() in norm_evidence.lower():
                return candidate
        return "Not disclosed"
    return "Not disclosed"


def serialize_project_item(p: CSRProject):
    c = p.company
    from modules.admin_panel.verification import format_relative_time
    raw_category = clean_text(getattr(p, 'raw_category', None) or p.category)
    norm_category = get_normalized_csr_category(raw_category) if raw_category else None
    cleaned_title = clean_text(getattr(p, 'raw_project_name', None) or p.project_name)

    # Strictly use the project's own source URL (never fall back to generic company homepage)
    src_url = _valid_http_url(p.source_url)
    company_csr_url = _company_best_csr_webpage(c)
    source_format = detect_csr_source_format(src_url) if src_url else (
        LOGIN_REQUIRED_TEXT if (c and c.csr_access == 'LOGIN_REQUIRED') else NOT_AVAILABLE_TEXT
    )
    company_csr_format = detect_csr_source_format(company_csr_url) if company_csr_url else (
        LOGIN_REQUIRED_TEXT if (c and c.csr_access == 'LOGIN_REQUIRED') else NOT_AVAILABLE_TEXT
    )

    verbatim_budget = get_verbatim_csr_budget_display(p)

    desc = clean_text(p.description)
    sch_vii = get_schedule_vii_classification(raw_category or norm_category, desc or '')
    partner = extract_implementing_partner(cleaned_title or '', desc or '')
    fy_period = extract_reporting_period(p.discovered_date, f"{cleaned_title or ''} {desc or ''} {src_url or ''}")

    retrieved_str = None
    if p.retrieved_at:
        try:
            retrieved_str = p.retrieved_at.isoformat()
        except Exception:
            retrieved_str = str(p.retrieved_at)

    verified_dt = getattr(p, 'last_reconciled_at', None) or p.link_verified_at or p.retrieved_at
    rel_time = format_relative_time(verified_dt)
    verified_badge_text = f"As listed on the official site - verified {rel_time}"

    is_company_unverifiable = bool(
        c and ((c.csr_access in ('LOGIN_REQUIRED', 'NOT_PUBLISHED')) or 
        (c.verification_status not in ('VERIFIED', 'SOURCE_CONFIRMED')))
    )

    return {
        'csr_id': p.csr_id,
        'company_id': p.company_id,
        'project_name': cleaned_title,
        'raw_project_name': cleaned_title,
        'category': raw_category,
        'raw_category': raw_category,
        'original_category': raw_category,
        'normalized_category': norm_category,
        'schedule_vii_classification': sch_vii,
        'implementing_partner': partner,
        'reporting_period': fy_period,
        'description': desc,
        'geographic_location': clean_text(getattr(p, 'raw_location', None) or p.geographic_location),
        'raw_location': clean_text(getattr(p, 'raw_location', None) or p.geographic_location),
        'state': clean_text(p.state),
        'budget': None if verbatim_budget == "Not disclosed" else verbatim_budget,
        'raw_budget_text': getattr(p, 'raw_budget_text', None),
        'allocated_budget_inr': None if verbatim_budget == "Not disclosed" else verbatim_budget,
        'budget_display': verbatim_budget,
        'spent_budget_inr': None,
        'source_url': src_url,
        'source_document_url': src_url,
        'source_format': source_format,
        'company_csr_webpage_url': company_csr_url,
        'company_csr_format': company_csr_format,
        'discovered_date': clean_text(p.discovered_date),
        'last_verified_date': clean_text(p.last_verified_date),
        'confidence': p.confidence,
        'link_status': p.link_status or 'PUBLISHED',
        'link_verified_at': p.link_verified_at,
        'fingerprint': p.fingerprint,
        'verification_status': p.verification_status,
        'verification_reason': clean_text(p.verification_reason),
        'evidence_text': p.evidence_text,
        'evidence_locator': p.evidence_locator,
        'content_hash': p.content_hash,
        'retrieved_at': retrieved_str,
        'company_name': c.company_name if c else None,
        'legal_name': c.legal_name if c else None,
        'nse_symbol': c.nse_symbol if c else None,
        'cin': c.cin if c else None,
        'sector': clean_text(c.sector) if c else None,
        'headquarters': clean_text(c.headquarters) if c else None,
        'website_url': _valid_http_url(c.website_url) if c else None,
        'csr_portal_url': _valid_http_url(c.csr_portal_url) if c else None,
        'sustainability_url': _valid_http_url(c.sustainability_url) if c else None,
        'esg_url': _valid_http_url(c.esg_url) if c else None,
        'foundation_url': _valid_http_url(c.foundation_url) if c else None,
        'annual_report_url': _valid_http_url(c.annual_report_url) if c else None,
        'brsr_url': _valid_http_url(c.brsr_url) if c else None,
        'csr_access': c.csr_access if c else 'UNKNOWN',
        'csr_access_text': LOGIN_REQUIRED_TEXT if (c and c.csr_access == 'LOGIN_REQUIRED') else None,
        'data_access_note': c.data_access_note if c else None,
        'not_available_text': NOT_AVAILABLE_TEXT,
        'login_required_text': LOGIN_REQUIRED_TEXT,
        'field_source': getattr(p, 'field_source', None) or {},
        'verified_badge_text': verified_badge_text,
        'verified_relative_time': rel_time,
        'is_company_unverifiable': is_company_unverifiable,
        'last_reconciled_at': (p.last_reconciled_at.isoformat() if hasattr(p.last_reconciled_at, 'isoformat') else str(p.last_reconciled_at)) if getattr(p, 'last_reconciled_at', None) else None,
        'mismatch_reason': getattr(p, 'mismatch_reason', None),
        'mismatch_diff': getattr(p, 'mismatch_diff', None),
    }


def csr_project_detail_api(request, csr_id):
    """Retrieve detailed information for a specific CSR project along with related initiatives and company CSR links."""
    try:
        project = public_records(CSRProject.objects.select_related('company')).filter(
            csr_id=int(csr_id)
        ).first()
        if not project:
            return JsonResponse({'error': 'CSR project not found or not verified'}, status=404)

        data = serialize_project_item(project)

        related_qs = public_records(CSRProject.objects.select_related('company')).filter(
            company_id=project.company_id
        ).exclude(csr_id=project.csr_id)

        data['related_projects'] = [
            serialize_project_item(rp) for rp in related_qs[:12]
            if not is_page_title_not_csr_project(rp.project_name, rp.company.company_name if rp.company else None)
        ]
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def serialize_opportunity_item(o: CSROpportunity):
    c = o.company
    raw_category = clean_text(o.category)
    norm_category = get_normalized_csr_category(raw_category) if raw_category else None
    cleaned_title = clean_text(o.title)

    # Strictly use the opportunity's own portal_url or source_url — never fall back to company homepage
    p_url = _valid_http_url(o.portal_url) or _valid_http_url(o.source_url)
    company_csr_url = _company_best_csr_webpage(c)

    return {
        'opp_id': o.opp_id,
        'company_id': o.company_id,
        'title': cleaned_title,
        'opportunity_type': clean_text(o.opportunity_type),
        'category': raw_category,
        'original_category': raw_category,
        'normalized_category': norm_category,
        'submission_deadline': clean_text(o.submission_deadline),
        'portal_url': p_url,
        'application_url': p_url,
        'submission_url': p_url,
        'source_url': _valid_http_url(o.source_url),
        'company_csr_webpage_url': company_csr_url,
        'requirements': clean_text(o.requirements),
        'budget': None,
        'estimated_grant': None,
        'status': o.status,
        'verification_status': o.verification_status,
        'confidence': o.confidence,
        'link_status': o.link_status,
        'link_verified_at': o.link_verified_at,
        'fingerprint': o.fingerprint,
        'company_name': c.company_name if c else None,
        'nse_symbol': c.nse_symbol if c else None,
        'website_url': _valid_http_url(c.website_url) if c else None,
        'csr_portal_url': _valid_http_url(c.csr_portal_url) if c else None,
        'sector': clean_text(c.sector) if c else None,
        'csr_access': c.csr_access if c else 'UNKNOWN',
        'csr_access_text': LOGIN_REQUIRED_TEXT if (c and c.csr_access == 'LOGIN_REQUIRED') else None,
        'not_available_text': NOT_AVAILABLE_TEXT,
        'login_required_text': LOGIN_REQUIRED_TEXT,
    }


def csr_projects_api(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    company = request.GET.get('company', '').strip() or request.GET.get('company_id', '').strip()
    state = request.GET.get('state', '').strip()
    fy = request.GET.get('fy', '').strip()
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    limit = int(request.GET.get('limit', 5000))

    status = request.GET.get('status', '').strip()

    # Unified verified rule: strictly PUBLIC_VERIFICATION_STATUSES with non-empty source_url and evidence_text
    qs = public_records(CSRProject.objects.select_related('company')).exclude(
        source_url__isnull=True
    ).exclude(source_url='').exclude(
        evidence_text__isnull=True
    ).exclude(evidence_text='')

    if q:
        qs = qs.filter(
            Q(project_name__icontains=q) |
            Q(description__icontains=q) |
            Q(company__company_name__icontains=q) |
            Q(geographic_location__icontains=q) |
            Q(state__icontains=q) |
            Q(category__icontains=q)
        )

    if status and status.lower() != 'all':
        qs = qs.filter(Q(link_status__iexact=status) | Q(verification_status__iexact=status))

    if company and company.lower() != 'all':
        qs = qs.filter(
            Q(company__company_id=company) |
            Q(company__company_name__icontains=company) |
            Q(company__nse_symbol__iexact=company)
        )

    if category and category.lower() != 'all':
        cat_l = category.lower()
        if cat_l in ('uncategorized', 'none', 'null'):
            qs = qs.filter(UNCATEGORIZED_CSR_Q)
        elif cat_l in ('others', 'other', 'company-specific', 'other / company-specific'):
            qs = qs.filter(OTHERS_CSR_Q)
        elif cat_l in STANDARD_CSR_FILTER_MAP:
            qs = qs.filter(STANDARD_CSR_FILTER_MAP[cat_l])
        else:
            qs = qs.filter(category__icontains=category)

    if state and state != 'all':
        qs = qs.filter(Q(state__icontains=state) | Q(geographic_location__icontains=state))
    if fy and fy != 'all':
        qs = qs.filter(discovered_date__icontains=fy)

    qs = qs.order_by('-confidence', '-csr_id')

    if request.GET.get('format') == 'csv' or request.GET.get('export') == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Project ID', 'Company Name', 'NSE Symbol', 'Sector', 'Project Title',
            'Focus Area (Theme)', 'Schedule VII Classification', 'State & District',
            'Disclosed Budget (INR)', 'Actual Expenditure (INR)', 'Reporting Period',
            'Implementing Agency / Partner', 'Company CSR Webpage URL', 'Source Document URL',
            'Source Format', 'Evidence Locator', 'Verification Status'
        ])
        for p in qs:
            item = serialize_project_item(p)
            writer.writerow([
                p.csr_id,
                item.get('company_name') or NOT_AVAILABLE_TEXT,
                item.get('nse_symbol') or NOT_AVAILABLE_TEXT,
                item.get('sector') or NOT_AVAILABLE_TEXT,
                item.get('project_name') or NOT_AVAILABLE_TEXT,
                item.get('normalized_category') or item.get('category') or NOT_AVAILABLE_TEXT,
                item.get('schedule_vii_classification') or NOT_AVAILABLE_TEXT,
                item.get('geographic_location') or item.get('state') or NOT_AVAILABLE_TEXT,
                item.get('budget') or NOT_AVAILABLE_TEXT,
                item.get('spent_budget_inr') or NOT_AVAILABLE_TEXT,
                item.get('reporting_period') or NOT_AVAILABLE_TEXT,
                item.get('implementing_partner') or NOT_AVAILABLE_TEXT,
                item.get('company_csr_webpage_url') or NOT_AVAILABLE_TEXT,
                item.get('source_url') or NOT_AVAILABLE_TEXT,
                item.get('source_format') or NOT_AVAILABLE_TEXT,
                p.evidence_locator or NOT_AVAILABLE_TEXT,
                item.get('verification_status') or 'PUBLISHED',
            ])
        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="impactbridge_csr_projects.csv"'
        return response

    data = paginate_queryset(
        queryset=qs,
        serialize_func=serialize_project_item,
        page=page,
        page_size=page_size,
        fallback_limit=limit
    )
    return JsonResponse(data, safe=False)


def csr_opportunities_api(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    company = request.GET.get('company', '').strip() or request.GET.get('company_id', '').strip()
    opp_type = request.GET.get('opp_type', '').strip()
    scope = request.GET.get('scope', '').strip().lower()
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    limit = int(request.GET.get('limit', 500))

    # Strictly verified records (PUBLIC_VERIFICATION_STATUSES) with status='OPEN', source URL and evidence_text
    qs = public_records(CSROpportunity.objects.select_related('company')).filter(status='OPEN').exclude(
        (Q(source_url__isnull=True) | Q(source_url='')) & (Q(portal_url__isnull=True) | Q(portal_url=''))
    ).exclude(
        evidence_text__isnull=True
    ).exclude(evidence_text='')

    if scope in ('procurement', 'vendor', 'b2b'):
        qs = qs.filter(opportunity_type='Procurement / Vendor EOI')
    elif scope in ('all', 'both', 'combined'):
        pass
    else:
        qs = qs.exclude(opportunity_type='Procurement / Vendor EOI')

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(requirements__icontains=q) |
            Q(company__company_name__icontains=q)
        )

    if company and company.lower() != 'all':
        qs = qs.filter(
            Q(company__company_id=company) |
            Q(company__company_name__icontains=company) |
            Q(company__nse_symbol__iexact=company)
        )

    if category and category.lower() != 'all':
        cat_l = category.lower()
        if cat_l in ('uncategorized', 'none', 'null'):
            qs = qs.filter(UNCATEGORIZED_CSR_Q)
        elif cat_l in ('others', 'other', 'company-specific', 'other / company-specific'):
            qs = qs.filter(OTHERS_CSR_Q)
        elif cat_l in STANDARD_CSR_FILTER_MAP:
            qs = qs.filter(STANDARD_CSR_FILTER_MAP[cat_l])
        else:
            qs = qs.filter(category__icontains=category)

    if opp_type and opp_type != 'all':
        qs = qs.filter(opportunity_type=opp_type)

    qs = qs.order_by('-opp_id')

    if request.GET.get('format') == 'csv' or request.GET.get('export') == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Opportunity ID', 'Company ID', 'Company Name', 'Title', 'Type', 'Category', 'Normalized Category', 'Deadline', 'Status', 'Portal URL', 'Source URL', 'Verification Status'])
        for o in qs:
            c = o.company
            writer.writerow([
                o.opp_id,
                o.company_id,
                c.company_name if c else NOT_AVAILABLE_TEXT,
                o.title or NOT_AVAILABLE_TEXT,
                o.opportunity_type or NOT_AVAILABLE_TEXT,
                o.category or NOT_AVAILABLE_TEXT,
                get_normalized_csr_category(o.category) or NOT_AVAILABLE_TEXT,
                o.submission_deadline or NOT_AVAILABLE_TEXT,
                o.status,
                o.portal_url or NOT_AVAILABLE_TEXT,
                o.source_url or NOT_AVAILABLE_TEXT,
                o.verification_status,
            ])
        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="impactbridge_csr_opportunities.csv"'
        return response

    data = paginate_queryset(
        queryset=qs,
        serialize_func=serialize_opportunity_item,
        page=page,
        page_size=page_size,
        fallback_limit=limit
    )
    return JsonResponse(data, safe=False)
