from django.core.management.base import BaseCommand
from modules.admin_panel.models import Plan, PlanEntitlement, User, Wallet, Subscription


CANONICAL_PLANS = [
    {
        'code': 'free',
        'name': 'Community Free',
        'slug': 'community-free',
        'description': '14-Day evaluation access to verified corporate profiles, active career opportunities, and Section 135 CSR projects.',
        'badge': '14-Day Free Trial',
        'cta_text': 'Start 14-Day Free Trial',
        'billing_note': '14-Day Free Trial • No credit card required',
        'monthly_price_paise': 0,
        'yearly_price_paise': 0,
        'currency': 'INR',
        'is_active': True,
        'is_visible': True,
        'is_popular': False,
        'is_contact_sales': False,
        'display_order': 1,
        'trial_days': 14,
        'allow_upgrade': True,
        'allow_downgrade': True,
        'allow_cancel': True,
        'auto_renew_default': False,
        'features': [
            'Full Top 200 Listed Companies Registry',
            'Verified Official Corporate & CSR Portal URLs',
            'Verified Corporate & Social-Impact Job Openings',
            '5 Donor Matchmaker Queries / Day',
            'Daily Web Crawl Provenance Logs',
            'Standard CSV Exports (up to 25 records / month)',
            '1 Team Seat & Community Support',
            '14 Days Full Evaluation Access',
        ],
        'highlight_features': ['14-Day Free Trial', '5 Matches/Day', 'Top 200 Companies', 'Verified Job Board'],
        'limits': {
            'daily_matches': 5,
            'api_access': False,
            'live_reprobe': False,
            'seats': 1,
            'export_rows_per_month': 25,
            'view_contacts': False,
            'audit_packs': False,
            'crm_limit': 10,
        },
        'entitlements': [
            ('daily_matches', 'Daily Matchmaker Queries', PlanEntitlement.TYPE_NUMERIC, 5, False),
            ('api_access', 'REST API Access', PlanEntitlement.TYPE_BOOLEAN, False, False),
            ('live_reprobe', 'Live Crawler Domain Probe', PlanEntitlement.TYPE_BOOLEAN, False, False),
            ('seats', 'Team Seats', PlanEntitlement.TYPE_NUMERIC, 1, False),
            ('export_rows_per_month', 'Monthly CSV Export Limit', PlanEntitlement.TYPE_NUMERIC, 25, False),
            ('view_contacts', 'Unmasked Corporate Direct Contacts', PlanEntitlement.TYPE_BOOLEAN, False, False),
            ('audit_packs', 'Section 135 Audit Packs', PlanEntitlement.TYPE_BOOLEAN, False, False),
            ('proposal_tools', 'AI CSR Pitch Generator', PlanEntitlement.TYPE_BOOLEAN, False, False),
            ('webhook_access', 'Webhook Alerts', PlanEntitlement.TYPE_BOOLEAN, False, False),
        ]
    },
    {
        'code': 'pro',
        'name': 'Impact Pro',
        'slug': 'impact-pro',
        'description': 'Advanced discovery, open RFPs, and direct corporate outreach suite for active non-profits and fundraisers.',
        'badge': 'Most Popular',
        'cta_text': 'Upgrade to Impact Pro',
        'billing_note': 'Billed monthly or annually (+18% GST)',
        'monthly_price_paise': 99900,
        'yearly_price_paise': 999000,
        'currency': 'INR',
        'is_active': True,
        'is_visible': True,
        'is_popular': True,
        'is_contact_sales': False,
        'display_order': 2,
        'trial_days': 14,
        'allow_upgrade': True,
        'allow_downgrade': True,
        'allow_cancel': True,
        'auto_renew_default': True,
        'features': [
            'Everything in Free, plus:',
            'Unlimited Algorithmic Donor Matchmaker Queries',
            'Unmasked CSR Decision-Maker & Executive Direct Contacts',
            'Real-Time Corporate Open RFPs & Grant Deadline Radar',
            'Live On-Demand Web Crawler Re-Check & HTTP Probing',
            '1-Click Tailored CSR Pitch & Outreach Email Generator',
            'Outreach Pipeline CRM with Custom Tags & Status Tracking',
            'Master Dataset Exports (up to 1,000 records / month)',
            '3 Dedicated Team Seats & Priority Support',
        ],
        'highlight_features': ['Unlimited Matchmaker', 'Unmasked Contacts', 'Open RFPs Radar', 'Outreach CRM'],
        'limits': {
            'daily_matches': None,
            'api_access': False,
            'live_reprobe': True,
            'seats': 3,
            'export_rows_per_month': 1000,
            'view_contacts': True,
            'audit_packs': False,
            'crm_limit': 100,
        },
        'entitlements': [
            ('daily_matches', 'Daily Matchmaker Queries', PlanEntitlement.TYPE_UNLIMITED, None, True),
            ('api_access', 'REST API Access', PlanEntitlement.TYPE_BOOLEAN, False, False),
            ('live_reprobe', 'Live Crawler Domain Probe', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('seats', 'Team Seats', PlanEntitlement.TYPE_NUMERIC, 3, False),
            ('export_rows_per_month', 'Monthly CSV Export Limit', PlanEntitlement.TYPE_NUMERIC, 1000, False),
            ('view_contacts', 'Unmasked Corporate Direct Contacts', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('audit_packs', 'Section 135 Audit Packs', PlanEntitlement.TYPE_BOOLEAN, False, False),
            ('proposal_tools', 'AI CSR Pitch Generator', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('webhook_access', 'Webhook Alerts', PlanEntitlement.TYPE_BOOLEAN, False, False),
        ]
    },
    {
        'code': 'ultra',
        'name': 'Ultra Enterprise',
        'slug': 'ultra-enterprise',
        'description': 'High-volume programmatic intelligence, Section 135 compliance, dedicated REST API access, and unlimited bulk data exports.',
        'badge': 'Ultra Enterprise Suite',
        'cta_text': 'Upgrade to Ultra Enterprise',
        'billing_note': 'Billed monthly or annually (+18% GST)',
        'monthly_price_paise': 199900,
        'yearly_price_paise': 1999000,
        'currency': 'INR',
        'is_active': True,
        'is_visible': True,
        'is_popular': False,
        'is_contact_sales': False,
        'display_order': 3,
        'trial_days': 14,
        'allow_upgrade': True,
        'allow_downgrade': True,
        'allow_cancel': True,
        'auto_renew_default': True,
        'features': [
            'Everything in Impact Pro, plus:',
            'Dedicated REST API Access (ib_enterprise_...) with Key Rotation',
            'Statutory Section 135 & Schedule VII Regulatory Audit Evidence Packs',
            'Immediate Live Crawler Re-Verification & MCA Statutory Re-Probing',
            'Real-Time Slack, Microsoft Teams & Custom Webhook Alerts',
            'Full Bulk Database Snapshot Exports (Complete Verified Dataset)',
            'White-Label Board-Ready PDF Company Intelligence Dossiers',
            '15 Dedicated Team Seats & 99.9% SLA Support',
        ],
        'highlight_features': ['REST API Access', 'Audit Evidence Packs', 'Immediate Re-Probing', 'Complete Bulk Exports'],
        'limits': {
            'daily_matches': None,
            'api_access': True,
            'live_reprobe': True,
            'seats': 15,
            'export_rows_per_month': None,
            'view_contacts': True,
            'audit_packs': True,
            'crm_limit': 1000,
        },
        'entitlements': [
            ('daily_matches', 'Daily Matchmaker Queries', PlanEntitlement.TYPE_UNLIMITED, None, True),
            ('api_access', 'REST API Access', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('live_reprobe', 'Live Crawler Domain Probe', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('seats', 'Team Seats', PlanEntitlement.TYPE_NUMERIC, 15, False),
            ('export_rows_per_month', 'Monthly CSV Export Limit', PlanEntitlement.TYPE_UNLIMITED, None, True),
            ('view_contacts', 'Unmasked Corporate Direct Contacts', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('audit_packs', 'Section 135 Audit Packs', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('proposal_tools', 'AI CSR Pitch Generator', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('webhook_access', 'Webhook Alerts', PlanEntitlement.TYPE_BOOLEAN, True, False),
        ]
    }
]


class Command(BaseCommand):
    help = 'Seeds canonical database-driven subscription plans, entitlements, and prototype wallets'

    def handle(self, *args, **options):
        self.stdout.write("Seeding canonical subscription plans...")
        for pdata_orig in CANONICAL_PLANS:
            pdata = pdata_orig.copy()
            entitlements = pdata.pop('entitlements', [])
            plan, created = Plan.objects.update_or_create(code=pdata['code'], defaults=pdata)
            action = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"  [OK] {action} plan: {plan.name} ({plan.code})"))

            # Populate entitlements
            for key, name, etype, val, is_unlim in entitlements:
                defaults = {
                    'display_name': name,
                    'feature_type': etype,
                    'is_unlimited': is_unlim,
                    'boolean_value': val if isinstance(val, bool) else False,
                    'numeric_value': val if isinstance(val, int) and not isinstance(val, bool) else None,
                    'text_value': str(val) if isinstance(val, str) else None,
                }
                PlanEntitlement.objects.update_or_create(
                    plan=plan,
                    feature_key=key,
                    defaults=defaults
                )

        # Remove any obsolete plans from the database (e.g. starter, enterprise, foundation)
        canonical_codes = [p['code'] for p in CANONICAL_PLANS]
        old_plans = list(Plan.objects.exclude(code__in=canonical_codes))
        for old_plan in old_plans:
            target_code = 'free' if old_plan.code in ('starter', 'community_free') else 'ultra'
            target_plan = Plan.objects.filter(code=target_code).first()
            Subscription.objects.filter(plan_record=old_plan).update(
                plan_id=target_code,
                plan_record=target_plan
            )
            Subscription.objects.filter(plan_id=old_plan.code).update(
                plan_id=target_code,
                plan_record=target_plan
            )
            PlanEntitlement.objects.filter(plan=old_plan).delete()
            old_plan.delete()
            self.stdout.write(f"  [CLEANUP] Migrated subscriptions and removed obsolete plan: {old_plan.code} -> {target_code}")

        # Initialize wallets for existing users
        self.stdout.write("Ensuring all users have prototype wallets...")
        for user in User.objects.all():
            wallet, created = Wallet.objects.get_or_create(user=user, defaults={'balance_paise': 0})
            if created:
                self.stdout.write(f"  [OK] Created wallet for {user.username}")

        # Link legacy subscriptions if needed
        admin_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        pro_plan = Plan.objects.filter(code='pro').first()
        if admin_user and pro_plan:
            Subscription.objects.filter(tenant_id='tenant_default').update(
                user=admin_user,
                plan_record=pro_plan,
                plan_id='pro'
            )
            self.stdout.write("  [OK] Linked tenant_default subscription to admin user.")

        self.stdout.write(self.style.SUCCESS("Database plan seeding successfully finished!"))
