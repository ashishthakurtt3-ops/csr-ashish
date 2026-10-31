# 03c. Crawler Pipeline: Rules, AI Classification & Idempotency

**Frozen Timestamp:** `2026-10-29 12:12:48 +05:30`  
**Git Commit Hash:** `0a538883c17b40774c119deb78b9aaff72220606`

---

## 1. Cleaning, Validation, Rejection & Deduplication Rules

### PLAIN
Web scraping often pulls in junk data: buttons labeled "Apply Now," links to "Terms of Use," corporate press releases, or duplicate job postings published across multiple sub-domains. The crawler enforces strict multi-layered filters. If a scraped text matches a known navigation phrase or if a link points to a bank loan application, the record is flagged as defective and quarantined. When a job is re-scraped, the system computes a cryptographic fingerprint of the application link so the job is updated rather than duplicated.

### TECHNICAL
The cleaning, rejection, and deduplication logic spans `crawler.py`, `detail_extractor.py`, `verification.py`, and `location_normalizer.py`:

| Rule Category | Filter Definition & Location | Exact Matching Condition | Action Taken on Match |
| :--- | :--- | :--- | :--- |
| **Navbar & Action Buttons** | `NAVBAR_BLACKLIST`<br>`modules/crawler_engine/crawler.py:31` | Case-insensitive exact match against 47 tokens: `"careers"`, `"apply now"`, `"view all"`, `"download"`, `"login"`, `"branch locator"`, `"odr portal"`, etc. | Drop candidate in-flight; never insert into database. |
| **Generic CTA Buttons** | `GENERIC_BUTTON_PHRASES`<br>`modules/crawler_engine/crawler.py:48` | Regex: `^(apply(\s+now)?\|view(\s+all)?(\s+roles\|\s+jobs)?\|read\s+more\|know\s+more\|click\s+here\|find\s+a\s+job\|join\s+our\s+team\|future\s+ready\|performance\s+driven\|purpose\s+led)$` | Discarded prior to extraction. |
| **Exact Defect Tokens** | `EXACT_MATCH_DEFECT_TOKENS`<br>`modules/admin_panel/verification.py:257` | Set of 150+ exact tokens: `"Next"`, `"Previous"`, `"Shareholders"`, `"Terms of Use"`, `"Investor Meet & Presentation"`, `"Two-Wheeler Loan"`, `"Housing Loan"`, etc. | Sets `is_defective=True`, `status='QUARANTINED'`, `verification_status='QUARANTINED'`. Excluded from public views. |
| **Navigation Defect Substrings** | `UI_NAV_DEFECT_PATTERNS`<br>`modules/admin_panel/verification.py:21` | Substring match against 250+ patterns: `"Review Accommodations"`, `"Loss of share certificate"`, `"Saksham Niveshak"`, `"Annual Secretarial Compliance"`. | Evaluated by `is_defective_job_record()`; sets `is_defective=True`. |
| **Non-Career Destination URLs**| `NON_CAREER_URL_PATTERNS`<br>`modules/admin_panel/verification.py:321` | Matches commercial/marketing paths: `/blog/`, `shop.`, `/collections/`, `shriramfinance.in/free-credit-score`, `nmdc.co.in/cms-admin/`. | Flagged defective; apply links suppressed. |
| **Indian Location Normalizer** | `location_normalizer.py:45`<br>`modules/crawler_engine/` | Dictionary mapping 28 Indian states, 8 Union Territories, and 400+ cities (Mumbai, Bengaluru, Pune, Delhi NCR, etc.). | Maps raw strings like `"BLR - Manyata"` to `"Bengaluru, Karnataka, India"`. Missing location fallback to `"Pan-India"`. |
| **CSR Budget Normalizer** | `CSR_BUDGET_REGEX`<br>`modules/crawler_engine/crawler.py:80` | Strict Regex: `(?:INR\|Rs\.?\|₹)\s*\d[\d,]*(?:\.\d+)?\s*(?:Crore\|Cr\.?\|Lakh\|Million)?` | Rejects unparseable numbers; records verbatim string in `raw_budget_text`. |
| **SHA-256 URL Deduplication** | `canonical_url_hash`<br>`modules/admin_panel/management/commands/dedupe_jobs.py:40` | `hashlib.sha256(normalize_canonical_url(url).encode()).hexdigest()` | On duplicate hash collision, updates existing row timestamp and marks older duplicates as `status='REMOVED'`. |

### EVIDENCE
Live database defect counts:
```sql
SELECT is_defective, COUNT(*) FROM admin_panel_job GROUP BY is_defective;
-- False (0): 4,600 clean jobs
-- True  (1):   949 quarantined defect jobs
```

---

## 2. Artificial Intelligence Integration (`ai_api_client.py`)

### PLAIN
The system optionally utilizes Large Language Models (LLMs) to classify complex corporate web pages when standard keyword rules are ambiguous. To protect against unpredictable cloud costs, the platform is strictly configured to use free-tier models (such as Google Gemini Flash) and includes an automatic disk cache that saves previous answers so the same webpage is never analyzed twice.

### TECHNICAL
- **File**: `modules/crawler_engine/ai_api_client.py`
- **Config & Zero-Cost Policy**: `modules/crawler_engine/ai_classifier_config.py`
- **Active Providers**:
  - `gemini`: Google Gemini via official free-tier models (`gemini-3.1-flash-lite`, `gemini-2.5-flash`).
  - `grok`: xAI Grok fallback (requires `GROK_FREE_CREDITS_CONFIRMED=true`; otherwise raises `ZeroCostPolicyViolationError`).
  - `openrouter`: Router supporting zero-cost models (`openrouter/free`).
- **Disk Cache**: SQLite database `PersistentDiskCache` at `.cache/ai_cache.sqlite3` caching prompts, responses, model names, and timestamps by SHA-256 payload hash.
- **Quota Guard**: HTTP 429 or 402 raises `QuotaExhaustedError`, triggering graceful checkpointing to `.checkpoints/discovery_checkpoint.json` without failing the crawl run.

### Prompts & Schemas

#### Stage 1: Link Semantics Batch Classification Prompt
```text
You are an enterprise link classifier for official Indian company websites.
Target Company: {company_name} (domain: {domain})

Classify each link in the provided JSON array into:
1. broad_category: MUST be one of:
   - CAREERS_RECRUITMENT, CSR_SOCIAL_IMPACT, SUSTAINABILITY_ESG, 
     REPORTS_PUBLICATIONS, OTHER_COMPANY_INFORMATION, UNRELATED, AMBIGUOUS
2. candidate_category: MUST be one of:
   - CAREERS_LANDING_CANDIDATE, JOBS_LISTING_CANDIDATE, INDIVIDUAL_JOB_CANDIDATE,
     JOB_APPLICATION_CANDIDATE, HR_INFORMATION_CANDIDATE, CSR_OVERVIEW_CANDIDATE,
     CSR_PROJECT_DISCLOSURE_CANDIDATE, CSR_PARTNERSHIP_RFP_CANDIDATE,
     SUSTAINABILITY_REPORT_CANDIDATE, ANNUAL_REPORT_CANDIDATE, CSR_REPORT_CANDIDATE,
     UNKNOWN_REQUIRES_REVIEW
3. confidence: float between 0.0 and 1.0.
4. reasoning: brief 1-sentence explanation based on link text and URL path.

Input Links:
{json_links}

Output strictly valid JSON with format:
[
  {
    "url": "<link url>",
    "broad_category": "<broad>",
    "candidate_category": "<candidate>",
    "confidence": 0.85,
    "reasoning": "..."
  }
]
```

#### Stage 2: Deep Destination Page Classification Prompt
```text
You are an enterprise page classifier for official Indian corporate websites.
Target Company: {company_name}
Target URL: {url}

Page Metadata:
- Title: {title}
- Headings: {json_headings}
- ATS Platform Detected: {ats_platform or 'None'}
- Job Vacancy Count Signals: {job_card_count}
- CSR Section 135 Signals: {statutory_terms_found}

Main Content Excerpt:
{snippet}

Classify the destination page into EXACTLY ONE page_type:
- CAREERS_LANDING_PAGE, JOBS_LISTING_PAGE, INDIVIDUAL_JOB_PAGE, JOB_APPLICATION_PAGE,
  HR_INFORMATION_PAGE, CSR_OVERVIEW_PAGE, CSR_PROJECT_DISCLOSURE, CSR_PARTNERSHIP_OR_RFP,
  SUSTAINABILITY_OR_ESG_REPORT, ANNUAL_REPORT_WITH_CSR_EVIDENCE, CSR_REPORT,
  UNRELATED_PAGE, INACCESSIBLE_PAGE, UNKNOWN_REQUIRES_REVIEW

Output strictly valid JSON with format:
{
  "company_name": "{company_name}",
  "url": "{url}",
  "page_type": "<TYPE>",
  "confidence": 0.90,
  "is_company_match": true,
  "supporting_evidence": ["item 1", "item 2"],
  "contradictory_evidence": [],
  "review_status": "APPROVED" | "REVIEW_REQUIRED" | "REJECTED",
  "reasoning": "..."
}
```

---

## 3. Idempotency, Database Transactions & Race Conditions

### PLAIN
If a web crawler crashes halfway through a run or runs multiple times in the same day, it could easily create thousands of duplicate jobs or leave the database corrupted with half-finished records. To ensure absolute data safety, every crawler operation is idempotent (re-running it produces the exact same clean state) and wrapped in database transactions that automatically cancel any changes if an error occurs.

### TECHNICAL
The crawler implements database safety across four dimensions:
1. **Cryptographic Idempotency**:
   - The primary deduplication key on `admin_panel_job` is `canonical_url_hash` (a unique SHA-256 hash).
   - Before persistence, URLs are normalized via `normalize_canonical_url()` in `modules/crawler_engine/normalizers.py:25` (stripping tracking parameters `utm_*`, session tokens, and trailing slashes).
   - When a job URL is encountered again, MySQL updates the existing record (`last_checked_date = timezone.now()`) rather than inserting a duplicate row.
2. **Atomic Transaction Blocks**:
   - Ingestion routines use `django.db.transaction.atomic()`:
     ```python
     with transaction.atomic():
         Job.objects.bulk_create(new_jobs, ignore_conflicts=True)
         Job.objects.bulk_update(existing_jobs, fields=['last_checked_date', 'status'])
         CompanyCrawlSummary.objects.create(...)
     ```
   - If an unhandled network error or process crash occurs during a crawl, the entire transaction rolls back cleanly, leaving previously verified records intact.
3. **Optimistic Locking & Soft Deletions**:
   - Inactive jobs are never deleted with SQL `DELETE`. Instead, they receive `status='EXPIRED'` or `status='REMOVED'` along with a timestamp `removed_at = timezone.now()`. This preserves historic audit trails and foreign key references.
4. **Race Condition Prevention in Concurrency**:
   - Batch commands utilizing multi-threading or sub-process concurrency operate strictly on isolated company boundaries (`company_id` partitions).
   - Single-entity updates use `select_for_update()` during administrative status reviews in `modules/admin_panel/views/company_views.py:85`.

