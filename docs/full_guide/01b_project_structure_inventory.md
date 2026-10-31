# 01b. Project Structure & Codebase File Inventory

**Frozen Timestamp:** `2026-10-29 12:12:48 +05:30`  
**Git Commit Hash:** `0a538883c17b40774c119deb78b9aaff72220606`

---

## 1. Architectural Layout & Logic Inventory

### PLAIN
The codebase is structured into modular applications. `config/` houses master server settings, `modules/admin_panel/` powers the administrative back office and relational database models, `modules/crawler_engine/` houses scraping spiders and text normalizers, and `modules/website/` serves public search pages and JSON APIs. Utility scripts, golden benchmark tests, and diagnostic scripts occupy dedicated directories.

### TECHNICAL
The project contains 100% of its logic partitioned across 4 primary namespaces:
1. `config`: Core Django settings, WSGI/ASGI handlers, and ATS domain dictionaries.
2. `modules/admin_panel`: 15 models, 25 migrations, 35 management commands, data exchange utilities, and back-office controllers.
3. `modules/crawler_engine`: Dedicated crawler classes, 14 ATS adapters, Playwright headless fallbacks, Trafilatura extractors, location normalizers, and the zero-cost AI API client.
4. `modules/website`: Client-facing controllers, dual-mode pagination utilities, custom static cache middleware, context processors, and single-page application templates.

---

## 2. Complete Folder Tree with Purpose Annotations

```
CSR_Job_Intelligence_Production_Ready/
│
├── config/                                 # Project configuration root
│   ├── __init__.py                         # Package initializer
│   ├── asgi.py                             # ASGI configuration for async entrypoints
│   ├── ats_domains.json                    # Domain signature lookup for known ATS platforms
│   ├── keywords.json                       # Keyword dictionary for CSR and job categorization
│   ├── settings.py                         # Django master settings (apps, DB, cache, auth)
│   ├── shared_tenants.json                 # Tenant registry for multi-organization ATS portals
│   ├── urls.py                             # Master URL dispatcher mounting admin and website
│   └── wsgi.py                             # WSGI entrypoint with Waitress server bindings
│
├── modules/                                # Core business and engine modules
│   ├── admin_panel/                        # Enterprise back-office administrative portal
│   │   ├── apps.py                         # AdminPanelConfig application definition
│   │   ├── data_exchange.py                # CSV/XLSX export/import engine for master entities
│   │   ├── management/commands/            # Administrative and operational CLI commands
│   │   │   ├── audit_link_quality.py       # Audits direct vs. listing-like URLs across records
│   │   │   ├── audit_public.py             # Audits public safety filter leakage
│   │   │   ├── audit_reconcile.py          # Verifies database reconciliation status
│   │   │   ├── backfill_job_link_metadata.py # Enriches jobs with canonical hash & link metadata
│   │   │   ├── backfill_job_locations.py   # Normalizes city, state, country on job records
│   │   │   ├── backup_database.py          # Executes mysqldump snapshots of relational schema
│   │   │   ├── build_assets.py             # Minifies CSS/JS and bundles production assets
│   │   │   ├── build_single_review_file.py # Compiles multi-module codebase reviews
│   │   │   ├── build_snapshots.py          # Pre-aggregates stats and job summaries into snapshots
│   │   │   ├── collect_candidates.py       # Stage 1 candidate link collection command
│   │   │   ├── crawl_all_companies.py      # Master crawler orchestrator for 201 corporate entities
│   │   │   ├── crawl_job_details.py        # Deep stage-2 detail extraction for raw job URLs
│   │   │   ├── crawl_review_sample.py      # Targeted crawler run on verified golden sample set
│   │   │   ├── create_mysql_schema.py      # Raw SQL schema generator for fresh MySQL instances
│   │   │   ├── dedupe_jobs.py              # Removes duplicate jobs using SHA256 canonical hash
│   │   │   ├── discover_and_verify_company_sources.py # Stage 1 link discovery & verifier
│   │   │   ├── enforce_strict_integrity.py # Applies quarantine status to unverified records
│   │   │   ├── expire_jobs.py              # Marks inactive/unseen jobs as EXPIRED
│   │   │   ├── extract_verified_gold.py    # Extracts golden benchmark sets for regression testing
│   │   │   ├── import_existing_data.py     # Ingests legacy seed JSON dumps into MySQL models
│   │   │   ├── migrate_to_mysql.py         # Data migration script transferring legacy tables
│   │   │   ├── normalize_job_data.py       # Text cleaner for titles, departments, work modes
│   │   │   ├── process_subscription_renewals.py # Cron worker renewing active tenant subscriptions
│   │   │   ├── purge_fake_data.py          # Quarantines mock REQ-* jobs and synthetic opps
│   │   │   ├── rebuild_snapshots.py        # Flushes and rebuilds snapshot aggregation tables
│   │   │   ├── reconcile.py                # Reconciles live scraped data with database records
│   │   │   ├── rediscover_links.py         # Discovers careers and CSR landing URLs on homepages
│   │   │   ├── score_accuracy.py           # Precision scorecard evaluator against golden datasets
│   │   │   ├── seed_subscription_plans.py  # Populates starter, pro, enterprise billing tiers
│   │   │   ├── set_company_access.py       # Sets PUBLIC / NOT_PUBLISHED access flags on companies
│   │   │   ├── sync_company_live.py        # Live sync worker for individual company endpoints
│   │   │   ├── test_ai_providers.py        # Diagnostic CLI verifying Gemini/Grok API credentials
│   │   │   ├── verify_company_homepages.py # Cross-checks official domains against HTTP responses
│   │   │   ├── verify_csr_links.py         # Validates HTTP 200 availability of CSR project links
│   │   │   ├── verify_homepage_crosscheck.py # Multi-engine domain verification crosscheck
│   │   │   ├── verify_job_links.py         # HEAD/GET probe checking live HTTP status of job links
│   │   │   └── warm_cache.py               # Preloads Django cache with dashboard & public metrics
│   │   ├── migrations/                     # 25 Database schema migrations (0001 to 0025)
│   │   ├── models/                         # Relational data models
│   │   │   ├── ai_config.py                # AIProviderConfig, AISystemSettings, AIConfigurationAuditLog
│   │   │   ├── company.py                  # Company, CompanyCompletenessRegister, CompanySource
│   │   │   ├── contact.py                  # Contact model (corporate CSR/HR leaders)
│   │   │   ├── coverage.py                 # CompanyMetrics coverage scorecard
│   │   │   ├── crawler.py                  # CompanyCrawlSummary crawler run telemetry
│   │   │   ├── document.py                 # Document model (CSR policy PDFs, annual filings)
│   │   │   ├── evidence.py                 # AuditTrail model for field-level change history
│   │   │   ├── job.py                      # Job master model with 75+ fields and canonical hashing
│   │   │   ├── opportunity.py              # CSRProject, CSROpportunity, NGOMatch models
│   │   │   ├── prospect.py                 # Prospect CRM sales lead tracking model
│   │   │   ├── service.py                  # ServiceCatalog consulting service offerings
│   │   │   ├── snapshot.py                 # StatsSnapshot, JobSummarySnapshot, AuditRun caching models
│   │   │   ├── source_registry.py          # CompanySource evidence validation register
│   │   │   ├── subscription.py             # SubscriptionPlan, Subscription, Invoice, Wallet models
│   │   │   └── user.py                     # Custom User model extending AbstractBaseUser
│   │   ├── signals.py                      # Post-save signals for cache invalidation & snapshot triggers
│   │   ├── snapshot_service.py             # High-speed JSON builder reading/writing snapshot tables
│   │   ├── urls/                           # URL configurations for admin dashboard and entities
│   │   ├── verification.py                 # Public safety filter definitions & defect patterns
│   │   └── views/                          # Admin portal controllers and dashboard views
│   │
│   ├── crawler_engine/                     # Ingestion, parsing, and link discovery core
│   │   ├── access_detector.py              # Detects public vs. login-required careers gates
│   │   ├── ai_api_client.py                # LLM client implementing Gemini free-tier & Grok guard
│   │   ├── ai_classifier_config.py         # Strict zero-cost policy enforcement & model options
│   │   ├── candidate_collector.py          # Stage 1 link harvesting with HTML structural context
│   │   ├── completeness_service.py         # Evaluates company completeness across 5 dimensions
│   │   ├── crawler.py                      # Master web crawler engine with curl_cffi and Playwright
│   │   ├── discovery_helpers.py            # URL scoring, keyword weighting, and path analyzers
│   │   ├── homepage_verifier.py            # Validates company official homepage identity
│   │   ├── link_validator.py               # Pre-flight link checker rejecting bad schemas/fragments
│   │   ├── link_verifier.py                # Asynchronous HTTP status code verifier for scraped links
│   │   ├── live_syncer.py                  # Real-time background syncer for single-entity updates
│   │   ├── location_normalizer.py          # Indian city, state, tier-1/tier-2 geography normalizer
│   │   ├── normalizers.py                  # String cleaners for salaries, dates, job titles
│   │   ├── ownership.py                    # Resolves corporate subsidiaries and parent ownership
│   │   ├── page_classifier.py              # Stage 2 page classifier extracting ATS & CSR metadata
│   │   ├── parsers/                        # Specialized content and ATS parsers
│   │   │   ├── ats.py                      # Parsers for Taleo, Workday, SuccessFactors, Lever, etc.
│   │   │   ├── base.py                     # Base parser abstract interface
│   │   │   ├── corporate.py                # Generic corporate careers portal parser
│   │   │   ├── csr_pdf.py                  # PDFPlumber parser for Schedule VII CSR reports
│   │   │   ├── detail_extractor.py         # UniversalJobDetailExtractor for individual job pages
│   │   │   └── generic.py                  # Fallback DOM parser for custom corporate web pages
│   │   ├── semantic_matcher.py             # Semantic similarity calculator for deduplication
│   │   ├── state.py                        # In-memory crawler execution state tracker
│   │   ├── strategies/                     # Pluggable crawling strategies (XHR, JSON-LD, Sitemap)
│   │   ├── validators/                     # Redirect and HTTP response validators
│   │   └── verification_service.py         # Universal evidence validation gate
│   │
│   └── website/                            # Public web interface and client-facing REST APIs
│       ├── apps.py                         # WebsiteConfig application definition
│       ├── context_processors.py           # Context processors injecting company & system counts
│       ├── management/commands/            # Frontend asset management commands
│       │   └── minify_assets.py            # Minifies CSS and JS files for fast browser delivery
│       ├── middleware.py                   # Custom middleware for security headers & timing
│       ├── urls/                           # Client-facing URL route definitions
│       ├── utils/pagination.py             # Enterprise pagination helper with page_size capping
│       └── views/                          # Public controllers (job_api, company_api, home_views)
│
├── static/                                 # Public static assets
│   ├── css/                                # Master stylesheets (style.css, style.min.css)
│   ├── fonts/                              # Locally hosted typography (Inter font family)
│   └── js/app.js                           # Core frontend application script (AJAX, rendering)
│
├── templates/                              # Django HTML templates
│   ├── admin/                              # Admin dashboard, audit logs, entity detail views
│   ├── emails/                             # Transactional email templates (invoices, receipts)
│   └── website/index.html                  # Master single-page public web interface
│
├── tests/                                  # Django regression and unit test suite
│   ├── golden/                             # Verified benchmark golden datasets for accuracy checks
│   ├── test_ai_admin_configuration.py      # Tests for AI configuration forms and audit trails
│   ├── test_ai_architecture_requirements.py# Tests asserting zero-cost policy enforcement
│   ├── test_crawler_job_sync.py            # Tests for crawler persistence and idempotency
│   ├── test_phase1_integrity_and_quarantine.py # Regression tests for public safety filters
│   ├── test_stage1_discovery_helpers.py    # Unit tests for link discovery heuristics
│   └── test_step0_exact_match_standard.py  # Tests asserting verbatim field serialization
│
├── tests_pure/                             # Standalone non-Django fast unit tests
│   ├── test_crawl_review_sample.py         # Evaluates parser against offline HTML samples
│   ├── test_homepage_verifier.py           # Evaluates homepage verification algorithms
│   ├── test_pure_modules.py                # Pure python tests for normalizers & regex rules
│   └── test_stage1_candidate_collection.py # Tests candidate link scoring without network
│
├── scratch/                                # Internal benchmark, analysis, and diagnostic scripts
│   ├── accuracy_analysis.py                # Comprehensive field-level precision measurement
│   ├── all_urls.json                       # Authoritative dump of all registered URL patterns
│   ├── baseline_measurements.json          # Pre-optimization endpoint latency benchmarks
│   ├── after_measurements.json             # Post-optimization endpoint latency benchmarks
│   ├── db_distributions.json               # Frozen GROUP BY query distributions snapshot
│   ├── db_schema_and_counts.json           # Frozen schema column definitions and row counts
│   └── show_create_tables.json             # Exact SHOW CREATE TABLE DDL for all primary models
│
├── scripts/                                # Utility scripts for backfills and data audits
│   ├── backfill_csr_locations.py           # Backfills state and location metadata on CSR projects
│   ├── backfill_job_details.py             # Batch enrichment script fetching job descriptions
│   └── source_to_view_diagnostic.py        # Complete pipeline tracing tool for single jobs
│
├── manage.py                               # Django CLI entrypoint script
├── requirements.txt                        # Pinned python dependency specifications
├── run_server.bat                          # Windows batch script starting Waitress production server
└── README.md                               # Top-level operational overview
```

