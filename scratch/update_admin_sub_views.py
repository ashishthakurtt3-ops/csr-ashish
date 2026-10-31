with open('modules/admin_panel/views/subscription_views.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Let's add the extraction of the 3-tier limits
old_limits_code = """        # Limits / entitlements
        daily_matches = request.POST.get('limit_daily_matches')"""

new_limits_code = """        # Limits / entitlements (Three-Tier Plan Configuration)
        saved_records = request.POST.get('limit_saved_records')
        saved_records_val = None if saved_records in ('', 'None', 'unlimited') else int(saved_records)

        saved_searches = request.POST.get('limit_saved_searches')
        saved_searches_val = None if saved_searches in ('', 'None', 'unlimited') else int(saved_searches)

        compare_companies = request.POST.get('limit_compare_companies')
        compare_companies_val = None if compare_companies in ('', 'None', 'unlimited') else int(compare_companies)

        alert_freq = str(request.POST.get('limit_alert_frequency') or 'weekly').strip().lower()
        adv_filters = bool(request.POST.get('limit_advanced_filters'))
        prio_support = bool(request.POST.get('limit_priority_support'))
        refresh_req = bool(request.POST.get('limit_request_company_refresh'))

        daily_matches = request.POST.get('limit_daily_matches')"""

for le in ['\r\n', '\n']:
    tgt = old_limits_code.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_limits_code.replace('\n', le))
        print("Updated limit extractions in subscription_views.py")
        break
else:
    print("WARNING: Could not update limit extractions in subscription_views.py")

# Update limits_dict
old_dict = """        limits_dict = {
            'daily_matches': daily_matches_val,"""

new_dict = """        limits_dict = {
            'saved_records_limit': saved_records_val,
            'saved_searches_limit': saved_searches_val,
            'compare_companies_limit': compare_companies_val,
            'alert_frequency': alert_freq,
            'advanced_filters': adv_filters,
            'priority_support': prio_support,
            'request_company_refresh': refresh_req,
            'daily_matches': daily_matches_val,"""

for le in ['\r\n', '\n']:
    tgt = old_dict.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_dict.replace('\n', le))
        print("Updated limits_dict in subscription_views.py")
        break
else:
    print("WARNING: Could not update limits_dict in subscription_views.py")

# Update entitlements_spec
old_spec = """        entitlements_spec = [
            ('daily_matches', 'Daily Matchmaker Queries',"""

new_spec = """        entitlements_spec = [
            ('saved_records_limit', 'Saved Jobs & CSR Projects', PlanEntitlement.TYPE_UNLIMITED if saved_records_val is None else PlanEntitlement.TYPE_NUMERIC, saved_records_val, saved_records_val is None),
            ('saved_searches_limit', 'Saved Search Queries', PlanEntitlement.TYPE_UNLIMITED if saved_searches_val is None else PlanEntitlement.TYPE_NUMERIC, saved_searches_val, saved_searches_val is None),
            ('compare_companies_limit', 'Company Comparison Limit', PlanEntitlement.TYPE_UNLIMITED if compare_companies_val is None else PlanEntitlement.TYPE_NUMERIC, compare_companies_val, compare_companies_val is None),
            ('alert_notifications', 'Matching & Alert Notifications', PlanEntitlement.TYPE_TEXT, f"{alert_freq.title()} Alerts", False),
            ('search_filters', 'Search & Filter Capabilities', PlanEntitlement.TYPE_TEXT, 'Advanced Filters' if adv_filters else 'Basic Filters', False),
            ('data_refresh_requests', 'On-Demand Data Refresh', PlanEntitlement.TYPE_BOOLEAN, refresh_req, False),
            ('support_level', 'Customer Support Level', PlanEntitlement.TYPE_TEXT, 'Priority Dedicated Support' if prio_support else 'Standard Support', False),
            ('daily_matches', 'Daily Matchmaker Queries',"""

for le in ['\r\n', '\n']:
    tgt = old_spec.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_spec.replace('\n', le))
        print("Updated entitlements_spec in subscription_views.py")
        break
else:
    print("WARNING: Could not update entitlements_spec in subscription_views.py")

with open('modules/admin_panel/views/subscription_views.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done updating subscription_views.py")

