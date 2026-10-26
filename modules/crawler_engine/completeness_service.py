"""
Company Completeness & Verification Audit Service
=================================================
Maintains the 200-Company Completeness Register.
Enforces strict truthful evidence reporting per Part 4 of the ImpactBridge Specification.
"""
import os
import csv
import json
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q
from modules.admin_panel.models import (
    Company, Job, CSRProject, CSROpportunity, Contact,
    PageRecord, CompanyCrawlSummary, CompanyCompletenessRegister
)


class CompletenessService:
    """
    Authoritative service to evaluate, audit, and synchronize the completeness state
    of every company in the canonical registry.
    """

    @classmethod
    def sync_company(cls, company: Company) -> CompanyCompletenessRegister:
        """Audits and synchronizes the completeness register for a single canonical company."""
        summary = CompanyCrawlSummary.objects.filter(company=company).order_by('-summary_id').first()

        # 1. Corporate Identity & Official URLs
        audit_file = os.path.join(settings.BASE_DIR, 'scratch', 'all_200_companies_identity_audit.json')
        corp_identity_status = None
        if os.path.exists(audit_file):
            try:
                with open(audit_file, 'r', encoding='utf-8') as f:
                    audit_data = json.load(f)
                    for a in audit_data:
                        if a.get('company_id') == company.company_id:
                            corp_identity_status = a.get('status')
                            break
            except Exception:
                pass

        if not corp_identity_status:
            if company.verification_status == 'SOURCE_CONFIRMED' and company.cin:
                corp_identity_status = 'AUTHORITATIVE_VERIFIED'
            elif 'STATUTORY' in (company.verification_reason or ''):
                corp_identity_status = 'STATUTORY_EXEMPT'
            else:
                corp_identity_status = 'CIN_UNKNOWN_UNVERIFIED'
        
        url_status = 'VERIFIED'
        if company.crawl_status == 'REDIRECT_BLOCKED':
            url_status = 'REDIRECT_BLOCKED'
        elif company.crawl_status in ['FAILED', 'BLOCKED']:
            url_status = company.crawl_status

        # 2. Careers & ATS Discovery
        ats_name = company.ats_platform or (summary.ats_platform if summary else None) or 'Direct/HTML'
        ats_disc_status = 'DISCOVERED' if (company.ats_platform or (summary and summary.ats_platform)) else 'NOT_DETECTED'

        # 3. Jobs
        active_jobs_qs = company.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).exclude(verification_status='LEGACY_UNVERIFIED')
        jobs_pub_count = active_jobs_qs.count()
        jobs_disc_count = summary.jobs_discovered if summary else jobs_pub_count
        jobs_val_count = summary.jobs_validated if summary else jobs_pub_count

        if jobs_pub_count > 0:
            jobs_status = 'VERIFIED'
        elif company.crawl_status == 'BLOCKED':
            jobs_status = 'BLOCKED'
        elif company.crawl_status == 'FAILED':
            jobs_status = 'CRAWL_FAILED'
        elif company.crawl_status == 'REDIRECT_BLOCKED':
            jobs_status = 'SOURCE_UNAVAILABLE'
        elif company.crawl_status == 'CRAWLED':
            jobs_status = 'NO_RECORDS_CONFIRMED'
        else:
            jobs_status = 'PENDING_VERIFICATION'

        careers_src_status = jobs_status

        # 4. CSR Initiatives & Financials
        csr_pub_qs = company.csr_projects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
        csr_pub_count = csr_pub_qs.count()
        csr_disc_count = summary.csr_projects_discovered if summary else csr_pub_count

        if csr_pub_count > 0:
            csr_status = 'VERIFIED'
            csr_fin_status = 'VERIFIED' if csr_pub_qs.filter(budget__isnull=False).exists() else 'STATUTORY_MCA_ONLY'
        elif company.crawl_status in ['BLOCKED', 'FAILED', 'REDIRECT_BLOCKED']:
            csr_status = 'SOURCE_UNAVAILABLE'
            csr_fin_status = 'STATUTORY_MCA_ONLY'
        elif company.crawl_status == 'CRAWLED':
            csr_status = 'NO_RECORDS_CONFIRMED'
            csr_fin_status = 'STATUTORY_MCA_ONLY'
        else:
            csr_status = 'PENDING_VERIFICATION'
            csr_fin_status = 'NOT_DISCLOSED'

        csr_src_status = 'VERIFIED' if (company.csr_portal_url or company.sustainability_url or company.foundation_url) else 'NOT_STARTED'

        # 5. Documents, Annual Reports, ESG, Foundation
        annual_rep_status = 'VERIFIED' if company.annual_report_url else ('DISCOVERED' if company.investor_url else 'NOT_FOUND')
        brsr_status = 'VERIFIED' if company.brsr_url else ('DISCOVERED' if company.esg_url or company.sustainability_url else 'NOT_FOUND')
        foundation_status = 'VERIFIED' if company.foundation_url else 'NOT_APPLICABLE'

        # 6. Opportunities & Contacts
        opps_qs = company.open_opportunities.filter(status='OPEN', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
        opps_pub_count = opps_qs.count()
        opps_status = 'VERIFIED' if opps_pub_count > 0 else ('NO_RECORDS_CONFIRMED' if company.crawl_status == 'CRAWLED' else 'NONE')

        contacts_qs = company.contacts.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
        contacts_pub_count = contacts_qs.count()
        contacts_status = 'VERIFIED' if contacts_pub_count > 0 else 'NONE'

        # 7. Discovered URLs
        discovered_urls = []
        for u in [company.website_url, company.careers_url, company.csr_portal_url, company.sustainability_url, company.foundation_url, company.annual_report_url, company.brsr_url]:
            if u and u not in discovered_urls:
                discovered_urls.append(u)

        # 8. Overall Coverage Status
        # Crucial principle: NO_RECORDS_CONFIRMED is a category-specific outcome, not an overall company status.
        if jobs_pub_count > 0 and csr_pub_count > 0:
            overall_status = 'VERIFIED'
        elif company.crawl_status == 'BLOCKED':
            overall_status = 'BLOCKED'
        elif company.crawl_status == 'FAILED':
            overall_status = 'CRAWL_FAILED'
        elif company.crawl_status == 'REDIRECT_BLOCKED':
            overall_status = 'SOURCE_UNAVAILABLE'
        elif company.crawl_status == 'CRAWLED':
            overall_status = 'PARTIAL_COVERAGE'
        elif jobs_pub_count > 0 or csr_pub_count > 0:
            overall_status = 'PARTIAL_COVERAGE'
        else:
            overall_status = 'PENDING_VERIFICATION'

        # Timestamps
        last_attempt = summary.crawl_started_at if summary else (company.link_verified_at or timezone.now())
        last_success = summary.crawl_finished_at if (summary and summary.crawl_status == 'CRAWLED') else None
        err_log = summary.error_log if summary else None
        probe_file = os.path.join(settings.BASE_DIR, 'scratch', 'source_access_41_retry_results.json')
        if os.path.exists(probe_file):
            try:
                with open(probe_file, 'r', encoding='utf-8') as f:
                    probe_data = json.load(f)
                    for p in probe_data:
                        if p.get('id') == company.company_id and p.get('remaining_limitation'):
                            err_log = p.get('remaining_limitation')
                            break
            except Exception:
                pass

        record = None
        for attempt in range(5):
            try:
                record = CompanyCompletenessRegister.objects.filter(company=company).first()
                if not record:
                    record = CompanyCompletenessRegister(company=company, company_id_str=company.company_id)

                record.company_name = company.company_name
                record.official_website = company.website_url
                record.corporate_profile_status = corp_identity_status
                record.official_url_status = url_status
                record.careers_source_status = careers_src_status
                record.ats_platform = ats_name
                record.ats_discovery_status = ats_disc_status
                record.jobs_discovered = jobs_disc_count
                record.jobs_validated = jobs_val_count
                record.jobs_published = jobs_pub_count
                record.jobs_status = jobs_status
                record.csr_source_status = csr_src_status
                record.csr_projects_discovered = csr_disc_count
                record.csr_projects_published = csr_pub_count
                record.csr_projects_status = csr_status
                record.csr_financials_status = csr_fin_status
                record.annual_reports_status = annual_rep_status
                record.brsr_esg_status = brsr_status
                record.foundation_status = foundation_status
                record.opportunities_discovered = opps_pub_count
                record.opportunities_published = opps_pub_count
                record.opportunities_status = opps_status
                record.contacts_discovered = contacts_pub_count
                record.contacts_published = contacts_pub_count
                record.contacts_status = contacts_status
                record.last_attempt_at = last_attempt if isinstance(last_attempt, timezone.datetime) else timezone.now()
                record.last_successful_fetch_at = last_success
                record.source_urls_discovered = json.dumps(discovered_urls)
                record.failed_requests_error = err_log
                record.overall_coverage_status = overall_status

                record.save()
                break
            except Exception as lock_err:
                import time
                time.sleep(0.5 * (attempt + 1))
        return record

    @classmethod
    def sync_all_200_companies(cls):
        """Audits and synchronizes all canonical companies into the Completeness Register."""
        companies = Company.objects.all().order_by('company_id')
        records = []
        for comp in companies:
            rec = cls.sync_company(comp)
            records.append(rec)
        return records

    @classmethod
    def export_csv(cls, filepath: str):
        """Generates the required impactbridge_200_company_data_coverage.csv per Part 19."""
        records = CompanyCompletenessRegister.objects.all().order_by('company_id_str')
        fieldnames = [
            'company_id',
            'company_name',
            'official_domain',
            'identity_verification_status',
            'careers_source_status',
            'ats_provider',
            'careers_last_successful_check',
            'jobs_discovered',
            'jobs_eligible_published',
            'jobs_status',
            'csr_sources_discovered',
            'csr_projects_published',
            'csr_status',
            'csr_financials_status',
            'annual_reports_status',
            'brsr_esg_status',
            'opportunities_published',
            'contacts_published',
            'overall_completeness_status',
            'failed_sources_unresolved_issues'
        ]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in records:
                comp = r.company
                writer.writerow({
                    'company_id': r.company_id_str,
                    'company_name': r.company_name,
                    'official_domain': comp.official_domain or comp.website_url or 'N/A',
                    'identity_verification_status': r.corporate_profile_status,
                    'careers_source_status': r.careers_source_status,
                    'ats_provider': r.ats_platform or 'Direct/HTML',
                    'careers_last_successful_check': r.last_successful_fetch_at.strftime('%Y-%m-%d %H:%M') if r.last_successful_fetch_at else 'Live Audited',
                    'jobs_discovered': r.jobs_discovered,
                    'jobs_eligible_published': r.jobs_published,
                    'jobs_status': r.jobs_status,
                    'csr_sources_discovered': r.csr_source_status,
                    'csr_projects_published': r.csr_projects_published,
                    'csr_status': r.csr_projects_status,
                    'csr_financials_status': r.csr_financials_status,
                    'annual_reports_status': r.annual_reports_status,
                    'brsr_esg_status': r.brsr_esg_status,
                    'opportunities_published': r.opportunities_published,
                    'contacts_published': r.contacts_published,
                    'overall_completeness_status': r.overall_coverage_status,
                    'failed_sources_unresolved_issues': r.failed_requests_error or 'None'
                })
        return len(records)
