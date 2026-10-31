# 08. Glossary & Developer FAQ

**Frozen Timestamp:** `2026-10-29 12:12:48 +05:30`  
**Git Commit Hash:** `0a538883c17b40774c119deb78b9aaff72220606`

---

## 1. Project-Specific Glossary

| Term | PLAIN Definition | TECHNICAL Definition | Code Reference |
| :--- | :--- | :--- | :--- |
| **ATS (Applicant Tracking System)** | Software used by employers to post job vacancies, collect resumes, and track candidates. | Third-party cloud recruitment systems (e.g. Oracle Taleo, SAP SuccessFactors, Workday, Lever, Greenhouse) with distinct domain signatures and REST/JSON endpoints. | `modules/crawler_engine/parsers/ats.py:89` |
| **Section 135 & Schedule VII** | An Indian legal mandate requiring large corporations to spend 2% of profits on social development causes. | Legal framework under the Indian Companies Act, 2013; Schedule VII specifies 12 statutory categories (Education, Healthcare, Environment, Rural Livelihood, etc.). | `modules/crawler_engine/crawler.py:67` |
| **rediscover_links** | A smart crawler command that finds a company's direct careers and CSR pages when only the homepage is known. | Command breaking the "Homepage Fallback Trap" by parsing navigation context (`NAV_HEADER`, `FOOTER_NAV`) and computing content scores to update `careers_url`. | `modules/admin_panel/management/commands/rediscover_links.py:28` |
| **COMP_TOP200** | The unique identifier prefix assigned to India's Top 200 listed corporations in the database. | Surrogate primary key pattern `COMP_TOP200_001` through `COMP_TOP200_200` in `admin_panel_company.company_id`. | `modules/admin_panel/models/company.py:15` |
| **Step 0 Exact-Match Standard** | A project quality rule stating the database must only contain real, verbatim data scraped from official websites. | Engineering standard prohibiting hardcoded fallback values (e.g., defaulting missing work modes to "On-site"); missing fields must be stored as `None`. | `tests/test_step0_exact_match_standard.py:1` |
| **is_defective** | A database flag indicating that a scraped job record is actually website navigation noise, not a real vacancy. | Boolean column in `admin_panel_job.is_defective` populated by matching `NAVBAR_BLACKLIST`, `UI_NAV_DEFECT_PATTERNS`, and `EXACT_MATCH_DEFECT_TOKENS`. | `modules/admin_panel/verification.py:408` |
| **canonical_url_hash** | A digital fingerprint used to identify identical job postings and prevent duplicate listings in the database. | SHA-256 cryptographic hash of the tracking-stripped application URL stored in a unique index on `admin_panel_job.canonical_url_hash`. | `modules/admin_panel/management/commands/dedupe_jobs.py:40` |
| **INVALID_SYNTHETIC** | A status assigned to records that were generated artificially by early crawlers rather than discovered as genuine calls. | Lifecycle state in `admin_panel_csropportunity.status` applied by migrations 0013 and 0014 to isolate 1,160 mirrored CSR project lines. | `modules/admin_panel/migrations/0013_mark_synthetic_csr_opportunities.py:2` |
| **StatsSnapshot** | A pre-calculated database summary that allows the homepage to load platform numbers in 2 milliseconds. | Relational model in `modules/admin_panel/models/snapshot.py` storing pre-computed JSON aggregation payloads delivered by `/api/stats/`. | `modules/admin_panel/snapshot_service.py:15` |
| **JobSummarySnapshot** | A pre-calculated JSON cache of active job titles, departments, and counts used by directory filters. | Model caching directory state to decouple high-frequency front-end searches from expensive database table scans. | `modules/admin_panel/snapshot_service.py:65` |
| **AuditRun** | An administrative record that tracks each time data quality audits and snapshot rebuilds are executed. | Relational model `modules/admin_panel/models/snapshot.py:45` linking snapshot generations with specific defect rule versions. | `modules/admin_panel/models/snapshot.py:45` |
| **candidate_collector** | An extraction helper that scans an HTML homepage and categorizes every link into potential careers or CSR leads. | Ingestion utility in `modules/crawler_engine/candidate_collector.py:25` extracting link text, URLs, and DOM parent containers. | `modules/crawler_engine/candidate_collector.py:25` |
| **UniversalJobDetailExtractor**| A universal web parser that reads full job post pages to extract descriptions, requirements, and qualifications. | Extractor in `modules/crawler_engine/parsers/detail_extractor.py:92` combining Schema.org JSON-LD, OpenGraph, and regex heading boundaries. | `modules/crawler_engine/parsers/detail_extractor.py:92` |
| **curl_cffi / chrome120** | A specialized web client that tricks anti-bot security systems into thinking Python is a regular Google Chrome browser. | Low-level C-based Python HTTP library replicating browser TLS handshakes, JA3 signatures, and HTTP/2 frames. | `modules/crawler_engine/access_detector.py:20` |
| **ZeroCostPolicyViolationError**| A safety error raised if any component attempts to make a paid commercial API call to an LLM provider. | Python exception in `modules/crawler_engine/ai_api_client.py:51` blocking execution if non-free API credits would be billed. | `modules/crawler_engine/ai_api_client.py:51` |
| **Dual-Mode Contract** | An API design where endpoints return flat lists for simple views, or structured pages when given a page number. | Pagination contract in `modules/website/utils/pagination.py:15` returning either a flat JSON array or an envelope `{items, total, page}`. | `modules/website/utils/pagination.py:15` |
| **CompanyCompletenessRegister**| A diagnostic table evaluating whether each company's website, careers page, and ATS have been discovered. | Table `company_completeness_register` auditing five dimensions of discovery readiness across all 201 corporate entities. | `modules/admin_panel/models/company.py:165` |
| **public_jobs()** | The master security filter that dictates which job records may be shown to the public. | ORM filter in `modules/admin_panel/verification.py:451` filtering `status='ACTIVE'`, `is_defective=False`, excluding `REQ-*` and rejected statuses. | `modules/admin_panel/verification.py:451` |

---

## 2. Developer & Operations FAQ

### Q1: How do I start the development or production server locally?
**A**: Make sure MySQL is running on port 3306. Activate the virtual environment and start Waitress:
```powershell
.\.venv\Scripts\Activate.ps1
python -m waitress --port=8000 --threads=8 config.wsgi:application
```
Access the public portal at `http://localhost:8000/`.

---

### Q2: How do I inspect a single company's jobs and CSR projects?
**A**: You can use Django management commands or query endpoints directly:
- CLI Check:
  ```powershell
  python manage.py shell -c "from modules.admin_panel.models import Company; c = Company.objects.get(company_id='COMP_TOP200_105'); print(c.company_name, 'Jobs:', c.jobs.filter(status='ACTIVE', is_defective=False).count(), 'CSR:', c.csr_projects.count())"
  ```
- REST API:
  - Jobs: `GET http://localhost:8000/api/companies/COMP_TOP200_105/jobs`
  - CSR: `GET http://localhost:8000/api/companies/COMP_TOP200_105/csr`

---

### Q3: How do I rebuild snapshot caches when database numbers change?
**A**: When new companies are crawled or records are reconciled, update the snapshot tables to immediately reflect the new numbers on the public website:
```powershell
python manage.py rebuild_snapshots
python manage.py warm_cache
```

---

### Q4: How do I run a crawl for just one company without waiting for all 200?
**A**: Pass the target `--company-id` flag to `crawl_all_companies`:
```powershell
python manage.py crawl_all_companies --company-id COMP_TOP200_042
```
This restricts network activity to the specified company's careers portal, executes deduplication, and writes a single `CompanyCrawlSummary` entry.

---

### Q5: How do I test AI page classification without getting billed?
**A**: The system enforces zero-cost compliance by default. Ensure your `.env` contains your free Google Gemini API key:
```env
AI_PROVIDER=gemini
GEMINI_MODEL=gemini-3.1-flash-lite
GEMINI_API_KEY=your_key
GROK_ZERO_COST_ONLY=true
```
Run the diagnostic verification tool:
```powershell
python manage.py test_ai_providers
```
If an unconfirmed paid model is configured, the system raises `ZeroCostPolicyViolationError` and halts safely.

---

### Q6: How do I verify whether an individual job URL is live or broken?
**A**: You can run the link verification command, or send a POST request to the refresh status endpoint:
- CLI:
  ```powershell
  python manage.py verify_job_links --limit 50
  ```
- HTTP:
  ```http
  POST /api/jobs/6524/refresh-status
  ```
  The server issues an authenticated HEAD/GET probe and returns `{"link_status": "VERIFIED_HTTP_200", "http_status": 200}`.

---

### Q7: Why do CSR Opportunities return 0 results on the website?
**A**: During Phase 1 data auditing, all 1,160 legacy `CSROpportunity` rows were discovered to be automated clones of `CSRProject` lines. Because statutory corporate CSR budget allocations are not public invitations for NGO proposals, showing them as "open grant applications" misled users. All 1,160 rows were marked `status='INVALID_SYNTHETIC'` in migrations 0013 and 0014 and are hidden by `modules/admin_panel/verification.py:493` until dedicated foundation RFP parsers are deployed.

---

### Q8: How do I export verified data to CSV or Excel?
**A**: Log into the enterprise back office at `http://localhost:8000/admin-portal/` with a staff user account. Navigate to the **Data Exchange Hub** (`/admin-portal/exchange/export/<entity>/`):
- `/admin-portal/exchange/export/companies/?format=csv`
- `/admin-portal/exchange/export/jobs/?format=csv`
- `/admin-portal/exchange/export/csr/?format=xlsx`
Filters applied on the export screen ensure quarantined defect rows are omitted from business exports.

---

### Q9: How do I run unit tests without modifying the MySQL database?
**A**: Execute the pure Python unit test suite:
```powershell
python -m unittest discover tests_pure
```
This runs 67 tests in ~0.6 seconds testing normalizers, domain extractors, and link classifiers completely in memory.

---

### Q10: Where do I find the authoritative database schema?
**A**: All model structures are defined under `modules/admin_panel/models/`. You can view raw MySQL table definitions in `scratch/show_create_tables.json` or by running:
```powershell
python manage.py shell -c "from django.db import connection; c = connection.cursor(); c.execute('SHOW CREATE TABLE admin_panel_job'); print(c.fetchone()[1])"
```

