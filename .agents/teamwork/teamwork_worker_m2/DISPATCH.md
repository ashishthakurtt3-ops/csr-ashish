## 2026-11-09T17:09:59Z
You are a Worker subagent implementing Milestone 2 (M2): Crawler Engine Reliability & Corporate Timeout Mitigation.
Working directory: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)
State folder: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_worker_m2
Original request path: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\ORIGINAL_REQUEST.md
Scope document: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\PROJECT.md
Explorer handoff report: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_explorer_survey_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY: Read the original user request at d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\ORIGINAL_REQUEST.md, PROJECT.md, and the explorer handoff report before starting work.

Write ownership:
You own EXCLUSIVELY:
- d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\modules\crawler_engine\discovery_helpers.py
- d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\modules\crawler_engine\strategies\click_capture_strategy.py
- d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\modules\crawler_engine\strategies\ats_strategy.py
- d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\modules\crawler_engine\crawler.py

Detailed Scope & Tasks:
1. `modules/crawler_engine/discovery_helpers.py`:
   - Expand `ALLOWED_ATS_HOSTS`: add `'turbohire.co'`, `'brassring.com'`, `'eightfold.ai'`, `'jobvite.com'`, `'breezy.hr'`, `'keka.com'`, `'avature.net'`, `'cornerstoneondemand.com'`, `'sap.com'` (lines 401-418).
   - In `JUNK_CSR_PATTERNS` (line 213): Remove `'environment & sustainability initiative'` and legitimate statutory themes from the junk pattern. Ensure legitimate Schedule VII projects are not flagged as junk.
   - In `is_allowed_domain_or_ats`: Recognize associated corporate foundation domains (e.g. `bhartifoundation.org`, `infosys.org`, `wiprofoundation.org`, `icicifoundation.org`, `tatatrusts.org`, `tatapowersocial.org`) as allowed domains for CSR matching.
2. `modules/crawler_engine/strategies/click_capture_strategy.py`:
   - Bounded navigation: Reduce `max_clicks` default from 40 to 8.
   - Add an overarching strategy execution deadline (e.g. max 12.0s wall clock) to break out of the card loop if cumulative time exceeds the deadline.
3. `modules/crawler_engine/strategies/ats_strategy.py`:
   - Enhance `ATS_SIGNATURES` to detect and match enterprise corporate domains:
     - Wipro (`careers.wipro.com`) -> Phenom / SuccessFactors
     - Adobe (`careers.adobe.com`) -> Phenom
     - IBM (`ibm.com/careers`, `jobs.brassring.com`) -> BrassRing
4. `modules/crawler_engine/crawler.py`:
   - In `_extract_csr_projects_rule_based` and project validation, ensure `f"{matched_theme} Initiative"` is accepted as a valid statutory CSR project.
5. Verification:
   - Run unit tests: `python -m unittest modules/crawler_engine/tests_link_intelligence.py`
   - Test `is_allowed_domain_or_ats` for `tatamotors.turbohire.co` and `bhartifoundation.org`.
   - Test `is_valid_csr_project` for "Environment & Sustainability Initiative".
6. Write your handoff report to `d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_worker_m2\handoff.md` and notify parent via send_message.
