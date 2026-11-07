"""
modules/admin_panel/views/batch_discovery_views.py
==================================================
Admin Portal views and streaming endpoints for the AI Bulk Discovery Engine.
Allows administrators to:
- Upload CSV / Excel / JSON company manifests
- Stream discovery probes with live progress and real-time logs
- Auto-import extracted jobs and CSR disclosures directly into the production database
- Download sample templates for bulk discovery
"""

import csv
import io
import json
import logging
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from modules.admin_panel.models import Company, Job, CSRProject
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.admin_panel.services.ai_config_service import get_active_ai_config

logger = logging.getLogger(__name__)


def _is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or getattr(user, 'role', '') in ('SUPER_ADMIN', 'ADMIN'))


@login_required
def batch_discovery_view(request):
    """Render the AI Bulk Discovery Dashboard."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("Administrative privilege required.")

    ai_config = get_active_ai_config()
    total_companies = Company.objects.count()
    total_jobs = Job.objects.filter(status='ACTIVE').count()
    total_csr = CSRProject.objects.count()

    context = {
        'ai_provider': ai_config.get('primary_provider', 'gemini').title(),
        'ai_model': ai_config.get('primary_model', 'gemini-3.1-flash-lite'),
        'total_companies': total_companies,
        'total_jobs': total_jobs,
        'total_csr': total_csr,
    }
    return render(request, 'admin/ai_discovery/index.html', context)


@login_required
@require_http_methods(['POST'])
def parse_file_api(request):
    """Upload handler that parses CSV / Excel / JSON and returns normalized company task queue."""
    if not _is_admin(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({'status': 'error', 'message': 'No file uploaded.'}, status=400)

    try:
        filename = uploaded_file.name
        records = BatchDiscoveryService.parse_uploaded_file(uploaded_file, filename)
        if not records:
            return JsonResponse({
                'status': 'error',
                'message': 'No valid company records found. Ensure your file contains a "Company Name" or "Company" column.'
            }, status=400)

        return JsonResponse({
            'status': 'success',
            'filename': filename,
            'count': len(records),
            'companies': records
        })
    except Exception as e:
        logger.exception("File parse error")
        return JsonResponse({'status': 'error', 'message': f'Failed to parse file: {str(e)}'}, status=500)


@login_required
@require_http_methods(['POST'])
def process_company_api(request):
    """Processes a single company task from the client queue: crawls website, invokes AI, auto-imports to DB."""
    if not _is_admin(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    try:
        data = json.loads(request.body.decode('utf-8'))
        company_task = data.get('company')
        options = data.get('options', {})

        if not company_task or not company_task.get('company_name'):
            return JsonResponse({'status': 'error', 'message': 'Invalid company payload.'}, status=400)

        result = BatchDiscoveryService.process_single_company(company_task, options)
        return JsonResponse(result)
    except Exception as e:
        logger.exception("Company processing failed")
        return JsonResponse({
            'status': 'error',
            'company_name': (company_task.get('company_name') if company_task else 'Unknown'),
            'message': str(e),
            'jobs_discovered': 0,
            'jobs_imported': 0,
            'csr_discovered': 0,
            'csr_imported': 0,
            'logs': [f"[ERROR] Discovery halted: {str(e)}"]
        }, status=200) # Return 200 so the client queue doesn't halt!


@login_required
def download_sample_template_view(request):
    """Generates a downloadable CSV or Excel sample template for bulk discovery."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("Forbidden")

    fmt = request.GET.get('format', 'csv').lower()

    headers = [
        "Company Name", "Official Website", "Careers URL",
        "CSR URL", "Sector / Industry", "NSE Symbol", "Headquarters"
    ]
    sample_rows = [
        ["Tata Consultancy Services", "https://www.tcs.com", "https://www.tcs.com/careers", "https://www.tcs.com/sustainability", "Information Technology", "TCS", "Mumbai, Maharashtra"],
        ["Swiggy Limited", "https://www.swiggy.com", "https://www.swiggy.com/careers", "https://www.swiggy.com/csr", "Consumer Internet & E-Commerce", "", "Bengaluru, Karnataka"],
        ["Zomato Limited", "", "", "", "Food & Quick Commerce", "ZOMATO", "Gurugram, Haryana"],
        ["Zepto Quick Commerce", "", "", "", "Retail & Logistics", "", "Mumbai, Maharashtra"],
        ["Apollo Hospitals Enterprise", "https://www.apollohospitals.com", "https://www.apollohospitals.com/careers", "https://www.apollohospitals.com/csr", "Healthcare & Life Sciences", "APOLLOHOSP", "Chennai, Tamil Nadu"]
    ]

    if fmt in ('xlsx', 'excel'):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Company Discovery"
        ws.append(headers)
        for r in sample_rows:
            ws.append(r)

        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        resp = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        resp['Content-Disposition'] = 'attachment; filename="company_discovery_sample_template.xlsx"'
        return resp
    else:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(sample_rows)

        resp = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="company_discovery_sample_template.csv"'
        return resp

