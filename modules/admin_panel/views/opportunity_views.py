from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from modules.admin_panel.models import CSROpportunity, CSRProject, Company


@login_required
def opportunity_list_view(request):
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', 'OPEN').strip()
    verification = request.GET.get('verification', 'PUBLISHED').strip()
    page_num = request.GET.get('page', 1)

    qs = CSROpportunity.objects.select_related('company').all().order_by('-opp_id')
    if verification and verification != 'all':
        qs = qs.filter(verification_status=verification)
    if status and status != 'all':
        qs = qs.filter(status=status)

    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(category__icontains=q) |
            Q(company__company_name__icontains=q)
        )

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/opportunities/list.html', {
        'page_obj': page_obj,
        'q': q,
        'selected_status': status,
        'selected_verification': verification,
        'total_count': paginator.count
    })


@login_required
def project_list_view(request):
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    state = request.GET.get('state', '').strip()
    verification = request.GET.get('verification', 'PUBLISHED').strip()
    page_num = request.GET.get('page', 1)

    qs = CSRProject.objects.select_related('company').all().order_by('-confidence', '-csr_id')
    if verification and verification != 'all':
        qs = qs.filter(verification_status=verification)

    if q:
        qs = qs.filter(
            Q(project_name__icontains=q) |
            Q(category__icontains=q) |
            Q(company__company_name__icontains=q) |
            Q(state__icontains=q)
        )
    if category and category != 'all':
        qs = qs.filter(category__icontains=category)
    if state and state != 'all':
        qs = qs.filter(state__icontains=state)

    paginator = Paginator(qs, 15)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/opportunities/projects_list.html', {
        'page_obj': page_obj,
        'q': q,
        'selected_category': category,
        'selected_state': state,
        'selected_verification': verification,
        'total_count': paginator.count
    })
