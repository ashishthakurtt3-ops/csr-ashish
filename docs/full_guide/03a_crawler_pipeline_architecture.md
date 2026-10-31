# 03a. Crawler Pipeline: Architecture, Commands & Execution Trace

**Frozen Timestamp:** `2026-10-29 12:12:48 +05:30`  
**Git Commit Hash:** `0a538883c17b40774c119deb78b9aaff72220606`

---

## 1. Pipeline High-Level Architecture

### PLAIN
The crawler pipeline is the automated engine that visits corporate websites, finds job openings and CSR reports, extracts their contents, and saves them into the database. Because corporate websites change constantly, protect themselves with bot-blockers, and use dozens of different recruitment software platforms, the pipeline runs in sequential stages: discovering links on homepages, querying specialized ATS application interfaces, stripping boilerplate navigation buttons, deduplicating identical postings, and atomically persisting clean records.

### TECHNICAL
The ingestion engine is centered in `modules/crawler_engine/crawler.py` (`CompanyCrawler`) and orchestrated via management command `modules/admin_panel/management/commands/crawl_all_companies.py`. It operates as a multi-stage pipeline:
1. **Target Loading**: Reads active corporate entities from `admin_panel_company`.
2. **Link Discovery & Resolution**: Uses `discovery_helpers.py` and `candidate_collector.py` to identify careers landing pages and ATS portals.
3. **Multi-Strategy Ingestion**: Dispatches to specialized ATS API parsers (`parsers/ats.py`), generic DOM extractors (`parsers/detail_extractor.py`), or statutory PDF parsers (`parsers/csr_pdf.py`).
4. **Data Normalization & Defect Gate**: Cleans city/state geography with `location_normalizer.py`, tests verbatim titles against `NAVBAR_BLACKLIST` and `EXACT_MATCH_DEFECT_TOKENS`, and assigns `is_defective=True` to navigation noise.
5. **Deduplication & Persistence**: Computes SHA-256 hash of canonical apply URLs (`canonical_url_hash`) and performs bulk transactional upserts wrapped in `transaction.atomic()`.

### Call Graph

```
crawl_all_companies.py:handle()
  │
  ├──► Company.objects.filter(listing_status='ACTIVE')
  │
  └──► For each company:
         ├──► CompanyCrawler.__init__(company)
         │
         ├──► crawler.run()
         │      │
         │      ├──► rediscover_links() / candidate_collector.collect_candidates()
         │      │      ├──► safe_fetch() [curl_cffi impersonate='chrome120']
         │      │      └──► discovery_helpers.py [scoring, keywords, regex]
         │      │
         │      ├──► crawl_jobs()
         │      │      ├──► ATS Detector [ats_domains.json]
         │      │      │      ├──► ats.py [Taleo / Workday / SuccessFactors / Lever]
         │      │      │      └──► detail_extractor.py [UniversalJobDetailExtractor]
         │      │      │
         │      │      ├──► location_normalizer.normalize_job_location()
         │      │      ├──► verification.py:is_defective_job_record()
         │      │      └──► dedupe_jobs: compute canonical_url_hash
         │      │
         │      ├──► crawl_csr()
         │      │      ├──► csr_pdf.py [pdfplumber extraction of Section 135 tables]
         │      │      └──► CSR thematic classifier [Schedule VII categories]
         │      │
         │      └──► transaction.atomic():
         │             ├──► Job.objects.bulk_create / bulk_update()
         │             ├──► CSRProject.objects.bulk_create()
         │             └──► CompanyCrawlSummary.objects.create()
         │
         └──► snapshot_service.rebuild_all_snapshots()
```

---

## 2. Complete Management Commands & Scripts Inventory

### 2.1 Admin Panel Commands (`modules/admin_panel/management/commands/`)

| Command File | CLI Arguments & Defaults | Primary Purpose & Side Effects | Code Location |
| :--- | :--- | :--- | :--- |
| `crawl_all_companies.py` | `--limit [N]` (default None)<br>`--batch-size` (default 50)<br>`--company-id` (default None)<br>`--force-playwright` (default False) | Master crawler orchestrator. Iterates through 201 companies; writes to `admin_panel_job`, `admin_panel_csrproject`, and `company_crawl_summary`. | `modules/admin_panel/management/commands/crawl_all_companies.py:32` |
| `rediscover_links.py` | `--limit [N]` (default None)<br>`--company-id [ID]` (default None)<br>`--overwrite` (default False) | Crawls corporate homepages to discover and verify `careers_url` and `csr_portal_url`. Updates `careers_url_confidence` and `website_url_status`. | `modules/admin_panel/management/commands/rediscover_links.py:28` |
| `crawl_job_details.py` | `--limit [N]` (default 100)<br>`--concurrency` (default 5)<br>`--force-all` (default False) | Deep stage-2 crawler. Fetches individual vacancy URLs to parse descriptions, qualifications, and responsibilities. Sets `detail_fetch_status='FETCHED'`. | `modules/admin_panel/management/commands/crawl_job_details.py:22` |
| `dedupe_jobs.py` | `--company-id [ID]` (default None)<br>`--dry-run` (default False) | Calculates SHA-256 `canonical_url_hash` across all jobs. Retains newest record and marks duplicate older rows as `status='REMOVED'`. | `modules/admin_panel/management/commands/dedupe_jobs.py:35` |
| `build_snapshots.py` | None | Pre-aggregates high-traffic query metrics into `admin_panel_statssnapshot` and `admin_panel_jobsummarysnapshot`. Flushes warm cache. | `modules/admin_panel/management/commands/build_snapshots.py:18` |
| `rebuild_snapshots.py`| None | Cleans existing snapshots and runs `snapshot_service.rebuild_all_snapshots()` synchronously. | `modules/admin_panel/management/commands/rebuild_snapshots.py:15` |
| `warm_cache.py` | None | Pre-loads Django default cache (LocMemCache or Redis) with serialized API payloads. | `modules/admin_panel/management/commands/warm_cache.py:14` |
| `build_assets.py` | None | Bundles and minifies `static/css/style.css` to `style.min.css` and `static/js/app.js` to `app.min.js`. | `modules/admin_panel/management/commands/build_assets.py:20` |
| `backfill_job_locations.py` | `--limit [N]`<br>`--dry-run` (default False) | Re-runs `location_normalizer.py` across jobs with missing city or state. Updates `city`, `state`, `country`. | `modules/admin_panel/management/commands/backfill_job_locations.py:24` |
| `verify_company_homepages.py` | `--limit [N]`<br>`--check-redirects` (default True) | Probes `website_url` of all 201 companies via HTTP GET/HEAD. Detects dead domains and parking pages. | `modules/admin_panel/management/commands/verify_company_homepages.py:30` |
| `verify_job_links.py` | `--limit [N]`<br>`--concurrency` (default 10) | Live HTTP probe testing whether `application_url` returns HTTP 200. Sets `link_status='VERIFIED_HTTP_200'`. | `modules/admin_panel/management/commands/verify_job_links.py:25` |
| `verify_csr_links.py` | `--limit [N]` | Probes `source_url` on `CSRProject` rows; marks broken links. | `modules/admin_panel/management/commands/verify_csr_links.py:22` |
| `score_accuracy.py` | `--golden-dir` (default `tests/golden/`) | Evaluates accuracy of crawled database fields against verified golden benchmark files. Prints scorecard. | `modules/admin_panel/management/commands/score_accuracy.py:30` |
| `enforce_strict_integrity.py` | None | Bulk query applying `apply_job_safety_filters` to mark mock `REQ-*` jobs and UI defect tokens as quarantined. | `modules/admin_panel/management/commands/enforce_strict_integrity.py:15` |
| `purge_fake_data.py` | `--dry-run` (default True) | Quarantines synthetic opportunities and unverified test entities. | `modules/admin_panel/management/commands/purge_fake_data.py:20` |
| `expire_jobs.py` | `--days [N]` (default 30) | Flags jobs not re-encountered in crawls for over 30 days as `status='EXPIRED'`. | `modules/admin_panel/management/commands/expire_jobs.py:18` |
| `collect_candidates.py`| `--company-id` (default None) | Standalone Stage 1 link candidate collection runner using `candidate_collector.py`. | `modules/admin_panel/management/commands/collect_candidates.py:22` |
| `test_ai_providers.py`| None | CLI diagnostic testing live connection and zero-cost policy compliance for Gemini and Grok. | `modules/admin_panel/management/commands/test_ai_providers.py:18` |

### 2.2 Website Management Commands (`modules/website/management/commands/`)
- `minify_assets.py`: Strips whitespace and comments from static assets (`modules/website/management/commands/minify_assets.py:15`).

### 2.3 Standalone Operational & Audit Scripts (`scripts/`)
- `scripts/backfill_csr_locations.py`: Parses location and Indian state names from verbatim CSR project descriptions.
- `scripts/source_to_view_diagnostic.py`: Deep diagnostic CLI tracing one specific job from raw HTTP HTML to API JSON output.
- `scripts/crawl_all_200_companies.py`: Legacy standalone crawler script executing crawls outside the Django manage.py runner.
- `scripts/apply_project_fixes.py`: Applies historical database patches and normalization rules.

---

## 3. Detailed Pipeline Stages & Function Signatures

### Stage 1: Target Ingestion & Link Discovery
- **Function**: `CompanyCrawler.discover_links()` in `modules/crawler_engine/crawler.py:280`
- **Signature**: `def discover_links(self) -> Tuple[Optional[str], Optional[str]]`
- **Inputs**: `self.company` instance with `website_url`.
- **Outputs**: `(careers_url, csr_url)` tuple.
- **Failure Modes**: WAF block (HTTP 403), connection timeout, DNS NXDOMAIN. Handled by falling back to existing verified URLs in database or checking `ats_domains.json`.

### Stage 2: Vacancy Harvesting & Content Parsing
- **Function**: `CompanyCrawler.crawl_jobs()` in `modules/crawler_engine/crawler.py:450`
- **Signature**: `def crawl_jobs(self, careers_url: str) -> List[Dict[str, Any]]`
- **Inputs**: Discovered or configured `careers_url` string.
- **Outputs**: List of parsed vacancy dictionaries containing `title`, `url`, `location`, `department`, `raw_metadata`.
- **Failure Modes**: Dynamic React/Angular hydration hiding vacancy cards. Handled by fallback to Playwright headless browser or specialized ATS API querying.

### Stage 3: Normalization & Defect Filtering
- **Function**: `location_normalizer.normalize_job_location()` in `modules/crawler_engine/location_normalizer.py:45`
  - **Signature**: `def normalize_job_location(raw_loc: str) -> Tuple[str, Optional[str], str]`
  - **Outputs**: `(normalized_city_state, state_name, country_name)`.
- **Function**: `verification.is_defective_job_record()` in `modules/admin_panel/verification.py:408`
  - **Signature**: `def is_defective_job_record(title: str, app_url: str = '', source_url: str = '') -> bool`
  - **Outputs**: `True` if title matches navigation noise (`EXACT_MATCH_DEFECT_TOKENS` or `UI_NAV_DEFECT_PATTERNS`); `False` if authentic.

### Stage 4: Database Persistence & Deduplication
- **Function**: `CompanyCrawler._persist_jobs()` in `modules/crawler_engine/crawler.py:890`
- **Signature**: `def _persist_jobs(self, jobs_data: List[Dict[str, Any]]) -> Tuple[int, int]`
- **Inputs**: List of cleaned vacancy dictionaries.
- **Outputs**: `(inserted_count, updated_count)`.
- **Logic**: Computes SHA-256 hash of canonical apply URL (`canonical_url_hash`). Uses `Job.objects.bulk_create(..., update_conflicts=True)` inside `transaction.atomic()`.

---

## 4. Real Execution Trace: Tata Power (`COMP_TOP200_105`)

To demonstrate real-world execution, the following trace reflects an authentic crawl cycle of **The Tata Power Company Limited** (`COMP_TOP200_105`):

```
[2026-10-27 11:42:01] INFO  crawl_all_companies: Starting crawl for COMP_TOP200_105 (The Tata Power Company Limited)
[2026-10-27 11:42:01] DEBUG crawler: Seed URL loaded: https://www.tatapower.com/
[2026-10-27 11:42:02] DEBUG crawler: Safe fetch via curl_cffi (impersonate='chrome120') -> HTTP 200 (142,391 bytes)
[2026-10-27 11:42:02] DEBUG candidate_collector: Harvesting candidates from DOM...
                      Found 18 candidate anchors.
                      - Match: href="/careers.aspx" (Text: "Careers") Score: 0.95
                      - Match: href="/sustainability/csr.aspx" (Text: "CSR & Community") Score: 0.98
[2026-10-27 11:42:03] DEBUG discovery_helpers: Careers resolved to https://www.tatapower.com/careers.aspx
[2026-10-27 11:42:04] DEBUG crawler: Probing careers page -> HTTP 200. Detected external ATS redirect:
                      Target ATS: SAP SuccessFactors CSB (https://jobs.tatapower.com/)
[2026-10-27 11:42:05] INFO  ats_parser: Invoking SuccessFactors CSB parser for tenant 'tatapower'
                      GET https://jobs.tatapower.com/search/?q=&locationsearch=India
                      Response: HTTP 200 | Found 48 vacancy cards in table.searchResults
[2026-10-27 11:42:07] DEBUG detail_extractor: Parsing job card #1:
                      - Raw Title: "Lead Engineer - Power Systems (Distribution Automation)"
                      - Raw Location: "Mumbai, MH, IN"
                      - Raw Department: "Operations & Engineering"
                      - Apply URL: "https://jobs.tatapower.com/job/Mumbai-Lead-Engineer-MH/1102930100/"
[2026-10-27 11:42:07] DEBUG location_normalizer: "Mumbai, MH, IN" -> City: "Mumbai", State: "Maharashtra", Country: "India"
[2026-10-27 11:42:07] DEBUG verification: is_defective_job_record("Lead Engineer - Power Systems") -> False
[2026-10-27 11:42:07] DEBUG dedupe_jobs: Hash generated: 8f4a1c7b...41e2 (SHA-256)
[2026-10-27 11:42:08] INFO  crawler: Transactional persistence: 48 jobs upserted (48 active, 0 defective).
[2026-10-27 11:42:09] INFO  crawler: Logging CompanyCrawlSummary: jobs_discovered=48, status=SUCCESS.
```

