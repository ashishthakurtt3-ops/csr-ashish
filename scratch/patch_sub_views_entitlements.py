path = r'modules\admin_panel\views\subscription_views.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

old_block = """        # Update structured entitlements
        entitlements_spec = [
            ('saved_records_limit', 'Saved Jobs & CSR Projects', PlanEntitlement.TYPE_UNLIMITED if saved_records_val is None else PlanEntitlement.TYPE_NUMERIC, saved_records_val, saved_records_val is None),
            ('saved_searches_limit', 'Saved Search Queries', PlanEntitlement.TYPE_UNLIMITED if saved_searches_val is None else PlanEntitlement.TYPE_NUMERIC, saved_searches_val, saved_searches_val is None),
            ('compare_companies_limit', 'Company Comparison Limit', PlanEntitlement.TYPE_UNLIMITED if compare_companies_val is None else PlanEntitlement.TYPE_NUMERIC, compare_companies_val, compare_companies_val is None),
            ('alert_notifications', 'Matching & Alert Notifications', PlanEntitlement.TYPE_TEXT, f"{alert_freq.title()} Alerts", False),
            ('search_filters', 'Search & Filter Capabilities', PlanEntitlement.TYPE_TEXT, 'Advanced Filters' if adv_filters else 'Basic Filters', False),
            ('data_refresh_requests', 'On-Demand Data Refresh', PlanEntitlement.TYPE_BOOLEAN, refresh_req, False),
            ('support_level', 'Customer Support Level', PlanEntitlement.TYPE_TEXT, 'Priority Dedicated Support' if prio_support else 'Standard Support', False),
            ('daily_matches', 'Daily Matchmaker Queries', PlanEntitlement.TYPE_UNLIMITED if daily_matches_val is None else PlanEntitlement.TYPE_NUMERIC, daily_matches_val, daily_matches_val is None),
            ('api_access', 'REST API Access', PlanEntitlement.TYPE_BOOLEAN, api_access, False),
            ('live_reprobe', 'Live Domain Socket Probing', PlanEntitlement.TYPE_BOOLEAN, live_reprobe, False),
            ('view_contacts', 'Unmasked Corporate Direct Contacts', PlanEntitlement.TYPE_BOOLEAN, view_contacts, False),
            ('audit_packs', 'Section 135 Audit Packs', PlanEntitlement.TYPE_BOOLEAN, audit_packs, False),
            ('seats', 'Team Seats', PlanEntitlement.TYPE_NUMERIC, seats, False),
            ('export_rows_per_month', 'Monthly CSV Export Rows', PlanEntitlement.TYPE_UNLIMITED if export_rows_val is None else PlanEntitlement.TYPE_NUMERIC, export_rows_val, export_rows_val is None),
            ('crm_limit', 'Outreach CRM Pipeline Limit', PlanEntitlement.TYPE_NUMERIC, crm_limit, False),
            ('jobs', 'Jobs Limit', PlanEntitlement.TYPE_UNLIMITED if jobs_val is None else PlanEntitlement.TYPE_NUMERIC, jobs_val, jobs_val is None),
            ('api_requests', 'API Requests Limit', PlanEntitlement.TYPE_UNLIMITED if api_req_val is None else PlanEntitlement.TYPE_NUMERIC, api_req_val, api_req_val is None),
            ('credits', 'Credits Limit', PlanEntitlement.TYPE_UNLIMITED if credits_val is None else PlanEntitlement.TYPE_NUMERIC, credits_val, credits_val is None),
            ('search_limit', 'Search Queries Limit', PlanEntitlement.TYPE_UNLIMITED if search_val is None else PlanEntitlement.TYPE_NUMERIC, search_val, search_val is None),
            ('storage', 'Storage Allowance', PlanEntitlement.TYPE_TEXT, storage_val, False),
        ]"""

new_block = """        # Update structured entitlements (strictly canonical 16-row keys)
        entitlements_spec = [
            ('saved_records_limit', 'Saved jobs & CSR projects', PlanEntitlement.TYPE_UNLIMITED if saved_records_val is None else PlanEntitlement.TYPE_NUMERIC, saved_records_val, saved_records_val is None),
            ('saved_searches_limit', 'Saved search queries', PlanEntitlement.TYPE_UNLIMITED if saved_searches_val is None else PlanEntitlement.TYPE_NUMERIC, saved_searches_val, saved_searches_val is None),
            ('export_rows_per_month', 'Export data (CSV & Excel)', PlanEntitlement.TYPE_UNLIMITED if export_rows_val is None else PlanEntitlement.TYPE_NUMERIC, export_rows_val, export_rows_val is None),
            ('company_comparison', 'Company comparison tool', PlanEntitlement.TYPE_TEXT, (f"Up to {compare_companies_val} Companies" if compare_companies_val else "Advanced Comparison") if compare_companies_val != 0 else False, False),
            ('alert_notifications', 'Matching & alert notifications', PlanEntitlement.TYPE_TEXT, f"{alert_freq.title()} Alerts", False),
            ('search_filters', 'Search & filter capabilities', PlanEntitlement.TYPE_TEXT, 'Advanced Filters' if adv_filters else 'Basic Filters', False),
            ('data_refresh_requests', 'On-demand company data refresh', PlanEntitlement.TYPE_BOOLEAN, refresh_req, False),
            ('support_level', 'Customer support', PlanEntitlement.TYPE_TEXT, 'Priority Dedicated Support' if prio_support else 'Standard Email Support', False),
            ('team_members', 'Team members / account seats', PlanEntitlement.TYPE_TEXT, f"Up to {seats} Team Members" if seats > 1 else "1 Member", False),
        ]"""

assert old_block in text, 'old_block not found!'
text = text.replace(old_block, new_block, 1)

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(text)

print('Successfully updated subscription_views.py entitlements_spec')

