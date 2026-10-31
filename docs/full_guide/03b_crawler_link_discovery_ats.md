# 03b. Crawler Pipeline: Link Discovery & ATS Architecture

**Frozen Timestamp:** `2026-10-29 12:12:48 +05:30`  
**Git Commit Hash:** `0a538883c17b40774c119deb78b9aaff72220606`

---

## 1. Link Discovery Engine (`rediscover_links`)

### PLAIN
Many corporate crawlers fall into the "Homepage Fallback Trap": when a crawler fails to find a direct career portal, it lazy-defaults to the company's main homepage (e.g., `https://tatapower.com/` instead of `https://jobs.tatapower.com/`). This pollutes the database with useless links that take job seekers to general corporate advertising. The `rediscover_links` subsystem visits the company's official domain, analyzes navigation menus, footers, and links, scores their semantic relevance, checks redirects, and verifies that the destination actually contains job vacancy cards before updating the database.

### TECHNICAL
Implemented in `modules/admin_panel/management/commands/rediscover_links.py:28` and supported by `modules/crawler_engine/discovery_helpers.py:39`.
The discovery process follows a multi-stage scoring heuristic:
1. **Candidate Extraction**: `candidate_collector.py:45` parses all `<a>` tags and identifies context (`NAV_HEADER`, `FOOTER_NAV`, `BODY_CONTENT`).
2. **Path & Keyword Scoring**: Links matching patterns like `/careers`, `/jobs`, `/en/careers`, or subdomains like `careers.company.com` receive priority weights (+0.4 to +0.8).
3. **Deep URL Verification**: `is_real_deep_url(url, base_url)` ensures the candidate is not just the homepage.
4. **Registrable Domain & ATS Equivalence**: `is_same_registrable_domain_or_ats()` verifies that external links match known ATS platforms in `config/ats_domains.json` or share the corporate apex domain (`tatamotors.com` vs `careers.tatamotors.com`).
5. **Content Verification Gate**: `verify_careers_url_content(url, html)` evaluates the destination page for job action phrases (`JOB_ACTION_PHRASES`), vacancy listing patterns (`JOB_URL_PATTERNS`), or CSS classes (`REPEATED_CARD_CLASSES`).
6. **Confidence Scoring**: Assigns a float score (0.0 to 1.0) written to `admin_panel_company.careers_url_confidence`.

### EVIDENCE
- Command: `python manage.py rediscover_links --dry-run`
- Function Signature: `verify_careers_url_content(url: str, html: str) -> Tuple[bool, str, int]` in `modules/crawler_engine/discovery_helpers.py:155`
- Database Field: `admin_panel_company.careers_url_confidence` (Float, default 0.0)

---

## 2. ATS Platform Detection & Adapter Architecture

### PLAIN
Large companies rarely host job applications on their main website; they redirect candidates to specialized recruitment platforms called Applicant Tracking Systems (ATS). Because each ATS uses different data formats—some provide hidden JSON data feeds, while others load job listings with JavaScript—the crawler includes tailored adapters for each major ATS platform.

### TECHNICAL
The master dispatcher `ATSParser` in `modules/crawler_engine/parsers/ats.py:1260` matches URLs against domain signatures in `config/ats_domains.json` and delegates to specific adapter classes derived from `BaseATSAdapter`:

| ATS Platform | Signature Patterns | Data Extraction Strategy | Field Mapping & Pagination | Code Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Oracle Taleo** | `taleo.net`, `oraclecloud.com`, `/careersection/` | Multi-stage JSON-RPC POST / REST API query to `.../requisitionList.ajax` | Pagination via `pageNo` and `pageSize=50`. Extracts `jobId`, `jobTitle`, `primaryLocation`, `description`. | `modules/crawler_engine/parsers/ats.py:640` |
| **SAP SuccessFactors** | `successfactors.com`, `jobs.company.com` | Career Site Builder (CSB) table scraper and pagination query `?q=&startrow=N` | Paginates by increments of 25. Extracts requisition ID, location string, posting date from HTML attributes. | `modules/crawler_engine/parsers/ats.py:530` |
| **Workday** | `myworkdayjobs.com`, `/wday/cxs/` | Direct internal REST API: `POST /wday/cxs/{tenant}/{site}/jobs` | Payloads include `limit=20`, `offset=N`. Maps `title`, `externalPath`, `locationsText`, `postedOn`. | `modules/crawler_engine/parsers/ats.py:210` |
| **Lever** | `jobs.lever.co/{tenant}` | Public JSON API: `GET https://api.lever.co/v0/postings/{tenant}?mode=json` | Single or paginated JSON list. Maps `text` -> `title`, `categories.location`, `hostedUrl`. | `modules/crawler_engine/parsers/ats.py:150` |
| **Greenhouse** | `boards.greenhouse.io/{tenant}`| Public JSON feed: `GET https://boards-api.greenhouse.io/v1/boards/{tenant}/jobs?content=true` | Full structured vacancies with `title`, `location.name`, `content` (HTML description), `absolute_url`. | `modules/crawler_engine/parsers/ats.py:95` |
| **SmartRecruiters** | `smartrecruiters.com/{tenant}` | JSON REST API: `GET https://api.smartrecruiters.com/v1/companies/{tenant}/postings` | Paginates via `offset` and `limit=100`. Maps `name`, `location.city`, `department.label`. | `modules/crawler_engine/parsers/ats.py:330` |
| **Darwinbox** | `darwinbox.in`, `darwinbox.com` | HTML DOM table parsing + internal search POST endpoint | Scrapes cards with class `.job-list-card`. Extracts requisition ID and city. | `modules/crawler_engine/parsers/ats.py:780` |
| **Keka** | `keka.com/careers` | Angular public API `/api/careers/jobs` | JSON array containing active job requisition objects. | `modules/crawler_engine/parsers/ats.py:870` |
| **Zoho Recruit** | `zohorecruit.com`, `zohorecruit.in` | XML / JSON embed widget endpoints | Scrapes career portal embed IFrames and JSON payloads. | `modules/crawler_engine/parsers/ats.py:990` |

### EVIDENCE
Live database platform breakdown across all 5,549 jobs:
```sql
SELECT ats_platform, COUNT(*) FROM admin_panel_job GROUP BY ats_platform ORDER BY COUNT(*) DESC;
-- NULL:              5,343  (Generic corporate career sites)
-- SuccessFactors:      177  (Tata Power, Larsen & Toubro, etc.)
-- Oracle_Cloud:         25  (Financial services & automotive)
-- Lever:                 4  (Tech/Fintech entities)
```

---

## 3. Universal Job Detail Extractor (`UniversalJobDetailExtractor`)

### PLAIN
Once a job opening is discovered, the pipeline must fetch the full job post to read the description, requirements, responsibilities, and qualifications. The `UniversalJobDetailExtractor` reads the full web page, strips out website menus and social media share buttons, and identifies specific headings (such as "What You Will Do" or "Key Qualifications") to build a clean, structured job summary.

### TECHNICAL
- **File & Class**: `modules/crawler_engine/parsers/detail_extractor.py:92` (`UniversalJobDetailExtractor`)
- **Method**: `extract_from_url(detail_url: str, preloaded_html: Optional[str] = None) -> Dict[str, Any]`
- **Extraction Capabilities**:
  1. **Schema.org / JSON-LD Extraction**: Uses `extruct` to extract `JobPosting` schema definitions (`title`, `description`, `datePosted`, `employmentType`, `hiringOrganization`, `jobLocation`).
  2. **Microdata & OpenGraph**: Extracts `og:title`, `og:description`, `meta[name="description"]`.
  3. **Section Boundary Parsing**: Uses regular expressions across `<h2>`, `<h3>`, `<strong>`, `<b>` tags to segment text into `responsibilities`, `qualifications`, `preferred_skills`, `benefits`.
  4. **Strict Grounding Rule**: If a field is omitted by the corporate source (such as salary), the extractor sets the value to `None`. It never invents, guesses, or defaults values.
- **Output Dictionary Keys**:
  `title`, `location`, `department`, `employment_type`, `work_mode`, `experience`, `education`, `job_description`, `responsibilities`, `qualifications`, `salary`, `salary_currency`, `posted_date`, `detail_fetch_status`.

---

## 4. Network Layer & Anti-Bot Bypassing

### PLAIN
Corporate career sites and cloud ATS platforms frequently block automated web scrapers using Web Application Firewalls (such as Cloudflare, Akamai, or AWS WAF). The platform utilizes specialized networking libraries that mimic real web browsers, preventing blocking while respecting server load limits.

### TECHNICAL
The network client configuration in `modules/crawler_engine/access_detector.py` and `crawler.py` incorporates:
1. **TLS / JA3 Fingerprint Impersonation**: Uses `curl_cffi` with `impersonate="chrome120"` to replicate Google Chrome's exact TLS handshake, cipher suite order, and HTTP/2 settings.
2. **Realistic Browser Headers**:
   ```python
   HEADERS = {
       'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
       'Accept-Language': 'en-US,en;q=0.9',
       'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
       'Sec-Ch-Ua-Platform': '"Windows"',
   }
   ```
3. **Headless Browser Fallback**: When pages require heavy client-side JavaScript execution or return challenge pages, `Playwright` (`playwright.sync_api`) launches Chromium in headless mode, waits for `domcontentloaded` (timeout 15,000 ms), and extracts post-hydration DOM.
4. **Retry & Backoff**: Transient HTTP errors (`429 Too Many Requests`, `502`, `503`, `504`) trigger automated exponential backoff (1.0s to 3.0s sleep).
5. **WAF & Security Block Isolation**: When a company blocks requests (HTTP 403 Forbidden), the crawl summary records `crawl_status='BLOCKED'`, leaving existing approved database records intact without corrupting the dataset.

---

## 5. Enterprise Batching & Top 200 Corporate Index

### PLAIN
The platform manages India's Top 200 listed companies. Crawling 200 complex corporate websites simultaneously would overwhelm the host computer and get its IP address banned. The crawler processes companies in controlled batches of 50, writing progress summaries after each company finishes.

### TECHNICAL
- **Target Population**: 201 corporate entities in `admin_panel_company`:
  - 200 companies prefixed `COMP_TOP200_001` to `COMP_TOP200_200`.
  - 1 legacy test company `COMP_0` (Razorpay).
- **Batch Processing**:
  Management command `crawl_all_companies.py:65` supports:
  - `--batch-size 50`: Slices the company queryset into chunks of 50 to maintain low memory footprints.
  - `--limit N`: Restricts the run to N companies for testing.
  - `--company-id COMP_TOP200_XXX`: Executes an isolated crawl for a single company.
- **Connection Hygiene**: Calls `close_old_connections()` before and after every corporate crawl cycle to prevent stale MySQL connections and connection pool exhaustion during long-running batch operations.

