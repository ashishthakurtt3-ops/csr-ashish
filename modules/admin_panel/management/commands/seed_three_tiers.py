"""
Idempotent three-tier subscription seeder.

Creates/updates exactly 3 customer-facing plans: FREE, PRO, ULTRA.
Archives legacy plans safely. Preserves all existing subscriptions,
payments, invoices, wallet balances, and historical records.

Usage: python manage.py seed_three_tiers
Re-run safely: idempotent (update_or_create on plan code).
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from modules.admin_panel.models import (
    Plan, PlanEntitlement, Subscription, SubscriptionEvent
)
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed or update the three-tier subscription plans (FREE, PRO, ULTRA)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Three-Tier Subscription Plan Seeder'
        ))
        self.stdout.write('')

        # ── STEP 1: Archive legacy plans ──────────────────────────────
        # Do NOT delete them — they have historical payment/invoice references.
        # Just hide from customer-facing views.
        legacy_codes = ['starter', 'enterprise', 'foundation']
        for code in legacy_codes:
            plan = Plan.objects.filter(code=code).first()
            if plan:
                changed = []
                if plan.is_visible:
                    plan.is_visible = False
                    changed.append('is_visible=False')
                if plan.is_active:
                    plan.is_active = False
                    changed.append('is_active=False')
                if changed:
                    plan.save()
                    self.stdout.write(
                        f"  Archived legacy plan '{code}': {', '.join(changed)}"
                    )
                else:
                    self.stdout.write(
                        f"  Legacy plan '{code}' already archived."
                    )

        # ── STEP 2: Create/Update FREE plan ───────────────────────────
        free_plan, free_created = Plan.objects.update_or_create(
            code='free',
            defaults={
                'name': 'FREE',
                'slug': 'free',
                'description': (
                    '14-Day evaluation access to verified corporate profiles, '
                    'active career opportunities, and Section 135 CSR projects.'
                ),
                'badge': '14-Day Free Trial',
                'cta_text': 'Start 14-Day Free Trial',
                'button_text': 'Start 14-Day Free Trial',
                'billing_note': '14-Day Free Trial • No credit card required',
                'monthly_price_paise': 0,
                'yearly_price_paise': 0,
                'currency': 'INR',
                'is_active': True,
                'is_visible': True,
                'is_recommended': False,
                'is_popular': False,
                'display_order': 1,
                'trial_days': 14,
                'allow_upgrade': True,
                'allow_downgrade': False,
                'allow_cancel': True,
                'auto_renew_default': False,
                'features': [
                    "Browse up to 20 verified companies & portals",
                    "Search active corporate vacancies & Section 135 projects",
                    "View verified job & CSR details and original portal links",
                    "Save up to 20 combined companies, jobs & CSR projects",
                    "Export up to 20 records / month (CSV & Excel)",
                    "Save 1 custom search query",
                    "Weekly job & CSR alert notifications",
                    "Single user account",
                ],
                'highlight_features': [
                    "20 Verified Companies",
                    "20 Saved Records",
                    "20 Exports / Month",
                    "14-Day Free Trial",
                ],
                'limits': {
                    'browse_companies_limit': 20,
                    'saved_records_limit': 20,
                    'saved_searches_limit': 1,
                    'export_rows_per_month': 20,
                    'alert_frequency': 'weekly',
                    'seats': 1,
                    'compare_companies_limit': 0,
                    'advanced_filters': False,
                    'priority_support': False,
                    'request_company_refresh': False,
                },
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f"  {'Created' if free_created else 'Updated'} FREE plan (code='free')"
        ))

        # ── STEP 3: Update PRO plan in-place ──────────────────────────
        # PRO already exists with code='pro'. We update it to match the
        # new three-tier spec. No active subscriptions to worry about.
        # Pricing fields are set to sensible initial defaults but remain
        # fully admin-configurable from the Admin Panel.
        pro_plan, pro_created = Plan.objects.update_or_create(
            code='pro',
            defaults={
                'name': 'PRO',
                'slug': 'pro',
                'description': (
                    'Advanced features for active professionals, job seekers, '
                    'corporate researchers, and Section 135 CSR teams.'
                ),
                'badge': 'RECOMMENDED',
                'cta_text': 'Upgrade to Pro',
                'button_text': 'Upgrade to Pro',
                'billing_note': 'Billed monthly or annually (+18% GST) • Instant activation',
                # Initial admin-configurable defaults — NOT hardcoded final prices
                'monthly_price_paise': 99900,   # Rs 999 — change in Admin Panel
                'yearly_price_paise': 999000,   # Rs 9,990 — change in Admin Panel
                'currency': 'INR',
                'is_active': True,
                'is_visible': True,
                'is_recommended': True,
                'is_popular': True,
                'display_order': 2,
                'trial_days': 0,
                'allow_upgrade': True,
                'allow_downgrade': False,
                'allow_cancel': True,
                'auto_renew_default': True,
                'features': [
                    "Everything in Free, plus:",
                    "Browse up to 100 verified companies & portals",
                    "Save up to 100 combined companies, jobs & CSR projects",
                    "Export up to 100 records / month (CSV & Excel)",
                    "On-demand company crawler rescan requests",
                    "Advanced multi-dimensional search filters",
                    "Save up to 10 search queries",
                    "Daily matching notifications",
                    "Detailed company profiles & historical data",
                    "Compare up to 10 companies side-by-side",
                ],
                'highlight_features': [
                    "100 Verified Companies",
                    "100 Saved Records",
                    "100 Exports / Month",
                    "Crawler Rescan Enabled",
                ],
                'limits': {
                    'browse_companies_limit': 100,
                    'saved_records_limit': 100,
                    'saved_searches_limit': 10,
                    'export_rows_per_month': 100,
                    'alert_frequency': 'daily',
                    'seats': 1,
                    'compare_companies_limit': 10,
                    'advanced_filters': True,
                    'priority_support': False,
                    'request_company_refresh': True,
                },
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f"  {'Created' if pro_created else 'Updated'} PRO plan (code='pro')"
        ))

        # ── STEP 4: Create/Update ULTRA plan ──────────────────────────
        ultra_plan, ultra_created = Plan.objects.update_or_create(
            code='ultra',
            defaults={
                'name': 'ULTRA',
                'slug': 'ultra',
                'description': (
                    'Unlimited institutional intelligence for businesses, consultants, '
                    'research teams, and organizations.'
                ),
                'badge': 'TEAMS & ORG',
                'cta_text': 'Upgrade to Ultra',
                'button_text': 'Upgrade to Ultra',
                'billing_note': 'Billed monthly or annually (+18% GST) • Instant activation',
                # Initial admin-configurable defaults — NOT hardcoded final prices
                'monthly_price_paise': 199900,   # Rs 1,999 — change in Admin Panel
                'yearly_price_paise': 1999000,   # Rs 19,990 — change in Admin Panel
                'currency': 'INR',
                'is_active': True,
                'is_visible': True,
                'is_recommended': False,
                'is_popular': False,
                'display_order': 3,
                'trial_days': 0,
                'allow_upgrade': True,
                'allow_downgrade': False,
                'allow_cancel': True,
                'auto_renew_default': True,
                'features': [
                    "Everything in Pro, plus:",
                    "Browse full directory of all verified companies & corporate portals",
                    "Unlimited saved companies, jobs & CSR projects",
                    "Unlimited bulk data exports (CSV & Excel)",
                    "On-demand company crawler rescan requests",
                    "Save up to 50 search queries",
                    "Custom & instant real-time alert notifications",
                    "Comprehensive multi-company comparison tool",
                    "Up to 3 team members (Owner + 2 members)",
                    "Multi-company research workspace",
                    "Priority Dedicated Support 24/7",
                ],
                'highlight_features': [
                    "All Companies (Full Access)",
                    "Unlimited Saved Records",
                    "Unlimited Exports",
                    "Crawler Rescan Enabled",
                ],
                'limits': {
                    'browse_companies_limit': None,   # Unlimited (All companies)
                    'saved_records_limit': None,      # Unlimited
                    'saved_searches_limit': 50,
                    'export_rows_per_month': None,    # Unlimited
                    'alert_frequency': 'custom',
                    'seats': 3,
                    'compare_companies_limit': None,  # Unlimited
                    'advanced_filters': True,
                    'priority_support': True,
                    'request_company_refresh': True,
                },
            }
        )
        self.stdout.write(self.style.SUCCESS(
            f"  {'Created' if ultra_created else 'Updated'} ULTRA plan (code='ultra')"
        ))

        # ── STEP 5: Populate PlanEntitlements for comparison table ─────
        # These drive the dynamic comparison table in the customer portal.
        # 17 rows x 3 plans = 51 entitlement records.
        ENTITLEMENTS = [
            # (feature_key, display_name,
            #   free_spec, pro_spec, ultra_spec)
            # Each spec is (value, type) where type is one of:
            #   BOOLEAN, NUMERIC, UNLIMITED, TEXT
            ('browse_companies', 'Browse verified companies & portals',
                (20, 'NUMERIC'), (100, 'NUMERIC'), (None, 'UNLIMITED')),
            ('view_job_csr_openings', 'View job openings & CSR projects',
                (True, 'BOOLEAN'), (True, 'BOOLEAN'), (True, 'BOOLEAN')),
            ('verified_portal_links', 'Verified official portal & career links',
                (True, 'BOOLEAN'), (True, 'BOOLEAN'), (True, 'BOOLEAN')),
            ('company_profiles', 'Company profile depth',
                ('Basic Overview', 'TEXT'),
                ('Detailed + History', 'TEXT'),
                ('Advanced + Insights', 'TEXT')),
            ('search_filters', 'Search & filter capabilities',
                ('Basic Filters', 'TEXT'),
                ('Advanced Filters', 'TEXT'),
                ('Advanced + Custom Filters', 'TEXT')),
            ('saved_records_limit', 'Saved companies, jobs & CSR projects',
                (20, 'NUMERIC'), (100, 'NUMERIC'), (None, 'UNLIMITED')),
            ('saved_searches_limit', 'Saved search queries',
                (1, 'NUMERIC'), (10, 'NUMERIC'), (50, 'NUMERIC')),
            ('export_rows_per_month', 'Export data (CSV & Excel)',
                (20, 'NUMERIC'), (100, 'NUMERIC'), (None, 'UNLIMITED')),
            ('crawler_rescan', 'On-demand crawler rescan requests',
                (False, 'BOOLEAN'), (True, 'BOOLEAN'), (True, 'BOOLEAN')),
            ('alert_notifications', 'Matching & alert notifications',
                ('Weekly Email', 'TEXT'),
                ('Daily Matching Alerts', 'TEXT'),
                ('Custom & Instant Alerts', 'TEXT')),
            ('company_comparison', 'Company comparison tool',
                (False, 'BOOLEAN'),
                ('Up to 10 Companies', 'TEXT'),
                ('Advanced Comparison', 'TEXT')),
            ('team_members', 'Team members / account seats',
                ('1 Member', 'TEXT'),
                ('1 Member', 'TEXT'),
                ('Up to 3 Team Members', 'TEXT')),
            ('data_refresh_requests', 'On-demand company data refresh',
                (False, 'BOOLEAN'), (True, 'BOOLEAN'), (True, 'BOOLEAN')),
            ('research_workspace', 'Research workspace',
                (False, 'BOOLEAN'),
                ('Advanced Dashboard', 'TEXT'),
                ('Multi-Company Workspace', 'TEXT')),
            ('support_level', 'Customer support',
                ('Community Support', 'TEXT'),
                ('Standard Email Support', 'TEXT'),
                ('Priority Dedicated Support', 'TEXT')),
            ('trial_period', 'Trial period',
                ('14 Days Free Trial', 'TEXT'),
                ('No Trial', 'TEXT'),
                ('No Trial', 'TEXT')),
            ('billing_flexibility', 'Billing options',
                ('14-Day Free Evaluation', 'TEXT'),
                ('Monthly & Annual Billing', 'TEXT'),
                ('Monthly & Annual Billing', 'TEXT')),
        ]

        created_count = 0
        updated_count = 0

        for key, name, free_spec, pro_spec, ultra_spec in ENTITLEMENTS:
            for plan_obj, (val, ftype) in [
                (free_plan, free_spec),
                (pro_plan, pro_spec),
                (ultra_plan, ultra_spec),
            ]:
                _, ent_created = PlanEntitlement.objects.update_or_create(
                    plan=plan_obj,
                    feature_key=key,
                    defaults={
                        'display_name': name,
                        'feature_type': ftype,
                        'boolean_value': val if ftype == 'BOOLEAN' else False,
                        'numeric_value': val if ftype == 'NUMERIC' else None,
                        'text_value': val if ftype == 'TEXT' else None,
                        'is_unlimited': ftype == 'UNLIMITED',
                    }
                )
                if ent_created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"  Entitlements: {created_count} created, {updated_count} updated "
            f"(3 plans x {len(ENTITLEMENTS)} features)"
        ))

        # ── STEP 6: Migrate existing subscriptions ────────────────────
        # starter -> free (preserving subscription_id, tenant, etc.)
        starter_subs = Subscription.objects.filter(plan_id='starter')
        if starter_subs.exists():
            count = starter_subs.count()
            starter_subs.update(plan_id='free', plan_record=free_plan)
            self.stdout.write(self.style.WARNING(
                f"  Migrated {count} 'starter' subscription(s) -> 'free'"
            ))
            # Log event
            for sub in Subscription.objects.filter(plan_id='free'):
                SubscriptionEvent.objects.create(
                    subscription_id=sub.subscription_id,
                    tenant_id=sub.tenant_id,
                    event_type='PLAN_MIGRATION',
                    from_plan='starter',
                    to_plan='free',
                    notes='Automatic migration to new three-tier structure (FREE/PRO/ULTRA)',
                    actor='system:seed_three_tiers',
                    created_at=timezone.now().isoformat(),
                )

        # foundation -> ultra
        foundation_subs = Subscription.objects.filter(plan_id='foundation')
        if foundation_subs.exists():
            count = foundation_subs.count()
            foundation_subs.update(plan_id='ultra', plan_record=ultra_plan)
            self.stdout.write(self.style.WARNING(
                f"  Migrated {count} 'foundation' subscription(s) -> 'ultra'"
            ))
            for sub in Subscription.objects.filter(
                plan_id='ultra',
                plan_record=ultra_plan
            ):
                SubscriptionEvent.objects.create(
                    subscription_id=sub.subscription_id,
                    tenant_id=sub.tenant_id,
                    event_type='PLAN_MIGRATION',
                    from_plan='foundation',
                    to_plan='ultra',
                    notes='Automatic migration to new three-tier structure (FREE/PRO/ULTRA)',
                    actor='system:seed_three_tiers',
                    created_at=timezone.now().isoformat(),
                )

        # enterprise -> ultra (if any exist)
        enterprise_subs = Subscription.objects.filter(plan_id='enterprise')
        if enterprise_subs.exists():
            count = enterprise_subs.count()
            enterprise_subs.update(plan_id='ultra', plan_record=ultra_plan)
            self.stdout.write(self.style.WARNING(
                f"  Migrated {count} 'enterprise' subscription(s) -> 'ultra'"
            ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Seeding completed successfully.'))

        # ── STEP 7: Final verification output ─────────────────────────
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Final Plan Configuration'
        ))
        for plan in Plan.objects.filter(
            is_active=True, is_visible=True
        ).order_by('display_order'):
            monthly_rs = plan.monthly_price_paise / 100
            yearly_rs = plan.yearly_price_paise / 100
            self.stdout.write(
                f"  [{plan.display_order}] {plan.name} (code={plan.code!r})"
            )
            self.stdout.write(
                f"      Monthly: Rs {monthly_rs:,.2f}  |  "
                f"Yearly: Rs {yearly_rs:,.2f}"
            )
            self.stdout.write(
                f"      Badge: {plan.badge}  |  "
                f"Recommended: {plan.is_recommended}"
            )
            limits = plan.limits or {}
            self.stdout.write(f"      Limits: {limits}")
            ent_count = plan.entitlements.count()
            self.stdout.write(f"      Entitlements: {ent_count} configured")
            subs = Subscription.objects.filter(
                Q(plan_id=plan.code) | Q(plan_record=plan)
            ).distinct().count()
            self.stdout.write(f"      Active subscribers: {subs}")
            self.stdout.write('')

