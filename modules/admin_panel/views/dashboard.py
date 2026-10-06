from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
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
    total_jobs = Job.objects.count()
    active_jobs = Job.objects.filter(status='ACTIVE').count()
    csr_projects_count = CSRProject.objects.count()
    open_opps_count = CSROpportunity.objects.filter(status='OPEN').count()
    users_count = User.objects.count()
    pending_docs = Document.objects.filter(status='PENDING').count()
    total_subscriptions = Subscription.objects.count()
    total_pages_crawled = PageRecord.objects.count()

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

    recent_audits = AuditTrail.objects.order_by('-audit_id')[:10]
    recent_companies = Company.objects.order_by('-company_id')[:6]
    recent_jobs = Job.objects.order_by('-job_row_id')[:6]
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

