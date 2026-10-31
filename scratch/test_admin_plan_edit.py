import os
import sys

# Ensure current working directory is on sys.path
sys.path.insert(0, r"d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)")

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import Client
from modules.admin_panel.models import User, Plan

print("=" * 70)
print("VERIFICATION: ADMIN PANEL PLAN EDITING & DYNAMIC CUSTOMER SYNC")
print("=" * 70)

admin = User.objects.filter(is_superuser=True).first()
if not admin:
    print("ERROR: Superuser not found!")
    sys.exit(1)

client = Client()
client.force_login(admin)

# 1. Fetch Plan Edit Form
print("\n[1] Fetching PRO plan edit form from Admin Portal...")
res_get = client.get('/admin-portal/subscriptions/plans/pro/edit/')
print(f"  GET /admin-portal/subscriptions/plans/pro/edit/ -> HTTP {res_get.status_code}")
assert res_get.status_code == 200, "Plan edit form should return 200"

# 2. Update Plan via POST
print("\n[2] Updating PRO plan via Admin Portal form submission:")
print("  - New Monthly Price: Rs. 1,599.00 (was 1,499.00)")
print("  - New Yearly Price: Rs. 15,990.00 (was 14,990.00)")
print("  - New Saved Records Limit: 120 (was 100)")
print("  - New Monthly Export Limit: 250 (was 200)")

update_data = {
    'code': 'pro',
    'name': 'PRO',
    'slug': 'pro',
    'description': 'Advanced features for regular users, job seekers, researchers, and CSR professionals.',
    'badge': 'RECOMMENDED',
    'cta_text': 'Upgrade to Pro',
    'button_text': 'Upgrade to Pro',
    'billing_note': 'Billed monthly or annually (+18% GST)',
    'monthly_price_inr': '1599.0',
    'yearly_price_inr': '15990.0',
    'currency': 'INR',
    'is_active': 'on',
    'is_visible': 'on',
    'is_popular': 'on',
    'is_recommended': 'on',
    'display_order': '2',
    'trial_days': '14',
    'allow_upgrade': 'on',
    'allow_cancel': 'on',
    'auto_renew_default': 'on',
    'limit_saved_records': '120',
    'limit_saved_searches': '10',
    'limit_export_rows': '250',
    'limit_compare_companies': '10',
    'limit_seats': '1',
    'limit_alert_frequency': 'daily',
    'limit_advanced_filters': 'on',
    'features': "Everything in Free, plus:\nAdvanced search filters\nSave up to 120 records\nExport up to 250 records / month",
    'highlight_features': "120 Saved Records\n250 Exports / Month",
}

res_post = client.post('/admin-portal/subscriptions/plans/pro/edit/', data=update_data)
print(f"  POST update -> HTTP {res_post.status_code}")
assert res_post.status_code in (200, 302), f"Expected 200 or 302 redirect, got {res_post.status_code}"

# 3. Verify public API reflects the update immediately
print("\n[3] Checking Customer API (/api/subscription/plans)...")
res_api = client.get('/api/subscription/plans')
data = res_api.json()
pro_api = next((p for p in data['plans'] if p['code'] == 'pro'), None)

print(f"  API monthly_price: Rs. {pro_api['monthly_price']}")
print(f"  API yearly_price: Rs. {pro_api['yearly_price']}")
print(f"  API saved_records_limit: {pro_api['limits'].get('saved_records_limit')}")
print(f"  API export_rows_per_month: {pro_api['limits'].get('export_rows_per_month')}")

assert pro_api['monthly_price'] == 1599.0, f"Expected 1599.0, got {pro_api['monthly_price']}"
assert pro_api['yearly_price'] == 15990.0, f"Expected 15990.0, got {pro_api['yearly_price']}"
assert pro_api['limits'].get('saved_records_limit') == 120, "Expected saved_records_limit == 120"
assert pro_api['limits'].get('export_rows_per_month') == 250, "Expected export_rows_per_month == 250"
print("  SUCCESS: Customer API updated dynamically with zero hardcoded values!")

# 4. Check Comparison Table API
print("\n[4] Checking Dynamic Comparison API (/api/subscription/comparison)...")
res_comp = client.get('/api/subscription/comparison')
comp_data = res_comp.json()
exp_row = next((f for f in comp_data['features'] if f['feature_key'] == 'export_rows_per_month'), None)
print(f"  Comparison table export row for PRO: {exp_row['values']['pro']['value']}")
assert exp_row['values']['pro']['value'] == 250, f"Expected 250 in comparison table, got {exp_row['values']['pro']['value']}"

# 5. Restore baseline PRO values
print("\n[5] Restoring baseline PRO plan settings...")
update_data['monthly_price_inr'] = '1499.0'
update_data['yearly_price_inr'] = '14990.0'
update_data['limit_saved_records'] = '100'
update_data['limit_export_rows'] = '200'
update_data['features'] = "Everything in Free, plus:\nAdvanced search filters (Industry, Department, Experience, Focus)\nSave up to 100 combined jobs & CSR projects\nSave up to 10 search queries\nExport up to 200 records / month (CSV & Excel)\nDaily matching notifications\nDetailed company profiles & historical data\nCompare up to 10 companies\nAdvanced research dashboard"
update_data['highlight_features'] = "100 Saved Records\n200 Exports / Month\n10 Saved Searches\nCompany Comparison (10)"

client.post('/admin-portal/subscriptions/plans/pro/edit/', data=update_data)
res_restored = client.get('/api/subscription/plans').json()
pro_restored = next((p for p in res_restored['plans'] if p['code'] == 'pro'), None)
print(f"  Restored monthly: Rs. {pro_restored['monthly_price']}, export limit: {pro_restored['limits'].get('export_rows_per_month')}")
assert pro_restored['monthly_price'] == 1499.0
assert pro_restored['limits'].get('export_rows_per_month') == 200
print("  Restoration successful.")

print("\n" + "=" * 70)
print("ADMIN EDITING & CUSTOMER SYNC TEST COMPLETED SUCCESSFULLY!")
print("=" * 70)
