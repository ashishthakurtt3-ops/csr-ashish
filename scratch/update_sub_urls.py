with open('modules/website/urls/subscription_urls.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Add imports
old_import = "    admin_run_renewals_now, admin_refund_payment\n)"
new_import = """    admin_run_renewals_now, admin_refund_payment,
    saved_records_api, saved_searches_api, team_members_api,
    company_refresh_api, subscription_comparison_api, user_quota_api
)"""

for le in ['\r\n', '\n']:
    tgt = old_import.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_import.replace('\n', le))
        print("Updated imports in subscription_urls.py")
        break
else:
    print("WARNING: Could not update imports in subscription_urls.py")

# Add new paths
new_paths = """
    # Dynamic Comparison & Entitlements
    path('api/subscription/comparison', subscription_comparison_api, name='subscription_comparison'),
    path('api/subscription/comparison/', subscription_comparison_api, name='subscription_comparison_slash'),

    # User Limits & Quotas
    path('api/user/quotas', user_quota_api, name='user_quotas'),
    path('api/user/quotas/', user_quota_api, name='user_quotas_slash'),

    # Saved Records & Searches (User features)
    path('api/user/saved-records', saved_records_api, name='user_saved_records'),
    path('api/user/saved-records/', saved_records_api, name='user_saved_records_slash'),
    path('api/user/saved-searches', saved_searches_api, name='user_saved_searches'),
    path('api/user/saved-searches/', saved_searches_api, name='user_saved_searches_slash'),

    # Ultra features: Team & Refresh
    path('api/user/team', team_members_api, name='user_team_members'),
    path('api/user/team/', team_members_api, name='user_team_members_slash'),
    path('api/user/company-refresh', company_refresh_api, name='user_company_refresh'),
    path('api/user/company-refresh/', company_refresh_api, name='user_company_refresh_slash'),
]"""

if "path('api/subscription/comparison'" not in c:
    # replace the closing bracket
    c = c.rstrip()
    if c.endswith(']'):
        c = c[:-1] + new_paths
        print("Appended new url paths to subscription_urls.py")

with open('modules/website/urls/subscription_urls.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done updating subscription_urls.py")

