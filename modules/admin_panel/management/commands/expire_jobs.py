"""
Expiry sweep based strictly on absence, not age:

    python manage.py expire_jobs

Rule: Age alone must never expire jobs. A failing apply-link must never expire jobs.
A job becomes EXPIRED only when confirmed absent:
When a job has been soft-deleted (status='REMOVED') for more than 7 days, it is transitioned to EXPIRED.
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.admin_panel.models import Job, AuditTrail


class Command(BaseCommand):
    help = "Expire jobs confirmed absent from source portals (expiry-by-absence, never by age or link failure)."

    def handle(self, *args, **o):
        from django.conf import settings
        if getattr(settings, 'FREEZE_JOB_EXPIRY_AND_DELETION', False):
            self.stdout.write(self.style.WARNING("FREEZE_JOB_EXPIRY_AND_DELETION is True: All job expiry and deletion are frozen until operator approval."))
            return

        now = timezone.now()
        # Expiry-by-absence: Jobs soft-removed for > 7 days become EXPIRED
        cutoff = now - timedelta(days=7)
        qs = Job.objects.filter(status='REMOVED', removed_at__lt=cutoff)
        n = qs.update(
            status='EXPIRED',
            verification_status='STALE',
            verification_reason='Confirmed absent from source portal for more than 7 days.'
        )
        AuditTrail.objects.create(
            record_type='Job',
            record_id='*',
            action='EXPIRY_BY_ABSENCE',
            new_value=f'expired={n}',
            user_role='expire_jobs',
            notes='Confirmed absent from source portal >7d grace period',
            timestamp=now.isoformat()
        )
        self.stdout.write(self.style.SUCCESS(f"Expired {n} jobs confirmed absent (>7 days since removal)."))
