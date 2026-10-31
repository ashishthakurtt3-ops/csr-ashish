# 07. Configuration, Operations, Code Health & Evolution History

**Frozen Timestamp:** `2026-10-29 12:12:48 +05:30`  
**Git Commit Hash:** `0a538883c17b40774c119deb78b9aaff72220606`

---

## 1. Django Settings & Operational Configuration Audit

### PLAIN
The platform configuration specifies how the system connects to the database, where it stores temporary cache files, how it serves static stylesheets, and how it protects itself from web attacks. Sensitive configuration parameters—such as database passwords and AI API keys—are never stored in the source code; they are loaded dynamically from environment variables.

### TECHNICAL
Master settings reside in `config/settings.py` (242 lines). Key parameters include:
- **DEBUG**: Configurable via env; in production set to `False`.
- **SECRET_KEY**: Loaded via `_require_env('SECRET_KEY')`; missing keys abort initialization with `ImproperlyConfigured`.
- **ALLOWED_HOSTS**: Set to `['localhost', '127.0.0.1']`. Wildcard `'*'` is forbidden when `DEBUG=False`.
- **Installed Applications (`INSTALLED_APPS`)**: Standard Django contrib (`admin`, `auth`, `contenttypes`, `sessions`, `messages`, `staticfiles`) plus local domain apps `modules.admin_panel.apps.AdminPanelConfig` and `modules.website.apps.WebsiteConfig`.
- **Database Engine**: `django.db.backends.mysql` connecting to `csr_intelligence_django` with persistent connections (`CONN_MAX_AGE=600`), connection health checks (`CONN_HEALTH_CHECKS=True`), and `SET sql_mode='STRICT_TRANS_TABLES'`.
- **Cache Engine**: Evaluates `REDIS_URL`. If absent, defaults to thread-safe in-memory `django.core.cache.backends.locmem.LocMemCache` (TTL: 300s).
- **Session Engine**: `django.contrib.sessions.backends.cached_db` (reads sessions from memory; writes asynchronously to MySQL).
- **Static Assets**: `STATIC_URL = '/static/'`, `STATIC_ROOT = BASE_DIR / 'staticfiles'`, `STATIC_VERSION = '4.0.3'`.

### Environment Variables Inventory (Names, Types & Purposes Only)

| Environment Variable Name | Data Type | Operational Purpose |
| :--- | :--- | :--- |
| `DEBUG` | Boolean (`True`/`False`) | Toggles detailed error tracebacks vs. production error pages. |
| `SECRET_KEY` | String (Cryptographic) | Signs Django sessions, CSRF tokens, and password reset hashes. |
| `ALLOWED_HOSTS` | Comma-separated Strings | Restricts HTTP Host header values to prevent HTTP Host poisoning. |
| `MYSQL_DB` | String (Identifier) | Target relational database name (`csr_intelligence_django`). |
| `MYSQL_USER` | String (Username) | MySQL database account username. |
| `MYSQL_PASSWORD` | String (Secret) | MySQL database password (never printed or logged). |
| `MYSQL_HOST` | String (Host / IP) | Hostname or IP address of the MySQL server (`127.0.0.1`). |
| `MYSQL_PORT` | Integer (Port) | TCP network port for MySQL service (`3306`). |
| `REDIS_URL` | String (URI, Optional) | Connection string for centralized Redis cache instances. |
| `AI_PROVIDER` | String (`gemini`/`grok`) | Selects active primary LLM classification adapter. |
| `AI_MODEL` | String (Model ID) | Model identifier (e.g., `gemini-3.1-flash-lite`). |
| `AI_CACHE_ENABLED` | Boolean | Toggles SQLite persistent disk caching of AI inferences. |
| `GEMINI_API_KEY` | String (Secret API Key) | Authentication token for Google Gemini free-tier endpoints. |
| `GROK_API_KEY` | String (Secret API Key) | Authentication token for xAI Grok API endpoints. |
| `GROK_ZERO_COST_ONLY` | Boolean | Strict guard ensuring Grok requests never incur commercial fees. |
| `GROK_FREE_CREDITS_CONFIRMED` | Boolean | Administrative assertion that non-billable credits exist. |
| `MAX_API_CALLS_PER_RUN` | Integer | Hard ceiling limiting AI calls per crawler run (default: 50). |
| `RECONCILE_MAX_AGE_HOURS` | Integer | Freshness window threshold (default: 72 hours). |
| `ENFORCE_RECONCILE_FRESHNESS` | Boolean | Controls whether stale jobs are hidden from public views. |

---

## 2. Test Suite Audit & Execution Verification

### PLAIN
The project contains test scripts designed to check whether parsing routines, normalizers, and security filters function properly. Tests that do not require an active database run in milliseconds. Tests that require creating test databases were safely noted but not executed, honoring the read-only mandate of this audit.

### TECHNICAL
The codebase includes two distinct test layers:
1. **Pure Python Unit Tests (`tests_pure/`)**: Standalone tests evaluating normalizers, link scorers, and regex filters without requiring Django database initialization.
2. **Django Integration & Regression Tests (`tests/`)**: Evaluates database querysets, API endpoints, and model signals.

### Test Execution Results (EVIDENCE)
- **Safe Read-Only Suite (`tests_pure/`)**: Executed via `python -m unittest discover tests_pure`:
  ```
  Ran 67 tests in 0.640s
  OK
  ```
  - `test_pure_modules.py`: 24 tests passing (URL normalizers, date parsers, location normalizers).
  - `test_homepage_verifier.py`: 18 tests passing (apex domain extraction, redirect verification).
  - `test_stage1_candidate_collection.py`: 15 tests passing (link scoring, candidate context tags).
  - `test_crawl_review_sample.py`: 10 tests passing (offline HTML parsing assertions).
- **Django Database Suite (`tests/`)**:
  - Test files present: `test_ai_admin_configuration.py`, `test_ai_architecture_requirements.py`, `test_crawler_job_sync.py`, `test_phase1_integrity_and_quarantine.py`, `test_step0_exact_match_standard.py`, `test_stage1_discovery_helpers.py`.
  - Result: **UNKNOWN** (Intentionally omitted from live execution because Django's test runner attempts to issue `CREATE DATABASE test_csr_intelligence_django`, which violates the read-only constraint).

---

## 3. Codebase Health, Static Quality & Technical Debt

| Metric / Concern | Quantitative Measurement | Location & Code Patterns | Technical Risk / Impact |
| :--- | :--- | :--- | :--- |
| **TODO / FIXME / HACK** | **0 occurrences** | Repository-wide grep across `.py`, `.js`, `.html`. | Codebase has been fully groomed; zero dangling developer markers. |
| **Broad Exception Clauses** | **261 occurrences** | `modules/crawler_engine/crawler.py:380`<br>`modules/crawler_engine/parsers/detail_extractor.py:60` | Extensive use of `except Exception:` prevents individual network failures from crashing batch crawler runs. |
| **Bare Exception Clauses** | **0 occurrences** | Zero instances of unadorned `except:`. | All catches bind explicitly to `Exception` or subclass. |
| **Invented / Defaulted Data** | **Eliminated (Phase 1 / Step 0)**| `normalizers.py`, `detail_extractor.py` | Historical crawlers defaulted missing work modes to "On-site" and employment types to "Full-time". Step 0 Standard preserves `None` when source omits values. |
| **Hardcoded ATS Domains** | Pinned in `config/ats_domains.json` | 65 domain signatures in JSON config. | High maintainability; domain additions do not require code modifications. |

---

## 4. History of Cleanup Phases (Phases 0–4 & Stages 1–2)

The project underwent structured remediation cycles documented in repository reports and migrations:

```
[Phase 0: Baseline & Precision Audit] (October 19, 2026)
  └── Evaluated 5,021 raw scraped jobs against golden datasets in tests/golden/.
  └── Discovered 70% of jobs linked to shared landing pages and 86.5% had hardcoded defaults.
  └── Produced reports/BASELINE.md documenting link quality and baseline precision.

[Phase 1: Integrity Enforcement & Synthetic Opportunity Quarantine] (Migrations 0011–0016)
  └── Identified that 1,160 CSROpportunity rows were synthetically cloned from CSRProject rows.
  └── Executed migrations 0013 and 0014 marking 100% of synthetic opps as INVALID_SYNTHETIC.
  └── Added soft deletion tracking (removed_at) and quarantined unverified REQ-* mock jobs.

[Phase 2: AI Classification & Zero-Cost Architecture] (Migrations 0018–0020)
  └── Integrated Google Gemini free-tier (gemini-3.1-flash-lite) and xAI Grok fallback.
  └── Enforced strict zero-cost policy (ZeroCostPolicyViolationError) blocking commercial billing.
  └── Built SQLite disk cache (.cache/ai_cache.sqlite3) and discovery checkpointing.

[Phase 3 / Step 2: Universal Detail Extractor & Defect Gate] (Migrations 0021–0022)
  └── Deployed UniversalJobDetailExtractor for Section 135 CSR tables and deep vacancy pages.
  └── Added is_defective flag, defect_rules_version, and 250+ UI defect rejection patterns.
  └── Added canonical_url_hash unique index (SHA-256) for permanent deduplication.

[Phase 4 / Step 4: Snapshot Caching, Asset Minification & Performance] (Migrations 0023–0025)
  └── Created StatsSnapshot and JobSummarySnapshot pre-aggregation tables.
  └── Dropped /stats API cold latency from 25,154 ms to 2.37 ms warm (10,613x speedup).
  └── Bundled local fonts and minified assets (style.min.css, app.min.js).
```

---

## 5. Security, Privacy & Compliance Evaluation

1. **Legality & Crawling Ethics**:
   - The platform strictly scrapes public, non-authenticated corporate disclosures (annual reports, Section 135 CSR filings) and public job vacancy notices.
   - It respects rate limits, executes with browser impersonation (`curl_cffi`), and explicitly honors corporate login walls: companies requiring authentication are marked `LOGIN_REQUIRED` and their listings are never scraped behind passwords.
2. **Secrets & Credential Hygiene**:
   - Zero API keys, passwords, or secrets are committed to Git. The `.gitignore` file includes `.env`, `*.sqlite3`, and credential dumps.
   - Management commands mask all secret keys when rendering diagnostic outputs (`ai_key_masked = '****'`).
3. **Application Security (OWASP Top 10)**:
   - **SQL Injection**: Prevented by strict use of Django ORM parameterized queries. Raw SQL in snapshot services utilizes parameterized cursor executions.
   - **Cross-Site Scripting (XSS)**: All user-facing strings are escaped via Django template auto-escaping and JavaScript `escapeHtml()` in `app.js:310`.
   - **Cross-Site Request Forgery (CSRF)**: Enforced via `django.middleware.csrf.CsrfViewMiddleware` on all POST endpoints.
   - **Clickjacking**: Mitigated by `django.middleware.clickjacking.XFrameOptionsMiddleware` (`DENY`).

---

## 6. Open Issues & Roadmap to Finished Product

| Area | Current State | Missing Element for Complete Production | Remediation Roadmap |
| :--- | :--- | :--- | :--- |
| **CSR Opportunities** | 100% quarantined (`INVALID_SYNTHETIC`). | Dedicated statutory RFP parser to detect real open grant calls from corporate foundations. | Implement `parsers/csr_rfp.py` targeting foundation grant portals. |
| **Deep Job Descriptions** | 183 fetched, 1,512 parsed from cards, 3,854 `NOT_FETCHED`. | Full body text enrichment across remaining 3,854 inactive/historic records. | Run scheduled background worker with `crawl_job_details.py --limit 500`. |
| **URL Route Redundancy** | Mounted at both root (`/`) and `/api/`, plus duplicate admin includes in `config/urls.py`. | Cleaner, canonicalized URL routing structure. | Consolidate `config/urls.py` to route strictly through versioned `/api/v1/` prefixes. |
| **Database Indexing** | `admin_panel_job` shows `Using filesort` on composite sort. | Composite index covering `(is_defective, status, posted_date, job_row_id)`. | Add migration introducing composite B-tree index on active sort fields. |
| **ROC / CIN Registration** | `admin_panel_company.cin` is 100% NULL across all 201 corporate records. | Official Ministry of Corporate Affairs (MCA) 21-digit CIN alphanumeric identifiers. | Ingest MCA master database CSV to populate CIN numbers. |

