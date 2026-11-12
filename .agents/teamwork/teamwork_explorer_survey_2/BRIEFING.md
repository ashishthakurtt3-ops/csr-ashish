# BRIEFING — 2026-11-09T16:55:00Z

## Mission
Survey R2 (Corporate Crawler Reliability and Timeout Mitigation) across `modules/crawler_engine/` and related services, investigating timeout causes, hanging connections, background worker stalling, anti-bot handling, SPA rendering, and statutory CSR / job extraction logic.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)
- State folder: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_explorer_survey_2
- Original parent: 4cfe8499-9ba8-461c-b776-46d4b062a5f3
- Milestone: survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Scope limited to R2 (Corporate Crawler Reliability and Timeout Mitigation) across `modules/crawler_engine/`
- All communications to parent via send_message
- Output handoff report in `d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_explorer_survey_2\handoff.md`

## Current Parent
- Conversation ID: 4cfe8499-9ba8-461c-b776-46d4b062a5f3
- Updated: 2026-11-09T16:55:00Z

## Investigation State
- **Explored paths**:
  - `modules/crawler_engine/crawler.py`
  - `modules/crawler_engine/access_detector.py`
  - `modules/crawler_engine/discovery_helpers.py`
  - `modules/crawler_engine/hybrid_ai_service.py`
  - `modules/crawler_engine/strategies/` (`pipeline.py`, `ats_strategy.py`, `click_capture_strategy.py`, `xhr_json_strategy.py`, `anchor_card_strategy.py`, `embedded_state_strategy.py`, `jsonld_strategy.py`, `sitemap_strategy.py`)
  - `modules/crawler_engine/adapters/` (`reliance.py`, `generic_jsonld.py`, `successfactors.py`, `taleo.py`, `workday.py`, `darwinbox.py`)
  - `modules/admin_panel/services/batch_discovery_service.py`
  - `modules/admin_panel/views/batch_discovery_views.py`
  - `templates/admin/ai_discovery/index.html`
- **Key findings**:
  1. Identified 10 root causes of timeouts (45s/120s), worker stalling, hanging connections, and false rejections.
  2. N+1 sequential live HTTP requests in `validate_job` (e.g. 100 requests for Amazon jobs) causing severe bottlenecks and WAF 403 blocks.
  3. Missing `is_ats_api` flags for fast APIs (Amazon, Phenom, Reliance, TCS).
  4. Excessive Chromium process launches per company.
  5. Synchronous execution of `process_single_company` within the Django web worker cycle.
  6. Domain-specific gaps for Microsoft, Google, IBM, Adobe, Infosys, and Wipro.
  7. Flawed regex in `JUNK_CSR_PATTERNS` rejecting "Environment & Sustainability Initiative".
- **Unexplored areas**: None within R2 scope; ready for synthesis and handoff.

## Key Decisions Made
- Structure comprehensive handoff report with exact line numbers, code quotes, architectural flow diagrams, and concrete fix specifications.

## Artifact Index
- `DISPATCH.md` — Inbound instructions record
- `BRIEFING.md` — Persistent working memory index
- `progress.md` — Liveness heartbeat and milestone tracker
- `handoff.md` — Final survey report
