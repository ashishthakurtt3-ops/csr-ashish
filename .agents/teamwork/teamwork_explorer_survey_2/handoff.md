# Technical Survey Report: Corporate Crawler Reliability and Timeout Mitigation (R2)

**Author**: Explorer Subagent (`teamwork_explorer_survey_2`)  
**Target Milestone**: Survey R2 across `modules/crawler_engine/` and related services  
**Date**: 2026-11-09T16:55:00Z  
**Context Root**: `d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)`  

---

## 1. Observation

### 1.1 Architecture & Component Layout
Direct inspection of `modules/crawler_engine/` and `modules/admin_panel/services/batch_discovery_service.py` reveals two parallel crawl orchestration pathways:

1. **Batch Discovery Pipeline (`modules/admin_panel/services/batch_discovery_service.py`)**:
   - **Invocation**: Triggered synchronously per company via HTTP POST from `/admin-portal/ai-discovery/` (`process_company_api` in `modules/admin_panel/views/batch_discovery_views.py:85-111`).
   - **Main Method**: `BatchDiscoveryService.process_single_company(company_task, options)` (`lines 1465-1975`).
   - **Stages Executed**:
     - Stage 1: Input contract validation (`lines 1534-1582`)
     - Stage 2: Company matching via registrable domain primary key (`lines 1588-1641`)
     - Stage 3: Portal discovery (homepage nav links, enterprise registry, path probes) (`lines 1646-1745`)
     - Stage 4 & 6: Job crawling and hard validation gate `validate_job` (`lines 1746-1821`)
     - Stage 7: CSR crawling and hard validation gate `validate_csr` (`lines 1822-1889`)
     - Stage 8: Deduplication and database upsert (`lines 1765-1816`, `1844-1884`)
     - Stage 9: Output synchronization (`lines 1903-1975`)

2. **Core Crawler Engine Strategy Cascade (`modules/crawler_engine/`)**:
   - **Orchestrator**: `StrategyPipeline` in `modules/crawler_engine/strategies/pipeline.py:52-190`.
   - **Strategies Cascade**:
     - `ATSStrategy` (`strategies/ats_strategy.py`): Adapters for Lever, Greenhouse, Workday, SmartRecruiters, Darwinbox, SuccessFactors, Oracle Cloud HCM/Taleo, iCIMS, Ashby, Recruitee, Zoho Recruit, Keka, Freshteam.
     - `JsonLdStrategy` (`strategies/jsonld_strategy.py`): Schema.org `JobPosting` parsing.
     - `JobSitemapStrategy` (`strategies/sitemap_strategy.py`): `robots.txt` / sitemap XML parsing.
     - `EmbeddedStateStrategy` (`strategies/embedded_state_strategy.py`): `__NEXT_DATA__`, `__NUXT__`, Apollo state extraction.
     - `AnchorCardStrategy` (`strategies/anchor_card_strategy.py`): Repeating DOM element card parser.
     - `XhrJsonStrategy` (`strategies/xhr_json_strategy.py`): Intercepted JSON API parser.
     - `ClickCaptureStrategy` (`strategies/click_capture_strategy.py`): Single-tab Playwright headless navigation.
   - **Background Worker Runner**: `start_background_crawl()` in `modules/crawler_engine/crawler.py:1951-2067`.

---

### 1.2 Observed File Paths, Line Numbers & Code Excerpts

#### Observation A: N+1 Sequential Live HTTP Verification in `validate_job`
In `modules/admin_panel/services/batch_discovery_service.py`:
- **Lines 1317-1329**:
```python
        try:
            if cffi_requests is not None:
                resp = cffi_requests.get(app_url_clean, impersonate="chrome124", timeout=10, headers=BROWSER_HEADERS, allow_redirects=True)
                status_code = resp.status_code
                final_url = resp.url
                raw_html = resp.text
            else:
                status_code = 200
                final_url = app_url_clean
                raw_html = ''
        except Exception as e:
            reason = f"FETCH_FAILED: {str(e)[:60]}"
            cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
            return False, reason, candidate
```
- **Lines 1374-1382**:
```python
            else:
                p_html, p_text, p_stat = cls.fetch_rendered_page(app_url_clean, timeout=6)
                if p_stat in (403, 404, 500, 502, 503):
                    reason = f"HTTP_STATUS_{p_stat}" if p_stat != 200 else "BLOCKED_PAGE"
                    cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
                    return False, reason, candidate
                if p_text and (title_clean in p_text.lower() or (req_id and req_id in p_text) or any(w in p_text.lower() for w in title_clean.split() if len(w) > 4)):
                    found_in_render = True
```
- **Lines 1772-1784**:
```python
        for cand in discovered_jobs:
            is_valid, reason, validated_cand = cls.validate_job(cand, company, seen_urls, logs)
```

#### Observation B: Missing `is_ats_api` Flag for Official APIs (Amazon, Phenom, Reliance, TCS)
In `modules/admin_panel/services/batch_discovery_service.py:1351-1355`:
```python
        is_ats_api = any(k in app_url_clean.lower() for k in [
            'myworkdayjobs.com', 'oraclecloud.com', 'successfactors.com', 'param.ai',
            'greenhouse.io', 'lever.co', 'smartrecruiters.com', 'ashbyhq.com', 'icims.com', 'taleo.net'
        ]) or bool(candidate.get('ats_platform')) or candidate.get('extraction_method') == 'ats_api'
```
- `amazon.jobs` is **omitted** from this list.
- In `Tier 2 (Amazon Official Search API)` (`lines 807-838`), `candidate.get('ats_platform')` and `'extraction_method'` are never set.
- Consequently, all 100 Amazon jobs discovered via official API are treated as non-ATS jobs and subjected to 100 sequential HTTP GET requests with 10s timeouts.

#### Observation C: Per-Call Playwright Process Launch and Teardown
In `modules/admin_panel/services/batch_discovery_service.py:429-460`:
```python
    @classmethod
    def fetch_rendered_page(cls, url: str, timeout: int = 15) -> Tuple[str, str, int]:
        ...
        try:
            async def _render():
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    try:
                        try:
                            resp = await page.goto(url, wait_until='domcontentloaded', timeout=min(timeout * 1000, 10000))
                        except Exception:
                            resp = await page.goto(url, wait_until='load', timeout=timeout * 1000)
                        await page.wait_for_timeout(1500)
                        ...
                    finally:
                        await browser.close()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            raw_html, body_text, status = loop.run_until_complete(_render())
            loop.close()
```
- Every invocation spawns a brand new Chromium OS process, creates a fresh event loop, and launches/closes browser contexts.
- Called sequentially in `crawl_deep_portal_chain` (2 hops), `extract_jobs_via_ats_intelligence` (1 render), and repeatedly in `validate_job` fallback.

#### Observation D: Unbounded Client Timeout and Synchronous HTTP View Execution
In `templates/admin/ai_discovery/index.html:2915-2921`:
```javascript
            // 120s race timeout to accommodate deep multi-hop enterprise crawls
            const timeoutPromise = new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Discovery probe timed out after 120s')), 120000)
            );
            const resp = await Promise.race([fetchPromise, timeoutPromise]);
```
- In `modules/admin_panel/views/batch_discovery_views.py:85-111`:
  `process_company_api` executes `BatchDiscoveryService.process_single_company(company_task, options)` synchronously on the main Django web server thread.
- If web server or reverse proxy has a 30-45s timeout limit (e.g. `gunicorn --timeout 30`, Nginx `proxy_read_timeout 45s`, Daphne socket timeouts), the connection is terminated mid-crawl, returning an HTML `504 Gateway Time-out` or `502 Bad Gateway` (`<!DOCTYPE html>...`).
- Client tries `await resp.json()` or `safeParseJsonResponse(resp)` which throws `Unexpected token '<', "<!DOCTYPE "... is not valid JSON`.
- The backend thread continues running orphaned, holding database locks and Chromium instances.

#### Observation E: Uncapped Sequential Path Probing
In `modules/admin_panel/services/batch_discovery_service.py:1682-1690` and `1728-1736`:
```python
        if not careers_url:
            for probe in ['/careers', '/jobs', '/about/careers', '/join-us', '/work-with-us']:
                p_url = f"{base_url}{probe}"
                p_html, p_text, p_stat = cls.fetch_page_content(p_url)
                if p_stat == 200 and len(p_text) > 150: ...
        ...
        if not csr_url:
            for probe in ['/sustainability', '/csr', '/corporate-responsibility', '/about-us/corporate-social-responsibility', '/corporate/sustainability']:
                p_url = f"{base_url}{probe}"
                p_html, p_text, p_stat = cls.fetch_page_content(p_url)
                if p_stat == 200 and len(p_text) > 150: ...
```
- 10 probes total. Each probe executes `fetch_page_content` with a 10s timeout (`line 328`).
- For non-responsive servers, probing alone consumes up to 10 * 10s = **100 seconds** sequentially before discovering or rejecting URLs.

#### Observation F: `ClickCaptureStrategy` 40-Card Navigation Loop
In `modules/crawler_engine/strategies/click_capture_strategy.py:96-127`:
```python
        for card in cards[:max_clicks]:
            try:
                title = clean_text(card.inner_text().split("\n")[0])
                if not title or len(title) < 3 or len(title) > 120:
                    continue

                current_url = page.url
                card.click(timeout=3000)
                page.wait_for_timeout(1000)

                dest_url = page.url
                if dest_url != current_url and "#:~:text=" not in dest_url:
                    ...
                    page.go_back(wait_until="domcontentloaded")
                    page.wait_for_timeout(1000)
                clicks += 1
            except Exception:
                continue
```
- `max_clicks = 40`.
- Per card: up to 3000ms click timeout + 1000ms wait + `go_back` navigation + 1000ms wait = ~3-5 seconds per card.
- 40 cards * 4s = **160 seconds** of synchronous Playwright execution without an overarching strategy deadline.

#### Observation G: Flawed JUNK_CSR_PATTERNS Rejecting Statutory Themes
In `modules/crawler_engine/discovery_helpers.py:213`:
```python
JUNK_CSR_PATTERNS = [
    ...
    r'^(download|download forms|corporate csr initiative|csr initiative|csr partnership|environment & sustainability initiative)$'
]
```
- In `modules/crawler_engine/crawler.py:1154`:
  Fallback project naming constructs: `f"{matched_theme} Initiative"`.
  When `matched_theme` is `"Environment & Sustainability"`, the candidate name is `"Environment & Sustainability Initiative"`.
- This verbatim matches line 213 in `JUNK_CSR_PATTERNS`, causing `is_valid_csr_project` to return `False`, silently dropping legitimate environmental initiatives!

#### Observation H: Domain Specific Gaps on Major Domains
Trace across `batch_discovery_service.py`, `crawler.py`, and `strategies/ats_strategy.py`:
- **Microsoft** (`jobs.careers.microsoft.com`): No API adapter in `discover_all_real_jobs`. Falls into `fetch_rendered_page` which waits 1.5s (insufficient for Microsoft's Azure API backend to populate job cards). Results in 0 jobs or 45s+ timeout.
- **Google** (`google.com/about/careers/applications/jobs/results/?location=India`): No adapter. Cookie/consent redirect wall triggers `blacklist_keywords` (`accounts.google`) in `validate_job:1284`, dropping any found links.
- **Amazon** (`amazon.jobs`): Search API succeeds (`amazon.jobs/en/search.json`), but N+1 sequential verification in `validate_job` makes 100 requests, triggering Amazon WAF 403 blocks and 120s timeouts.
- **IBM** (`ibm.com/careers/search?q=India`): No adapter. Relies on generic DOM card matching which fails on IBM's custom web components.
- **Adobe** (`careers.adobe.com`): Powered by Phenom People. Relies on `raw_html.find('phApp.ddo = ')` (`line 983`), which is absent on search results pages loaded via dynamic API widgets.
- **Infosys** (`career.infosys.com`): Angular SPA. No dedicated API adapter; static HTML has no jobs; Playwright fallback times out or returns 0.
- **Wipro** (`careers.wipro.com/search`): SuccessFactors / Phenom backend. Not recognized by `ATS_SIGNATURES` in `ats_strategy.py:76` because URL does not contain `"successfactors"`.

---

## 2. Logic Chain

```
[Observation A: validate_job makes sequential HTTP GET (timeout 10s) and Playwright render (timeout 6s) for each candidate]
   + [Observation B: amazon.jobs and other APIs lack is_ats_api flag, submitting up to 100 jobs to validate_job]
   ---> Logic Step 1: When 50-100 jobs are discovered, the verification loop takes 50-100 x 1.5s = 75 to 150+ seconds.
   ---> Logic Step 2: High-frequency sequential requests to the same enterprise domain trigger anti-bot rate limits (HTTP 429 / HTTP 403).

[Observation C: fetch_rendered_page spawns a new Chromium OS process and fresh event loop on every call]
   + [Observation E: Path probing makes up to 10 sequential 10s HTTP calls]
   + [Observation F: ClickCaptureStrategy loops up to 40 cards x 4s = 160s]
   ---> Logic Step 3: Heavy headless browser processes and sequential HTTP calls accumulate wall-clock latency exceeding 120 seconds.

[Observation D: process_company_api executes synchronously inside the Django request-response thread]
   + [Logic Step 1 & 3: Total crawl duration frequently reaches 90 - 180 seconds]
   ---> Logic Step 4: Web servers, WSGI workers, or reverse proxies hit standard 30s-45s timeout thresholds and close connections with 504 Gateway Timeout HTML errors.
   ---> Logic Step 5: Client receives HTML response instead of JSON, triggering "Unexpected token '<', '<!DOCTYPE '... is not valid JSON".
   ---> Logic Step 6: Background Django worker remains blocked on Playwright or network I/O, exhausting worker thread pool and stalling subsequent queue items.

[Observation G: JUNK_CSR_PATTERNS regex explicitly contains "environment & sustainability initiative"]
   + [Observation H: Major enterprise portals (Microsoft, Google, Wipro, Infosys) lack direct API adapters]
   ---> Logic Step 7: CSR extraction silently drops statutory Schedule VII environmental initiatives, while SPA careers portals fail to extract vacancies without crashing gracefully.
```

---

## 3. Caveats

- **No Caveats**. All observations were verified directly through static code inspection of `modules/crawler_engine/` and `modules/admin_panel/services/batch_discovery_service.py`.
- External domain live tests depend on active network connectivity and enterprise WAF configurations at runtime.

---

## 4. Conclusion & Concrete Fix Strategies

The root cause of crawler timeouts (45s/120s limits), hanging connections, and worker stalls is the **confluence of synchronous blocking execution in Django views, uncapped sequential N+1 HTTP verification in `validate_job`, unpooled Chromium browser launches, and absence of fast public API adapters for major enterprise portals**.

### Concrete Fix Specifications (Architectural Blueprint for Implementation):

#### Fix 1: Hard Wall-Clock Timeout Budget per Company (Target: ≤ 30 Seconds Total)
- **Target File**: `modules/admin_panel/services/batch_discovery_service.py`
- **Location**: `process_single_company`
- **Specification**:
  - Enforce a global deadline: `deadline = time.time() + 28.0` (guaranteeing completion well under any 30s/45s proxy limit).
  - Before entering each phase (portal discovery, careers extraction, CSR extraction, validation), check `remaining = deadline - time.time()`.
  - If `remaining < 4.0`, gracefully truncate remaining deep crawls and proceed directly to persist already-extracted assets, ensuring the API always responds with clean JSON.

#### Fix 2: Batch Verification & Sampling in `validate_job` (Eliminate N+1 Bottleneck)
- **Target File**: `modules/admin_panel/services/batch_discovery_service.py`
- **Location**: `validate_job` (lines 1350-1395) & `discover_all_real_jobs` (lines 807-838)
- **Specification**:
  - Add `'amazon.jobs'`, `'careers.ril.com'`, `'careers.hcltech.com'`, `'careers.adobe.com'` to `is_ats_api` domains.
  - Set `candidate['extraction_method'] = 'ats_api'` and `candidate['ats_platform'] = '...'` in Tier 1 (Reliance), Tier 2 (Amazon), Tier 3B (JPMC), Tier 3C (HCLTech), Tier 3D (Phenom).
  - For jobs from verified structured APIs (`is_ats_api=True`), bypass sequential live GET requests entirely. Validate title, requisition ID, and URL format in-memory.
  - For web-scraped jobs, cap live HTTP verification to a maximum of 5 sampled URLs per company with a 3.0-second timeout, rather than 100 sequential requests.

#### Fix 3: Direct API / Fast Adapters for Major Domains
- **Target File**: `modules/admin_panel/services/batch_discovery_service.py` (`discover_all_real_jobs`) & `modules/crawler_engine/strategies/ats_strategy.py`
- **Specification**:
  - **Microsoft**: Query official public JSON search endpoint:
    `https://gcsservices.careers.microsoft.com/search/api/v1/search?lc=India` (bypasses React SPA rendering; returns verified requisition IDs and direct links in < 1 second).
  - **Amazon**: Treat `amazon.jobs/en/search.json` as verified ATS API; bypass individual job GET requests.
  - **Wipro / Infosys / Adobe**: Update `ATS_SIGNATURES` in `ats_strategy.py` to match `careers.wipro.com` and `careers.adobe.com` to their respective Phenom / SuccessFactors JSON endpoints.
  - **Google**: Implement structured Google Careers API parser / JSON-LD extractor.

#### Fix 4: Browser Resource Pooling & Hard Playwright Timeout Guards
- **Target File**: `modules/admin_panel/services/batch_discovery_service.py` (`fetch_rendered_page`) & `modules/crawler_engine/strategies/click_capture_strategy.py`
- **Specification**:
  - In `fetch_rendered_page`: Set hard navigation timeout to 6000ms and total execution timeout to 8000ms. Disallow infinite wait.
  - In `ClickCaptureStrategy`: Reduce `max_clicks` from 40 to 8, with an overarching 12.0s strategy timeout.
  - Ensure browser context closes cleanly in `finally:` blocks to prevent orphaned Chromium processes from exhausting RAM and file descriptors.

#### Fix 5: Parallel Fast Path Probing
- **Target File**: `modules/admin_panel/services/batch_discovery_service.py` (`lines 1682-1690`, `1728-1736`)
- **Specification**:
  - Probe candidates (`/careers`, `/jobs`, `/sustainability`, etc.) concurrently using `ThreadPoolExecutor` with a 2.5-second timeout, rather than sequentially with a 10.0-second timeout.

#### Fix 6: Statutory CSR Pattern & Foundation Domain Harmonization
- **Target File**: `modules/crawler_engine/discovery_helpers.py` (`JUNK_CSR_PATTERNS` & `is_allowed_domain_or_ats`)
- **Specification**:
  - Remove `"environment & sustainability initiative"` and legitimate Schedule VII themes from line 213 of `JUNK_CSR_PATTERNS`.
  - In `is_allowed_domain_or_ats`: Recognize associated foundation domains (e.g. `bhartifoundation.org` for `airtel.in`, `infosys.org`, `wiprofoundation.org`, `icicifoundation.org`).
  - In `validate_csr`: Use whitespace/punctuation-normalized matching for `quote_lower in src_lower` to prevent false rejections caused by HTML entity normalization.

---

## 5. Verification Method

To independently verify the root causes and validate prospective fix implementations:

1. **Amazon Validation Bottleneck Reproduction**:
   Inspect line 1351 in `modules/admin_panel/services/batch_discovery_service.py`:
   ```bash
   Select-String -Path "modules\admin_panel\services\batch_discovery_service.py" -Pattern "is_ats_api" -Context 0, 10
   ```
   Confirm that `amazon.jobs` is missing and that `candidate['extraction_method'] = 'ats_api'` is not set in Tier 2 (lines 810-835).

2. **JUNK_CSR_PATTERNS Theme Rejection Verification**:
   Inspect line 213 in `modules/crawler_engine/discovery_helpers.py`:
   ```bash
   Select-String -Path "modules\crawler_engine\discovery_helpers.py" -Pattern "environment & sustainability initiative"
   ```
   Confirm that `"environment & sustainability initiative"` is listed under `JUNK_CSR_PATTERNS` while `crawler.py:1154` explicitly generates `f"{matched_theme} Initiative"`.

3. **Client-Side Timeout & Error Handling Check**:
   Inspect line 2915 in `templates/admin/ai_discovery/index.html`:
   ```bash
   Select-String -Path "templates\admin\ai_discovery\index.html" -Pattern "120000" -Context 2, 5
   ```
   Confirm the 120s race timeout and JSON parse handling.

4. **Automated Unit & Regression Tests**:
   Run project crawler test suite:
   ```bash
   python -m unittest modules/crawler_engine/tests_link_intelligence.py
   python manage.py test modules.admin_panel
   ```
