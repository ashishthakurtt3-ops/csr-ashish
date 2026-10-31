import time
from datetime import datetime
from django.core.management.base import BaseCommand
from modules.website.utils.subscription_service import process_subscription_renewals


class Command(BaseCommand):
    help = 'Processes subscription renewals whose period end date has arrived using prototype wallet balances'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force renewal attempt even if period end has not yet arrived',
        )
        parser.add_argument(
            '--tenant',
            type=str,
            default=None,
            help='Run renewal only for a specific tenant ID',
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run continuously in background daemon mode for demo/testing',
        )
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Polling interval in seconds when running in daemon mode (default: 60)',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        tenant = options.get('tenant')
        is_daemon = options.get('daemon', False)
        interval = max(5, options.get('interval', 60))

        if not is_daemon:
            self._run_cycle(force, tenant)
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Starting Subscription Renewal Daemon (Polling every {interval}s)... Press Ctrl+C to stop."
        ))
        try:
            while True:
                self._run_cycle(force, tenant)
                time.sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nRenewal daemon stopped by user."))

    def _run_cycle(self, force, tenant):
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.stdout.write(f"[{now_str}] Checking automated subscription renewals...")
        result = process_subscription_renewals(force_run=force, tenant_id=tenant)

        msg = (
            f"Processed={result['processed']}, Renewed={result['renewed']}, "
            f"Failed={result['failed']}, Expired={result['expired']}"
        )
        if result['renewed'] > 0 or result['failed'] > 0 or result['expired'] > 0:
            self.stdout.write(self.style.SUCCESS(f"  [UPDATE] {msg}"))
            for d in result.get('details', []):
                self.stdout.write(f"    - Sub {d['subscription_id']}: {d.get('result')} ({d.get('reason') or d.get('plan') or ''})")
        else:
            self.stdout.write(f"  [OK] No subscriptions due for renewal ({msg}).")
