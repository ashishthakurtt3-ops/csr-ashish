from django.core.management.base import BaseCommand
from modules.admin_panel.snapshot_service import build_snapshots


class Command(BaseCommand):
    help = "Forces a full manual rebuild of all platform statistics snapshots and defect flags."

    def add_arguments(self, parser):
        parser.add_argument(
            '--notes',
            type=str,
            default='Manual snapshot rebuild requested via CLI',
            help='Notes describing the purpose of this manual rebuild.'
        )
        parser.add_argument(
            '--ignore-suspect',
            action='store_true',
            help='Force publish even if metric change threshold is tripped.'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Executing forced manual snapshot rebuild..."))
        audit_run = build_snapshots(
            triggered_by='MANUAL_REBUILD',
            notes=options.get('notes'),
            force_defects=True,
            ignore_suspect=options.get('ignore_suspect', False),
        )
        if audit_run.status == 'COMPLETE':
            self.stdout.write(self.style.SUCCESS(
                f"Manual rebuild succeeded: AuditRun #{audit_run.id} is now CURRENT."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"Manual rebuild ended with status: {audit_run.status}"
            ))
