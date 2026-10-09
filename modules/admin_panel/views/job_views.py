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

    qs = Job.objects.select_related('company').all()
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

    qs = Job.objects.select_related('company').all()

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
    page_num = request.GET.get('page', 1)

    qs = Company.objects.annotate(job_count=Count('jobs')).all().order_by('-job_count', 'company_name')

    if q:
        qs = qs.filter(
            Q(company_name__icontains=q) |
            Q(nse_symbol__icontains=q) |
            Q(sector__icontains=q) |
            Q(headquarters__icontains=q)
        )
    if sector and sector != 'all':
        qs = qs.filter(sector=sector)

    paginator = Paginator(qs, 16)
    page_obj = paginator.get_page(page_num)

    all_sectors = Company.objects.values_list('sector', flat=True).distinct().order_by('sector')

    return render(request, 'admin/jobs/company_directory.html', {
        'page_obj': page_obj,
        'q': q,
        'selected_sector': sector,
        'all_sectors': [s for s in all_sectors if s],
        'total_count': paginator.count
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

    qs = company.jobs.all()

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

    total_company_jobs = company.jobs.count()
    depts = company.jobs.exclude(department__isnull=True).exclude(department='').values_list('department', flat=True).distinct()
    locations = company.jobs.exclude(location__isnull=True).exclude(location='').values_list('location', flat=True).distinct()

    return render(request, 'admin/jobs/company_detail.html', {
        'company': company,
        'page_obj': page_obj,
        'q': q,
        'location': location,
        'work_mode': work_mode,
        'experience': experience,
        'department': department,
        'sort': sort,
        'total_company_jobs': total_company_jobs,
        'filtered_count': paginator.count,
        'company_depts': sorted(list(set(depts)))[:15],
        'company_locations': sorted(list(set(locations)))[:15],
    })


@login_required
def job_detail_view(request, job_row_id):
    """Job Details Page: Comprehensive enterprise view of a single job opening."""
    job = get_object_or_404(Job.objects.select_related('company'), job_row_id=job_row_id)
    related_jobs = Job.objects.filter(company=job.company).exclude(job_row_id=job.job_row_id)[:5]
    if not related_jobs.exists() and job.department:
        related_jobs = Job.objects.filter(department=job.department).exclude(job_row_id=job.job_row_id)[:5]

    return render(request, 'admin/jobs/detail.html', {
        'job': job,
        'company': job.company,
        'related_jobs': related_jobs,
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
        job.status = request.POST.get('status', job.status).strip()
        job.skills = request.POST.get('skills', job.skills).strip()
        job.experience = request.POST.get('experience', job.experience).strip()
        job.salary = request.POST.get('salary', job.salary).strip()
        job.job_description = request.POST.get('job_description', job.job_description).strip()
        job.save()
        messages.success(request, f"Job '{job.job_title}' updated successfully.")
        return redirect('admin_jobs:detail', job_row_id=job.job_row_id)

    return render(request, 'admin/jobs/form.html', {'job': job})
