from django.core.management.base import BaseCommand
from modules.admin_panel.models import PlanEntitlement


NEW_KEYS = {
    'browse_companies', 'view_job_csr_openings', 'verified_portal_links',
    'company_profiles', 'search_filters', 'saved_records_limit',
    'saved_searches_limit', 'export_rows_per_month', 'alert_notifications',
    'company_comparison', 'team_members', 'data_refresh_requests',
    'research_workspace', 'support_level', 'trial_period', 'billing_flexibility',
}


class Command(BaseCommand):
    help = 'Remove stale entitlements from active plans'

    def handle(self, *args, **options):
        for plan_code in ['free', 'pro', 'ultra']:
            stale = PlanEntitlement.objects.filter(
                plan_id=plan_code
            ).exclude(feature_key__in=NEW_KEYS)
            if stale.exists():
                keys = list(stale.values_list('feature_key', flat=True))
                count = stale.count()
                stale.delete()
                self.stdout.write(self.style.WARNING(
                    f"Removed {count} stale entitlements from {plan_code}: {keys}"
                ))
            else:
                total = PlanEntitlement.objects.filter(plan_id=plan_code).count()
                self.stdout.write(self.style.SUCCESS(
                    f"{plan_code}: all {total} entitlements are current"
                ))

