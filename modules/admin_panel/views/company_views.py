import hashlib
import json
import logging
from functools import wraps
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from modules.admin_panel.models import (
    AuditTrail,
    Company,
    CompanyCrawlSummary,
    Contact,
    CSROpportunity,
    CSRProject,
    Job,
    OpportunityScore,
    PageRecord,
)
from modules.admin_panel.verification import (
    LINK_OK,
    LOGIN_REQUIRED_TEXT,
    NOT_AVAILABLE_TEXT,
    PUBLIC_VERIFICATION_STATUSES,
    public_job_q,
    public_jobs,
    public_records,
)
from modules.crawler_engine.normalizers import (
    clean_text,
    detect_csr_source_format,
    is_generic_or_non_csr_contact_email,
    is_page_title_not_csr_project,
)

logger = logging.getLogger(__name__)


def is_admin_user(user):
    """Check if the user has administrative or staff access."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    if hasattr(user, 'is_admin_or_staff') and user.is_admin_or_staff():
        return True
    if hasattr(user, 'role') and user.role in ('ADMIN', 'SUPERADMIN', 'STAFF'):
        return True
    return False


def admin_required(view_func):
    """Strict backend access enforcement decorator for Company Management."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/admin-portal/login/?next={request.path}")
        if not is_admin_user(request.user):
            if (
                request.headers.get('x-requested-with') == 'XMLHttpRequest' or
                request.content_type == 'application/json'
            ):
                return JsonResponse({'success': False, 'error': 'Forbidden: Administrator privileges required.'}, status=403)
            messages.error(request, "Access denied: Administrator privileges required.")
            return redirect('/')
        return view_func(request, *args, **kwargs)
    return _wrapped


def log_audit_change(record_type, record_id, action, previous_val, new_val, user, notes=None):
    """Safely log an administrative change to MySQL audit_trail table."""
    try:
        username = user.username if user and getattr(user, 'is_authenticated', False) else 'SYSTEM_ADMIN'
        AuditTrail.objects.create(
            record_type=str(record_type),
            record_id=str(record_id),
            action=str(action),
            previous_value=str(previous_val)[:500] if previous_val is not None else None,
            new_value=str(new_val)[:500] if new_val is not None else None,
            user_role=username,
            notes=notes,
            timestamp=timezone.now().isoformat()
        )
    except Exception as e:
        logger.warning(f"Failed to record audit trail: {e}")


def _valid_http_url(u):
    s = clean_text(u)
    if not s or not s.lower().startswith(('http://', 'https://')) or 'google.com/search' in s.lower():
        return None
    return s


def _company_csr_sources(company: Company):
    """Returns (best_csr_webpage_url, csr_links_list, csr_display_format) for admin views."""
    links = []
    candidates = [
        ('CSR Portal Webpage', _valid_http_url(company.csr_portal_url)),
        ('Corporate Foundation Portal', _valid_http_url(company.foundation_url)),
        ('Sustainability Webpage', _valid_http_url(company.sustainability_url)),
        ('ESG Disclosures Webpage', _valid_http_url(company.esg_url)),
        ('SEBI BRSR Filing', _valid_http_url(company.brsr_url)),
        ('Annual Report Disclosure', _valid_http_url(company.annual_report_url)),
    ]
    seen = set()
    has_webpage = False
    has_pdf = False
    for label, url in candidates:
        if url and url not in seen:
            seen.add(url)
            fmt = detect_csr_source_format(url)
            if 'PDF' in fmt:
                has_pdf = True
            else:
                has_webpage = True
            links.append({'label': label, 'url': url, 'format': fmt})

    for pr in company.crawled_pages.filter(page_type__in=['CSR', 'CSR_PDF'], status='200').order_by('-page_id')[:15]:
        u = _valid_http_url(pr.url)
        if u and u not in seen:
            seen.add(u)
            fmt = detect_csr_source_format(u)
            if 'PDF' in fmt:
                has_pdf = True
            else:
                has_webpage = True
            links.append({
                'label': clean_text(pr.title) or ('Crawled CSR PDF' if pr.page_type == 'CSR_PDF' else 'Crawled CSR Webpage'),
                'url': u,
                'format': fmt,
            })

    best_url = (
        _valid_http_url(company.csr_portal_url) or
        _valid_http_url(company.foundation_url) or
        _valid_http_url(company.sustainability_url) or
        _valid_http_url(company.esg_url) or
        _valid_http_url(company.brsr_url) or
        _valid_http_url(company.annual_report_url)
    )

    if company.csr_access == 'LOGIN_REQUIRED':
        display_format = LOGIN_REQUIRED_TEXT
    elif has_webpage and has_pdf:
        display_format = 'CSR Webpage & PDF Disclosures'
    elif has_pdf:
        display_format = 'PDF Disclosures (BRSR / Annual Report)'
    elif has_webpage:
        display_format = detect_csr_source_format(best_url)
    else:
        display_format = NOT_AVAILABLE_TEXT

    return best_url, links, display_format


# -----------------------------------------------------------------------------
# COMPANY LIST & DASHBOARD
# -----------------------------------------------------------------------------

@admin_required
def company_list_view(request):
    """Company Management Dashboard: Statistics, filters, pagination, and directory."""
    # Shared ATS mapping post handler
    if request.method == 'POST' and request.POST.get('action') == 'update_shared_tenant':
        cfg_path = Path(settings.BASE_DIR) / 'config' / 'shared_tenants.json'
        try:
            cfg = json.loads(cfg_path.read_text(encoding='utf-8')) if cfg_path.exists() else {'tenants': []}
        except Exception:
            cfg = {'tenants': []}
        host = (request.POST.get('tenant_host') or '').strip()
        sym = (request.POST.get('nse_symbol') or '').strip().upper()
        aliases_raw = (request.POST.get('entity_aliases') or '').strip()
        site_code = (request.POST.get('site_code') or '').strip().upper()
        if host and sym:
            tenant_obj = next((t for t in cfg.get('tenants', []) if t.get('host', '').lower() == host.lower()), None)
            if not tenant_obj:
                tenant_obj = {'host': host, 'ats': 'Shared_ATS', 'group': host, 'site_owner': {}, 'shared_sites': ['CX_1'], 'entity_aliases': {}}
                cfg.setdefault('tenants', []).append(tenant_obj)
            if aliases_raw:
                tenant_obj.setdefault('entity_aliases', {})[sym] = [a.strip().lower() for a in aliases_raw.split(',') if a.strip()]
            if site_code:
                tenant_obj.setdefault('site_owner', {})[site_code] = sym
            cfg_path.write_text(json.dumps(cfg, indent=2), encoding='utf-8')
            log_audit_change('SharedTenantConfig', host, 'UPDATE_MAPPING', None, f"Mapped {sym} on {host}", request.user)
            messages.success(request, f"Saved shared ATS portal legal-entity mapping for {sym} on {host}.")
        return redirect(request.get_full_path())

    # Quick inline access update post handler
    if request.method == 'POST' and request.POST.get('action') == 'quick_update_access':
        cid = request.POST.get('company_id', '').strip()
        target_comp = Company.objects.filter(company_id=cid).first()
        if target_comp:
            valid_modes = {k for k, _ in Company.ACCESS_CHOICES}
            old_summary = f"Jobs: {target_comp.jobs_access}, CSR: {target_comp.csr_access}, Contacts: {target_comp.contacts_access}"
            for field in ('jobs_access', 'csr_access', 'contacts_access'):
                val = request.POST.get(field)
                if val in valid_modes:
                    setattr(target_comp, field, val)
            if 'data_access_note' in request.POST:
                target_comp.data_access_note = (request.POST.get('data_access_note') or '').strip() or None
            target_comp.data_access_checked_at = timezone.now()
            target_comp.save(update_fields=['jobs_access', 'csr_access', 'contacts_access', 'data_access_note', 'data_access_checked_at'])
            new_summary = f"Jobs: {target_comp.jobs_access}, CSR: {target_comp.csr_access}, Contacts: {target_comp.contacts_access}"
            log_audit_change('Company', target_comp.company_id, 'QUICK_ACCESS_UPDATE', old_summary, new_summary, request.user)
            messages.success(
                request,
                f"Updated login/access status for '{target_comp.company_name}' (Jobs: {target_comp.get_jobs_access_display()}, CSR: {target_comp.get_csr_access_display()})."
            )
        return redirect(request.get_full_path())

    # 1. Executive Statistics directly from MySQL database (optimized index-only counts)
    total_companies = Company.objects.count()
    verified_companies = Company.objects.filter(
        verification_status__in=['SOURCE_CONFIRMED', 'PUBLISHED', 'VALIDATED']
    ).count()
    unverified_companies = Company.objects.exclude(
        verification_status__in=['SOURCE_CONFIRMED', 'PUBLISHED', 'VALIDATED']
    ).count()
    companies_with_jobs = Company.objects.filter(jobs__status='ACTIVE').values('company_id').distinct().count()
    companies_with_csr = Company.objects.filter(csr_projects__status='ACTIVE').values('company_id').distinct().count()
    companies_requiring_verification = Company.objects.filter(
        Q(verification_status__in=['UNVERIFIED', 'PARTIAL_COVERAGE', 'NOT_FOUND']) |
        Q(website_url_status='UNKNOWN') |
        Q(website_url__isnull=True)
    ).count()
    companies_with_crawl_errors = Company.objects.filter(
        Q(crawl_status='FAILED') | Q(sync_status='FAILED')
    ).count()

    # 2. Filter Parameters
    q = request.GET.get('q', '').strip()
    sector = request.GET.get('sector', '').strip()
    verification_status = request.GET.get('verification_status', '').strip()
    crawl_status = request.GET.get('crawl_status', '').strip() or request.GET.get('status', '').strip()
    has_jobs = request.GET.get('has_jobs', '').strip().lower()
    has_csr = request.GET.get('has_csr', '').strip().lower()
    access = request.GET.get('access', '').strip()
    sort = request.GET.get('sort', 'name')
    page_num = request.GET.get('page', 1)
    per_page_raw = request.GET.get('per_page', '25').strip().lower()

    if per_page_raw == 'all':
        per_page = max(1, total_companies or 200)
    else:
        try:
            per_page = max(10, min(500, int(per_page_raw)))
        except ValueError:
            per_page = 25

    # 3. Base Queryset with optimized related counts
    qs = Company.objects.all().annotate(
        active_jobs_total=Count('jobs', filter=Q(jobs__status='ACTIVE'), distinct=True),
        active_csr_total=Count('csr_projects', filter=Q(csr_projects__status='ACTIVE'), distinct=True)
    )

    # 4. Apply Filters
    if q:
        qs = qs.filter(
            Q(company_name__icontains=q) |
            Q(legal_name__icontains=q) |
            Q(nse_symbol__icontains=q) |
            Q(bse_scrip_code__icontains=q) |
            Q(cin__icontains=q) |
            Q(sector__icontains=q) |
            Q(headquarters__icontains=q) |
            Q(company_id__icontains=q) |
            Q(website_url__icontains=q)
        )
    if sector and sector != 'all':
        qs = qs.filter(sector=sector)
    if verification_status and verification_status != 'all':
        qs = qs.filter(verification_status=verification_status)
    if crawl_status and crawl_status != 'all':
        qs = qs.filter(crawl_status=crawl_status)

    if has_jobs == 'yes':
        comp_ids_jobs = list(Job.objects.filter(status='ACTIVE').values_list('company_id', flat=True).distinct())
        qs = qs.filter(company_id__in=comp_ids_jobs)
    elif has_jobs == 'no':
        comp_ids_jobs = list(Job.objects.filter(status='ACTIVE').values_list('company_id', flat=True).distinct())
        qs = qs.exclude(company_id__in=comp_ids_jobs)

    if has_csr == 'yes':
        comp_ids_csr = list(CSRProject.objects.filter(status='ACTIVE').values_list('company_id', flat=True).distinct())
        qs = qs.filter(company_id__in=comp_ids_csr)
    elif has_csr == 'no':
        comp_ids_csr = list(CSRProject.objects.filter(status='ACTIVE').values_list('company_id', flat=True).distinct())
        qs = qs.exclude(company_id__in=comp_ids_csr)

    if access == 'LOGIN_REQUIRED':
        qs = qs.filter(Q(jobs_access='LOGIN_REQUIRED') | Q(csr_access='LOGIN_REQUIRED') | Q(contacts_access='LOGIN_REQUIRED'))
    elif access == 'JOBS_LOGIN':
        qs = qs.filter(jobs_access='LOGIN_REQUIRED')
    elif access == 'CSR_LOGIN':
        qs = qs.filter(csr_access='LOGIN_REQUIRED')
    elif access == 'CONTACTS_LOGIN':
        qs = qs.filter(contacts_access='LOGIN_REQUIRED')

    # 5. Sorting
    if sort == 'jobs':
        qs = qs.order_by('-active_jobs_total', 'company_name')
    elif sort == 'csr':
        qs = qs.order_by('-active_csr_total', 'company_name')
    elif sort == 'crawled':
        qs = qs.order_by('-last_live_synced_at', 'company_name')
    elif sort == 'status':
        qs = qs.order_by('crawl_status', 'company_name')
    else:
        qs = qs.order_by('company_name')

    # 6. Pagination
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page_num)

    # 7. Facet metadata
    all_sectors = Company.objects.exclude(sector__isnull=True).exclude(sector='').values_list('sector', flat=True).distinct().order_by('sector')
    all_verification_statuses = [
        'SOURCE_CONFIRMED', 'PARTIAL_COVERAGE', 'PUBLISHED', 'VALIDATED', 'UNVERIFIED', 'FAILED', 'NOT_FOUND'
    ]
    all_crawl_statuses = ['CRAWLED', 'PENDING', 'FAILED', 'SUSPECT_DROP', 'BLOCKED']

    login_required_qs = Company.objects.filter(
        Q(jobs_access='LOGIN_REQUIRED') | Q(csr_access='LOGIN_REQUIRED') | Q(contacts_access='LOGIN_REQUIRED')
    )
    all_companies_for_select = Company.objects.all().only(
        'company_id', 'company_name', 'nse_symbol', 'jobs_access', 'csr_access', 'contacts_access'
    ).order_by('company_name')

    cfg_path = Path(settings.BASE_DIR) / 'config' / 'shared_tenants.json'
    try:
        shared_tenants = json.loads(cfg_path.read_text(encoding='utf-8')).get('tenants', [])
    except Exception:
        shared_tenants = []

    return render(request, 'admin/companies/list.html', {
        # Statistics Cards
        'total_companies': total_companies,
        'verified_companies': verified_companies,
        'unverified_companies': unverified_companies,
        'companies_with_jobs': companies_with_jobs,
        'companies_with_csr': companies_with_csr,
        'companies_requiring_verification': companies_requiring_verification,
        'companies_with_crawl_errors': companies_with_crawl_errors,

        # Listing & Pagination
        'page_obj': page_obj,
        'total_count': paginator.count,
        'per_page': per_page_raw,
        'selected_sort': sort,

        # Filter States
        'q': q,
        'selected_sector': sector,
        'selected_verification': verification_status,
        'selected_status': crawl_status,
        'selected_has_jobs': has_jobs,
        'selected_has_csr': has_csr,
        'selected_access': access,

        # Dropdown Options
        'all_sectors': [s for s in all_sectors if s],
        'all_verification_statuses': all_verification_statuses,
        'all_crawl_statuses': all_crawl_statuses,

        # Login Required Section & Shared Tenants
        'shared_tenants': shared_tenants,
        'login_required_count': login_required_qs.count(),
        'login_required_companies': list(login_required_qs.order_by('company_name')),
        'all_companies_for_select': all_companies_for_select,
        'access_choices': Company.ACCESS_CHOICES,
        'not_available_text': NOT_AVAILABLE_TEXT,
        'login_required_text': LOGIN_REQUIRED_TEXT,
    })


# -----------------------------------------------------------------------------
# COMPANY CREATE
# -----------------------------------------------------------------------------

@admin_required
def company_create_view(request):
    """Register a new enterprise company in the database with strict validation."""
    if request.method == 'POST':
        company_name = (request.POST.get('company_name') or '').strip()
        legal_name = (request.POST.get('legal_name') or '').strip() or None
        cin = (request.POST.get('cin') or '').strip().upper() or None
        nse_symbol = (request.POST.get('nse_symbol') or '').strip().upper() or None
        bse_scrip_code = (request.POST.get('bse_scrip_code') or '').strip() or None
        sector = (request.POST.get('sector') or '').strip() or None
        headquarters = (request.POST.get('headquarters') or '').strip() or None
        website_url = (request.POST.get('website_url') or '').strip() or None
        careers_url = (request.POST.get('careers_url') or '').strip() or None
        csr_portal_url = (request.POST.get('csr_portal_url') or '').strip() or None

        if not company_name:
            messages.error(request, "Company name is required.")
            return render(request, 'admin/companies/create.html', {'form_data': request.POST})

        # Check for duplicates
        if Company.objects.filter(company_name__iexact=company_name).exists():
            messages.error(request, f"A company with name '{company_name}' already exists in the database.")
            return render(request, 'admin/companies/create.html', {'form_data': request.POST})

        if cin and Company.objects.filter(cin__iexact=cin).exists():
            messages.error(request, f"A company with CIN '{cin}' already exists in the database.")
            return render(request, 'admin/companies/create.html', {'form_data': request.POST})

        if nse_symbol and Company.objects.filter(nse_symbol__iexact=nse_symbol).exists():
            messages.error(request, f"A company with NSE Symbol '{nse_symbol}' already exists in the database.")
            return render(request, 'admin/companies/create.html', {'form_data': request.POST})

        # Generate unique company_id
        highest_id = 200
        for comp in Company.objects.filter(company_id__startswith='COMP_TOP200_'):
            try:
                num = int(comp.company_id.replace('COMP_TOP200_', ''))
                if num > highest_id:
                    highest_id = num
            except ValueError:
                pass
        new_company_id = f"COMP_TOP200_{highest_id + 1}"

        try:
            with transaction.atomic():
                company = Company(
                    company_id=new_company_id,
                    company_name=company_name,
                    legal_name=legal_name,
                    cin=cin,
                    nse_symbol=nse_symbol,
                    bse_scrip_code=bse_scrip_code,
                    listed_on_nse=bool(nse_symbol),
                    listed_on_bse=bool(bse_scrip_code),
                    listing_status='ACTIVE',
                    sector=sector,
                    headquarters=headquarters,
                    website_url=website_url,
                    careers_url=careers_url,
                    csr_portal_url=csr_portal_url,
                    verification_status='UNVERIFIED',
                    crawl_status='PENDING',
                    sync_status='IDLE',
                    jobs_access='UNKNOWN',
                    csr_access='UNKNOWN',
                    contacts_access='UNKNOWN',
                    source_url=website_url or 'https://example.com',
                    retrieved_at=timezone.now(),
                    content_hash=hashlib.sha256(company_name.encode('utf-8')).hexdigest()
                )
                company.save()

                log_audit_change(
                    'Company',
                    company.company_id,
                    'CREATE_COMPANY',
                    None,
                    f"Created company {company.company_name} ({company.company_id})",
                    request.user,
                    notes=f"Initial registration by admin {request.user.username}"
                )

            messages.success(request, f"Company '{company.company_name}' successfully registered with ID {company.company_id}.")
            return redirect('admin_companies:detail', company_id=company.company_id)
        except Exception as e:
            logger.exception(f"Error creating company: {e}")
            messages.error(request, f"Failed to create company: {e}")
            return render(request, 'admin/companies/create.html', {'form_data': request.POST})

    return render(request, 'admin/companies/create.html', {
        'all_sectors': Company.objects.exclude(sector__isnull=True).exclude(sector='').values_list('sector', flat=True).distinct().order_by('sector')
    })


# -----------------------------------------------------------------------------
# COMPANY DETAIL & MANAGEMENT DOSSIER
# -----------------------------------------------------------------------------

@admin_required
def company_detail_view(request, company_id):
    """Company Management Profile & Dossier with multi-tab interface."""
    company = get_object_or_404(Company, company_id=company_id)
    active_tab = request.GET.get('tab', 'overview').strip().lower()

    # --- TAB: ASSOCIATED JOBS MANAGEMENT ---
    job_q = request.GET.get('job_q', '').strip()
    job_dept = request.GET.get('job_dept', '').strip()
    job_mode = request.GET.get('job_mode', '').strip()
    job_status = request.GET.get('job_status', 'ALL').strip().upper()
    job_page_num = request.GET.get('job_page', 1)

    jobs_qs = company.jobs.all()
    if job_status != 'ALL':
        jobs_qs = jobs_qs.filter(status=job_status)
    if job_q:
        jobs_qs = jobs_qs.filter(
            Q(job_title__icontains=job_q) |
            Q(department__icontains=job_q) |
            Q(location__icontains=job_q) |
            Q(skills__icontains=job_q) |
            Q(job_description__icontains=job_q) |
            Q(job_id__icontains=job_q) |
            Q(external_job_id__icontains=job_q)
        )
    if job_dept and job_dept != 'all':
        jobs_qs = jobs_qs.filter(department__icontains=job_dept)
    if job_mode and job_mode != 'all':
        jobs_qs = jobs_qs.filter(work_mode=job_mode)

    jobs_qs = jobs_qs.order_by('-last_checked_date', '-job_row_id')
    jobs_paginator = Paginator(jobs_qs, 20)
    jobs_page_obj = jobs_paginator.get_page(job_page_num)

    total_company_jobs = company.jobs.count()
    active_jobs_count = company.jobs.filter(status='ACTIVE').count()
    archived_jobs_count = company.jobs.filter(status__in=['ARCHIVED', 'CLOSED', 'EXPIRED']).count()

    # --- TAB: ASSOCIATED CSR PROJECTS MANAGEMENT ---
    csr_q = request.GET.get('csr_q', '').strip()
    csr_category = request.GET.get('csr_category', '').strip()
    csr_status = request.GET.get('csr_status', 'ALL').strip().upper()
    csr_page_num = request.GET.get('csr_page', 1)

    csr_qs = company.csr_projects.all()
    if csr_status != 'ALL':
        csr_qs = csr_qs.filter(status=csr_status)
    if csr_q:
        csr_qs = csr_qs.filter(
            Q(project_name__icontains=csr_q) |
            Q(category__icontains=csr_q) |
            Q(description__icontains=csr_q) |
            Q(geographic_location__icontains=csr_q) |
            Q(state__icontains=csr_q)
        )
    if csr_category and csr_category != 'all':
        csr_qs = csr_qs.filter(category__icontains=csr_category)

    csr_qs = csr_qs.order_by('-confidence', '-csr_id')
    csr_paginator = Paginator(csr_qs, 20)
    csr_page_obj = csr_paginator.get_page(csr_page_num)

    total_csr_projects = company.csr_projects.count()
    active_csr_projects = company.csr_projects.filter(status='ACTIVE').count()

    # Pre-calculate source format on current page
    for p in csr_page_obj:
        p.source_format = detect_csr_source_format(p.source_url) if p.source_url else 'Unknown'

    # --- TAB: ASSOCIATED CSR OPPORTUNITIES & CONTACTS ---
    opportunities = list(
        company.open_opportunities.all().order_by('-confidence', '-opp_id')[:15]
    )
    contacts = list(company.contacts.all().order_by('-confidence', '-contact_id')[:15])

    # --- TAB: CRAWLING, ATS & AUDIT TRAIL ---
    crawl_summaries = list(company.crawl_summaries.all().order_by('-crawl_started_at')[:10])
    latest_crawl_summary = crawl_summaries[0] if crawl_summaries else None
    crawled_pages = list(company.crawled_pages.all().order_by('-page_id')[:25])
    csr_webpage_url, csr_links, csr_display_format = _company_csr_sources(company)

    # Change log audit history
    audit_trails = list(AuditTrail.objects.filter(
        Q(record_id=str(company.company_id)) |
        Q(record_type='Company', record_id=company.company_id) |
        Q(notes__icontains=company.company_id)
    ).order_by('-audit_id')[:30])

    company_depts = company.jobs.exclude(department__isnull=True).exclude(department='').values_list('department', flat=True).distinct()
    csr_categories = company.csr_projects.exclude(category__isnull=True).exclude(category='').values_list('category', flat=True).distinct()

    login_required_sections = [
        label for label, mode in (
            ('Jobs', company.jobs_access),
            ('CSR', company.csr_access),
            ('Contacts', company.contacts_access),
        ) if mode == 'LOGIN_REQUIRED'
    ]

    return render(request, 'admin/companies/detail.html', {
        'company': company,
        'active_tab': active_tab,

        # Jobs Management
        'jobs_page_obj': jobs_page_obj,
        'total_company_jobs': total_company_jobs,
        'active_jobs_count': active_jobs_count,
        'archived_jobs_count': archived_jobs_count,
        'job_q': job_q,
        'job_dept': job_dept,
        'job_mode': job_mode,
        'job_status': job_status,
        'company_depts': sorted(list(set(company_depts)))[:25],

        # CSR Projects Management
        'csr_page_obj': csr_page_obj,
        'total_csr_projects': total_csr_projects,
        'active_csr_projects': active_csr_projects,
        'csr_q': csr_q,
        'csr_category': csr_category,
        'csr_status': csr_status,
        'csr_categories': sorted(list(set(csr_categories)))[:25],
        'csr_webpage_url': csr_webpage_url,
        'csr_links': csr_links,
        'csr_display_format': csr_display_format,

        # Other Associated Intelligence
        'opportunities': opportunities,
        'contacts': contacts,
        'score': getattr(company, 'score_record', None),
        'crawl_summaries': crawl_summaries,
        'latest_crawl_summary': latest_crawl_summary,
        'crawled_pages': crawled_pages,
        'audit_trails': audit_trails,

        # Accessibility and UI Labels
        'login_required_sections': login_required_sections,
        'not_available_text': NOT_AVAILABLE_TEXT,
        'login_required_text': LOGIN_REQUIRED_TEXT,
        'link_ok': LINK_OK,
    })


# -----------------------------------------------------------------------------
# COMPANY PROFILE EDIT
# -----------------------------------------------------------------------------

@admin_required
def company_edit_view(request, company_id):
    """Edit comprehensive company profile with field-level audit tracking."""
    company = get_object_or_404(Company, company_id=company_id)

    if request.method == 'POST':
        # Track changed fields for audit log
        changed_fields = []
        old_values = {}
        new_values = {}

        def _update_field(field_name, new_val):
            old_val = getattr(company, field_name)
            if old_val != new_val:
                changed_fields.append(field_name)
                old_values[field_name] = str(old_val)
                new_values[field_name] = str(new_val)
                setattr(company, field_name, new_val)

        # 1. Core Corporate Identity
        new_name = (request.POST.get('company_name') or company.company_name).strip()
        if not new_name:
            messages.error(request, "Company name cannot be empty.")
            return redirect('admin_companies:edit', company_id=company.company_id)
        _update_field('company_name', new_name)
        _update_field('legal_name', (request.POST.get('legal_name') or '').strip() or None)
        _update_field('cin', (request.POST.get('cin') or '').strip().upper() or None)
        _update_field('sector', (request.POST.get('sector') or '').strip() or None)
        _update_field('headquarters', (request.POST.get('headquarters') or '').strip() or None)
        _update_field('isin', (request.POST.get('isin') or '').strip().upper() or None)
        _update_field('nse_symbol', (request.POST.get('nse_symbol') or '').strip().upper() or None)
        _update_field('bse_scrip_code', (request.POST.get('bse_scrip_code') or '').strip() or None)
        _update_field('listed_on_nse', request.POST.get('listed_on_nse') in ('1', 'true', 'on'))
        _update_field('listed_on_bse', request.POST.get('listed_on_bse') in ('1', 'true', 'on'))
        _update_field('listing_status', (request.POST.get('listing_status') or 'ACTIVE').strip().upper())

        # 2. URLs & Source Discovery
        _update_field('website_url', (request.POST.get('website_url') or '').strip() or None)
        _update_field('official_domain', (request.POST.get('official_domain') or '').strip() or None)
        _update_field('careers_url', (request.POST.get('careers_url') or '').strip() or None)
        _update_field('jobs_page_url', (request.POST.get('jobs_page_url') or '').strip() or None)
        _update_field('csr_portal_url', (request.POST.get('csr_portal_url') or '').strip() or None)
        _update_field('sustainability_url', (request.POST.get('sustainability_url') or '').strip() or None)
        _update_field('esg_url', (request.POST.get('esg_url') or '').strip() or None)
        _update_field('foundation_url', (request.POST.get('foundation_url') or '').strip() or None)
        _update_field('annual_report_url', (request.POST.get('annual_report_url') or '').strip() or None)
        _update_field('brsr_url', (request.POST.get('brsr_url') or '').strip() or None)
        _update_field('investor_url', (request.POST.get('investor_url') or '').strip() or None)
        _update_field('contact_page_url', (request.POST.get('contact_page_url') or '').strip() or None)

        # 3. ATS & Crawl Settings
        _update_field('ats_platform', (request.POST.get('ats_platform') or '').strip() or None)
        _update_field('ats_url', (request.POST.get('ats_url') or '').strip() or None)
        _update_field('ats_type', (request.POST.get('ats_type') or '').strip() or None)
        _update_field('ats_token', (request.POST.get('ats_token') or '').strip() or None)
        _update_field('crawl_status', (request.POST.get('crawl_status') or company.crawl_status).strip().upper())
        _update_field('sync_status', (request.POST.get('sync_status') or company.sync_status).strip().upper())
        _update_field('website_url_locked', request.POST.get('website_url_locked') in ('1', 'true', 'on'))

        # 4. Verification & Governance
        new_v_status = (request.POST.get('verification_status') or company.verification_status).strip()
        _update_field('verification_status', new_v_status)
        _update_field('verification_reason', (request.POST.get('verification_reason') or '').strip() or None)
        _update_field('website_url_status', (request.POST.get('website_url_status') or company.website_url_status).strip())
        _update_field('website_url_review_notes', (request.POST.get('website_url_review_notes') or '').strip() or None)
        _update_field('evidence_text', (request.POST.get('evidence_text') or '').strip() or None)

        # 5. Login/Access Controls
        valid_modes = {k for k, _ in Company.ACCESS_CHOICES}
        for field in ('jobs_access', 'csr_access', 'contacts_access'):
            val = request.POST.get(field, getattr(company, field))
            if val in valid_modes:
                _update_field(field, val)
        _update_field('data_access_note', (request.POST.get('data_access_note') or '').strip() or None)
        company.data_access_checked_at = timezone.now()

        # Enforce VerifiableModel requirements if SOURCE_CONFIRMED or PUBLISHED
        if company.verification_status in ['SOURCE_CONFIRMED', 'PUBLISHED']:
            if not company.source_url:
                company.source_url = company.website_url or 'https://example.com'
            if not company.retrieved_at:
                company.retrieved_at = timezone.now()
            if not company.evidence_text and not company.content_hash:
                company.evidence_text = f"Admin verified record on {timezone.now().strftime('%Y-%m-%d')}"

        try:
            with transaction.atomic():
                company.save()
                if changed_fields:
                    log_audit_change(
                        'Company',
                        company.company_id,
                        'UPDATE_COMPANY_PROFILE',
                        json.dumps(old_values, default=str),
                        json.dumps(new_values, default=str),
                        request.user,
                        notes=f"Admin {request.user.username} modified fields: {', '.join(changed_fields)}"
                    )
            messages.success(request, f"Company '{company.company_name}' updated successfully ({len(changed_fields)} fields modified).")
            return redirect('admin_companies:detail', company_id=company.company_id)
        except Exception as e:
            logger.exception(f"Error updating company {company.company_id}: {e}")
            messages.error(request, f"Failed to save changes: {e}")

    return render(request, 'admin/companies/edit.html', {
        'company': company,
        'access_choices': Company.ACCESS_CHOICES,
        'verification_choices': Company.VERIFICATION_STATUS_CHOICES,
        'sync_choices': Company.SYNC_STATUS_CHOICES,
        'all_sectors': Company.objects.exclude(sector__isnull=True).exclude(sector='').values_list('sector', flat=True).distinct().order_by('sector'),
    })


# -----------------------------------------------------------------------------
# ASSOCIATED JOB MANAGEMENT (CREATE, EDIT, TOGGLE STATUS)
# -----------------------------------------------------------------------------

@admin_required
def company_job_create_view(request, company_id):
    """Add a new job opening directly under this company."""
    company = get_object_or_404(Company, company_id=company_id)

    if request.method == 'POST':
        title = (request.POST.get('job_title') or '').strip()
        department = (request.POST.get('department') or '').strip() or None
        location = (request.POST.get('location') or '').strip() or None
        work_mode = (request.POST.get('work_mode') or 'On-site').strip()
        employment_type = (request.POST.get('employment_type') or 'Full-time').strip()
        salary = (request.POST.get('salary') or '').strip() or None
        application_url = (request.POST.get('application_url') or '').strip() or None
        source_url = (request.POST.get('source_url') or '').strip() or company.careers_url or company.website_url or 'https://example.com'
        description = (request.POST.get('job_description') or '').strip() or None
        skills = (request.POST.get('skills') or '').strip() or None
        experience = (request.POST.get('experience') or '').strip() or None
        status = (request.POST.get('status') or 'ACTIVE').strip().upper()
        verification_status = (request.POST.get('verification_status') or 'SOURCE_CONFIRMED').strip()

        if not title:
            messages.error(request, "Job title is required.")
            return redirect(f"/admin-portal/companies/{company.company_id}/?tab=jobs")

        canon_hash = hashlib.sha256((application_url or source_url or title).encode('utf-8')).hexdigest()
        fp = hashlib.sha256(f"{company.company_id}|{title.lower()}|{application_url or ''}".encode('utf-8')).hexdigest()

        try:
            with transaction.atomic():
                job = Job(
                    company=company,
                    job_id=f"JOB_{timezone.now().strftime('%Y%m%d%H%M%S')}_{company.company_id[-4:]}",
                    job_title=title,
                    department=department,
                    location=location,
                    work_mode=work_mode,
                    employment_type=employment_type,
                    salary=salary,
                    salary_text=salary,
                    application_url=application_url,
                    canonical_url=application_url or source_url,
                    canonical_url_hash=canon_hash,
                    source_url=source_url,
                    job_description=description,
                    description_raw=description,
                    skills=skills,
                    experience=experience,
                    status=status,
                    verification_status=verification_status,
                    fingerprint=fp,
                    posted_date=timezone.now().strftime('%Y-%m-%d'),
                    last_checked_date=timezone.now().strftime('%Y-%m-%d'),
                    retrieved_at=timezone.now(),
                    evidence_text=f"Manually created by Admin {request.user.username}",
                    content_hash=canon_hash,
                    link_quality='DIRECT' if application_url else 'LISTING_FALLBACK'
                )
                job.save()

                log_audit_change(
                    'Job',
                    job.job_row_id,
                    'CREATE_JOB',
                    None,
                    f"Created job '{job.job_title}' for {company.company_name}",
                    request.user,
                    notes=f"Created via Company Management Jobs Tab"
                )

            messages.success(request, f"Job '{job.job_title}' successfully created.")
        except Exception as e:
            logger.exception(f"Error creating job for company {company.company_id}: {e}")
            messages.error(request, f"Failed to create job: {e}")

    return redirect(f"/admin-portal/companies/{company.company_id}/?tab=jobs")


@admin_required
def company_job_edit_view(request, company_id, job_row_id):
    """Edit an existing job associated with this company."""
    company = get_object_or_404(Company, company_id=company_id)
    job = get_object_or_404(Job, job_row_id=job_row_id, company=company)

    if request.method == 'POST':
        title = (request.POST.get('job_title') or '').strip()
        if not title:
            messages.error(request, "Job title cannot be empty.")
            return redirect(f"/admin-portal/companies/{company.company_id}/?tab=jobs")

        old_snapshot = f"Title: {job.job_title}, Dept: {job.department}, Status: {job.status}"

        job.job_title = title
        job.department = (request.POST.get('department') or '').strip() or None
        job.location = (request.POST.get('location') or '').strip() or None
        job.work_mode = (request.POST.get('work_mode') or job.work_mode).strip()
        job.employment_type = (request.POST.get('employment_type') or job.employment_type).strip()
        job.salary = (request.POST.get('salary') or '').strip() or None
        job.salary_text = job.salary
        job.application_url = (request.POST.get('application_url') or '').strip() or None
        job.source_url = (request.POST.get('source_url') or '').strip() or job.source_url or 'https://example.com'
        job.job_description = (request.POST.get('job_description') or '').strip() or None
        job.description_raw = job.job_description
        job.skills = (request.POST.get('skills') or '').strip() or None
        job.experience = (request.POST.get('experience') or '').strip() or None
        job.status = (request.POST.get('status') or job.status).strip().upper()
        job.verification_status = (request.POST.get('verification_status') or job.verification_status).strip()
        job.last_checked_date = timezone.now().strftime('%Y-%m-%d')

        if job.verification_status in ['SOURCE_CONFIRMED', 'PUBLISHED']:
            if not job.retrieved_at:
                job.retrieved_at = timezone.now()
            if not job.evidence_text and not job.content_hash:
                job.evidence_text = f"Admin updated record on {timezone.now().strftime('%Y-%m-%d')}"

        try:
            with transaction.atomic():
                job.save()
                new_snapshot = f"Title: {job.job_title}, Dept: {job.department}, Status: {job.status}"
                log_audit_change(
                    'Job',
                    job.job_row_id,
                    'UPDATE_JOB',
                    old_snapshot,
                    new_snapshot,
                    request.user,
                    notes=f"Updated job #{job.job_row_id} from Company Management"
                )
            messages.success(request, f"Job '{job.job_title}' successfully updated.")
        except Exception as e:
            logger.exception(f"Error editing job {job_row_id}: {e}")
            messages.error(request, f"Failed to update job: {e}")

    return redirect(f"/admin-portal/companies/{company.company_id}/?tab=jobs")


@admin_required
def company_job_toggle_status_view(request, company_id, job_row_id):
    """Quickly toggle a job between ACTIVE and ARCHIVED."""
    company = get_object_or_404(Company, company_id=company_id)
    job = get_object_or_404(Job, job_row_id=job_row_id, company=company)

    old_status = job.status
    job.status = 'ARCHIVED' if old_status == 'ACTIVE' else 'ACTIVE'
    job.save(update_fields=['status'])

    log_audit_change(
        'Job',
        job.job_row_id,
        'TOGGLE_JOB_STATUS',
        old_status,
        job.status,
        request.user,
        notes=f"Admin {request.user.username} toggled status"
    )
    messages.success(request, f"Job '{job.job_title}' status set to {job.status}.")
    return redirect(f"/admin-portal/companies/{company.company_id}/?tab=jobs")


# -----------------------------------------------------------------------------
# ASSOCIATED CSR PROJECT MANAGEMENT (CREATE, EDIT, TOGGLE STATUS)
# -----------------------------------------------------------------------------

@admin_required
def company_csr_create_view(request, company_id):
    """Add a new statutory CSR project directly under this company."""
    company = get_object_or_404(Company, company_id=company_id)

    if request.method == 'POST':
        project_name = (request.POST.get('project_name') or '').strip()
        category = (request.POST.get('category') or '').strip() or None
        description = (request.POST.get('description') or '').strip() or None
        geographic_location = (request.POST.get('geographic_location') or '').strip() or None
        state = (request.POST.get('state') or '').strip() or None
        budget = (request.POST.get('budget') or '').strip() or None
        source_url = (request.POST.get('source_url') or '').strip() or company.csr_portal_url or company.website_url or 'https://example.com'
        status = (request.POST.get('status') or 'ACTIVE').strip().upper()
        verification_status = (request.POST.get('verification_status') or 'SOURCE_CONFIRMED').strip()
        evidence_text = (request.POST.get('evidence_text') or '').strip() or f"Manually verified statutory disclosure for {company.company_name}"

        if not project_name:
            messages.error(request, "Project name is required.")
            return redirect(f"/admin-portal/companies/{company.company_id}/?tab=csr")

        fp = hashlib.sha256(f"{company.company_id}|{project_name.lower()}|{timezone.now().isoformat()}".encode('utf-8')).hexdigest()

        try:
            with transaction.atomic():
                csr = CSRProject(
                    company=company,
                    project_name=project_name,
                    category=category,
                    description=description,
                    geographic_location=geographic_location,
                    state=state,
                    budget=budget,
                    raw_budget_text=budget,
                    source_url=source_url,
                    status=status,
                    verification_status=verification_status,
                    evidence_text=evidence_text,
                    content_hash=fp,
                    fingerprint=fp,
                    confidence=100.0,
                    discovered_date=timezone.now().strftime('%Y-%m-%d'),
                    last_verified_date=timezone.now().strftime('%Y-%m-%d'),
                    retrieved_at=timezone.now()
                )
                csr.save()

                log_audit_change(
                    'CSRProject',
                    csr.csr_id,
                    'CREATE_CSR_PROJECT',
                    None,
                    f"Created CSR project '{csr.project_name}' for {company.company_name}",
                    request.user,
                    notes=f"Created via Company Management CSR Tab"
                )

            messages.success(request, f"CSR Project '{csr.project_name}' successfully created.")
        except Exception as e:
            logger.exception(f"Error creating CSR project for {company.company_id}: {e}")
            messages.error(request, f"Failed to create CSR project: {e}")

    return redirect(f"/admin-portal/companies/{company.company_id}/?tab=csr")


@admin_required
def company_csr_edit_view(request, company_id, csr_id):
    """Edit an existing CSR project associated with this company."""
    company = get_object_or_404(Company, company_id=company_id)
    csr = get_object_or_404(CSRProject, csr_id=csr_id, company=company)

    if request.method == 'POST':
        project_name = (request.POST.get('project_name') or '').strip()
        if not project_name:
            messages.error(request, "Project name cannot be empty.")
            return redirect(f"/admin-portal/companies/{company.company_id}/?tab=csr")

        old_snapshot = f"Name: {csr.project_name}, Category: {csr.category}, Budget: {csr.budget}, Status: {csr.status}"

        csr.project_name = project_name
        csr.category = (request.POST.get('category') or '').strip() or None
        csr.description = (request.POST.get('description') or '').strip() or None
        csr.geographic_location = (request.POST.get('geographic_location') or '').strip() or None
        csr.state = (request.POST.get('state') or '').strip() or None
        csr.budget = (request.POST.get('budget') or '').strip() or None
        csr.raw_budget_text = csr.budget
        csr.source_url = (request.POST.get('source_url') or '').strip() or csr.source_url or 'https://example.com'
        csr.status = (request.POST.get('status') or csr.status).strip().upper()
        csr.verification_status = (request.POST.get('verification_status') or csr.verification_status).strip()
        csr.evidence_text = (request.POST.get('evidence_text') or '').strip() or csr.evidence_text
        csr.last_verified_date = timezone.now().strftime('%Y-%m-%d')

        if csr.verification_status in ['SOURCE_CONFIRMED', 'PUBLISHED']:
            if not csr.retrieved_at:
                csr.retrieved_at = timezone.now()
            if not csr.evidence_text and not csr.content_hash:
                csr.evidence_text = f"Admin updated record on {timezone.now().strftime('%Y-%m-%d')}"

        try:
            with transaction.atomic():
                csr.save()
                new_snapshot = f"Name: {csr.project_name}, Category: {csr.category}, Budget: {csr.budget}, Status: {csr.status}"
                log_audit_change(
                    'CSRProject',
                    csr.csr_id,
                    'UPDATE_CSR_PROJECT',
                    old_snapshot,
                    new_snapshot,
                    request.user,
                    notes=f"Updated CSR project #{csr.csr_id} from Company Management"
                )
            messages.success(request, f"CSR Project '{csr.project_name}' successfully updated.")
        except Exception as e:
            logger.exception(f"Error editing CSR project {csr_id}: {e}")
            messages.error(request, f"Failed to update CSR project: {e}")

    return redirect(f"/admin-portal/companies/{company.company_id}/?tab=csr")


@admin_required
def company_csr_toggle_status_view(request, company_id, csr_id):
    """Quickly toggle a CSR project between ACTIVE and ARCHIVED."""
    company = get_object_or_404(Company, company_id=company_id)
    csr = get_object_or_404(CSRProject, csr_id=csr_id, company=company)

    old_status = csr.status
    csr.status = 'ARCHIVED' if old_status == 'ACTIVE' else 'ACTIVE'
    csr.save(update_fields=['status'])

    log_audit_change(
        'CSRProject',
        csr.csr_id,
        'TOGGLE_CSR_STATUS',
        old_status,
        csr.status,
        request.user,
        notes=f"Admin {request.user.username} toggled status"
    )
    messages.success(request, f"CSR Project '{csr.project_name}' status set to {csr.status}.")
    return redirect(f"/admin-portal/companies/{company.company_id}/?tab=csr")
