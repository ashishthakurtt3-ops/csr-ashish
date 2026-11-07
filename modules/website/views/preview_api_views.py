"""
modules/website/views/preview_api_views.py
==========================================
Public Preview API Views for Unauthenticated Visitors and Unsubscribed Users.
Dynamically driven by database-persisted GuestPreviewSettings and dedicated
high-fidelity PreviewDummy datasets (Companies, Jobs, Section 135 CSR Initiatives).

Guarantees 100%:
- All preview data is strictly dummy data.
- Matches real production format, fields, and UI display 1:1.
- Manageable and uploadable via Excel/CSV in Admin Panel -> Dummy Preview Manager.
- Real production database records are never exposed to preview visitors.
"""
from django.http import JsonResponse
from modules.admin_panel.models import (
    GuestPreviewSettings,
    PreviewDummyCompany,
    PreviewDummyJob,
    PreviewDummyCSRProject
)

PREVIEW_LIMIT = 5

def _clean_str(val):
    if not val:
        return None
    s = str(val).strip()
    if not s or s.lower() in ('none', 'null', 'not specified', 'undefined', 'nan'):
        return None
    return s


def get_public_preview_companies():
    """
    Retrieve corporate records for Guest Preview.
    Strictly serves high-fidelity dummy data formatted identical to real companies.
    """
    cfg = GuestPreviewSettings.get_settings()
    if not cfg.preview_enabled:
        return []

    limit = cfg.preview_limit or 5

    dummy_qs = PreviewDummyCompany.objects.filter(is_active=True).order_by('display_order', 'id')
    if not dummy_qs.exists():
        from modules.admin_panel.services.preview_dummy_service import seed_default_dummy_data
        seed_default_dummy_data()
        dummy_qs = PreviewDummyCompany.objects.filter(is_active=True).order_by('display_order', 'id')

    return [c.as_preview_dict() for c in dummy_qs[:limit]]


def get_public_preview_jobs():
    """
    Retrieve career vacancies for Guest Preview.
    Strictly serves high-fidelity dummy vacancies formatted identical to real jobs.
    """
    cfg = GuestPreviewSettings.get_settings()
    if not cfg.preview_enabled:
        return []

    limit = cfg.preview_limit or 5

    dummy_qs = PreviewDummyJob.objects.filter(is_active=True).order_by('display_order', 'id')
    if not dummy_qs.exists():
        from modules.admin_panel.services.preview_dummy_service import seed_default_dummy_data
        seed_default_dummy_data()
        dummy_qs = PreviewDummyJob.objects.filter(is_active=True).order_by('display_order', 'id')

    return [j.as_preview_dict() for j in dummy_qs[:limit]]


def get_public_preview_csr():
    """
    Retrieve Section 135 CSR initiatives for Guest Preview.
    Strictly serves high-fidelity dummy CSR filings formatted identical to real projects.
    """
    cfg = GuestPreviewSettings.get_settings()
    if not cfg.preview_enabled:
        return []

    limit = cfg.preview_limit or 5

    dummy_qs = PreviewDummyCSRProject.objects.filter(is_active=True).order_by('display_order', 'id')
    if not dummy_qs.exists():
        from modules.admin_panel.services.preview_dummy_service import seed_default_dummy_data
        seed_default_dummy_data()
        dummy_qs = PreviewDummyCSRProject.objects.filter(is_active=True).order_by('display_order', 'id')

    return [p.as_preview_dict() for p in dummy_qs[:limit]]


def preview_companies_api(request):
    """Public preview API: returns dummy corporate records governed by GuestPreviewSettings."""
    cfg = GuestPreviewSettings.get_settings()
    companies = get_public_preview_companies()
    return JsonResponse({
        'companies': companies,
        'count': len(companies),
        'total': len(companies),
        'limit': cfg.preview_limit,
        'is_preview': True,
        'preview_enabled': cfg.preview_enabled,
        'message': f'Guest preview mode active. Showing {len(companies)} sample records. Register or log in to access all verified corporations.'
    })


def preview_jobs_api(request):
    """Public preview API: returns dummy career vacancies governed by GuestPreviewSettings."""
    cfg = GuestPreviewSettings.get_settings()
    jobs = get_public_preview_jobs()
    return JsonResponse({
        'jobs': jobs,
        'count': len(jobs),
        'total': len(jobs),
        'limit': cfg.preview_limit,
        'is_preview': True,
        'preview_enabled': cfg.preview_enabled,
        'message': f'Guest preview mode active. Showing {len(jobs)} sample records. Register or log in to access all verified jobs.'
    })


def preview_csr_api(request):
    """Public preview API: returns dummy CSR initiatives governed by GuestPreviewSettings."""
    cfg = GuestPreviewSettings.get_settings()
    csr_projects = get_public_preview_csr()
    return JsonResponse({
        'csr_projects': csr_projects,
        'count': len(csr_projects),
        'total': len(csr_projects),
        'limit': cfg.preview_limit,
        'is_preview': True,
        'preview_enabled': cfg.preview_enabled,
        'message': f'Guest preview mode active. Showing {len(csr_projects)} sample records. Register or log in to access all verified CSR initiatives.'
    })


def preview_bundle_api(request):
    """Consolidated public preview API returning sample entities and UI configuration."""
    cfg = GuestPreviewSettings.get_settings()
    companies = get_public_preview_companies()
    jobs = get_public_preview_jobs()
    csr = get_public_preview_csr()

    return JsonResponse({
        'is_preview': True,
        'preview_enabled': cfg.preview_enabled,
        'limit': cfg.preview_limit,
        'banner': {
            'enabled': cfg.banner_enabled,
            'badge_text': cfg.banner_badge_text,
            'headline': cfg.banner_headline,
            'cta_text': cfg.banner_cta_text,
            'cta_url': cfg.banner_cta_url,
        },
        'auth_modal': {
            'title': cfg.auth_modal_title,
            'description': cfg.auth_modal_description,
            'primary_btn_text': cfg.auth_modal_primary_btn_text,
            'primary_btn_url': cfg.auth_modal_primary_btn_url,
            'secondary_btn_text': cfg.auth_modal_secondary_btn_text,
            'secondary_btn_url': cfg.auth_modal_secondary_btn_url,
        },
        'bottom_banner': {
            'enabled': cfg.bottom_banner_enabled,
            'title': cfg.bottom_banner_title,
            'description': cfg.bottom_banner_description,
            'btn_text': cfg.bottom_banner_btn_text,
            'btn_url': cfg.bottom_banner_btn_url,
        },
        'companies': companies,
        'jobs': jobs,
        'csr_projects': csr,
        'counts': {
            'companies': len(companies),
            'jobs': len(jobs),
            'csr': len(csr),
        }
    })
