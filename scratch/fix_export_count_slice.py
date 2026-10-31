# 1. Update job_api_views.py
with open('modules/website/views/job_api_views.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_block = """    if request.GET.get('format') == 'csv' or request.GET.get('export') == 'csv':
        import io, csv
        from django.http import HttpResponse
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
        # ── End entitlement check ────────────────────────────────────
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Job Row ID', 'Job ID', 'Company ID', 'Company Name', 'NSE Symbol', 'Sector', 'Job Title', 'Department', 'Location', 'Work Mode', 'Employment Type', 'Experience', 'ATS Platform', 'Application URL', 'Source URL', 'Status'])
        _rows_written = 0
        for j in qs:"""

new_block = """    if request.GET.get('format') == 'csv' or request.GET.get('export') == 'csv':
        import io, csv
        from django.http import HttpResponse
        # Calculate capped rows for export
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
        # ── End entitlement check ────────────────────────────────────
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Job Row ID', 'Job ID', 'Company ID', 'Company Name', 'NSE Symbol', 'Sector', 'Job Title', 'Department', 'Location', 'Work Mode', 'Employment Type', 'Experience', 'ATS Platform', 'Application URL', 'Source URL', 'Status'])
        _rows_written = 0
        for j in qs[:_export_count]:"""

for le in ['\r\n', '\n']:
    tgt = old_block.replace('\n', le)
    if tgt in c:
        c = c.replace(tgt, new_block.replace('\n', le))
        print("Updated export quota calculation in job_api_views.py")
        break
else:
    print("WARNING: Could not update job_api_views.py")

with open('modules/website/views/job_api_views.py', 'w', encoding='utf-8') as f:
    f.write(c)


# 2. Update opportunity_api_views.py
with open('modules/website/views/opportunity_api_views.py', 'r', encoding='utf-8') as f:
    op = f.read()

# First block in opportunity_api_views.py (CSR Projects)
old_op1 = """    if request.GET.get('format') == 'csv' or request.GET.get('export') == 'csv':
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
        # ── End entitlement check ────────────────────────────────────
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Project ID', 'Company Name', 'NSE Symbol', 'Sector', 'Project Title',
            'Focus Area (Theme)', 'Schedule VII Classification', 'State & District',
            'Financial Year', 'CSR Allocation (INR Cr)', 'Execution Partner / NGO',
            'Project Status', 'Official Source URL', 'Verification Confidence'
        ])
        _rows_written = 0
        for p in qs:"""

new_op1 = """    if request.GET.get('format') == 'csv' or request.GET.get('export') == 'csv':
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
        # ── End entitlement check ────────────────────────────────────
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            'Project ID', 'Company Name', 'NSE Symbol', 'Sector', 'Project Title',
            'Focus Area (Theme)', 'Schedule VII Classification', 'State & District',
            'Financial Year', 'CSR Allocation (INR Cr)', 'Execution Partner / NGO',
            'Project Status', 'Official Source URL', 'Verification Confidence'
        ])
        _rows_written = 0
        for p in qs[:_export_count]:"""

for le in ['\r\n', '\n']:
    tgt = old_op1.replace('\n', le)
    if tgt in op:
        op = op.replace(tgt, new_op1.replace('\n', le))
        print("Updated export quota calculation in opportunity_api_views.py (Block 1)")
        break
else:
    print("WARNING: Could not update opportunity_api_views.py (Block 1)")

with open('modules/website/views/opportunity_api_views.py', 'w', encoding='utf-8') as f:
    f.write(op)
print("Done")

