"""
Pre-seed dependency audit as a Django management command.
Usage: python manage.py audit_plan_deps
"""
import sys
from django.core.management.base import BaseCommand
from django.db.models import Q
from modules.admin_panel.models import (
    Plan, PlanEntitlement, Subscription, Payment,
    WalletTransaction, SubscriptionEvent, Invoice, UsageCounter
)


class Command(BaseCommand):
    help = 'Audit all plan dependencies before three-tier seed'

    def handle(self, *args, **options):
        self.stdout.write("=" * 70)
        self.stdout.write("PRE-SEED DEPENDENCY AUDIT")
        self.stdout.write("=" * 70)

        # 1. All plans with metadata
        self.stdout.write("\n--- EXISTING PLANS ---")
        for p in Plan.objects.all().order_by('display_order'):
            self.stdout.write(
                f"  code={p.code!r}, name={p.name!r}, active={p.is_active}, "
                f"visible={p.is_visible}, monthly={p.monthly_price_paise}, "
                f"yearly={p.yearly_price_paise}, order={p.display_order}"
            )

        # 2. Subscriptions per plan
        self.stdout.write("\n--- SUBSCRIPTIONS PER PLAN ---")
        for p in Plan.objects.all():
            subs_by_id = Subscription.objects.filter(plan_id=p.code)
            subs_by_fk = Subscription.objects.filter(plan_record=p)
            combined = Subscription.objects.filter(
                Q(plan_id=p.code) | Q(plan_record=p)
            ).distinct()
            self.stdout.write(
                f"  {p.code}: by plan_id={subs_by_id.count()}, "
                f"by plan_record FK={subs_by_fk.count()}, "
                f"combined distinct={combined.count()}"
            )
            for s in combined:
                self.stdout.write(
                    f"    sub={s.subscription_id}, user={s.user}, "
                    f"tenant={s.tenant_id}, status={s.status}, "
                    f"plan_id={s.plan_id}, plan_fk={s.plan_record_id}"
                )

        # Also check for aliases
        for alias in ['free', 'ultra']:
            subs = Subscription.objects.filter(plan_id=alias)
            if subs.exists():
                self.stdout.write(f"  ALIAS '{alias}': {subs.count()} subscriptions")

        # 3. Payments referencing each plan
        self.stdout.write("\n--- PAYMENTS PER PLAN ---")
        for p in Plan.objects.all():
            payments = Payment.objects.filter(plan_code=p.code)
            self.stdout.write(f"  {p.code}: {payments.count()} payments")
            for pay in payments[:5]:
                self.stdout.write(
                    f"    {pay.payment_id} type={pay.payment_type} "
                    f"status={pay.payment_status} amount={pay.amount_paise}"
                )

        for alias in ['free', 'ultra', 'starter']:
            payments = Payment.objects.filter(plan_code=alias)
            if payments.exists():
                self.stdout.write(f"  ALIAS '{alias}': {payments.count()} payments")

        # 4. Subscription events
        self.stdout.write("\n--- SUBSCRIPTION EVENTS ---")
        for p in Plan.objects.all():
            events_from = SubscriptionEvent.objects.filter(from_plan=p.code)
            events_to = SubscriptionEvent.objects.filter(to_plan=p.code)
            if events_from.exists() or events_to.exists():
                self.stdout.write(
                    f"  {p.code}: from_plan={events_from.count()}, "
                    f"to_plan={events_to.count()}"
                )
        total_events = SubscriptionEvent.objects.count()
        self.stdout.write(f"  Total events: {total_events}")

        # 5. Invoices per plan
        self.stdout.write("\n--- INVOICES PER PLAN ---")
        for p in Plan.objects.all():
            invs = Invoice.objects.filter(plan_id=p.code)
            self.stdout.write(f"  {p.code}: {invs.count()} invoices")
        total_invoices = Invoice.objects.count()
        self.stdout.write(f"  Total invoices: {total_invoices}")

        # 6. Entitlements per plan
        self.stdout.write("\n--- ENTITLEMENTS PER PLAN ---")
        for p in Plan.objects.all():
            ents = PlanEntitlement.objects.filter(plan=p)
            self.stdout.write(f"  {p.code}: {ents.count()} entitlements")
            for e in ents:
                self.stdout.write(
                    f"    {e.feature_key}: type={e.feature_type}, "
                    f"bool={e.boolean_value}, num={e.numeric_value}, "
                    f"text={e.text_value!r}, unlimited={e.is_unlimited}"
                )

        # 7. Usage counters
        self.stdout.write("\n--- USAGE COUNTERS ---")
        counters = UsageCounter.objects.all()
        self.stdout.write(f"  Total: {counters.count()}")
        for c in counters[:10]:
            self.stdout.write(
                f"    tenant={c.tenant_id}, metric={c.metric}, "
                f"period={c.period_date}, used={c.used}"
            )

        # 8. Plan code availability
        self.stdout.write("\n--- PLAN CODE AVAILABILITY ---")
        for code in ['free', 'ultra']:
            exists = Plan.objects.filter(code=code).exists()
            self.stdout.write(
                f"  code={code!r}: {'EXISTS' if exists else 'AVAILABLE'}"
            )

        # 9. PLAN_ALIASES in subscription_service.py
        self.stdout.write("\n--- SUBSCRIPTION SERVICE PLAN_ALIASES ---")
        try:
            from modules.website.utils.subscription_service import PLAN_ALIASES
            self.stdout.write(f"  {PLAN_ALIASES}")
        except Exception as e:
            self.stdout.write(f"  Could not import: {e}")

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("AUDIT COMPLETE - SAFE TO PROCEED")
        self.stdout.write("=" * 70)

