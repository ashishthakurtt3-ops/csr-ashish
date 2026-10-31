import sys
from django.core.management.base import BaseCommand
from modules.admin_panel.snapshot_service import reconcile_snapshots


class Command(BaseCommand):
    help = "Recomputes every snapshot figure live and reconciles with current snapshot. Exits non-zero on any mismatch."

    def add_arguments(self, parser):
        parser.add_argument(
            '--run-id',
            type=int,
            default=None,
            help='Specific AuditRun ID to reconcile against (defaults to current complete run).'
        )

    def handle(self, *args, **options):
        from modules.admin_panel.models.snapshot import AuditRun

        run_id = options.get('run_id')
        audit_run = None
        if run_id:
            audit_run = AuditRun.objects.filter(pk=run_id).first()
            if not audit_run:
                self.stdout.write(self.style.ERROR(f"AuditRun #{run_id} not found."))
                sys.exit(1)

        self.stdout.write(self.style.NOTICE("Running Authoritative Snapshot Reconciliation..."))
        all_matched, results = reconcile_snapshots(audit_run)

        # Print formatted table
        header = f"{'Metric':<30} | {'Snapshot':<10} | {'Live':<10} | {'Diff':<8} | {'Status':<8}"
        separator = "-" * len(header)
        self.stdout.write("\n" + separator)
        self.stdout.write(header)
        self.stdout.write(separator)

        for row in results:
            if 'error' in row:
                self.stdout.write(self.style.ERROR(row['error']))
                sys.exit(1)

            metric = row['label']
            s_val = str(row['snapshot'])
            l_val = str(row['live'])
            diff = str(row['diff'])
            status = "MATCH" if row['match'] else "MISMATCH"
            status_styled = self.style.SUCCESS(status) if row['match'] else self.style.ERROR(status)

            self.stdout.write(f"{metric:<30} | {s_val:<10} | {l_val:<10} | {diff:<8} | {status_styled}")

        self.stdout.write(separator + "\n")

        if not all_matched:
            self.stdout.write(self.style.ERROR("Reconciliation FAILED: One or more snapshot metrics differ from live queries!"))
            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("Reconciliation PASSED: All snapshot metrics perfectly match live queries."))
            sys.exit(0)
