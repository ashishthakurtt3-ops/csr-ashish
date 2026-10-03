from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from modules.admin_panel.models import Job, Company


@login_required
def job_list_view(request):
    q = request.GET.get('q', '').strip()
    work_mode = request.GET.get('work_mode', '').strip()
    link_status = request.GET.get('link_status', '').strip()
    page_num = request.GET.get('page', 1)

    qs = Job.objects.select_related('company').all().order_by('-last_checked_date', '-job_row_id')
    if q:
        qs = qs.filter(
            Q(job_title__icontains=q) |
            Q(company__company_name__icontains=q) |
            Q(department__icontains=q) |
            Q(skills__icontains=q) |
            Q(location__icontains=q)
        )
    if work_mode and work_mode != 'all':
        qs = qs.filter(work_mode=work_mode)
    if link_status and link_status != 'all':
        qs = qs.filter(link_status=link_status)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/jobs/list.html', {
        'page_obj': page_obj,
        'q': q,
        'selected_mode': work_mode,
        'selected_link_status': link_status,
        'total_count': paginator.count
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
        job.save()
        messages.success(request, f"Job '{job.job_title}' updated successfully.")
        return redirect('admin_jobs:list')

    return render(request, 'admin/jobs/form.html', {'job': job})
