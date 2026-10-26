import json
from django.utils import timezone
from typing import Tuple, List, Any
from datetime import timedelta
from modules.admin_panel.models import Job, CSRProject, CSROpportunity, Contact, AuditTrail
from modules.admin_panel.verification import LINK_OK
from .link_verifier import verify_job_link, verify_csr_link, UNREACHABLE, BROKEN, CLOSED, LOGIN_WALL
from .normalizers import (
    is_page_title_not_csr_project,
    is_generic_or_non_csr_contact_email,
)

LINK_RECHECK_AFTER = timedelta(hours=24)


class VerificationService:
    """
    Enforces the strict multi-phase lifecycle:
    DISCOVERED -> FETCHED -> EXTRACTED -> VALIDATED -> SOURCE_CONFIRMED -> PUBLISHED

    Verifies that every populated factual field in the database record is
    strictly supported by the underlying source evidence and that links resolve live.
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

        # Check against interactive UI navigation defect patterns
        title_lower = job.job_title.strip().lower()
        ui_defect_patterns = [
            'how to apply',
            'discover more',
            'faqs & support',
            'review accommodations',
            'upload resume',
            'submit resume',
            'know more',
            'learn more',
            'apply now',
            'click here',
            'view details',
            'read more',
            'search jobs',
            'next >>',
            'previous <<',
        ]
        if any(p == title_lower or p in title_lower for p in ui_defect_patterns):
            return False, f"Job title '{job.job_title}' is an interactive UI navigation defect, not a genuine job opening."

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
            job.salary = None
            job.salary_min = None
            job.salary_max = None
            job.salary_currency = None

        # 4. Department check (if populated)
        if job.department and job.department.lower() not in ev_lower:
            job.department = None

        return True, "All populated fields verified against raw source evidence."

    @classmethod
    def validate_csr_project(cls, project: CSRProject) -> Tuple[bool, str]:
        """Validates that all populated CSR project fields have matching evidence and are not generic page titles."""
        if not project.source_url or not project.retrieved_at:
            return False, "Missing source_url or retrieved_at timestamp."

        if not project.evidence_text:
            return False, "Missing evidence_text."

        ev_lower = project.evidence_text.lower()

        # Project name check
        if not project.project_name:
            return False, "Empty project name."

        comp_name = None
        if getattr(project, 'company_id', None):
            try:
                comp_name = project.company.company_name
            except Exception:
                comp_name = None

        if is_page_title_not_csr_project(project.project_name, comp_name):
            return False, f"Project name '{project.project_name}' is a generic webpage title/heading, not a CSR project."

        proj_words = [w for w in project.project_name.lower().split() if len(w) > 3]
        if proj_words:
            matched = [w for w in proj_words if w in ev_lower]
            if len(matched) / len(proj_words) < 0.6:
                return False, f"Project name '{project.project_name}' not supported by source evidence."

        # Budget check (if populated)
        if project.budget and project.budget.lower() not in ev_lower:
            project.budget = None

        # Location check (if populated)
        if project.geographic_location and project.geographic_location.lower() not in ev_lower:
            project.geographic_location = None

        return True, "CSR project fields verified against source evidence."

    @classmethod
    def validate_csr_opportunity(cls, opp: CSROpportunity) -> Tuple[bool, str]:
        """Validates that a CSR opportunity/RFP has source URL and matching evidence."""
        src = opp.source_url or opp.portal_url
        if not src or not opp.retrieved_at:
            return False, "Missing source_url/portal_url or retrieved_at timestamp."

        if not opp.evidence_text:
            return False, "Missing evidence_text for CSR opportunity."

        if not opp.title:
            return False, "Empty opportunity title."

        comp_name = None
        if getattr(opp, 'company_id', None):
            try:
                comp_name = opp.company.company_name
            except Exception:
                comp_name = None

        if is_page_title_not_csr_project(opp.title, comp_name):
            return False, f"Opportunity title '{opp.title}' is a generic webpage title, not an RFP/grant call."

        ev_lower = opp.evidence_text.lower()
        title_words = [w for w in opp.title.lower().split() if len(w) > 3]
        if title_words:
            matched = [w for w in title_words if w in ev_lower]
            if len(matched) / len(title_words) < 0.6:
                return False, f"Opportunity title '{opp.title}' not supported by source evidence."

        return True, "CSR opportunity verified against source evidence."

    @classmethod
    def validate_contact(cls, contact: Contact) -> Tuple[bool, str]:
        """Validates that contact email/phone has matching evidence and is not a generic info@/webmaster@ mailbox."""
        if not contact.source_url or not contact.retrieved_at:
            return False, "Missing source_url or retrieved_at timestamp."

        if not contact.evidence_text:
            return False, "Missing evidence_text."

        ev_lower = contact.evidence_text.lower()

        if contact.email:
            if contact.email.lower() not in ev_lower or is_generic_or_non_csr_contact_email(contact.email):
                contact.email = None

        if contact.phone and contact.phone.lower() not in ev_lower:
            contact.phone = None

        if not contact.email and not contact.phone:
            return False, "Neither verified CSR email nor phone found in source evidence (generic info@/webmaster@ excluded)."

        return True, "Contact information verified against source evidence."

    @classmethod
    def process_validation_pipeline(cls, record: Any) -> bool:
        """Executes validation on an EXTRACTED record and advances to VALIDATED if sound."""
        if record.verification_status not in ('EXTRACTED', 'UNVERIFIED'):
            return False

        if isinstance(record, Job):
            is_valid, reason = cls.validate_job(record)
        elif isinstance(record, CSRProject):
            is_valid, reason = cls.validate_csr_project(record)
        elif isinstance(record, CSROpportunity):
            is_valid, reason = cls.validate_csr_opportunity(record)
        elif isinstance(record, Contact):
            is_valid, reason = cls.validate_contact(record)
        else:
            return False

        if is_valid:
            record.verification_status = 'VALIDATED'
            record.verification_reason = reason
            record.save()
            return True
        else:
            record.verification_status = 'REJECTED'
            record.verification_reason = reason
            if hasattr(record, 'status'):
                record.status = 'INACTIVE' if isinstance(record, Job) else 'CLOSED'
            record.save()
            return False

    @classmethod
    def verify_and_apply_link(cls, job: Job, force: bool = False) -> bool:
        """
        Live-checks the job's apply link and writes the outcome on the record.
        Returns True only when the link is verified (HTTP 200 + same posting). A job whose link is
        not verified is made INACTIVE so it can never be shown with a wrong/dead Apply button.
        """
        now = timezone.now()
        if not force and job.link_status == LINK_OK and job.link_verified_at:
            try:
                from django.utils.dateparse import parse_datetime
                last = parse_datetime(job.link_verified_at)
                if last and now - last < LINK_RECHECK_AFTER:
                    return True
            except Exception:
                pass
        res = verify_job_link(job.application_url, job.job_title, job.external_job_id)
        job.link_status = res.status
        job.link_http_status = res.http_status
        job.link_check_reason = res.reason
        job.link_verified_at = now.isoformat()
        if res.ok:
            return True
        job.status = 'INACTIVE'
        if res.status == LOGIN_WALL and getattr(job, 'company_id', None):
            try:
                comp = job.company
                if comp and comp.jobs_access != 'LOGIN_REQUIRED':
                    comp.jobs_access = 'LOGIN_REQUIRED'
                    comp.data_access_checked_at = now
                    comp.save(update_fields=['jobs_access', 'data_access_checked_at'])
            except Exception:
                pass
        if res.status in (BROKEN, CLOSED):
            job.verification_status = 'NOT_FOUND'
        elif res.status != UNREACHABLE:           # mismatch / redirected / generic landing page
            job.verification_status = 'REJECTED'
        job.verification_reason = f"Apply link not verified: {res.status} - {res.reason}"
        return False

    @classmethod
    def verify_and_apply_csr_link(cls, record: Any, force: bool = False) -> bool:
        """
        Live-checks a CSRProject or CSROpportunity source URL.
        Updates final URL if redirected within the company's official/foundation domain,
        and marks company.csr_access = 'LOGIN_REQUIRED' if a login wall is encountered.
        """
        now = timezone.now()
        url = getattr(record, 'source_url', None) or getattr(record, 'portal_url', None)
        comp = getattr(record, 'company', None)
        exp_domain = (comp.official_domain or comp.website_url) if comp else None
        res = verify_csr_link(url, expected_domain=exp_domain)
        if hasattr(record, 'link_status'):
            record.link_status = LINK_OK if res.ok else res.status
        if hasattr(record, 'link_verified_at'):
            record.link_verified_at = now.isoformat()
        if res.ok:
            if res.final_url and res.final_url != url and hasattr(record, 'source_url') and record.source_url:
                record.source_url = res.final_url
            return True
        if res.status == LOGIN_WALL and comp:
            try:
                if comp.csr_access != 'LOGIN_REQUIRED':
                    comp.csr_access = 'LOGIN_REQUIRED'
                    comp.data_access_checked_at = now
                    comp.save(update_fields=['csr_access', 'data_access_checked_at'])
            except Exception:
                pass
        if res.status in (BROKEN, CLOSED):
            record.verification_status = 'REJECTED'
            record.verification_reason = f"CSR source link broken: {res.reason}"
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

        # Jobs additionally need a live-verified apply link and an unambiguous owner.
        if isinstance(record, Job):
            if record.owner_status != 'OWNED':
                record.status = 'INACTIVE'
                record.verification_reason = f"Owner not resolved ({record.owner_status or 'unknown'})."
                record.save()
                return False
            if not cls.verify_and_apply_link(record):
                record.save()
                return False

        # Step 1: Advance to SOURCE_CONFIRMED
        if record.verification_status == 'VALIDATED':
            record.verification_status = 'SOURCE_CONFIRMED'
            if hasattr(record, 'link_status') and not isinstance(record, Job):
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
            if hasattr(record, 'link_status') and not isinstance(record, Job):
                record.link_status = 'PUBLISHED'
            if hasattr(record, 'status'):
                record.status = 'ACTIVE' if isinstance(record, Job) else 'OPEN'
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
