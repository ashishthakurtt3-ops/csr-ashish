#!/usr/bin/env python
"""
Complete Audit of Existing Jobs across all 200 Companies (Section 2).
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

from modules.admin_panel.models import Company, Job
from django.db.models import Count, Q


def run_full_audit():
    print("======================================================================")
    print("AUDITING EXISTING JOBS ACROSS ALL 200 CANONICAL COMPANIES")
    print("======================================================================")

    companies = list(Company.objects.all().order_by('company_name'))
    total_companies = len(companies)
    print(f"Total Companies in Registry: {total_companies}")

    overall_stats = {
        "total_companies": total_companies,
        "companies_with_jobs": 0,
        "companies_without_jobs": 0,
        "total_all_jobs": Job.objects.count(),
        "total_active_jobs": Job.objects.filter(status='ACTIVE').count(),
        "total_detail_fetched": Job.objects.filter(detail_fetched=True).count(),
        "total_unfetched": Job.objects.filter(detail_fetched=False).count(),
        "status_breakdown": {},
        "field_population_summary": {
            "has_description": 0,
            "has_responsibilities": 0,
            "has_qualifications": 0,
            "has_education": 0,
            "has_experience": 0,
            "has_pay_band": 0,
            "has_function": 0,
            "has_department": 0,
            "has_skills": 0,
            "has_structured_details": 0,
        },
        "company_breakdown": []
    }

    # Status counts
    for s in ['FETCHED', 'NOT_FETCHED', 'EXTRACTION_FAILED', 'SOURCE_UNAVAILABLE']:
        overall_stats["status_breakdown"][s] = Job.objects.filter(detail_fetch_status=s).count()

    # Field population on active jobs
    active_qs = Job.objects.filter(status='ACTIVE')
    overall_stats["field_population_summary"]["has_description"] = active_qs.exclude(job_description__isnull=True).exclude(job_description='').count()
    overall_stats["field_population_summary"]["has_responsibilities"] = active_qs.exclude(responsibilities__isnull=True).exclude(responsibilities='').count()
    overall_stats["field_population_summary"]["has_qualifications"] = active_qs.exclude(qualifications__isnull=True).exclude(qualifications='').count()
    overall_stats["field_population_summary"]["has_education"] = active_qs.exclude(education__isnull=True).exclude(education='').count()
    overall_stats["field_population_summary"]["has_experience"] = active_qs.exclude(experience__isnull=True).exclude(experience='').count()
    overall_stats["field_population_summary"]["has_pay_band"] = active_qs.exclude(pay_band__isnull=True).exclude(pay_band='').count()
    overall_stats["field_population_summary"]["has_function"] = active_qs.exclude(function__isnull=True).exclude(function='').count()
    overall_stats["field_population_summary"]["has_department"] = active_qs.exclude(department__isnull=True).exclude(department='').count()
    overall_stats["field_population_summary"]["has_skills"] = active_qs.filter(
        Q(skills__isnull=False, skills__gt='') |
        Q(technical_skills__isnull=False, technical_skills__gt='') |
        Q(behavioural_skills__isnull=False, behavioural_skills__gt='')
    ).count()
    overall_stats["field_population_summary"]["has_structured_details"] = active_qs.exclude(structured_details__isnull=True).exclude(structured_details={}).count()

    incomplete_jobs_list = []

    for c in companies:
        c_jobs = Job.objects.filter(company=c)
        total_c_jobs = c_jobs.count()
        active_c_jobs = c_jobs.filter(status='ACTIVE').count()

        if total_c_jobs > 0:
            overall_stats["companies_with_jobs"] += 1
        else:
            overall_stats["companies_without_jobs"] += 1

        fetched_count = c_jobs.filter(detail_fetched=True).count()
        unfetched_count = c_jobs.filter(detail_fetched=False).count()
        eligible_for_backfill = c_jobs.filter(status='ACTIVE', detail_fetched=False).exclude(application_url__isnull=True).exclude(application_url='').count()

        c_row = {
            "company_id": c.company_id,
            "company_name": c.company_name,
            "careers_url": c.careers_url or "",
            "total_jobs": total_c_jobs,
            "active_jobs": active_c_jobs,
            "detail_fetched": fetched_count,
            "detail_unfetched": unfetched_count,
            "eligible_for_backfill": eligible_for_backfill,
            "fetch_status": {
                "FETCHED": c_jobs.filter(detail_fetch_status='FETCHED').count(),
                "NOT_FETCHED": c_jobs.filter(detail_fetch_status='NOT_FETCHED').count(),
                "EXTRACTION_FAILED": c_jobs.filter(detail_fetch_status='EXTRACTION_FAILED').count(),
                "SOURCE_UNAVAILABLE": c_jobs.filter(detail_fetch_status='SOURCE_UNAVAILABLE').count(),
            },
            "field_counts": {
                "description": c_jobs.exclude(job_description__isnull=True).exclude(job_description='').count(),
                "responsibilities": c_jobs.exclude(responsibilities__isnull=True).exclude(responsibilities='').count(),
                "qualifications": c_jobs.exclude(qualifications__isnull=True).exclude(qualifications='').count(),
                "education": c_jobs.exclude(education__isnull=True).exclude(education='').count(),
                "experience": c_jobs.exclude(experience__isnull=True).exclude(experience='').count(),
                "pay_band": c_jobs.exclude(pay_band__isnull=True).exclude(pay_band='').count(),
                "function": c_jobs.exclude(function__isnull=True).exclude(function='').count(),
                "skills": c_jobs.filter(
                    Q(skills__isnull=False, skills__gt='') |
                    Q(technical_skills__isnull=False, technical_skills__gt='') |
                    Q(behavioural_skills__isnull=False, behavioural_skills__gt='')
                ).count(),
            }
        }
        overall_stats["company_breakdown"].append(c_row)

        # Track incomplete active jobs
        for j in c_jobs.filter(status='ACTIVE'):
            if not j.detail_fetched or not j.responsibilities or not j.job_description:
                if len(incomplete_jobs_list) < 500:
                    incomplete_jobs_list.append({
                        "job_row_id": j.job_row_id,
                        "company_id": c.company_id,
                        "company_name": c.company_name,
                        "job_title": j.job_title,
                        "detail_fetched": j.detail_fetched,
                        "detail_fetch_status": j.detail_fetch_status,
                        "application_url": j.application_url or "",
                        "missing_fields": [
                            f for f, has in [
                                ('job_description', bool(j.job_description)),
                                ('responsibilities', bool(j.responsibilities)),
                                ('qualifications', bool(j.qualifications)),
                                ('education', bool(j.education)),
                                ('experience', bool(j.experience)),
                                ('pay_band', bool(j.pay_band)),
                                ('function', bool(j.function)),
                            ] if not has
                        ]
                    })

    os.makedirs(project_dir / 'data', exist_ok=True)
    out_file = project_dir / 'data' / 'company_jobs_audit.json'
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump({
            "overall_stats": overall_stats,
            "incomplete_sample": incomplete_jobs_list
        }, f, indent=2)

    print(f"Audit completed successfully!")
    print(f"Total Companies with jobs: {overall_stats['companies_with_jobs']}/{total_companies}")
    print(f"Total Active Jobs: {overall_stats['total_active_jobs']}")
    print(f"Detail Fetched: {overall_stats['total_detail_fetched']}")
    print(f"Unfetched: {overall_stats['total_unfetched']}")
    print(f"Audit output written to: {out_file}")
    return overall_stats


if __name__ == '__main__':
    run_full_audit()
