import json
from django.utils import timezone
from typing import Tuple, List, Any
from modules.admin_panel.models import Job, CSRProject, CSROpportunity, Contact, AuditTrail


class VerificationService:
    """
    Enforces the strict multi-phase lifecycle:
    DISCOVERED -> FETCHED -> EXTRACTED -> VALIDATED -> SOURCE_CONFIRMED -> PUBLISHED
    
    Verifies that every populated factual field in the database record is 
    strictly supported by the underlying source evidence.
    """

    @classmethod
    def validate_job(cls, job: Job) -> Tuple[bool, str]:
        """Validates that all populated job fields have matching evidence."""
        if not job.source_url or not job.retrieved_at:
            return False, "Missing source_url or retrieved_at timestamp."

        if not job.evidence_text:
            return False, "Missing evidence_text: HTTP 200 alone cannot justify factual validity."

        ev_lower = job.evidence_text.lower()

        # 1. Job Title check
        if not job.job_title:
            return False, "Empty job title."
        
        # Check title in evidence (case-insensitive substring or stripped)
        title_words = [w for w in job.job_title.lower().split() if len(w) > 3]
        if title_words:
            # At least 70% of distinctive title words must appear in evidence
            matched_words = [w for w in title_words if w in ev_lower]
            if len(matched_words) / len(title_words) < 0.7:
                return False, f"Job title '{job.job_title}' is not supported by source evidence."
        elif job.job_title.lower() not in ev_lower:
            return False, f"Job title '{job.job_title}' is not in source evidence."

        # 2. Location check (if populated)
        if job.location:
            loc_clean = job.location.lower().split(',')[0].strip()
            if loc_clean and loc_clean not in ev_lower:
                return False, f"Populated location '{job.location}' not found in source evidence."

        # 3. Salary check (if populated)
        if job.salary and job.salary.lower() not in ev_lower:
            return False, f"Populated salary '{job.salary}' not found in source evidence."

        # 4. Department check (if populated)
        if job.department and job.department.lower() not in ev_lower:
            return False, f"Populated department '{job.department}' not found in source evidence."

        return True, "All populated fields verified against raw source evidence."

    @classmethod
    def validate_csr_project(cls, project: CSRProject) -> Tuple[bool, str]:
        """Validates that all populated CSR project fields have matching evidence."""
        if not project.source_url or not project.retrieved_at:
            return False, "Missing source_url or retrieved_at timestamp."

        if not project.evidence_text:
            return False, "Missing evidence_text."

        ev_lower = project.evidence_text.lower()

        # Project name check
        if not project.project_name:
            return False, "Empty project name."

        proj_words = [w for w in project.project_name.lower().split() if len(w) > 3]
        if proj_words:
            matched = [w for w in proj_words if w in ev_lower]
            if len(matched) / len(proj_words) < 0.6:
                return False, f"Project name '{project.project_name}' not supported by source evidence."

        # Budget check (if populated)
        if project.budget and project.budget.lower() not in ev_lower:
            return False, f"Populated budget '{project.budget}' not found in source evidence."

        # Location check (if populated)
        if project.geographic_location and project.geographic_location.lower() not in ev_lower:
            return False, f"Populated location '{project.geographic_location}' not found in source evidence."

        return True, "CSR project fields verified against source evidence."

    @classmethod
    def validate_contact(cls, contact: Contact) -> Tuple[bool, str]:
        """Validates that contact email/phone has matching evidence."""
        if not contact.source_url or not contact.retrieved_at:
            return False, "Missing source_url or retrieved_at timestamp."

        if not contact.evidence_text:
            return False, "Missing evidence_text."

        ev_lower = contact.evidence_text.lower()

        if contact.email and contact.email.lower() not in ev_lower:
            return False, f"Email '{contact.email}' not found in source evidence."

        if contact.phone and contact.phone.lower() not in ev_lower:
            return False, f"Phone '{contact.phone}' not found in source evidence."

        return True, "Contact information verified against source evidence."

    @classmethod
    def process_validation_pipeline(cls, record: Any) -> bool:
        """Executes validation on an EXTRACTED record and advances to VALIDATED if sound."""
        if record.verification_status != 'EXTRACTED' and record.verification_status != 'UNVERIFIED':
            return False

        if isinstance(record, Job):
            is_valid, reason = cls.validate_job(record)
        elif isinstance(record, CSRProject):
            is_valid, reason = cls.validate_csr_project(record)
        elif isinstance(record, Contact):
            is_valid, reason = cls.validate_contact(record)
        else:
            return False

        now_str = timezone.now().isoformat()
        if is_valid:
            record.verification_status = 'VALIDATED'
            record.verification_reason = reason
            record.save()
            return True
        else:
            record.verification_status = 'REJECTED'
            record.verification_reason = reason
            record.save()
            return False

    @classmethod
    def publish_record(cls, record: Any, actor: str = "SystemValidator") -> bool:
        """
        Promotes a VALIDATED record through SOURCE_CONFIRMED to PUBLISHED.
        Enforces VerifiableModel transition constraints strictly.
        """
        if record.verification_status not in ('VALIDATED', 'SOURCE_CONFIRMED'):
            # Run validation first
            valid = cls.process_validation_pipeline(record)
            if not valid:
                return False

        now_str = timezone.now().isoformat()

        # Step 1: Advance to SOURCE_CONFIRMED
        if record.verification_status == 'VALIDATED':
            record.verification_status = 'SOURCE_CONFIRMED'
            if hasattr(record, 'link_status'):
                record.link_status = 'SOURCE_CONFIRMED'
            if hasattr(record, 'confidence'):
                record.confidence = 0.98
            record.save()

            AuditTrail.objects.create(
                record_type=record.__class__.__name__,
                record_id=str(getattr(record, 'pk', '')),
                action='VERIFICATION_SOURCE_CONFIRMED',
                new_value='SOURCE_CONFIRMED',
                user_role=actor,
                notes=record.verification_reason or "Source evidence verified.",
                timestamp=now_str
            )

        # Step 2: Advance to PUBLISHED
        if record.verification_status == 'SOURCE_CONFIRMED':
            record.verification_status = 'PUBLISHED'
            if hasattr(record, 'link_status'):
                record.link_status = 'PUBLISHED'
            record.save()

            AuditTrail.objects.create(
                record_type=record.__class__.__name__,
                record_id=str(getattr(record, 'pk', '')),
                action='VERIFICATION_PUBLISHED',
                new_value='PUBLISHED',
                user_role=actor,
                notes="Published to live platform index.",
                timestamp=now_str
            )
            return True

        return False
