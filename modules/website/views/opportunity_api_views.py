import csv
import io
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from modules.admin_panel.models import CSRProject, CSROpportunity
from modules.website.utils.pagination import paginate_queryset

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


def get_normalized_csr_category(cat: str) -> str:
    if not cat or cat.strip().lower() in ('uncategorized', 'none', 'null', ''):
        return 'Uncategorized'
    c_lower = cat.lower()
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
    return 'Other / Company-specific'


def get_schedule_vii_classification(category: str, description: str = '') -> str:
    cat_lower = (category or '').lower()
    desc_lower = (description or '').lower()
    
    # 1. Primary classification by explicit category
    if any(k in cat_lower for k in ['educat', 'school', 'skill', 'literacy', 'scholarship', 'vocational']):
        return 'Schedule VII, Item (ii): Promoting education, special education & employment enhancing vocational skills'
    if any(k in cat_lower for k in ['health', 'medic', 'sanitat', 'hospit', 'malnutrition', 'hunger', 'nutrition']):
        return 'Schedule VII, Item (i): Promoting health care, preventive health care & sanitation'
    if any(k in cat_lower for k in ['women', 'gender', 'empower']):
        return 'Schedule VII, Item (iii): Promoting gender equality & women empowerment'
    if any(k in cat_lower for k in ['environ', 'sustainab', 'renewab', 'green', 'tree', 'ecological', 'biodiversity']):
        return 'Schedule VII, Item (iv): Ensuring environmental sustainability & ecological balance'
    if any(k in cat_lower for k in ['sport', 'olympic', 'paralympic']):
        return 'Schedule VII, Item (vii): Training to promote rural sports & nationally recognised sports'
    if any(k in cat_lower for k in ['rural', 'infrastruct', 'village', 'watershed']):
        return 'Schedule VII, Item (x): Rural development projects'
    if any(k in cat_lower for k in ['relief', 'disaster', 'rehabilitat']):
        return 'Schedule VII, Item (xii): Disaster management, relief, rehabilitation & reconstruction'

    # 2. Secondary classification by description keywords
    combined = f"{cat_lower} {desc_lower}"
    if any(k in combined for k in ['educat', 'school', 'skill', 'literacy', 'scholarship', 'vocational', 'iit', 'jee', 'learning', 'fellow']):
        return 'Schedule VII, Item (ii): Promoting education, special education & employment enhancing vocational skills'
    if any(k in combined for k in ['health', 'medic', 'sanitat', 'hospit', 'malnutrition', 'hunger', 'doctor', 'ambulance']):
        return 'Schedule VII, Item (i): Promoting health care, preventive health care & sanitation'
    if any(k in combined for k in ['women', 'gender', 'empower', 'hostel', 'orphan', 'shg', 'maternal']):
        return 'Schedule VII, Item (iii): Promoting gender equality & women empowerment'
    if any(k in combined for k in ['environ', 'sustainab', 'renewab', 'green', 'tree', 'ecological', 'biodiversity', 'solar', 'carbon']):
        return 'Schedule VII, Item (iv): Ensuring environmental sustainability & ecological balance'
    if any(k in combined for k in ['sport', 'olympic', 'paralympic', 'champion', 'athlete']):
        return 'Schedule VII, Item (vii): Training to promote rural sports & nationally recognised sports'
    if any(k in combined for k in ['rural', 'infrastruct', 'village', 'watershed', 'farmland', 'farmer', 'livelihood']):
        return 'Schedule VII, Item (x): Rural development projects'
    if any(k in combined for k in ['relief', 'disaster', 'rehabilitat', 'covid']):
        return 'Schedule VII, Item (xii): Disaster management, relief, rehabilitation & reconstruction'
    if any(k in combined for k in ['art', 'culture', 'heritage']):
        return 'Schedule VII, Item (v): Protection of national heritage, art and culture'
    return 'Schedule VII, Item (xi): Slum area development / Other statutory causes'


def extract_implementing_partner(project_name: str, description: str = '') -> str:
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


def extract_reporting_period(discovered_date: str, text: str = '') -> str:
    if discovered_date and any(c.isdigit() for c in str(discovered_date)):
        return str(discovered_date)
    if text:
        import re
        m = re.search(r'\b(FY\s*20\d{2}[-–]\d{2,4}|20\d{2}[-–]\d{2,4})\b', text, re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return None


def serialize_project_item(p: CSRProject):
    c = p.company
    raw_category = p.category if p.category else None
    norm_category = get_normalized_csr_category(p.category) if p.category else None
    cleaned_title = ' '.join((p.project_name or '').split()).strip()

    src_url = (p.source_url or '').strip()
    if ' ' in src_url:
        import urllib.parse
        src_url = urllib.parse.quote(src_url, safe=':/?&=#%')
    if not src_url and c:
        src_url = c.csr_portal_url or c.website_url or ''

    # Clean budget: strictly reject malformed strings like "rs,", "NaN", "None" or strings without digits
    raw_budget = (p.budget or '').strip()
    if raw_budget.lower() in ('rs,', 'inr,', 'nan', 'none', 'null', ''):
        clean_budget = None
    elif not any(char.isdigit() for char in raw_budget):
        clean_budget = None
    else:
        clean_budget = raw_budget

    desc = p.description or ''
    sch_vii = get_schedule_vii_classification(raw_category or norm_category, desc)
    partner = extract_implementing_partner(cleaned_title, desc)
    fy_period = extract_reporting_period(p.discovered_date, f"{cleaned_title} {desc}")

    retrieved_str = None
    if p.retrieved_at:
        try:
            retrieved_str = p.retrieved_at.isoformat()
        except Exception:
            retrieved_str = str(p.retrieved_at)

    return {
        'csr_id': p.csr_id,
        'company_id': p.company_id,
        'project_name': cleaned_title,
        'category': raw_category,
        'original_category': raw_category,
        'normalized_category': norm_category,
        'schedule_vii_classification': sch_vii,
        'implementing_partner': partner,
        'reporting_period': fy_period,
        'description': p.description,
        'geographic_location': p.geographic_location,
        'state': p.state,
        'budget': clean_budget,
        'allocated_budget_inr': clean_budget,
        'spent_budget_inr': None,
        'source_url': src_url,
        'source_document_url': src_url,
        'discovered_date': p.discovered_date,
        'last_verified_date': p.last_verified_date,
        'confidence': p.confidence,
        'link_status': p.link_status or 'ACTIVE',
        'link_verified_at': p.link_verified_at,
        'fingerprint': p.fingerprint,
        'verification_status': p.verification_status,
        'verification_reason': p.verification_reason or 'Source-verified statutory Section 135 initiative.',
        'evidence_text': p.evidence_text,
        'evidence_locator': p.evidence_locator,
        'content_hash': p.content_hash,
        'retrieved_at': retrieved_str,
        'company_name': c.company_name if c else None,
        'legal_name': c.legal_name if c else None,
        'nse_symbol': c.nse_symbol if c else None,
        'cin': c.cin if c else None,
        'sector': c.sector if c else None,
        'headquarters': c.headquarters if c else None,
        'website_url': c.website_url if c else None,
        'csr_portal_url': c.csr_portal_url if c else None,
    }


def csr_project_detail_api(request, csr_id):
    """Retrieve detailed information for a specific CSR project along with related initiatives."""
    try:
        project = CSRProject.objects.select_related('company').filter(
            csr_id=int(csr_id),
            verification_status='PUBLISHED'
        ).first()
        if not project:
            return JsonResponse({'error': 'CSR project not found or not published'}, status=404)

        data = serialize_project_item(project)

        # Related projects from the same company (only real eligible published records, excluding this one)
        related_qs = CSRProject.objects.select_related('company').filter(
            company_id=project.company_id,
            verification_status='PUBLISHED'
        ).exclude(csr_id=project.csr_id)

        data['related_projects'] = [serialize_project_item(rp) for rp in related_qs[:6]]
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def serialize_opportunity_item(o: CSROpportunity):
    c = o.company
    raw_category = o.category if o.category else None
    norm_category = get_normalized_csr_category(o.category) if o.category else None
    cleaned_title = ' '.join((o.title or '').split()).strip()

    p_url = (o.portal_url or '').strip()
    if ' ' in p_url:
        import urllib.parse
        p_url = urllib.parse.quote(p_url, safe=':/?&=#%')
    if not p_url and c:
        p_url = c.csr_portal_url or c.website_url or ''

    return {
        'opp_id': o.opp_id,
        'company_id': o.company_id,
        'title': cleaned_title,
        'opportunity_type': o.opportunity_type,
        'category': raw_category,
        'original_category': raw_category,
        'normalized_category': norm_category,
        'submission_deadline': o.submission_deadline if o.submission_deadline else None,
        'portal_url': p_url,
        'application_url': p_url,
        'submission_url': p_url,
        'requirements': o.requirements,
        'status': o.status,
        'confidence': o.confidence,
        'link_status': o.link_status,
        'link_verified_at': o.link_verified_at,
        'fingerprint': o.fingerprint,
        'company_name': c.company_name if c else None,
        'nse_symbol': c.nse_symbol if c else None,
        'website_url': c.website_url if c else None,
        'sector': c.sector if c else None,
    }


def csr_projects_api(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    company = request.GET.get('company', '').strip() or request.GET.get('company_id', '').strip()
    state = request.GET.get('state', '').strip()
    fy = request.GET.get('fy', '').strip()
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    limit = int(request.GET.get('limit', 200))

    status = request.GET.get('status', '').strip()

    # Authoritative publication filter: strictly genuine verified published records
    qs = CSRProject.objects.select_related('company').filter(
        verification_status='PUBLISHED'
    )

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

    # PART 10: Flexible Category Filtering (All, Standard, Others, Uncategorized)
    if category and category.lower() != 'all':
        cat_l = category.lower()
        if cat_l in ('uncategorized', 'none', 'null'):
            qs = qs.filter(UNCATEGORIZED_CSR_Q)
        elif cat_l in ('others', 'other', 'company-specific', 'other / company-specific'):
            # Records not falling into standard categories, but have a category value
            qs = qs.filter(OTHERS_CSR_Q)
        elif cat_l in STANDARD_CSR_FILTER_MAP:
            qs = qs.filter(STANDARD_CSR_FILTER_MAP[cat_l])
        else:
            # Matches any specific category string
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
            'Disclosed Budget (INR)', 'Actual Expenditure (INR)', 'Status / Period',
            'Implementing Agency / Partner', 'Source Document URL', 'Evidence Locator', 'Verification Status'
        ])
        for p in qs:
            item = serialize_project_item(p)
            c = p.company
            writer.writerow([
                p.csr_id,
                item.get('company_name') or '',
                item.get('nse_symbol') or '',
                item.get('sector') or '',
                item.get('project_name') or '',
                item.get('normalized_category') or item.get('category') or '',
                item.get('schedule_vii_classification') or '',
                item.get('geographic_location') or item.get('state') or 'Not mentioned by source',
                item.get('budget') or 'Not mentioned by source',
                item.get('spent_budget_inr') or 'Not mentioned by source',
                item.get('reporting_period') or item.get('status') or 'Active',
                item.get('implementing_partner') or 'Direct Implementation',
                item.get('source_url') or '',
                p.evidence_locator or '',
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

    # Strictly published & extracted records, excluding quarantined legacy records
    qs = CSROpportunity.objects.select_related('company').exclude(
        verification_status__in=['LEGACY_UNVERIFIED', 'REJECTED', 'FETCH_FAILED', 'INVALID_SOURCE', 'BLOCKED']
    )

    # Default customer-facing scope is CSR-only ('Grant / RFP'); procurement notices require explicit scope
    if scope in ('procurement', 'vendor', 'b2b'):
        qs = qs.filter(opportunity_type='Procurement / Vendor EOI')
    elif scope in ('all', 'both', 'combined'):
        pass
    else:
        # Default customer-facing scope: CSR / Social Impact Grants and RFPs ONLY
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
                c.company_name if c else '',
                o.title,
                o.opportunity_type,
                o.category or '',
                get_normalized_csr_category(o.category),
                o.submission_deadline or '',
                o.status,
                o.portal_url or '',
                o.source_url or '',
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
