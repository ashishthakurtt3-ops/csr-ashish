from django.core.management.base import BaseCommand
from modules.admin_panel.snapshot_service import build_snapshots


class Command(BaseCommand):
    help = "Builds, strictly validates, and publishes precomputed platform statistics snapshots."

    def add_arguments(self, parser):
        parser.add_argument(
            '--triggered-by',
            type=str,
            default='CLI_COMMAND',
            help='Originator identifier (e.g. CLI_COMMAND, CRAWL_ENGINE, ADMIN_ACTION).'
        )
        parser.add_argument(
            '--notes',
            type=str,
            default=None,
            help='Optional notes describing the purpose of this audit run.'
        )
        parser.add_argument(
            '--force-defects',
            action='store_true',
            help='Force recalculation of is_defective flags across all jobs.'
        )
        parser.add_argument(
            '--ignore-suspect',
            action='store_true',
            help='Override SKIPPED_SUSPECT guard and publish even if threshold exceeded.'
        )
        parser.add_argument(
            '--max-change-threshold',
            type=float,
            default=0.30,
            help='Maximum permitted metric change vs previous run before flagging as suspect (default 0.30).'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting platform snapshot build..."))
        try:
            audit_run = build_snapshots(
                triggered_by=options['triggered_by'],
                notes=options.get('notes'),
                force_defects=options.get('force_defects', False),
                max_change_threshold=options.get('max_change_threshold', 0.30),
                ignore_suspect=options.get('ignore_suspect', False),
            )
            if audit_run.status == 'COMPLETE':
                self.stdout.write(self.style.SUCCESS(
                    f"Successfully published AuditRun #{audit_run.id} as CURRENT.\n"
                    f"Tracked Jobs: {audit_run.job_count}\n"
                    f"Status: {audit_run.status}\n"
                    f"Validation: {audit_run.validation_report.get('checks', {})}"
                ))
                # Prime caches automatically following authoritative snapshot publishing
                from django.core.management import call_command
                call_command('warm_cache')
            else:
                self.stdout.write(self.style.WARNING(
                    f"AuditRun #{audit_run.id} ended with status: {audit_run.status} (NOT published as current).\n"
                    f"Warnings: {audit_run.validation_report.get('warnings', [])}\n"
                    f"Errors: {audit_run.validation_report.get('errors', [])}"
                ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to build snapshot: {str(e)}"))
            raise
