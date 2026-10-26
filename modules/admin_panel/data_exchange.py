import os
"""
Data Exchange Engine for ImpactBridge Custom Enterprise Admin Panel.
Provides 100% accurate, high-fidelity data extraction (Export) and importation (Import)
across all platform entities with ACID transaction safety and audit trail logging.
"""

import csv
import io
import json
import zipfile
from datetime import datetime
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.utils import timezone

from modules.admin_panel.models import (
    Company, Job, CSRProject, CSROpportunity,
    Document, User, Subscription, Invoice,
    PromoCode, PageRecord, AuditTrail, Contact, NGOCollaboration, Prospect,
    OpportunityScore
)


def _to_bool(val):
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ('true', '1', 'yes', 't', 'y')


def _to_int(val, default=0):
    if val is None or val == '':
        return default
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return default


def _to_float(val, default=0.0):
    if val is None or val == '':
        return default
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return default


def _clean_str(val):
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


# Configuration mapping for all platform entities
ENTITY_SCHEMAS = {
    'companies': {
        'model': Company,
        'label': 'Enterprise Companies',
        'pk': 'company_id',
        'export_fields': [
            'company_id', 'company_name', 'legal_name', 'isin', 'nse_symbol',
            'bse_scrip_code', 'listed_on_nse', 'listed_on_bse', 'listing_status',
            'website_url', 'sector', 'headquarters', 'cin', 'last_crawled',
            'crawl_status', 'data_confidence', 'careers_url', 'csr_portal_url',
            'link_quality', 'link_verified_at', 'total_jobs_tracked', 'total_csr_projects', 'total_contacts'
        ],
        'import_fields': [
            'company_id', 'company_name', 'legal_name', 'isin', 'nse_symbol',
            'bse_scrip_code', 'listed_on_nse', 'listed_on_bse', 'listing_status',
            'website_url', 'sector', 'headquarters', 'cin', 'last_crawled',
            'crawl_status', 'data_confidence', 'careers_url', 'csr_portal_url',
            'link_quality', 'link_verified_at'
        ],
        'type_converters': {
            'listed_on_nse': _to_bool,
            'listed_on_bse': _to_bool,
            'data_confidence': _to_float,
        },
        'required_fields': ['company_id', 'company_name'],
    },
    'jobs': {
        'model': Job,
        'label': 'Job Openings',
        'pk': 'job_row_id',
        'export_fields': [
            'job_row_id', 'company_id', 'company_name', 'nse_symbol', 'sector',
            'job_id', 'job_title', 'category', 'department', 'function',
            'location', 'state', 'country', 'work_mode', 'employment_type',
            'experience', 'education', 'skills', 'salary', 'job_description',
            'application_url', 'source_url', 'company_website', 'careers_url',
            'posted_date', 'closing_date', 'last_checked_date', 'status',
            'confidence', 'link_status', 'link_verified_at', 'data_provenance', 'fingerprint'
        ],
        'import_fields': [
            'job_row_id', 'company_id', 'job_id', 'job_title', 'department',
            'function', 'location', 'state', 'country', 'work_mode',
            'employment_type', 'experience', 'education', 'skills', 'salary',
            'job_description', 'posted_date', 'closing_date', 'application_url',
            'source_url', 'last_checked_date', 'status', 'confidence',
            'link_status', 'link_verified_at', 'data_provenance', 'fingerprint'
        ],
        'fk_lookups': {
            'company': {
                'model': Company,
                'target_field': 'company',
                'fk_id_key': 'company_id',
                'alt_key': 'company_name'
            }
        },
        'type_converters': {
            'job_row_id': _to_int,
            'confidence': _to_float,
        },
        'required_fields': ['job_title'],
    },
    'opportunities': {
        'model': CSROpportunity,
        'label': 'CSR Opportunities',
        'pk': 'opp_id',
        'export_fields': [
            'opp_id', 'company_id', 'company_name', 'title', 'opportunity_type',
            'category', 'submission_deadline', 'portal_url', 'requirements',
            'status', 'confidence', 'link_status', 'link_verified_at', 'fingerprint'
        ],
        'import_fields': [
            'opp_id', 'company_id', 'title', 'opportunity_type', 'category',
            'submission_deadline', 'portal_url', 'requirements', 'status',
            'confidence', 'link_status', 'link_verified_at', 'fingerprint'
        ],
        'fk_lookups': {
            'company': {
                'model': Company,
                'target_field': 'company',
                'fk_id_key': 'company_id',
                'alt_key': 'company_name'
            }
        },
        'type_converters': {
            'opp_id': _to_int,
            'confidence': _to_float,
        },
        'required_fields': ['title'],
    },
    'projects': {
        'model': CSRProject,
        'label': 'CSR Projects',
        'pk': 'csr_id',
        'export_fields': [
            'csr_id', 'company_id', 'company_name', 'project_name', 'category',
            'description', 'geographic_location', 'state', 'budget',
            'source_url', 'discovered_date', 'last_verified_date', 'confidence',
            'link_status', 'link_verified_at', 'fingerprint'
        ],
        'import_fields': [
            'csr_id', 'company_id', 'project_name', 'category', 'description',
            'geographic_location', 'state', 'budget', 'source_url',
            'discovered_date', 'last_verified_date', 'confidence',
            'link_status', 'link_verified_at', 'fingerprint'
        ],
        'fk_lookups': {
            'company': {
                'model': Company,
                'target_field': 'company',
                'fk_id_key': 'company_id',
                'alt_key': 'company_name'
            }
        },
        'type_converters': {
            'csr_id': _to_int,
            'confidence': _to_float,
        },
        'required_fields': ['project_name'],
    },
    'documents': {
        'model': Document,
        'label': 'Documents Hub',
        'pk': 'document_id',
        'export_fields': [
            'document_id', 'title', 'document_type', 'company_id', 'company_name',
            'file_size', 'file_format', 'status', 'notes', 'uploaded_at', 'verified_at'
        ],
        'import_fields': [
            'document_id', 'title', 'document_type', 'company_id',
            'file_size', 'file_format', 'status', 'notes'
        ],
        'fk_lookups': {
            'company': {
                'model': Company,
                'target_field': 'company',
                'fk_id_key': 'company_id',
                'alt_key': 'company_name'
            }
        },
        'type_converters': {
            'document_id': _to_int,
            'file_size': _to_int,
        },
        'required_fields': ['title'],
    },
    'users': {
        'model': User,
        'label': 'User Accounts',
        'pk': 'id',
        'export_fields': [
            'id', 'username', 'email', 'first_name', 'last_name', 'role',
            'organization_name', 'phone', 'designation', 'is_active',
            'is_staff', 'is_verified', 'date_joined'
        ],
        'import_fields': [
            'id', 'username', 'email', 'first_name', 'last_name', 'role',
            'organization_name', 'phone', 'designation', 'is_active',
            'is_staff', 'is_verified'
        ],
        'type_converters': {
            'id': _to_int,
            'is_active': _to_bool,
            'is_staff': _to_bool,
            'is_verified': _to_bool,
        },
        'required_fields': ['username', 'email'],
    },
    'subscriptions': {
        'model': Subscription,
        'label': 'Subscriptions',
        'pk': 'subscription_id',
        'export_fields': [
            'subscription_id', 'tenant_id', 'plan_id', 'status', 'billing_cycle',
            'organization_name', 'contact_email', 'activated_at',
            'current_period_start', 'current_period_end', 'cancel_at_period_end',
            'promo_code', 'promo_percent', 'base_amount_paise', 'discount_paise',
            'taxable_paise', 'cgst_paise', 'sgst_paise', 'igst_paise', 'total_paise',
            'currency', 'payment_method', 'transaction_id', 'gstin',
            'place_of_supply', 'supply_type', 'seats', 'daily_match_quota',
            'created_at', 'updated_at'
        ],
        'import_fields': [
            'subscription_id', 'tenant_id', 'plan_id', 'status', 'billing_cycle',
            'organization_name', 'contact_email', 'activated_at',
            'current_period_start', 'current_period_end', 'cancel_at_period_end',
            'promo_code', 'promo_percent', 'base_amount_paise', 'discount_paise',
            'taxable_paise', 'cgst_paise', 'sgst_paise', 'igst_paise', 'total_paise',
            'currency', 'payment_method', 'transaction_id', 'gstin',
            'place_of_supply', 'supply_type', 'seats', 'daily_match_quota'
        ],
        'type_converters': {
            'cancel_at_period_end': _to_bool,
            'promo_percent': _to_int,
            'base_amount_paise': _to_int,
            'discount_paise': _to_int,
            'taxable_paise': _to_int,
            'cgst_paise': _to_int,
            'sgst_paise': _to_int,
            'igst_paise': _to_int,
            'total_paise': _to_int,
            'seats': _to_int,
            'daily_match_quota': _to_int,
        },
        'required_fields': ['subscription_id', 'tenant_id'],
    },
    'invoices': {
        'model': Invoice,
        'label': 'Subscription Invoices',
        'pk': 'invoice_id',
        'export_fields': [
            'invoice_id', 'invoice_no', 'subscription_id', 'tenant_id',
            'issued_at', 'description', 'taxable_paise', 'cgst_paise',
            'sgst_paise', 'igst_paise', 'total_paise', 'currency',
            'gstin', 'place_of_supply', 'status', 'line_items'
        ],
        'import_fields': [
            'invoice_id', 'invoice_no', 'subscription_id', 'tenant_id',
            'issued_at', 'description', 'taxable_paise', 'cgst_paise',
            'sgst_paise', 'igst_paise', 'total_paise', 'currency',
            'gstin', 'place_of_supply', 'status', 'line_items'
        ],
        'type_converters': {
            'invoice_id': _to_int,
            'taxable_paise': _to_int,
            'cgst_paise': _to_int,
            'sgst_paise': _to_int,
            'igst_paise': _to_int,
            'total_paise': _to_int,
        },
        'required_fields': ['invoice_no', 'tenant_id'],
    },
    'promos': {
        'model': PromoCode,
        'label': 'Promo Codes',
        'pk': 'code',
        'export_fields': [
            'code', 'percent_off', 'max_redemptions', 'times_redeemed',
            'valid_from', 'valid_until', 'applicable_plans', 'description', 'active'
        ],
        'import_fields': [
            'code', 'percent_off', 'max_redemptions', 'times_redeemed',
            'valid_from', 'valid_until', 'applicable_plans', 'description', 'active'
        ],
        'type_converters': {
            'percent_off': _to_int,
            'max_redemptions': _to_int,
            'times_redeemed': _to_int,
            'active': _to_bool,
        },
        'required_fields': ['code'],
    },
    'pages': {
        'model': PageRecord,
        'label': 'Crawler Web Pages',
        'pk': 'page_id',
        'export_fields': [
            'page_id', 'company_id', 'company_name', 'url', 'title',
            'page_type', 'content_hash', 'last_modified', 'last_crawled',
            'status', 'relevant_snippet', 'confidence'
        ],
        'import_fields': [
            'page_id', 'company_id', 'url', 'title', 'page_type',
            'content_hash', 'last_modified', 'last_crawled', 'status',
            'relevant_snippet', 'confidence'
        ],
        'fk_lookups': {
            'company': {
                'model': Company,
                'target_field': 'company',
                'fk_id_key': 'company_id',
                'alt_key': 'company_name'
            }
        },
        'type_converters': {
            'page_id': _to_int,
            'confidence': _to_float,
        },
        'required_fields': ['url'],
    },
    'audits': {
        'model': AuditTrail,
        'label': 'System Audit Trail',
        'pk': 'audit_id',
        'export_fields': [
            'audit_id', 'record_type', 'record_id', 'action',
            'previous_value', 'new_value', 'user_role', 'notes', 'timestamp'
        ],
        'import_fields': [
            'audit_id', 'record_type', 'record_id', 'action',
            'previous_value', 'new_value', 'user_role', 'notes', 'timestamp'
        ],
        'type_converters': {
            'audit_id': _to_int,
        },
        'required_fields': ['record_type', 'action'],
    },
    'queue': {
        'model': CSRProject,
        'label': 'Verification Queue (CSR Projects)',
        'pk': 'csr_id',
        'export_fields': [
            'csr_id', 'company_id', 'company_name', 'project_name', 'category',
            'description', 'geographic_location', 'state', 'budget',
            'source_url', 'discovered_date', 'last_verified_date', 'confidence',
            'link_status', 'link_verified_at', 'fingerprint'
        ],
        'import_fields': [
            'csr_id', 'company_id', 'project_name', 'category', 'description',
            'geographic_location', 'state', 'budget', 'source_url',
            'discovered_date', 'last_verified_date', 'confidence',
            'link_status', 'link_verified_at', 'fingerprint'
        ],
        'fk_lookups': {
            'company': {
                'model': Company,
                'target_field': 'company',
                'fk_id_key': 'company_id',
                'alt_key': 'company_name'
            }
        },
        'type_converters': {
            'csr_id': _to_int,
            'confidence': _to_float,
        },
        'required_fields': ['project_name'],
    },
    'contacts': {
        'model': Contact,
        'label': 'Corporate Governance & Key Officials',
        'pk': 'contact_id',
        'export_fields': [
            'contact_id', 'company_id', 'company_name', 'name', 'designation',
            'department', 'email', 'phone', 'source_url', 'confidence',
            'last_verified_date', 'link_status', 'link_verified_at', 'verification_status', 'fingerprint'
        ],
        'import_fields': [
            'contact_id', 'company_id', 'name', 'designation', 'department',
            'email', 'phone', 'source_url', 'confidence', 'last_verified_date',
            'link_status', 'link_verified_at', 'verification_status', 'fingerprint'
        ],
        'type_converters': {
            'contact_id': _to_int,
            'confidence': _to_float,
        },
        'required_fields': ['name'],
    },
    'collaborations': {
        'model': NGOCollaboration,
        'label': 'NGO Collaborations & Strategic Partnerships',
        'pk': 'collab_id',
        'export_fields': [
            'collab_id', 'company_id', 'company_name', 'ngo_name', 'project_id',
            'relationship_type', 'location', 'source_url', 'discovered_date',
            'confidence', 'fingerprint'
        ],
        'import_fields': [
            'collab_id', 'company_id', 'ngo_name', 'project_id', 'relationship_type',
            'location', 'source_url', 'discovered_date', 'confidence', 'fingerprint'
        ],
        'type_converters': {
            'collab_id': _to_int,
            'confidence': _to_float,
        },
        'required_fields': ['ngo_name'],
    },
    'scores': {
        'model': OpportunityScore,
        'label': 'Corporate Opportunity & Impact Scores',
        'pk': 'company_id',
        'export_fields': [
            'company_id', 'company_name', 'active_csr', 'focus_match', 'recent_activity',
            'ngo_activity', 'opportunity_page', 'contact_availability',
            'geographic_match', 'score', 'evidence_status', 'rationale', 'scored_at'
        ],
        'import_fields': [
            'company_id', 'active_csr', 'focus_match', 'recent_activity',
            'ngo_activity', 'opportunity_page', 'contact_availability',
            'geographic_match', 'score', 'evidence_status', 'rationale', 'scored_at'
        ],
        'type_converters': {
            'active_csr': _to_float,
            'focus_match': _to_float,
            'recent_activity': _to_float,
            'ngo_activity': _to_float,
            'opportunity_page': _to_float,
            'contact_availability': _to_float,
            'geographic_match': _to_float,
            'score': _to_float,
        },
        'required_fields': ['company_id'],
    },
    'prospects': {
        'model': Prospect,
        'label': 'Saved Prospects & Target Pipeline',
        'pk': 'prospect_id',
        'export_fields': [
            'prospect_id', 'company_id', 'company_name', 'stage', 'notes',
            'assigned_to', 'target_proposal', 'follow_up_date', 'match_score',
            'created_at', 'updated_at'
        ],
        'import_fields': [
            'prospect_id', 'company_id', 'stage', 'notes', 'assigned_to',
            'target_proposal', 'follow_up_date', 'match_score'
        ],
        'type_converters': {
            'prospect_id': _to_int,
            'match_score': _to_float,
        },
        'required_fields': ['company_id'],
    },
}


def classify_job_category(job):
    """
    Classifies a job into one of the 9 canonical enterprise categories shown on the website.
    """
    title = (job.job_title or '').lower()
    dept = (job.department or '').lower()
    func = (job.function or '').lower()
    skills = (job.skills or '').lower()
    combined = f"{title} {dept} {func} {skills}"

    if any(k in combined for k in ['csr', 'esg', 'sustainab', 'foundation', 'social impact', 'community']):
        return 'CSR, ESG & Sustainability'
    if any(k in combined for k in ['software', 'developer', 'cloud', 'devops', 'python', 'java', 'frontend', 'backend', 'full stack', 'data engineer', 'cyber', 'machine learning', 'artificial intelligence', 'information technology', 'tech']):
        return 'Technology & Software'
    if any(k in combined for k in ['plant', 'process engineer', 'mechanic', 'electrical engineer', 'civil engineer', 'manufacturing', 'automation', 'maintenance engineer', 'metallurg', 'piping']):
        return 'Engineering & Production'
    if any(k in combined for k in ['finance', 'credit', 'risk', 'treasury', 'wealth', 'banking', 'accounts', 'taxation', 'chartered accountant', 'audit', 'controller', 'balance sheet']):
        return 'Finance & Banking'
    if any(k in combined for k in ['supply chain', 'procurement', 'logistics', 'warehouse', 'sourcing', 'inventory', 'dispatch', 'vendor management', 'operations']):
        return 'Operations & Supply Chain'
    if any(k in combined for k in ['sales', 'marketing', 'business development', 'account manager', 'brand', 'channel', 'commercial', 'territory']):
        return 'Sales & Marketing'
    if any(k in combined for k in ['human resources', 'talent acquisition', 'payroll', 'recruiter', 'hr ', 'people operations', 'employee engagement']):
        return 'HR & People Operations'
    if any(k in combined for k in ['pharma', 'clinical', 'medical', 'formulation', 'regulatory affairs', 'quality assurance', 'healthcare', 'rd scientist']):
        return 'Healthcare & Pharma'
    if any(k in combined for k in ['legal', 'compliance', 'company secretary', 'contract', 'litigation', 'governance', 'counsel', 'statutory']):
        return 'Legal & Governance'
    return 'Corporate / Operations'


def serialize_record(record, schema):
    """
    Extracts high-fidelity dictionary for a model instance according to export_fields.
    Enriches with full corporate details, sector classification, and direct application links.
    """
    data = {}
    for field in schema['export_fields']:
        if field == 'company_name':
            company = getattr(record, 'company', None)
            data[field] = company.company_name if company else ''
        elif field == 'company_id':
            company = getattr(record, 'company', None)
            data[field] = company.company_id if company else getattr(record, 'company_id', '')
        elif field == 'nse_symbol':
            company = getattr(record, 'company', None)
            data[field] = (company.nse_symbol if company else getattr(record, 'nse_symbol', '')) or ''
        elif field == 'sector':
            company = getattr(record, 'company', None)
            data[field] = (company.sector if company else getattr(record, 'sector', '')) or ''
        elif field == 'company_website':
            company = getattr(record, 'company', None)
            data[field] = (company.website_url if company else getattr(record, 'website_url', '')) or ''
        elif field == 'careers_url':
            company = getattr(record, 'company', None)
            data[field] = (company.careers_url if company else getattr(record, 'careers_url', '')) or ''
        elif field == 'category':
            if hasattr(record, 'job_title'):
                data[field] = classify_job_category(record)
            else:
                data[field] = getattr(record, 'category', '') or ''
        elif field == 'application_url':
            val = getattr(record, 'application_url', None) or ''
            if not val or '---' in val or not val.startswith('http'):
                company = getattr(record, 'company', None)
                if company:
                    val = company.careers_url or company.website_url or val
            data[field] = val or ''
        elif field == 'total_jobs_tracked':
            data[field] = record.jobs.count() if hasattr(record, 'jobs') else 0
        elif field == 'total_csr_projects':
            data[field] = record.csr_projects.count() if hasattr(record, 'csr_projects') else 0
        elif field == 'total_contacts':
            data[field] = record.contacts.count() if hasattr(record, 'contacts') else 0
        elif field == 'username':
            user = getattr(record, 'user', None)
            data[field] = user.username if user else getattr(record, 'username', '')
        elif field == 'user_email':
            user = getattr(record, 'user', None)
            data[field] = user.email if user else getattr(record, 'email', '')
        else:
            val = getattr(record, field, None)
            if isinstance(val, (datetime,)):
                val = val.isoformat()
            data[field] = val if val is not None else ''
    return data


@login_required
def export_entity_view(request, entity):
    """
    Extracts authentic database records for the requested entity as CSV or JSON.
    Supports ?company_id= for scoped downloads, and ?format=csv|json.
    """
    schema = ENTITY_SCHEMAS.get(entity)
    if not schema:
        return HttpResponse("Invalid entity requested.", status=400)

    export_format = request.GET.get('format', 'csv').lower()
    model = schema['model']

    # Select base queryset
    qs = model.objects.all()
    field_names = [f.name for f in model._meta.fields]
    if 'company' in field_names:
        qs = qs.select_related('company')

    # Exclude invalid synthetic and soft-removed records by default
    if 'status' in field_names and request.GET.get('include_invalid') != 'true':
        qs = qs.exclude(status__in=['INVALID_SYNTHETIC', 'REMOVED'])

    # Optional filter by company_id
    cid = request.GET.get('company_id', '').strip()
    if cid:
        if 'company_id' in field_names:
            qs = qs.filter(company_id=cid)
        elif 'company' in field_names:
            qs = qs.filter(company__company_id=cid)

    # If verification queue, optionally scope to borderline items if not requested all
    if entity == 'queue' and request.GET.get('all') != 'true':
        qs = qs.filter(confidence__gte=0.60, confidence__lte=0.95)

    timestamp_str = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f"{entity}_details_all_records_{timestamp_str}" if not cid else f"{entity}_{cid}_details_{timestamp_str}"

    if export_format == 'json':
        records_list = [serialize_record(obj, schema) for obj in qs]
        payload = {
            'entity': entity,
            'label': schema['label'],
            'exported_at': timezone.now().isoformat(),
            'total_records': len(records_list),
            'records': records_list
        }
        response = HttpResponse(json.dumps(payload, indent=2, default=str), content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}.json"'
        return response

    # Default to CSV export
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=schema['export_fields'], extrasaction='ignore')
    writer.writeheader()

    for obj in qs:
        writer.writerow(serialize_record(obj, schema))

    # Add UTF-8 BOM for Microsoft Excel compatibility
    csv_content = '\ufeff' + output.getvalue()
    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    return response


@login_required
def sample_template_view(request, entity):
    """
    Generates a clean CSV or JSON template with correct column headers and a real sample row.
    """
    schema = ENTITY_SCHEMAS.get(entity)
    if not schema:
        return HttpResponse("Invalid entity.", status=400)

    export_format = request.GET.get('format', 'csv').lower()
    fields = schema['import_fields']

    # Fetch one existing record if present to provide real format example
    sample_data = {}
    existing = schema['model'].objects.first()
    if existing:
        full_rec = serialize_record(existing, schema)
        for f in fields:
            sample_data[f] = full_rec.get(f, '')
    else:
        for f in fields:
            sample_data[f] = ''

    filename = f"{entity}_import_template"

    if export_format == 'json':
        payload = {
            'instructions': f"Fill in records list below for {schema['label']} and upload via Custom Admin Portal.",
            'required_fields': schema.get('required_fields', []),
            'sample_records': [sample_data]
        }
        response = HttpResponse(json.dumps(payload, indent=2), content_type='application/json; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}.json"'
        return response

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerow(sample_data)

    csv_content = '\ufeff' + output.getvalue()
    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    return response


@login_required
@require_http_methods(["POST"])
def import_entity_view(request, entity):
    # [STRICT_EXPORT_ONLY_GUARD]
    from django.http import HttpResponseForbidden
    return HttpResponseForbidden('CSV/JSON import for crawled records is disabled. All records must come from verified live crawls.')
    """
    Parses and imports data from CSV or JSON with validation, upsert/insert mode, and AuditTrail.
    """
    schema = ENTITY_SCHEMAS.get(entity)
    if not schema:
        messages.error(request, "Invalid entity specified for data import.")
        return redirect(request.META.get('HTTP_REFERER', 'admin_portal:dashboard'))

    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        messages.error(request, "Please select a valid CSV or JSON file to import.")
        return redirect(request.META.get('HTTP_REFERER', 'admin_portal:dashboard'))

    mode = request.POST.get('mode', 'upsert')  # 'upsert' or 'insert_only'
    model = schema['model']
    pk_field = schema['pk']
    converters = schema.get('type_converters', {})
    fk_configs = schema.get('fk_lookups', {})
    required_fields = schema.get('required_fields', [])

    # Read and parse file
    raw_content = uploaded_file.read()
    records_to_process = []

    try:
        # Detect JSON vs CSV
        filename_lower = uploaded_file.name.lower()
        if filename_lower.endswith('.json') or uploaded_file.content_type == 'application/json':
            text = raw_content.decode('utf-8-sig', errors='replace')
            parsed_json = json.loads(text)
            if isinstance(parsed_json, list):
                # Detect and unpack Django dumpdata format: [{"model": "admin_panel.xyz", "pk": ..., "fields": {...}}]
                if parsed_json and isinstance(parsed_json[0], dict) and 'model' in parsed_json[0] and 'fields' in parsed_json[0]:
                    target_model_name = f"admin_panel.{model._meta.model_name}".lower()
                    filtered = []
                    for item in parsed_json:
                        if str(item.get('model', '')).lower() == target_model_name:
                            rec = dict(item.get('fields', {}))
                            rec[pk_field] = item.get('pk')
                            if 'company' in rec and 'company_id' not in rec:
                                rec['company_id'] = rec['company']
                            filtered.append(rec)
                    records_to_process = filtered
                else:
                    records_to_process = parsed_json
            elif isinstance(parsed_json, dict) and 'records' in parsed_json and isinstance(parsed_json['records'], list):
                records_to_process = parsed_json['records']
            elif isinstance(parsed_json, dict) and 'sample_records' in parsed_json:
                records_to_process = parsed_json['sample_records']
            else:
                records_to_process = [parsed_json]
        else:
            # Treat as CSV
            text = raw_content.decode('utf-8-sig', errors='replace')
            csv_reader = csv.DictReader(io.StringIO(text))
            records_to_process = [row for row in csv_reader]
    except Exception as e:
        messages.error(request, f"Error decoding file format: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER', 'admin_portal:dashboard'))

    return _execute_import_records(schema, records_to_process, mode=mode, request=request, source_label=uploaded_file.name)


def _execute_import_records(schema, records_to_process, mode, request, source_label="file"):
    """
    Core ACID transaction engine for importing records into a schema model with AuditTrail logging.
    """
    if not records_to_process:
        messages.warning(request, f"No records found to import for {schema['label']}.")
        return redirect(request.META.get('HTTP_REFERER', 'admin_portal:dashboard'))

    model = schema['model']
    pk_field = schema['pk']
    converters = schema.get('type_converters', {})
    fk_configs = schema.get('fk_lookups', {})
    required_fields = schema.get('required_fields', [])
    entity = [k for k, v in ENTITY_SCHEMAS.items() if v['model'] == model][0]

    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []

    # Cache companies for fast FK resolution
    company_cache = {}
    if fk_configs:
        for c in Company.objects.all():
            company_cache[c.company_id.strip().lower()] = c
            company_cache[c.company_name.strip().lower()] = c

    try:
        with transaction.atomic():
            for idx, raw_row in enumerate(records_to_process, start=1):
                # Clean keys and values
                row = {k.strip(): v for k, v in raw_row.items() if k}

                # Check required fields
                missing = [rf for rf in required_fields if not row.get(rf)]
                if missing:
                    errors.append(f"Row {idx}: Missing required field(s): {', '.join(missing)}")
                    skipped_count += 1
                    continue

                # Prepare field payload
                model_data = {}
                for field in schema['import_fields']:
                    if field in row:
                        val = row[field]
                        if field in converters:
                            model_data[field] = converters[field](val)
                        else:
                            model_data[field] = _clean_str(val)

                # Resolve Foreign Keys
                fk_error = False
                for fk_name, fk_info in fk_configs.items():
                    target_field = fk_info['target_field']
                    id_val = str(row.get(fk_info['fk_id_key'], row.get('company', ''))).strip().lower()
                    alt_val = str(row.get(fk_info.get('alt_key', ''), '')).strip().lower()

                    matched_obj = company_cache.get(id_val) or (company_cache.get(alt_val) if alt_val else None)
                    if matched_obj:
                        model_data[target_field] = matched_obj
                    else:
                        field_meta = model._meta.get_field(target_field)
                        if not field_meta.null:
                            errors.append(f"Row {idx}: Could not match required {fk_name} with ID '{id_val}' or Name '{alt_val}'")
                            fk_error = True
                            break
                        else:
                            model_data[target_field] = None

                if fk_error:
                    skipped_count += 1
                    continue

                # Determine whether PK exists
                pk_val = row.get(pk_field)
                if pk_val is not None:
                    pk_val = str(pk_val).strip()
                    if pk_val == '' or pk_val == '0':
                        pk_val = None

                existing_instance = None
                if pk_val is not None:
                    try:
                        existing_instance = model.objects.filter(**{pk_field: pk_val}).first()
                    except Exception:
                        existing_instance = None

                # Secondary matching for duplicates
                if not existing_instance:
                    if entity == 'companies' and row.get('company_id'):
                        existing_instance = Company.objects.filter(company_id=row['company_id']).first()
                    elif entity == 'users' and row.get('username'):
                        existing_instance = User.objects.filter(username=row['username']).first()
                    elif entity == 'subscriptions' and row.get('tenant_id'):
                        existing_instance = Subscription.objects.filter(tenant_id=row['tenant_id']).first()
                    elif entity == 'promos' and row.get('code'):
                        existing_instance = PromoCode.objects.filter(code=row['code'].strip().upper()).first()
                    elif 'fingerprint' in row and row.get('fingerprint'):
                        existing_instance = model.objects.filter(fingerprint=row['fingerprint']).first()

                if existing_instance:
                    if mode == 'insert_only':
                        skipped_count += 1
                        continue

                    # Update existing
                    for k, v in model_data.items():
                        if k != pk_field or pk_val is not None:
                            setattr(existing_instance, k, v)
                    existing_instance.save()
                    updated_count += 1
                else:
                    # Create new instance
                    if entity == 'users':
                        username = model_data.get('username')
                        email = model_data.get('email', '')
                        user_obj = User(username=username, email=email)
                        for k, v in model_data.items():
                            if k not in ('id', 'password'):
                                setattr(user_obj, k, v)
                        user_obj.set_password(os.environ.get('ADMIN_EXCHANGE_PASSWORD', ''))
                        if user_obj.role in (User.ROLE_ADMIN, User.ROLE_STAFF):
                            user_obj.is_staff = True
                            if user_obj.role == User.ROLE_ADMIN:
                                user_obj.is_superuser = True
                        user_obj.save()
                    else:
                        if pk_field in model_data and model_data[pk_field] is None:
                            del model_data[pk_field]
                        model.objects.create(**model_data)
                    created_count += 1

            # Log to immutable AuditTrail
            AuditTrail.objects.create(
                record_type=f"IMPORT_{entity.upper()}",
                record_id=f"SYNC_{timezone.now().strftime('%Y%m%d%H%M%S')}",
                action='DATA_IMPORT',
                previous_value='N/A',
                new_value=f"Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}",
                user_role=getattr(request.user, 'role', 'ADMIN'),
                notes=f"Source: '{source_label}' | Strategy: '{mode}' | Processed: {len(records_to_process)} records",
                timestamp=timezone.now().isoformat()
            )

    except Exception as e:
        messages.error(request, f"Import transaction failed: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER', 'admin_portal:dashboard'))

    # Flash success message
    msg = f"Import completed for {schema['label']}: {created_count} record(s) created, {updated_count} record(s) updated from {source_label}."
    if skipped_count:
        msg += f" {skipped_count} record(s) skipped."
    messages.success(request, msg)

    if errors:
        for err in errors[:5]:
            messages.warning(request, err)
        if len(errors) > 5:
            messages.warning(request, f"... and {len(errors) - 5} more row warnings.")

    return redirect(request.META.get('HTTP_REFERER', 'admin_portal:dashboard'))


@login_required
def quick_sync_entity_view(request, entity):
    """
    1-Click direct synchronization of authentic database records from server's master backup
    (data/db_backup_20260929_173023.json) into the active database for the selected section.
    """
    schema = ENTITY_SCHEMAS.get(entity)
    if not schema:
        messages.error(request, f"Invalid entity: '{entity}'.")
        return redirect(request.META.get('HTTP_REFERER', 'admin_portal:dashboard'))

    from django.conf import settings
    backup_file = None
    data_dir = settings.BASE_DIR / 'data'
    if data_dir.exists():
        candidates = list(data_dir.glob('db_backup_*.json'))
        if candidates:
            candidates.sort(reverse=True)
            backup_file = candidates[0]
        elif (data_dir / 'db_backup_20260929_173023.json').exists():
            backup_file = data_dir / 'db_backup_20260929_173023.json'

    if not backup_file or not backup_file.exists():
        messages.error(request, "Master backup file (data/db_backup_*.json) not found on server.")
        return redirect(request.META.get('HTTP_REFERER', 'admin_portal:dashboard'))

    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            dump_data = json.load(f)
    except Exception as e:
        messages.error(request, f"Could not read backup file: {str(e)}")
        return redirect(request.META.get('HTTP_REFERER', 'admin_portal:dashboard'))

    model = schema['model']
    target_model_name = f"admin_panel.{model._meta.model_name}".lower()
    pk_field = schema['pk']

    records = []
    for item in dump_data:
        if str(item.get('model', '')).lower() == target_model_name:
            rec = dict(item.get('fields', {}))
            rec[pk_field] = item.get('pk')
            if 'company' in rec and 'company_id' not in rec:
                rec['company_id'] = rec['company']
            records.append(rec)

    if not records:
        messages.warning(request, f"No records found for {schema['label']} in master backup '{backup_file.name}'.")
        return redirect(request.META.get('HTTP_REFERER', 'admin_portal:dashboard'))

    return _execute_import_records(schema, records, mode='upsert', request=request, source_label=f"Master Backup ({backup_file.name})")


@login_required
def sync_all_master_backup_view(request):
    """
    1-Click Master Synchronization: Synchronizes all platform entities from the server's master backup.
    """
    from django.conf import settings
    backup_file = None
    data_dir = settings.BASE_DIR / 'data'
    if data_dir.exists():
        candidates = list(data_dir.glob('db_backup_*.json'))
        if candidates:
            candidates.sort(reverse=True)
            backup_file = candidates[0]

    if not backup_file or not backup_file.exists():
        messages.error(request, "Master backup file not found in data/ directory.")
        return redirect('admin_portal:dashboard')

    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            dump_data = json.load(f)
    except Exception as e:
        messages.error(request, f"Failed reading master backup: {str(e)}")
        return redirect('admin_portal:dashboard')

    # Order of synchronization to satisfy foreign keys
    sync_order = ['companies', 'jobs', 'opportunities', 'projects', 'users', 'subscriptions', 'invoices', 'promos', 'pages']
    total_synced = 0

    for entity in sync_order:
        schema = ENTITY_SCHEMAS.get(entity)
        if not schema:
            continue
        model = schema['model']
        target_model_name = f"admin_panel.{model._meta.model_name}".lower()
        pk_field = schema['pk']

        records = []
        for item in dump_data:
            if str(item.get('model', '')).lower() == target_model_name:
                rec = dict(item.get('fields', {}))
                rec[pk_field] = item.get('pk')
                if 'company' in rec and 'company_id' not in rec:
                    rec['company_id'] = rec['company']
                records.append(rec)

        if records:
            _execute_import_records(schema, records, mode='upsert', request=request, source_label=f"Master Sync: {entity}")
            total_synced += len(records)

    messages.success(request, f"⚡ Full Platform Sync Complete: Processed {total_synced} authentic records across all sections from {backup_file.name}!")
    return redirect('admin_portal:dashboard')


SECTION_METADATA = {
    'companies': {
        'icon': '🏢',
        'desc': 'Complete directory of 200 top NSE corporations with verified ISIN, CIN, headquarters, sector taxonomy, careers URLs, CSR portals and domain quality scores.'
    },
    'jobs': {
        'icon': '💼',
        'desc': 'Verified corporate job openings across all 200 companies, covering Tech/IT, Engineering, Finance, Operations, Sales, HR, CSR, Healthcare, and Legal with direct application links.'
    },
    'projects': {
        'icon': '🌱',
        'desc': 'Statutory CSR projects under Companies Act Section 135, Schedule VII thematic categories, sanctioned budgets, geographic states, and verification evidence.'
    },
    'opportunities': {
        'icon': '📢',
        'desc': 'Open corporate grant RFPs, call-for-proposals, thematic eligibility criteria, application submission deadlines, and verified RFP portal links.'
    },
    'contacts': {
        'icon': '👥',
        'desc': 'Corporate governance key personnel, CSR Committee members, Sustainability Directors, and Company Secretaries with official designation and contact data.'
    },
    'collaborations': {
        'icon': '🤝',
        'desc': 'Historical and active corporate-NGO partnerships, multi-year strategic alliances, relationship classifications, and implementation footprints.'
    },
    'scores': {
        'icon': '🎯',
        'desc': 'Algorithmic 7-pillar opportunity scores, active CSR index, focus thematic alignment, contact accessibility, and empirical scoring rationales.'
    },
    'documents': {
        'icon': '📁',
        'desc': 'Uploaded CSR policies, annual CSR reports, project proposals, FCRA certificates, and 80G/12A non-profit verification documents.'
    },
    'pages': {
        'icon': '🌐',
        'desc': 'Web crawler telemetry records, HTTP status codes, discovered URLs, sitemaps, robots.txt, and page content hashes.'
    },
    'audits': {
        'icon': '📜',
        'desc': 'Immutable platform audit trail logging data imports, administrative edits, compliance approvals, and system state transitions.'
    },
    'users': {
        'icon': '👤',
        'desc': 'Registered enterprise users, NGO managers, staff members, super administrators, organizations, and authentication metadata.'
    },
    'subscriptions': {
        'icon': '💎',
        'desc': 'Active tenant subscription plans, seat allocations, billing cycles, GST invoicing attributes, and API license keys.'
    },
    'invoices': {
        'icon': '🧾',
        'desc': 'Tax invoices, taxable amounts, CGST/SGST/IGST breakdowns, GSTIN place-of-supply details, and payment reconciliation statuses.'
    },
    'promos': {
        'icon': '🎟️',
        'desc': 'Promotional discount codes, percentage offsets, redemption caps, usage counters, and validity period parameters.'
    },
    'prospects': {
        'icon': '📌',
        'desc': 'Target donor pipeline, NGO saved prospecting lists, pipeline stages, strategic match scores, and partner outreach notes.'
    },
    'queue': {
        'icon': '🛡️',
        'desc': 'CSR projects and records awaiting human verification, confidence ranking review, and evidence auditing.'
    },
}


@login_required
def download_hub_view(request):
    """
    Central Data Download Hub:
    Enables administrators to download each and every detail from each and every section
    of the intelligence platform in CSV, JSON, and complete master archives.
    """
    sections = []
    total_records = 0

    # Display order for sections in the Download Hub
    order = [
        'companies', 'jobs', 'projects', 'opportunities',
        'contacts', 'collaborations', 'scores', 'documents',
        'pages', 'audits', 'users', 'subscriptions',
        'invoices', 'promos', 'prospects', 'queue'
    ]

    for key in order:
        schema = ENTITY_SCHEMAS.get(key)
        if not schema:
            continue
        model = schema['model']
        meta = SECTION_METADATA.get(key, {'icon': '📦', 'desc': 'Platform intelligence records and attributes.'})
        
        try:
            count = model.objects.count()
        except Exception:
            count = 0

        total_records += count

        sections.append({
            'key': key,
            'title': schema['label'],
            'icon': meta.get('icon', '📦'),
            'desc': meta.get('desc', ''),
            'model_name': model.__name__,
            'table_name': model._meta.db_table,
            'count': count,
            'fields': schema['export_fields'],
            'fields_count': len(schema['export_fields']),
            'csv_url': f"{reverse('admin_portal:data_export', args=[key])}?format=csv",
            'json_url': f"{reverse('admin_portal:data_export', args=[key])}?format=json",
            'template_csv_url': f"{reverse('admin_portal:data_template', args=[key])}?format=csv",
            'template_json_url': f"{reverse('admin_portal:data_template', args=[key])}?format=json",
            'quick_sync_url': reverse('admin_portal:quick_sync', args=[key]),
        })

    context = {
        'sections': sections,
        'total_sections': len(sections),
        'total_records': total_records,
        'current_time': timezone.now().strftime('%d %B %Y, %I:%M %p UTC'),
    }
    return render(request, 'admin/downloads/index.html', context)


@login_required
def download_all_archive_view(request):
    """
    One-Click Master Extraction:
    Packages all platform sections into a single compressed ZIP file containing
    high-fidelity CSV files for every database entity plus a system manifest.
    """
    zip_buffer = io.BytesIO()
    timestamp_str = timezone.now().strftime('%Y%m%d_%H%M%S')
    manifest = {
        'platform': 'ImpactBridge CSR & Job Intelligence OS',
        'extracted_at': timezone.now().isoformat(),
        'extracted_by': request.user.username,
        'sections': {}
    }

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for key, schema in ENTITY_SCHEMAS.items():
            model = schema['model']
            qs = model.objects.all()
            if 'company' in [f.name for f in model._meta.fields]:
                qs = qs.select_related('company')

            # Write CSV
            csv_output = io.StringIO()
            writer = csv.DictWriter(csv_output, fieldnames=schema['export_fields'], extrasaction='ignore')
            writer.writeheader()

            row_count = 0
            for obj in qs:
                row_dict = serialize_record(obj, schema)
                writer.writerow(row_dict)
                row_count += 1

            zip_file.writestr(f"{key}.csv", csv_output.getvalue().encode('utf-8'))
            manifest['sections'][key] = {
                'label': schema['label'],
                'model': model.__name__,
                'record_count': row_count,
                'fields': schema['export_fields']
            }

        # Write manifest.json
        zip_file.writestr('MANIFEST.json', json.dumps(manifest, indent=2).encode('utf-8'))

        # Write README.txt
        readme_text = (
            f"ImpactBridge Intelligence OS — Master Database Export\n"
            f"Generated: {timezone.now().isoformat()}\n"
            f"User: {request.user.username}\n"
            f"Total Sections: {len(ENTITY_SCHEMAS)}\n\n"
            f"This archive contains complete, authentic CSV records for every section of the system.\n"
            f"All relations are mapped via primary keys (company_id, job_row_id, etc.).\n"
        )
        zip_file.writestr('README.txt', readme_text.encode('utf-8'))

    zip_buffer.seek(0)
    filename = f"ImpactBridge_Master_Intelligence_All_Sections_{timestamp_str}.zip"
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

