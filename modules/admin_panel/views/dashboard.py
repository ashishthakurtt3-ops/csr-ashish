from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from modules.admin_panel.models import (
    Company, Job, CSROpportunity, CSRProject, User,
    Document, Subscription, AuditTrail, PageRecord,
    Payment, Wallet
)


@login_required
def admin_dashboard_view(request):
    total_companies = Company.objects.count()
    verified_websites = Company.objects.filter(website_url__isnull=False).count()
    total_jobs = Job.objects.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).exclude(job_id__startswith='REQ').count()
    active_jobs = total_jobs
    csr_projects_count = CSRProject.objects.count()
    open_opps_count = CSROpportunity.objects.filter(status='OPEN').count()
    users_count = User.objects.count()
    pending_docs = Document.objects.filter(status='PENDING').count()
    total_subscriptions = Subscription.objects.count()
    total_pages_crawled = PageRecord.objects.count()

    # Data Quality Reporting
    jobs_by_status = list(Job.objects.values('link_status').annotate(count=Count('job_row_id')).order_by('-count'))
    companies_by_status = list(Company.objects.values('crawl_status').annotate(count=Count('company_id')).order_by('-count'))

    # Work Mode Distribution (Active Published Genuine Jobs)
    active_jobs_qs = Job.objects.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).exclude(job_id__startswith='REQ')
    remote_jobs = active_jobs_qs.filter(work_mode='Remote').count()
    hybrid_jobs = active_jobs_qs.filter(work_mode='Hybrid').count()
    onsite_jobs = active_jobs_qs.filter(work_mode='On-site').count()

    # Top Sectors Breakdown
    top_sectors = list(
        Company.objects.exclude(sector__isnull=True).exclude(sector='')
        .values('sector')
        .annotate(count=Count('company_id'))
        .order_by('-count')[:5]
    )

    # Top CSR Project Categories
    top_causes = list(
        CSRProject.objects.exclude(category__isnull=True).exclude(category='')
        .values('category')
        .annotate(count=Count('csr_id'))
        .order_by('-count')[:5]
    )

    # Top Hiring Companies (Authentic verified active jobs only)
    top_hiring_companies = list(
        Company.objects.annotate(
            job_count=Count('jobs', filter=Q(jobs__status='ACTIVE', jobs__verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']))
        )
        .filter(job_count__gt=0)
        .order_by('-job_count')[:6]
    )

    # Billing & Subscription Prototype Metrics
    active_subscribers = Subscription.objects.filter(status='ACTIVE').count()
    free_subscribers = Subscription.objects.filter(plan_id='starter', status='ACTIVE').count()
    paid_subscribers = Subscription.objects.filter(status='ACTIVE').exclude(plan_id='starter').count()
    active_auto_renewals = Subscription.objects.filter(auto_renew=True, status='ACTIVE').count()
    cancelled_subscriptions = Subscription.objects.filter(status='CANCELLED').count()

    total_proto_revenue_paise = Payment.objects.filter(
        payment_status='SUCCESS',
        payment_type__in=['SUBSCRIPTION', 'UPGRADE', 'RENEWAL']
    ).aggregate(s=Sum('amount_paise'))['s'] or 0
    total_proto_revenue_inr = total_proto_revenue_paise / 100.0

    successful_payments = Payment.objects.filter(payment_status='SUCCESS').count()
    failed_payments = Payment.objects.filter(payment_status='FAILED').count()
    refunded_payments = Payment.objects.filter(payment_status='REFUNDED').count()

    total_wallet_balance_paise = Wallet.objects.aggregate(s=Sum('balance_paise'))['s'] or 0
    total_wallet_balance_inr = total_wallet_balance_paise / 100.0

    now = timezone.now()
    upcoming_renewals_count = Subscription.objects.filter(
        auto_renew=True,
        status='ACTIVE',
        current_period_end__gte=now,
        current_period_end__lte=now + timedelta(days=7)
    ).count()

    recent_audits = AuditTrail.objects.order_by('-audit_id')[:8]
    recent_companies = Company.objects.order_by('-company_id')[:6]
    recent_jobs = Job.objects.select_related('company').filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).exclude(job_id__startswith='REQ').order_by('-job_row_id')[:6]
    recent_opps = CSROpportunity.objects.select_related('company').order_by('-opp_id')[:5]
    recent_payments = Payment.objects.select_related('user').order_by('-created_at')[:6]

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
        'jobs_by_status': jobs_by_status,
        'companies_by_status': companies_by_status,
        # Distribution
        'remote_jobs': remote_jobs,
        'hybrid_jobs': hybrid_jobs,
        'onsite_jobs': onsite_jobs,
        'top_sectors': top_sectors,
        'top_causes': top_causes,
        'top_hiring_companies': top_hiring_companies,
        'recent_opps': recent_opps,
        # Billing Metrics
        'active_subscribers': active_subscribers,
        'free_subscribers': free_subscribers,
        'paid_subscribers': paid_subscribers,
        'active_auto_renewals': active_auto_renewals,
        'cancelled_subscriptions': cancelled_subscriptions,
        'total_proto_revenue_inr': total_proto_revenue_inr,
        'successful_payments': successful_payments,
        'failed_payments': failed_payments,
        'refunded_payments': refunded_payments,
        'total_wallet_balance_inr': total_wallet_balance_inr,
        'upcoming_renewals_count': upcoming_renewals_count,
        'recent_payments': recent_payments,
        'recent_audits': recent_audits,
        'recent_companies': recent_companies,
        'recent_jobs': recent_jobs,
    }
    return render(request, 'admin/dashboard.html', context)
