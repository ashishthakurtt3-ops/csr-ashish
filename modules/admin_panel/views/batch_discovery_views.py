"""
modules/admin_panel/views/batch_discovery_views.py
==================================================
Admin Portal views and streaming endpoints for the AI Bulk Discovery Engine.
Allows administrators to:
- Upload CSV / Excel / JSON company manifests
- Stream discovery probes with live progress and real-time logs
- Auto-import extracted jobs and CSR disclosures directly into the production database
- Download sample templates for bulk discovery

IMPORTANT: All AJAX API endpoints in this module deliberately avoid @login_required
decorator. Django's @login_required returns HTTP 302 redirects to HTML login pages,
causing "Unexpected token '<', <!DOCTYPE..." JSON parse errors on the client.
Instead, each API endpoint performs explicit authentication checks and returns
structured JSON 401 responses.
"""

import csv
import io
import json
import logging
import traceback
import functools
import urllib.parse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from modules.admin_panel.models import Company, Job, CSRProject
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.admin_panel.services.ai_config_service import get_active_ai_config, resolve_active_ai_summary

logger = logging.getLogger(__name__)


def _is_admin(user):
    return user.is_authenticated and (
        user.is_staff
        or user.is_superuser
        or getattr(user, 'role', '') in ('SUPER_ADMIN', 'SUPERADMIN', 'ADMIN')
    )


def json_api_view(fn):
    """
    Decorator guaranteeing that AJAX API views ALWAYS return valid JSON,
    even on unhandled exceptions, CSRF failures, or middleware errors.
    Replaces @login_required for AJAX endpoints to prevent HTML redirect responses.
    """
    @functools.wraps(fn)
    def wrapper(request, *args, **kwargs):
        # --- Auth guard: return JSON 401 instead of HTML redirect ---
        if not request.user.is_authenticated or not _is_admin(request.user):
            return JsonResponse({
                'status': 'error',
                'message': 'Authentication required. Please sign in as admin.',
                'code': 'AUTH_REQUIRED'
            }, status=401)
        try:
            return fn(request, *args, **kwargs)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error in {fn.__name__}: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Malformed JSON request body: {str(e)}',
                'code': 'INVALID_JSON'
            }, status=400)
        except Exception as e:
            logger.exception(f"Unhandled error in {fn.__name__}")
            return JsonResponse({
                'status': 'error',
                'message': f'Internal server error: {str(e)}',
                'code': 'INTERNAL_ERROR',
                'traceback_hint': traceback.format_exc().split('\n')[-3].strip()
            }, status=200)  # 200 so the client queue doesn't halt
    return wrapper


@login_required
def batch_discovery_view(request):
    """Render the AI Bulk Discovery Dashboard."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("Administrative privilege required.")

    ai_summary = resolve_active_ai_summary(force_refresh=True)
    total_companies = Company.objects.count()
    total_jobs = Job.objects.filter(status='ACTIVE').count()
    total_csr = CSRProject.objects.count()

    context = {
        'ai_provider': ai_summary.get('provider_display', 'Not Configured'),
        'ai_provider_id': ai_summary.get('provider_id', ''),
        'ai_model': ai_summary.get('model', ''),
        'ai_status': ai_summary.get('status', 'UNCONFIGURED'),
        'ai_is_ready': ai_summary.get('is_ready', False),
        'ai_is_configured': ai_summary.get('is_configured', False),
        'ai_badge_label': ai_summary.get('badge_label', 'No AI Model Configured'),
        'ai_using_failover': ai_summary.get('using_failover', False),
        'ai_fallback_enabled': ai_summary.get('fallback_enabled', False),
        'ai_fallback_provider': ai_summary.get('fallback_provider', ''),
        'ai_fallback_model': ai_summary.get('fallback_model', ''),
        'total_companies': total_companies,
        'total_jobs': total_jobs,
        'total_csr': total_csr,
    }
    return render(request, 'admin/ai_discovery/index.html', context)


@require_http_methods(['GET'])
@json_api_view
def ai_status_api(request):
    """Returns the exact currently active AI provider and model configuration."""
    ai_summary = resolve_active_ai_summary(force_refresh=True)
    return JsonResponse({
        'status': 'success',
        'ai_provider': ai_summary.get('provider_display', 'Not Configured'),
        'ai_provider_id': ai_summary.get('provider_id', ''),
        'ai_model': ai_summary.get('model', ''),
        'ai_status': ai_summary.get('status', 'UNCONFIGURED'),
        'ai_is_ready': ai_summary.get('is_ready', False),
        'ai_is_configured': ai_summary.get('is_configured', False),
        'ai_badge_label': ai_summary.get('badge_label', 'No AI Model Configured'),
        'ai_using_failover': ai_summary.get('using_failover', False),
        'ai_fallback_enabled': ai_summary.get('fallback_enabled', False),
        'ai_fallback_provider': ai_summary.get('fallback_provider', ''),
        'ai_fallback_model': ai_summary.get('fallback_model', ''),
    })


@require_http_methods(['POST'])
@json_api_view
def parse_file_api(request):
    """Upload handler that parses CSV / Excel / JSON and returns normalized company task queue."""
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({'status': 'error', 'message': 'No file uploaded.'}, status=400)

    filename = uploaded_file.name
    try:
        raw_records = BatchDiscoveryService.parse_uploaded_file(uploaded_file, filename)
    except Exception as parse_err:
        return JsonResponse({
            'status': 'error',
            'message': f'Unable to parse uploaded file "{filename}": {str(parse_err)}'
        }, status=400)

    if not raw_records:
        return JsonResponse({
            'status': 'error',
            'message': 'No valid company records found. Ensure your file contains both "Company Name" and "Homepage URL" columns.'
        }, status=400)

    # Strictly validate company_name and homepage_url, stripping any careers/CSR/optional override fields
    validated_records = []
    skipped_count = 0
    for r in raw_records:
        comp_name = (r.get('company_name') or '').strip()
        home_url = BatchDiscoveryService._sanitize_url(r.get('homepage_url') or r.get('website_url') or '')
        if not comp_name or not home_url:
            skipped_count += 1
            continue
        parsed_home = urllib.parse.urlparse(home_url)
        if not parsed_home.netloc or '.' not in parsed_home.netloc:
            skipped_count += 1
            continue
        validated_records.append({
            'company_name': comp_name,
            'homepage_url': home_url,
            'website_url': home_url,
        })

    if not validated_records:
        return JsonResponse({
            'status': 'error',
            'message': 'No valid company records found. Both "Company Name" and "Homepage URL" are strictly required for every row.',
            'skipped_count': skipped_count,
        }, status=400)

    return JsonResponse({
        'status': 'success',
        'filename': filename,
        'count': len(validated_records),
        'skipped_count': skipped_count,
        'companies': validated_records
    })


@require_http_methods(['POST'])
@json_api_view
def process_company_api(request):
    """Processes a single company task from the client queue: crawls website, invokes AI, auto-imports to DB."""
    company_task = None
    try:
        data = json.loads(request.body.decode('utf-8'))
        if not isinstance(data, dict):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid payload: expected JSON object.'
            }, status=400)
        raw_company = data.get('company')
        if not isinstance(raw_company, dict):
            raw_company = {}
        options = data.get('options', {})
        if not isinstance(options, dict):
            options = {}

        comp_name = (raw_company.get('company_name') or '').strip()
        raw_home_url = (raw_company.get('homepage_url') or raw_company.get('website_url') or '').strip()
        home_url = BatchDiscoveryService._sanitize_url(raw_home_url)

        if not comp_name or not home_url:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid company payload: both company_name and homepage_url are strictly required.'
            }, status=400)

        parsed_home = urllib.parse.urlparse(home_url)
        if not parsed_home.netloc or '.' not in parsed_home.netloc:
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid homepage_url "{raw_home_url}": must be a valid corporate domain URL.'
            }, status=400)

        # Strictly sanitize task payload: ONLY company_name, homepage_url, and website_url.
        # Discard and strip any incoming careers_url, csr_url, sector, headquarters, nse_symbol, or bypass fields.
        sanitized_task = {
            'company_name': comp_name,
            'homepage_url': home_url,
            'website_url': home_url,
        }

        company_task = sanitized_task
        result = BatchDiscoveryService.process_single_company(sanitized_task, options)
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
        }, status=200)  # Return 200 so the client queue doesn't halt!


@login_required
def download_sample_template_view(request):
    """Generates a downloadable CSV or Excel sample template for bulk discovery."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("Forbidden")

    fmt = request.GET.get('format', 'csv').lower()

    headers = [
        "Company Name", "Homepage URL"
    ]
    sample_rows = [
        ["Tata Consultancy Services", "https://www.tcs.com"],
        ["Swiggy Limited", "https://www.swiggy.com"],
        ["Zomato Limited", "https://www.zomato.com"],
        ["One97 Communications (Paytm)", "https://paytm.com"],
        ["Apollo Hospitals Enterprise", "https://www.apollohospitals.com"]
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

