import os
import sys
import django
import json

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection

cursor = connection.cursor()

def q(sql):
    cursor.execute(sql)
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]

stats = {}

# Company stats
stats['company_listing_status'] = q("SELECT listing_status, COUNT(*) as cnt FROM admin_panel_company GROUP BY listing_status")
stats['company_crawl_status'] = q("SELECT crawl_status, COUNT(*) as cnt FROM admin_panel_company GROUP BY crawl_status")
stats['company_data_confidence'] = q("SELECT data_confidence, COUNT(*) as cnt FROM admin_panel_company GROUP BY data_confidence")
stats['company_ats_platform'] = q("SELECT ats_platform, COUNT(*) as cnt FROM admin_panel_company GROUP BY ats_platform ORDER BY cnt DESC")
stats['company_careers_url_confidence'] = q("SELECT careers_url_confidence, COUNT(*) as cnt FROM admin_panel_company GROUP BY careers_url_confidence")
stats['company_has_careers_url'] = q("SELECT (careers_url IS NOT NULL AND careers_url != '') as has_careers, COUNT(*) as cnt FROM admin_panel_company GROUP BY (careers_url IS NOT NULL AND careers_url != '')")
stats['company_has_csr_url'] = q("SELECT (csr_portal_url IS NOT NULL AND csr_portal_url != '') as has_csr, COUNT(*) as cnt FROM admin_panel_company GROUP BY (csr_portal_url IS NOT NULL AND csr_portal_url != '')")
stats['company_id_prefixes'] = q("SELECT LEFT(company_id, 12) as pfx, COUNT(*) as cnt FROM admin_panel_company GROUP BY pfx")
stats['company_jobs_access'] = q("SELECT jobs_access, COUNT(*) as cnt FROM admin_panel_company GROUP BY jobs_access")
stats['company_csr_access'] = q("SELECT csr_access, COUNT(*) as cnt FROM admin_panel_company GROUP BY csr_access")
stats['company_contacts_access'] = q("SELECT contacts_access, COUNT(*) as cnt FROM admin_panel_company GROUP BY contacts_access")
stats['company_sync_status'] = q("SELECT sync_status, COUNT(*) as cnt FROM admin_panel_company GROUP BY sync_status")
stats['company_website_url_status'] = q("SELECT website_url_status, COUNT(*) as cnt FROM admin_panel_company GROUP BY website_url_status")

# Job stats
stats['job_status'] = q("SELECT status, COUNT(*) as cnt FROM admin_panel_job GROUP BY status")
stats['job_verification_status'] = q("SELECT verification_status, COUNT(*) as cnt FROM admin_panel_job GROUP BY verification_status")
stats['job_link_status'] = q("SELECT link_status, COUNT(*) as cnt FROM admin_panel_job GROUP BY link_status ORDER BY cnt DESC")
stats['job_confidence'] = q("SELECT confidence, COUNT(*) as cnt FROM admin_panel_job GROUP BY confidence ORDER BY cnt DESC")
stats['job_is_defective'] = q("SELECT is_defective, COUNT(*) as cnt FROM admin_panel_job GROUP BY is_defective")
stats['job_detail_fetch_status'] = q("SELECT detail_fetch_status, COUNT(*) as cnt FROM admin_panel_job GROUP BY detail_fetch_status")
stats['job_details_status'] = q("SELECT details_status, COUNT(*) as cnt FROM admin_panel_job GROUP BY details_status")
stats['job_field_source'] = q("SELECT field_source, COUNT(*) as cnt FROM admin_panel_job GROUP BY field_source ORDER BY cnt DESC")
stats['job_work_mode'] = q("SELECT work_mode, COUNT(*) as cnt FROM admin_panel_job GROUP BY work_mode ORDER BY cnt DESC")
stats['job_employment_type'] = q("SELECT employment_type, COUNT(*) as cnt FROM admin_panel_job GROUP BY employment_type ORDER BY cnt DESC")
stats['job_ats_platform'] = q("SELECT ats_platform, COUNT(*) as cnt FROM admin_panel_job GROUP BY ats_platform ORDER BY cnt DESC LIMIT 15")

# Job null/empty rates
stats['job_null_rates'] = q("""
SELECT
    COUNT(*) as total_jobs,
    SUM(CASE WHEN location IS NULL OR location = '' THEN 1 ELSE 0 END) as empty_location,
    SUM(CASE WHEN job_description IS NULL OR job_description = '' THEN 1 ELSE 0 END) as empty_description,
    SUM(CASE WHEN responsibilities IS NULL OR responsibilities = '' THEN 1 ELSE 0 END) as empty_responsibilities,
    SUM(CASE WHEN qualifications IS NULL OR qualifications = '' THEN 1 ELSE 0 END) as empty_qualifications,
    SUM(CASE WHEN application_url IS NULL OR application_url = '' THEN 1 ELSE 0 END) as empty_application_url,
    SUM(CASE WHEN department IS NULL OR department = '' THEN 1 ELSE 0 END) as empty_department,
    SUM(CASE WHEN salary_min IS NULL AND salary_max IS NULL THEN 1 ELSE 0 END) as empty_salary,
    SUM(CASE WHEN canonical_url_hash IS NULL OR canonical_url_hash = '' THEN 1 ELSE 0 END) as empty_canonical_hash
FROM admin_panel_job
""")

# CSRProject stats
stats['csrproject_status'] = q("SELECT status, COUNT(*) as cnt FROM admin_panel_csrproject GROUP BY status")
stats['csrproject_field_source'] = q("SELECT field_source, COUNT(*) as cnt FROM admin_panel_csrproject GROUP BY field_source ORDER BY cnt DESC")
stats['csrproject_category'] = q("SELECT category, COUNT(*) as cnt FROM admin_panel_csrproject GROUP BY category ORDER BY cnt DESC LIMIT 15")
stats['csrproject_confidence'] = q("SELECT confidence, COUNT(*) as cnt FROM admin_panel_csrproject GROUP BY confidence ORDER BY cnt DESC")
stats['csrproject_link_status'] = q("SELECT link_status, COUNT(*) as cnt FROM admin_panel_csrproject GROUP BY link_status ORDER BY cnt DESC")

# CSROpportunity stats
stats['csropp_status'] = q("SELECT status, COUNT(*) as cnt FROM admin_panel_csropportunity GROUP BY status")
stats['csropp_category'] = q("SELECT category, COUNT(*) as cnt FROM admin_panel_csropportunity GROUP BY category ORDER BY cnt DESC LIMIT 15")
stats['csropp_opportunity_type'] = q("SELECT opportunity_type, COUNT(*) as cnt FROM admin_panel_csropportunity GROUP BY opportunity_type ORDER BY cnt DESC")
stats['csropp_confidence'] = q("SELECT confidence, COUNT(*) as cnt FROM admin_panel_csropportunity GROUP BY confidence ORDER BY cnt DESC")
stats['csropp_link_status'] = q("SELECT link_status, COUNT(*) as cnt FROM admin_panel_csropportunity GROUP BY link_status ORDER BY cnt DESC")

# Pages stats
stats['pages_page_type'] = q("SELECT page_type, COUNT(*) as cnt FROM pages GROUP BY page_type ORDER BY cnt DESC")
stats['pages_status'] = q("SELECT status, COUNT(*) as cnt FROM pages GROUP BY status ORDER BY cnt DESC")

# Completeness Register stats
stats['completeness_status'] = q("SELECT corporate_profile_status, official_url_status, careers_source_status, ats_discovery_status, COUNT(*) as cnt FROM company_completeness_register GROUP BY corporate_profile_status, official_url_status, careers_source_status, ats_discovery_status")

# AI Provider Config stats
stats['ai_providers'] = q("SELECT provider, display_name, is_enabled, selected_model, allow_paid_calls FROM ai_provider_config")

# Subscriptions
stats['subscription_plans'] = q("SELECT code, name, monthly_price_paise, yearly_price_paise FROM subscription_plans")

# 5 Sample rows for important tables (masking personal email / phone / password)
def get_samples(table, limit=5, cols='*'):
    cursor.execute(f"SELECT {cols} FROM `{table}` LIMIT {limit}")
    desc = [d[0] for d in cursor.description]
    rows = []
    for r in cursor.fetchall():
        row_dict = dict(zip(desc, r))
        # Mask secrets
        for k in list(row_dict.keys()):
            if 'password' in k or 'secret' in k or 'key' in k or 'token' in k:
                row_dict[k] = '***MASKED***'
            if k in ('email', 'phone') and row_dict[k]:
                row_dict[k] = row_dict[k][:3] + '***@***' if '@' in str(row_dict[k]) else '***'
        rows.append(row_dict)
    return rows

stats['samples_company'] = get_samples('admin_panel_company', 5, 'company_id, company_name, sector, listing_status, website_url, careers_url, ats_platform, careers_url_confidence, jobs_access, csr_access')
stats['samples_job'] = get_samples('admin_panel_job', 5, 'job_row_id, job_id, company_id, job_title, department, location, employment_type, work_mode, status, verification_status, is_defective, field_source')
stats['samples_csrproject'] = get_samples('admin_panel_csrproject', 5, 'csr_id, company_id, project_name, category, geographic_location, state, status, field_source, source_url')
stats['samples_csropportunity'] = get_samples('admin_panel_csropportunity', 5, 'opp_id, company_id, title, opportunity_type, category, status, portal_url')
stats['samples_user'] = get_samples('admin_panel_user', 5, 'id, username, email, is_staff, is_active, role')

with open('scratch/db_distributions.json', 'w') as f:
    json.dump(stats, f, indent=2, default=str)

print('Successfully written scratch/db_distributions.json')
