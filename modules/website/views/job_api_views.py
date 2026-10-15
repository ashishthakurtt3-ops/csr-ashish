from django.http import JsonResponse
from django.db.models import Q, Count
from modules.admin_panel.models import Job, Company
from modules.website.utils.pagination import paginate_queryset

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
]

def apply_job_safety_filters(qs):
    """Filters out any UI navigation boilerplate defect titles and quarantined legacy seed data."""
    qs = qs.exclude(job_id__startswith='REQ-')
    qs = qs.exclude(verification_status__in=['LEGACY_UNVERIFIED', 'REJECTED', 'QUARANTINED'])
    for pattern in UI_NAV_DEFECT_PATTERNS:
        qs = qs.exclude(job_title__iexact=pattern).exclude(job_title__icontains=pattern)
    return qs



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


def serialize_job_item(j: Job):
    c = j.company
    raw_app_url = (j.application_url or '').strip()
    if raw_app_url and raw_app_url.lower() not in ('---', '--', '-', 'null', 'none', 'undefined') and raw_app_url.startswith('http'):
        app_url = raw_app_url
        if 'api.smartrecruiters.com/v1/companies/' in app_url and '/postings/' in app_url:
            app_url = app_url.replace('api.smartrecruiters.com/v1/companies/', 'jobs.smartrecruiters.com/').replace('/postings/', '/')
        if ' ' in app_url:
            import urllib.parse
            app_url = urllib.parse.quote(app_url, safe=':/?&=#%')
    else:
        app_url = None

    cname = c.company_name
    sym = c.nse_symbol
    careers_url = c.careers_url
    website_url = c.website_url

    if c.company_id == 'COMP_TOP200_025' or sym == 'ETERNAL' or 'eternal' in str(cname).lower():
        cname = 'Zomato Limited'
        sym = 'ZOMATO'
    elif c.company_id == 'COMP_TOP200_169' or sym == 'ACC' or 'acc limited' in str(cname).lower():
        website_url = 'https://www.acclimited.com/'
        careers_url = 'https://www.acclimited.com/'
    elif c.company_id == 'COMP_TOP200_082' or sym == 'AMBUJACEM' or 'ambuja cement' in str(cname).lower():
        website_url = 'https://www.ambujacement.com/'
        careers_url = 'https://www.ambujacement.com/'

    raw_dept = _clean_field_val(j.department)
    norm_cat = get_normalized_job_category(raw_dept, j.job_title, j.function)

    return {
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
        'job_title': j.job_title,
        'department': raw_dept,
        'original_category': raw_dept,
        'normalized_category': norm_cat,
        'team': _clean_field_val(j.team),
        'business_unit': _clean_field_val(j.business_unit),
        'function': _clean_field_val(j.function),
        'location': _clean_field_val(j.location),
        'city': _clean_field_val(j.city),
        'state': _clean_field_val(j.state),
        'country': _clean_field_val(j.country),
        'work_mode': _clean_field_val(j.work_mode),
        'employment_type': _clean_field_val(j.employment_type),
        'experience': _clean_field_val(j.experience),
        'education': _clean_field_val(j.education),
        'skills': _clean_field_val(j.skills),
        'salary': _clean_field_val(j.salary),
        'salary_min': str(j.salary_min) if j.salary_min else None,
        'salary_max': str(j.salary_max) if j.salary_max else None,
        'salary_currency': _clean_field_val(j.salary_currency),
        'pay_band': _clean_field_val(getattr(j, 'pay_band', None)),
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
        'source_url': j.source_url,
        'source_domain': j.source_domain,
        'retrieved_at': (j.retrieved_at.isoformat() if hasattr(j.retrieved_at, 'isoformat') else str(j.retrieved_at)) if j.retrieved_at else None,
        'last_checked_date': j.last_checked_date,
        'status': j.status,
        'verification_status': j.verification_status,
        'confidence': j.confidence,
        'link_status': j.link_status,
        'link_verified_at': j.link_verified_at,
        'data_provenance': j.data_provenance,
        'fingerprint': j.fingerprint,
        'evidence_text': j.evidence_text,
    }



def jobs_list_api(request):
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
    sort = request.GET.get('sort', 'recent')
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    limit = int(request.GET.get('limit', 2000))

    # Authoritative eligible jobs: strictly ACTIVE and verified/published with official source evidence
    qs = Job.objects.select_related('company').filter(
        status='ACTIVE',
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
    )
    qs = apply_job_safety_filters(qs)

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
        qs = qs.filter(location__icontains=location)
    if state and state != 'all':
        qs = qs.filter(state__icontains=state)
    if department and department != 'all':
        qs = qs.filter(department__icontains=department)
    if work_mode and work_mode != 'all':
        qs = qs.filter(work_mode=work_mode)
    if status and status != 'all':
        qs = qs.filter(status=status)
    if impact_only:
        qs = qs.filter(IMPACT_ROLE_FILTER)

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
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Job Row ID', 'Job ID', 'Company ID', 'Company Name', 'NSE Symbol', 'Sector', 'Job Title', 'Department', 'Location', 'Work Mode', 'Employment Type', 'Experience', 'ATS Platform', 'Application URL', 'Source URL', 'Status'])
        for j in qs:
            item = serialize_job_item(j)
            writer.writerow([
                item['job_row_id'], item['job_id'], item['company_id'], item['company_name'],
                item['nse_symbol'], item['sector'], item['job_title'], item['department'],
                item['location'], item['work_mode'], item['employment_type'], item['experience'],
                item['ats_platform'], item['application_url'], item['source_url'], item['status']
            ])
        resp = HttpResponse(output.getvalue(), content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="impactbridge_verified_jobs.csv"'
        return resp

    data = paginate_queryset(
        queryset=qs,
        serialize_func=serialize_job_item,
        page=page,
        page_size=page_size,
        fallback_limit=limit
    )
    return JsonResponse(data, safe=False)


def jobs_summary_api(request):
    """Job intelligence dashboard facets — strictly authoritative live verified records."""
    base_qs = Job.objects.filter(
        status='ACTIVE',
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
    )
    base_qs = apply_job_safety_filters(base_qs)

    total_roles = base_qs.count()
    active_roles = total_roles
    impact_roles = base_qs.filter(IMPACT_ROLE_FILTER).count()
    remote_roles = base_qs.filter(work_mode='Remote').count()
    hybrid_roles = base_qs.filter(work_mode='Hybrid').count()
    onsite_roles = base_qs.filter(work_mode='On-site').count()
    companies_hiring = base_qs.values('company_id').distinct().count()
    live_verified_links = total_roles

    by_dept = list(
        base_qs.values('department')
        .annotate(roles=Count('job_row_id'))
        .order_by('-roles')[:15]
    )
    by_loc = list(
        base_qs.values('location')
        .annotate(roles=Count('job_row_id'))
        .order_by('-roles')[:15]
    )
    by_comp = list(
        base_qs.values('company__company_name', 'company__nse_symbol')
        .annotate(roles=Count('job_row_id'))
        .order_by('-roles')[:20]
    )
    by_comp_formatted = [
        {'company_name': r['company__company_name'], 'nse_symbol': r['company__nse_symbol'], 'roles': r['roles']}
        for r in by_comp
    ]

    summary = {
        'total_roles': total_roles,
        'active_roles': active_roles,
        'impact_roles': impact_roles,
        'remote_roles': remote_roles,
        'hybrid_roles': hybrid_roles,
        'onsite_roles': onsite_roles,
        'companies_hiring': companies_hiring,
        'live_verified_links': live_verified_links,
        'by_department': by_dept,
        'by_location': by_loc,
        'by_company': by_comp_formatted,
    }
    return JsonResponse(summary)


def job_detail_api(request, job_id):
    """Retrieve detailed information for a specific job along with related openings."""
    try:
        job = None
        if str(job_id).isdigit():
            job = Job.objects.select_related('company').filter(Q(job_row_id=int(job_id)) | Q(job_id=str(job_id))).first()
        else:
            job = Job.objects.select_related('company').filter(job_id=str(job_id)).first()

        if not job:
            return JsonResponse({'error': 'Job not found'}, status=404)

        data = serialize_job_item(job)
        related_qs = Job.objects.select_related('company').filter(
            company_id=job.company_id,
            status='ACTIVE',
            verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
        ).exclude(job_row_id=job.job_row_id).exclude(verification_status='LEGACY_UNVERIFIED')
        related_qs = apply_job_safety_filters(related_qs)

        related_jobs_list = []
        if job.department:
            dept_related = list(related_qs.filter(department__icontains=job.department)[:4])
            related_jobs_list.extend(dept_related)

        if len(related_jobs_list) < 4:
            more_needed = 4 - len(related_jobs_list)
            existing_ids = [j.job_row_id for j in related_jobs_list]
            other_related = list(related_qs.exclude(job_row_id__in=existing_ids)[:more_needed])
            related_jobs_list.extend(other_related)

        data['related_jobs'] = [serialize_job_item(j) for j in related_jobs_list]
        return JsonResponse(data)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
