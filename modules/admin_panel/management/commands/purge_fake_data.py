"""
Delete fabricated / unverifiable records and demote records without proof so they can never resurface.

    python manage.py purge_fake_data                 # dry run (default): only prints counts
    python manage.py purge_fake_data --apply         # really delete & demote (take a backup first!)
    python manage.py purge_fake_data --apply --include-unverified

Always deleted (they are invented, not crawled):
  * Job rows whose job_id starts with 'REQ' or verification_status = LEGACY_UNVERIFIED
  * Contact rows with verification_status = PATTERN_DERIVED_UNVERIFIED (guessed e-mail addresses)

Always demoted to REJECTED (never shown publicly because they lack proof or are generic):
  * Published CSROpportunity rows with no source_url/portal_url or no evidence_text
  * Published CSRProject rows with no source_url or no evidence_text, or whose project_name is a generic webpage title
  * Published Contact rows with no source_url or no evidence_text, or whose email is a generic info@/webmaster@ mailbox

With --include-unverified also deleted:
  * Jobs / CSR projects / opportunities with status QUARANTINED or REJECTED
  * NGO collaborations still UNVERIFIED
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from modules.admin_panel.models import Job, Contact, CSRProject, CSROpportunity, NGOCollaboration
from modules.crawler_engine.normalizers import (
    is_page_title_not_csr_project,
    is_generic_or_non_csr_contact_email,
)


class Command(BaseCommand):
    help = "Purge fabricated seed jobs/contacts and demote unverified opportunities, page-title CSR projects, and generic contacts."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Actually delete/demote (default is dry run).')
        parser.add_argument('--include-unverified', action='store_true',
                            help='Also delete quarantined/rejected/unverified records.')

    def handle(self, *args, **opts):
        delete_plan = [
            ('Fake REQ-* / legacy jobs', Job.objects.filter(job_id__startswith='REQ') |
             Job.objects.filter(verification_status='LEGACY_UNVERIFIED')),
            ('Pattern-derived (guessed) contacts', Contact.objects.filter(verification_status='PATTERN_DERIVED_UNVERIFIED')),
        ]
        if opts['include_unverified']:
            delete_plan += [
                ('Quarantined/rejected jobs', Job.objects.filter(verification_status__in=['QUARANTINED', 'REJECTED'])),
                ('Quarantined/rejected CSR projects', CSRProject.objects.filter(verification_status__in=['QUARANTINED', 'REJECTED'])),
                ('Quarantined/rejected opportunities', CSROpportunity.objects.filter(verification_status__in=['QUARANTINED', 'REJECTED'])),
                ('Unverified NGO collaborations', NGOCollaboration.objects.filter(verification_status='UNVERIFIED')),
            ]

        # 1. Opportunities without source URL or evidence
        unproven_opps_qs = CSROpportunity.objects.filter(
            verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED']
        ).filter(
            (Q(source_url__isnull=True) | Q(source_url='')) & (Q(portal_url__isnull=True) | Q(portal_url='')) |
            Q(evidence_text__isnull=True) | Q(evidence_text='')
        )

        # 2. CSR projects without source URL / evidence OR that are actually webpage titles
        bad_csr_pks = []
        for p in CSRProject.objects.select_related('company').filter(
            verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED']
        ):
            cname = p.company.company_name if p.company else None
            if (not (p.source_url or '').strip()
                    or not (p.evidence_text or '').strip()
                    or is_page_title_not_csr_project(p.project_name, cname)):
                bad_csr_pks.append(p.pk)

        # 3. Contacts without source URL / evidence OR with generic info@/webmaster@ email
        bad_contact_pks = []
        for c in Contact.objects.filter(
            verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED']
        ):
            has_valid_csr_email = bool(c.email and not is_generic_or_non_csr_contact_email(c.email))
            has_phone = bool((c.phone or '').strip())
            if (not (c.source_url or '').strip()
                    or not (c.evidence_text or '').strip()
                    or (not has_valid_csr_email and not has_phone)):
                bad_contact_pks.append(c.pk)

        for label, qs in delete_plan:
            self.stdout.write(f"[DELETE] {label}: {qs.count()}")
        self.stdout.write(f"[DEMOTE] Opportunities without source URL or evidence: {unproven_opps_qs.count()}")
        self.stdout.write(f"[DEMOTE] CSR projects that are page titles or lack evidence: {len(bad_csr_pks)}")
        self.stdout.write(f"[DEMOTE] Generic (info@/webmaster@) or unproven contacts: {len(bad_contact_pks)}")

        if not opts['apply']:
            self.stdout.write(self.style.WARNING(
                "Dry run only. Back up first (python manage.py backup_database), then re-run with --apply."
            ))
            return

        with transaction.atomic():
            for label, qs in delete_plan:
                n, _ = qs.delete()
                self.stdout.write(self.style.SUCCESS(f"Deleted {n} rows: {label}"))

            n_opps = unproven_opps_qs.update(
                verification_status='REJECTED',
                status='CLOSED',
                verification_reason='Demoted: missing source_url or evidence_text.'
            )
            self.stdout.write(self.style.SUCCESS(f"Demoted {n_opps} unproven opportunities"))

            if bad_csr_pks:
                n_csr = CSRProject.objects.filter(pk__in=bad_csr_pks).update(
                    verification_status='REJECTED',
                    verification_reason='Demoted: generic webpage title or missing source evidence.'
                )
                self.stdout.write(self.style.SUCCESS(f"Demoted {n_csr} page-title / unproven CSR projects"))

            if bad_contact_pks:
                n_con = Contact.objects.filter(pk__in=bad_contact_pks).update(
                    verification_status='REJECTED',
                    verification_reason='Demoted: generic non-CSR mailbox (info@/webmaster@) or missing source evidence.'
                )
                self.stdout.write(self.style.SUCCESS(f"Demoted {n_con} generic / unproven contacts"))
