import json
from pathlib import Path
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from modules.admin_panel.models import (
    Company, CSRProject, Job, Contact, OpportunityScore,
    CSROpportunity, PageRecord, CompanyCrawlSummary, AuditTrail
)
from modules.admin_panel.verification import (
    PUBLIC_VERIFICATION_STATUSES, public_jobs, public_records, public_job_q,
    NOT_AVAILABLE_TEXT, LOGIN_REQUIRED_TEXT, LINK_OK,
)
from modules.crawler_engine.normalizers import (
    clean_text, detect_csr_source_format, is_page_title_not_csr_project,
    is_generic_or_non_csr_contact_email,
)


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


@login_required
def company_list_view(request):
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
            messages.success(request, f"Saved shared ATS portal legal-entity mapping for {sym} on {host}.")
        return redirect(request.get_full_path())

    # Support quick inline update of a company's Login-Required settings directly from the Admin Panel list page
    if request.method == 'POST' and request.POST.get('action') == 'quick_update_access':
        cid = request.POST.get('company_id', '').strip()
        target_comp = Company.objects.filter(company_id=cid).first()
        if target_comp:
            valid_modes = {k for k, _ in Company.ACCESS_CHOICES}
            for field in ('jobs_access', 'csr_access', 'contacts_access'):
                val = request.POST.get(field)
                if val in valid_modes:
                    setattr(target_comp, field, val)
            if 'data_access_note' in request.POST:
                target_comp.data_access_note = (request.POST.get('data_access_note') or '').strip() or None
            target_comp.data_access_checked_at = timezone.now()
            target_comp.save(update_fields=['jobs_access', 'csr_access', 'contacts_access', 'data_access_note', 'data_access_checked_at'])
            messages.success(
                request,
                f"Updated login/access status for '{target_comp.company_name}' (Jobs: {target_comp.get_jobs_access_display()}, CSR: {target_comp.get_csr_access_display()})."
            )
        return redirect(request.get_full_path())

    q = request.GET.get('q', '').strip()
    sector = request.GET.get('sector', '').strip()
    crawl_status = request.GET.get('status', '').strip()
    access = request.GET.get('access', '').strip()
    page_num = request.GET.get('page', 1)
    per_page_raw = request.GET.get('per_page', '50').strip().lower()
    if per_page_raw == 'all':
        per_page = max(1, Company.objects.count() or 200)
    else:
        try:
            per_page = max(10, min(1000, int(per_page_raw)))
        except ValueError:
            per_page = 50

    qs = Company.objects.all().annotate(
        verified_jobs_total=Count('jobs', filter=public_job_q('jobs__'), distinct=True),
        verified_csr_total=Count(
            'csr_projects',
            filter=Q(csr_projects__verification_status__in=list(PUBLIC_VERIFICATION_STATUSES)),
            distinct=True
        ),
        verified_contacts_total=Count(
            'contacts',
            filter=Q(contacts__verification_status__in=list(PUBLIC_VERIFICATION_STATUSES)),
            distinct=True
        ),
    ).order_by('company_name')

    if access == 'LOGIN_REQUIRED':
        qs = qs.filter(Q(jobs_access='LOGIN_REQUIRED') | Q(csr_access='LOGIN_REQUIRED') | Q(contacts_access='LOGIN_REQUIRED'))
    elif access == 'JOBS_LOGIN':
        qs = qs.filter(jobs_access='LOGIN_REQUIRED')
    elif access == 'CSR_LOGIN':
        qs = qs.filter(csr_access='LOGIN_REQUIRED')
    elif access == 'CONTACTS_LOGIN':
        qs = qs.filter(contacts_access='LOGIN_REQUIRED')

    if q:
        qs = qs.filter(
            Q(company_name__icontains=q) |
            Q(nse_symbol__icontains=q) |
            Q(sector__icontains=q) |
            Q(headquarters__icontains=q) |
            Q(company_id__icontains=q)
        )
    if sector and sector != 'all':
        qs = qs.filter(sector=sector)
    if crawl_status and crawl_status != 'all':
        qs = qs.filter(crawl_status=crawl_status)

    all_sectors = Company.objects.values_list('sector', flat=True).distinct().order_by('sector')
    paginator = Paginator(qs, per_page)
    page_obj = paginator.get_page(page_num)

    login_required_qs = Company.objects.filter(
        Q(jobs_access='LOGIN_REQUIRED') | Q(csr_access='LOGIN_REQUIRED') | Q(contacts_access='LOGIN_REQUIRED')
    )
    all_companies_for_select = Company.objects.all().only('company_id', 'company_name', 'nse_symbol', 'jobs_access', 'csr_access', 'contacts_access').order_by('company_name')

    cfg_path = Path(settings.BASE_DIR) / 'config' / 'shared_tenants.json'
    try:
        shared_tenants = json.loads(cfg_path.read_text(encoding='utf-8')).get('tenants', [])
    except Exception:
        shared_tenants = []

    return render(request, 'admin/companies/list.html', {
        'shared_tenants': shared_tenants,
        'page_obj': page_obj,
        'q': q,
        'selected_sector': sector,
        'selected_status': crawl_status,
        'selected_access': access,
        'per_page': per_page_raw,
        'login_required_count': login_required_qs.count(),
        'login_required_companies': list(login_required_qs.order_by('company_name')),
        'all_companies_for_select': all_companies_for_select,
        'access_choices': Company.ACCESS_CHOICES,
        'not_available_text': NOT_AVAILABLE_TEXT,
        'login_required_text': LOGIN_REQUIRED_TEXT,
        'all_sectors': [s for s in all_sectors if s],
        'total_count': paginator.count
    })


@login_required
def company_detail_view(request, company_id):
    company = get_object_or_404(Company, company_id=company_id)

    job_q = request.GET.get('job_q', '').strip()
    job_dept = request.GET.get('job_dept', '').strip()
    job_mode = request.GET.get('job_mode', '').strip()
    job_page_num = request.GET.get('job_page', 1)

    show_historical = request.GET.get('historical', '').lower() in ('true', '1')
    if show_historical:
        jobs_qs = company.jobs.exclude(job_id__startswith='REQ').exclude(verification_status='LEGACY_UNVERIFIED')
    else:
        jobs_qs = public_jobs(company.jobs.all())

    if job_q:
        jobs_qs = jobs_qs.filter(
            Q(job_title__icontains=job_q) |
            Q(department__icontains=job_q) |
            Q(location__icontains=job_q) |
            Q(skills__icontains=job_q) |
            Q(job_description__icontains=job_q)
        )
    if job_dept and job_dept != 'all':
        jobs_qs = jobs_qs.filter(department__icontains=job_dept)
    if job_mode and job_mode != 'all':
        jobs_qs = jobs_qs.filter(work_mode=job_mode)

    jobs_qs = jobs_qs.order_by('-last_checked_date', '-job_row_id')
    jobs_paginator = Paginator(jobs_qs, 25)
    jobs_page_obj = jobs_paginator.get_page(job_page_num)

    total_company_jobs = company.jobs.exclude(job_id__startswith='REQ').exclude(verification_status='LEGACY_UNVERIFIED').count()
    active_jobs_count = public_jobs(company.jobs.all()).count()

    # Strictly verified CSR Projects (excluding generic webpage titles)
    raw_projects = public_records(company.csr_projects.all()).exclude(
        source_url__isnull=True
    ).exclude(source_url='').order_by('-confidence', '-csr_id')
    projects = []
    for p in raw_projects:
        if is_page_title_not_csr_project(p.project_name, company.company_name):
            continue
        p.source_format = detect_csr_source_format(p.source_url)
        projects.append(p)

    # Strictly verified CSR Opportunities / Grants / RFPs
    opportunities = list(
        public_records(company.open_opportunities.all()).exclude(
            (Q(source_url__isnull=True) | Q(source_url='')) & (Q(portal_url__isnull=True) | Q(portal_url=''))
        ).order_by('-confidence', '-opp_id')
    )

    # Strictly verified Corporate Contacts (excluding generic info@/webmaster@ mailboxes)
    contacts = []
    for ct in public_records(company.contacts.all()).order_by('-confidence', '-contact_id'):
        if ct.email and is_generic_or_non_csr_contact_email(ct.email):
            if not ct.phone:
                continue
            ct.email = None
        if ct.email or ct.phone:
            contacts.append(ct)

    score = getattr(company, 'score_record', None)

    crawl_summaries = list(company.crawl_summaries.all().order_by('-crawl_started_at')[:10])
    latest_crawl_summary = crawl_summaries[0] if crawl_summaries else None

    crawled_pages = list(company.crawled_pages.all().order_by('-page_id')[:30])
    csr_webpage_url, csr_links, csr_display_format = _company_csr_sources(company)

    login_required_sections = [
        label for label, mode in (
            ('Jobs', company.jobs_access),
            ('CSR', company.csr_access),
            ('Contacts', company.contacts_access),
        ) if mode == 'LOGIN_REQUIRED'
    ]

    audit_trails = list(AuditTrail.objects.filter(
        Q(record_id=str(company.company_id)) | Q(record_type='Company', record_id=company.company_id)
    ).order_by('-audit_id')[:15])

    company_depts = company.jobs.exclude(department__isnull=True).exclude(department='').values_list('department', flat=True).distinct()

    return render(request, 'admin/companies/detail.html', {
        'company': company,
        'jobs_page_obj': jobs_page_obj,
        'total_company_jobs': total_company_jobs,
        'active_jobs_count': active_jobs_count,
        'job_q': job_q,
        'job_dept': job_dept,
        'job_mode': job_mode,
        'company_depts': sorted(list(set(company_depts)))[:20],
        'projects': projects,
        'opportunities': opportunities,
        'contacts': contacts,
        'csr_webpage_url': csr_webpage_url,
        'csr_links': csr_links,
        'csr_display_format': csr_display_format,
        'login_required_sections': login_required_sections,
        'not_available_text': NOT_AVAILABLE_TEXT,
        'login_required_text': LOGIN_REQUIRED_TEXT,
        'link_ok': LINK_OK,
        'score': score,
        'crawl_summaries': crawl_summaries,
        'latest_crawl_summary': latest_crawl_summary,
        'crawled_pages': crawled_pages,
        'audit_trails': audit_trails,
    })


@login_required
def company_edit_view(request, company_id):
    company = get_object_or_404(Company, company_id=company_id)
    if request.method == 'POST':
        company.company_name = request.POST.get('company_name', company.company_name).strip()
        company.legal_name = (request.POST.get('legal_name') or '').strip() or None
        company.website_url = (request.POST.get('website_url') or '').strip() or None
        company.careers_url = (request.POST.get('careers_url') or '').strip() or None
        company.csr_portal_url = (request.POST.get('csr_portal_url') or '').strip() or None
        company.sustainability_url = (request.POST.get('sustainability_url') or '').strip() or None
        company.esg_url = (request.POST.get('esg_url') or '').strip() or None
        company.foundation_url = (request.POST.get('foundation_url') or '').strip() or None
        company.annual_report_url = (request.POST.get('annual_report_url') or '').strip() or None
        company.brsr_url = (request.POST.get('brsr_url') or '').strip() or None
        company.investor_url = (request.POST.get('investor_url') or '').strip() or None
        company.contact_page_url = (request.POST.get('contact_page_url') or '').strip() or None
        company.sector = (request.POST.get('sector') or '').strip() or None
        company.headquarters = (request.POST.get('headquarters') or '').strip() or None
        company.crawl_status = request.POST.get('crawl_status', company.crawl_status).strip()
        valid_modes = {k for k, _ in Company.ACCESS_CHOICES}
        for field in ('jobs_access', 'csr_access', 'contacts_access'):
            val = request.POST.get(field, getattr(company, field))
            if val in valid_modes:
                setattr(company, field, val)
        company.data_access_note = (request.POST.get('data_access_note') or '').strip() or None
        company.data_access_checked_at = timezone.now()
        company.save()
        messages.success(request, f"Company '{company.company_name}' updated successfully.")
        return redirect('admin_companies:detail', company_id=company.company_id)

    access_fields = [
        ('jobs_access', 'Jobs', company.jobs_access),
        ('csr_access', 'CSR', company.csr_access),
        ('contacts_access', 'Contacts', company.contacts_access),
    ]
    return render(request, 'admin/companies/edit.html', {
        'company': company,
        'access_fields': access_fields,
        'access_choices': Company.ACCESS_CHOICES,
        'not_available_text': NOT_AVAILABLE_TEXT,
        'login_required_text': LOGIN_REQUIRED_TEXT,
    })
