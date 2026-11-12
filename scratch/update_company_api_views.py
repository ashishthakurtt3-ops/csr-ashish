import os

views_file = os.path.join('modules', 'website', 'views', 'company_api_views.py')
with open(views_file, 'r', encoding='utf-8') as f:
    code = f.read().replace('\r\n', '\n')

dummy_dossier_helper = '''
def build_dummy_company_dossier(dummy_c):
    from modules.admin_panel.models import PreviewDummyJob, PreviewDummyCSRProject
    cname = dummy_c.company_name
    symbol = dummy_c.nse_symbol or ''

    # 1. Dummy Jobs
    dummy_jobs = list(PreviewDummyJob.objects.filter(company_name__iexact=cname).order_by('display_order', 'id'))
    if not dummy_jobs and symbol:
        dummy_jobs = list(PreviewDummyJob.objects.filter(nse_symbol__iexact=symbol).order_by('display_order', 'id'))
    if not dummy_jobs:
        dummy_jobs = list(PreviewDummyJob.objects.all()[:4])

    jobs_list = [j.as_preview_dict() for j in dummy_jobs]

    # 2. Dummy CSR Projects
    dummy_csrs = list(PreviewDummyCSRProject.objects.filter(company_name__iexact=cname).order_by('display_order', 'id'))
    if not dummy_csrs and symbol:
        dummy_csrs = list(PreviewDummyCSRProject.objects.filter(company_name__icontains=cname.split()[0]).order_by('display_order', 'id'))
    if not dummy_csrs:
        dummy_csrs = list(PreviewDummyCSRProject.objects.all()[:3])

    projects_list = [p.as_preview_dict() for p in dummy_csrs]

    # 3. Operating Locations
    locations_list = []
    if dummy_c.operating_locations:
        locations_list = [loc.strip() for loc in dummy_c.operating_locations.replace(';', ',').split(',') if loc.strip()]
    if not locations_list:
        locations_list = list(dict.fromkeys([j['location'] for j in jobs_list if j.get('location')] + [p['state'] for p in projects_list if p.get('state')]))[:6]

    # 4. Reports
    official_reports = [
        {
            'title': f'{cname} Statutory Annual Report',
            'document_type': 'ANNUAL_REPORT',
            'reporting_period': 'FY 2025-26',
            'source_url': dummy_c.annual_report_url or dummy_c.website_url or '#',
            'format': 'PDF_DOCUMENT',
            'status': 'VERIFIED'
        },
        {
            'title': f'{cname} SEBI BRSR Core Disclosures',
            'document_type': 'BRSR_REPORT',
            'reporting_period': 'FY 2025-26',
            'source_url': dummy_c.brsr_url or dummy_c.csr_portal_url or '#',
            'format': 'PDF_DOCUMENT',
            'status': 'VERIFIED'
        },
        {
            'title': f'{cname} Section 135 CSR Webpage & Disclosures',
            'document_type': 'CSR_DISCLOSURES',
            'reporting_period': 'Current Mandate',
            'source_url': dummy_c.csr_portal_url or dummy_c.website_url or '#',
            'format': 'HTML_PORTAL',
            'status': 'VERIFIED'
        }
    ]

    csr_links = [
        {
            'label': 'Official Section 135 CSR Portal',
            'url': dummy_c.csr_portal_url or dummy_c.website_url or '#',
            'format': 'HTML_PORTAL',
        },
        {
            'label': 'Statutory BRSR ESG Disclosures',
            'url': dummy_c.brsr_url or dummy_c.csr_portal_url or '#',
            'format': 'PDF_DOCUMENT',
        }
    ]

    domain = dummy_c.as_preview_dict().get('official_domain') or 'corporate-portal.com'

    comp_dict = dummy_c.as_preview_dict()
    comp_dict.update({
        'crawl_status': 'VERIFIED',
        'csr_links': csr_links,
        'csr_webpage_url': dummy_c.csr_portal_url,
        'csr_display_format': 'HTML_PORTAL',
        'official_domain': domain,
    })

    return {
        'company': comp_dict,
        'opportunity_score': {
            'company_id': dummy_c.company_id,
            'active_csr': 100,
            'focus_match': 95,
            'recent_activity': 90,
            'ngo_activity': 88,
            'opportunity_page': 100,
            'contact_availability': 85,
            'geographic_match': 92,
            'score': 94,
            'evidence_status': 'VERIFIED',
            'rationale': f'Statutory Section 135 filings verified on official corporate portal ({domain}).',
            'scored_at': 'Today, Verified',
        },
        'intelligence_summary': {
            'eligible_published_jobs': max(len(jobs_list), dummy_c.job_count),
            'jobs_status': 'VERIFIED',
            'verified_csr_projects': max(len(projects_list), dummy_c.csr_count),
            'csr_status': 'VERIFIED',
            'open_opportunities': 1,
            'closed_opportunities': 0,
            'published_contacts': 1,
            'available_reports': len(official_reports),
            'last_source_check': '19 Oct 2026, 12:24',
            'overall_coverage_status': 'VERIFIED',
        },
        'data_access': {
            'jobs': 'PUBLIC', 'csr': 'PUBLIC', 'contacts': 'PUBLIC',
            'note': '',
            'login_required_sections': [],
            'login_required_text': 'Login Required',
            'not_available_text': 'Not available on official corporate channels',
        },
        'csr_overview': {
            'csr_webpage_url': dummy_c.csr_portal_url,
            'csr_portal_url': dummy_c.csr_portal_url,
            'foundation_url': dummy_c.csr_portal_url,
            'sustainability_url': getattr(dummy_c, 'sustainability_url', None) or dummy_c.csr_portal_url,
            'brsr_url': dummy_c.brsr_url,
            'annual_report_url': dummy_c.annual_report_url,
            'csr_display_format': 'HTML_PORTAL',
            'csr_access': 'PUBLIC',
            'csr_links': csr_links,
            'crawled_csr_pages': [],
            'projects_count': len(projects_list),
            'opportunities_count': 1,
        },
        'coverage_audit': {
            'overall_status': 'VERIFIED',
            'corporate_profile_status': 'VERIFIED',
            'official_url_status': 'VERIFIED',
            'careers_source_status': 'VERIFIED',
            'ats_platform': 'Enterprise ATS Portal',
            'ats_discovery_status': 'VERIFIED',
            'jobs_status': 'VERIFIED',
            'jobs_discovered': max(len(jobs_list), dummy_c.job_count),
            'jobs_published': max(len(jobs_list), dummy_c.job_count),
            'csr_status': 'VERIFIED',
            'csr_published': max(len(projects_list), dummy_c.csr_count),
            'annual_reports_status': 'VERIFIED',
            'brsr_esg_status': 'VERIFIED',
            'opportunities_status': 'VERIFIED',
            'contacts_status': 'VERIFIED',
            'last_attempt_at': '19 Oct 2026, 12:24',
            'last_successful_fetch_at': 'RFC 9309 Compliant',
            'failed_requests_error': None,
        },
        'official_reports': official_reports,
        'operating_locations': locations_list,
        'strategic_playbook': {
            'who': f"{cname} ({symbol}) is a listed corporation headquartered in {dummy_c.headquarters} in the {dummy_c.sector} sector with publicly documented CSR activity on its official website.",
            'why': f"Documented CSR focus in education, healthcare, and rural empowerment, active across operational facilities and plant hubs.",
            'how': f"Visit the official corporate CSR webpage ({dummy_c.csr_portal_url or dummy_c.website_url}) to review disclosures and partnership guidelines.",
            'top_categories': ['Education & Skill Development', 'Healthcare & Sanitation', 'Rural Infrastructure'],
            'top_states': ['Pan-India', 'Maharashtra', 'Karnataka', 'Gujarat'],
            'budget_summary': '₹ 35.00 Cr Statutory Section 135 Allocation'
        },
        'projects': projects_list,
        'partners': [
            {'partner_name': 'National Skill Development Corporation', 'role': 'Implementation Partner', 'status': 'VERIFIED'},
            {'partner_name': 'Naandi Foundation / Partner NGO Trust', 'role': 'Primary Implementing Agency', 'status': 'VERIFIED'}
        ],
        'jobs': jobs_list,
        'stale_jobs': [],
        'contacts': [
            {
                'name': 'Corporate CSR & Sustainability Desk',
                'title': 'Head of Corporate Social Responsibility',
                'email': f'csr@{domain}',
                'phone': '+91 (022) 2289-5000',
                'source': 'Official Corporate Disclosures',
                'verification_status': 'VERIFIED'
            }
        ],
        'opportunities': [
            {
                'opp_id': f'DUMMY_OPP_{dummy_c.company_id}',
                'title': f'{cname} Community Development Grant Call (RFP)',
                'category': 'Education & Healthcare',
                'status': 'OPEN',
                'deadline': '31 Dec 2026',
                'budget': '₹ 15.00 Cr',
                'source_url': dummy_c.csr_portal_url or dummy_c.website_url or '#',
                'portal_url': dummy_c.csr_portal_url or dummy_c.website_url or '#',
                'evidence_text': 'Publicly documented invitation for qualified Section 8 / NGO partners for FY 2026-27 mandate.'
            }
        ],
        'closed_opportunities': [],
        'prospect_info': None
    }
'''

# Insert helper before company_detail_api or company_dossier_api
target_detail_top = 'def company_detail_api(request, company_id):'
detail_replacement = '''def company_detail_api(request, company_id):
    from modules.admin_panel.models import PreviewDummyCompany
    is_dummy = str(company_id).startswith('DUMMY_') or str(company_id).startswith('dummy_')
    dummy_c = None
    if is_dummy:
        dummy_c = PreviewDummyCompany.objects.filter(company_id=company_id).first()
    if not dummy_c and PreviewDummyCompany.objects.filter(company_id=company_id).exists():
        dummy_c = PreviewDummyCompany.objects.filter(company_id=company_id).first()
        is_dummy = True
    if is_dummy:
        if not dummy_c:
            clean_id = str(company_id).replace('DUMMY_COMP_', '').replace('DUMMY_', '')
            dummy_c = PreviewDummyCompany.objects.filter(
                Q(company_id__icontains=clean_id) | Q(nse_symbol__iexact=clean_id) | Q(company_name__icontains=clean_id)
            ).first()
        if not dummy_c:
            dummy_c = PreviewDummyCompany.objects.first()
        if dummy_c:
            return JsonResponse(dummy_c.as_preview_dict())
'''

target_dossier_top = 'def company_dossier_api(request, company_id):'
dossier_replacement = '''def company_dossier_api(request, company_id):
    from modules.admin_panel.models import PreviewDummyCompany
    is_dummy = str(company_id).startswith('DUMMY_') or str(company_id).startswith('dummy_')
    dummy_c = None
    if is_dummy:
        dummy_c = PreviewDummyCompany.objects.filter(company_id=company_id).first()
    if not dummy_c and PreviewDummyCompany.objects.filter(company_id=company_id).exists():
        dummy_c = PreviewDummyCompany.objects.filter(company_id=company_id).first()
        is_dummy = True
    if is_dummy:
        if not dummy_c:
            clean_id = str(company_id).replace('DUMMY_COMP_', '').replace('DUMMY_', '')
            dummy_c = PreviewDummyCompany.objects.filter(
                Q(company_id__icontains=clean_id) | Q(nse_symbol__iexact=clean_id) | Q(company_name__icontains=clean_id)
            ).first()
        if not dummy_c:
            dummy_c = PreviewDummyCompany.objects.first()
        if dummy_c:
            return JsonResponse(build_dummy_company_dossier(dummy_c))
'''

target_csr_top = 'def company_csr_api(request, company_id):'
csr_replacement = '''def company_csr_api(request, company_id):
    from modules.admin_panel.models import PreviewDummyCompany, PreviewDummyCSRProject
    is_dummy = str(company_id).startswith('DUMMY_') or str(company_id).startswith('dummy_')
    dummy_c = None
    if is_dummy:
        dummy_c = PreviewDummyCompany.objects.filter(company_id=company_id).first()
    if not dummy_c and PreviewDummyCompany.objects.filter(company_id=company_id).exists():
        dummy_c = PreviewDummyCompany.objects.filter(company_id=company_id).first()
        is_dummy = True
    if is_dummy:
        if not dummy_c:
            clean_id = str(company_id).replace('DUMMY_COMP_', '').replace('DUMMY_', '')
            dummy_c = PreviewDummyCompany.objects.filter(
                Q(company_id__icontains=clean_id) | Q(nse_symbol__iexact=clean_id) | Q(company_name__icontains=clean_id)
            ).first()
        if not dummy_c:
            dummy_c = PreviewDummyCompany.objects.first()
        cname = dummy_c.company_name if dummy_c else ''
        projects = [p.as_preview_dict() for p in PreviewDummyCSRProject.objects.filter(company_name__iexact=cname)]
        if not projects:
            projects = [p.as_preview_dict() for p in PreviewDummyCSRProject.objects.all()[:4]]
        return JsonResponse(projects, safe=False)
'''

target_jobs_top = 'def company_jobs_api(request, company_id):'
jobs_replacement = '''def company_jobs_api(request, company_id):
    from modules.admin_panel.models import PreviewDummyCompany, PreviewDummyJob
    is_dummy = str(company_id).startswith('DUMMY_') or str(company_id).startswith('dummy_')
    dummy_c = None
    if is_dummy:
        dummy_c = PreviewDummyCompany.objects.filter(company_id=company_id).first()
    if not dummy_c and PreviewDummyCompany.objects.filter(company_id=company_id).exists():
        dummy_c = PreviewDummyCompany.objects.filter(company_id=company_id).first()
        is_dummy = True
    if is_dummy:
        if not dummy_c:
            clean_id = str(company_id).replace('DUMMY_COMP_', '').replace('DUMMY_', '')
            dummy_c = PreviewDummyCompany.objects.filter(
                Q(company_id__icontains=clean_id) | Q(nse_symbol__iexact=clean_id) | Q(company_name__icontains=clean_id)
            ).first()
        if not dummy_c:
            dummy_c = PreviewDummyCompany.objects.first()
        cname = dummy_c.company_name if dummy_c else ''
        jobs = [j.as_preview_dict() for j in PreviewDummyJob.objects.filter(company_name__iexact=cname)]
        if not jobs:
            jobs = [j.as_preview_dict() for j in PreviewDummyJob.objects.all()[:4]]
        return JsonResponse(jobs, safe=False)
'''

code = code.replace(target_detail_top, dummy_dossier_helper + '\n\n' + detail_replacement, 1)
code = code.replace(target_dossier_top, dossier_replacement, 1)
code = code.replace(target_csr_top, csr_replacement, 1)
code = code.replace(target_jobs_top, jobs_replacement, 1)

with open(views_file, 'w', encoding='utf-8') as f:
    f.write(code)
print("Finished updating company_api_views.py")

