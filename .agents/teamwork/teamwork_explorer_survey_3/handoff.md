# Comprehensive Technical Survey Report: R3 — Batch Discovery Pipeline and Background Task Stabilization

**Target Scope**: `modules/admin_panel/services/batch_discovery_service.py`, corporate file uploads, background task execution, crawler timeouts, and batch persistence.  
**Survey Agent**: Teamwork Explorer (Survey 3)  
**Date**: 2026-11-09T16:55:00Z  

---

## 1. Observation

### 1.1 Architecture & Workflow Observations

1. **Manifest File Upload & Parsing Entrypoint**:
   - In `modules/admin_panel/views/batch_discovery_views.py:54-82`, `parse_file_api` handles HTTP POST file uploads:
     ```python
     filename = uploaded_file.name
     records = BatchDiscoveryService.parse_uploaded_file(uploaded_file, filename)
     ```
   - In `modules/admin_panel/services/batch_discovery_service.py:91-147`:
     - Line 116-120: Handles Excel files via:
       ```python
       elif filename_lower.endswith(('.xlsx', '.xls')):
           import openpyxl
           wb = openpyxl.load_workbook(file_obj, data_only=True)
       ```
       Direct inspection confirms that `openpyxl` only supports XML-based `.xlsx/.xlsm` spreadsheets. Passing a legacy binary BIFF8 `.xls` file raises `openpyxl.utils.exceptions.InvalidFileException: openpyxl does not support the old .xls file format, please use xlrd to read this file, or convert it to the more recent .xlsx file format.`.
     - Lines 98-108: CSV encoding handling:
       ```python
       content = file_obj.read()
       text = None
       for enc in ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']:
           try:
               text = content.decode(enc)
               break
           except UnicodeDecodeError:
               continue
       if not text:
           text = content.decode('utf-8', errors='replace')
       ```
       `latin-1` accepts any byte sequence without raising `UnicodeDecodeError`. If a user uploads a Windows UTF-16 file (`Unicode Text`), `utf-8` fails, then `cp1252` or `latin-1` decodes it into null-byte corrupted strings (e.g. `\x00C\x00o\x00m\x00p\x00a\x00n\x00y`), causing header mapping failure.
     - Line 109: Rigid delimiter assignment:
       ```python
       delimiter = '\t' if filename_lower.endswith('.tsv') else ','
       reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
       ```
       If a CSV uses semicolons (`;`) or pipes (`|`), standard in European regional Excel exports, the entire row is read as a single un-split header, failing column normalization and returning `"No valid company records found"`.
     - Stream pointer: `file_obj.seek(0)` is never called before reading or passing `file_obj` to `openpyxl.load_workbook`.

2. **Absence of Server-Side Background Task Infrastructure**:
   - In `config/settings.py:52-64`:
     ```python
     INSTALLED_APPS = [
         'django.contrib.admin',
         'django.contrib.auth',
         'django.contrib.contenttypes',
         'django.contrib.sessions',
         'django.contrib.messages',
         'django.contrib.staticfiles',
         'modules.admin_panel.apps.AdminPanelConfig',
         'modules.website.apps.WebsiteConfig',
     ]
     ```
     Neither Celery, Django-Q, Huey, RQ, nor Dramatiq is installed.
   - In `config/settings.py:125-140`:
     Redis is optional; if `REDIS_URL` is omitted, the project defaults to in-memory `LocMemCache`.
   - In `modules/admin_panel/models/__init__.py:1-67`:
     There is no `BatchJob`, `BatchTask`, or `DiscoveryBatch` model in Django ORM.

3. **Client-Side Browser Queue Architecture**:
   - In `templates/admin/ai_discovery/index.html:2761-2814` (`uploadAndStartQueue`):
     - The uploaded file is parsed by `parse_file_api`, and the parsed records are returned to the browser in the HTTP response:
       ```javascript
       companyQueue = data.companies || [];
       ```
     - The entire batch is maintained solely in the browser's JavaScript variable `companyQueue`.
   - In `templates/admin/ai_discovery/index.html:2869-2937` (`processNextCompany`):
     - The client iterates sequentially through `companyQueue` using synchronous `fetch`:
       ```javascript
       const fetchPromise = fetch("{% url 'admin_ai_discovery:process_company' %}", {
           method: 'POST',
           headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
           body: JSON.stringify({ company: companyTask, options: options }),
           signal: window.activeDiscoveryAbortController.signal
       });
       const timeoutPromise = new Promise((_, reject) =>
           setTimeout(() => reject(new Error('Discovery probe timed out after 120s')), 120000)
       );
       const resp = await Promise.race([fetchPromise, timeoutPromise]);
       ```
     - If the admin closes or navigates away from the browser tab, the batch ceases immediately and the remaining queue is lost.
     - If a company crawl exceeds 120 seconds, the client aborts the request, increments `consecutiveNetworkFailures`, and marks the company as failed.

4. **Synchronous Execution and Quadratic Validation Stalls in `batch_discovery_service.py`**:
   - In `modules/admin_panel/views/batch_discovery_views.py:85-112` (`process_company_api`):
     - Receives a single company payload and synchronously calls:
       `result = BatchDiscoveryService.process_single_company(company_task, options)`.
   - In `modules/admin_panel/services/batch_discovery_service.py:1465-1975`:
     - Line 1750: `crawl_deep_portal_chain` traverses up to 2-3 hops, each hop launching headless Playwright if SPA detected:
       `fetch_rendered_page(curr_url)` (lines 429-472) creates a new event loop, launches Chromium, navigates with 10s-15s timeouts, and waits 1.5s for DOM rendering.
     - Line 1751: `discover_all_real_jobs` executes 9 tiers of extraction, including `HybridAIExtractionService.extract_unstructured_jobs` with timeout=18s.
     - Lines 1772-1784: Iterates through each extracted job candidate and invokes `validate_job`:
       - In `validate_job` (lines 1318-1325): Performs a synchronous HTTP GET with `timeout=10` via `cffi_requests`.
       - In lines 1375-1382: If the title is not found in static HTML, it launches headless Playwright `fetch_rendered_page(app_url_clean, timeout=6)`.
       - For 15 job candidates, this results in up to 15 sequential HTTP requests + 15 browser renders, consuming over 150 seconds.
       - This directly breaches the browser's 120s timeout and standard reverse proxy (Nginx 60s, Gunicorn 30s) timeouts.

5. **Pre-emptive Data Destruction on Failed Validation**:
   - In `modules/admin_panel/services/batch_discovery_service.py:1766`:
     ```python
     # STAGE 8: DEDUPLICATE & PURGE OLD BEFORE INSERT
     company.jobs.all().delete()
     ```
   - In line 1844:
     ```python
     company.csr_projects.all().delete()
     ```
   - Both calls execute **before** verifying whether any candidate passes the validation gate (`validate_job` or `validate_csr`).
   - If zero candidate jobs pass validation, all existing verified jobs for that company in MySQL are wiped out, violating `settings.py:238` (`FREEZE_JOB_EXPIRY_AND_DELETION = True`).

6. **Incomplete ATS Host Registry Dropping Authentic Enterprise Jobs**:
   - In `modules/crawler_engine/discovery_helpers.py:401-418`:
     `ALLOWED_ATS_HOSTS` contains:
     `myworkdayjobs.com`, `oraclecloud.com`, `successfactors.com`, `greenhouse.io`, `lever.co`, `smartrecruiters.com`, `ashbyhq.com`, `icims.com`, `taleo.net`, `param.ai`, `ripplehire.com`, `darwinbox.in`, `darwinbox.com`, `peoplestrong.com`, `phenompeople.com`, `phenom.com`.
   - Missing hosts: `turbohire.co` (used by Tata Motors), `brassring.com` (used by IBM), `eightfold.ai`, `jobvite.com`, `breezy.hr`, `keka.com`, `avature.net`, `cornerstoneondemand.com`, `sap.com`.
   - In `batch_discovery_service.py:1274`:
     ```python
     if not is_allowed_domain_or_ats(app_url, comp_domain):
         reason = f"DISALLOWED_HOST: Host for {app_url[:45]} not allowed"
         cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
         return False, reason, candidate
     ```
     Jobs hosted on `tatamotors.turbohire.co` or `jobs.brassring.com` are discarded with `DISALLOWED_HOST`.

7. **Test Suite Status**:
   - Inspection of `tests/` shows 21 test files, but **zero** tests covering `BatchDiscoveryService`, `batch_discovery_views.py`, file upload parsing, or bulk CSV/Excel ingestion.

---

## 2. Logic Chain

```
[Observation 1.1: openpyxl.load_workbook on .xls]
       │
       ▼ (Step 1)
Uploading an .xls file raises openpyxl InvalidFileException, causing an unhandled 500 error in parse_file_api.
       │
[Observation 1.1: rigid CSV delimiter ',' and missing UTF-16 decoding]
       │
       ▼ (Step 2)
Uploading semicolon/pipe CSVs or UTF-16 Windows Excel files causes column mapping to fail, resulting in 400 Bad Request ("No valid company records found").
       │
[Observation 1.2 & 1.3: No server-side queue; client loop executes sequential 120s requests]
       │
       ▼ (Step 3)
Batch state exists solely in browser memory. If session expires (30-60 min into a batch), Django returns HTML login redirect (302/403).
Browser fetch encounters non-JSON HTML, throwing "Unexpected token '<', <!DOCTYPE... is not valid JSON", breaking the entire queue.
       │
[Observation 1.4: validate_job executes sequential HTTP GET + Playwright render per candidate]
       │
       ▼ (Step 4)
When discover_all_real_jobs returns multiple jobs, validate_job runs 10s HTTP checks and 6s Playwright renders sequentially.
Total request execution time exceeds 120s, triggering client timeoutPromise or proxy 504 Gateway Timeout.
       │
[Observation 1.6: ALLOWED_ATS_HOSTS omits turbohire.co, brassring.com, etc.]
       │
       ▼ (Step 5)
Legitimate corporate ATS links from Tata Motors, IBM, etc. fail is_allowed_domain_or_ats and are dropped as DISALLOWED_HOST.
       │
[Observation 1.5: company.jobs.all().delete() executes before validation]
       │
       ▼ (Step 6)
When all candidates are dropped (due to DISALLOWED_HOST, SPA title mismatch, or timeouts), the company's existing database records have already been purged, causing silent data loss.
```

---

## 3. Caveats

1. **External Celery/Redis Dependency**: `config/settings.py` is configured to run without Redis by default (`LocMemCache`). Introducing an external Celery worker requirement would break environments lacking a Redis or RabbitMQ service daemon. Background task stabilization must function with an in-process thread pool / DB-persisted queue or provide a graceful fallback.
2. **Playwright Resource Intensity on Windows**: As observed during testing, launching multiple headless Chromium instances under Windows commit limits can exhaust paging files (`The paging file is too small for this operation to complete`). Headless browser operations in batch discovery must be strictly gated and bounded.
3. **Legacy BIFF8 `.xls`**: Python's `openpyxl` cannot parse `.xls`. If `xlrd` is not installed in the environment, the parser must gracefully catch `.xls` uploads and return a structured JSON validation message explaining the file must be saved as `.xlsx` or `.csv`.

---

## 4. Conclusion & Concrete Remediation Plan

### 4.1 Summary of Root Causes
1. **Parser Fragility**: `.xls` raises unhandled `InvalidFileException`; CSV delimiter autodetection is absent; UTF-16 encoding is unhandled.
2. **Missing Server-Side Batch State**: The entire batch queue lives in browser memory; closing the tab or losing network destroys the run.
3. **Worker Timeout & Starvation**: `validate_job` performs sequential blocking HTTP GET and Playwright calls for every candidate, ballooning execution time past 120 seconds.
4. **Data Destruction on Zero Results**: `company.jobs.all().delete()` runs prior to validation, wiping existing data if no candidates survive the gate.
5. **False Rejections**: Omission of common ATS hosts (`turbohire.co`, `brassring.com`) in `ALLOWED_ATS_HOSTS` drops genuine enterprise jobs.
6. **Session Expiry Non-JSON Crashes**: Long batches outlast admin sessions, triggering HTML login redirects that crash client JSON parsing.

### 4.2 Exact Remediation Plan

#### Phase 1: File Parsing Stabilization (`modules/admin_panel/services/batch_discovery_service.py`)
- **Fix .xls handling** (lines 116-130):
  Check for `.xls` extension or BIFF8 magic bytes (`\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1`). If `xlrd` is installed, use `xlrd.open_workbook`. Otherwise, catch the extension early and return a structured JSON error: `"Legacy .xls format detected. Please save your spreadsheet as .xlsx or .csv."`.
- **Implement Delimiter Sniffing & Encoding Fallback** (lines 97-115):
  - Prepend `'utf-16'`, `'utf-16-le'`, `'utf-16-be'` to encoding candidates before falling back to `'latin-1'`.
  - Use `csv.Sniffer().sniff(text[:4096])` to determine delimiter (`,`, `;`, `\t`, `|`), falling back to `,`.
  - Add `file_obj.seek(0)` before any read or openpyxl call. Wrap in `io.BytesIO(file_obj.read())` to avoid closed stream errors.

#### Phase 2: ATS Host Registry Expansion & False-Positive Elimination (`modules/crawler_engine/discovery_helpers.py`)
- **Expand `ALLOWED_ATS_HOSTS`** (lines 401-418):
  Add: `'turbohire.co'`, `'brassring.com'`, `'eightfold.ai'`, `'jobvite.com'`, `'breezy.hr'`, `'keka.com'`, `'avature.net'`, `'cornerstoneondemand.com'`, `'sap.com'`.

#### Phase 3: Bounded Crawling & Safe Non-Destructive Update (`batch_discovery_service.py`)
- **Non-Destructive Replacement** (lines 1766 & 1844):
  Do NOT purge `company.jobs.all().delete()` before validation. Collect `validated_jobs`. Only purge and replace if `len(validated_jobs) > 0` (or if an explicit `force_empty=True` option is set).
- **Fast Job Validation** (lines 1318-1392):
  - Use `HEAD` or fast GET with a 3.5s timeout for live link checking.
  - Skip headless browser renders during candidate validation if the job was already extracted from structured DOM cards or ATS APIs.
  - Cap overall company crawl budget to 45 seconds to prevent gateway timeouts.

#### Phase 4: Server-Side Batch Persistence & Background Execution (`modules/admin_panel/`)
- **Persisted Batch Tracking Models**:
  Introduce `DiscoveryBatch` and `DiscoveryTask` models in `modules/admin_panel/models/crawler.py` (or dedicated model file) to persist batch state, task status (`PENDING`, `IN_PROGRESS`, `SUCCESS`, `FAILED`), company name, jobs discovered, CSR discovered, and execution logs.
- **Background Execution / Polling**:
  - Implement a thread-pool-based background dispatcher in Django (`concurrent.futures.ThreadPoolExecutor(max_workers=2)`).
  - Provide a status polling endpoint: `/admin-portal/ai-discovery/api/batch/<batch_id>/status/` returning structured JSON.
  - Even if the browser tab disconnects, the server-side batch continues to completion and syncs upon page reload.

#### Phase 5: API Non-JSON Resilience & Frontend Error Shielding (`batch_discovery_views.py` & `index.html`)
- **Structured JSON on All Failure Modes**:
  Decorate `parse_file_api`, `process_company_api`, and batch status views with an error shield returning `{status: "error", code: "...", message: "..."}` with `content_type='application/json'` on 401, 403, and 500 conditions.
- **Frontend Session Expiry Recovery**:
  When the client receives HTTP 401/403 or `{code: "SESSION_EXPIRED"}`, pause the queue, save state to `localStorage`, and display an in-app re-authentication modal instead of throwing unhandled exceptions.

#### Phase 6: Automated Test Suite (`tests/test_batch_discovery_pipeline.py`)
- Create end-to-end unit and integration tests:
  - Test CSV with standard headers, BOM, semicolon delimiters, and messy headers.
  - Test Excel `.xlsx` and `.xls` error handling.
  - Test `process_single_company` with mock HTML/APIs.
  - Test non-destructive data retention when 0 jobs are validated.
  - Test API JSON responses on unauthenticated requests.

---

## 5. Verification Method

To independently verify the survey findings and validate future implementations:

1. **Verify File Parsing Behavior**:
   ```bash
   python -c "
   from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
   import io
   # Test semicolon CSV
   csv_data = io.BytesIO(b'Company Name;Official Website\nTata Motors;https://www.tatamotors.com\n')
   res = BatchDiscoveryService.parse_uploaded_file(csv_data, 'test.csv')
   print('Semicolon CSV parsed:', len(res), res)
   "
   ```
   *Expected Current Failure*: Returns `[]` because delimiter defaults to `,`.

2. **Verify `.xls` Rejection Crash**:
   ```bash
   python -c "
   from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
   import io
   # Minimal BIFF8 header
   xls_data = io.BytesIO(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\x00' * 504)
   try:
       res = BatchDiscoveryService.parse_uploaded_file(xls_data, 'test.xls')
       print('Parsed:', res)
   except Exception as e:
       print('Caught expected failure:', type(e), e)
   "
   ```
   *Expected Current Failure*: Throws `openpyxl.utils.exceptions.InvalidFileException`.

3. **Verify TurboHire ATS Dropping**:
   ```bash
   python -c "
   from modules.crawler_engine.discovery_helpers import is_allowed_domain_or_ats
   print('tatamotors.turbohire.co allowed:', is_allowed_domain_or_ats('https://tatamotors.turbohire.co/dashboardv2', 'tatamotors.com'))
   "
   ```
   *Expected Current Result*: Returns `False` (confirming `turbohire.co` is dropped as `DISALLOWED_HOST`).

4. **Verify Existing Test Suite Execution**:
   ```bash
   python manage.py test tests.test_reliance_adapter tests.test_pilot_batch_crawler --settings=config.settings
   ```
