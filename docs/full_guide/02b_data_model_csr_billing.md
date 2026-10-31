# 02b. Data Model: CSR, Billing, AI Configuration & Drift Analysis

**Frozen Timestamp:** `2026-10-29 12:12:48 +05:30`  
**Git Commit Hash:** `0a538883c17b40774c119deb78b9aaff72220606`

---

## 1. CSR Domain Entities

### 1.1 CSRProject (`admin_panel_csrproject`)
- **PLAIN**: Under Section 135 of India's Companies Act, large companies must publish reports describing their social development programs. The CSRProject model stores these real corporate projects, such as school construction, rural water filtration, or healthcare clinics. It tracks the statutory Schedule VII thematic category, the location, the allocated budget, and the exact evidence link.
- **TECHNICAL**: Defined in `modules/admin_panel/models/opportunity.py:12` (`CSRProject`).
  - Primary Key: `csr_id` (AutoField, auto-increment integer). Total rows: **1,591**.
  - Foreign Key: `company` (`ForeignKey(Company, on_delete=models.CASCADE, related_name='csr_projects')`).
  - Fields: `project_name` (TextField), `category` (TextField), `description` (TextField), `geographic_location` (TextField), `state` (TextField), `budget` (TextField), `source_url` (TextField), `status` (CharField 30, default 'ACTIVE'), `field_source` (JSONField).
- **EVIDENCE & Distributions**:
```sql
-- All 1,591 CSR projects are ACTIVE
SELECT status, COUNT(*) FROM admin_panel_csrproject GROUP BY status;
-- ACTIVE: 1,591

-- Top 5 Thematic Categories (Schedule VII)
SELECT category, COUNT(*) FROM admin_panel_csrproject GROUP BY category ORDER BY COUNT(*) DESC LIMIT 5;
-- Education & Skill Development: 586
-- Environment & Sustainability: 487
-- Healthcare & Nutrition: 270
-- Schedule VII Statutory CSR: 169
-- Rural Development & Livelihood: 52
```

### 1.2 CSROpportunity (`admin_panel_csropportunity`)
- **PLAIN**: In theory, this table was intended to hold open invitations from companies asking NGOs to submit grant proposals or tender bids. In practice, early versions of the web crawler improperly cloned CSR projects into "opportunities" without verifying whether the company had actually issued an open call. Under Phase 1 cleanup, all 1,160 rows were permanently flagged as `INVALID_SYNTHETIC` and hidden from the public website to maintain complete data integrity.
- **TECHNICAL**: Defined in `modules/admin_panel/models/opportunity.py:85` (`CSROpportunity`).
  - Primary Key: `opp_id` (AutoField, auto-increment integer). Total rows: **1,160**.
  - Foreign Key: `company` (`ForeignKey(Company, on_delete=models.CASCADE, related_name='opportunities')`).
  - Fields: `title` (TextField), `opportunity_type` (TextField), `category` (TextField), `submission_deadline` (TextField), `portal_url` (TextField), `requirements` (TextField), `status` (CharField 50).
- **EVIDENCE & Distributions**:
```sql
SELECT status, COUNT(*) FROM admin_panel_csropportunity GROUP BY status;
-- INVALID_SYNTHETIC: 1,160 (100% quarantined)

SELECT COUNT(*) FROM admin_panel_csropportunity WHERE status = 'OPEN';
-- 0
```

### 1.3 Contact (`admin_panel_contact`)
- **PLAIN**: Stores verified names, titles, and departments of corporate CSR committee chairs, ESG heads, and human resource directors across corporate entities.
- **TECHNICAL**: Defined in `modules/admin_panel/models/contact.py:10` (`Contact`).
  - Primary Key: `contact_id` (AutoField). Total rows: **41**.
  - Foreign Key: `company` (`ForeignKey(Company, on_delete=models.CASCADE, related_name='contacts')`).
  - Fields: `name` (CharField 255), `designation` (CharField 255), `department` (CharField 100), `email` (EmailField), `phone` (CharField 50), `confidence` (FloatField), `link_status` (CharField 50). All 41 records have `link_status = 'LINK_OK'`.
- **EVIDENCE**:
```sql
SELECT COUNT(*) FROM admin_panel_contact; -- 41
SELECT department, COUNT(*) FROM admin_panel_contact GROUP BY department;
-- CSR / ESG: 28, Human Resources: 13
```

---

## 2. Subscription, Billing & Monetization Models

### PLAIN
The platform provides a commercial multi-tier SaaS model. Public users access basic directories, while verified NGOs, researchers, and enterprises subscribe to premium plans that unlock contact details, bulk data downloads, custom matching algorithms, and automated email alerts.

### TECHNICAL
The monetization system spans **11 relational tables** in `modules/admin_panel/models/subscription.py`:
- `subscription_plans`: 4 active tiers seeded via `seed_subscription_plans.py:35`.
  1. `starter` (Community Starter): ₹0 / month. 50 search queries, 0 CSV exports.
  2. `pro` (Impact Pro): ₹4,999 / month (499,900 paise). 2,000 queries, 50 exports.
  3. `enterprise` (Corporate Enterprise): ₹19,999 / month (1,999,900 paise). Unlimited queries, 500 exports.
  4. `foundation` (Foundation Master): ₹49,999 / month (4,999,900 paise). Full API access, unlimited exports.
- `subscriptions`: Active tenant subscriptions. 2 rows in database (`status='ACTIVE'`).
- `invoices`: 7 invoice records containing statutory GST breakdowns (`cgst_paise`, `sgst_paise`, `igst_paise`).
- `wallets`: 2 prepaid wallets for consumption-based metering.
- `wallet_transactions`: 13 ledger entries with balance tracking (`balance_before_paise`, `balance_after_paise`).
- `promo_codes`: 6 discount codes (e.g., `IMPACT50`, `WELCOME20`).

### EVIDENCE
```sql
SELECT code, name, monthly_price_paise / 100 as price_inr FROM subscription_plans;
-- starter:    Community Starter     | 0 INR
-- pro:        Impact Pro            | 4,999 INR
-- enterprise: Corporate Enterprise  | 19,999 INR
-- foundation: Foundation Master     | 49,999 INR

SELECT status, COUNT(*) FROM subscriptions GROUP BY status;
-- ACTIVE: 2
```

---

## 3. AI Configuration & Governance Models

### PLAIN
To discover company careers pages and classify CSR initiatives automatically, the platform can consult artificial intelligence models. To prevent unexpected cloud computing bills, the system enforces a strict zero-cost policy: it only allows free-tier API calls (such as Google Gemini's free tier) and strictly blocks billable models unless an administrator provides verified pre-existing promotional credits.

### TECHNICAL
Defined in `modules/admin_panel/models/ai_config.py`:
- `AIProviderConfig` (`ai_provider_config`): 10 configured provider profiles.
  - Active: `gemini` (`is_enabled=1`, `selected_model='gemini-3.1-flash-lite'`, `allow_paid_calls=0`).
  - Inactive / Guarded: `openrouter`, `grok`, `groq`, `ollama`, `openai`, `anthropic`, `mistral`, `deepseek`, `custom`.
- `AISystemSettings` (`ai_system_settings`): 1 singleton row.
  - `primary_provider='gemini'`, `primary_model='gemini-3.1-flash-lite'`.
  - `fallback_enabled=1`, `fallback_provider='grok'`.
  - `free_tier_only=1` (Strict Boolean flag preventing billable inference calls).
- `AIConfigurationAuditLog` (`ai_configuration_audit_log`): 19 immutable audit entries tracking model switches and API key configurations.

### EVIDENCE
```sql
SELECT provider, is_enabled, selected_model, allow_paid_calls FROM ai_provider_config;
-- gemini:     enabled=1, model=gemini-3.1-flash-lite, allow_paid_calls=0
-- grok:       enabled=0, model=grok-2-latest,         allow_paid_calls=0
-- openai:     enabled=0, model=gpt-4o-mini,           allow_paid_calls=1
-- openrouter: enabled=0, model=openrouter/free,       allow_paid_calls=0
-- anthropic:  enabled=0, model=claude-3-5-haiku-latest, allow_paid_calls=0

SELECT primary_provider, primary_model, free_tier_only FROM ai_system_settings;
-- gemini | gemini-3.1-flash-lite | 1
```

---

## 4. Model-vs-Database Drift Analysis

### PLAIN
Over time, developers modify Python model definitions and create database migrations. If a column exists in Python but not in MySQL, or if a column in MySQL is missing from the Python code, the system experiences "schema drift," which can cause crashes during crawling or queries.

### TECHNICAL
A full audit comparing Django ORM models (`modules/admin_panel/models/*.py`) against the actual MySQL database schema (`SHOW COLUMNS FROM <table>`) reveals:
1. **Zero Unapplied Migrations**: `python manage.py showmigrations` confirms all 25 migrations in `admin_panel` and all website migrations are marked `[X]`.
2. **Intentional Structural Denormalizations**:
   - `admin_panel_job.is_defective` and `admin_panel_job.canonical_url_hash` were added in migration `0021` and `0022` to accelerate Step 2 & Step 3 query performance. Both the Python model and MySQL table have matching columns.
   - `admin_panel_company.careers_url_confidence` was added in migration `0025` and is present in both code and MySQL.
3. **Legacy Inactive Fields**:
   - `admin_panel_company.cin` is defined on the model and exists in MySQL, but is 100% NULL across all 201 rows (Corporate Identification Numbers were deferred to a future ROC integration phase).
   - `admin_panel_job.salary`: Present in model and DB, but 100% NULL/empty because Indian corporate job postings omit salary figures.

### EVIDENCE
- `python manage.py showmigrations` output:
```
admin_panel
 [X] 0001_initial
 [X] 0002_plan_invoice_billing_cycle_invoice_period_end_and_more
 [X] 0003_plan_additional_info_plan_button_order_and_more
 [X] 0004_company_canonical_url_company_content_hash_and_more
 [X] 0005_company_annual_report_url_company_ats_platform_and_more
 [X] 0006_companycompletenessregister
 [X] 0007_job_behavioural_skills_job_day_in_the_life_and_more
 [X] 0008_ownership_link_verification_and_login_access
 [X] 0009_company_last_live_synced_at_company_last_sync_error_and_more
 [X] 0010_company_ats_token_company_ats_type_and_more
 [X] 0011_job_removed_at
 [X] 0012_companycrawlsummary_direct_percentage_and_more
 [X] 0013_mark_synthetic_csr_opportunities
 [X] 0014_mark_all_synthetic_csr_opportunities
 [X] 0015_csrproject_status_and_removed_at
 [X] 0016_csrproject_field_source_and_more
 [X] 0017_companysource
 [X] 0018_ai_models_and_api_configuration
 [X] 0019_company_website_url_history_and_more
 [X] 0020_aiproviderconfig_allow_paid_calls_and_more
 [X] 0021_job_detail_fields
 [X] 0022_job_unique_canonical_hash
 [X] 0023_snapshot_system
 [X] 0024_companymetrics_ats_companymetrics_crawl_status_and_more
 [X] 0025_company_careers_url_confidence_and_more
```

---

## 5. Authentic Sample Rows (Sensitive Data Masked)

### Company (`admin_panel_company`)
```json
[
  {
    "company_id": "COMP_0",
    "company_name": "Razorpay",
    "sector": null,
    "listing_status": "ACTIVE",
    "website_url": "https://razorpay.com/",
    "careers_url": "https://razorpay.com/careers/",
    "ats_platform": "GREENHOUSE",
    "careers_url_confidence": 0.0,
    "jobs_access": "PUBLIC",
    "csr_access": "PUBLIC"
  },
  {
    "company_id": "COMP_TOP200_001",
    "company_name": "Reliance Industries Limited",
    "sector": "Oil & Gas / Diversified",
    "listing_status": "ACTIVE",
    "website_url": "https://www.ril.com/",
    "careers_url": "https://www.ril.com/",
    "ats_platform": null,
    "careers_url_confidence": 0.0,
    "jobs_access": "NOT_PUBLISHED",
    "csr_access": "PUBLIC"
  }
]
```

### Job (`admin_panel_job`)
```json
[
  {
    "job_row_id": 6524,
    "job_id": "JOB_TATA_001",
    "company_id": "COMP_TOP200_105",
    "job_title": "Lead Engineer - Power Systems",
    "department": "Engineering & Manufacturing",
    "location": "Mumbai, Maharashtra, India",
    "employment_type": "Full-time",
    "work_mode": "On-site",
    "status": "ACTIVE",
    "verification_status": "PUBLISHED",
    "is_defective": 0,
    "field_source": "{\"raw_title\": \"raw_metadata.title\", \"raw_location\": \"location\", \"raw_department\": \"department\"}"
  }
]
```

### CSR Project (`admin_panel_csrproject`)
```json
[
  {
    "csr_id": 1266,
    "company_id": "COMP_TOP200_156",
    "project_name": "List of CSR projects approved by 360 ONE WAM Ltd",
    "category": "Schedule VII Statutory CSR",
    "geographic_location": "Pan-India",
    "state": "Pan-India",
    "status": "ACTIVE",
    "field_source": "{\"raw_category\": \"category\", \"raw_budget_text\": \"budget\", \"raw_project_name\": \"project_name\"}",
    "source_url": "https://www.360.one/compliance/corporate-social-responsibility#:~:text=List%20of%20CSR%20projects"
  }
]
```

---

## 6. SHOW CREATE TABLE DDL (Core Models)

```sql
-- DDL for admin_panel_job
CREATE TABLE `admin_panel_job` (
  `job_row_id` bigint NOT NULL AUTO_INCREMENT,
  `job_id` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `job_title` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `department` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `function` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `location` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `country` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_mode` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `employment_type` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `experience` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `education` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `skills` longtext COLLATE utf8mb4_unicode_ci,
  `salary` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `job_description` longtext COLLATE utf8mb4_unicode_ci,
  `posted_date` datetime(6) DEFAULT NULL,
  `closing_date` datetime(6) DEFAULT NULL,
  `application_url` varchar(1000) COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_url` varchar(1000) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_checked_date` datetime(6) DEFAULT NULL,
  `status` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `confidence` double NOT NULL,
  `link_status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `company_id` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `canonical_url_hash` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_defective` tinyint(1) NOT NULL DEFAULT '0',
  `defect_rules_version` varchar(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `field_source` json DEFAULT NULL,
  `raw_title` longtext COLLATE utf8mb4_unicode_ci,
  `raw_location` longtext COLLATE utf8mb4_unicode_ci,
  `raw_department` longtext COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`job_row_id`),
  KEY `admin_panel_job_company_id_idx` (`company_id`),
  KEY `admin_panel_job_status_idx` (`status`),
  KEY `admin_panel_job_canonical_hash_idx` (`canonical_url_hash`),
  KEY `admin_panel_job_defect_status_idx` (`is_defective`,`status`),
  CONSTRAINT `admin_panel_job_company_id_fk` FOREIGN KEY (`company_id`) REFERENCES `admin_panel_company` (`company_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

