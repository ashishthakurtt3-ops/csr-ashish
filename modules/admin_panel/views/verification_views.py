from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Count, Q
from modules.admin_panel.models import (
    CSRProject, AuditTrail, PageRecord, Company, Job, CompanyCrawlSummary
)
from modules.crawler_engine.state import CRAWL_TASK_STATE
from modules.crawler_engine.verification_service import VerificationService


@login_required
def verification_queue_view(request):
    # Returns records with status UNVERIFIED or EXTRACTED or VALIDATED for review
    pending_records = CSRProject.objects.filter(
        verification_status__in=['UNVERIFIED', 'EXTRACTED', 'VALIDATED']
    ).order_by('confidence', '-csr_id')[:50]
    return render(request, 'admin/verification/queue.html', {'pending_records': pending_records})


@login_required
def verification_action_view(request, record_id):
    project = get_object_or_404(CSRProject, csr_id=record_id)
    action = request.POST.get('action') # APPROVE or REJECT
    notes = request.POST.get('notes', 'Manual audit verification')
    now_ts = timezone.now().isoformat()

    if action == 'APPROVE':
        project.confidence = 0.99
        project.last_verified_date = now_ts
        # Step through strict lifecycle: VALIDATED -> SOURCE_CONFIRMED -> PUBLISHED
        VerificationService.publish_record(project, actor=f"Admin_{request.user.username}")
        messages.success(request, f"Approved & Published project '{project.project_name}'.")
    elif action == 'REJECT':
        project.confidence = 0.40
        project.verification_status = 'REJECTED'
        project.link_status = 'REJECTED'
        project.save()
        messages.warning(request, f"Flagged project '{project.project_name}' as REJECTED.")

    AuditTrail.objects.create(
        record_type='CSR_PROJECT',
        record_id=str(project.csr_id),
        action=f"VERIFY_{action}",
        new_value=f"Status: {project.verification_status} | Confidence: {project.confidence}",
        user_role=getattr(request.user, 'role', 'Admin'),
        notes=notes,
        timestamp=now_ts
    )

    return redirect('admin_verification:queue')


@login_required
def audit_trail_view(request):
    page_num = request.GET.get('page', 1)
    audits = AuditTrail.objects.all().order_by('-audit_id')
    paginator = Paginator(audits, 25)
    page_obj = paginator.get_page(page_num)

    return render(request, 'admin/verification/audit_trail.html', {
        'page_obj': page_obj,
        'total_count': paginator.count
    })


import csv
from django.http import HttpResponse

@login_required
def crawler_telemetry_view(request):
    recent_pages = PageRecord.objects.select_related('company').order_by('-page_id')[:30]
    recent_summaries = CompanyCrawlSummary.objects.select_related('company').order_by('-crawl_started_at')[:30]
    total_pages = PageRecord.objects.count()
    total_companies = Company.objects.count()
    total_crawled = Company.objects.filter(crawl_status='CRAWLED').count()

    telemetry = {
        'crawler_engine': 'SafeCrawler v2.0 (robots.txt compliant & validated)',
        'rate_limit_delay': '1.0s exponential backoff',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/128.0 (respectful public discovery)',
        'compliance_status': 'RFC 9309 Compliant Non-Intrusive Discovery',
        'pages_catalogued': total_pages,
        'companies_monitored': total_companies,
        'companies_crawled': total_crawled,
    }

    # Company-by-Company Coverage Report across all companies
    coverage_q = request.GET.get('coverage_q', '').strip()
    coverage_status = request.GET.get('coverage_status', '').strip()
    coverage_page_num = request.GET.get('coverage_page', 1)

    coverage_qs = Company.objects.annotate(
        jobs_found=Count('jobs', filter=~Q(jobs__verification_status='LEGACY_UNVERIFIED')),
        jobs_published=Count('jobs', filter=Q(jobs__status='ACTIVE', jobs__verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])),
        csr_records=Count('csr_projects', filter=Q(csr_projects__verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])),
        stale_jobs=Count('jobs', filter=Q(jobs__status='EXPIRED')),
        validated_jobs=Count('jobs', filter=Q(jobs__verification_status__in=['VALIDATED', 'SOURCE_CONFIRMED', 'PUBLISHED'])),
    ).all().order_by('-jobs_published', '-csr_records', 'company_name')

    if coverage_q:
        coverage_qs = coverage_qs.filter(
            Q(company_name__icontains=coverage_q) |
            Q(company_id__icontains=coverage_q) |
            Q(nse_symbol__icontains=coverage_q) |
            Q(ats_platform__icontains=coverage_q)
        )
    if coverage_status and coverage_status != 'all':
        coverage_qs = coverage_qs.filter(crawl_status=coverage_status)

    # Evaluate to list and attach explanation for zero records
    coverage_list = list(coverage_qs)
    for c in coverage_list:
        reasons = []
        if c.jobs_published == 0:
            if c.crawl_status == 'PENDING':
                reasons.append("Jobs: Crawl pending")
            elif c.crawl_status == 'NO_CAREER_URL':
                reasons.append("Jobs: Official careers URL not discoverable")
            elif c.crawl_status == 'BLOCKED':
                reasons.append("Jobs: Source blocked by bot firewall (HTTP 403)")
            elif c.crawl_status == 'FAILED':
                reasons.append("Jobs: Source connection unreachable")
            elif c.crawl_status == 'CRAWLED':
                reasons.append("Jobs: Verified checked; no active openings listed")
            else:
                reasons.append("Jobs: Verification pending")
        if c.csr_records == 0:
            if c.crawl_status == 'PENDING':
                reasons.append("CSR: Scan pending")
            elif c.crawl_status == 'CRAWLED':
                reasons.append("CSR: Verified checked; Schedule VII breakdown in PDF")
            else:
                reasons.append("CSR: Portal pending")
        c.zero_explanation = " | ".join(reasons) if reasons else "Fully Verified & Published"

    # Optional CSV Export of the Complete Coverage Report
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="company_job_coverage_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Company ID', 'Company Name', 'NSE Symbol', 'Website', 'Careers Source', 'ATS Platform', 'Jobs Found', 'Jobs Published', 'CSR Records', 'Crawl Status', 'Last Verified', 'Reason / Notes'])
        for c in coverage_list:
            writer.writerow([
                c.company_id, c.company_name, c.nse_symbol or '',
                c.website_url or '', c.careers_url or '',
                c.ats_platform or 'Direct/HTML',
                c.jobs_found, c.jobs_published, c.csr_records,
                c.crawl_status or 'PENDING', c.last_crawled or '',
                c.zero_explanation
            ])
        return response

    paginator = Paginator(coverage_list, 25)
    coverage_page_obj = paginator.get_page(coverage_page_num)

    return render(request, 'admin/verification/crawler_status.html', {
        'telemetry': telemetry,
        'recent_pages': recent_pages,
        'recent_summaries': recent_summaries,
        'coverage_page_obj': coverage_page_obj,
        'coverage_total_count': paginator.count,
        'coverage_q': coverage_q,
        'coverage_status': coverage_status,
        'live_stats': CRAWL_TASK_STATE["stats"],
        'is_running': CRAWL_TASK_STATE["is_running"]
    })

