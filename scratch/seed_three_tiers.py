import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Plan, PlanEntitlement, Subscription

print("Starting three-tier subscription plan configuration...")

# 1. Archive legacy starter, enterprise, foundation from public view
legacy_codes = ['starter', 'enterprise', 'foundation']
for code in legacy_codes:
    p = Plan.objects.filter(code=code).first()
    if p:
        p.is_visible = False
        p.is_active = False
        p.save()
        print(f"Archived legacy plan: {code}")

# 2. Configure FREE plan
free_plan, _ = Plan.objects.update_or_create(
    code='free',
    defaults={
        'name': 'FREE',
        'slug': 'free',
        'description': 'Basic access for new users, students, job seekers, and casual researchers.',
        'badge': 'Free Forever',
        'cta_text': 'Get Started',
        'button_text': 'Get Started',
        'billing_note': 'No payment method required',
        'monthly_price_paise': 0,
        'yearly_price_paise': 0,
        'currency': 'INR',
        'is_active': True,
        'is_visible': True,
        'is_recommended': False,
        'is_popular': False,
        'display_order': 1,
        'trial_days': 0,
        'allow_upgrade': True,
        'allow_downgrade': False,
        'allow_cancel': True,
        'auto_renew_default': False,
        'features': [
            "Browse verified companies & CSR profiles",
            "Search job openings & CSR projects",
            "View job & project details and original links",
            "Save up to 10 combined jobs & CSR projects",
            "Save 1 custom search query",
            "Weekly email notifications",
            "Single user account"
        ],
        'highlight_features': [
            "10 Saved Records",
            "1 Saved Search",
            "Weekly Alerts"
        ],
        'limits': {
            'saved_records_limit': 10,
            'saved_searches_limit': 1,
            'export_rows_per_month': 0,
            'alert_frequency': 'weekly',
            'seats': 1,
            'compare_companies_limit': 0,
            'advanced_filters': False,
            'priority_support': False,
            'request_company_refresh': False
        }
    }
)
print("Configured FREE plan.")

# 3. Configure PRO plan (Admin-configurable monthly/yearly pricing)
pro_plan, _ = Plan.objects.update_or_create(
    code='pro',
    defaults={
        'name': 'PRO',
        'slug': 'pro',
        'description': 'Advanced discovery & outreach for regular users, job seekers, researchers, and CSR professionals.',
        'badge': 'RECOMMENDED',
        'cta_text': 'Upgrade to Pro',
        'button_text': 'Upgrade to Pro',
        'billing_note': 'Billed monthly or annually (+18% GST)',
        'monthly_price_paise': 149900,  # ₹1,499.00 initial admin-configurable default
        'yearly_price_paise': 1499000,  # ₹14,990.00 initial admin-configurable default (2 months free)
        'currency': 'INR',
        'is_active': True,
        'is_visible': True,
        'is_recommended': True,
        'is_popular': True,
        'display_order': 2,
        'trial_days': 14,
        'allow_upgrade': True,
        'allow_downgrade': False,
        'allow_cancel': True,
        'auto_renew_default': True,
        'savings_text': 'Save ₹2,998.00 / year (2 months free)',
        'features': [
            "Everything in Free, plus:",
            "Advanced search filters (Industry, Department, Experience, Focus)",
            "Save up to 100 combined jobs & CSR projects",
            "Save up to 10 search queries",
            "Export up to 200 records / month (CSV & Excel)",
            "Daily matching notifications",
            "Detailed company profiles & historical data",
            "Compare up to 10 companies",
            "Advanced research dashboard"
        ],
        'highlight_features': [
            "100 Saved Records",
            "200 Exports / Month",
            "10 Saved Searches",
            "Company Comparison (10)"
        ],
        'limits': {
            'saved_records_limit': 100,
            'saved_searches_limit': 10,
            'export_rows_per_month': 200,
            'alert_frequency': 'daily',
            'seats': 1,
            'compare_companies_limit': 10,
            'advanced_filters': True,
            'priority_support': False,
            'request_company_refresh': False
        }
    }
)
print("Configured PRO plan.")

# 4. Configure ULTRA plan (Admin-configurable monthly/yearly pricing)
ultra_plan, _ = Plan.objects.update_or_create(
    code='ultra',
    defaults={
        'name': 'ULTRA',
        'slug': 'ultra',
        'description': 'Premium intelligence suite for businesses, consultants, research teams, and non-profit organizations.',
        'badge': 'TEAMS & ORG',
        'cta_text': 'Upgrade to Ultra',
        'button_text': 'Upgrade to Ultra',
        'billing_note': 'Billed monthly or annually (+18% GST)',
        'monthly_price_paise': 499900,  # ₹4,999.00 initial admin-configurable default
        'yearly_price_paise': 4999000,  # ₹49,990.00 initial admin-configurable default (2 months free)
        'currency': 'INR',
        'is_active': True,
        'is_visible': True,
        'is_recommended': False,
        'is_popular': False,
        'display_order': 3,
        'trial_days': 14,
        'allow_upgrade': True,
        'allow_downgrade': False,
        'allow_cancel': True,
        'auto_renew_default': True,
        'savings_text': 'Save ₹9,998.00 / year (2 months free)',
        'features': [
            "Everything in Pro, plus:",
            "Unlimited saved jobs & CSR projects",
            "Save up to 50 search queries",
            "Bulk export up to 2,000 records / month (CSV & Excel)",
            "Custom alerts & instant matching notifications",
            "Advanced company comparison & intelligence",
            "Up to 3 team members (Owner + 2 members)",
            "Multi-company research workspace",
            "Priority dedicated support",
            "On-demand company data refresh requests"
        ],
        'highlight_features': [
            "Unlimited Saved Records",
            "2,000 Exports / Month",
            "3 Team Members",
            "Custom Alerts & Refresh Requests"
        ],
        'limits': {
            'saved_records_limit': None,
            'saved_searches_limit': 50,
            'export_rows_per_month': 2000,
            'alert_frequency': 'custom',
            'seats': 3,
            'compare_companies_limit': None,
            'advanced_filters': True,
            'priority_support': True,
            'request_company_refresh': True
        }
    }
)
print("Configured ULTRA plan.")

# 5. Populate the 16 structured PlanEntitlements for dynamic database-driven comparison
ENTITLEMENT_DEFINITIONS = [
    # (feature_key, display_name, free_val, pro_val, ultra_val)
    ('browse_companies', 'Browse available companies', (True, 'BOOLEAN'), (True, 'BOOLEAN'), (True, 'BOOLEAN')),
    ('view_job_csr_openings', 'View job openings & CSR projects', (True, 'BOOLEAN'), (True, 'BOOLEAN'), (True, 'BOOLEAN')),
    ('verified_portal_links', 'Verified official portal & career links', (True, 'BOOLEAN'), (True, 'BOOLEAN'), (True, 'BOOLEAN')),
    ('company_profiles', 'Company profile overview', ('Basic Overview', 'TEXT'), ('Detailed + History', 'TEXT'), ('Advanced + Insights', 'TEXT')),
    ('search_filters', 'Search & filter capabilities', ('Basic Filters', 'TEXT'), ('Advanced Filters', 'TEXT'), ('Advanced + Custom Filters', 'TEXT')),
    ('saved_records_limit', 'Saved jobs & CSR projects', (10, 'NUMERIC'), (100, 'NUMERIC'), (None, 'UNLIMITED')),
    ('saved_searches_limit', 'Saved search queries', (1, 'NUMERIC'), (10, 'NUMERIC'), (50, 'NUMERIC')),
    ('export_rows_per_month', 'Export data (CSV & Excel)', (0, 'NUMERIC'), (200, 'NUMERIC'), (2000, 'NUMERIC')),
    ('alert_notifications', 'Matching & alert notifications', ('Weekly Email', 'TEXT'), ('Daily Matching Alerts', 'TEXT'), ('Custom & Instant Alerts', 'TEXT')),
    ('company_comparison', 'Company comparison tool', (False, 'BOOLEAN'), ('Up to 10 Companies', 'TEXT'), ('Advanced Comparison', 'TEXT')),
    ('team_members', 'Team members / account seats', ('1 Member', 'TEXT'), ('1 Member', 'TEXT'), ('Up to 3 Team Members', 'TEXT')),
    ('data_refresh_requests', 'On-demand company data refresh', (False, 'BOOLEAN'), (False, 'BOOLEAN'), (True, 'BOOLEAN')),
    ('research_workspace', 'Research workspace', (False, 'BOOLEAN'), ('Advanced Dashboard', 'TEXT'), ('Multi-Company Workspace', 'TEXT')),
    ('support_level', 'Customer support', ('Community Support', 'TEXT'), ('Standard Email Support', 'TEXT'), ('Priority Dedicated Support', 'TEXT')),
    ('trial_period', 'Trial period', ('No Trial (Free)', 'TEXT'), ('14 Days Free Trial', 'TEXT'), ('14 Days Free Trial', 'TEXT')),
    ('billing_flexibility', 'Monthly & Annual billing', ('Free Forever', 'TEXT'), ('Monthly & Annual Savings', 'TEXT'), ('Monthly & Annual Savings', 'TEXT')),
]

for key, name, free_v, pro_v, ultra_v in ENTITLEMENT_DEFINITIONS:
    for plan, val_spec in [(free_plan, free_v), (pro_plan, pro_v), (ultra_plan, ultra_v)]:
        val, ftype = val_spec
        b_val = val if ftype == 'BOOLEAN' else False
        n_val = val if ftype == 'NUMERIC' else None
        t_val = val if ftype == 'TEXT' else None
        is_unl = ftype == 'UNLIMITED'
        
        PlanEntitlement.objects.update_or_create(
            plan=plan,
            feature_key=key,
            defaults={
                'display_name': name,
                'feature_type': ftype,
                'boolean_value': b_val,
                'numeric_value': n_val,
                'text_value': t_val,
                'is_unlimited': is_unl
            }
        )

print("Populated all 16 dynamic PlanEntitlements across Free, Pro, and Ultra.")

# 6. Seamlessly point existing starter subscriptions to free
updated_subs = Subscription.objects.filter(plan_id='starter').update(plan_id='free', plan_record=free_plan)
print(f"Updated {updated_subs} existing starter subscriptions to canonical 'free'.")

print("Seeding completed successfully.")

