"""
Public Preview API Views for Unauthenticated Visitors.
Strictly server-enforces maximum 5 genuine, verified records per category.
Tampering with limit, page, or query parameters CANNOT bypass this 5-record ceiling.
"""
from django.http import JsonResponse
from modules.admin_panel.models import Company, Job, CSRProject
from modules.admin_panel.verification import public_jobs, NOT_AVAILABLE_TEXT

PREVIEW_LIMIT = 5

def _clean_str(val):
    if not val:
        return None
    s = str(val).strip()
    if not s or s.lower() in ('none', 'null', 'not specified', 'undefined', 'nan'):
        return None
    return s


def get_public_preview_companies():
    """Retrieve exactly 5 verified corporate records with sanitized public fields."""
    qs = Company.objects.all().order_by('company_name')[:PREVIEW_LIMIT]

    items = []
    for c in qs:
        items.append({
            'company_id': c.company_id,
            'company_name': c.company_name,
            'nse_symbol': _clean_str(c.nse_symbol),
            'sector': _clean_str(c.sector),
            'headquarters': _clean_str(c.headquarters),
            'website_url': _clean_str(c.website_url),
            'careers_url': _clean_str(c.careers_url),
            'csr_portal_url': _clean_str(c.csr_portal_url or c.sustainability_url),
            'verification_status': c.verification_status,
            'job_count': c.jobs.filter(status='ACTIVE').count(),
            'csr_count': c.csr_projects.count(),
            'is_preview': True,
        })
    return items


def get_public_preview_jobs():
    """Retrieve exactly 5 active, verified corporate vacancies with sanitized public fields."""
    qs = public_jobs(Job.objects.select_related('company')).filter(
        status='ACTIVE'
    ).order_by('-posted_date', '-job_row_id')[:PREVIEW_LIMIT]

    items = []
    for j in qs:
        comp = j.company
        items.append({
            'job_row_id': j.job_row_id,
            'job_title': j.job_title,
            'company_name': comp.company_name if comp else 'Verified Corporate',
            'nse_symbol': _clean_str(comp.nse_symbol) if comp else None,
            'location': _clean_str(j.location) or 'India',
            'work_mode': _clean_str(j.work_mode) or 'On-site / Hybrid',
            'department': _clean_str(j.department) or 'General',
            'experience': _clean_str(j.experience) or 'Not specified',
            'application_url': _clean_str(j.application_url),
            'posted_date': str(j.posted_date) if j.posted_date else None,
            'is_preview': True,
        })
    return items


def get_public_preview_csr():
    """Retrieve exactly 5 verified statutory CSR initiatives with sanitized public fields."""
    qs = CSRProject.objects.select_related('company').filter(
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
    ).order_by('-csr_id')[:PREVIEW_LIMIT]

    items = []
    for p in qs:
        comp = p.company
        items.append({
            'csr_id': p.csr_id,
            'project_name': p.project_name,
            'company_name': comp.company_name if comp else 'Verified Enterprise',
            'sector': _clean_str(p.category) or 'Education & Healthcare',
            'state': _clean_str(p.state) or 'Pan-India',
            'budget': _clean_str(p.budget) or 'Statutory Section 135 Allocation',
            'source_url': _clean_str(p.source_url),
            'is_preview': True,
        })
    return items


def preview_companies_api(request):
    """Public preview API: returns max 5 corporate records."""
    companies = get_public_preview_companies()
    return JsonResponse({
        'companies': companies,
        'count': len(companies),
        'total': len(companies),
        'limit': PREVIEW_LIMIT,
        'is_preview': True,
        'message': 'Guest preview mode active. Showing 5 sample records. Register or log in to access all verified corporations.'
    })


def preview_jobs_api(request):
    """Public preview API: returns max 5 career vacancies."""
    jobs = get_public_preview_jobs()
    return JsonResponse({
        'jobs': jobs,
        'count': len(jobs),
        'total': len(jobs),
        'limit': PREVIEW_LIMIT,
        'is_preview': True,
        'message': 'Guest preview mode active. Showing 5 sample records. Register or log in to access all verified jobs.'
    })


def preview_csr_api(request):
    """Public preview API: returns max 5 CSR initiatives."""
    csr_projects = get_public_preview_csr()
    return JsonResponse({
        'csr_projects': csr_projects,
        'count': len(csr_projects),
        'total': len(csr_projects),
        'limit': PREVIEW_LIMIT,
        'is_preview': True,
        'message': 'Guest preview mode active. Showing 5 sample records. Register or log in to access all verified CSR initiatives.'
    })


def preview_bundle_api(request):
    """Consolidated public preview API returning 5 of each entity in a single payload."""
    companies = get_public_preview_companies()
    jobs = get_public_preview_jobs()
    csr = get_public_preview_csr()
    return JsonResponse({
        'companies': companies,
        'jobs': jobs,
        'csr_projects': csr,
        'is_preview': True,
        'limits': {
            'companies_preview_count': len(companies),
            'jobs_preview_count': len(jobs),
            'csr_preview_count': len(csr),
            'max_allowed': PREVIEW_LIMIT,
        },
        'cta': {
            'register_url': '/register/',
            'login_url': '/login/',
            'pricing_url': '/pricing/',
            'message': 'Create a free account to unlock full dossiers, active applications, and complete search filters.'
        }
    })
