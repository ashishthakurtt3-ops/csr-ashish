from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from modules.admin_panel.models import (
    Company, CSRProject, Job, Contact, OpportunityScore,
    CSROpportunity, PageRecord, CompanyCrawlSummary, AuditTrail
)


@login_required
def company_list_view(request):
    q = request.GET.get('q', '').strip()
    sector = request.GET.get('sector', '').strip()
    crawl_status = request.GET.get('status', '').strip()
    page_num = request.GET.get('page', 1)

    qs = Company.objects.all().order_by('company_name')
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
    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/companies/list.html', {
        'page_obj': page_obj,
        'q': q,
        'selected_sector': sector,
        'selected_status': crawl_status,
        'all_sectors': [s for s in all_sectors if s],
        'total_count': paginator.count
    })


@login_required
def company_detail_view(request, company_id):
    company = get_object_or_404(Company, company_id=company_id)
    
    # Jobs with optional search & filtering, paginated without artificial limit
    job_q = request.GET.get('job_q', '').strip()
    job_dept = request.GET.get('job_dept', '').strip()
    job_mode = request.GET.get('job_mode', '').strip()
    job_page_num = request.GET.get('job_page', 1)

    show_historical = request.GET.get('historical', '').lower() in ('true', '1')
    if show_historical:
        jobs_qs = company.jobs.all()
    else:
        jobs_qs = company.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])

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

    total_company_jobs = company.jobs.exclude(verification_status='LEGACY_UNVERIFIED').count()
    active_jobs_count = company.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()

    # All CSR Projects (published & verified)
    projects = list(company.csr_projects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).order_by('-confidence', '-csr_id'))

    # All CSR Opportunities / Grants / RFPs (published & verified)
    opportunities = list(company.open_opportunities.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED']).order_by('-confidence', '-opp_id'))

    # All Verified Corporate Contacts
    contacts = list(company.contacts.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED']).order_by('-confidence', '-contact_id'))

    # Opportunity score
    score = getattr(company, 'score_record', None)

    # Crawl summaries
    crawl_summaries = list(company.crawl_summaries.all().order_by('-crawl_started_at')[:10])
    latest_crawl_summary = crawl_summaries[0] if crawl_summaries else None

    # Telemetry crawled pages
    crawled_pages = list(company.crawled_pages.all().order_by('-page_id')[:30])

    # Company audit trails
    audit_trails = list(AuditTrail.objects.filter(
        Q(record_id=str(company.company_id)) | Q(record_type='Company', record_id=company.company_id)
    ).order_by('-audit_id')[:15])

    # Unique departments for job facet filter
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
        company.website_url = request.POST.get('website_url', company.website_url).strip()
        company.careers_url = request.POST.get('careers_url', company.careers_url).strip()
        company.csr_portal_url = request.POST.get('csr_portal_url', company.csr_portal_url).strip()
        company.sector = request.POST.get('sector', company.sector).strip()
        company.headquarters = request.POST.get('headquarters', company.headquarters).strip()
        company.crawl_status = request.POST.get('crawl_status', company.crawl_status).strip()
        company.save()
        messages.success(request, f"Company '{company.company_name}' updated successfully.")
        return redirect('admin_companies:detail', company_id=company.company_id)

    return render(request, 'admin/companies/edit.html', {'company': company})
