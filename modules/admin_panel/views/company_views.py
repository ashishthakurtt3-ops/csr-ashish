from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from modules.admin_panel.models import Company, CSRProject, Job, Contact, OpportunityScore


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
    projects = company.csr_projects.all()[:15]
    jobs = company.jobs.all()[:15]
    contacts = company.contacts.all()[:10]
    score = getattr(company, 'score_record', None)

    return render(request, 'admin/companies/detail.html', {
        'company': company,
        'projects': projects,
        'jobs': jobs,
        'contacts': contacts,
        'score': score
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
