"""
modules/admin_panel/services/company_deletion_service.py
=======================================================
Single source of truth for permanently deleting a company and every record
that belongs to it.

Both the Company Management delete button and the Django admin bulk delete
action use this service so the deletion scope can never drift between them.
"""

import logging

from django.db import transaction

from modules.admin_panel.models import (
    AuditTrail,
    Company,
    CompanyCompletenessRegister,
    CompanyCrawlSummary,
    CompanyMetrics,
    CompanyRefreshRequest,
    CompanySource,
    Contact,
    CSROpportunity,
    CSRProject,
    Document,
    DroppedCandidate,
    Job,
    NGOCollaboration,
    OpportunityScore,
    PageRecord,
    Prospect,
)

logger = logging.getLogger(__name__)


# Audit-trail record types that store their own row id (as text) in record_id.
_AUDIT_RECORD_TYPES = {
    'Company': 'company',
    'Job': 'jobs',
    'CSRProject': 'csr_projects',
    'DOCUMENT': 'documents',
}


def delete_company_completely(company, deleted_by=None):
    """
    Permanently delete ``company`` and every related record.

    Returns a dict of deletion counts suitable for an admin confirmation message.

    Deletion order matters:
      1. Capture ids for audit purging and reporting.
      2. Delete stored document files (the Document FK is SET_NULL, so the rows
         would otherwise survive the company cascade).
      3. Purge audit-trail rows belonging to the company and its child records.
      4. Explicitly delete every child table (including SET_NULL relations).
      5. Delete the company itself as a final catch-all for CASCADE relations.
      6. Write one admin action record proving the deletion happened.
    """
    company_id = str(company.company_id)
    company_name = company.company_name

    with transaction.atomic():
        job_ids = [str(pk) for pk in Job.objects.filter(company=company).values_list('job_row_id', flat=True)]
        csr_ids = [str(pk) for pk in CSRProject.objects.filter(company=company).values_list('csr_id', flat=True)]

        documents = list(Document.objects.filter(company=company))
        document_ids = [str(doc.document_id) for doc in documents]

        stats = {
            'company_id': company_id,
            'company_name': company_name,
            'jobs': len(job_ids),
            'csr_projects': len(csr_ids),
            'documents': len(document_ids),
            'sources': CompanySource.objects.filter(company=company).count(),
            'crawl_summaries': CompanyCrawlSummary.objects.filter(company=company).count(),
            'crawled_pages': PageRecord.objects.filter(company=company).count(),
            'dropped_candidates': DroppedCandidate.objects.filter(company=company).count(),
            'contacts': Contact.objects.filter(company=company).count(),
            'opportunities': CSROpportunity.objects.filter(company=company).count(),
            'refresh_requests': CompanyRefreshRequest.objects.filter(company=company).count(),
        }

        # 1. Remove uploaded document files from storage before deleting the rows.
        for doc in documents:
            if not doc.file:
                continue
            try:
                doc.file.delete(save=False)
            except Exception as exc:  # Never let a storage error block a data purge.
                logger.warning(
                    "Could not delete stored file for document %s of company %s: %s",
                    doc.document_id, company_id, exc,
                )

        # 2. Purge audit history tied to the company and its child records.
        audit_ids = {
            'Company': [company_id],
            'Job': job_ids,
            'CSRProject': csr_ids,
            'DOCUMENT': document_ids,
        }
        for record_type, record_ids in audit_ids.items():
            if record_ids:
                AuditTrail.objects.filter(
                    record_type=record_type,
                    record_id__in=record_ids,
                ).delete()

        # 3. Explicitly remove every child table. Some FKs are SET_NULL, so they
        #    would be left behind by the cascade if we skipped this step.
        CompanySource.objects.filter(company=company).delete()
        DroppedCandidate.objects.filter(company=company).delete()
        CompanyCrawlSummary.objects.filter(company=company).delete()
        PageRecord.objects.filter(company=company).delete()
        CompanyCompletenessRegister.objects.filter(company=company).delete()
        CompanyMetrics.objects.filter(company=company).delete()
        CompanyRefreshRequest.objects.filter(company=company).delete()
        Document.objects.filter(company=company).delete()
        OpportunityScore.objects.filter(company=company).delete()
        CSROpportunity.objects.filter(company=company).delete()
        CSRProject.objects.filter(company=company).delete()
        Job.objects.filter(company=company).delete()
        Contact.objects.filter(company=company).delete()
        NGOCollaboration.objects.filter(company=company).delete()
        Prospect.objects.filter(company=company).delete()

        # 4. Final cascade for anything not covered above (saved records etc.).
        company.delete()

        # 5. Keep an immutable record of the administrative action itself.
        username = (
            deleted_by.username
            if deleted_by is not None and getattr(deleted_by, 'is_authenticated', False)
            else 'SYSTEM_ADMIN'
        )
        AuditTrail.objects.create(
            record_type='CompanyDeletion',
            record_id=company_id,
            action='DELETE_COMPANY',
            previous_value=f"{company_name} ({company_id})",
            new_value=None,
            user_role=username,
            notes=(
                "Permanently deleted company and all related data: "
                f"{stats['jobs']} jobs, {stats['csr_projects']} CSR projects, "
                f"{stats['documents']} documents, {stats['sources']} sources, "
                f"{stats['crawl_summaries']} crawl summaries, {stats['crawled_pages']} pages, "
                f"{stats['dropped_candidates']} dropped candidates, {stats['contacts']} contacts, "
                f"{stats['opportunities']} opportunities, {stats['refresh_requests']} refresh requests."
            ),
        )

    return stats