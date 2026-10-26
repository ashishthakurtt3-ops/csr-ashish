from django.http import JsonResponse, Http404
from django.db.models import Q, Count, Subquery, OuterRef, IntegerField
from django.db.models.functions import Coalesce
from modules.admin_panel.models import (
    Company, CSRProject, Job, NGOCollaboration, Contact,
    OpportunityScore, CSROpportunity, Prospect, PageRecord
)
from modules.website.utils.pagination import paginate_queryset

from modules.admin_panel.verification import (
    PUBLIC_VERIFICATION_STATUSES, public_jobs, public_records, public_job_q,
    NOT_AVAILABLE_TEXT, LOGIN_REQUIRED_TEXT, LINK_OK,
)
from modules.crawler_engine.normalizers import (
    clean_text, detect_csr_source_format, is_page_title_not_csr_project,
    is_generic_or_non_csr_contact_email,
)

VERIFIED_CONTACT_STATUSES = set(PUBLIC_VERIFICATION_STATUSES)


def _valid_http_url(u):
    s = clean_text(u)
    if not s or not s.lower().startswith(('http://', 'https://')) or 'google.com/search' in s.lower():
        return None
    return s


def _build_company_csr_links(c: Company):
    """
    Collects all verified CSR-related webpage and PDF disclosure URLs for a company,
    since different companies publish CSR in different ways (dedicated CSR portal,
    Foundation website, Sustainability/ESG page, or BRSR / Annual Report PDFs).
    Never falls back to the generic company homepage or careers page.
    """
    links = []
    candidates = [
        ('CSR Portal Webpage', _valid_http_url(c.csr_portal_url)),
        ('Corporate Foundation Portal', _valid_http_url(c.foundation_url)),
        ('Sustainability Webpage', _valid_http_url(c.sustainability_url)),
        ('ESG Disclosures Webpage', _valid_http_url(c.esg_url)),
        ('SEBI BRSR Filing', _valid_http_url(c.brsr_url)),
        ('Annual Report Disclosure', _valid_http_url(c.annual_report_url)),
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
            links.append({
                'label': label,
                'url': url,
                'format': fmt,
            })

    best_csr_webpage = (
        _valid_http_url(c.csr_portal_url) or
        _valid_http_url(c.foundation_url) or
        _valid_http_url(c.sustainability_url) or
        _valid_http_url(c.esg_url) or
        _valid_http_url(c.brsr_url) or
        _valid_http_url(c.annual_report_url)
    )

    if c.csr_access == 'LOGIN_REQUIRED':
        display_format = LOGIN_REQUIRED_TEXT
    elif has_webpage and has_pdf:
        display_format = 'CSR Webpage & PDF Disclosures'
    elif has_pdf:
        display_format = 'PDF Disclosures (BRSR / Annual Report)'
    elif has_webpage:
        display_format = detect_csr_source_format(best_csr_webpage)
    else:
        display_format = NOT_AVAILABLE_TEXT

    return best_csr_webpage, links, display_format


def _normalize_company_dict(d):
    """Company values are shown exactly as stored (verified) in the database."""
    return d


def serialize_company_list_item(c: Company):
    if hasattr(c, 'active_verified_jobs_count'):
        verified_jobs_count = c.active_verified_jobs_count
    else:
        verified_jobs_qs = public_jobs(c.jobs.all())
        verified_jobs_count = verified_jobs_qs.count()

    if hasattr(c, 'published_csr_count_annotated'):
        published_csr_count = c.published_csr_count_annotated
    else:
        published_csr_qs = public_records(c.csr_projects.all())
        published_csr_count = published_csr_qs.count()

    if hasattr(c, 'open_opps_count_annotated'):
        open_opps = c.open_opps_count_annotated
    else:
        open_opps = public_records(c.open_opportunities.all()).filter(status='OPEN').count()

    primary_project = None
    if published_csr_count > 0:
        # Avoid database roundtrip by using prefetched objects if available
        if hasattr(c, '_prefetched_objects_cache') and 'csr_projects' in c._prefetched_objects_cache:
            proj_candidates = [p for p in c.csr_projects.all() if (p.verification_status or '') in PUBLIC_VERIFICATION_STATUSES]
            if proj_candidates:
                primary_project = max(proj_candidates, key=lambda p: (getattr(p, 'confidence', 0.0) or 0.0))
        else:
            primary_project = public_records(c.csr_projects.all()).order_by('-confidence').first()

    primary_job = None
    if verified_jobs_count > 0:
        if hasattr(c, '_prefetched_objects_cache') and 'jobs' in c._prefetched_objects_cache:
            job_candidates = [j for j in c.jobs.all() if (j.verification_status or '') in PUBLIC_VERIFICATION_STATUSES or j.status == 'ACTIVE']
            if job_candidates:
                primary_job = max(job_candidates, key=lambda j: (j.last_checked_date or ''))
        else:
            primary_job = public_jobs(c.jobs.all()).order_by('-last_checked_date').first()

    primary_ngo = None
    if published_csr_count > 0:
        if hasattr(c, '_prefetched_objects_cache') and 'ngo_collaborations' in c._prefetched_objects_cache:
            ngo_candidates = [n for n in c.ngo_collaborations.all() if (n.verification_status or '') in PUBLIC_VERIFICATION_STATUSES]
            primary_ngo = ngo_candidates[0] if ngo_candidates else None
        else:
            primary_ngo = public_records(c.ngo_collaborations.all()).first()

    score_obj = getattr(c, 'score_record', None)

    best_csr_webpage, csr_links, csr_display_format = _build_company_csr_links(c)

    # Authoritative Job Status Rule (including Login-Required state)
    if verified_jobs_count > 0:
        job_status_label = f'{verified_jobs_count} Verified Jobs'
        job_status_state = 'VERIFIED_JOBS'
        job_status_badge = 'badge-emerald'
    elif c.jobs_access == 'LOGIN_REQUIRED':
        job_status_label = LOGIN_REQUIRED_TEXT
        job_status_state = 'LOGIN_REQUIRED'
        job_status_badge = 'badge-amber'
    elif c.crawl_status in ('BLOCKED', 'REDIRECT_BLOCKED'):
        job_status_label = 'Source Protected / Blocked'
        job_status_state = 'SOURCE_BLOCKED'
        job_status_badge = 'badge-amber'
    elif c.crawl_status == 'FAILED':
        job_status_label = 'Crawl Failed'
        job_status_state = 'CRAWL_FAILED'
        job_status_badge = 'badge-rose'
    elif c.crawl_status == 'IN_PROGRESS':
        job_status_label = 'Checking live career source...'
        job_status_state = 'CRAWL_IN_PROGRESS'
        job_status_badge = 'badge-amber'
    elif c.crawl_status == 'CRAWLED':
        if c.careers_url or c.jobs_page_url or c.ats_url:
            job_status_label = '0 Verified Jobs (Confirmed Zero)'
            job_status_state = 'VERIFIED_ZERO'
            job_status_badge = 'badge-slate'
        else:
            job_status_label = NOT_AVAILABLE_TEXT
            job_status_state = 'ATS_DISCOVERY_FAILED'
            job_status_badge = 'badge-amber'
    elif not c.careers_url and not c.jobs_page_url and not c.ats_url:
        job_status_label = NOT_AVAILABLE_TEXT
        job_status_state = 'ATS_DISCOVERY_FAILED'
        job_status_badge = 'badge-amber'
    else:
        job_status_label = 'Coverage Pending'
        job_status_state = 'PENDING_COVERAGE'
        job_status_badge = 'badge-slate'

    # CSR Status (including Login-Required state and Webpage/PDF availability)
    if published_csr_count > 0:
        csr_status_label = f'{published_csr_count} Verified CSR Projects'
        csr_status_state = 'VERIFIED'
        csr_status_badge = 'badge-emerald'
    elif c.csr_access == 'LOGIN_REQUIRED':
        csr_status_label = LOGIN_REQUIRED_TEXT
        csr_status_state = 'LOGIN_REQUIRED'
        csr_status_badge = 'badge-amber'
    elif best_csr_webpage:
        csr_status_label = f'Official CSR Source ({csr_display_format})'
        csr_status_state = 'PORTAL_IDENTIFIED'
        csr_status_badge = 'badge-teal'
    else:
        csr_status_label = NOT_AVAILABLE_TEXT
        csr_status_state = 'NOT_VERIFIED'
        csr_status_badge = 'badge-slate'

    login_required_sections = [
        label for label, mode in (
            ('Jobs', c.jobs_access),
            ('CSR', c.csr_access),
            ('Contacts', c.contacts_access),
        ) if mode == 'LOGIN_REQUIRED'
    ]

    d = {
        'company_id': c.company_id,
        'company_name': c.company_name,
        'legal_name': clean_text(c.legal_name),
        'isin': clean_text(c.isin),
        'nse_symbol': clean_text(c.nse_symbol),
        'bse_scrip_code': clean_text(c.bse_scrip_code),
        'listed_on_nse': c.listed_on_nse,
        'listed_on_bse': c.listed_on_bse,
        'listing_status': c.listing_status,
        'website_url': _valid_http_url(c.website_url),
        'sector': clean_text(c.sector),
        'headquarters': clean_text(c.headquarters),
        'cin': clean_text(c.cin),
        'last_crawled': c.last_crawled,
        'crawl_status': c.crawl_status,
        'data_confidence': c.data_confidence,
        'official_domain': clean_text(c.official_domain),
        'sustainability_url': _valid_http_url(c.sustainability_url),
        'esg_url': _valid_http_url(c.esg_url),
        'foundation_url': _valid_http_url(c.foundation_url),
        'annual_report_url': _valid_http_url(c.annual_report_url),
        'brsr_url': _valid_http_url(c.brsr_url),
        'investor_url': _valid_http_url(c.investor_url),
        'contact_page_url': _valid_http_url(c.contact_page_url),
        'ats_platform': clean_text(c.ats_platform),
        'verification_status': c.verification_status,
        'careers_url': _valid_http_url(c.careers_url),
        'jobs_access': c.jobs_access,
        'csr_access': c.csr_access,
        'contacts_access': c.contacts_access,
        'login_required_sections': login_required_sections,
        'has_login_required': len(login_required_sections) > 0,
        'data_access_note': clean_text(c.data_access_note),
        'login_required_text': LOGIN_REQUIRED_TEXT,
        'not_available_text': NOT_AVAILABLE_TEXT,
        'csr_portal_url': _valid_http_url(c.csr_portal_url),
        'csr_webpage_url': best_csr_webpage,
        'csr_links': csr_links,
        'csr_display_format': csr_display_format,
        'link_quality': c.link_quality,
        'link_verified_at': c.link_verified_at,
        'last_verified_display': c.link_verified_at or c.last_crawled or NOT_AVAILABLE_TEXT,
        'primary_csr_url': _valid_http_url(primary_project.source_url) if primary_project else best_csr_webpage,
        'primary_csr_name': clean_text(primary_project.project_name) if primary_project else None,
        'primary_csr_budget': clean_text(primary_project.budget) if primary_project else None,
        'primary_job_url': _valid_http_url(primary_job.application_url) if primary_job else None,
        'primary_ngo_url': _valid_http_url(primary_ngo.source_url) if primary_ngo else None,
        'opportunity_score': score_obj.score if score_obj else 0.0,
        'open_opportunities_count': open_opps,
        'job_count': verified_jobs_count,
        'verified_jobs_count': verified_jobs_count,
        'current_verified_jobs': verified_jobs_count,
        'job_status_label': job_status_label,
        'job_status_state': job_status_state,
        'job_status_badge': job_status_badge,
        'csr_count': published_csr_count,
        'published_csr_count': published_csr_count,
        'csr_status_label': csr_status_label,
        'csr_status_state': csr_status_state,
        'csr_status_badge': csr_status_badge,
        'sync_status': getattr(c, 'sync_status', 'IDLE'),
        'last_live_synced_at': c.last_live_synced_at.isoformat() if getattr(c, 'last_live_synced_at', None) else None,
        'last_sync_error': getattr(c, 'last_sync_error', None),
        'content_hash': getattr(c, 'content_hash', None),
    }
    return _normalize_company_dict(d)


def serialize_contact(ct: Contact):
    is_verified = (ct.verification_status or '') in VERIFIED_CONTACT_STATUSES
    email = clean_text(ct.email) if is_verified else None
    if email and is_generic_or_non_csr_contact_email(email):
        email = None
    phone = clean_text(ct.phone) if is_verified else None
    return {
        'contact_id': ct.contact_id,
        'company_id': ct.company_id,
        'name': clean_text(ct.name) if is_verified else None,
        'designation': clean_text(ct.designation) if is_verified else None,
        'department': clean_text(ct.department) if is_verified else None,
        'email': email,
        'phone': phone,
        'source_url': _valid_http_url(ct.source_url),
        'confidence': ct.confidence,
        'last_verified_date': ct.last_verified_date,
        'link_status': ct.link_status,
        'link_verified_at': ct.link_verified_at,
        'verification_status': ct.verification_status,
        'fingerprint': ct.fingerprint,
        'contact_note': (
            None if (is_verified and (email or phone)) else
            NOT_AVAILABLE_TEXT
        )
    }


def _annotate_company_metrics(qs):
    jobs_subquery = Subquery(
        Job.objects.filter(
            company_id=OuterRef('company_id')
        ).filter(
            public_job_q(prefix="")
        ).values('company_id').annotate(
            c=Count('job_row_id')
        ).values('c')[:1],
        output_field=IntegerField()
    )

    csr_subquery = Subquery(
        CSRProject.objects.filter(
            company_id=OuterRef('company_id'),
            verification_status__in=list(PUBLIC_VERIFICATION_STATUSES)
        ).values('company_id').annotate(
            c=Count('csr_id')
        ).values('c')[:1],
        output_field=IntegerField()
    )

    opps_subquery = Subquery(
        CSROpportunity.objects.filter(
            company_id=OuterRef('company_id'),
            verification_status__in=list(PUBLIC_VERIFICATION_STATUSES),
            status='OPEN'
        ).values('company_id').annotate(
            c=Count('opp_id')
        ).values('c')[:1],
        output_field=IntegerField()
    )

    return qs.annotate(
        active_verified_jobs_count=Coalesce(jobs_subquery, 0),
        published_csr_count_annotated=Coalesce(csr_subquery, 0),
        open_opps_count_annotated=Coalesce(opps_subquery, 0)
    ).order_by('-active_verified_jobs_count', '-score_record__score', 'company_name')


def companies_list_api(request):
    q = request.GET.get('q', '').strip()
    sector = request.GET.get('sector', '').strip()
    state = request.GET.get('state', '').strip()
    status = request.GET.get('status', '').strip()
    access = request.GET.get('access', '').strip()
    opp_only = request.GET.get('opp_only', '').lower() in ('true', '1')
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    limit = int(request.GET.get('limit', 5000))

    qs = Company.objects.select_related('score_record').prefetch_related(
        'csr_projects', 'jobs', 'ngo_collaborations', 'open_opportunities'
    )

    if q:
        qs = qs.filter(
            Q(company_name__icontains=q) |
            Q(nse_symbol__icontains=q) |
            Q(sector__icontains=q) |
            Q(headquarters__icontains=q)
        )
    if sector and sector != 'all':
        qs = qs.filter(sector=sector)
    if state and state != 'all':
        qs = qs.filter(headquarters__icontains=state)
    if access == 'LOGIN_REQUIRED':
        qs = qs.filter(
            Q(jobs_access='LOGIN_REQUIRED') |
            Q(csr_access='LOGIN_REQUIRED') |
            Q(contacts_access='LOGIN_REQUIRED')
        )
    elif access == 'PUBLIC':
        qs = qs.exclude(
            Q(jobs_access='LOGIN_REQUIRED') &
            Q(csr_access='LOGIN_REQUIRED')
        )
    if status and status != 'all':
        qs = qs.filter(crawl_status=status)
    if access == 'LOGIN_REQUIRED':
        qs = qs.filter(
            Q(jobs_access='LOGIN_REQUIRED') |
            Q(csr_access='LOGIN_REQUIRED') |
            Q(contacts_access='LOGIN_REQUIRED')
        )
    if opp_only:
        qs = qs.filter(
            open_opportunities__status='OPEN',
            open_opportunities__verification_status__in=list(PUBLIC_VERIFICATION_STATUSES)
        ).distinct()

    qs = _annotate_company_metrics(qs)

    data = paginate_queryset(
        queryset=qs,
        serialize_func=serialize_company_list_item,
        page=page,
        page_size=page_size,
        fallback_limit=limit
    )
    return JsonResponse(data, safe=False)


def company_detail_api(request, company_id):
    qs = Company.objects.filter(company_id=company_id)
    qs = _annotate_company_metrics(qs).select_related('score_record', 'prospect_entry')
    c = qs.first()
    if not c:
        return JsonResponse({'detail': 'Company not found'}, status=404)

    score_obj = getattr(c, 'score_record', None)
    prospect_obj = getattr(c, 'prospect_entry', None)

    d = serialize_company_list_item(c)
    d['opportunity_score'] = {
        'active_csr': score_obj.active_csr if score_obj else 0.0,
        'focus_match': score_obj.focus_match if score_obj else 0.0,
        'recent_activity': score_obj.recent_activity if score_obj else 0.0,
        'ngo_activity': score_obj.ngo_activity if score_obj else 0.0,
        'opportunity_page': score_obj.opportunity_page if score_obj else 0.0,
        'contact_availability': score_obj.contact_availability if score_obj else 0.0,
        'geographic_match': score_obj.geographic_match if score_obj else 0.0,
        'score': score_obj.score if score_obj else 0.0,
        'evidence_status': score_obj.evidence_status if score_obj else NOT_AVAILABLE_TEXT,
        'rationale': score_obj.rationale if score_obj else '',
        'scored_at': score_obj.scored_at if score_obj else None,
    } if score_obj else None

    d['prospect_status'] = {
        'prospect_id': prospect_obj.prospect_id,
        'stage': prospect_obj.stage,
        'notes': prospect_obj.notes,
        'assigned_to': prospect_obj.assigned_to,
        'target_proposal': prospect_obj.target_proposal,
        'follow_up_date': prospect_obj.follow_up_date,
        'match_score': prospect_obj.match_score,
        'created_at': prospect_obj.created_at,
        'updated_at': prospect_obj.updated_at,
    } if prospect_obj else None

    return JsonResponse(d)


def company_dossier_api(request, company_id):
    """
    Unified strategic dossier:
    Provides standardized data across all 10 universal sections with strict source verification,
    including all CSR webpage/PDF links and login-required indicators.
    """
    from modules.website.views.job_api_views import serialize_job_item, apply_job_safety_filters
    from modules.website.views.opportunity_api_views import (
        serialize_project_item, serialize_opportunity_item, extract_reporting_period
    )
    try:
        c = Company.objects.get(company_id=company_id)
    except Company.DoesNotExist:
        return JsonResponse({'detail': 'Company not found'}, status=404)

    reg_obj = getattr(c, 'completeness_register', None)

    # 1. Verified CSR Projects (excluding generic webpage titles)
    raw_projects = public_records(c.csr_projects.all()).exclude(
        source_url__isnull=True
    ).exclude(source_url='').exclude(
        evidence_text__isnull=True
    ).exclude(evidence_text='').order_by('-confidence', '-csr_id')

    projects = [
        serialize_project_item(p)
        for p in raw_projects
        if not is_page_title_not_csr_project(p.project_name, c.company_name)
    ]

    # 2. Verified Active Jobs
    jobs_qs = list(public_jobs(c.jobs.select_related('company')).order_by('-last_checked_date'))
    jobs = [serialize_job_item(j) for j in jobs_qs]
    stale_jobs = []

    # 3. NGO Partners & Collaborations (verified only)
    partners = list(public_records(c.ngo_collaborations.all()).values())

    # 4. Publicly Verified Contacts (excluding generic info@/webmaster@ mailboxes)
    contacts = []
    for ct in public_records(c.contacts.all()):
        serialized_ct = serialize_contact(ct)
        if serialized_ct.get('email') or serialized_ct.get('phone'):
            contacts.append(serialized_ct)

    # 5. Open & Closed Opportunities (strictly verified)
    opps = [
        serialize_opportunity_item(o)
        for o in public_records(c.open_opportunities.all()).filter(status='OPEN').exclude(
            (Q(source_url__isnull=True) | Q(source_url='')) & (Q(portal_url__isnull=True) | Q(portal_url=''))
        ).exclude(evidence_text__isnull=True).exclude(evidence_text='').order_by('-opp_id')
    ]
    closed_opps = [
        serialize_opportunity_item(o)
        for o in public_records(c.open_opportunities.all()).filter(status='CLOSED').order_by('-opp_id')
    ]

    # 6. Authentic Reports, CSR Webpages & Documents
    best_csr_webpage, csr_links, csr_display_format = _build_company_csr_links(c)

    # Also include crawled CSR webpages and CSR PDFs from PageRecord
    crawled_csr_pages = []
    seen_csr_urls = {item['url'] for item in csr_links}
    for pr in c.crawled_pages.filter(page_type__in=['CSR', 'CSR_PDF'], status='200').order_by('-page_id')[:20]:
        u = _valid_http_url(pr.url)
        if not u:
            continue
        fmt = detect_csr_source_format(u)
        crawled_csr_pages.append({
            'page_id': pr.page_id,
            'title': clean_text(pr.title) or f"{c.company_name} CSR Source",
            'url': u,
            'page_type': pr.page_type,
            'format': fmt,
            'last_crawled': pr.last_crawled,
        })
        if u not in seen_csr_urls:
            seen_csr_urls.add(u)
            csr_links.append({
                'label': clean_text(pr.title) or ('CSR PDF Disclosure' if pr.page_type == 'CSR_PDF' else 'Crawled CSR Webpage'),
                'url': u,
                'format': fmt,
            })

    official_reports = []
    if _valid_http_url(c.annual_report_url):
        official_reports.append({
            'title': f'{c.company_name} Statutory Annual Report',
            'document_type': 'ANNUAL_REPORT',
            'reporting_period': extract_reporting_period('', c.annual_report_url),
            'source_url': _valid_http_url(c.annual_report_url),
            'format': detect_csr_source_format(c.annual_report_url),
            'status': 'VERIFIED'
        })
    if _valid_http_url(c.brsr_url):
        official_reports.append({
            'title': f'{c.company_name} SEBI BRSR Core Disclosures',
            'document_type': 'BRSR_REPORT',
            'reporting_period': extract_reporting_period('', c.brsr_url),
            'source_url': _valid_http_url(c.brsr_url),
            'format': detect_csr_source_format(c.brsr_url),
            'status': 'VERIFIED'
        })
    if _valid_http_url(c.csr_portal_url):
        official_reports.append({
            'title': f'{c.company_name} Section 135 CSR Webpage & Disclosures',
            'document_type': 'CSR_DISCLOSURES',
            'reporting_period': extract_reporting_period('', c.csr_portal_url),
            'source_url': _valid_http_url(c.csr_portal_url),
            'format': detect_csr_source_format(c.csr_portal_url),
            'status': 'VERIFIED'
        })
    if _valid_http_url(c.foundation_url):
        official_reports.append({
            'title': f'{c.company_name} Corporate Foundation Portal',
            'document_type': 'FOUNDATION_PORTAL',
            'reporting_period': None,
            'source_url': _valid_http_url(c.foundation_url),
            'format': detect_csr_source_format(c.foundation_url),
            'status': 'VERIFIED'
        })
    if _valid_http_url(c.sustainability_url):
        official_reports.append({
            'title': f'{c.company_name} Sustainability & ESG Webpage',
            'document_type': 'SUSTAINABILITY_REPORT',
            'reporting_period': extract_reporting_period('', c.sustainability_url),
            'source_url': _valid_http_url(c.sustainability_url),
            'format': detect_csr_source_format(c.sustainability_url),
            'status': 'VERIFIED'
        })
    if _valid_http_url(c.esg_url):
        official_reports.append({
            'title': f'{c.company_name} ESG Portal & Disclosures',
            'document_type': 'ESG_DISCLOSURE',
            'reporting_period': extract_reporting_period('', c.esg_url),
            'source_url': _valid_http_url(c.esg_url),
            'format': detect_csr_source_format(c.esg_url),
            'status': 'VERIFIED'
        })
    if _valid_http_url(c.investor_url):
        official_reports.append({
            'title': f'{c.company_name} Investor Relations & Corporate Governance Disclosures',
            'document_type': 'GOVERNANCE_DISCLOSURE',
            'reporting_period': None,
            'source_url': _valid_http_url(c.investor_url),
            'format': detect_csr_source_format(c.investor_url),
            'status': 'VERIFIED'
        })

    for doc in c.documents.all():
        official_reports.append({
            'title': doc.title,
            'document_type': doc.document_type,
            'reporting_period': clean_text(doc.notes),
            'source_url': doc.file.url if doc.file else '',
            'format': doc.file_format or 'DOCUMENT',
            'status': doc.status,
            'file_format': doc.file_format,
            'file_size': doc.file_size
        })

    score_obj = getattr(c, 'score_record', None)
    prospect_obj = getattr(c, 'prospect_entry', None)

    # 7. Coverage Audit Breakdown
    coverage_audit = {
        'overall_status': reg_obj.overall_coverage_status if reg_obj else c.crawl_status,
        'corporate_profile_status': reg_obj.corporate_profile_status if reg_obj else 'VERIFIED',
        'official_url_status': reg_obj.official_url_status if reg_obj else ('VERIFIED' if c.website_url else NOT_AVAILABLE_TEXT),
        'careers_source_status': LOGIN_REQUIRED_TEXT if c.jobs_access == 'LOGIN_REQUIRED' else (reg_obj.careers_source_status if reg_obj else ('VERIFIED' if c.careers_url else NOT_AVAILABLE_TEXT)),
        'ats_platform': (reg_obj.ats_platform if reg_obj else None) or clean_text(c.ats_platform) or NOT_AVAILABLE_TEXT,
        'ats_discovery_status': reg_obj.ats_discovery_status if reg_obj else ('VERIFIED' if c.ats_platform else NOT_AVAILABLE_TEXT),
        'jobs_status': LOGIN_REQUIRED_TEXT if c.jobs_access == 'LOGIN_REQUIRED' else (reg_obj.jobs_status if reg_obj else ('VERIFIED' if jobs else ('VERIFIED_ZERO_JOBS' if c.careers_url else NOT_AVAILABLE_TEXT))),
        'jobs_discovered': reg_obj.jobs_discovered if reg_obj else len(jobs),
        'jobs_published': len(jobs),
        'csr_status': LOGIN_REQUIRED_TEXT if c.csr_access == 'LOGIN_REQUIRED' else (reg_obj.csr_projects_status if reg_obj else ('VERIFIED' if (projects or best_csr_webpage) else NOT_AVAILABLE_TEXT)),
        'csr_published': len(projects),
        'annual_reports_status': reg_obj.annual_reports_status if reg_obj else ('VERIFIED' if c.annual_report_url else NOT_AVAILABLE_TEXT),
        'brsr_esg_status': reg_obj.brsr_esg_status if reg_obj else ('VERIFIED' if c.brsr_url else NOT_AVAILABLE_TEXT),
        'opportunities_status': reg_obj.opportunities_status if reg_obj else ('VERIFIED' if opps else 'NO_RECORDS_CONFIRMED'),
        'contacts_status': LOGIN_REQUIRED_TEXT if c.contacts_access == 'LOGIN_REQUIRED' else (reg_obj.contacts_status if reg_obj else ('VERIFIED' if contacts else 'NO_RECORDS_CONFIRMED')),
        'last_attempt_at': reg_obj.last_attempt_at.strftime('%d %b %Y, %H:%M') if reg_obj and reg_obj.last_attempt_at else (c.last_crawled or NOT_AVAILABLE_TEXT),
        'last_successful_fetch_at': reg_obj.last_successful_fetch_at.strftime('%d %b %Y, %H:%M') if reg_obj and reg_obj.last_successful_fetch_at else (c.link_verified_at or c.last_crawled or NOT_AVAILABLE_TEXT),
        'failed_requests_error': reg_obj.failed_requests_error if reg_obj and reg_obj.failed_requests_error else None,
    }

    # 8. Intelligence Summary Cards
    intelligence_summary = {
        'eligible_published_jobs': len(jobs),
        'jobs_status': coverage_audit['jobs_status'],
        'verified_csr_projects': len(projects),
        'csr_status': coverage_audit['csr_status'],
        'open_opportunities': len(opps),
        'closed_opportunities': len(closed_opps),
        'published_contacts': len(contacts),
        'available_reports': len(official_reports),
        'last_source_check': coverage_audit['last_successful_fetch_at'],
        'overall_coverage_status': coverage_audit['overall_status'],
    }

    cname = c.company_name
    sector = clean_text(c.sector)
    hq = clean_text(c.headquarters)
    symbol = clean_text(c.nse_symbol)

    cats = list(dict.fromkeys([cat.strip() for p in projects for cat in (p.get('category') or '').split(';') if cat.strip()]))
    states = list(dict.fromkeys([st.strip() for p in projects for st in (p.get('state') or '').split(';') if st.strip()]))
    budget_sum = projects[0].get('budget') if projects else None

    who_parts = [f"{cname}"]
    if symbol:
        who_parts.append(f"({symbol})")
    who_parts.append("is a listed corporation")
    if hq:
        who_parts.append(f"headquartered in {hq}")
    if sector:
        who_parts.append(f"in the {sector} sector")
    if projects:
        who_parts.append("with publicly documented CSR activity on its official website.")
    elif best_csr_webpage:
        who_parts.append(f"with an official CSR source published at {best_csr_webpage}.")
    elif c.csr_access == 'LOGIN_REQUIRED':
        who_parts.append(f"({LOGIN_REQUIRED_TEXT}).")
    else:
        who_parts.append(f"({NOT_AVAILABLE_TEXT}).")
    who = " ".join(who_parts)

    cats_text = ', '.join(cats[:3]) if cats else None
    states_text = ', '.join(states[:3]) if states else None
    partner_count = len(partners)
    why_parts = []
    if cats_text and states_text:
        why_parts.append(f"Documented CSR focus in {cats_text}, active in {states_text}.")
    elif cats_text:
        why_parts.append(f"Documented CSR focus in {cats_text}.")
    elif states_text:
        why_parts.append(f"Documented CSR activity in {states_text}.")
    if projects or partner_count:
        why_parts.append(
            f"The platform has catalogued {len(projects)} verified CSR project record(s) and "
            f"{partner_count} recorded NGO collaboration(s) from the company’s official web pages/PDFs."
        )
    elif c.csr_access == 'LOGIN_REQUIRED':
        why_parts.append(LOGIN_REQUIRED_TEXT + ".")
    else:
        why_parts.append(NOT_AVAILABLE_TEXT + ".")
    if budget_sum and projects:
        why_parts.append(f"Disclosed project budget on record: {budget_sum}.")
    why = " ".join(why_parts)

    # Strictly use CSR webpage link — NEVER fall back to careers_url!
    csr_link = best_csr_webpage
    opp_lead = opps[0] if opps else None
    verified_contacts = [ct for ct in contacts if ct.get('email')]

    if verified_contacts:
        how = f"Contact the verified CSR contact listed in this dossier" + (f", or visit the company’s official CSR page: {csr_link}." if csr_link else ".")
    elif csr_link:
        how = f"Open the company’s official CSR webpage ({csr_link}) to review CSR disclosures and partnership details published there." + (f" An open call ({opp_lead['title']}) is currently listed." if opp_lead else "")
    elif c.csr_access == 'LOGIN_REQUIRED':
        how = LOGIN_REQUIRED_TEXT
    else:
        how = NOT_AVAILABLE_TEXT

    c.active_verified_jobs_count = len(jobs)
    c.published_csr_count_annotated = len(projects)
    c.open_opps_count_annotated = len(opps)
    c._prefetched_objects_cache = {
        'jobs': jobs_qs,
        'csr_projects': raw_projects,
        'ngo_collaborations': list(public_records(c.ngo_collaborations.all()))
    }
    comp_dict = _normalize_company_dict(serialize_company_list_item(c))
    comp_dict['csr_links'] = csr_links
    comp_dict['csr_webpage_url'] = best_csr_webpage
    comp_dict['csr_display_format'] = csr_display_format

    score_dict = {
        'company_id': score_obj.company_id,
        'active_csr': score_obj.active_csr,
        'focus_match': score_obj.focus_match,
        'recent_activity': score_obj.recent_activity,
        'ngo_activity': score_obj.ngo_activity,
        'opportunity_page': score_obj.opportunity_page,
        'contact_availability': score_obj.contact_availability,
        'geographic_match': score_obj.geographic_match,
        'score': score_obj.score,
        'evidence_status': score_obj.evidence_status,
        'rationale': score_obj.rationale,
        'scored_at': score_obj.scored_at,
    } if score_obj else None

    prospect_dict = {
        'prospect_id': prospect_obj.prospect_id,
        'company_id': prospect_obj.company_id,
        'stage': prospect_obj.stage,
        'notes': prospect_obj.notes,
        'assigned_to': prospect_obj.assigned_to,
        'target_proposal': prospect_obj.target_proposal,
        'follow_up_date': prospect_obj.follow_up_date,
        'match_score': prospect_obj.match_score,
        'created_at': prospect_obj.created_at,
        'updated_at': prospect_obj.updated_at,
    } if prospect_obj else None

    return JsonResponse({
        'company': comp_dict,
        'opportunity_score': score_dict,
        'intelligence_summary': intelligence_summary,
        'data_access': {
            'jobs': c.jobs_access, 'csr': c.csr_access, 'contacts': c.contacts_access,
            'note': clean_text(c.data_access_note),
            'checked_at': c.data_access_checked_at.isoformat() if c.data_access_checked_at else None,
            'login_required_text': LOGIN_REQUIRED_TEXT,
            'not_available_text': NOT_AVAILABLE_TEXT,
            'login_required_sections': [k for k, v in (('Jobs', c.jobs_access), ('CSR', c.csr_access), ('Contacts', c.contacts_access)) if v == 'LOGIN_REQUIRED'],
        },
        'csr_overview': {
            'csr_webpage_url': best_csr_webpage,
            'csr_portal_url': _valid_http_url(c.csr_portal_url),
            'foundation_url': _valid_http_url(c.foundation_url),
            'sustainability_url': _valid_http_url(c.sustainability_url),
            'esg_url': _valid_http_url(c.esg_url),
            'brsr_url': _valid_http_url(c.brsr_url),
            'annual_report_url': _valid_http_url(c.annual_report_url),
            'csr_display_format': csr_display_format,
            'csr_access': c.csr_access,
            'csr_links': csr_links,
            'crawled_csr_pages': crawled_csr_pages,
            'projects_count': len(projects),
            'opportunities_count': len(opps),
        },
        'coverage_audit': coverage_audit,
        'official_reports': official_reports,
        'strategic_playbook': {
            'who': who,
            'why': why,
            'how': how,
            'top_categories': cats,
            'top_states': states,
            'budget_summary': budget_sum
        },
        'projects': projects,
        'partners': partners,
        'jobs': jobs,
        'stale_jobs': stale_jobs,
        'contacts': contacts,
        'opportunities': opps,
        'closed_opportunities': closed_opps,
        'prospect_info': prospect_dict
    })


def company_csr_api(request, company_id):
    from modules.website.views.opportunity_api_views import serialize_project_item
    try:
        c = Company.objects.get(company_id=company_id)
    except Company.DoesNotExist:
        c = None
    cname = c.company_name if c else None
    projects = [
        serialize_project_item(p)
        for p in public_records(CSRProject.objects.select_related('company').filter(company_id=company_id)).order_by('-confidence')
        if not is_page_title_not_csr_project(p.project_name, cname)
    ]
    return JsonResponse(projects, safe=False)


def company_jobs_api(request, company_id):
    from modules.website.views.job_api_views import serialize_job_item, apply_job_safety_filters
    include_stale = request.GET.get('include_stale', '').lower() in ('true', '1')
    qs = Job.objects.select_related('company').filter(company_id=company_id)
    if not include_stale:
        qs = public_jobs(qs)
    else:
        qs = apply_job_safety_filters(qs)
    jobs = [serialize_job_item(j) for j in qs.order_by('-last_checked_date')]
    return JsonResponse(jobs, safe=False)


def company_partners_api(request, company_id):
    partners = list(public_records(NGOCollaboration.objects.filter(company_id=company_id)).values())
    return JsonResponse(partners, safe=False)


def company_contacts_api(request, company_id):
    contacts = []
    for ct in Contact.objects.filter(company_id=company_id, verification_status__in=VERIFIED_CONTACT_STATUSES):
        item = serialize_contact(ct)
        if item.get('email') or item.get('phone'):
            contacts.append(item)
    return JsonResponse(contacts, safe=False)


from django.core.cache import cache
import hashlib


def recommendations_api(request):
    query_str = request.META.get('QUERY_STRING', '')
    cache_key = f"rec_api_{hashlib.md5(query_str.encode('utf-8')).hexdigest()}"
    cached_data = cache.get(cache_key)
    if cached_data is not None and not request.GET.get('refresh'):
        return JsonResponse(cached_data, safe=False)

    q = request.GET.get('q', '').strip()
    sector = request.GET.get('sector', '').strip()
    state = request.GET.get('state', '').strip()
    min_score = float(request.GET.get('min_score', 0.0))
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    limit = int(request.GET.get('limit', 5000))

    cause = request.GET.get('cause', '').strip().lower()
    access = request.GET.get('access', '').strip().upper()

    qs = Company.objects.select_related('score_record').prefetch_related(
        'csr_projects', 'jobs', 'ngo_collaborations', 'open_opportunities'
    )
    if min_score > 0:
        qs = qs.filter(score_record__score__gte=min_score)
    if q:
        qs = qs.filter(
            Q(company_name__icontains=q) |
            Q(nse_symbol__icontains=q) |
            Q(sector__icontains=q)
        )
    if sector and sector != 'all':
        qs = qs.filter(sector=sector)
    if state and state != 'all':
        qs = qs.filter(headquarters__icontains=state)
    if access == 'LOGIN_REQUIRED':
        qs = qs.filter(
            Q(jobs_access='LOGIN_REQUIRED') |
            Q(csr_access='LOGIN_REQUIRED') |
            Q(contacts_access='LOGIN_REQUIRED')
        )
    elif access == 'PUBLIC':
        qs = qs.exclude(
            Q(jobs_access='LOGIN_REQUIRED') &
            Q(csr_access='LOGIN_REQUIRED')
        )
    if cause and cause != 'all':
        if cause in ('others', 'other'):
            standard_causes = ['education', 'health', 'rural', 'women', 'environment', 'water', 'skill']
            for sc in standard_causes:
                qs = qs.exclude(csr_projects__category__icontains=sc)
        elif cause == 'uncategorized':
            qs = qs.filter(csr_projects__isnull=True)
        else:
            qs = qs.filter(
                Q(csr_projects__category__icontains=cause) |
                Q(csr_projects__project_name__icontains=cause) |
                Q(sector__icontains=cause)
            ).distinct()

    qs = _annotate_company_metrics(qs)

    def serialize_rec(c: Company):
        d = serialize_company_list_item(c)
        score_obj = getattr(c, 'score_record', None)
        if score_obj:
            d['active_csr'] = score_obj.active_csr
            d['focus_match'] = score_obj.focus_match
            d['recent_activity'] = score_obj.recent_activity
            d['ngo_activity'] = score_obj.ngo_activity
            d['opportunity_page'] = score_obj.opportunity_page
            d['contact_availability'] = score_obj.contact_availability
            d['geographic_match'] = score_obj.geographic_match
            d['score'] = score_obj.score
            d['evidence_status'] = score_obj.evidence_status
            d['rationale'] = score_obj.rationale
            d['scored_at'] = score_obj.scored_at
        return d

    data = paginate_queryset(
        queryset=qs,
        serialize_func=serialize_rec,
        page=page,
        page_size=page_size,
        fallback_limit=limit
    )
    cache.set(cache_key, data, 120)
    return JsonResponse(data, safe=False)


from django.views.decorators.csrf import csrf_exempt
from modules.crawler_engine.live_syncer import sync_company_live


@csrf_exempt
def company_fetch_live_api(request, company_id):
    """
    POST /api/companies/<str:company_id>/fetch-live/
    Triggers an on-demand 1:1 live delta sync for a single company directly from its live website.
    Updates MySQL in real-time and returns the diff summary and updated company record.
    """
    if request.method not in ('POST', 'GET'):
        return JsonResponse({'status': 'error', 'message': 'Method not allowed. Use POST.'}, status=405)

    comp = Company.objects.filter(company_id=str(company_id).strip()).first()
    if not comp and str(company_id).isdigit():
        comp = Company.objects.filter(
            models.Q(company_id=f"COMP_TOP200_{int(company_id):03d}")
            | models.Q(company_id=f"COMP_{company_id}")
        ).first()
    if not comp:
        comp = Company.objects.filter(official_domain__icontains=str(company_id).strip()).first()

    if not comp:
        return JsonResponse({'status': 'error', 'message': f"Company with identifier '{company_id}' not found."}, status=404)

    diff = sync_company_live(company=comp)
    comp.refresh_from_db()

    serialized_company = serialize_company_list_item(comp)

    return JsonResponse({
        'status': 'ok' if diff.get('status') == 'SUCCESS' else 'error',
        'diff': diff,
        'company': serialized_company,
        'message': (
            f"Live Sync Complete: {diff.get('active_jobs_count', 0)} Active Jobs "
            f"(+{diff.get('jobs_added', 0)} Added, ~{diff.get('jobs_updated', 0)} Updated, -{diff.get('jobs_removed', 0)} Removed), "
            f"{diff.get('active_csr_count', 0)} CSR Projects verified."
        ),
    })

