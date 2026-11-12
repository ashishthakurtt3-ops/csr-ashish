# BRIEFING — 2026-11-09T17:11:00Z

## Mission
Stabilize Batch Discovery Ingestion & Pipeline in `modules/admin_panel/services/batch_discovery_service.py` (M3).

## 🔒 My Identity
- Archetype: implementer, qa
- Roles: implementer, qa
- Working directory: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)
- State folder: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_worker_m3
- Original parent: 4cfe8499-9ba8-461c-b776-46d4b062a5f3
- Milestone: M3 (Batch Discovery Ingestion & Pipeline Stabilization)

## 🔒 Key Constraints
- Write ownership strictly limited to: `modules/admin_panel/services/batch_discovery_service.py`
- DO NOT CHEAT: genuine implementation, real state and logic, no hardcoded results
- Must enforce global timeout budget <= 28s wall clock
- Graceful truncation when remaining < 4.0s
- Support legacy XLS detection / clean error, UTF-16 CSV, delimiter sniffing
- Eliminate N+1 verification for ATS APIs and cap scraped job verification to 5 URLs
- Parallelize path probing with ThreadPoolExecutor
- Bounded browser execution (6000ms navigation, 8000ms total, guaranteed close)
- Non-destructive DB updates: only delete existing records if validated count > 0

## Current Parent
- Conversation ID: 4cfe8499-9ba8-461c-b776-46d4b062a5f3
- Updated: 2026-11-09T17:11:00Z

## Task Summary
- **What to build**: 6 key stabilization fixes to `modules/admin_panel/services/batch_discovery_service.py`
- **Success criteria**: Robust file parsing, bounded execution <= 28s, parallelized probing, ATS fast-path, bounded browser, non-destructive DB updates, passing syntax and unit tests.
- **Interface contracts**: PROJECT.md
- **Code layout**: `modules/admin_panel/services/batch_discovery_service.py`

## Key Decisions Made
- [TBD]

## Artifact Index
- `.agents/teamwork/teamwork_worker_m3/DISPATCH.md` — Dispatch requirements
- `.agents/teamwork/teamwork_worker_m3/progress.md` — Progress tracker and heartbeat
- `modules/admin_panel/services/batch_discovery_service.py` — Target code file

## Change Tracker
- **Files modified**: None yet
- **Build status**: Untested
- **Pending issues**: None

## Quality Status
- **Build/test result**: Not run yet
- **Lint status**: Clean
- **Tests added/modified**: TBD
