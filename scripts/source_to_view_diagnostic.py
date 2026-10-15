#!/usr/bin/env python
"""
Source-to-View Data Integrity Diagnostic Tool (Part 10).

Traces sampled and affected jobs across companies and ATS platforms:
Official Job Detail URL -> HTTP Response -> Parsed Headings -> DB Record -> Django API Serializer -> View Card Mapping.
Reports missing-field counts, root causes, evidence references, and verification status.
"""

import os
import sys
import json
from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models.company import Company
from modules.admin_panel.models.job import Job
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor
from modules.website.views.job_api_views import serialize_job_item


def diagnose_job(job_row_id):
    """Deep trace of a single job through the entire pipeline."""
    job = Job.objects.select_related('company').filter(job_row_id=job_row_id).first()
    if not job:
        return {"error": f"Job row {job_row_id} not found"}

    app_url = job.application_url or job.source_url or ''
    diag = {
        "job_row_id": job.job_row_id,
        "company_id": job.company.company_id,
        "company_name": job.company.company_name,
        "external_requisition_id": job.external_job_id or job.job_id,
        "original_listing_url": job.source_url,
        "actual_detail_page_url": app_url,
        "source_ats_provider": job.ats_platform or "Direct Careers Portal",
        "detail_page_fetched": bool(job.detail_fetched),
        "detail_fetch_status": getattr(job, 'detail_fetch_status', 'NOT_FETCHED'),
        "verification_status": job.verification_status,
        "stage_1_extraction": {},
        "stage_2_database_persistence": {},
        "stage_3_api_response": {},
        "stage_4_view_card_mapping": {},
        "missing_fields": [],
        "pipeline_integrity_status": "PASS"
    }

    # Stage 1: Extraction test
    if app_url.startswith('http'):
        extracted = UniversalJobDetailExtractor.extract_from_url(app_url)
        diag["stage_1_extraction"] = {
            "fetch_status": extracted.get("detail_fetch_status"),
            "final_url_after_redirects": extracted.get("final_url"),
            "extracted_source_headings": list(extracted.get("structured_details", {}).keys()),
            "extracted_fields_present": [k for k, v in extracted.items() if v and k != "structured_details"]
        }
    else:
        diag["stage_1_extraction"] = {"error": "No valid HTTP detail URL"}

    # Stage 2: Database Persistence
    db_fields = {}
    for f in [
        'job_title', 'external_job_id', 'posted_date', 'location', 'city', 'state', 'country',
        'function', 'department', 'pay_band', 'salary', 'salary_currency', 'role_purpose',
        'responsibilities', 'day_in_the_life', 'qualifications', 'education', 'experience',
        'technical_skills', 'behavioural_skills', 'skills', 'employer_info', 'detail_fetched',
        'detail_fetch_status'
    ]:
        val = getattr(job, f, None)
        if val is not None and str(val).strip():
            db_fields[f] = str(val)[:60] + ('...' if len(str(val)) > 60 else '')
    diag["stage_2_database_persistence"] = db_fields

    # Stage 3: Django API Serializer
    api_data = serialize_job_item(job)
    api_fields = {}
    for f in [
        'job_title', 'external_job_id', 'posted_date', 'location', 'city', 'state', 'country',
        'function', 'department', 'pay_band', 'salary', 'salary_currency', 'role_purpose',
        'responsibilities', 'day_in_the_life', 'qualifications', 'education', 'experience',
        'technical_skills', 'behavioural_skills', 'skills', 'employer_info', 'detail_fetched',
        'detail_fetch_status'
    ]:
        val = api_data.get(f)
        if val is not None and str(val).strip():
            api_fields[f] = str(val)[:60] + ('...' if len(str(val)) > 60 else '')
    diag["stage_3_api_response"] = api_fields

    # Stage 4: View Card Mapping (Universal 12 Sections)
    view_sections = {
        "1_job_header": {
            "title": api_data.get('job_title'),
            "verification_badge": api_data.get('verification_status'),
            "detail_status": api_data.get('detail_fetch_status')
        },
        "2_key_job_details": {
            "location": api_data.get('location') or "Not mentioned by source",
            "type": api_data.get('employment_type') or "Not mentioned by source",
            "experience": api_data.get('experience') or "Not mentioned by source",
            "department": api_data.get('department') or "Not mentioned by source",
            "function": api_data.get('function') or "Not mentioned by source",
            "posted_date": api_data.get('posted_date') or "Not mentioned by source",
            "requisition_id": api_data.get('external_job_id') or "Not mentioned by source"
        },
        "3_position_description_and_role": {
            "role_purpose": bool(api_data.get('role_purpose')),
            "job_description_present": bool(api_data.get('job_description'))
        },
        "4_responsibilities": {
            "present": bool(api_data.get('responsibilities'))
        },
        "5_qualifications_and_experience": {
            "qualifications_present": bool(api_data.get('qualifications'))
        },
        "6_education": {
            "education_present": bool(api_data.get('education'))
        },
        "7_technical_and_behavioural_skills": {
            "technical_skills_present": bool(api_data.get('technical_skills')),
            "behavioural_skills_present": bool(api_data.get('behavioural_skills')),
            "skills_present": bool(api_data.get('skills'))
        },
        "8_compensation_and_benefits": {
            "salary_present": bool(api_data.get('salary')),
            "pay_band_present": bool(api_data.get('pay_band')),
            "benefits_present": bool(api_data.get('benefits'))
        },
        "9_additional_source_provided_info": {
            "day_in_the_life_present": bool(api_data.get('day_in_the_life')),
            "employer_info_present": bool(api_data.get('employer_info'))
        },
        "10_application_action": {
            "apply_url_present": bool(api_data.get('application_url'))
        },
        "11_source_provenance_and_verification": {
            "source_url_present": bool(api_data.get('source_url')),
            "hash_present": bool(api_data.get('fingerprint'))
        },
        "12_related_openings": {
            "company_id_match": bool(api_data.get('company_id'))
        }
    }
    diag["stage_4_view_card_mapping"] = view_sections

    # Check for lost fields between DB and API
    for db_k in db_fields:
        if db_k not in api_fields:
            diag["missing_fields"].append({
                "field": db_k,
                "cause": "Field exists in DB but omitted by API serializer"
            })
            diag["pipeline_integrity_status"] = "FAIL"

    return diag


def run_sampling_diagnostics():
    print("======================================================================")
    print("RUNNING SOURCE-TO-VIEW DATA INTEGRITY DIAGNOSTIC ACROSS ATS PROVIDERS")
    print("======================================================================")

    # Sample jobs from different ATS providers
    sample_queries = [
        {"desc": "Hero MotoCorp (SAP SuccessFactors CSB)", "q": Job.objects.filter(company__company_name__icontains='Hero', job_title__icontains='TERRITORY MANAGER-SALES').first()},
        {"desc": "Mahindra (SAP SuccessFactors)", "q": Job.objects.filter(company__company_name__icontains='Mahindra', application_url__icontains='mahindracareers').first()},
        {"desc": "Hindustan Unilever (Workday)", "q": Job.objects.filter(company__company_name__icontains='Unilever', application_url__icontains='myworkdayjobs').first()},
        {"desc": "Dr. Reddy's (SmartRecruiters)", "q": Job.objects.filter(company__company_name__icontains='Reddy', application_url__icontains='smartrecruiters').first()},
        {"desc": "Generic Company Careers Site", "q": Job.objects.filter(detail_fetched=True).exclude(company__company_name__icontains='Hero').first()},
    ]

    results = []
    for s in sample_queries:
        job = s["q"]
        if not job:
            continue
        print(f"\nTracing Sample: {s['desc']} (Job {job.job_row_id})")
        diag = diagnose_job(job.job_row_id)
        results.append(diag)
        print(f"  Company: {diag['company_name']}")
        print(f"  Title: {job.job_title}")
        print(f"  Detail URL: {diag['actual_detail_page_url']}")
        print(f"  Detail Fetched: {diag['detail_page_fetched']} ({diag['detail_fetch_status']})")
        print(f"  DB Fields Present: {len(diag['stage_2_database_persistence'])}")
        print(f"  API Fields Present: {len(diag['stage_3_api_response'])}")
        print(f"  Integrity Status: {diag['pipeline_integrity_status']}")

    out_file = Path(__file__).resolve().parent.parent / "data" / "source_to_view_diagnostic_report.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nDiagnostic results written to {out_file}")
    return results


if __name__ == "__main__":
    run_sampling_diagnostics()
