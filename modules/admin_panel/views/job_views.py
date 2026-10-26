from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from modules.admin_panel.models import Job, Company


@login_required
def job_list_view(request):
    """All Jobs: Enterprise management table view."""
    q = request.GET.get('q', '').strip()
    work_mode = request.GET.get('work_mode', '').strip()
    link_status = request.GET.get('link_status', '').strip()
    company_id = request.GET.get('company_id', '').strip()
    department = request.GET.get('department', '').strip()
    sort = request.GET.get('sort', 'recent')
    page_num = request.GET.get('page', 1)

    show_historical = request.GET.get('historical', '').lower() in ('true', '1')
    if show_historical:
        qs = Job.objects.select_related('company').all()
    else:
        qs = Job.objects.select_related('company').filter(
            status='ACTIVE',
            verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
        ).exclude(job_id__startswith='REQ')
    if q:
        qs = qs.filter(
            Q(job_title__icontains=q) |
            Q(company__company_name__icontains=q) |
            Q(department__icontains=q) |
            Q(skills__icontains=q) |
            Q(location__icontains=q)
        )
    if company_id:
        qs = qs.filter(company_id=company_id)
    if work_mode and work_mode != 'all':
        qs = qs.filter(work_mode=work_mode)
    if department and department != 'all':
        qs = qs.filter(department__icontains=department)
    if link_status and link_status != 'all':
        qs = qs.filter(link_status=link_status)
    link_quality = request.GET.get('link_quality', '').strip()
    if link_quality and link_quality != 'all':
        qs = qs.filter(link_quality=link_quality)

    if sort == 'title':
        qs = qs.order_by('job_title')
    elif sort == 'company':
        qs = qs.order_by('company__company_name', 'job_title')
    else:
        qs = qs.order_by('-last_checked_date', '-job_row_id')

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(page_num)

    all_departments = Job.objects.exclude(department__isnull=True).exclude(department='').values_list('department', flat=True).distinct()[:25]

    return render(request, 'admin/jobs/list.html', {
        'page_obj': page_obj,
        'q': q,
        'selected_mode': work_mode,
        'selected_link_status': link_status,
        'selected_link_quality': link_quality,
        'selected_dept': department,
        'selected_sort': sort,
        'all_departments': sorted(list(set(all_departments))),
        'total_count': paginator.count
    })


@login_required
def job_find_view(request):
    """Find Jobs: Dedicated job-discovery and search experience with cards."""
    q = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    work_mode = request.GET.get('work_mode', '').strip()
    experience = request.GET.get('experience', '').strip()
    department = request.GET.get('department', '').strip()
    sort = request.GET.get('sort', 'newest')
    page_num = request.GET.get('page', 1)

    qs = Job.objects.select_related('company').filter(
        status='ACTIVE',
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
    ).exclude(job_id__startswith='REQ')

    if q:
        qs = qs.filter(
            Q(job_title__icontains=q) |
            Q(company__company_name__icontains=q) |
            Q(department__icontains=q) |
            Q(skills__icontains=q) |
            Q(location__icontains=q) |
            Q(job_description__icontains=q)
        )
    if location and location != 'all':
        qs = qs.filter(Q(location__icontains=location) | Q(state__icontains=location))
    if work_mode and work_mode != 'all':
        qs = qs.filter(work_mode=work_mode)
    if department and department != 'all':
        qs = qs.filter(department__icontains=department)
    if experience and experience != 'all':
        exp_l = experience.lower()
        if exp_l == 'entry':
            qs = qs.filter(
                Q(experience__icontains='0-') | Q(experience__icontains='1-') |
                Q(experience__icontains='2-') | Q(job_title__icontains='Associate') |
                Q(job_title__icontains='Junior') | Q(job_title__icontains='Trainee')
            )
        elif exp_l == 'mid':
            qs = qs.filter(
                Q(experience__icontains='3-') | Q(experience__icontains='4-') |
                Q(experience__icontains='5-')
            )
        elif exp_l == 'senior':
            qs = qs.filter(
                Q(experience__icontains='6-') | Q(experience__icontains='7-') |
                Q(experience__icontains='8-') | Q(experience__icontains='9-')
            )
        elif exp_l == 'lead':
            qs = qs.filter(
                Q(experience__icontains='10-') | Q(job_title__icontains='Lead') |
                Q(job_title__icontains='Head') | Q(job_title__icontains='Director')
            )

    if sort == 'title':
        qs = qs.order_by('job_title')
    elif sort == 'company':
        qs = qs.order_by('company__company_name')
    elif sort == 'oldest':
        qs = qs.order_by('job_row_id')
    else:  # newest / default
        qs = qs.order_by('-last_checked_date', '-job_row_id')

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(page_num)

    # Aggregations for filter facets
    top_locations = ['Mumbai', 'Bengaluru', 'Delhi NCR', 'Pune', 'Hyderabad', 'Chennai', 'Kolkata', 'Ahmedabad']
    top_departments = ['Software Engineering', 'IT & Digital', 'Finance & Accounts', 'Operations', 'CSR & Sustainability', 'Human Resources', 'Sales & Marketing', 'Engineering']

    return render(request, 'admin/jobs/find.html', {
        'page_obj': page_obj,
        'q': q,
        'location': location,
        'work_mode': work_mode,
        'experience': experience,
        'department': department,
        'sort': sort,
        'top_locations': top_locations,
        'top_departments': top_departments,
        'total_count': paginator.count
    })


@login_required
def job_company_directory_view(request):
    """Company Jobs: Directory to search/select a company to see its job intelligence."""
    q = request.GET.get('q', '').strip()
    sector = request.GET.get('sector', '').strip()
    raw_status = request.GET.get('status', None)
    if raw_status is not None:
        status_filter = raw_status.strip().lower()
    else:
        # Default to actively hiring corporations so all cards across all pages show verified jobs
        status_filter = 'all' if q else 'hiring'

    page_num = request.GET.get('page', 1)

    qs = Company.objects.annotate(
        job_count=Count('jobs', filter=Q(jobs__status='ACTIVE', jobs__verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])),
        total_discovered_jobs=Count('jobs', filter=~Q(jobs__verification_status='LEGACY_UNVERIFIED'))
    ).all().order_by('-job_count', 'company_name')

    if q:
        qs = qs.filter(
            Q(company_name__icontains=q) |
            Q(nse_symbol__icontains=q) |
            Q(sector__icontains=q) |
            Q(headquarters__icontains=q)
        )
    if sector and sector != 'all':
        qs = qs.filter(sector=sector)

    if status_filter == 'hiring':
        qs = qs.filter(job_count__gt=0)
    elif status_filter == 'zero':
        qs = qs.filter(job_count=0)
    elif status_filter == 'failed':
        qs = qs.filter(crawl_status__in=['FAILED', 'BLOCKED', 'REDIRECT_BLOCKED'])

    paginator = Paginator(qs, 16)
    page_obj = paginator.get_page(page_num)

    all_sectors = Company.objects.values_list('sector', flat=True).distinct().order_by('sector')

    # Aggregates for filter pills and telemetry
    hiring_companies_count = Company.objects.annotate(
        vjobs=Count('jobs', filter=Q(jobs__status='ACTIVE', jobs__verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']) & ~Q(jobs__job_id__startswith='REQ'))
    ).filter(vjobs__gt=0).count()

    total_verified_jobs = Job.objects.filter(
        status='ACTIVE',
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
    ).exclude(job_id__startswith='REQ').count()

    zero_verified_count = Company.objects.annotate(
        vjobs=Count('jobs', filter=Q(jobs__status='ACTIVE', jobs__verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']) & ~Q(jobs__job_id__startswith='REQ'))
    ).filter(vjobs=0).count()

    failed_crawl_count = Company.objects.filter(
        crawl_status__in=['FAILED', 'BLOCKED', 'REDIRECT_BLOCKED']
    ).count()

    return render(request, 'admin/jobs/company_directory.html', {
        'page_obj': page_obj,
        'q': q,
        'selected_sector': sector,
        'selected_status': status_filter,
        'all_sectors': [s for s in all_sectors if s],
        'total_count': paginator.count,
        'hiring_companies_count': hiring_companies_count,
        'total_verified_jobs': total_verified_jobs,
        'zero_verified_count': zero_verified_count,
        'failed_crawl_count': failed_crawl_count,
        'total_directory_companies': Company.objects.count(),
    })


@login_required
def job_company_detail_view(request, company_id):
    """Company Job Dashboard: Overview of the company + complete jobs inventory."""
    company = get_object_or_404(Company, company_id=company_id)
    q = request.GET.get('q', '').strip()
    location = request.GET.get('location', '').strip()
    work_mode = request.GET.get('work_mode', '').strip()
    experience = request.GET.get('experience', '').strip()
    department = request.GET.get('department', '').strip()
    sort = request.GET.get('sort', 'newest')
    page_num = request.GET.get('page', 1)
    show_all = request.GET.get('show_all', '').lower() in ('true', '1')

    if show_all:
        qs = company.jobs.all()
    else:
        qs = company.jobs.filter(
            status='ACTIVE',
            verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
        ).exclude(job_id__startswith='REQ')

    if q:
        qs = qs.filter(
            Q(job_title__icontains=q) |
            Q(department__icontains=q) |
            Q(skills__icontains=q) |
            Q(location__icontains=q) |
            Q(job_description__icontains=q)
        )
    if location and location != 'all':
        qs = qs.filter(Q(location__icontains=location) | Q(state__icontains=location))
    if work_mode and work_mode != 'all':
        qs = qs.filter(work_mode=work_mode)
    if department and department != 'all':
        qs = qs.filter(department__icontains=department)
    if experience and experience != 'all':
        exp_l = experience.lower()
        if exp_l == 'entry':
            qs = qs.filter(
                Q(experience__icontains='0-') | Q(experience__icontains='1-') |
                Q(experience__icontains='2-') | Q(job_title__icontains='Associate') |
                Q(job_title__icontains='Junior')
            )
        elif exp_l == 'mid':
            qs = qs.filter(
                Q(experience__icontains='3-') | Q(experience__icontains='4-') |
                Q(experience__icontains='5-')
            )
        elif exp_l == 'senior':
            qs = qs.filter(
                Q(experience__icontains='6-') | Q(experience__icontains='7-') |
                Q(experience__icontains='8-') | Q(experience__icontains='9-')
            )
        elif exp_l == 'lead':
            qs = qs.filter(
                Q(experience__icontains='10-') | Q(job_title__icontains='Lead') |
                Q(job_title__icontains='Head')
            )

    if sort == 'title':
        qs = qs.order_by('job_title')
    elif sort == 'oldest':
        qs = qs.order_by('job_row_id')
    else:  # newest
        qs = qs.order_by('-last_checked_date', '-job_row_id')

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_num)

    verified_jobs_count = company.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
    total_company_jobs = verified_jobs_count
    legacy_jobs_count = company.jobs.filter(verification_status='LEGACY_UNVERIFIED').count()
    quarantined_count = company.jobs.filter(verification_status__in=['QUARANTINED', 'REJECTED', 'STALE']).count()
    verified_jobs_qs = company.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
    depts = verified_jobs_qs.exclude(department__isnull=True).exclude(department='').values_list('department', flat=True).distinct()
    locations = verified_jobs_qs.exclude(location__isnull=True).exclude(location='').values_list('location', flat=True).distinct()

    return render(request, 'admin/jobs/company_detail.html', {
        'company': company,
        'page_obj': page_obj,
        'q': q,
        'location': location,
        'work_mode': work_mode,
        'experience': experience,
        'department': department,
        'sort': sort,
        'show_all': show_all,
        'total_company_jobs': total_company_jobs,
        'verified_jobs_count': verified_jobs_count,
        'legacy_jobs_count': legacy_jobs_count,
        'quarantined_count': quarantined_count,
        'filtered_count': paginator.count,
        'company_depts': sorted(list(set(depts)))[:15],
        'company_locations': sorted(list(set(locations)))[:15],
    })


@login_required
def job_detail_view(request, job_row_id):
    """Job Details Page: Comprehensive enterprise view of a single job opening."""
    job = get_object_or_404(Job.objects.select_related('company'), job_row_id=job_row_id)
    related_jobs = Job.objects.filter(
        company=job.company,
        status='ACTIVE',
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
    ).exclude(job_id__startswith='REQ').exclude(job_row_id=job.job_row_id)[:5]
    if not related_jobs.exists() and job.department:
        related_jobs = Job.objects.filter(
            department=job.department,
            status='ACTIVE',
            verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
        ).exclude(job_id__startswith='REQ').exclude(job_row_id=job.job_row_id)[:5]

    company_verified_jobs_count = job.company.jobs.filter(
        status='ACTIVE',
        verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
    ).exclude(job_id__startswith='REQ').count()

    return render(request, 'admin/jobs/detail.html', {
        'job': job,
        'company': job.company,
        'related_jobs': related_jobs,
        'company_verified_jobs_count': company_verified_jobs_count,
    })


@login_required
def job_edit_view(request, job_row_id):
    job = get_object_or_404(Job, job_row_id=job_row_id)
    if request.method == 'POST':
        job.job_title = request.POST.get('job_title', job.job_title).strip()
        job.department = request.POST.get('department', job.department).strip()
        job.work_mode = request.POST.get('work_mode', job.work_mode).strip()
        job.location = request.POST.get('location', job.location).strip()
        job.application_url = request.POST.get('application_url', job.application_url).strip()
        job.status = ('CLOSED' if request.POST.get('status', job.status) in ('CLOSED', 'INACTIVE', 'EXPIRED') else 'INACTIVE')  # [CLOSE_ONLY_JOB_EDIT_GUARD].strip()
        job.skills = request.POST.get('skills', job.skills).strip()
        job.experience = request.POST.get('experience', job.experience).strip()
        job.salary = request.POST.get('salary', job.salary).strip()
        job.job_description = request.POST.get('job_description', job.job_description).strip()
        job.save()
        messages.success(request, f"Job '{job.job_title}' updated successfully.")
        return redirect('admin_jobs:detail', job_row_id=job.job_row_id)

    return render(request, 'admin/jobs/form.html', {'job': job})


@login_required
def job_link_quality_dashboard_view(request):
    """Link Quality Dashboard: Direct %, Fallback %, Strategy Breakdown, Top Failing Companies."""
    total_active = Job.objects.filter(status='ACTIVE').count()
    direct_count = Job.objects.filter(status='ACTIVE', link_quality='DIRECT').count()
    fallback_count = Job.objects.filter(status='ACTIVE', link_quality='LISTING_FALLBACK').count()
    unverified_count = Job.objects.filter(status='ACTIVE', link_quality='UNVERIFIED').count()
    direct_pct = round((direct_count / total_active) * 100, 2) if total_active > 0 else 0.0

    # Top strategies
    strategies = Company.objects.exclude(extraction_strategy__isnull=True).exclude(extraction_strategy='').values('extraction_strategy').annotate(count=Count('company_id')).order_by('-count')

    # Top failing companies (companies with 0 direct jobs or low success rate)
    failing_companies = Company.objects.filter(
        Q(last_strategy_success_rate__lt=50.0) | Q(last_strategy_success_rate__isnull=True)
    ).order_by('last_strategy_success_rate', 'company_id')[:25]

    # Common fallback / error reasons
    failing_reasons = Job.objects.filter(link_quality='LISTING_FALLBACK').values('link_check_note').annotate(count=Count('job_row_id')).order_by('-count')[:10]

    return render(request, 'admin/jobs/link_quality_dashboard.html', {
        'total_active': total_active,
        'direct_count': direct_count,
        'fallback_count': fallback_count,
        'unverified_count': unverified_count,
        'direct_pct': direct_pct,
        'strategies': strategies,
        'failing_companies': failing_companies,
        'failing_reasons': failing_reasons,
    })


@login_required
def recrawl_company_admin_view(request, company_id):
    """Re-crawl a specific company on-demand with Strategy Cascade."""
    company = get_object_or_404(Company, company_id=company_id)
    from modules.crawler_engine.crawler import sync_single_company_live
    summary = sync_single_company_live(company)
    company.refresh_from_db()
    messages.success(request, f"Successfully re-crawled {company.company_name}. Strategy: {company.extraction_strategy}, Success: {company.last_strategy_success_rate}% direct.")
    return redirect('admin_jobs:company_jobs', company_id=company.company_id)

