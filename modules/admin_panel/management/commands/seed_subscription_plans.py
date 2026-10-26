from django.core.management.base import BaseCommand
from modules.admin_panel.models import Plan, PlanEntitlement, User, Wallet, Subscription


CANONICAL_PLANS = [
    {
        'code': 'starter',
        'name': 'Community Starter',
        'slug': 'community-starter',
        'description': 'Essential CSR discovery & directory access for grassroots non-profits, researchers, and job seekers.',
        'badge': 'Free Forever',
        'cta_text': 'Start Free',
        'billing_note': 'No credit card required',
        'monthly_price_paise': 0,
        'yearly_price_paise': 0,
        'currency': 'INR',
        'is_active': True,
        'is_visible': True,
        'is_popular': False,
        'is_contact_sales': False,
        'display_order': 1,
        'trial_days': 0,
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
        ],
        'highlight_features': ['5 Matches/Day', 'Top 200 Companies', 'Verified Job Board'],
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
        'monthly_price_paise': 499900,
        'yearly_price_paise': 4799000,
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
            'Everything in Starter, plus:',
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
        'code': 'enterprise',
        'name': 'Corporate Enterprise',
        'slug': 'corporate-enterprise',
        'description': 'High-volume programmatic intelligence, Section 135 compliance, and multi-user seats for large foundations and corporates.',
        'badge': 'Institutional Access',
        'cta_text': 'Upgrade to Enterprise',
        'billing_note': 'Billed monthly or annually (+18% GST)',
        'monthly_price_paise': 1999900,
        'yearly_price_paise': 18999000,
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
            'Everything in Pro, plus:',
            'Dedicated REST API Access (ib_enterprise_...) with Key Rotation',
            'Statutory Section 135 & Schedule VII Regulatory Audit Evidence Packs',
            'Priority High-Speed Web Scraping Probes (Hourly Sync Priority)',
            'Real-Time Slack, Microsoft Teams & Custom Webhook Alerts',
            'Full Bulk Database Snapshot Exports (10,000+ Records)',
            'White-Label Board-Ready PDF Company Intelligence Dossiers',
            '15 Dedicated Team Seats & 99.9% SLA Support',
        ],
        'highlight_features': ['REST API Access', 'Audit Evidence Packs', '15 Team Seats', 'Real-Time Webhooks'],
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
    },
    {
        'code': 'foundation',
        'name': 'Foundation Master',
        'slug': 'foundation-master',
        'description': 'Apex institutional data feed, raw programmatic stream, custom crawler pipelines, and multi-organization federation.',
        'badge': 'Apex Institutional Suite',
        'cta_text': 'Get Foundation Master',
        'billing_note': 'Billed monthly or annually (+18% GST)',
        'monthly_price_paise': 4999900,
        'yearly_price_paise': 47999000,
        'currency': 'INR',
        'is_active': True,
        'is_visible': True,
        'is_popular': False,
        'is_contact_sales': False,
        'display_order': 4,
        'trial_days': 0,
        'allow_upgrade': True,
        'allow_downgrade': True,
        'allow_cancel': True,
        'auto_renew_default': True,
        'features': [
            'Everything in Corporate Enterprise, plus:',
            'Highest Priority Dedicated API Data Feed & High-Volume Batch Limits',
            'Custom Domain Monitoring & Dedicated On-Demand Web Scraping Clusters',
            'Multi-Entity Consolidated CSR Portfolio Monitoring & ERP Integrations',
            'Full Statutory MCA Disclosures Stream & Archival Data Vaults',
            'Unlimited Team Seats & Dedicated Institutional Account Strategist',
            'Custom SLA Guarantees & Contract Invoicing Support',
        ],
        'highlight_features': ['Highest API Limits', 'Custom Crawler Clusters', 'Unlimited Seats', 'Dedicated Strategist'],
        'limits': {
            'daily_matches': None,
            'api_access': True,
            'live_reprobe': True,
            'seats': 50,
            'export_rows_per_month': None,
            'view_contacts': True,
            'audit_packs': True,
            'crm_limit': 10000,
        },
        'entitlements': [
            ('daily_matches', 'Daily Matchmaker Queries', PlanEntitlement.TYPE_UNLIMITED, None, True),
            ('api_access', 'REST API Access', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('live_reprobe', 'Live Crawler Domain Probe', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('seats', 'Team Seats', PlanEntitlement.TYPE_NUMERIC, 50, False),
            ('export_rows_per_month', 'Monthly CSV Export Limit', PlanEntitlement.TYPE_UNLIMITED, None, True),
            ('view_contacts', 'Unmasked Corporate Direct Contacts', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('audit_packs', 'Section 135 Audit Packs', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('proposal_tools', 'AI CSR Pitch Generator', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('webhook_access', 'Webhook Alerts', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('custom_domain_monitoring', 'Custom Domain Monitoring', PlanEntitlement.TYPE_BOOLEAN, True, False),
            ('web_scraping', 'Dedicated Web Scraping Clusters', PlanEntitlement.TYPE_BOOLEAN, True, False),
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
