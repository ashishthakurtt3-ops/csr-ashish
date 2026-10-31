with open('modules/admin_panel/views/subscription_views.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_block = """        # Limits / entitlements (Three-Tier Plan Configuration)
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

        daily_matches = request.POST.get('limit_daily_matches')
        daily_matches_val = None if daily_matches in ('', 'None', 'unlimited') else int(daily_matches)
        api_access = bool(request.POST.get('limit_api_access'))
        live_reprobe = bool(request.POST.get('limit_live_reprobe'))
        view_contacts = bool(request.POST.get('limit_view_contacts'))
        audit_packs = bool(request.POST.get('limit_audit_packs'))
        seats = int(request.POST.get('limit_seats') or 1)
        export_rows = request.POST.get('limit_export_rows')
        export_rows_val = None if export_rows in ('', 'None', 'unlimited') else int(export_rows)
        crm_limit = int(request.POST.get('limit_crm') or 10)

        jobs_raw = request.POST.get('limit_jobs')
        jobs_val = None if jobs_raw in ('', 'None', 'unlimited') else int(jobs_raw)

        api_req_raw = request.POST.get('limit_api_requests')
        api_req_val = None if api_req_raw in ('', 'None', 'unlimited') else int(api_req_raw)

        storage_val = request.POST.get('limit_storage', '').strip() or '10 GB'

        credits_raw = request.POST.get('limit_credits')
        credits_val = None if credits_raw in ('', 'None', 'unlimited') else int(credits_raw)

        search_raw = request.POST.get('limit_search')
        search_val = None if search_raw in ('', 'None', 'unlimited') else int(search_raw)

        export_limit_raw = request.POST.get('limit_export')
        export_limit_val = None if export_limit_raw in ('', 'None', 'unlimited') else int(export_limit_raw)"""

new_block = """        # Safe numeric parser for optional plan limits
        def _parse_opt_int(val):
            if val is None:
                return None
            val_str = str(val).strip()
            if val_str in ('', 'None', 'unlimited', 'null'):
                return None
            try:
                return int(val_str)
            except ValueError:
                return None

        # Limits / entitlements (Three-Tier Plan Configuration)
        saved_records_val = _parse_opt_int(request.POST.get('limit_saved_records'))
        saved_searches_val = _parse_opt_int(request.POST.get('limit_saved_searches'))
        compare_companies_val = _parse_opt_int(request.POST.get('limit_compare_companies'))

        alert_freq = str(request.POST.get('limit_alert_frequency') or 'weekly').strip().lower()
        adv_filters = bool(request.POST.get('limit_advanced_filters'))
        prio_support = bool(request.POST.get('limit_priority_support'))
        refresh_req = bool(request.POST.get('limit_request_company_refresh'))

        daily_matches_val = _parse_opt_int(request.POST.get('limit_daily_matches'))
        api_access = bool(request.POST.get('limit_api_access'))
        live_reprobe = bool(request.POST.get('limit_live_reprobe'))
        view_contacts = bool(request.POST.get('limit_view_contacts'))
        audit_packs = bool(request.POST.get('limit_audit_packs'))
        seats = _parse_opt_int(request.POST.get('limit_seats')) or 1
        export_rows_val = _parse_opt_int(request.POST.get('limit_export_rows'))
        crm_limit = _parse_opt_int(request.POST.get('limit_crm')) or 10

        jobs_val = _parse_opt_int(request.POST.get('limit_jobs'))
        api_req_val = _parse_opt_int(request.POST.get('limit_api_requests'))
        storage_val = request.POST.get('limit_storage', '').strip() or '10 GB'
        credits_val = _parse_opt_int(request.POST.get('limit_credits'))
        search_val = _parse_opt_int(request.POST.get('limit_search'))
        export_limit_val = _parse_opt_int(request.POST.get('limit_export'))"""

for le in ['\r\n', '\n']:
    tgt = old_block.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_block.replace('\n', le))
        print("Updated limits parsing in subscription_views.py with safe helper")
        break
else:
    print("WARNING: Could not update limits parsing in subscription_views.py")

with open('modules/admin_panel/views/subscription_views.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done")

