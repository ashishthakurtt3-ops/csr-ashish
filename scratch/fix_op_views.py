with open('modules/website/views/opportunity_api_views.py', 'r', encoding='utf-8') as f:
    op = f.read()

# Replace block 1
old_b1 = """    if request.GET.get('format') == 'csv' or request.GET.get('export') == 'csv':
        # ── Entitlement: export quota check ──────────────────────────
        from modules.admin_panel.models import User as _User
        if getattr(request, 'user', None) and request.user.is_authenticated:
            _export_user = request.user
        else:
            _export_user = _User.objects.filter(is_active=True).order_by('id').first()
        if _export_user:
            _export_svc = EntitlementService(_export_user)
            try:
                _export_svc.check_export_quota(count=qs.count())
            except EntitlementError as _ex_err:
                return JsonResponse({
                    'error': _ex_err.message,
                    'feature': _ex_err.feature,
                    'limit': _ex_err.limit,
                    'current': _ex_err.current,
                    'upgrade_to': _ex_err.upgrade_to,
                    'code': 'entitlement_exceeded',
                }, status=403)
        # ── End entitlement check ────────────────────────────────────"""

new_b1 = """    if request.GET.get('format') == 'csv' or request.GET.get('export') == 'csv':
        _req_limit = int(request.GET.get('limit', 2000))
        _export_count = min(qs.count(), _req_limit)
        # ── Entitlement: export quota check ──────────────────────────
        from modules.admin_panel.models import User as _User
        if getattr(request, 'user', None) and request.user.is_authenticated:
            _export_user = request.user
        else:
            _export_user = _User.objects.filter(is_active=True).order_by('id').first()
        if _export_user:
            _export_svc = EntitlementService(_export_user)
            try:
                _export_svc.check_export_quota(count=_export_count)
            except EntitlementError as _ex_err:
                return JsonResponse({
                    'error': _ex_err.message,
                    'feature': _ex_err.feature,
                    'limit': _ex_err.limit,
                    'current': _ex_err.current,
                    'upgrade_to': _ex_err.upgrade_to,
                    'code': 'entitlement_exceeded',
                }, status=403)
        # ── End entitlement check ────────────────────────────────────"""

# Replace in op
for le in ['\r\n', '\n']:
    t1 = old_b1.replace('\n', le)
    if t1 in op:
        op = op.replace(t1, new_b1.replace('\n', le), 1)
        print("Replaced Block 1 in opportunity_api_views.py")
        break
else:
    print("WARNING: Could not find Block 1 in opportunity_api_views.py")

# Update iteration for block 1
op = op.replace("        for p in qs:\n            writer.writerow([", "        for p in qs[:_export_count]:\n            writer.writerow([")
op = op.replace("        for p in qs:\r\n            writer.writerow([", "        for p in qs[:_export_count]:\r\n            writer.writerow([")

with open('modules/website/views/opportunity_api_views.py', 'w', encoding='utf-8') as f:
    f.write(op)
print("Done updating opportunity_api_views.py")

