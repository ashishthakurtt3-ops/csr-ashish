# Project: AI Bulk Discovery Engine Stabilization

## Architecture
The AI Bulk Discovery Engine (`/admin-portal/ai-discovery/`) enables administrators to upload corporate rosters (CSV/XLSX), discover corporate career portals and statutory CSR initiatives, execute multi-tier web extraction, validate discovered jobs and CSR projects, and persist clean records to the Django database.

The system consists of four interacting architectural layers:
1. **Frontend Administrative SPA (`templates/admin/ai_discovery/index.html`)**:
   - Manages manifest upload, table rendering, company queue, real-time logging terminal, and interactive discovery controls.
2. **API & Middleware Layer (`modules/admin_panel/middleware.py`, `modules/admin_panel/views/batch_discovery_views.py`)**:
   - Enforces authentication and role verification, accepts file uploads, dispatches single-company discovery tasks, and enforces JSON response contracts across all failure modes.
3. **Batch Discovery Service (`modules/admin_panel/services/batch_discovery_service.py`)**:
   - Parses heterogeneous spreadsheets, identifies corporate domains, coordinates portal traversal, bounds execution timeouts, orchestrates extraction tiers, validates candidates, and executes non-destructive DB upserts.
4. **Crawler Engine (`modules/crawler_engine/`)**:
   - Provides ATS strategy adapters, JSON-LD extractors, DOM card parsers, bounded Playwright rendering, and statutory Schedule VII CSR classifiers.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | API Session Expiry JSON Handling | Return structured HTTP 401 JSON instead of 302 HTML login redirect on unauthenticated `/admin-portal/ai-discovery/*` API calls | M1 | Survey 1 |
| 2 | Role Denial JSON Handling | Return structured HTTP 403 JSON instead of 302 redirect when non-admin accesses bulk discovery API endpoints | M1 | Survey 1 |
| 3 | JSON Exception & CSRF Failure Handlers | Custom JSON error handling for 500 server errors and CSRF token failures on discovery API routes | M1 | Survey 1 |
| 4 | Safe Request Payload Parsing | Fix `UnboundLocalError` on malformed/invalid JSON payloads in `process_company_api` | M1 | Survey 1 |
| 5 | Frontend Session Expiry Detection & Queue Pause | Inspect `resp.redirected` and 401/403 status to pause discovery queue, display actionable re-auth alert, and prevent failure cascades | M1 | Survey 1 |
| 6 | Frontend HTML Error Interception | Upgrade `safeParseJsonResponse` to parse error bodies and display clear in-app notifications without syntax parse crashes | M1 | Survey 1 |
| 7 | Global Wall-Clock Timeout Budget (≤ 30s) | Enforce a 28-30s hard wall-clock budget per company crawl to complete safely within server/proxy limits | M2 | Survey 2 |
| 8 | Batch Verification & Fast ATS Validation | Mark structured APIs (`amazon.jobs`, `careers.ril.com`, etc.) as verified ATS APIs; bypass N+1 sequential live GETs; cap live HTTP validation to 5 samples | M2 | Survey 2 |
| 9 | Enterprise ATS Host Registry Expansion | Add `turbohire.co`, `brassring.com`, `eightfold.ai`, `jobvite.com`, `breezy.hr`, `keka.com`, `avature.net`, `cornerstoneondemand.com`, `sap.com` to `ALLOWED_ATS_HOSTS` | M2 | Survey 2 |
| 10 | Major Corporate Portal Direct Adapters | Implement fast public API / structured adapters for Microsoft, Amazon, Adobe, Infosys, and Wipro | M2 | Survey 2 |
| 11 | Bounded Playwright Resource Execution | Set strict 6s navigation and 8s overall timeout for Chromium rendering; ensure guaranteed process teardown in `finally:` blocks | M2 | Survey 2 |
| 12 | Parallel Concurrent Path Probing | Replace sequential 10s probes for `/careers` and `/sustainability` with concurrent worker probes (timeout 2.5s) | M2 | Survey 2 |
| 13 | Statutory CSR Pattern Harmonization | Remove `"environment & sustainability initiative"` from `JUNK_CSR_PATTERNS`; add corporate foundation domain recognition (`is_allowed_domain_or_ats`) | M2 | Survey 2 |
| 14 | Resilient File Ingestion | Graceful `.xls` detection and error formatting; delimiter sniffing (`,`, `;`, `\t`, `|`); UTF-16 encoding support; stream pointer reset | M3 | Survey 3 |
| 15 | Non-Destructive Record Replacement | Retain existing database jobs/CSR records until new candidates pass validation gates; eliminate pre-emptive record purging | M3 | Survey 3 |
| 16 | Synthetic Manifest Test Suite | Unit & integration test cases for CSV, TSV, XLSX, and XLS file formats with varying encodings and delimiters | M4 / E2E | Survey 3 |
| 17 | E2E API & Crawler Integration Test Suite | Opaque-box automated test harness verifying error shielding, session expiry, corporate domain crawling, and extraction | M4 / E2E | Survey 1, 2, 3 |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Non-JSON & Session Expiry API Resilience | `modules/admin_panel/middleware.py`, `modules/admin_panel/views/batch_discovery_views.py`, `templates/admin/ai_discovery/index.html` | none | PLANNED |
| M2 | Crawler Engine Reliability & Corporate Timeout Mitigation | `modules/crawler_engine/discovery_helpers.py`, `modules/crawler_engine/strategies/click_capture_strategy.py`, `modules/crawler_engine/strategies/ats_strategy.py`, `modules/crawler_engine/crawler.py` | none | PLANNED |
| M3 | Batch Discovery Ingestion & Pipeline Stabilization | `modules/admin_panel/services/batch_discovery_service.py` | M2 (interface contracts) | PLANNED |
| M4 | Final E2E Test Pass & Coverage Hardening | Test suite execution (Tiers 1-4) and adversarial verification (Tier 5) | M1, M2, M3, E2E | PLANNED |

---

## Interface Contracts

### 1. API Error Response Contract
All API endpoints serving `/admin-portal/ai-discovery/` (`parse-file/`, `process-company/`, etc.) must return:
```json
{
  "status": "error",
  "error": "<ERROR_CODE>",
  "message": "<Human-readable actionable message>",
  "login_url": "/admin-portal/login/?next=..." (optional for auth errors)
}
```
HTTP Status Codes:
- `401 Unauthorized`: Session expired or unauthenticated request.
- `403 Forbidden`: Authenticated user lacking admin/staff role, or CSRF validation failure.
- `400 Bad Request`: Malformed JSON or invalid file payload.
- `500 Internal Server Error`: Unhandled server exception (formatted as JSON).

### 2. Company Crawl Execution Contract (`process_single_company`)
- **Input**:
  - `company_task`: `{"company_name": str, "website": str, "careers_url": Optional[str], "csr_url": Optional[str]}`
  - `options`: `{"deep_crawl": bool, "extract_jobs": bool, "extract_csr": bool, ...}`
- **Output**:
  ```json
  {
    "status": "success" | "partial" | "error",
    "company_name": str,
    "jobs_discovered": int,
    "jobs_imported": int,
    "csr_discovered": int,
    "csr_imported": int,
    "logs": list[str]
  }
  ```
- **Constraint**: Wall-clock execution time MUST NOT exceed 30 seconds.

### 3. File Parsing Contract (`parse_uploaded_file`)
- **Input**: `file_obj` (stream), `filename` (str)
- **Output**: `list[dict]` where each dict has normalized keys:
  - `'company_name'`, `'website'`, `'careers_url'`, `'csr_url'`
- **Error Behavior**: Raises `ValueError` with clear message on invalid/empty/corrupted files; never throws unhandled `InvalidFileException` or `UnicodeDecodeError`.

---

## Code Layout & Write Boundaries
- **Milestone 1 (M1)**:
  - `modules/admin_panel/middleware.py`
  - `modules/admin_panel/views/batch_discovery_views.py`
  - `templates/admin/ai_discovery/index.html`
- **Milestone 2 (M2)**:
  - `modules/crawler_engine/discovery_helpers.py`
  - `modules/crawler_engine/strategies/click_capture_strategy.py`
  - `modules/crawler_engine/strategies/ats_strategy.py`
  - `modules/crawler_engine/crawler.py`
- **Milestone 3 (M3)**:
  - `modules/admin_panel/services/batch_discovery_service.py`
- **E2E Testing Track**:
  - `tests/test_batch_discovery_pipeline.py`
  - `tests/test_ai_discovery_e2e.py`
  - `TEST_INFRA.md`
  - `TEST_READY.md`
