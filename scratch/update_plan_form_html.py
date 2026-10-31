with open('templates/admin/subscriptions/plan_form.html', 'r', encoding='utf-8') as f:
    c = f.read()

old_sec5 = """        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:16px;">
            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Jobs Limit</label>
                <input type="text" id="field-limit_jobs" name="limit_jobs" value="{{ limits.jobs|default:'' }}" placeholder="e.g. 100 or unlimited"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>

            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">API Requests Limit</label>
                <input type="text" id="field-limit_api_requests" name="limit_api_requests" value="{{ limits.api_requests|default:'' }}" placeholder="e.g. 5000 or unlimited"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>

            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Storage Allowance</label>
                <input type="text" id="field-limit_storage" name="limit_storage" value="{{ limits.storage|default:'10 GB' }}" placeholder="e.g. 10 GB"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>

            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Credits Limit</label>
                <input type="text" id="field-limit_credits" name="limit_credits" value="{{ limits.credits|default:'' }}" placeholder="e.g. 500 or unlimited"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>

            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Search Queries Limit</label>
                <input type="text" id="field-limit_search" name="limit_search" value="{{ limits.search_limit|default:'' }}" placeholder="e.g. 200 or unlimited"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>

            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Export Limit (Rows)</label>
                <input type="text" id="field-limit_export" name="limit_export" value="{{ limits.export_limit|default:limits.export_rows_per_month|default:'' }}" placeholder="e.g. 1000 or unlimited"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>
        </div>"""

new_sec5 = """        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:16px;">
            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Saved Jobs &amp; CSR Projects</label>
                <input type="text" id="field-limit_saved_records" name="limit_saved_records" value="{{ limits.saved_records_limit|default:'' }}" placeholder="e.g. 10, 100 or unlimited"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>

            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Saved Search Queries</label>
                <input type="text" id="field-limit_saved_searches" name="limit_saved_searches" value="{{ limits.saved_searches_limit|default:'' }}" placeholder="e.g. 1, 10 or 50"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>

            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Monthly Export Quota (Rows)</label>
                <input type="text" id="field-limit_export_rows" name="limit_export_rows" value="{{ limits.export_rows_per_month|default:'' }}" placeholder="e.g. 0, 200 or 2000"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>

            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Company Comparison Limit</label>
                <input type="text" id="field-limit_compare_companies" name="limit_compare_companies" value="{{ limits.compare_companies_limit|default:'' }}" placeholder="e.g. 0, 10 or unlimited"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>

            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Team Member Seats (Max)</label>
                <input type="number" id="field-limit_seats" name="limit_seats" value="{{ limits.seats|default:'1' }}" min="1" max="50"
                       style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
            </div>

            <div>
                <label style="display:block; font-size:12px; font-weight:600; color:var(--admin-muted); margin-bottom:6px;">Alert Frequency</label>
                <select id="field-limit_alert_frequency" name="limit_alert_frequency" style="width:100%; box-sizing:border-box; padding:9px 12px; background:rgba(30,41,59,0.6); border:1px solid var(--admin-border); border-radius:6px; color:#fff; font-size:13px;">
                    <option value="weekly" {% if limits.alert_frequency == 'weekly' %}selected{% endif %}>Weekly Alerts (Free)</option>
                    <option value="daily" {% if limits.alert_frequency == 'daily' %}selected{% endif %}>Daily Alerts (Pro)</option>
                    <option value="custom" {% if limits.alert_frequency == 'custom' %}selected{% endif %}>Custom / Real-Time Alerts (Ultra)</option>
                </select>
            </div>
        </div>

        <div style="display:flex; gap:20px; flex-wrap:wrap; margin-top:16px; padding:14px; background:rgba(15,23,42,0.5); border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
            <label style="display:flex; align-items:center; gap:8px; font-size:13px; color:#fff; cursor:pointer;">
                <input type="checkbox" id="field-limit_advanced_filters" name="limit_advanced_filters" {% if limits.advanced_filters %}checked{% endif %} style="width:16px; height:16px;">
                <span>Advanced Search Filters (Industry, Dept, Exp, Focus)</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; font-size:13px; color:#fff; cursor:pointer;">
                <input type="checkbox" id="field-limit_priority_support" name="limit_priority_support" {% if limits.priority_support %}checked{% endif %} style="width:16px; height:16px;">
                <span>Priority Dedicated Support</span>
            </label>
            <label style="display:flex; align-items:center; gap:8px; font-size:13px; color:#fff; cursor:pointer;">
                <input type="checkbox" id="field-limit_request_company_refresh" name="limit_request_company_refresh" {% if limits.request_company_refresh %}checked{% endif %} style="width:16px; height:16px;">
                <span>On-Demand Company Data Refresh</span>
            </label>
        </div>"""

for le in ['\r\n', '\n']:
    tgt = old_sec5.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_sec5.replace('\n', le))
        print("Updated Section 5 in plan_form.html")
        break
else:
    print("WARNING: Could not update Section 5 in plan_form.html")

with open('templates/admin/subscriptions/plan_form.html', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done")

