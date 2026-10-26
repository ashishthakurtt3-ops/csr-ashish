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

    def handle(self, *args, **options):
        force = options.get('force', False)
        tenant = options.get('tenant')

        self.stdout.write("Running automated subscription renewal engine...")
        result = process_subscription_renewals(force_run=force, tenant_id=tenant)

        self.stdout.write(self.style.SUCCESS(
            f"[OK] Renewals complete: Processed={result['processed']}, "
            f"Renewed={result['renewed']}, Failed={result['failed']}, Expired={result['expired']}"
        ))
        for d in result.get('details', []):
            self.stdout.write(f"  - Sub {d['subscription_id']}: {d.get('result')} ({d.get('reason') or d.get('plan') or ''})")
