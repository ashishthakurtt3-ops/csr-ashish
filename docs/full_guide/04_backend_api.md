# 04. Backend Architecture & REST APIs

**Frozen Timestamp:** `2026-10-29 12:12:48 +05:30`  
**Git Commit Hash:** `0a538883c17b40774c119deb78b9aaff72220606`

---

## 1. API Architecture & Routing Overview

### PLAIN
The backend serves as the bridge between the MySQL database and the user interface. It provides two layers of web addresses: public REST APIs that deliver clean job listings, corporate directories, and CSR statistics in fast JSON format, and a secure administrative back-office panel where managers can review crawl results, inspect system logs, test AI providers, and trigger manual crawl updates.

### TECHNICAL
The application uses standard Django class-free and class-based view controllers mounted via `config/urls.py` and `modules/website/urls/__init__.py`. To ensure compatibility with frontend codebases, public APIs are mounted with dual aliases: directly at the root (e.g. `/jobs/`) and under the `/api/` prefix (e.g. `/api/jobs/`).
The API adopts a **Dual-Mode Contract**:
- **Paginated Envelope**: When called with `?page=N` (e.g. `?page=1&page_size=12`), the response is an object: `{"items": [...], "total": N, "page": P, "page_size": S, "total_pages": TP, "has_next": bool, "has_prev": bool}`.
- **Flat Capped Array**: When called without `?page` (e.g. `/api/jobs/`), the response returns a flat JSON array `[...]` capped at `fallback_limit` (capped to max 100 rows) to prevent accidental bandwidth exhaustion.

---

## 2. Master Route & Endpoint Inventory

### 2.1 Public Core REST APIs (`modules/website/views/`)

| URL Route Pattern | View Function & Location | Methods | Permissions | Serializer / Response Format |
| :--- | :--- | :--- | :--- | :--- |
| `/jobs`, `/jobs/`<br>`/api/jobs`, `/api/jobs/` | `jobs_list_api`<br>`website/views/job_api_views.py:270` | GET | Public | `serialize_job_item()` JSON (Dual Mode) |
| `/jobs/summary`, `/jobs/summary/`<br>`/api/jobs/summary/` | `jobs_summary_api`<br>`website/views/job_api_views.py:755` | GET | Public | Reads `JobSummarySnapshot` JSON (2ms) |
| `/jobs/filters`, `/jobs/filters/`<br>`/api/jobs/filters/` | `jobs_filters_api`<br>`website/views/job_api_views.py:805` | GET | Public | JSON list of available departments & locations |
| `/jobs/<job_id>`, `/jobs/<job_id>/`<br>`/api/jobs/<job_id>/` | `job_detail_api`<br>`website/views/job_api_views.py:530` | GET | Public | Verbatim full job detail JSON payload |
| `/jobs/<job_id>/refresh-status` | `job_refresh_status_api`<br>`website/views/job_api_views.py:780` | POST | Public | Live HTTP 200 HEAD probe on apply URL |
| `/companies`, `/companies/`<br>`/api/companies/` | `company_directory_api`<br>`website/views/company_api_views.py:45`| GET | Public | `serialize_company()` JSON (Dual Mode) |
| `/companies/<company_id>` | `company_detail_api`<br>`website/views/company_api_views.py:110` | GET | Public | Corporate profile & nested stats JSON |
| `/companies/<company_id>/jobs` | `company_jobs_api`<br>`website/views/company_api_views.py:165` | GET | Public | Active public vacancies for single company |
| `/companies/<company_id>/csr` | `company_csr_api`<br>`website/views/company_api_views.py:210` | GET | Public | Active CSR projects for single company |
| `/companies/<company_id>/fetch-live` | `company_fetch_live_api`<br>`website/views/company_api_views.py:250` | POST | Admin/Auth | Triggers immediate real-time crawler sync |
| `/csr/projects`, `/csr/projects/`<br>`/api/csr/projects/` | `csr_projects_api`<br>`website/views/opportunity_api_views.py:35`| GET | Public | `serialize_csr_project()` JSON (Dual Mode) |
| `/csr/opportunities`<br>`/api/csr/opportunities/` | `csr_opportunities_api`<br>`website/views/opportunity_api_views.py:115`| GET | Public | Returns `[]` (100% synthetic opps quarantined) |
| `/stats`, `/stats/`<br>`/api/stats/` | `stats_view`<br>`website/views/home_views.py:40` | GET | Public | Reads `StatsSnapshot` JSON (2ms latency) |
| `/plans`, `/api/plans/` | `subscription_plans_api`<br>`website/views/subscription_api_views.py:30` | GET | Public | JSON array of 4 subscription billing plans |
| `/wallet/balance` | `wallet_balance`<br>`website/views/subscription_api_views.py:120` | GET | Auth | JSON balance in paise and currency |
| `/wallet/topup` | `wallet_topup`<br>`website/views/subscription_api_views.py:145` | POST | Auth | Credits mock wallet balance |
| `/ngo/matches`, `/prospects` | `match_ngo_api`, `prospects_api`<br>`website/views/matching_api_views.py:15` | GET/POST | Auth | Scoring match between NGO profile & CSR projects |

### 2.2 Administrative Portal Views (`modules/admin_panel/views/`)

| Admin Route Pattern | Controller Function & Location | Methods | Permissions | Template Used |
| :--- | :--- | :--- | :--- | :--- |
| `/admin-portal/` | `admin_dashboard_view`<br>`admin_panel/views/dashboard.py:25` | GET | `is_staff` | `templates/admin/dashboard.html` |
| `/admin-portal/audit/run-now/` | `run_audit_now_view`<br>`admin_panel/views/dashboard.py:160` | POST | `is_staff` | Triggers background data integrity audit |
| `/admin-portal/audit/status/` | `audit_status_api`<br>`admin_panel/views/dashboard.py:190` | GET | `is_staff` | JSON progress telemetry of active audit run |
| `/admin-portal/companies/` | `company_list_view`<br>`admin_panel/views/company_views.py:30` | GET | `is_staff` | `templates/admin/companies/list.html` |
| `/admin-portal/jobs/` | `job_list_view`<br>`admin_panel/views/job_views.py:40` | GET | `is_staff` | `templates/admin/jobs/list.html` |
| `/admin-portal/jobs/review/` | `job_review_view`<br>`admin_panel/views/job_views.py:120` | GET/POST | `is_staff` | `templates/admin/jobs/review.html` |
| `/admin-portal/ai-config/` | `ai_config_dashboard`<br>`admin_panel/views/ai_config_views.py:35` | GET/POST | Superuser | `templates/admin/ai/dashboard.html` |
| `/admin-portal/exchange/export/<entity>/` | `export_entity_view`<br>`admin_panel/data_exchange.py:45` | GET | `is_staff` | Streams CSV / XLSX binary file download |
| `/admin-portal/login/`, `/logout/`| `admin_login_view`, `admin_logout_view`<br>`admin_panel/views/auth.py:15` | GET/POST | Public | `templates/admin/auth/login.html` |

---

## 3. Queryset Anatomy & View Mechanics

### 3.1 Public Jobs Endpoint (`jobs_list_api`)
- **Location**: `modules/website/views/job_api_views.py:270`
- **ORM Queryset Construction**:
  ```python
  qs = public_jobs(Job.objects.select_related('company').all())
  
  # Search & filters
  if q:
      qs = qs.filter(Q(job_title__icontains=q) | Q(location__icontains=q) | Q(company__company_name__icontains=q))
  if company_id:
      qs = qs.filter(company_id=company_id)
  if department:
      qs = qs.filter(department__iexact=department)
  if location:
      qs = qs.filter(location__icontains=location)
  if work_mode:
      qs = qs.filter(work_mode__iexact=work_mode)
  if employment_type:
      qs = qs.filter(employment_type__iexact=employment_type)
      
  qs = qs.order_by('-posted_date', '-job_row_id')
  ```
- **Equivalent SQL**:
  ```sql
  SELECT `admin_panel_job`.`job_row_id`, `admin_panel_job`.`job_id`, `admin_panel_job`.`job_title`,
         `admin_panel_job`.`department`, `admin_panel_job`.`location`, `admin_panel_job`.`work_mode`,
         `admin_panel_job`.`employment_type`, `admin_panel_company`.`company_name`
  FROM `admin_panel_job`
  INNER JOIN `admin_panel_company` ON (`admin_panel_job`.`company_id` = `admin_panel_company`.`company_id`)
  WHERE (`admin_panel_job`.`status` = 'ACTIVE' 
     AND `admin_panel_job`.`is_defective` = 0
     AND NOT (`admin_panel_job`.`verification_status` IN ('REJECTED', 'QUARANTINED', 'LEGACY_UNVERIFIED', 'NEEDS_REVIEW'))
     AND NOT (`admin_panel_job`.`job_id` LIKE 'REQ%'))
  ORDER BY `admin_panel_job`.`posted_date` DESC, `admin_panel_job`.`job_row_id` DESC
  LIMIT 12 OFFSET 0;
  ```
- **Public Visibility Output**:
  - Total Jobs in DB: **5,549**
  - Matches Queryset: **1,492**
  - Returned per page: **12**

### 3.2 Public Stats Endpoint (`stats_view`)
- **Location**: `modules/website/views/home_views.py:40`
- **Mechanics**:
  Instead of executing dynamic `COUNT(*)` and `GROUP BY` aggregates over 5,549 jobs and 201 companies (which costs ~25 seconds cold), `stats_view` reads the latest active `StatsSnapshot` payload directly:
  ```python
  snapshot = StatsSnapshot.objects.order_by('-created_at').first()
  if snapshot and snapshot.payload:
      return JsonResponse(snapshot.payload, safe=False)
  ```
- **Latency Benchmark**:
  - Dynamic Calculation: **25,154.27 ms**
  - Snapshot Delivery: **2.37 ms** (Speedup: **10,613x**)

---

## 4. Query Performance, EXPLAIN Output & N+1 Audit

### 4.1 EXPLAIN Execution Plan on Public Jobs

Executing `EXPLAIN` on the primary public jobs query:
```sql
EXPLAIN SELECT job_row_id, job_id, job_title, department, location, employment_type, work_mode 
FROM admin_panel_job 
WHERE status = 'ACTIVE' 
  AND is_defective = 0 
  AND verification_status NOT IN ('REJECTED', 'QUARANTINED', 'LEGACY_UNVERIFIED', 'NEEDS_REVIEW')
  AND job_id NOT LIKE 'REQ%'
ORDER BY posted_date DESC, job_row_id DESC 
LIMIT 12;
```

#### MySQL 8.0.42 Real EXPLAIN Output (EVIDENCE)
```
+----+-------------+-----------------+------------+------+----------------------------------------------------------+-------------------------------------+---------+-------+------+----------+----------------------------------+
| id | select_type | table           | partitions | type | possible_keys                                            | key                                 | key_len | ref   | rows | filtered | Extra                            |
+----+-------------+-----------------+------------+------+----------------------------------------------------------+-------------------------------------+---------+-------+------+----------+----------------------------------+
|  1 | SIMPLE      | admin_panel_job | NULL       | ref  | idx_job_stat_def_ver,admin_panel_job_is_defective_12f94ea4 | admin_panel_job_is_defective_12f94ea4| 1       | const | 4600 |     5.33 | Using where; Using filesort      |
+----+-------------+-----------------+------------+------+----------------------------------------------------------+-------------------------------------+---------+-------+------+----------+----------------------------------+
```

### 4.2 Query Risk Analysis
1. **Using Filesort Risk**:
   - The query uses index `admin_panel_job_is_defective_12f94ea4` to filter rows, but reports `Using filesort` because sorting uses `ORDER BY posted_date DESC, job_row_id DESC`.
   - While execution takes <15ms on 5,549 rows, scaling to 500,000 rows will require a composite index: `KEY idx_active_sort (is_defective, status, posted_date DESC, job_row_id DESC)`.
2. **N+1 Prevention**:
   - All company lookups inside `jobs_list_api` and `csr_projects_api` utilize `select_related('company')`. This executes a single SQL `INNER JOIN` rather than issuing 12 individual queries for company names, eliminating the N+1 problem.

---

## 5. Middleware & Context Processors

### 5.1 StaticCacheMiddleware (`modules/website/middleware.py`)
- Sets `Cache-Control: public, max-age=0, must-revalidate` on all `/static/` responses to ensure updated JavaScript bundles (`app.min.js`) are revalidated immediately by user browsers without caching stale scripts.

### 5.2 Global Context Processor (`modules/website/context_processors.py`)
- Injects global platform branding into all rendered HTML templates:
  - `PLATFORM_NAME`: `'ImpactBridge™ CSR & Job Intelligence OS'`
  - `PLATFORM_VERSION`: `'2.5.0'`
  - `STATIC_VERSION`: `'4.0.1'`
  - `DEBUG`: `False` (in production)
  - `CURRENT_YEAR`: `2026`

