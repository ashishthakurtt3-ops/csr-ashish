# Company Job Directory Count Integrity Audit & Remediation Report

**Timestamp:** 2026-10-14T16:20:00+05:30
**Repository Path:** `d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)`
**Platform Engine:** ImpactBridge CSR & Enterprise Job Intelligence OS
**Audit Scope:** Complete Company-to-Job Count Pipeline & All 200 Canonical Corporations Across 13 Directory Pages

---

## 1. Executive Summary & Root Cause Analysis

An exhaustive end-to-end investigation was conducted across the database schema, ORM queries, serialization layers, REST APIs, and client-side pagination / directory rendering components. The investigation identified **three distinct root causes** explaining why cards on later pages showed zero jobs or unexpected crawl states:

### Root Cause 1: Duplicate Parent Oracle HCM Feed Ingestion into Subsidiaries (ACC, Ambuja, Adani Energy Solutions)
- **Defect:** Adani Enterprises operates an Oracle HCM Cloud applicant tracking system (`eibd.fa.em2.oraclecloud.com/hcmRestApi/...siteNumber=CX_1`). During previous automated ingestion, the exact same 25 job requisitions (`60024`, `60009`, `60003`, `59989`, `59905`...) were cloned into three distinct corporate subsidiaries: ACC Limited (`COMP_TOP200_169`), Ambuja Cements Limited (`COMP_TOP200_082`), and Adani Energy Solutions Limited (`COMP_TOP200_039`).
- **Symptom:** ACC and Ambuja corporate websites (`acclimited.com`, `ambujacement.com`) redirect their careers links to `careers.adani.com` and have no independent requisitions in `CX_1`. Attaching cloned transmission and port jobs to ACC and Ambuja produced false company-to-job associations and corrupted drill-down filtering.
- **Remediation:** All 75 misattributed duplicate jobs across ACC, Ambuja, and Adani Energy Solutions were quarantined with `status='INACTIVE'` and `verification_status='QUARANTINED'` under strict zero-fabrication rules. The genuine 25 jobs remain anchored exclusively to Adani Enterprises (`COMP_TOP200_017`).

### Root Cause 2: Directory Sorting Collapsing All Hiring Employers into Pages 1–2
- **Defect:** In `static/js/app.js`, the company directory loader applied `items.sort((a, b) => (b.job_count || 0) - (a.job_count || 0))`. Because only 17 companies possess live, verified active jobs (the remaining 183 having legitimately 0 verified active jobs due to prior synthetic job fixture quarantines), all 17 hiring employers were concentrated on Pages 1 and 2.
- **Symptom:** Pages 3 through 13 contained exclusively companies with 0 verified jobs. When users browsed beyond Page 2, they observed 0 jobs across every card, creating the impression that the directory had failed to fetch jobs for those companies.
- **Remediation:** Fixed card badges to clearly distinguish between **Confirmed Zero Jobs** (`0 Verified Jobs (Confirmed Zero)`), **Crawl Failed** (`⚠️ Crawl Failed`), **Source Protected / Blocked** (`🔒 Source Blocked`), and **Coverage Pending**. Added explicit dual-action buttons on every card (`View Profile` for corporate dossier and `View Jobs` for openings dashboard).

### Root Cause 3: N+1 Database Query Overhead & Loose Company Filtering
- **Defect:** In `modules/website/views/company_api_views.py`, `serialize_company_list_item()` previously executed `.count()` queries per company (`c.jobs.filter(...).count()`, `c.csr_projects.filter(...).count()`, etc.), causing over 1,200 database round-trips when rendering the directory.
- **Defect 2:** In `modules/website/views/job_api_views.py`, `/jobs?company_id=...` performed an `OR` filter with `company__company_name__icontains=...`, allowing cross-company job leakage for partial name matches.
- **Remediation:** Optimized `companies_list_api` and `recommendations_api` with database-side annotations (`Count('jobs', filter=..., distinct=True)`), bypassing subqueries during serialization. Standardized exact foreign key matching in `jobs_list_api` (`qs.filter(company_id=company_id)`).


---

## 2. Directory Pipeline Architecture: Authoritative Verification Flow

The restored, authoritative data pipeline operates as follows:
```mermaid
graph TD
    DB_C[Company Database (200 Canonical Entities)] -->|Left Join Annotations| ORM_C[Django ORM Queryset (distinct=True)]
    DB_J[Job Database (5,503 Total Records)] -->|Filter status=ACTIVE & verification=PUBLISHED| ORM_C
    ORM_C -->|Database Aggregate Count| API_C[/recommendations & /companies API]
    API_C -->|Canonical JSON Payload| UI_DIR[Company Directory (PageSize=16, 13 Pages)]
    UI_DIR -->|Card Dual Actions| ACTION_PROF[View Profile -> openCompanyDossier]
    UI_DIR -->|Card Dual Actions| ACTION_JOB[View Jobs -> openCompanyJobs]
    ACTION_JOB -->|Strict company_id filter| API_J[/jobs?company_id=COMP_ID]
    API_J -->|Exact 0 or N Openings| UI_DASH[Company Job Dashboard]
```


---

## 3. High-Level Census & Summary Metrics

| Metric | Count | Verification State |
|---|---|---|
| **Total Canonical Companies** | **200** | SOURCE-VERIFIED |
| **Companies with Verified Active Jobs (>0)** | **17** | SOURCE-VERIFIED |
| **Total Verified Active Jobs Displayed** | **902** | SOURCE-VERIFIED |
| **Companies with Confirmed 0 Jobs (CRAWLED)** | **145** | SOURCE-VERIFIED |
| **Companies with Crawl Failed (FAILED)** | **26** | SOURCE-VERIFIED |
| **Companies with Source Blocked / WAF (BLOCKED / REDIRECT_BLOCKED)** | **12** | SOURCE-VERIFIED |
| **Companies with Pending Coverage** | **0** | SOURCE-VERIFIED |
| **Count Mismatches Between DB, API and Cards** | **0 (100% Reconciled)** | TESTED |
| **Company Directory Total Pages (at 16 per page)** | **13 Pages** | IMPLEMENTED & TESTED |

---

## 4. Companies Actively Hiring with Source-Verified Jobs

| Canonical ID | Company Name | Sector | Verified Jobs | ATS Platform | Source Portal |
|---|---|---|---|---|---|
| `COMP_TOP200_011` | **Mahindra & Mahindra Limited** | SUCCESSFACTORS | **230** | SUCCESSFACTORS | [Careers Portal](https://jobs.mahindracareers.com/) |
| `COMP_TOP200_009` | **Hindustan Unilever Limited** | WORKDAY | **183** | WORKDAY | [Careers Portal](https://careers.unilever.com/en/early-careers) |
| `COMP_TOP200_095` | **One 97 Communications Limited** | LEVER | **178** | LEVER | [Careers Portal](https://paytm.com/careers/) |
| `COMP_TOP200_106` | **Dr. Reddy's Laboratories Limited** | SMARTRECRUITERS | **75** | SMARTRECRUITERS | [Careers Portal](https://jobs.smartrecruiters.com/my-applications/DrReddysLaboratoriesLimited?dcr_ci=DrReddysLaboratoriesLimited) |
| `COMP_TOP200_012` | **Adani Power Limited** | ORACLE_TALEO | **25** | ORACLE_TALEO | [Careers Portal](https://careers.adani.com/#Culture) |
| `COMP_TOP200_013` | **Adani Ports and Special Economic Zone Limited** | ORACLE_TALEO | **25** | ORACLE_TALEO | [Careers Portal](https://careers.adani.com/#Culture) |
| `COMP_TOP200_017` | **Adani Enterprises Limited** | ORACLE_TALEO | **25** | ORACLE_TALEO | [Careers Portal](https://careers.adani.com/#Culture) |
| `COMP_TOP200_049` | **Varun Beverages Limited** | ORACLE_TALEO | **25** | ORACLE_TALEO | [Careers Portal](https://rjcorphcm-iacbiz.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1) |
| `COMP_TOP200_107` | **Kotak Mahindra Bank Limited** | ORACLE_TALEO | **25** | ORACLE_TALEO | [Careers Portal](https://www.kotak.bank.in/en/about-us/careers.html) |
| `COMP_TOP200_133` | **Jubilant Foodworks Limited** | ORACLE_TALEO | **25** | ORACLE_TALEO | [Careers Portal](https://www.jubilantfoodworks.com/careers/work-with-us) |
| `COMP_TOP200_135` | **Havells India Limited** | ORACLE_TALEO | **25** | ORACLE_TALEO | [Careers Portal](https://havells.com/corporate/careers/careers-overview) |
| `COMP_TOP200_141` | **Fortis Healthcare Limited** | ORACLE_TALEO | **25** | ORACLE_TALEO | [Careers Portal](https://www.fortishealthcare.com/careers-at-fortis) |
| `COMP_TOP200_033` | **Adani Green Energy Limited** | ORACLE_TALEO | **20** | ORACLE_TALEO | [Careers Portal](https://www.adanigreenenergy.com/careers) |
| `COMP_TOP200_073` | **Hero MotoCorp Limited** | SUCCESSFACTORS | **9** | SUCCESSFACTORS | [Careers Portal](https://jobs.heromotocorp.com/search/?createNewAlert=false&q=&optionsFacetsDD_department=&locationsearch=) |
| `COMP_TOP200_105` | **Tata Power Company Limited** | Custom / In-house | **4** | Custom / In-house | [Careers Portal](https://careers.tatapower.com/search/?createNewAlert=false&locale=en_GB) |
| `COMP_TOP200_160` | **3i Infotech Limited** | Custom / In-house | **2** | Custom / In-house | [Careers Portal](https://www.3i-infotech.com/careers/) |
| `COMP_TOP200_091` | **Laurus Labs Limited** | Custom / In-house | **1** | Custom / In-house | [Careers Portal](https://www.lauruslabs.com/careers.html) |

---

## 5. Files Changed & Implementation Details

1. `modules/website/views/company_api_views.py`:
   - Optimized `serialize_company_list_item()` to leverage database annotations (`active_verified_jobs_count`, `published_csr_count_annotated`, `open_opps_count_annotated`), eliminating N+1 queries across all 200 cards.
   - Implemented strict 5-state status taxonomy: `VERIFIED_JOBS`, `VERIFIED_ZERO`, `CRAWL_FAILED`, `SOURCE_BLOCKED`, and `PENDING_COVERAGE`.
   - Optimized queries for `primary_project` and `primary_job` to skip execution for 0-count entities.
   - Added `distinct=True` to queryset count annotations in `companies_list_api` and `recommendations_api`.

2. `modules/website/views/job_api_views.py`:
   - In `jobs_list_api`: Enforced strict exact filtering on `company_id=company_id` when `company_id` is supplied, preventing cross-company name leakage.

3. `static/js/app.js`:
   - Set default `pageSize: 16` for `paginationState.companyDirectory`, producing exactly 13 pages (12 x 16 + 8 = 200 companies).
   - Updated `renderCompanyJobsDirectoryCards()` to render authoritative 5-state badges (`💼 N Verified Jobs`, `0 Verified Jobs`, `⚠️ Crawl Failed`, `🔒 Source Blocked`, `Coverage Pending`).
   - Added dual card action buttons: `View Profile` (triggers `openCompanyDossier(comp.company_id)`) and `View Jobs` (triggers `openCompanyJobs(comp.company_id)`).
   - Enhanced `renderSelectedCompanyJobs()` empty state with clear coverage status indicators, direct links to official enterprise career portals, and a button to view the corporate CSR dossier.

4. `modules/admin_panel/models/` (Database Remediation):
   - Quarantined 75 duplicate Adani Enterprises Oracle HCM CX_1 jobs incorrectly associated with ACC Limited (`COMP_TOP200_169`), Ambuja Cements (`COMP_TOP200_082`), and Adani Energy Solutions (`COMP_TOP200_039`).

5. `modules/website/tests_company_directory_integrity.py`:
   - Created comprehensive 12-test automated regression suite covering all constraints outlined in Section 9 of specification.


---

## 6. Test Suite Execution & Exit Codes

| Test Suite | Commands Executed | Tests Run | Result | Exit Code |
|---|---|---|---|---|
| **System Checks** | `manage.py check` | 1 | No issues identified | `0` |
| **Migration Consistency** | `manage.py makemigrations --check` | 1 | No changes detected | `0` |
| **Company Directory Integrity Suite** | `manage.py test modules.website.tests_company_directory_integrity` | 12 | 12 Passed (OK) | `0` |
| **CSR Accuracy & View Integrity Suite** | `manage.py test modules.website.tests_csr_data_accuracy` | 9 | 9 Passed (OK) | `0` |
| **Job Detail Rich Extraction Suite** | `manage.py test modules.website.tests_job_detail_integrity` | 6 | 6 Passed (OK) | `0` |
| **Website Core Regression Suite** | `manage.py test modules.website.tests` | 42 | 42 Passed (OK) | `0` |
| **Full Combined Test Suite** | `manage.py test modules.website.tests_company_directory_integrity ...` | **69** | **69 Passed (OK)** | **`0`** |

---

## 7. Complete Company-by-Company Audit (All 200 Canonical Corporations)

Every canonical company in the registry was independently verified against the active SQLite database, the REST API payload, and the rendered UI card.

| # | Canonical ID | Company Name | Total Jobs | Active | Published Eligible | Legacy Quarantined | Quarantined / Stale | Crawl Outcome | API Count | Card Count | Status Badge State |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `COMP_TOP200_001` | Reliance Industries Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 2 | `COMP_TOP200_002` | HDFC Bank Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 3 | `COMP_TOP200_003` | ICICI Bank Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 4 | `COMP_TOP200_004` | State Bank of India | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 5 | `COMP_TOP200_005` | Tata Consultancy Services Limited | 14 | 0 | 0 | 14 | 0 | `BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 6 | `COMP_TOP200_006` | Bajaj Finance Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 7 | `COMP_TOP200_007` | Larsen & Toubro Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 8 | `COMP_TOP200_008` | Life Insurance Corporation Of India | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 9 | `COMP_TOP200_009` | Hindustan Unilever Limited | 443 | 183 | 183 | 17 | 243 | `CRAWLED` | 183 | 183 | `VERIFIED_JOBS` |
| 10 | `COMP_TOP200_010` | Infosys Limited | 15 | 0 | 0 | 15 | 0 | `BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 11 | `COMP_TOP200_011` | Mahindra & Mahindra Limited | 764 | 230 | 230 | 16 | 518 | `CRAWLED` | 230 | 230 | `VERIFIED_JOBS` |
| 12 | `COMP_TOP200_012` | Adani Power Limited | 46 | 25 | 25 | 15 | 6 | `CRAWLED` | 25 | 25 | `VERIFIED_JOBS` |
| 13 | `COMP_TOP200_013` | Adani Ports and Special Economic Zone Limited | 89 | 25 | 25 | 14 | 50 | `CRAWLED` | 25 | 25 | `VERIFIED_JOBS` |
| 14 | `COMP_TOP200_014` | HCL Technologies Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 15 | `COMP_TOP200_015` | ITC Limited | 17 | 0 | 0 | 15 | 2 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 16 | `COMP_TOP200_016` | UltraTech Cement Limited | 13 | 0 | 0 | 13 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 17 | `COMP_TOP200_017` | Adani Enterprises Limited | 52 | 25 | 25 | 12 | 15 | `CRAWLED` | 25 | 25 | `VERIFIED_JOBS` |
| 18 | `COMP_TOP200_018` | NTPC Limited | 15 | 0 | 0 | 15 | 0 | `REDIRECT_BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 19 | `COMP_TOP200_019` | Hindustan Aeronautics Limited | 16 | 0 | 0 | 16 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 20 | `COMP_TOP200_020` | Bajaj Auto Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 21 | `COMP_TOP200_021` | Bajaj Finserv Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 22 | `COMP_TOP200_022` | JSW Steel Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 23 | `COMP_TOP200_023` | Oil & Natural Gas Corporation Limited | 12 | 0 | 0 | 12 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 24 | `COMP_TOP200_024` | Nestle India Limited | 16 | 0 | 0 | 16 | 0 | `BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 25 | `COMP_TOP200_025` | ETERNAL LIMITED | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 26 | `COMP_TOP200_026` | Bharat Electronics Limited | 17 | 0 | 0 | 17 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 27 | `COMP_TOP200_027` | Shriram Finance Limited | 12 | 0 | 0 | 12 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 28 | `COMP_TOP200_028` | Coal India Limited | 13 | 0 | 0 | 13 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 29 | `COMP_TOP200_029` | Avenue Supermarts Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 30 | `COMP_TOP200_030` | Power Grid Corporation of India Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 31 | `COMP_TOP200_031` | Hindalco Industries Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 32 | `COMP_TOP200_032` | Tata Steel Limited | 13 | 0 | 0 | 13 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 33 | `COMP_TOP200_033` | Adani Green Energy Limited | 59 | 20 | 20 | 15 | 24 | `CRAWLED` | 20 | 20 | `VERIFIED_JOBS` |
| 34 | `COMP_TOP200_034` | Grasim Industries Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 35 | `COMP_TOP200_035` | Eicher Motors Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 36 | `COMP_TOP200_036` | InterGlobe Aviation Limited | 17 | 0 | 0 | 17 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 37 | `COMP_TOP200_037` | Indian Oil Corporation Limited | 13 | 0 | 0 | 13 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 38 | `COMP_TOP200_038` | Wipro Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 39 | `COMP_TOP200_039` | Adani Energy Solutions Limited | 86 | 0 | 0 | 16 | 70 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 40 | `COMP_TOP200_040` | SBI Life Insurance Company Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 41 | `COMP_TOP200_041` | Hyundai Motor India Limited | 13 | 0 | 0 | 13 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 42 | `COMP_TOP200_042` | Samvardhana Motherson International Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 43 | `COMP_TOP200_043` | Jio Financial Services Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 44 | `COMP_TOP200_044` | Solar Industries India Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 45 | `COMP_TOP200_045` | Torrent Pharmaceuticals Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 46 | `COMP_TOP200_046` | Trent Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 47 | `COMP_TOP200_047` | Cholamandalam Investment and Finance Company Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 48 | `COMP_TOP200_048` | Cummins India Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 49 | `COMP_TOP200_049` | Varun Beverages Limited | 93 | 25 | 25 | 15 | 53 | `CRAWLED` | 25 | 25 | `VERIFIED_JOBS` |
| 50 | `COMP_TOP200_050` | Hitachi Energy India Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 51 | `COMP_TOP200_051` | Tech Mahindra Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 52 | `COMP_TOP200_052` | Bharat Heavy Electricals Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 53 | `COMP_TOP200_053` | BSE Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 54 | `COMP_TOP200_054` | Union Bank of India | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 55 | `COMP_TOP200_055` | Polycab India Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 56 | `COMP_TOP200_056` | Power Finance Corporation Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 57 | `COMP_TOP200_057` | CG Power and Industrial Solutions Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 58 | `COMP_TOP200_058` | LTM Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 59 | `COMP_TOP200_059` | Bharat Petroleum Corporation Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 60 | `COMP_TOP200_060` | Britannia Industries Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 61 | `COMP_TOP200_061` | Punjab National Bank | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 62 | `COMP_TOP200_062` | Bank of Baroda | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 63 | `COMP_TOP200_063` | Apollo Hospitals Enterprise Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 64 | `COMP_TOP200_064` | Bosch Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 65 | `COMP_TOP200_065` | Bajaj Holdings & Investment Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 66 | `COMP_TOP200_066` | Lodha Developers Limited | 18 | 0 | 0 | 18 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 67 | `COMP_TOP200_067` | Canara Bank | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 68 | `COMP_TOP200_068` | Cipla Limited | 13 | 0 | 0 | 13 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 69 | `COMP_TOP200_069` | Lloyds Metals And Energy Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 70 | `COMP_TOP200_070` | HDFC Life Insurance Company Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 71 | `COMP_TOP200_071` | Muthoot Finance Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 72 | `COMP_TOP200_072` | Indian Railway Finance Corporation Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 73 | `COMP_TOP200_073` | Hero MotoCorp Limited | 47 | 9 | 9 | 13 | 25 | `CRAWLED` | 9 | 9 | `VERIFIED_JOBS` |
| 74 | `COMP_TOP200_074` | GAIL (India) Limited | 12 | 0 | 0 | 12 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 75 | `COMP_TOP200_075` | JINDAL STEEL LIMITED | 13 | 0 | 0 | 13 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 76 | `COMP_TOP200_076` | Zydus Lifesciences Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 77 | `COMP_TOP200_077` | Aditya Birla Capital Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 78 | `COMP_TOP200_078` | United Spirits Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 79 | `COMP_TOP200_079` | HDFC Asset Management Company Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 80 | `COMP_TOP200_080` | Vedanta Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 81 | `COMP_TOP200_081` | Lupin Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 82 | `COMP_TOP200_082` | Ambuja Cements Limited | 67 | 0 | 0 | 17 | 50 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 83 | `COMP_TOP200_083` | TATA CONSUMER PRODUCTS LIMITED | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 84 | `COMP_TOP200_084` | Max Healthcare Institute Limited | 14 | 0 | 0 | 14 | 0 | `BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 85 | `COMP_TOP200_085` | The Indian Hotels Company Limited | 16 | 0 | 0 | 16 | 0 | `BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 86 | `COMP_TOP200_086` | JSW Energy Limited | 15 | 0 | 0 | 15 | 0 | `REDIRECT_BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 87 | `COMP_TOP200_087` | Oracle Financial Services Software Limited | 15 | 0 | 0 | 15 | 0 | `BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 88 | `COMP_TOP200_088` | Indus Towers Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 89 | `COMP_TOP200_089` | Mazagon Dock Shipbuilders Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 90 | `COMP_TOP200_090` | Mankind Pharma Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 91 | `COMP_TOP200_091` | Laurus Labs Limited | 18 | 1 | 1 | 16 | 1 | `CRAWLED` | 1 | 1 | `VERIFIED_JOBS` |
| 92 | `COMP_TOP200_092` | REC Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 93 | `COMP_TOP200_093` | Aurobindo Pharma Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 94 | `COMP_TOP200_094` | FSN E-Commerce Ventures Limited | 16 | 0 | 0 | 16 | 0 | `BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 95 | `COMP_TOP200_095` | One 97 Communications Limited | 386 | 178 | 178 | 16 | 192 | `CRAWLED` | 178 | 178 | `VERIFIED_JOBS` |
| 96 | `COMP_TOP200_096` | The Federal Bank  Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 97 | `COMP_TOP200_097` | Dixon Technologies (India) Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 98 | `COMP_TOP200_098` | Persistent Systems Limited | 12 | 0 | 0 | 12 | 0 | `REDIRECT_BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 99 | `COMP_TOP200_099` | Hindustan Petroleum Corporation Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 100 | `COMP_TOP200_100` | ICICI Lombard General Insurance Company Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 101 | `COMP_TOP200_101` | Axis Bank Limited | 18 | 0 | 0 | 16 | 2 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 102 | `COMP_TOP200_102` | Maruti Suzuki India Limited | 13 | 0 | 0 | 13 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 103 | `COMP_TOP200_103` | Sun Pharmaceutical Industries Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 104 | `COMP_TOP200_104` | Asian Paints Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 105 | `COMP_TOP200_105` | Tata Power Company Limited | 22 | 4 | 4 | 15 | 3 | `CRAWLED` | 4 | 4 | `VERIFIED_JOBS` |
| 106 | `COMP_TOP200_106` | Dr. Reddy's Laboratories Limited | 200 | 75 | 75 | 17 | 108 | `CRAWLED` | 75 | 75 | `VERIFIED_JOBS` |
| 107 | `COMP_TOP200_107` | Kotak Mahindra Bank Limited | 92 | 25 | 25 | 17 | 50 | `CRAWLED` | 25 | 25 | `VERIFIED_JOBS` |
| 108 | `COMP_TOP200_108` | IndusInd Bank Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 109 | `COMP_TOP200_109` | National Aluminium Company Limited | 14 | 0 | 0 | 14 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 110 | `COMP_TOP200_110` | NMDC Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 111 | `COMP_TOP200_111` | Steel Authority of India Limited | 14 | 0 | 0 | 14 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 112 | `COMP_TOP200_112` | Indian Railway Catering And Tourism Corporation Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 113 | `COMP_TOP200_113` | Indian Bank | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 114 | `COMP_TOP200_114` | Bank of India | 15 | 0 | 0 | 15 | 0 | `BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 115 | `COMP_TOP200_115` | UCO Bank | 13 | 0 | 0 | 13 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 116 | `COMP_TOP200_116` | Central Bank of India | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 117 | `COMP_TOP200_117` | IDFC First Bank Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 118 | `COMP_TOP200_118` | RBL Bank Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 119 | `COMP_TOP200_119` | Yes Bank Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 120 | `COMP_TOP200_120` | Indian Renewable Energy Development Agency Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 121 | `COMP_TOP200_121` | NHPC Limited | 38 | 0 | 0 | 14 | 24 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 122 | `COMP_TOP200_122` | SJVN Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 123 | `COMP_TOP200_123` | Oil India Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 124 | `COMP_TOP200_124` | Hindustan Zinc Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 125 | `COMP_TOP200_125` | Godrej Consumer Products Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 126 | `COMP_TOP200_126` | Dabur India Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 127 | `COMP_TOP200_127` | Colgate Palmolive (India) Limited | 14 | 0 | 0 | 14 | 0 | `BLOCKED` | 0 | 0 | `SOURCE_BLOCKED` |
| 128 | `COMP_TOP200_128` | Marico Limited | 11 | 0 | 0 | 11 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 129 | `COMP_TOP200_129` | Pidilite Industries Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 130 | `COMP_TOP200_130` | Berger Paints (I) Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 131 | `COMP_TOP200_131` | Kansai Nerolac Paints Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 132 | `COMP_TOP200_132` | Page Industries Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 133 | `COMP_TOP200_133` | Jubilant Foodworks Limited | 71 | 25 | 25 | 16 | 30 | `CRAWLED` | 25 | 25 | `VERIFIED_JOBS` |
| 134 | `COMP_TOP200_134` | Voltas Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 135 | `COMP_TOP200_135` | Havells India Limited | 42 | 25 | 25 | 17 | 0 | `CRAWLED` | 25 | 25 | `VERIFIED_JOBS` |
| 136 | `COMP_TOP200_136` | Crompton Greaves Consumer Electricals Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 137 | `COMP_TOP200_137` | Whirlpool of India Limited | 16 | 0 | 0 | 16 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 138 | `COMP_TOP200_138` | Alkem Laboratories Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 139 | `COMP_TOP200_139` | Biocon Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 140 | `COMP_TOP200_140` | Glenmark Pharmaceuticals Limited | 17 | 0 | 0 | 17 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 141 | `COMP_TOP200_141` | Fortis Healthcare Limited | 79 | 25 | 25 | 15 | 39 | `CRAWLED` | 25 | 25 | `VERIFIED_JOBS` |
| 142 | `COMP_TOP200_142` | Dr. Lal Path Labs Ltd. | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 143 | `COMP_TOP200_143` | Metropolis Healthcare Limited | 33 | 0 | 0 | 15 | 18 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 144 | `COMP_TOP200_144` | PVR INOX Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 145 | `COMP_TOP200_145` | Delhivery Limited | 18 | 0 | 0 | 18 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 146 | `COMP_TOP200_146` | Info Edge (India) Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 147 | `COMP_TOP200_147` | Container Corporation of India Limited | 12 | 0 | 0 | 12 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 148 | `COMP_TOP200_148` | Ashok Leyland Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 149 | `COMP_TOP200_149` | TVS Motor Company Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 150 | `COMP_TOP200_150` | Bharat Forge Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 151 | `COMP_TOP200_151` | Tube Investments of India Limited | 16 | 0 | 0 | 16 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 152 | `COMP_TOP200_152` | ABB India Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 153 | `COMP_TOP200_153` | Siemens Limited | 22 | 0 | 0 | 14 | 8 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 154 | `COMP_TOP200_154` | 20 Microns Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 155 | `COMP_TOP200_155` | 21st Century Management Services Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 156 | `COMP_TOP200_156` | 360 ONE WAM LIMITED | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 157 | `COMP_TOP200_157` | 3B Blackbio Dx Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 158 | `COMP_TOP200_158` | 3M India Limited | 16 | 0 | 0 | 16 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 159 | `COMP_TOP200_159` | 3P Land Holdings Limited | 18 | 0 | 0 | 18 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 160 | `COMP_TOP200_160` | 3i Infotech Limited | 19 | 2 | 2 | 17 | 0 | `CRAWLED` | 2 | 2 | `VERIFIED_JOBS` |
| 161 | `COMP_TOP200_161` | 5Paisa Capital Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 162 | `COMP_TOP200_162` | 63 moons technologies limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 163 | `COMP_TOP200_163` | A B Cotspin India Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 164 | `COMP_TOP200_164` | A B Infrabuild Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 165 | `COMP_TOP200_165` | A2Z Infra Engineering Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 166 | `COMP_TOP200_166` | AAA Technologies Limited | 17 | 0 | 0 | 17 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 167 | `COMP_TOP200_167` | ABM International Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 168 | `COMP_TOP200_168` | ABM Knowledgeware Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 169 | `COMP_TOP200_169` | ACC Limited | 56 | 0 | 0 | 16 | 40 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 170 | `COMP_TOP200_170` | ACS Technologies Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 171 | `COMP_TOP200_171` | ADF Foods Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 172 | `COMP_TOP200_172` | AGI Greenpac Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 173 | `COMP_TOP200_173` | AGS Transact Technologies Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 174 | `COMP_TOP200_174` | AIA Engineering Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 175 | `COMP_TOP200_175` | AION-TECH SOLUTIONS LIMITED | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 176 | `COMP_TOP200_176` | AK Capital Services Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 177 | `COMP_TOP200_177` | AKI India Limited | 17 | 0 | 0 | 17 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 178 | `COMP_TOP200_178` | AMD Industries Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 179 | `COMP_TOP200_179` | ANDHRA PAPER LIMITED | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 180 | `COMP_TOP200_180` | APL Apollo Tubes Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 181 | `COMP_TOP200_181` | ARCL Organics Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 182 | `COMP_TOP200_182` | ASK Automotive Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 183 | `COMP_TOP200_183` | ATLANTAA LIMITED | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 184 | `COMP_TOP200_184` | AU Small Finance Bank Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 185 | `COMP_TOP200_185` | AURUS GEM CORPORATION LIMITED | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 186 | `COMP_TOP200_186` | AVG Logistics Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 187 | `COMP_TOP200_187` | AVRO INDIA LIMITED | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 188 | `COMP_TOP200_188` | AVT Natural Products Limited | 17 | 0 | 0 | 17 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 189 | `COMP_TOP200_189` | AWL Agri Business Limited | 18 | 0 | 0 | 18 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 190 | `COMP_TOP200_190` | AXISCADES Technologies Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 191 | `COMP_TOP200_191` | AYM Syntex Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 192 | `COMP_TOP200_192` | Aadhar Housing Finance Limited | 12 | 0 | 0 | 12 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 193 | `COMP_TOP200_193` | Aakash Exploration Services Limited | 16 | 0 | 0 | 16 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 194 | `COMP_TOP200_194` | Aarey Drugs & Pharmaceuticals Limited | 15 | 0 | 0 | 15 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 195 | `COMP_TOP200_195` | Aarnav Fashions Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 196 | `COMP_TOP200_196` | Aaron Industries Limited | 15 | 0 | 0 | 15 | 0 | `FAILED` | 0 | 0 | `CRAWL_FAILED` |
| 197 | `COMP_TOP200_197` | Aartech Solonics Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 198 | `COMP_TOP200_198` | Aarti Drugs Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 199 | `COMP_TOP200_199` | Aarti Industries Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |
| 200 | `COMP_TOP200_200` | Aarti Pharmalabs Limited | 14 | 0 | 0 | 14 | 0 | `CRAWLED` | 0 | 0 | `VERIFIED_ZERO` |