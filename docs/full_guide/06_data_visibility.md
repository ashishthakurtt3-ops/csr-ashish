# 06. Data Visibility: Database, API & Screen Attrition

**Frozen Timestamp:** `2026-10-29 12:12:48 +05:30`  
**Git Commit Hash:** `0a538883c17b40774c119deb78b9aaff72220606`

---

## 1. End-to-End Visibility Funnel

### PLAIN
Just because a row exists in the database does not mean it appears on the website. Data passes through multiple inspection gates between the MySQL storage engine, the Django API controllers, and the user's browser. These filters protect users from seeing broken links, marketing banners, navigation buttons, and healthcare articles that were mistakenly ingested by web crawlers.

### TECHNICAL
The visibility funnel measures exact attrition across three tiers:
1. **Tier A (MySQL Storage)**: Raw row counts in database tables.
2. **Tier B (API Queryset Output)**: Rows matching `public_jobs()`, `public_records()`, and `paginate_queryset()`.
3. **Tier C (Screen Rendering)**: Rows dynamically inserted into the DOM by `static/js/app.js`.

### Visibility Funnel Summary Table

| Entity Type | (a) MySQL Rows | (b) API Queryset Output | (c) UI Screen Rendered | Attrition % | Primary Reason for Attrition |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Jobs** | **5,549** | **1,492** | **1,492** (12/page) | **73.1%** | 4,035 inactive/expired/removed rows + 22 active navigation defect rows quarantined. |
| **CSR Projects** | **1,591** | **1,591** | **1,591** (12/page) | **0.0%** | 100% of projects are active, authentic statutory filings passing all safety checks. |
| **CSR Opportunities**| **1,160** | **0** (`[]`) | **0** (Empty State) | **100.0%** | 100% of rows flagged `INVALID_SYNTHETIC` under Phase 1 data integrity enforcement. |
| **Companies** | **201** | **201** (48 Job Public) | **201** (16/page) | **0.0%** | All 201 visible in directory; 153 carry "Login Required" badge on jobs tab. |

---

## 2. Multi-Layer Filter Audit & Code History

Every layer that filters, hides, or mutates data between the database and the screen:

```
MySQL admin_panel_job (5,549 Rows)
  │
  ├── [Layer 1] Status Gate: status == 'ACTIVE'
  │             Hides 4,035 rows (INACTIVE: 3,123, QUARANTINED: 452, EXPIRED: 317, REMOVED: 141, NEEDS_REVIEW: 2)
  │             Remaining: 1,514 rows
  │
  ├── [Layer 2] Defect Token Gate: is_defective == False
  │             Hides 22 active rows matching NAVBAR_BLACKLIST, UI_NAV_DEFECT_PATTERNS
  │             Remaining: 1,492 rows
  │
  ├── [Layer 3] Requisition Prefix Gate: NOT job_id.startswith('REQ')
  │             Hides unverified legacy mock test rows (0 remaining active affected)
  │             Remaining: 1,492 rows
  │
  ├── [Layer 4] Verification Status Gate: verification_status NOT IN (REJECTED, QUARANTINED, etc.)
  │             Excludes unverified crawl candidates (0 remaining active affected)
  │             Remaining: 1,492 rows
  │
  └──► Public API & UI Screen: EXACTLY 1,492 VERIFIED JOBS
```

### Layer Details & Git Blame History

| Filter Layer | Code Location | Condition / Rule | Why It Exists | Introducing Commit | Predates Cleanup? |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Layer 1: Status Lifecycle** | `modules/admin_panel/verification.py:456` | `status='ACTIVE'` | Excludes expired vacancies, soft-deleted rows, and unverified imports. | Initial Commit (`292c1b8`) & updated in `0a53888` | Yes (core model) |
| **Layer 2: Defect Tokens** | `modules/admin_panel/verification.py:441` | `is_defective=False` | Filters out UI navigation boilerplate ("How to Apply", "Gold Loan", "Next >>"). | Commit `0a53888` (Phase 3 / Step 2) | No (Cleanup Phase) |
| **Layer 3: REQ Prefix** | `modules/admin_panel/verification.py:442` | `~Q(job_id__startswith='REQ')` | Isolates legacy synthetic mock seed jobs from live employer postings. | Commit `e00978c` (Phase 1) | No (Cleanup Phase) |
| **Layer 4: Verification State**| `modules/admin_panel/verification.py:443` | `verification_status in PUBLIC_VERIFICATION_STATUSES` | Blocks rejected crawls and unverified draft items. | Commit `0a53888` | No (Cleanup Phase) |
| **Layer 5: Freshness Window** | `modules/admin_panel/verification.py:471` | `last_reconciled_at >= cutoff` | Hides listings older than 72 hours if `ENFORCE_RECONCILE_FRESHNESS=True`. | Commit `0a53888` (Default: False) | No (Cleanup Phase) |
| **Layer 6: Company Access Gate**| `modules/website/views/company_api_views.py:168` | `company__jobs_access='PUBLIC'` | Respects corporate login-wall designations on company detail pages. | Commit `e00978c` | No (Cleanup Phase) |
| **Layer 7: Synthetic Opp Guard**| `modules/admin_panel/verification.py:493` | `~Q(status='INVALID_SYNTHETIC')`| Prevents mirrored CSR project allocations from masquerading as open NGO grants. | Migrations 0013 / 0014 (Phase 1) | No (Cleanup Phase) |

---

## 3. Hidden Rows Grouped by Rule (with Authentic Samples)

### Rule 1: Non-Active Status Filter (4,035 Rows Hidden)
- **Total Count**: 4,035 rows (INACTIVE: 3,123, QUARANTINED: 452, EXPIRED: 317, REMOVED: 141, NEEDS_REVIEW: 2).
- **Reason**: Replaced during crawl reconciliations, expired after 30 days without re-discovery, or soft-deleted.
- **5 Authentic Samples (EVIDENCE)**:
  ```json
  [
    { "job_row_id": 6713, "company_id": "COMP_TOP200_095", "job_title": "Senior AI Engineer", "status": "INACTIVE" },
    { "job_row_id": 6719, "company_id": "COMP_TOP200_095", "job_title": "Staff AI Platform Engineer", "status": "INACTIVE" },
    { "job_row_id": 10889, "company_id": "COMP_TOP200_010", "job_title": "EdgeVerve Systems", "status": "INACTIVE" },
    { "job_row_id": 12334, "company_id": "COMP_TOP200_103", "job_title": "CURRENT OPENINGS – UNITED STATES", "status": "INACTIVE" },
    { "job_row_id": 6477, "company_id": "COMP_TOP200_001", "job_title": "Fraud Alert - Global", "status": "INACTIVE" }
  ]
  ```

### Rule 2: Active Defect Jobs Filter (22 Rows Hidden)
- **Total Count**: 22 rows where `status='ACTIVE'` but `is_defective=1`.
- **Reason**: Crawled text matched navigation boilerplate, cookie banners, commercial products, or governance committees.
- **5 Authentic Samples (EVIDENCE)**:
  ```json
  [
    { "job_row_id": 10526, "company_id": "COMP_TOP200_141", "job_title": "recruitingCEUserTrackings", "is_defective": 1 },
    { "job_row_id": 10527, "company_id": "COMP_TOP200_141", "job_title": "recruitingCEUserSettings", "is_defective": 1 },
    { "job_row_id": 6526, "company_id": "COMP_TOP200_051", "job_title": "Diversity & Inclusion", "is_defective": 1 },
    { "job_row_id": 7360, "company_id": "COMP_TOP200_047", "job_title": "Gold Loan", "is_defective": 1 },
    { "job_row_id": 7687, "company_id": "COMP_TOP200_069", "job_title": "Committees of the Board of Directors", "is_defective": 1 }
  ]
  ```

### Rule 3: Quarantined CMS & Medical Leaks (452 Rows Hidden)
- **Total Count**: 452 rows with `status='QUARANTINED'`.
- **Reason**: Crawler followed corporate blog or consumer health links and scraped medical encyclopedia articles as job titles.
- **5 Authentic Samples (EVIDENCE)**:
  ```json
  [
    { "job_row_id": 6778, "company_id": "COMP_TOP200_063", "job_title": "Cervical Pain: Causes, Symptoms, Types and Treatment" },
    { "job_row_id": 6779, "company_id": "COMP_TOP200_063", "job_title": "What Would You Like To Explore?" },
    { "job_row_id": 6780, "company_id": "COMP_TOP200_063", "job_title": "A-Z Directory" },
    { "job_row_id": 6782, "company_id": "COMP_TOP200_063", "job_title": "Explore By Body Systems" },
    { "job_row_id": 6783, "company_id": "COMP_TOP200_063", "job_title": "Prevention & Lifestyle" }
  ]
  ```

### Rule 4: Quarantined Synthetic CSR Opportunities (1,160 Rows Hidden)
- **Total Count**: 1,160 rows with `status='INVALID_SYNTHETIC'`.
- **Reason**: Mirrored from CSR budget lines by legacy crawler without verified RFP or deadline documentation.
- **5 Authentic Samples (EVIDENCE)**:
  ```json
  [
    { "opp_id": 142, "company_id": "COMP_TOP200_133", "title": "CSR Initiative: Becoming one of the most admired corporate citizens in India..." },
    { "opp_id": 143, "company_id": "COMP_TOP200_133", "title": "CSR Initiative: We believe in pursuing responsible stewardship..." },
    { "opp_id": 144, "company_id": "COMP_TOP200_133", "title": "CSR Initiative: Jubilant FoodWorks is committed to pursuing responsible growth..." },
    { "opp_id": 145, "company_id": "COMP_TOP200_133", "title": "CSR Initiative: Becoming one of the most admired corporate citizens in India..." },
    { "opp_id": 146, "company_id": "COMP_TOP200_133", "title": "CSR Initiative: We believe in pursuing responsible stewardship..." }
  ]
  ```

---

## 4. Detection Criteria for Bad Crawled Data

The platform continuously evaluates candidate records against four explicit defect signatures:
1. **CMS Leaks**: Strings containing words like `"Symptoms"`, `"Causes"`, `"Prevention"`, `"Treatment"`, or URLs matching `/blog/` or `cms.*`.
2. **Action Prompts**: Text matching UI command buttons (`"Apply"`, `"Click Here"`, `"Read More"`, `"Upload Resume"`).
3. **Corporate Governance Boilerplate**: Titles matching statutory committees (`"Audit Committee"`, `"Nomination and Remuneration Committee"`, `"Shareholders Relationship Committee"`).
4. **Consumer Products & Retail Banking**: Titles advertising financial or retail services (`"Personal Loan"`, `"Car Loan"`, `"Fixed Deposit"`, `"Free Credit Score"`).
All records matching these patterns are safely trapped in the database with `is_defective=True` and `status='QUARANTINED'`, ensuring zero pollution of public screens.

