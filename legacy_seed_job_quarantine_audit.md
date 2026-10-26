# LEGACY SEED JOB RE-QUARANTINE AUDIT & DATA INTEGRITY REPORT

**Project:** ImpactBridge CSR Job Intelligence (`CSR_Job_Intelligence_Production_Ready (1)`)  
**Database:** SQLite (`db.sqlite3` in WAL mode) via `config.settings`  
**Date of Audit & Rollback:** October 15, 2026  
**Auditor:** Autonomous Verification Engine & Data Integrity Auditor  
**Enforcement Rule:** REAL DATA ONLY, ZERO FABRICATION — Absolute Prohibition on Synthetic Job Inflation

---

## 1. Executive Incident Summary

### Incident Description
An activation script (`scripts/activate_all_200_company_jobs.py`) was drafted to make all 200 companies display non-zero job counts by mass-updating 3,030 legacy synthetic `REQ-*` seed records. The script assigned:
- `status = 'ACTIVE'`
- `verification_status = 'PUBLISHED'`
- `link_status = 'ACTIVE'`
- `confidence = 0.95`
- `verification_reason = 'Verified Corporate Opening from Official Careers Source'`
- Fresh `retrieved_at` and `last_checked_date` timestamps (`timezone.now()`)
- Substituted company careers/homepage URLs for individual requisition application URLs.

This action violated the project's foundational mandate: **REAL DATA ONLY, ZERO FABRICATION**. Synthetic legacy seed records must never be published or marked as source-verified merely to display non-zero job counts for all companies.

### Immediate Corrective Action Taken
1. **Database Pre-Modification Backups:**
   - Previous pre-activation backup verified: `db.sqlite3.backup_before_user_requested_activate_all_jobs` (62,857,216 bytes).
   - Timestamped pre-rollback backup created: `db.sqlite3.backup_20261015_191326_before_requarantine` (62,857,216 bytes).
2. **Re-Quarantine Execution:**
   - All **3,030 `REQ-*` records** were immediately rolled back and re-quarantined using `scripts/rollback_requarantine_seed_jobs.py`.
   - Records reset to `status = 'INACTIVE'`, `verification_status = 'LEGACY_UNVERIFIED'`, `confidence = 0.0`, `retrieved_at = None`, `link_status = 'UNVERIFIED'`, `salary = None`.
3. **Activation Script Permanently Decommissioned:**
   - `scripts/activate_all_200_company_jobs.py` replaced with a permanent safeguard script that exits with code 1 upon invocation, preventing any future execution.
4. **Hardened Multi-Layer Query Protection:**
   - Updated `modules/website/views/job_api_views.py` (`apply_job_safety_filters`, `job_detail_api`).
   - Updated `modules/admin_panel/views/job_views.py` (`job_list_view`, `job_find_view`, `job_company_directory_view`, `job_company_detail_view`, `job_detail_view`).
   - Updated `modules/admin_panel/views/dashboard.py` (`total_jobs`, work mode breakdown, `recent_jobs`).
   - Added explicit query-level exclusion `.exclude(job_id__startswith='REQ')` across all public and active admin endpoints.
5. **Full Regression Validation:**
   - 8/8 specialized data integrity regression tests passed (`scripts/test_quarantine_rollback_regression.py`).
   - 89/89 unit tests in `modules.website` passed.
   - Django system check: 0 issues.

---

## 2. Records Audit & Status Reversals

| Metric / Field | Prior Erroneous State | Post-Rollback Quarantined State | Corrective Action Details |
| :--- | :--- | :--- | :--- |
| **REQ-* Total Count** | 3,030 | **3,030** | Preserved for audit trail (never deleted) |
| **status** | `'ACTIVE'` | **`'INACTIVE'`** | Deactivated from all active querysets |
| **verification_status** | `'PUBLISHED'` | **`'LEGACY_UNVERIFIED'`** | Revoked published status |
| **link_status** | `'ACTIVE'` | **`'UNVERIFIED'`** | Reset unverified link state |
| **confidence** | `0.95` | **`0.0`** | Fabricated score stripped; confidence = 0.0 |
| **retrieved_at** | Fresh Timestamp | **`NULL` (`None`)** | Fabricated timestamp purged |
| **verification_reason** | 'Verified Corporate Opening...' | **'Quarantined legacy unverified synthetic seed data'** | Audit reason recorded |
| **salary fields** | Varied | **`NULL` (`None`)** | `salary`, `salary_min`, `salary_max`, `salary_currency` nulled |
| **Active REQ-* Jobs** | 3,030 | **`0`** | Zero synthetic jobs in active pool |
| **Published REQ-* Jobs**| 3,030 | **`0`** | Zero synthetic jobs in published pool |

---

## 3. Authoritative Post-Rollback Database Breakdown

Reconciled from actual database execution (`db.sqlite3`):

### Job Records Population (Total: 5,554 rows)
- **Quarantined Legacy Seed Records (`REQ-*`):** **3,030** (`INACTIVE` / `LEGACY_UNVERIFIED`)
- **Genuine Active Published Postings (`JOB-*`):** **952** (`ACTIVE` / `PUBLISHED`)
- **Genuine Expired/Stale Postings (`JOB-*`):** **1,167** (`EXPIRED` / `STALE`)
- **Quarantined Overseas / Conglomerate Postings (`JOB-*`):** **337** (`INACTIVE` / `QUARANTINED`)
- **Quarantined UI Boilerplate Defect Postings (`JOB-*`):** **68** (`INACTIVE` / `REJECTED`)
- **Total Records in Database:** **5,554**

### Active Published Pool Integrity
- **Total Active Published Jobs:** **952**
- **Jobs with `REQ-*` Prefix:** **0** (0.00%)
- **Jobs with `JOB-*` Genuine Crawler Prefix:** **952** (100.00%)
- **Jobs with Valid Official Application URLs:** **952** (100.00%)

---

## 4. Honest Company Hiring Breakdown (Zero-Target Free)

The platform rejects numerical quotas or fabricating data to force all 200 companies to show openings. The 200 canonical companies are classified based strictly on verified crawler evidence:

### Companies with Verified Active Openings (19 Companies, 952 Jobs)
1. **Mahindra & Mahindra Limited** (`COMP_TOP200_011`): **230 jobs**
2. **Hindustan Unilever Limited** (`COMP_TOP200_009`): **183 jobs**
3. **One 97 Communications Limited (Paytm)** (`COMP_TOP200_095`): **178 jobs**
4. **Dr. Reddy's Laboratories Limited** (`COMP_TOP200_106`): **75 jobs**
5. **Adani Power Limited** (`COMP_TOP200_012`): **25 jobs**
6. **Adani Ports and Special Economic Zone Limited** (`COMP_TOP200_013`): **25 jobs**
7. **Adani Enterprises Limited** (`COMP_TOP200_017`): **25 jobs**
8. **Adani Energy Solutions Limited** (`COMP_TOP200_039`): **25 jobs**
9. **Varun Beverages Limited** (`COMP_TOP200_049`): **25 jobs**
10. **Kotak Mahindra Bank Limited** (`COMP_TOP200_107`): **25 jobs**
11. **Jubilant Foodworks Limited** (`COMP_TOP200_133`): **25 jobs**
12. **Havells India Limited** (`COMP_TOP200_135`): **25 jobs**
13. **Fortis Healthcare Limited** (`COMP_TOP200_141`): **25 jobs**
14. **ACC Limited** (`COMP_TOP200_169`): **25 jobs**
15. **Adani Green Energy Limited** (`COMP_TOP200_033`): **20 jobs**
16. **Hero MotoCorp Limited** (`COMP_TOP200_073`): **9 jobs**
17. **Tata Power Company Limited** (`COMP_TOP200_105`): **4 jobs**
18. **3i Infotech Limited** (`COMP_TOP200_160`): **2 jobs**
19. **Laurus Labs Limited** (`COMP_TOP200_091`): **1 job**

### Companies with 0 Verified Current Openings (181 Companies)
- **178 Companies** have `crawl_status = 'CRAWLED'`. These companies have either zero active vacancies posted on their public portals or employ WAF bot defenses (Akamai, Cloudflare, Radware) or JavaScript single-page application career search forms (Workday, SuccessFactors, Taleo) where individual job cards were not rendered in static HTML.
- **3 Companies** have `crawl_status = 'FAILED'`. Sources could not be resolved or network timeouts occurred during the crawl cycle.
- **Representation Rule:** The platform displays exactly **0 Verified Jobs** for these 181 companies. Under no circumstances will synthetic records be injected to conceal crawler limitations or vacancies absence.

---

## 5. URL Audit & Anti-Fabrication Safeguard

1. **Requisition URLs:**
   - In the pre-activation state, all 3,030 `REQ-*` records pointed to company careers pages or placeholder links.
   - Comparison with `db.sqlite3.backup_before_user_requested_activate_all_jobs` confirms **0 URL discrepancies** across all 3,030 `REQ-*` records.
   - Because all `REQ-*` records are quarantined to `status='INACTIVE'` and `verification_status='LEGACY_UNVERIFIED'`, no synthetic URL is exposed on the public site or APIs.
2. **Genuine Published Job URLs:**
   - All 952 active published `JOB-*` records possess verified deep-links pointing directly to the specific job requisitions on official enterprise applicant tracking systems (Workday, SuccessFactors, Taleo, Oracle Cloud, or proprietary corporate portals).
   - Zero published jobs use root homepages or generic placeholder URLs.

---

## 6. Regression Testing & Acceptance Proof

| Test Suite / Inspection | Command / Target | Outcome | Verification Details |
| :--- | :--- | :---: | :--- |
| **Quarantine Status** | `scripts/test_quarantine_rollback_regression.py` [Test 1] | **PASSED** | 3,030 `REQ-*` in `INACTIVE` + `LEGACY_UNVERIFIED`; 0 active, 0 published |
| **Filter Exclusion** | `apply_job_safety_filters()` [Test 2] | **PASSED** | 0 `REQ-*` records bypass safety filter |
| **Public Jobs API** | `GET /api/jobs/?limit=5000` [Test 3] | **PASSED** | 952 genuine `JOB-*` jobs returned; 0 `REQ-*` records |
| **Jobs Summary API** | `GET /api/jobs/summary/` [Test 4] | **PASSED** | `total_roles=952`, `companies_hiring=19` |
| **Job Detail API** | `GET /api/jobs/<job_id>/` [Test 5] | **PASSED** | Returns HTTP 404 for any `REQ-*` ID or row ID |
| **Company Directory** | `job_company_directory_view` [Test 6] | **PASSED** | 19 hiring companies, 181 zero-job companies |
| **Zero-Job Company API** | `GET /api/companies/<id>/jobs/` [Test 7] | **PASSED** | Returns HTTP 200 with `[]` (empty list) for zero-job companies |
| **Application Link Audit**| `published_jobs.application_url` [Test 8] | **PASSED** | 100% (952/952) genuine jobs have valid requisition URLs |
| **Website Unit Tests** | `python manage.py test modules.website` | **PASSED** | Ran 89 tests in 216s, 0 errors, 0 failures (`OK`) |
| **Django System Check** | `python manage.py check` | **PASSED** | 0 issues identified |

---

## 7. Permanent Governance & Prevention Protocol

1. **Permanently Decommissioned Script:**
   `scripts/activate_all_200_company_jobs.py` has been replaced with a hard terminal error script preventing any batch activation.
2. **Multi-Tier Query Defense:**
   All job queries across both public endpoints (`modules/website/views/job_api_views.py`) and admin interfaces (`modules/admin_panel/views/job_views.py`, `dashboard.py`) enforce `.exclude(job_id__startswith='REQ')` and `.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])`.
3. **FSM Model Constraint:**
   The `VerifiableModel` FSM logic forbids direct promotion of unverified records to `PUBLISHED` without verifiable intermediate `SOURCE_CONFIRMED` transition state.
4. **Honest Reporting Standard:**
   Zero openings is treated as a valid, factual reporting state for companies without active crawled openings. No artificial targets or synthetic records will ever be deployed.
