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

JOB_SORT_OPTIONS = {
    'recent': ['-last_checked_date', '-job_row_id'],
    'company': ['company__company_name', 'job_title'],
    'title': ['job_title'],
    'seniority': ['-experience', '-job_row_id'],
    'experience': ['-experience', '-job_row_id'],
}


def serialize_job_item(j: Job):
    c = j.company
    app_url = j.application_url or ''
    if not app_url or '---' in app_url or not app_url.startswith('http'):
        app_url = c.careers_url or c.website_url or app_url

    cname = c.company_name
    sym = c.nse_symbol
    if c.company_id == 'COMP_TOP200_025' or sym == 'ETERNAL' or 'eternal' in str(cname).lower():
        cname = 'Zomato Limited'
        sym = 'ZOMATO'

    return {
        'job_row_id': j.job_row_id,
        'company_id': j.company_id,
        'company_name': cname,
        'nse_symbol': sym,
        'website_url': c.website_url,
        'sector': c.sector,
        'careers_url': c.careers_url,
        'job_id': j.job_id,
        'job_title': j.job_title,
        'department': j.department,
        'function': j.function,
        'location': j.location,
        'state': j.state,
        'country': j.country,
        'work_mode': j.work_mode,
        'employment_type': j.employment_type,
        'experience': j.experience,
        'education': j.education,
        'skills': j.skills,
        'salary': j.salary,
        'job_description': j.job_description,
        'posted_date': j.posted_date,
        'closing_date': j.closing_date,
        'application_url': app_url,
        'source_url': j.source_url,
        'last_checked_date': j.last_checked_date,
        'status': j.status,
        'confidence': j.confidence,
        'link_status': j.link_status,
        'link_verified_at': j.link_verified_at,
        'data_provenance': j.data_provenance,
        'fingerprint': j.fingerprint,
    }


def jobs_list_api(request):
    q = request.GET.get('q', '').strip()
    company_id = request.GET.get('company_id', '').strip()
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

    qs = Job.objects.select_related('company').all()

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
    if company_id:
        qs = qs.filter(company_id=company_id)
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

    if category and category != 'all':
        cat_l = category.lower()
        if cat_l == 'tech':
            qs = qs.filter(
                Q(job_title__icontains='software') | Q(job_title__icontains='tech') |
                Q(job_title__icontains='engineer') | Q(job_title__icontains='cloud') |
                Q(job_title__icontains='data') | Q(job_title__icontains='devops') |
                Q(job_title__icontains='cyber') | Q(job_title__icontains='developer') |
                Q(job_title__icontains='analytics') | Q(job_title__icontains='ai') |
                Q(department__icontains='tech') | Q(department__icontains='IT') |
                Q(department__icontains='software') | Q(department__icontains='data') |
                Q(function__icontains='information technology')
            )
        elif cat_l == 'engineering':
            qs = qs.filter(
                Q(job_title__icontains='plant') | Q(job_title__icontains='process') |
                Q(job_title__icontains='mechanic') | Q(job_title__icontains='manufacturing') |
                Q(job_title__icontains='automation') | Q(job_title__icontains='maintenance') |
                Q(job_title__icontains='electrical') | Q(job_title__icontains='structural') |
                Q(job_title__icontains='civil') | Q(job_title__icontains='metallurg') |
                Q(department__icontains='Engineering') | Q(department__icontains='Automation') |
                Q(department__icontains='Maintenance') | Q(department__icontains='Manufacturing') |
                Q(function__icontains='Engineering')
            )
        elif cat_l == 'finance':
            qs = qs.filter(
                Q(job_title__icontains='finance') | Q(job_title__icontains='risk') |
                Q(job_title__icontains='credit') | Q(job_title__icontains='treasury') |
                Q(job_title__icontains='audit') | Q(job_title__icontains='wealth') |
                Q(job_title__icontains='banking') | Q(job_title__icontains='tax') |
                Q(job_title__icontains='accounting') | Q(job_title__icontains='controller') |
                Q(department__icontains='Finance') | Q(department__icontains='Banking') |
                Q(department__icontains='Accounts') | Q(department__icontains='Treasury') |
                Q(function__icontains='Finance')
            )
        elif cat_l == 'operations':
            qs = qs.filter(
                Q(job_title__icontains='supply') | Q(job_title__icontains='logistics') |
                Q(job_title__icontains='procurement') | Q(job_title__icontains='warehouse') |
                Q(job_title__icontains='sourcing') | Q(job_title__icontains='inventory') |
                Q(job_title__icontains='operations') | Q(job_title__icontains='dispatch') |
                Q(department__icontains='Supply Chain') | Q(department__icontains='Procurement') |
                Q(department__icontains='Logistics') | Q(department__icontains='Operations') |
                Q(function__icontains='Supply Chain')
            )
        elif cat_l == 'sales':
            qs = qs.filter(
                Q(job_title__icontains='sales') | Q(job_title__icontains='marketing') |
                Q(job_title__icontains='account') | Q(job_title__icontains='brand') |
                Q(job_title__icontains='commercial') | Q(job_title__icontains='business development') |
                Q(job_title__icontains='channel') | Q(department__icontains='Sales') |
                Q(department__icontains='Marketing') | Q(department__icontains='Commercial') |
                Q(function__icontains='Sales') | Q(function__icontains='Marketing')
            )
        elif cat_l == 'hr':
            qs = qs.filter(
                Q(job_title__icontains='hr') | Q(job_title__icontains='talent') |
                Q(job_title__icontains='people') | Q(job_title__icontains='recruit') |
                Q(job_title__icontains='human resources') | Q(job_title__icontains='payroll') |
                Q(department__icontains='Human Resources') | Q(department__icontains='Talent') |
                Q(department__icontains='People') | Q(function__icontains='Human Resources')
            )
        elif cat_l == 'csr':
            qs = qs.filter(
                IMPACT_ROLE_FILTER | Q(department__icontains='CSR') |
                Q(department__icontains='Sustainability') | Q(function__icontains='Sustainability') |
                Q(job_title__icontains='Sustainability') | Q(job_title__icontains='ESG') |
                Q(job_title__icontains='Decarbonization') | Q(job_title__icontains='Community')
            )
        elif cat_l == 'healthcare':
            qs = qs.filter(
                Q(job_title__icontains='health') | Q(job_title__icontains='pharma') |
                Q(job_title__icontains='medical') | Q(job_title__icontains='clinical') |
                Q(job_title__icontains='formulation') | Q(job_title__icontains='chemist') |
                Q(job_title__icontains='regulatory affairs') | Q(job_title__icontains='pharmacovigilance') |
                Q(job_title__icontains='wellness') | Q(department__icontains='Health') |
                Q(department__icontains='Pharma') | Q(department__icontains='Medical') |
                Q(department__icontains='Formulation') | Q(function__icontains='Healthcare')
            )
        elif cat_l == 'legal':
            qs = qs.filter(
                Q(job_title__icontains='legal') | Q(job_title__icontains='counsel') |
                Q(job_title__icontains='compliance') | Q(job_title__icontains='secretarial') |
                Q(job_title__icontains='governance') | Q(job_title__icontains='regulatory') |
                Q(job_title__icontains='law') | Q(job_title__icontains='contracts') |
                Q(department__icontains='Legal') | Q(department__icontains='Compliance') |
                Q(department__icontains='Corporate Affairs') | Q(function__icontains='Legal')
            )

    order_by_fields = JOB_SORT_OPTIONS.get(sort, JOB_SORT_OPTIONS['recent'])
    qs = qs.order_by(*order_by_fields)

    data = paginate_queryset(
        queryset=qs,
        serialize_func=serialize_job_item,
        page=page,
        page_size=page_size,
        fallback_limit=limit
    )
    return JsonResponse(data, safe=False)


def jobs_summary_api(request):
    """Job intelligence dashboard facets."""
    total_roles = Job.objects.count()
    active_roles = Job.objects.filter(status='ACTIVE').count()
    impact_roles = Job.objects.filter(IMPACT_ROLE_FILTER).count()
    remote_roles = Job.objects.filter(work_mode='Remote').count()
    hybrid_roles = Job.objects.filter(work_mode='Hybrid').count()
    onsite_roles = Job.objects.filter(work_mode='On-site').count()
    companies_hiring = Job.objects.values('company_id').distinct().count()
    live_verified_links = Job.objects.filter(link_status='VERIFIED_HTTP_200').count()

    by_dept = list(
        Job.objects.values('department')
        .annotate(roles=Count('job_row_id'))
        .order_by('-roles')[:15]
    )
    by_loc = list(
        Job.objects.values('location')
        .annotate(roles=Count('job_row_id'))
        .order_by('-roles')[:15]
    )
    by_comp = list(
        Job.objects.values('company__company_name', 'company__nse_symbol')
        .annotate(roles=Count('job_row_id'))
        .order_by('-roles')[:20]
    )
    # Format keys to match existing API expectation
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
