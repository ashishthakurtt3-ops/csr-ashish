from django.http import JsonResponse
from django.db.models import Q
from modules.admin_panel.models import CSRProject, CSROpportunity
from modules.website.utils.pagination import paginate_queryset


def serialize_project_item(p: CSRProject):
    c = p.company
    return {
        'csr_id': p.csr_id,
        'company_id': p.company_id,
        'project_name': p.project_name,
        'category': p.category,
        'description': p.description,
        'geographic_location': p.geographic_location,
        'state': p.state,
        'budget': p.budget,
        'source_url': p.source_url,
        'discovered_date': p.discovered_date,
        'last_verified_date': p.last_verified_date,
        'confidence': p.confidence,
        'link_status': p.link_status,
        'link_verified_at': p.link_verified_at,
        'fingerprint': p.fingerprint,
        'company_name': c.company_name,
        'nse_symbol': c.nse_symbol,
        'sector': c.sector,
        'website_url': c.website_url,
    }


def serialize_opportunity_item(o: CSROpportunity):
    c = o.company
    return {
        'opp_id': o.opp_id,
        'company_id': o.company_id,
        'title': o.title,
        'opportunity_type': o.opportunity_type,
        'category': o.category,
        'submission_deadline': o.submission_deadline,
        'portal_url': o.portal_url,
        'requirements': o.requirements,
        'status': o.status,
        'confidence': o.confidence,
        'link_status': o.link_status,
        'link_verified_at': o.link_verified_at,
        'fingerprint': o.fingerprint,
        'company_name': c.company_name if c else 'General / Consortium',
        'nse_symbol': c.nse_symbol if c else None,
        'website_url': c.website_url if c else None,
        'sector': c.sector if c else None,
    }


def csr_projects_api(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    state = request.GET.get('state', '').strip()
    fy = request.GET.get('fy', '').strip()
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    limit = int(request.GET.get('limit', 200))

    qs = CSRProject.objects.select_related('company').all()
    if q:
        qs = qs.filter(
            Q(project_name__icontains=q) |
            Q(description__icontains=q) |
            Q(company__company_name__icontains=q)
        )
    if category and category != 'all':
        qs = qs.filter(category__icontains=category)
    if state and state != 'all':
        qs = qs.filter(Q(state__icontains=state) | Q(geographic_location__icontains=state))
    if fy and fy != 'all':
        qs = qs.filter(discovered_date__icontains=fy)

    qs = qs.order_by('-confidence', '-csr_id')

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
    opp_type = request.GET.get('opp_type', '').strip()
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    limit = int(request.GET.get('limit', 500))

    qs = CSROpportunity.objects.select_related('company').all()
    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(requirements__icontains=q) |
            Q(company__company_name__icontains=q)
        )
    if category and category != 'all':
        qs = qs.filter(category__icontains=category)
    if opp_type and opp_type != 'all':
        qs = qs.filter(opportunity_type=opp_type)

    qs = qs.order_by('-opp_id')

    data = paginate_queryset(
        queryset=qs,
        serialize_func=serialize_opportunity_item,
        page=page,
        page_size=page_size,
        fallback_limit=limit
    )
    return JsonResponse(data, safe=False)
