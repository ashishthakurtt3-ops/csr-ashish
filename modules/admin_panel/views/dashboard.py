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


from modules.admin_panel.snapshot_service import (
    get_current_stats_snapshot, get_current_job_summary_snapshot, build_snapshots
)
from modules.admin_panel.models.snapshot import AuditRun


@login_required
def admin_dashboard_view(request):
    stats_data, snapshot_is_stale, audit_run_id, data_as_of = get_current_stats_snapshot()
    job_summary_data, _, _, _ = get_current_job_summary_snapshot()

    total_companies = stats_data.get('total_companies', 0)
    verified_websites = stats_data.get('verified_websites', 0)
    total_jobs = stats_data.get('jobs_tracked', 0)
    active_jobs = total_jobs
    csr_projects_count = stats_data.get('csr_projects', 0)
    open_opps_count = stats_data.get('active_opportunities', 0)
    from django.core.cache import cache

    # Data Quality Reporting & Distributions (Cached for 300s to avoid expensive group-bys on every page view)
    jobs_by_status = cache.get_or_set(
        'admin_dashboard_jobs_by_status',
        lambda: list(Job.objects.values('link_status').annotate(count=Count('job_row_id')).order_by('-count')),
        300
    )
    companies_by_status = cache.get_or_set(
        'admin_dashboard_companies_by_status',
        lambda: list(Company.objects.values('crawl_status').annotate(count=Count('company_id')).order_by('-count')),
        300
    )

    # Work Mode Distribution from Snapshot
    remote_jobs = job_summary_data.get('remote_roles', 0)
    hybrid_jobs = job_summary_data.get('hybrid_roles', 0)
    onsite_jobs = job_summary_data.get('onsite_roles', 0)

    # Top Sectors Breakdown
    top_sectors = cache.get_or_set(
        'admin_dashboard_top_sectors',
        lambda: list(
            Company.objects.exclude(sector__isnull=True).exclude(sector='')
            .values('sector')
            .annotate(count=Count('company_id'))
            .order_by('-count')[:5]
        ),
        300
    )

    # Top CSR Project Categories
    top_causes = cache.get_or_set(
        'admin_dashboard_top_causes',
        lambda: list(
            CSRProject.objects.exclude(category__isnull=True).exclude(category='')
            .values('category')
            .annotate(count=Count('csr_id'))
            .order_by('-count')[:5]
        ),
        300
    )

    # Current Audit Run & Top Hiring Companies from Precomputed CompanyMetrics Snapshot
    from modules.admin_panel.models.snapshot import CompanyMetrics
    current_audit_run = cache.get_or_set(
        'admin_dashboard_current_audit_run',
        lambda: AuditRun.objects.filter(is_current=True).first(),
        60
    )
    top_hiring_companies = []
    if current_audit_run:
        top_metrics = (
            CompanyMetrics.objects.filter(audit_run=current_audit_run, active_jobs_count__gt=0)
            .select_related('company')
            .order_by('-active_jobs_count')[:6]
        )
        for m in top_metrics:
            c = m.company
            c.job_count = m.active_jobs_count
            top_hiring_companies.append(c)
    else:
        top_hiring_companies = list(
            Company.objects.annotate(
                job_count=Count('jobs', filter=Q(jobs__status='ACTIVE', jobs__verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']))
            )
            .filter(job_count__gt=0)
            .order_by('-job_count')[:6]
        )

    # Billing & Subscription Aggregated Metrics (Merged 7 queries into 1)
    now = timezone.now()
    sub_metrics = Subscription.objects.aggregate(
        total_cnt=Count('subscription_id'),
        active_cnt=Count('subscription_id', filter=Q(status='ACTIVE')),
        free_cnt=Count('subscription_id', filter=Q(plan_id='starter', status='ACTIVE')),
        paid_cnt=Count('subscription_id', filter=Q(status='ACTIVE') & ~Q(plan_id='starter')),
        auto_renew_cnt=Count('subscription_id', filter=Q(auto_renew=True, status='ACTIVE')),
        cancelled_cnt=Count('subscription_id', filter=Q(status='CANCELLED')),
        upcoming_cnt=Count('subscription_id', filter=Q(
            auto_renew=True,
            status='ACTIVE',
            current_period_end__gte=now,
            current_period_end__lte=now + timedelta(days=7)
        ))
    )
    total_subscriptions = sub_metrics['total_cnt'] or 0
    active_subscribers = sub_metrics['active_cnt'] or 0
    free_subscribers = sub_metrics['free_cnt'] or 0
    paid_subscribers = sub_metrics['paid_cnt'] or 0
    active_auto_renewals = sub_metrics['auto_renew_cnt'] or 0
    cancelled_subscriptions = sub_metrics['cancelled_cnt'] or 0
    upcoming_renewals_count = sub_metrics['upcoming_cnt'] or 0

    # Payment Metrics Aggregated (Merged 4 queries into 1)
    pay_metrics = Payment.objects.aggregate(
        revenue_paise=Sum('amount_paise', filter=Q(
            payment_status='SUCCESS',
            payment_type__in=['SUBSCRIPTION', 'UPGRADE', 'RENEWAL']
        )),
        successful_cnt=Count('payment_id', filter=Q(payment_status='SUCCESS')),
        failed_cnt=Count('payment_id', filter=Q(payment_status='FAILED')),
        refunded_cnt=Count('payment_id', filter=Q(payment_status='REFUNDED'))
    )
    total_proto_revenue_paise = pay_metrics['revenue_paise'] or 0
    total_proto_revenue_inr = total_proto_revenue_paise / 100.0
    successful_payments = pay_metrics['successful_cnt'] or 0
    failed_payments = pay_metrics['failed_cnt'] or 0
    refunded_payments = pay_metrics['refunded_cnt'] or 0

    users_count = cache.get_or_set('admin_dashboard_users_cnt', lambda: User.objects.count(), 120)
    pending_docs = cache.get_or_set('admin_dashboard_pending_docs_cnt', lambda: Document.objects.filter(status='PENDING').count(), 60)
    total_pages_crawled = cache.get_or_set('admin_dashboard_pages_cnt', lambda: PageRecord.objects.count(), 300)
    total_wallet_balance_paise = cache.get_or_set('admin_dashboard_wallet_paise', lambda: Wallet.objects.aggregate(s=Sum('balance_paise'))['s'] or 0, 120)
    total_wallet_balance_inr = total_wallet_balance_paise / 100.0

    recent_audits = list(AuditTrail.objects.order_by('-audit_id')[:8])
    recent_companies = list(Company.objects.order_by('-company_id')[:6])
    recent_jobs = list(Job.objects.select_related('company').filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).exclude(job_id__startswith='REQ').order_by('-job_row_id')[:6])
    recent_opps = list(CSROpportunity.objects.select_related('company').order_by('-opp_id')[:5])
    recent_payments = list(Payment.objects.select_related('user').order_by('-created_at')[:5])

    audit_history = cache.get_or_set(
        'admin_dashboard_audit_history',
        lambda: list(AuditRun.objects.order_by('-started_at')[:10]),
        60
    )

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
        # Snapshot & Audit Governance
        'data_as_of': data_as_of,
        'snapshot_is_stale': snapshot_is_stale,
        'audit_run_id': audit_run_id,
        'current_audit_run': current_audit_run,
        'audit_history': audit_history,
    }
    return render(request, 'admin/dashboard.html', context)


@login_required
def run_audit_now_view(request):
    """Triggers an audit snapshot build immediately or in background."""
    from django.http import JsonResponse
    import threading
    
    notes = request.POST.get('notes', 'Triggered from Admin Dashboard Console')
    triggered_by = f"ADMIN:{request.user.username}"

    def _worker():
        try:
            build_snapshots(triggered_by=triggered_by, notes=notes)
        except Exception as e:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

    return JsonResponse({
        'status': 'TRIGGERED',
        'message': 'Audit run started in background. Refresh in a few seconds to view the new snapshot.'
    })


@login_required
def audit_status_api(request):
    """Returns status of current and recent audit runs."""
    from django.http import JsonResponse
    current_run = AuditRun.objects.filter(is_current=True).first()
    recent_runs = list(AuditRun.objects.order_by('-started_at').values(
        'id', 'status', 'started_at', 'finished_at', 'triggered_by', 'job_count', 'is_current', 'validation_report'
    )[:10])

    return JsonResponse({
        'current_run_id': current_run.id if current_run else None,
        'current_status': current_run.status if current_run else None,
        'runs': recent_runs
    })
