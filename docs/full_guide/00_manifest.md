# 00. Complete Project Documentation Manifest

**Frozen Timestamp:** `2026-10-29 12:12:48 +05:30`  
**Git Commit Hash:** `0a538883c17b40774c119deb78b9aaff72220606`

---

## 1. Environment & Runtime Specifications

| Component | Verified Version | Configuration / Location |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Enterprise (x64) | Host Environment |
| **Python Runtime** | `3.11.9` | `D:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.venv\Scripts\python.exe` |
| **Django Framework** | `5.2.17` | `django.get_version()` |
| **Database Server** | MySQL Community Server `8.0.42` | `localhost:3306` via TCP/IP |
| **Database Name** | `csr_intelligence_django` | 42 Relational InnoDB Tables |
| **WSGI Server** | Waitress `3.0.2` | Threads: 8, Port: 8000 (Stopped for frozen read-only snapshot) |

---

## 2. Git Status & Modified Working Tree

- **Current Branch**: `main`
- **Upstream Tracking**: Up to date with `origin/main`
- **Working Tree State**: Uncommitted modifications from recent cleanup and asset optimization passes.

### Modified Files (40 Files)
```
M  .gitignore
M  config/settings.py
M  config/urls.py
M  config/wsgi.py
M  modules/admin_panel/apps.py
M  modules/admin_panel/management/commands/crawl_all_companies.py
M  modules/admin_panel/management/commands/verify_company_homepages.py
M  modules/admin_panel/models/__init__.py
M  modules/admin_panel/models/company.py
M  modules/admin_panel/models/job.py
M  modules/admin_panel/models/opportunity.py
M  modules/admin_panel/urls/__init__.py
M  modules/admin_panel/verification.py
M  modules/admin_panel/views/dashboard.py
M  modules/crawler_engine/__init__.py
M  modules/crawler_engine/crawler.py
M  modules/crawler_engine/parsers/detail_extractor.py
M  modules/website/context_processors.py
M  modules/website/tests_job_detail_integrity.py
M  modules/website/urls/company_urls.py
M  modules/website/urls/crawler_urls.py
M  modules/website/urls/job_urls.py
M  modules/website/urls/opportunity_urls.py
M  modules/website/utils/pagination.py
M  modules/website/views/company_api_views.py
M  modules/website/views/crawler_api_views.py
M  modules/website/views/home_views.py
M  modules/website/views/job_api_views.py
M  modules/website/views/matching_api_views.py
M  modules/website/views/opportunity_api_views.py
M  requirements.txt
M  run_server.bat
M  scratch/measure_baseline.py
M  scripts/hero_job_detail.html
M  static/css/style.css
M  static/js/app.js
M  templates/admin/auth/login.html
M  templates/admin/base_admin.html
M  templates/admin/dashboard.html
M  templates/website/index.html
```

---

## 3. Full Guide Document Inventory & File Sizes

All documents are authored in the standard **PLAIN / TECHNICAL / EVIDENCE** format and split to stay under ~25,000 characters for ease of copying and analysis.

| Document Filename | Primary Subject Area | Byte Size | Character Count |
| :--- | :--- | :--- | :--- |
| [`00_manifest.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/00_manifest.md) | Documentation Index, Git Status, Environment Versions | ~5,500 B | ~5,200 chars |
| [`01a_big_picture_architecture.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/01a_big_picture_architecture.md) | Executive Summary, Mermaid Flowchart, Tech Stack, Zero-Run Setup | 14,391 B | 14,391 chars |
| [`01b_project_structure_inventory.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/01b_project_structure_inventory.md) | Complete Annotated Folder Tree & Purpose of Every File | 16,570 B | 15,096 chars |
| [`02a_data_model_core.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/02a_data_model_core.md) | ER Diagram, Company, Job Model (75+ fields), Metrics & Snapshots | 18,476 B | 18,476 chars |
| [`02b_data_model_csr_billing.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/02b_data_model_csr_billing.md) | CSR Projects, Quarantined Opps, Subscriptions, AI Models, DDL, Drift | 14,567 B | 14,559 chars |
| [`03a_crawler_pipeline_architecture.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/03a_crawler_pipeline_architecture.md) | Commands & Scripts, Stages, Signatures, Call Graph, Execution Trace | 13,699 B | 13,435 chars |
| [`03b_crawler_link_discovery_ats.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/03b_crawler_link_discovery_ats.md) | Link Discovery Heuristics, 14 ATS Adapters, Network Layer (WAF/Anti-Bot) | 10,589 B | 10,585 chars |
| [`03c_crawler_rules_ai_idempotency.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/03c_crawler_rules_ai_idempotency.md) | Rejection Rules, Defect Regex, AI Prompts & Zero-Cost Guard, Idempotency | 9,646 B | 9,644 chars |
| [`04_backend_api.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/04_backend_api.md) | Route Inventory, Dual-Mode API Contract, Querysets, EXPLAIN Plan, N+1 | 11,595 B | 11,593 chars |
| [`05_frontend_ui_ux.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/05_frontend_ui_ux.md) | Master Templates, JS State Machine, cachedFetch, UX Flows, URL Cleansers | 8,705 B | 8,703 chars |
| [`06_data_visibility.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/06_data_visibility.md) | DB-to-Screen Funnel (5,549 -> 1,492), 7 Hiding Layers, Authentic Samples | 9,537 B | 9,477 chars |
| [`07_config_ops_history.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/07_config_ops_history.md) | Settings, Tests, Code Quality (0 TODOs), Phases 0-4 Evolution, Security | 11,693 B | 11,587 chars |
| [`08_glossary_faq.md`](file:///d:/D%20DOWNLOADS/CSR_Job_Intelligence_Production_Ready%20%281%29/docs/full_guide/08_glossary_faq.md) | Project-Specific Terminology, Plain/Tech Definitions, 10 Operator FAQs | 10,557 B | 10,557 chars |

---

## 4. Key Verification Metrics at Frozen Snapshot

```
- Corporate Entities in Master Register:    201 (200 Top Listed + 1 Legacy Seed)
- Verified Public Jobs Visible on UI:      1,492 (Out of 5,549 total stored in MySQL)
- Defective / Boilerplate Jobs Quarantined: 949 (Marked with is_defective=1)
- Statutory CSR Projects Active on UI:      1,591 (Categorized across Schedule VII)
- Synthetic CSR Opportunities Quarantined:  1,160 (100% hidden by public_records filter)
- Warm Cache Public Endpoint Latency:       2.37 ms (/api/stats/)
- Unit Tests Passing (Pure Python):        67 / 67 (0 failures, 0.640s execution)
```

