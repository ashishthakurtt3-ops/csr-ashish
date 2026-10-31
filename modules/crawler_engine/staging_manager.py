"""
modules/crawler_engine/staging_manager.py
=========================================
Candidate Staging and Controlled Publication Workflow.
Ensures extraction candidates are isolated in staging, validated against evidence,
and published to MySQL tables atomically without data loss or duplicate creation.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.db import transaction
from django.utils import timezone
from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, CompanySource
from .evidence_verifier import IndependentEvidenceVerifier


class CandidateStagingManager:
    """
    Manages the staging and controlled publication lifecycle:
    DISCOVERED -> FETCHED -> EXTRACTED -> EVIDENCE_VALIDATED -> APPROVED -> PUBLISHED
    """

    @classmethod
    def stage_and_publish_job(cls, company_id: str, job_data: Dict[str, Any], page_text: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Validates an extracted job record and, if approved, safely publishes it to MySQL.
        """
        is_valid, decision, details = IndependentEvidenceVerifier.verify_job_candidate(job_data, page_text)
        
        status_result = {
            "candidate_type": "JOB",
            "company_id": company_id,
            "title": job_data.get("job_title"),
            "url": job_data.get("detail_url"),
            "decision": decision,
            "is_valid": is_valid,
            "details": details,
            "action_taken": "STAGED_ONLY" if dry_run or not is_valid else "PUBLISHED"
        }

        if not is_valid or dry_run:
            return status_result

        # Controlled Atomic Publication
        with transaction.atomic():
            company = Company.objects.filter(company_id=company_id).first()
            if not company:
                status_result["action_taken"] = "ERROR_COMPANY_NOT_FOUND"
                return status_result

            # Check for existing duplicate by canonical URL or title+company
            app_url = job_data.get("application_url") or job_data.get("detail_url")
            existing = Job.objects.filter(company=company, application_url=app_url).first()
            if not existing:
                existing = Job.objects.filter(company=company, job_title=job_data.get("job_title")).first()

            now = timezone.now()
            if existing:
                # Update last seen timestamp without destroying existing fields
                existing.last_seen_at = now
                existing.last_seen_live_at = now
                existing.verification_status = 'SOURCE_CONFIRMED'
                existing.save(update_fields=['last_seen_at', 'last_seen_live_at', 'verification_status'])
                status_result["action_taken"] = "UPDATED_EXISTING"
            else:
                # Insert new verified job record
                job_id = f"JOB_{company_id}_{int(datetime.utcnow().timestamp())}"
                new_job = Job(
                    job_id=job_id,
                    company=company,
                    job_title=job_data.get("job_title"),
                    department=job_data.get("department") or "",
                    job_description=job_data.get("description") or "",
                    location=job_data.get("location_raw") or "India",
                    country="India",
                    employment_type=job_data.get("employment_type") or "Full-time",
                    source_url=job_data.get("detail_url"),
                    application_url=app_url,
                    ats_platform=job_data.get("ats_platform") or "Direct",
                    status='ACTIVE',
                    verification_status='PUBLISHED',
                    first_seen_at=now,
                    last_seen_at=now,
                    last_seen_live_at=now
                )
                new_job.save()
                status_result["action_taken"] = "INSERTED_NEW"
                status_result["new_job_id"] = job_id

        return status_result

    @classmethod
    def stage_and_publish_csr(cls, company_id: str, csr_data: Dict[str, Any], source_text: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Validates an extracted CSR project record and, if approved, safely publishes it to MySQL.
        """
        is_valid, decision, details = IndependentEvidenceVerifier.verify_csr_candidate(csr_data, source_text)

        status_result = {
            "candidate_type": "CSR_PROJECT",
            "company_id": company_id,
            "title": csr_data.get("project_name"),
            "url": csr_data.get("source_url"),
            "decision": decision,
            "is_valid": is_valid,
            "details": details,
            "action_taken": "STAGED_ONLY" if dry_run or not is_valid else "PUBLISHED"
        }

        if not is_valid or dry_run:
            return status_result

        with transaction.atomic():
            company = Company.objects.filter(company_id=company_id).first()
            if not company:
                status_result["action_taken"] = "ERROR_COMPANY_NOT_FOUND"
                return status_result

            project_name = csr_data.get("project_name")
            existing = CSRProject.objects.filter(company=company, project_name=project_name).first()
            now = timezone.now()

            if existing:
                existing.last_seen_at = now
                existing.last_seen_live_at = now
                existing.verification_status = 'SOURCE_CONFIRMED'
                existing.save(update_fields=['last_seen_at', 'last_seen_live_at', 'verification_status'])
                status_result["action_taken"] = "UPDATED_EXISTING"
            else:
                csr_id = f"CSR_{company_id}_{int(datetime.utcnow().timestamp())}"
                new_csr = CSRProject(
                    csr_id=csr_id,
                    company=company,
                    project_name=project_name,
                    category=csr_data.get("category") or "Item (x) - Rural Development Projects",
                    description=csr_data.get("description") or csr_data.get("evidence_text") or "",
                    state=csr_data.get("state") or "",
                    geographic_location=csr_data.get("location") or "India",
                    source_url=csr_data.get("source_url") or company.website_url,
                    evidence_text=csr_data.get("evidence_text") or "",
                    status='ACTIVE',
                    verification_status='PUBLISHED',
                    first_seen_at=now,
                    last_seen_at=now,
                    last_seen_live_at=now
                )
                new_csr.save()
                status_result["action_taken"] = "INSERTED_NEW"
                status_result["new_csr_id"] = csr_id

        return status_result
