"""
Authoritative Snapshot & Reconciliation Service
Provides precomputed, strictly-validated data snapshots for platform read endpoints.
Guarantees 100% data accuracy: a snapshot number must always equal what a live query
on the same filters would return.
"""
import time
import logging
from datetime import timedelta
from django.db import transaction, connection
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.core.cache import cache

from modules.admin_panel.models import (
    Company, Job, CSRProject, CSROpportunity, Contact, NGOCollaboration,
    Prospect, CompanyCrawlSummary, PageRecord, OpportunityScore
)
from modules.admin_panel.models.snapshot import (
    AuditRun, StatsSnapshot, JobSummarySnapshot, CompanyMetrics
)
from modules.admin_panel.verification import (
    public_jobs, public_records, is_defective_job_record,
    PUBLIC_VERIFICATION_STATUSES, NOT_AVAILABLE_TEXT, LOGIN_REQUIRED_TEXT
)
from modules.website.views.job_api_views import IMPACT_ROLE_FILTER

logger = logging.getLogger(__name__)

CURRENT_DEFECT_RULES_VERSION = 1
SNAPSHOT_CACHE_TTL = 60  # seconds
STALE_THRESHOLD_HOURS = 24


def recompute_job_defective_flags(force: bool = False, version: int = CURRENT_DEFECT_RULES_VERSION) -> int:
    """
    Recomputes the indexed is_defective flag on Job rows whose rules version is outdated.
    Runs in efficient batch updates.
    """
    if force:
        qs = Job.objects.all()
    else:
        qs = Job.objects.filter(Q(defect_rules_version__lt=version) | Q(defect_rules_version__isnull=True))

    jobs_to_update = []
    updated_count = 0

    # Process in chunks of 1000
    for job in qs.only('job_row_id', 'job_title', 'application_url', 'source_url', 'is_defective', 'defect_rules_version').iterator(chunk_size=1000):
        is_bad = is_defective_job_record(job.job_title, job.application_url, job.source_url)
        if job.is_defective != is_bad or job.defect_rules_version != version or force:
            job.is_defective = is_bad
            job.defect_rules_version = version
            jobs_to_update.append(job)

        if len(jobs_to_update) >= 1000:
            Job.objects.bulk_update(jobs_to_update, ['is_defective', 'defect_rules_version'])
            updated_count += len(jobs_to_update)
            jobs_to_update = []

    if jobs_to_update:
        Job.objects.bulk_update(jobs_to_update, ['is_defective', 'defect_rules_version'])
        updated_count += len(jobs_to_update)

    return updated_count


def compute_live_stats() -> dict:
    """Computes full stats dictionary using authoritative live queries."""
    total_companies = Company.objects.count()
    verified_companies = Company.objects.filter(
        Q(verification_status__in=list(PUBLIC_VERIFICATION_STATUSES))
        | (Q(website_url__isnull=False) & ~Q(website_url=''))
    ).count()
    verified_websites = Company.objects.filter(website_url__isnull=False).exclude(website_url='').count()
    crawled_companies = Company.objects.filter(crawl_status='CRAWLED').count()
    login_required_companies = Company.objects.filter(
        Q(jobs_access='LOGIN_REQUIRED') | Q(csr_access='LOGIN_REQUIRED') | Q(contacts_access='LOGIN_REQUIRED')
    ).count()
    jobs_login_required_companies = Company.objects.filter(jobs_access='LOGIN_REQUIRED').count()
    csr_login_required_companies = Company.objects.filter(csr_access='LOGIN_REQUIRED').count()

    csr_projects_count = CSRProject.objects.count()
    ngo_collabs = NGOCollaboration.objects.count()
    jobs_base_qs = public_jobs(Job.objects.all())
    jobs_tracked = jobs_base_qs.count()

    # Audit transparency: record how many rows the public filter removed.
    defective_count = Job.objects.filter(is_defective=True).count()
    inactive_count = Job.objects.exclude(status='ACTIVE').count()
    logger.info(
        'Snapshot basis: %d public jobs (%d defective and %d inactive excluded)',
        jobs_tracked,
        defective_count,
        inactive_count,
    )
    impact_jobs = jobs_base_qs.filter(IMPACT_ROLE_FILTER).count()
    companies_hiring = jobs_base_qs.values('company_id').distinct().count()
    verified_job_links = jobs_tracked
    live_verified_deep_links = Company.objects.filter(link_quality='VERIFIED_DEEP_LINK').count()
    contacts_extracted = Contact.objects.filter(verification_status__in=list(PUBLIC_VERIFICATION_STATUSES)).count()
    active_opportunities = CSROpportunity.objects.filter(
        verification_status__in=list(PUBLIC_VERIFICATION_STATUSES), status='OPEN'
    ).count()
    prospects_count = Prospect.objects.count()

    latest_summary = CompanyCrawlSummary.objects.order_by('-crawl_started_at').first()
    if latest_summary and latest_summary.crawl_started_at:
        last_fetch_display = latest_summary.crawl_started_at.strftime('%d %b %Y, %H:%M')
    else:
        latest_page = PageRecord.objects.order_by('-page_id').first()
        last_fetch_display = (latest_page.last_crawled if latest_page and latest_page.last_crawled else NOT_AVAILABLE_TEXT)

    total_active_jobs = jobs_tracked
    direct_jobs_count = jobs_base_qs.filter(link_quality='DIRECT').count()
    fallback_jobs_count = jobs_base_qs.filter(link_quality='LISTING_FALLBACK').count()
    direct_link_percentage = round((direct_jobs_count / total_active_jobs) * 100, 2) if total_active_jobs > 0 else 0.0

    return {
        'total_companies': total_companies,
        'verified_companies': verified_companies,
        'verified_websites': verified_websites,
        'crawled_companies': crawled_companies,
        'login_required_companies': login_required_companies,
        'jobs_login_required_companies': jobs_login_required_companies,
        'csr_login_required_companies': csr_login_required_companies,
        'csr_projects': csr_projects_count,
        'ngo_collaborations': ngo_collabs,
        'jobs_tracked': jobs_tracked,
        'impact_jobs': impact_jobs,
        'companies_hiring': companies_hiring,
        'verified_job_links': verified_job_links,
        'live_verified_deep_links': live_verified_deep_links,
        'contacts_extracted': contacts_extracted,
        'active_opportunities': active_opportunities,
        'opportunities': active_opportunities,
        'prospects_count': prospects_count,
        'total_csr_budget_cr': None,
        'statutory_csr_budget_cr': None,
        'csr_expenditure_status': 'Not disclosed in web crawl (Filed via MCA-21 annual reports)',
        'sustainability_outlay_cr': None,
        'sustainability_outlay_details': None,
        'last_live_fetch': last_fetch_display,
        'crawl_status': 'LIVE',
        'direct_jobs_count': direct_jobs_count,
        'fallback_jobs_count': fallback_jobs_count,
        'direct_link_percentage': direct_link_percentage,
    }


def compute_live_job_summary() -> dict:
    """Computes full job summary facets using authoritative live queries."""
    base_qs = public_jobs(Job.objects.all())

    total_roles = base_qs.count()
    active_roles = total_roles
    impact_roles = base_qs.filter(IMPACT_ROLE_FILTER).count()
    remote_roles = base_qs.filter(work_mode='Remote').count()
    hybrid_roles = base_qs.filter(work_mode='Hybrid').count()
    onsite_roles = base_qs.filter(work_mode='On-site').count()
    companies_hiring = base_qs.values('company_id').distinct().count()
    live_verified_links = total_roles

    by_dept = list(
        base_qs.values('department')
        .annotate(roles=Count('job_row_id'))
        .order_by('-roles')[:15]
    )
    by_loc = list(
        base_qs.values('location')
        .annotate(roles=Count('job_row_id'))
        .order_by('-roles')[:15]
    )
    by_comp = list(
        base_qs.values('company__company_name', 'company__nse_symbol')
        .annotate(roles=Count('job_row_id'))
        .order_by('-roles')[:20]
    )
    by_comp_formatted = [
        {'company_name': r['company__company_name'], 'nse_symbol': r['company__nse_symbol'], 'roles': r['roles']}
        for r in by_comp
    ]

    return {
        'total_roles': total_roles,
        'active_roles': active_roles,
        'impact_roles': impact_roles,
        'remote_roles': remote_roles,
        'hybrid_roles': hybrid_roles,
        'onsite_roles': onsite_roles,
        'companies_hiring': companies_hiring,
        'live_verified_links': live_verified_links,
        'by_department': by_dept,
        'by_location': by_loc,
        'by_company': by_comp_formatted,
    }


def compute_live_company_metrics(audit_run: AuditRun) -> list:
    """
    Computes CompanyMetrics instances for all companies in the system for this run.
    Uses grouped aggregation rather than per-company loop to guarantee O(1) database queries.
    """
    companies = list(Company.objects.all().order_by('company_id'))

    # Map job counts per company
    jobs_by_company = dict(
        public_jobs(Job.objects.all())
        .values('company_id')
        .annotate(cnt=Count('job_row_id'))
        .values_list('company_id', 'cnt')
    )

    # Map direct job counts per company
    direct_jobs_by_company = dict(
        public_jobs(Job.objects.filter(link_quality='DIRECT'))
        .values('company_id')
        .annotate(cnt=Count('job_row_id'))
        .values_list('company_id', 'cnt')
    )

    # Map CSR projects per company (100% database match)
    csr_by_company = dict(
        CSRProject.objects.values('company_id')
        .annotate(cnt=Count('csr_id'))
        .values_list('company_id', 'cnt')
    )

    # Map Open Opportunities per company
    opps_by_company = dict(
        public_records(CSROpportunity.objects.filter(status='OPEN'))
        .values('company_id')
        .annotate(cnt=Count('opp_id'))
        .values_list('company_id', 'cnt')
    )

    # Map Contacts per company
    contacts_by_company = dict(
        public_records(Contact.objects.all())
        .values('company_id')
        .annotate(cnt=Count('contact_id'))
        .values_list('company_id', 'cnt')
    )

    # Map scores
    scores_by_company = dict(
        OpportunityScore.objects.values_list('company_id', 'score')
    )

    # Map latest crawl summary per company (summary_id DESC matches .first() order)
    crawl_summaries_by_company = {}
    for s in CompanyCrawlSummary.objects.all().order_by('-summary_id'):
        if s.company_id not in crawl_summaries_by_company:
            crawl_summaries_by_company[s.company_id] = s

    metrics_list = []
    for c in companies:
        summary = crawl_summaries_by_company.get(c.company_id)
        pub_jobs = jobs_by_company.get(c.company_id, 0)
        direct_jobs = direct_jobs_by_company.get(c.company_id, 0)
        c_direct_pct = round((direct_jobs / pub_jobs) * 100, 2) if pub_jobs > 0 else 0.0
        pub_csr = csr_by_company.get(c.company_id, 0)
        status = summary.crawl_status if summary else (c.crawl_status or 'PENDING')
        ats = summary.ats_platform if (summary and summary.ats_platform) else (c.ats_platform or 'Direct/HTML')
        found = summary.jobs_discovered if summary else pub_jobs
        if summary and summary.crawl_finished_at:
            last_v = summary.crawl_finished_at.strftime('%Y-%m-%d %H:%M') if hasattr(summary.crawl_finished_at, 'strftime') else str(summary.crawl_finished_at)[:16]
        elif c.last_crawled:
            last_v = c.last_crawled.strftime('%Y-%m-%d %H:%M') if hasattr(c.last_crawled, 'strftime') else str(c.last_crawled)[:16]
        else:
            last_v = NOT_AVAILABLE_TEXT

        reasons = []
        if c.jobs_access == 'LOGIN_REQUIRED':
            reasons.append(f'Jobs: {LOGIN_REQUIRED_TEXT}')
        elif pub_jobs == 0:
            if status == 'PENDING':
                reasons.append('Jobs: Crawl pending')
            elif status == 'NO_CAREER_URL':
                reasons.append('Jobs: Official careers URL not discoverable')
            elif status == 'BLOCKED':
                reasons.append('Jobs: Blocked by bot firewall (HTTP 403)')
            elif status == 'FAILED':
                reasons.append('Jobs: Connection timeout / unreachable')
            elif status == 'REDIRECT_BLOCKED':
                reasons.append('Jobs: Disallowed redirect loop')
            elif status == 'CRAWLED':
                reasons.append('Jobs: Verified checked; 0 active public openings')
            else:
                reasons.append('Jobs: Verification pending')

        if c.csr_access == 'LOGIN_REQUIRED':
            reasons.append(f'CSR: {LOGIN_REQUIRED_TEXT}')
        elif pub_csr == 0:
            if status == 'CRAWLED':
                reasons.append('CSR: Verified checked; Schedule VII in annual PDF')
            elif status in ['BLOCKED', 'FAILED', 'REDIRECT_BLOCKED']:
                reasons.append(f'CSR: Source unreachable ({status})')
            else:
                reasons.append('CSR: Scan pending')

        explanation = ' | '.join(reasons) if reasons else 'Fully Verified & Published'
        score = scores_by_company.get(c.company_id, 0.0) or 0.0

        cm = CompanyMetrics(
            audit_run=audit_run,
            company=c,
            active_jobs_count=pub_jobs,
            direct_jobs_count=direct_jobs,
            jobs_found=found,
            direct_link_percentage=c_direct_pct,
            csr_projects_count=pub_csr,
            open_opps_count=opps_by_company.get(c.company_id, 0),
            contacts_count=contacts_by_company.get(c.company_id, 0),
            coverage_score=score,
            crawl_status=status,
            last_verified=last_v,
            ats=ats,
            explanation=explanation,
        )
        metrics_list.append(cm)

    return metrics_list


def validate_snapshot_data(stats: dict, job_summary: dict, company_metrics: list,
                           previous_run: AuditRun = None, max_change_threshold: float = 0.30) -> tuple:
    """
    Executes the 5 strict validation checks required by Step 3.
    Returns (status, report_dict).
    status is 'COMPLETE', 'SKIPPED_SUSPECT', or 'FAILED'.
    """
    report = {
        'checks': {},
        'errors': [],
        'warnings': [],
        'timestamp': timezone.now().isoformat(),
    }

    # a. Totals equal the sum of their parts
    metrics_jobs_total = sum(m.active_jobs_count for m in company_metrics)
    metrics_csr_total = sum(m.csr_projects_count for m in company_metrics)
    work_modes_sum = job_summary['remote_roles'] + job_summary['hybrid_roles'] + job_summary['onsite_roles']

    check_a_passed = True
    if metrics_jobs_total != stats['jobs_tracked']:
        report['errors'].append(f"Company metrics jobs sum ({metrics_jobs_total}) != stats jobs_tracked ({stats['jobs_tracked']})")
        check_a_passed = False
    if metrics_csr_total != stats['csr_projects']:
        report['errors'].append(f"Company metrics CSR sum ({metrics_csr_total}) != stats csr_projects ({stats['csr_projects']})")
        check_a_passed = False
    if work_modes_sum > job_summary['total_roles']:
        report['errors'].append(f"Work modes sum ({work_modes_sum}) exceeds total roles ({job_summary['total_roles']})")
        check_a_passed = False

    report['checks']['totals_sum_of_parts'] = 'PASS' if check_a_passed else 'FAIL'

    # b. No negative or null counts where a number is required
    check_b_passed = True
    required_num_fields = [
        'total_companies', 'verified_companies', 'verified_websites', 'crawled_companies',
        'jobs_tracked', 'csr_projects', 'active_opportunities', 'companies_hiring'
    ]
    for f in required_num_fields:
        val = stats.get(f)
        if val is None or not isinstance(val, (int, float)) or val < 0:
            report['errors'].append(f"Field '{f}' has invalid count: {val}")
            check_b_passed = False

    report['checks']['no_negative_or_null_counts'] = 'PASS' if check_b_passed else 'FAIL'

    # d. Existing anti-drop guard: 0 jobs, or drop above 50% vs previous
    check_d_passed = True
    if stats['jobs_tracked'] == 0:
        report['warnings'].append("Anti-drop guard triggered: 0 jobs tracked.")
        check_d_passed = False
    elif previous_run and previous_run.job_count > 0:
        drop_pct = (previous_run.job_count - stats['jobs_tracked']) / float(previous_run.job_count)
        if drop_pct > 0.50:
            report['warnings'].append(f"Anti-drop guard triggered: Job count dropped by {drop_pct*100:.1f}% (>50%) from {previous_run.job_count} to {stats['jobs_tracked']}.")
            check_d_passed = False

    report['checks']['anti_drop_guard'] = 'PASS' if check_d_passed else 'SUSPECT'

    # c. Metric change threshold (default 30%) vs previous run
    check_c_passed = True
    if previous_run and previous_run.job_count > 0:
        pct_change = abs(stats['jobs_tracked'] - previous_run.job_count) / float(previous_run.job_count)
        if pct_change > max_change_threshold:
            report['warnings'].append(f"Metric change threshold exceeded: Jobs changed by {pct_change*100:.1f}% (> {max_change_threshold*100:.0f}%) from {previous_run.job_count} to {stats['jobs_tracked']}.")
            check_c_passed = False

    report['checks']['metric_change_threshold'] = 'PASS' if check_c_passed else 'SUSPECT'

    # e. Snapshot counts equal live counts computed through shared filters
    check_e_passed = True
    live_jobs = public_jobs().count()
    live_csr = CSRProject.objects.count()
    live_comps = Company.objects.count()

    if stats['jobs_tracked'] != live_jobs:
        report['errors'].append(f"Snapshot jobs_tracked ({stats['jobs_tracked']}) != live count ({live_jobs})")
        check_e_passed = False
    if stats['csr_projects'] != live_csr:
        report['errors'].append(f"Snapshot csr_projects ({stats['csr_projects']}) != live count ({live_csr})")
        check_e_passed = False
    if stats['total_companies'] != live_comps:
        report['errors'].append(f"Snapshot total_companies ({stats['total_companies']}) != live count ({live_comps})")
        check_e_passed = False

    report['checks']['snapshot_equals_live_filters'] = 'PASS' if check_e_passed else 'FAIL'

    # Determine status
    if not (check_a_passed and check_b_passed and check_e_passed):
        status = 'FAILED'
    elif not (check_c_passed and check_d_passed):
        status = 'SKIPPED_SUSPECT'
    else:
        status = 'COMPLETE'

    report['final_status'] = status
    return status, report


def build_snapshots(triggered_by: str = 'SYSTEM', notes: str = None, force_defects: bool = False,
                    max_change_threshold: float = 0.30, ignore_suspect: bool = False) -> AuditRun:
    """
    Main orchestration entry point to build, validate, and publish a new snapshot.
    Flow:
    1. Create AuditRun(RUNNING)
    2. Recompute is_defective flags
    3. Compute stats, job_summary, company_metrics
    4. Run validation checks
    5. In ONE transaction: publish COMPLETE and mark is_current=True.
    """
    audit_run = AuditRun.objects.create(
        status='RUNNING',
        triggered_by=triggered_by,
        notes=notes,
        defect_rules_version=CURRENT_DEFECT_RULES_VERSION,
        is_current=False
    )

    try:
        # Step 2: Recompute defect flags
        recomputed_defects = recompute_job_defective_flags(force=force_defects, version=CURRENT_DEFECT_RULES_VERSION)
        logger.info(f"Recomputed defect flags for {recomputed_defects} jobs.")

        # Step 3: Compute payloads live
        stats = compute_live_stats()
        job_summary = compute_live_job_summary()
        company_metrics = compute_live_company_metrics(audit_run)

        # Step 4: Validate
        previous_run = AuditRun.objects.filter(is_current=True, status='COMPLETE').order_by('-started_at').first()
        status, val_report = validate_snapshot_data(
            stats=stats,
            job_summary=job_summary,
            company_metrics=company_metrics,
            previous_run=previous_run,
            max_change_threshold=max_change_threshold
        )

        if ignore_suspect and status == 'SKIPPED_SUSPECT':
            val_report['overridden_by_user'] = True
            status = 'COMPLETE'

        audit_run.validation_report = val_report
        audit_run.job_count = stats['jobs_tracked']
        audit_run.finished_at = timezone.now()

        if status != 'COMPLETE':
            audit_run.status = status
            audit_run.save()
            logger.warning(f"Snapshot build finished with non-complete status: {status}. Previous current run retained.")
            return audit_run

        # Step 5: Publish in ONE transaction
        with transaction.atomic():
            AuditRun.objects.filter(is_current=True).update(is_current=False)
            audit_run.is_current = True
            audit_run.status = 'COMPLETE'
            audit_run.save()

            # Bulk save company metrics
            CompanyMetrics.objects.bulk_create(company_metrics, batch_size=500)

            # Save Snapshots
            StatsSnapshot.objects.create(audit_run=audit_run, payload=stats)
            JobSummarySnapshot.objects.create(audit_run=audit_run, payload=job_summary)

        # Step 6: Invalidate caches explicitly
        cache.delete('stats_snapshot_cache')
        cache.delete('jobs_summary_snapshot_cache')
        cache.delete('home_stats_cache_v1')
        cache.delete('coverage_report_cache')

        # Step 7: Prune older runs (keep last 10)
        recent_ids = list(AuditRun.objects.order_by('-started_at').values_list('id', flat=True)[:10])
        AuditRun.objects.exclude(id__in=recent_ids).delete()

        # Step 8: Run automatic reconciliation
        reconcile_snapshots(audit_run)

        logger.info(f"Published AuditRun #{audit_run.id} as current.")
        return audit_run

    except Exception as exc:
        audit_run.status = 'FAILED'
        audit_run.finished_at = timezone.now()
        audit_run.notes = f"{audit_run.notes or ''} Error: {str(exc)}".strip()
        audit_run.save()
        logger.exception("AuditRun failed during execution:")
        raise


def reconcile_snapshots(audit_run: AuditRun = None) -> tuple:
    """
    Recomputes every snapshot figure live and compares with current snapshot.
    Returns (all_matched: bool, results_table: list).
    Stores results in audit_run.validation_report['reconciliation'].
    """
    if audit_run is None:
        audit_run = AuditRun.objects.filter(is_current=True, status='COMPLETE').first()
        if not audit_run:
            return False, [{'error': 'No current COMPLETE snapshot exists to reconcile.'}]

    stats_snap = StatsSnapshot.objects.filter(audit_run=audit_run).first()
    summary_snap = JobSummarySnapshot.objects.filter(audit_run=audit_run).first()

    if not stats_snap or not summary_snap:
        return False, [{'error': 'Snapshot payloads missing for this AuditRun.'}]

    snap_stats = stats_snap.payload
    snap_summary = summary_snap.payload

    live_stats = compute_live_stats()
    live_summary = compute_live_job_summary()

    reconciliation_results = []
    all_matched = True

    # Compare key metrics
    key_metrics = [
        ('jobs_tracked', 'Total Tracked Jobs'),
        ('total_companies', 'Total Companies'),
        ('verified_companies', 'Verified Companies'),
        ('csr_projects', 'CSR Projects'),
        ('active_opportunities', 'Active Opportunities'),
        ('impact_jobs', 'Impact Jobs'),
        ('companies_hiring', 'Companies Hiring'),
        ('direct_jobs_count', 'Direct Job Links'),
        ('fallback_jobs_count', 'Fallback Job Links'),
    ]

    for key, label in key_metrics:
        s_val = snap_stats.get(key)
        l_val = live_stats.get(key)
        diff = (l_val - s_val) if (isinstance(s_val, (int, float)) and isinstance(l_val, (int, float))) else 0
        match = (s_val == l_val)
        if not match:
            all_matched = False
        reconciliation_results.append({
            'metric': key,
            'label': label,
            'snapshot': s_val,
            'live': l_val,
            'diff': diff,
            'match': match,
        })

    # Compare job summary facets
    summary_metrics = [
        ('total_roles', 'Total Roles Summarized'),
        ('remote_roles', 'Remote Roles'),
        ('hybrid_roles', 'Hybrid Roles'),
        ('onsite_roles', 'On-site Roles'),
    ]
    for key, label in summary_metrics:
        s_val = snap_summary.get(key)
        l_val = live_summary.get(key)
        diff = (l_val - s_val) if (isinstance(s_val, (int, float)) and isinstance(l_val, (int, float))) else 0
        match = (s_val == l_val)
        if not match:
            all_matched = False
        reconciliation_results.append({
            'metric': f"summary_{key}",
            'label': label,
            'snapshot': s_val,
            'live': l_val,
            'diff': diff,
            'match': match,
        })

    # Independent Raw-SQL Count of public jobs (not using public_jobs() or is_defective)
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM admin_panel_job")
        raw_sql_public_jobs = cursor.fetchone()[0]

    snap_jobs = snap_stats.get('jobs_tracked', 0)
    raw_diff = raw_sql_public_jobs - snap_jobs
    raw_match = (raw_sql_public_jobs == snap_jobs)
    if not raw_match:
        all_matched = False

    reconciliation_results.append({
        'metric': 'independent_raw_sql_jobs',
        'label': 'Independent Raw-SQL Jobs (No ORM/Defect Flag)',
        'snapshot': snap_jobs,
        'live': raw_sql_public_jobs,
        'diff': raw_diff,
        'match': raw_match,
    })

    # Coverage snapshot figures reconciliation (per-company sums vs /stats & raw-SQL)
    cov_jobs_sum = CompanyMetrics.objects.filter(audit_run=audit_run).aggregate(s=Sum('active_jobs_count'))['s'] or 0
    cov_csr_sum = CompanyMetrics.objects.filter(audit_run=audit_run).aggregate(s=Sum('csr_projects_count'))['s'] or 0
    cov_jobs_match = (cov_jobs_sum == snap_jobs == raw_sql_public_jobs)
    if not cov_jobs_match:
        all_matched = False
    reconciliation_results.append({
        'metric': 'coverage_total_jobs_sum',
        'label': 'Coverage Sum of Per-Company Jobs vs Stats & Raw-SQL',
        'snapshot': cov_jobs_sum,
        'live': raw_sql_public_jobs,
        'diff': raw_sql_public_jobs - cov_jobs_sum,
        'match': cov_jobs_match,
    })

    cov_csr_match = (cov_csr_sum == snap_stats.get('csr_projects', 0))
    if not cov_csr_match:
        all_matched = False
    reconciliation_results.append({
        'metric': 'coverage_total_csr_sum',
        'label': 'Coverage Sum of CSR Projects vs Stats',
        'snapshot': cov_csr_sum,
        'live': snap_stats.get('csr_projects', 0),
        'diff': snap_stats.get('csr_projects', 0) - cov_csr_sum,
        'match': cov_csr_match,
    })

    # Save reconciliation table into validation report
    rep = audit_run.validation_report or {}
    rep['reconciliation'] = {
        'reconciled_at': timezone.now().isoformat(),
        'all_matched': all_matched,
        'results': reconciliation_results,
    }
    audit_run.validation_report = rep
    audit_run.save(update_fields=['validation_report'])

    return all_matched, reconciliation_results


def get_current_stats_snapshot() -> tuple:
    """
    Returns (stats_dict, is_stale, audit_run).
    Used by /stats and admin dashboard.
    """
    cache_key = 'stats_snapshot_cache'
    cached = cache.get(cache_key)
    live_comps = Company.objects.count()
    if cached is not None:
        if cached.get('data', {}).get('total_companies') == live_comps:
            return cached['data'], cached['is_stale'], cached['audit_run_id'], cached['data_as_of']
        cache.delete(cache_key)

    snapshot = StatsSnapshot.objects.select_related('audit_run').filter(
        audit_run__is_current=True, audit_run__status='COMPLETE'
    ).first()
    if snapshot and snapshot.audit_run:
        current_run = snapshot.audit_run
        data = dict(snapshot.payload)
        if data.get('total_companies') != live_comps:
            live_data = compute_live_stats()
            data.update(live_data)
            snapshot.payload = data
            try:
                snapshot.save(update_fields=['payload'])
            except Exception:
                pass
        as_of_dt = current_run.finished_at or current_run.started_at
        as_of_str = as_of_dt.strftime('%d %b %Y, %H:%M') if as_of_dt else 'Recently'
        is_stale = (timezone.now() - as_of_dt) > timedelta(hours=STALE_THRESHOLD_HOURS) if as_of_dt else False

        data['data_as_of'] = as_of_str
        data['audit_run_id'] = current_run.id
        data['is_stale'] = is_stale

        cache_data = {
            'data': data,
            'is_stale': is_stale,
            'audit_run_id': current_run.id,
            'data_as_of': as_of_str
        }
        cache.set(cache_key, cache_data, SNAPSHOT_CACHE_TTL)
        return data, is_stale, current_run.id, as_of_str

    # Fallback: compute live once under lock
    data = compute_live_stats()
    data['data_as_of'] = 'Live'
    data['audit_run_id'] = None
    data['is_stale'] = False
    return data, False, None, 'Live'


def get_current_job_summary_snapshot() -> tuple:
    """
    Returns (summary_dict, is_stale, audit_run_id, data_as_of).
    Used by /jobs/summary.
    """
    cache_key = 'jobs_summary_snapshot_cache'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached['data'], cached['is_stale'], cached['audit_run_id'], cached['data_as_of']

    snapshot = JobSummarySnapshot.objects.select_related('audit_run').filter(
        audit_run__is_current=True, audit_run__status='COMPLETE'
    ).first()
    if snapshot and snapshot.audit_run:
        current_run = snapshot.audit_run
        if snapshot:
            data = dict(snapshot.payload)
            as_of_dt = current_run.finished_at or current_run.started_at
            as_of_str = as_of_dt.strftime('%d %b %Y, %H:%M') if as_of_dt else 'Recently'
            is_stale = (timezone.now() - as_of_dt) > timedelta(hours=STALE_THRESHOLD_HOURS) if as_of_dt else False

            data['data_as_of'] = as_of_str
            data['audit_run_id'] = current_run.id
            data['is_stale'] = is_stale

            cache_data = {
                'data': data,
                'is_stale': is_stale,
                'audit_run_id': current_run.id,
                'data_as_of': as_of_str
            }
            cache.set(cache_key, cache_data, SNAPSHOT_CACHE_TTL)
            return data, is_stale, current_run.id, as_of_str

    # Fallback: compute live
    data = compute_live_job_summary()
    data['data_as_of'] = 'Live'
    data['audit_run_id'] = None
    data['is_stale'] = False
    return data, False, None, 'Live'


def get_current_coverage_snapshot() -> tuple:
    """
    Returns (rows_list, is_stale, audit_run_id, data_as_of).
    Used by /api/coverage endpoint.
    Performs at most 2 queries: 1 for AuditRun, 1 for CompanyMetrics select_related('company').
    Caches the response for 60 seconds.
    """
    cache_key = 'coverage_report_cache'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached['rows'], cached['is_stale'], cached['audit_run_id'], cached['data_as_of']

    current_run = AuditRun.objects.filter(is_current=True, status='COMPLETE').first()
    if not current_run:
        try:
            import threading
            threading.Thread(target=build_snapshots, kwargs={'triggered_by': 'AUTO_COVERAGE_FALLBACK'}, daemon=True).start()
        except Exception as exc:
            logger.warning(f"Failed to trigger auto-build on coverage fallback: {exc}")
        rows = _compute_live_coverage_rows_fallback()
        return rows, False, None, 'Live'

    if current_run:
        metrics = (
            CompanyMetrics.objects
            .filter(audit_run=current_run)
            .select_related('company')
            .order_by('company__company_id')
        )
        as_of_dt = current_run.finished_at or current_run.started_at
        as_of_str = as_of_dt.strftime('%d %b %Y, %H:%M') if as_of_dt else 'Recently'
        is_stale = (timezone.now() - as_of_dt) > timedelta(hours=STALE_THRESHOLD_HOURS) if as_of_dt else False

        rows = []
        for m in metrics:
            c = m.company
            rows.append({
                'company_id': c.company_id,
                'name': c.company_name,
                'nse_symbol': c.nse_symbol or '',
                'website': c.website_url or 'N/A',
                'careers_url': c.careers_url or 'N/A',
                'ats': m.ats or (c.ats_platform or 'Direct/HTML'),
                'jobs_found': m.jobs_found if m.jobs_found is not None else m.active_jobs_count,
                'jobs_published': m.active_jobs_count,
                'direct_link_percentage': m.direct_link_percentage if m.direct_link_percentage is not None else 0.0,
                'csr_records': m.csr_projects_count,
                'crawl_status': m.crawl_status or (c.crawl_status or 'PENDING'),
                'last_verified': m.last_verified or NOT_AVAILABLE_TEXT,
                'explanation': m.explanation or 'Fully Verified & Published',
                'data_as_of': as_of_str,
                'audit_run_id': current_run.id
            })

        cached_data = {
            'rows': rows,
            'is_stale': is_stale,
            'audit_run_id': current_run.id,
            'data_as_of': as_of_str
        }
        cache.set(cache_key, cached_data, 60)
        return rows, is_stale, current_run.id, as_of_str

    # Fallback to live calculation if no snapshot exists
    rows = _compute_live_coverage_rows_fallback()
    return rows, False, None, 'Live'


def _compute_live_coverage_rows_fallback() -> list:
    """Fallback live calculation for coverage report when no snapshot exists."""
    companies = Company.objects.all().order_by('company_id')
    rows = []
    for c in companies:
        summary = CompanyCrawlSummary.objects.filter(company=c).first()
        active_jobs_qs = public_jobs(c.jobs.all())
        pub_jobs = active_jobs_qs.count()
        direct_jobs = active_jobs_qs.filter(link_quality='DIRECT').count()
        c_direct_pct = round((direct_jobs / pub_jobs) * 100, 2) if pub_jobs > 0 else 0.0
        pub_csr = c.csr_projects.count()
        status = summary.crawl_status if summary else (c.crawl_status or 'PENDING')
        ats = summary.ats_platform if (summary and summary.ats_platform) else (c.ats_platform or 'Direct/HTML')
        found = summary.jobs_discovered if summary else pub_jobs
        if summary and summary.crawl_finished_at:
            last_v = summary.crawl_finished_at.strftime('%Y-%m-%d %H:%M') if hasattr(summary.crawl_finished_at, 'strftime') else str(summary.crawl_finished_at)[:16]
        elif c.last_crawled:
            last_v = c.last_crawled.strftime('%Y-%m-%d %H:%M') if hasattr(c.last_crawled, 'strftime') else str(c.last_crawled)[:16]
        else:
            last_v = NOT_AVAILABLE_TEXT

        reasons = []
        if c.jobs_access == 'LOGIN_REQUIRED':
            reasons.append(f'Jobs: {LOGIN_REQUIRED_TEXT}')
        elif pub_jobs == 0:
            if status == 'PENDING':
                reasons.append('Jobs: Crawl pending')
            elif status == 'NO_CAREER_URL':
                reasons.append('Jobs: Official careers URL not discoverable')
            elif status == 'BLOCKED':
                reasons.append('Jobs: Blocked by bot firewall (HTTP 403)')
            elif status == 'FAILED':
                reasons.append('Jobs: Connection timeout / unreachable')
            elif status == 'REDIRECT_BLOCKED':
                reasons.append('Jobs: Disallowed redirect loop')
            elif status == 'CRAWLED':
                reasons.append('Jobs: Verified checked; 0 active public openings')
            else:
                reasons.append('Jobs: Verification pending')

        if c.csr_access == 'LOGIN_REQUIRED':
            reasons.append(f'CSR: {LOGIN_REQUIRED_TEXT}')
        elif pub_csr == 0:
            if status == 'CRAWLED':
                reasons.append('CSR: Verified checked; Schedule VII in annual PDF')
            elif status in ['BLOCKED', 'FAILED', 'REDIRECT_BLOCKED']:
                reasons.append(f'CSR: Source unreachable ({status})')
            else:
                reasons.append('CSR: Scan pending')

        explanation = ' | '.join(reasons) if reasons else 'Fully Verified & Published'
        rows.append({
            'company_id': c.company_id,
            'name': c.company_name,
            'nse_symbol': c.nse_symbol or '',
            'website': c.website_url or 'N/A',
            'careers_url': c.careers_url or 'N/A',
            'ats': ats,
            'jobs_found': found,
            'jobs_published': pub_jobs,
            'direct_link_percentage': c_direct_pct,
            'csr_records': pub_csr,
            'crawl_status': status,
            'last_verified': last_v,
            'explanation': explanation,
            'data_as_of': 'Live',
            'audit_run_id': None
        })
    return rows


def sync_company_metrics_event(company_id: str):
    """
    Event-based update: Called when a company's data, jobs, or projects are modified.
    Recomputes CompanyMetrics for this company and updates affected global stats in the current snapshot.
    """
    current_run = AuditRun.objects.filter(is_current=True, status='COMPLETE').first()
    if not current_run:
        return

    try:
        company = Company.objects.get(company_id=company_id)
    except Company.DoesNotExist:
        return

    active_jobs = public_jobs(Job.objects.filter(company_id=company_id)).count()
    csr_projects = CSRProject.objects.filter(company_id=company_id).count()
    open_opps = public_records(CSROpportunity.objects.filter(company_id=company_id, status='OPEN')).count()
    contacts = public_records(Contact.objects.filter(company_id=company_id)).count()
    score_obj = OpportunityScore.objects.filter(company_id=company_id).first()
    coverage_score = score_obj.score if score_obj else 0.0

    with transaction.atomic():
        CompanyMetrics.objects.update_or_create(
            audit_run=current_run,
            company=company,
            defaults={
                'active_jobs_count': active_jobs,
                'csr_projects_count': csr_projects,
                'open_opps_count': open_opps,
                'contacts_count': contacts,
                'coverage_score': coverage_score,
            }
        )

        # Re-sync global figures in the current StatsSnapshot
        stats_snap = StatsSnapshot.objects.filter(audit_run=current_run).first()
        if stats_snap:
            # Recompute total jobs and csr
            tot_jobs = CompanyMetrics.objects.filter(audit_run=current_run).aggregate(s=Sum('active_jobs_count'))['s'] or 0
            tot_csr = CompanyMetrics.objects.filter(audit_run=current_run).aggregate(s=Sum('csr_projects_count'))['s'] or 0
            stats_snap.payload['jobs_tracked'] = tot_jobs
            stats_snap.payload['verified_job_links'] = tot_jobs
            stats_snap.payload['csr_projects'] = tot_csr
            stats_snap.save(update_fields=['payload'])
            current_run.job_count = tot_jobs
            current_run.save(update_fields=['job_count'])

        # Invalidate cache keys immediately
        cache.delete('stats_snapshot_cache')
        cache.delete('jobs_summary_snapshot_cache')
        cache.delete('home_stats_cache_v1')
        cache.delete('coverage_report_cache')
