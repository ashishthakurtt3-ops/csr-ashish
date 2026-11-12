# BRIEFING — 2026-11-09T17:15:00Z

## Mission
Implement Milestone 1 (M1): Non-JSON & Session Expiry API Resilience for AI Bulk Discovery Engine.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)
- State folder: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_worker_m1
- Original parent: 4cfe8499-9ba8-461c-b776-46d4b062a5f3
- Milestone: M1 - Non-JSON & Session Expiry API Resilience

## 🔒 Key Constraints
- Write ownership restricted exclusively to:
  - `modules/admin_panel/middleware.py`
  - `modules/admin_panel/views/batch_discovery_views.py`
  - `templates/admin/ai_discovery/index.html`
- Do not touch files owned by M2, M3, or E2E.
- DO NOT CHEAT: No hardcoded test results, facade logic, or fabricated tests.
- All API endpoints serving `/admin-portal/ai-discovery/` must return valid JSON with appropriate status codes (401, 403, 400, 500).
- Frontend UI must handle session expiry and error responses cleanly without JSON parse crashes or failing the entire queue.

## Current Parent
- Conversation ID: 4cfe8499-9ba8-461c-b776-46d4b062a5f3
- Updated: 2026-11-09T17:15:00Z

## Task Summary
- **What to build**:
  1. Middleware API detection: Return 401 JSON on unauthenticated AI discovery API requests, 403 JSON on unauthorized requests.
  2. Safe request payload parsing & UnboundLocalError fix in `process_company_api`: initialize `company_task` & `options`, catch JSON/Unicode decode errors (HTTP 400), add JSON error/csrf helpers if applicable.
  3. Frontend `safeParseJsonResponse` and `processNextCompany` updates: detect session expiry (`resp.redirected`, 401/403, login HTML), pause queue, display emergency alert & Toast, allow re-auth and resume.
- **Success criteria**:
  - Unauthenticated requests to discovery APIs return HTTP 401 JSON.
  - Unauthorized requests return HTTP 403 JSON.
  - Malformed payloads return HTTP 400 JSON without server 500 / UnboundLocalError.
  - Frontend parses JSON reliably without `<!DOCTYPE` syntax errors and pauses queue on session expiry.
  - All existing tests pass + verification scripts succeed.
- **Interface contracts**: `PROJECT.md` § Interface Contracts
- **Code layout**: `PROJECT.md` § Code Layout & Write Boundaries

## Key Decisions Made
- Follow Survey 1 recommendations accurately.

## Artifact Index
- `.agents/teamwork/teamwork_worker_m1/DISPATCH.md` — Initial dispatch assignment
- `.agents/teamwork/teamwork_worker_m1/BRIEFING.md` — Agent briefing & state
- `.agents/teamwork/teamwork_worker_m1/progress.md` — Execution progress & heartbeat
- `.agents/teamwork/teamwork_worker_m1/handoff.md` — Final handoff report

## Change Tracker
- **Files modified**: None yet
- **Build status**: Not run yet
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending
- **Lint status**: Pending
- **Tests added/modified**: Pending
