"""
modules/admin_panel/views/preview_settings_views.py
==================================================
Admin Portal views for configuring Guest Preview Mode and managing dedicated
Dummy Preview Datasets (Companies, Jobs, Section 135 CSR Initiatives).

Provides:
- Master guest preview status & record limits
- Top preview banner text, badges, and CTA links
- Auth-Gate modal headers, descriptions, and action buttons
- Bottom unlock banners
- Dedicated Dummy Preview Dataset Manager (Excel/CSV upload, download templates, edit/delete)
"""

import io
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_http_methods
from modules.admin_panel.models import (
    GuestPreviewSettings, Company, Job, CSRProject,
    PreviewDummyCompany, PreviewDummyJob, PreviewDummyCSRProject
)
from modules.admin_panel.services.preview_dummy_service import (
    seed_default_dummy_data,
    get_dummy_preview_summary,
    parse_and_import_dummy_file,
    build_sample_excel_template,
    build_sample_unified_csv,
    DEFAULT_DUMMY_COMPANIES,
    DEFAULT_DUMMY_JOBS,
    DEFAULT_DUMMY_CSR
)


def _is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser or getattr(user, 'role', '') in ('SUPER_ADMIN', 'ADMIN'))


@login_required
def preview_settings_view(request):
    """Admin dashboard to view and modify general Guest Preview configuration."""
    if not _is_admin(request.user):
        return HttpResponseForbidden("Administrative privilege required.")

    settings_obj = GuestPreviewSettings.get_settings()

    if request.method == 'POST':
        try:
            # 1. Master controls
            settings_obj.preview_enabled = request.POST.get('preview_enabled') == 'on'
            limit_val = int(request.POST.get('preview_limit', 5))
            settings_obj.preview_limit = max(1, min(25, limit_val))

            # 2. Top banner
            settings_obj.banner_enabled = request.POST.get('banner_enabled') == 'on'
            settings_obj.banner_badge_text = request.POST.get('banner_badge_text', 'Guest Preview Mode').strip()
            settings_obj.banner_headline = request.POST.get('banner_headline', '').strip()
            settings_obj.banner_cta_text = request.POST.get('banner_cta_text', 'Unlock All Records Free →').strip()
            settings_obj.banner_cta_url = request.POST.get('banner_cta_url', '/register/').strip()

            # 3. Auth-Gate modal
            settings_obj.auth_modal_title = request.POST.get('auth_modal_title', 'Unlock Full Corporate Dossier').strip()
            settings_obj.auth_modal_description = request.POST.get('auth_modal_description', '').strip()
            settings_obj.auth_modal_primary_btn_text = request.POST.get('auth_modal_primary_btn_text', 'Create Free Account').strip()
            settings_obj.auth_modal_primary_btn_url = request.POST.get('auth_modal_primary_btn_url', '/register/').strip()
            settings_obj.auth_modal_secondary_btn_text = request.POST.get('auth_modal_secondary_btn_text', 'Sign In').strip()
            settings_obj.auth_modal_secondary_btn_url = request.POST.get('auth_modal_secondary_btn_url', '/login/').strip()

            # 4. Bottom unlock card
            settings_obj.bottom_banner_enabled = request.POST.get('bottom_banner_enabled') == 'on'
            settings_obj.bottom_banner_title = request.POST.get('bottom_banner_title', '').strip()
            settings_obj.bottom_banner_description = request.POST.get('bottom_banner_description', '').strip()
            settings_obj.bottom_banner_btn_text = request.POST.get('bottom_banner_btn_text', 'Create Free Account').strip()
            settings_obj.bottom_banner_btn_url = request.POST.get('bottom_banner_btn_url', '/register/').strip()

            # 5. Content curation strategies
            settings_obj.company_selection_mode = request.POST.get('company_selection_mode', 'ALPHABETICAL')
            settings_obj.featured_company_ids = request.POST.get('featured_company_ids', '').strip()
            settings_obj.job_selection_mode = request.POST.get('job_selection_mode', 'LATEST')
            settings_obj.featured_job_ids = request.POST.get('featured_job_ids', '').strip()
            settings_obj.csr_selection_mode = request.POST.get('csr_selection_mode', 'LATEST')
            settings_obj.featured_csr_ids = request.POST.get('featured_csr_ids', '').strip()

            # 6. Audit
            settings_obj.updated_by = request.user
            settings_obj.save()

            messages.success(request, "Guest Preview settings successfully updated and live across public pages.")
            return redirect('admin_preview_settings:index')
        except Exception as e:
            messages.error(request, f"Failed to save settings: {str(e)}")

    dummy_summary = get_dummy_preview_summary()

    context = {
        'settings': settings_obj,
        'dummy_summary': dummy_summary,
        'total_companies': Company.objects.count(),
        'total_jobs': Job.objects.filter(status='ACTIVE').count(),
        'total_csr': CSRProject.objects.count(),
    }
    return render(request, 'admin/preview_settings/index.html', context)


@login_required
def preview_dummy_data_view(request):
    """
    Dedicated Admin Dashboard to view, manage, and upload Dummy Preview Datasets.
    Supports CSV and Excel files.
    """
    if not _is_admin(request.user):
        return HttpResponseForbidden("Administrative privilege required.")

    settings_obj = GuestPreviewSettings.get_settings()
    summary = get_dummy_preview_summary()

    # Seed defaults if completely empty
    if summary['total_records'] == 0:
        seed_default_dummy_data()
        summary = get_dummy_preview_summary()

    companies = PreviewDummyCompany.objects.all().order_by('display_order', 'id')
    jobs = PreviewDummyJob.objects.all().order_by('display_order', 'id')
    csr_projects = PreviewDummyCSRProject.objects.all().order_by('display_order', 'id')

    context = {
        'settings': settings_obj,
        'summary': summary,
        'companies': companies,
        'jobs': jobs,
        'csr_projects': csr_projects,
    }
    return render(request, 'admin/preview_settings/dummy_data.html', context)


@login_required
@require_http_methods(['POST'])
def preview_dummy_upload_api(request):
    """
    Handle CSV or Excel file uploads containing Dummy Preview Datasets.
    """
    if not _is_admin(request.user):
        return HttpResponseForbidden("Administrative privilege required.")

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        messages.error(request, "Please select a valid CSV or Excel file to upload.")
        return redirect('admin_preview_settings:dummy_data')

    mode = request.POST.get('import_mode', 'REPLACE').upper()
    category = request.POST.get('target_category', 'AUTO').upper()

    try:
        results = parse_and_import_dummy_file(uploaded_file, mode=mode, target_category=category)
        if results['status'] == 'success':
            total_imported = results['companies_imported'] + results['jobs_imported'] + results['csr_imported']
            msg_details = f"Successfully imported {total_imported} dummy preview records: {results['companies_imported']} companies, {results['jobs_imported']} jobs, {results['csr_imported']} CSR projects."
            messages.success(request, msg_details)
        else:
            messages.error(request, "Upload failed: " + " ".join(results['messages']))
    except Exception as e:
        messages.error(request, f"Error processing file '{uploaded_file.name}': {str(e)}")

    return redirect('admin_preview_settings:dummy_data')


@login_required
def preview_download_template_view(request):
    """
    Download pre-formatted Excel or CSV sample templates for Dummy Preview Data.
    Pre-populated with realistic dummy records in the exact production format.
    """
    if not _is_admin(request.user):
        return HttpResponseForbidden("Administrative privilege required.")

    fmt = request.GET.get('format', 'xlsx').lower()
    category = request.GET.get('category', 'all').lower()

    if fmt == 'xlsx':
        stream = build_sample_excel_template()
        response = HttpResponse(
            stream.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="dummy_preview_dataset_template.xlsx"'
        return response

    # CSV Downloads
    output = io.StringIO()
    if category == 'companies':
        writer = csv.writer(output)
        writer.writerow(["Company ID", "Company Name", "NSE Symbol", "Sector", "Headquarters", "Website URL", "Careers URL", "CSR Portal URL", "Job Count", "CSR Count"])
        for c in DEFAULT_DUMMY_COMPANIES:
            writer.writerow([c['company_id'], c['company_name'], c['nse_symbol'], c['sector'], c['headquarters'], c['website_url'], c['careers_url'], c['csr_portal_url'], c['job_count'], c['csr_count']])
        filename = "dummy_preview_companies_template.csv"

    elif category == 'jobs':
        writer = csv.writer(output)
        writer.writerow(["Job ID", "Job Title", "Company Name", "NSE Symbol", "Location", "Work Mode", "Department", "Experience", "Application URL", "Posted Date"])
        for j in DEFAULT_DUMMY_JOBS:
            writer.writerow([j['job_row_id'], j['job_title'], j['company_name'], j['nse_symbol'], j['location'], j['work_mode'], j['department'], j['experience'], j['application_url'], j['posted_date']])
        filename = "dummy_preview_jobs_template.csv"

    elif category == 'csr':
        writer = csv.writer(output)
        writer.writerow(["CSR ID", "Project Name", "Company Name", "Category", "State", "Budget", "Source URL"])
        for p in DEFAULT_DUMMY_CSR:
            writer.writerow([p['csr_id'], p['project_name'], p['company_name'], p['category'], p['state'], p['budget'], p['source_url']])
        filename = "dummy_preview_csr_template.csv"

    else:
        # Unified 5-Companies All-in-One Master CSV
        csv_data = build_sample_unified_csv()
        response = HttpResponse(csv_data, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="dummy_preview_5_companies.csv"'
        return response

    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_http_methods(['POST'])
def preview_dummy_reset_defaults_api(request):
    """Restore default realistic dummy records for preview mode."""
    if not _is_admin(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    seed_default_dummy_data(force=True)
    summary = get_dummy_preview_summary()
    messages.success(request, f"Restored default realistic dummy dataset: {summary['companies_count']} companies, {summary['jobs_count']} jobs, and {summary['csr_count']} CSR projects.")
    return redirect('admin_preview_settings:dummy_data')


@login_required
@require_http_methods(['POST'])
def preview_dummy_delete_item_api(request, category, record_id):
    """Delete a specific dummy record by ID."""
    if not _is_admin(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    deleted = False
    if category == 'company':
        PreviewDummyCompany.objects.filter(company_id=record_id).delete()
        deleted = True
    elif category == 'job':
        PreviewDummyJob.objects.filter(job_row_id=record_id).delete()
        deleted = True
    elif category == 'csr':
        PreviewDummyCSRProject.objects.filter(csr_id=record_id).delete()
        deleted = True

    if deleted:
        messages.success(request, f"Removed dummy {category} record '{record_id}'.")
    return redirect('admin_preview_settings:dummy_data')


@login_required
@require_http_methods(['POST'])
def preview_reset_defaults_api(request):
    """Reset Guest Preview settings to platform standard defaults."""
    if not _is_admin(request.user):
        return JsonResponse({'error': 'Forbidden'}, status=403)

    settings_obj = GuestPreviewSettings.get_settings()
    settings_obj.preview_enabled = True
    settings_obj.preview_limit = 5
    settings_obj.banner_enabled = True
    settings_obj.banner_badge_text = "Guest Preview Mode"
    settings_obj.banner_headline = "Viewing {count} sample records from our verified database of {companies} corporations, {jobs} jobs, and {csr} CSR initiatives."
    settings_obj.banner_cta_text = "Unlock All Records Free →"
    settings_obj.banner_cta_url = "/register/"
    settings_obj.auth_modal_title = "Unlock Full Corporate Dossier"
    settings_obj.auth_modal_description = "Sign in to access comprehensive statutory filings, active vacancies, and CSR allocations."
    settings_obj.auth_modal_primary_btn_text = "Create Free Account"
    settings_obj.auth_modal_primary_btn_url = "/register/"
    settings_obj.auth_modal_secondary_btn_text = "Sign In"
    settings_obj.auth_modal_secondary_btn_url = "/login/"
    settings_obj.bottom_banner_enabled = True
    settings_obj.bottom_banner_title = "Viewing {count} of {total} verified corporations"
    settings_obj.bottom_banner_description = "Create a free account to unlock all corporate dossiers, active vacancies, and advanced search filters."
    settings_obj.bottom_banner_btn_text = "Create Free Account"
    settings_obj.bottom_banner_btn_url = "/register/"
    settings_obj.company_selection_mode = "ALPHABETICAL"
    settings_obj.featured_company_ids = ""
    settings_obj.job_selection_mode = "LATEST"
    settings_obj.featured_job_ids = ""
    settings_obj.csr_selection_mode = "LATEST"
    settings_obj.featured_csr_ids = ""
    settings_obj.updated_by = request.user
    settings_obj.save()

    return JsonResponse({
        'status': 'success',
        'message': 'Guest preview settings restored to factory defaults.'
    })
