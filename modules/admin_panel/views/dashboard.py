from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from modules.admin_panel.models import (
    Company, Job, CSROpportunity, CSRProject, User,
    Document, Subscription, AuditTrail, PageRecord
)


@login_required
def admin_dashboard_view(request):
    total_companies = Company.objects.count()
    verified_websites = Company.objects.filter(website_url__isnull=False).count()
    total_jobs = Job.objects.count()
    active_jobs = Job.objects.filter(status='ACTIVE').count()
    csr_projects_count = CSRProject.objects.count()
    open_opps_count = CSROpportunity.objects.filter(status='OPEN').count()
    users_count = User.objects.count()
    pending_docs = Document.objects.filter(status='PENDING').count()
    total_subscriptions = Subscription.objects.count()
    total_pages_crawled = PageRecord.objects.count()

    recent_audits = AuditTrail.objects.order_by('-audit_id')[:10]
    recent_companies = Company.objects.order_by('-company_id')[:6]
    recent_jobs = Job.objects.order_by('-job_row_id')[:6]

    context = {
        'total_companies': total_companies,
        'verified_websites': verified_websites,
        'total_jobs': total_jobs,
        'active_jobs': active_jobs,
        'csr_projects_count': csr_projects_count,
        'open_opps_count': open_opps_count,
        'users_count': users_count,
        'pending_docs': pending_docs,
        'total_subscriptions': total_subscriptions,
        'total_pages_crawled': total_pages_crawled,
        'recent_audits': recent_audits,
        'recent_companies': recent_companies,
        'recent_jobs': recent_jobs,
    }
    return render(request, 'admin/dashboard.html', context)
