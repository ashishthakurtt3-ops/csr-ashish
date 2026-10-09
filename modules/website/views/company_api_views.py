from django.http import JsonResponse, Http404
from django.db.models import Q
from modules.admin_panel.models import (
    Company, CSRProject, Job, NGOCollaboration, Contact,
    OpportunityScore, CSROpportunity, Prospect
)
from modules.website.utils.pagination import paginate_queryset

VERIFIED_CONTACT_STATUSES = {'VERIFIED', 'HTTP_VERIFIED', 'MANUAL_VERIFIED'}


def _normalize_company_dict(d):
    cid = d.get('company_id')
    sym = d.get('nse_symbol')
    cname = d.get('company_name', '')
    if cid == 'COMP_TOP200_025' or sym == 'ETERNAL' or 'eternal' in str(cname).lower():
        d['company_name'] = 'Zomato Limited'
        d['nse_symbol'] = 'ZOMATO'
        d['website_url'] = 'https://www.zomato.com/'
        d['careers_url'] = 'https://www.zomato.com/careers'
        d['csr_portal_url'] = 'https://www.feedingindia.org/'
        d['sector'] = 'CONSUMER TECH'
        d['headquarters'] = 'Gurugram, Haryana'
    elif cid == 'COMP_TOP200_058' or sym == 'LTIM':
        d['company_name'] = 'LTIMindtree Limited'
        d['website_url'] = 'https://www.ltimindtree.com/'
        d['careers_url'] = 'https://www.ltimindtree.com/careers/'
    elif cid == 'COMP_TOP200_012' or sym == 'ADANIPOWER':
        if not d.get('careers_url') or 'not-found' in str(d.get('careers_url')):
            d['careers_url'] = 'https://www.adanipower.com/careers'
    return d


def serialize_company_list_item(c: Company):
    # Strictly verified & published counts
    verified_jobs_qs = c.jobs.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'], status='ACTIVE')
    verified_jobs_count = verified_jobs_qs.count()
    published_csr_qs = c.csr_projects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
    published_csr_count = published_csr_qs.count()

    primary_project = published_csr_qs.order_by('-confidence').first()
    primary_job = verified_jobs_qs.order_by('-last_checked_date').first()
    primary_ngo = c.ngo_collaborations.first()
    score_obj = getattr(c, 'score_record', None)
    open_opps = c.open_opportunities.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED'], status='OPEN').count()

    # 5-State Job Status Rule (PART 12)
    if c.crawl_status == 'IN_PROGRESS':
        job_status_label = 'Checking live career source...'
        job_status_state = 'CRAWL_IN_PROGRESS'
        job_status_badge = 'badge-amber'
    elif c.crawl_status == 'FAILED':
        job_status_label = 'Unable to verify current jobs'
        job_status_state = 'CRAWL_FAILED'
        job_status_badge = 'badge-red'
    elif c.crawl_status == 'CRAWLED':
        if verified_jobs_count > 0:
            job_status_label = f'{verified_jobs_count} Current Verified Jobs'
            job_status_state = 'VERIFIED_JOBS'
            job_status_badge = 'badge-cyan'
        elif c.careers_url or c.jobs_page_url or c.ats_url:
            job_status_label = '0 current verified jobs'
            job_status_state = 'VERIFIED_ZERO'
            job_status_badge = 'badge-slate'
        else:
            job_status_label = 'Career source could not be verified'
            job_status_state = 'ATS_DISCOVERY_FAILED'
            job_status_badge = 'badge-amber'
    elif not c.careers_url and not c.jobs_page_url and not c.ats_url:
        job_status_label = 'Career source could not be verified'
        job_status_state = 'ATS_DISCOVERY_FAILED'
        job_status_badge = 'badge-amber'
    else:
        job_status_label = 'Jobs not yet verified'
        job_status_state = 'NOT_CRAWLED'
        job_status_badge = 'badge-slate'

    # CSR Status
    if published_csr_count > 0:
        csr_status_label = f'{published_csr_count} Verified CSR Projects'
        csr_status_state = 'VERIFIED'
        csr_status_badge = 'badge-emerald'
    elif c.csr_portal_url or c.sustainability_url:
        csr_status_label = 'Official CSR Portal Identified'
        csr_status_state = 'PORTAL_IDENTIFIED'
        csr_status_badge = 'badge-teal'
    else:
        csr_status_label = 'CSR not yet verified'
        csr_status_state = 'NOT_VERIFIED'
        csr_status_badge = 'badge-slate'

    d = {
        'company_id': c.company_id,
        'company_name': c.company_name,
        'legal_name': c.legal_name,
        'isin': c.isin,
        'nse_symbol': c.nse_symbol,
        'bse_scrip_code': c.bse_scrip_code,
        'listed_on_nse': c.listed_on_nse,
        'listed_on_bse': c.listed_on_bse,
        'listing_status': c.listing_status,
        'website_url': c.website_url,
        'sector': c.sector,
        'headquarters': c.headquarters,
        'cin': c.cin,
        'last_crawled': c.last_crawled,
        'crawl_status': c.crawl_status,
        'data_confidence': c.data_confidence,
        'careers_url': c.careers_url,
        'csr_portal_url': c.csr_portal_url,
        'link_quality': c.link_quality,
        'link_verified_at': c.link_verified_at,
        'last_verified_display': c.link_verified_at or c.last_crawled or 'Pending verification',
        'primary_csr_url': primary_project.source_url if primary_project else None,
        'primary_csr_name': primary_project.project_name if primary_project else None,
        'primary_csr_budget': primary_project.budget if primary_project else None,
        'primary_job_url': primary_job.application_url if primary_job else None,
        'primary_ngo_url': primary_ngo.source_url if primary_ngo else None,
        'opportunity_score': score_obj.score if score_obj else 0.0,
        'open_opportunities_count': open_opps,
        'job_count': verified_jobs_count,
        'current_verified_jobs': verified_jobs_count,
        'job_status_label': job_status_label,
        'job_status_state': job_status_state,
        'job_status_badge': job_status_badge,
        'csr_count': published_csr_count,
        'csr_status_label': csr_status_label,
        'csr_status_state': csr_status_state,
        'csr_status_badge': csr_status_badge,
    }
    return _normalize_company_dict(d)



def serialize_contact(ct: Contact):
    is_verified = (ct.verification_status or '') in VERIFIED_CONTACT_STATUSES
    return {
        'contact_id': ct.contact_id,
        'company_id': ct.company_id,
        'name': ct.name if is_verified else None,
        'designation': ct.designation if is_verified else None,
        'department': ct.department if is_verified else None,
        'email': ct.email if is_verified else None,
        'phone': ct.phone if is_verified else None,
        'source_url': ct.source_url,
        'confidence': ct.confidence,
        'last_verified_date': ct.last_verified_date,
        'link_status': ct.link_status,
        'link_verified_at': ct.link_verified_at,
        'verification_status': ct.verification_status,
        'fingerprint': ct.fingerprint,
        'contact_note': (
            None if is_verified else
            'No publicly verified CSR contact on record yet. '
            'Use the company’s official CSR page (link in this dossier) to find the current contact.'
        )
    }


def companies_list_api(request):
    q = request.GET.get('q', '').strip()
    sector = request.GET.get('sector', '').strip()
    state = request.GET.get('state', '').strip()
    status = request.GET.get('status', '').strip()
    opp_only = request.GET.get('opp_only', '').lower() in ('true', '1')
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    limit = int(request.GET.get('limit', 200))

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
    if status and status != 'all':
        qs = qs.filter(crawl_status=status)
    if opp_only:
        qs = qs.filter(open_opportunities__status='OPEN').distinct()

    # Order by opportunity score descending, then name
    qs = qs.order_by('-score_record__score', 'company_name')

    data = paginate_queryset(
        queryset=qs,
        serialize_func=serialize_company_list_item,
        page=page,
        page_size=page_size,
        fallback_limit=limit
    )
    return JsonResponse(data, safe=False)


def company_detail_api(request, company_id):
    try:
        c = Company.objects.get(company_id=company_id)
    except Company.DoesNotExist:
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
        'evidence_status': score_obj.evidence_status if score_obj else 'Pending scrape',
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
    Answers WHO, WHY, and HOW for the company with strict source verification.
    """
    from modules.website.views.job_api_views import serialize_job_item
    try:
        c = Company.objects.get(company_id=company_id)
    except Company.DoesNotExist:
        return JsonResponse({'detail': 'Company not found'}, status=404)

    projects = list(c.csr_projects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).order_by('-confidence').values())
    jobs = [serialize_job_item(j) for j in c.jobs.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'], status='ACTIVE').order_by('-last_checked_date')]
    stale_jobs = [serialize_job_item(j) for j in c.jobs.filter(status='EXPIRED').order_by('-last_checked_date')]
    partners = list(c.ngo_collaborations.all().values())
    contacts = [serialize_contact(ct) for ct in c.contacts.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])]
    score_obj = getattr(c, 'score_record', None)
    opps = list(c.open_opportunities.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED'], status='OPEN').order_by('-opp_id').values())
    prospect_obj = getattr(c, 'prospect_entry', None)

    cname = c.company_name
    sector = c.sector
    hq = c.headquarters
    symbol = c.nse_symbol

    cats = list(dict.fromkeys([cat.strip() for p in projects for cat in (p.get('category') or '').split(';') if cat.strip()]))
    states = list(dict.fromkeys([st.strip() for p in projects for st in (p.get('state') or '').split(';') if st.strip()]))
    budget_sum = projects[0].get('budget') if projects else None

    who_parts = [f"{cname}"]
    if symbol:
        who_parts.append(f"({symbol})")
    who_parts.append("is an enterprise corporation")
    if hq:
        who_parts.append(f"headquartered in {hq}")
    if sector:
        who_parts.append(f"in the {sector} sector")
    if projects:
        who_parts.append("with publicly documented social-investment activity on its official website.")
    else:
        who_parts.append(". No source-verified CSR project records are available for this company yet.")
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
            f"{partner_count} recorded NGO collaboration(s) from the company’s official web pages."
        )
    else:
        why_parts.append(
            "No source-verified CSR project or NGO collaboration records are available yet."
        )
    if budget_sum and projects:
        why_parts.append(f"Latest publicly stated budget figure on record: {budget_sum}.")
    why = " ".join(why_parts)

    csr_link = c.csr_portal_url or c.careers_url or c.website_url
    opp_lead = opps[0] if opps else None
    verified_contacts = [ct for ct in contacts if ct.get('email')]

    if verified_contacts:
        how = f"Contact the verified CSR contact listed in this dossier, or submit a concept note via the company’s official page: {csr_link}."
    elif csr_link:
        how = f"No verified CSR email is on record yet. Open the company’s official CSR page ({csr_link}) and use the contact/partnership details published there." + (f" An open call ({opp_lead['title']}) is currently listed." if opp_lead else "")
    else:
        how = "No verified contact or CSR page link is on record yet. Search the company’s official website for a CSR or Sustainability section before reaching out."

    comp_dict = _normalize_company_dict(serialize_company_list_item(c))

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
        'prospect_info': prospect_dict
    })


def company_csr_api(request, company_id):
    projects = list(CSRProject.objects.filter(
        company_id=company_id,
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
    ).order_by('-confidence').values())
    return JsonResponse(projects, safe=False)


def company_jobs_api(request, company_id):
    from modules.website.views.job_api_views import serialize_job_item
    include_stale = request.GET.get('include_stale', '').lower() in ('true', '1')
    qs = Job.objects.select_related('company').filter(company_id=company_id)
    if not include_stale:
        qs = qs.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'], status='ACTIVE')
    jobs = [serialize_job_item(j) for j in qs.order_by('-last_checked_date')]
    return JsonResponse(jobs, safe=False)


def company_partners_api(request, company_id):
    partners = list(NGOCollaboration.objects.filter(company_id=company_id).values())
    return JsonResponse(partners, safe=False)


def company_contacts_api(request, company_id):
    contacts = [serialize_contact(ct) for ct in Contact.objects.filter(company_id=company_id)]
    return JsonResponse(contacts, safe=False)


def recommendations_api(request):
    q = request.GET.get('q', '').strip()
    sector = request.GET.get('sector', '').strip()
    state = request.GET.get('state', '').strip()
    min_score = float(request.GET.get('min_score', 0.0))
    page = request.GET.get('page')
    page_size = request.GET.get('page_size', 12)
    limit = int(request.GET.get('limit', 200))

    qs = Company.objects.filter(score_record__score__gte=min_score).select_related('score_record').prefetch_related(
        'csr_projects', 'jobs', 'ngo_collaborations', 'open_opportunities'
    )
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

    qs = qs.order_by('-score_record__score', 'company_name')

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
    return JsonResponse(data, safe=False)
