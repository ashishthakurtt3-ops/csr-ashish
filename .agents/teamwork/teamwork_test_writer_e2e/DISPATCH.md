## 2026-11-09T17:09:20Z
You are a comprehensive test writer subagent (E2E Testing Track).
Working directory: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)
State folder: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_test_writer_e2e
Original request path: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\ORIGINAL_REQUEST.md
Scope document: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\PROJECT.md

MANDATORY: Read the original user request at d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\ORIGINAL_REQUEST.md and PROJECT.md before starting work.

Write ownership:
You own EXCLUSIVELY:
- d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\TEST_INFRA.md
- d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\TEST_READY.md
- d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\tests\test_batch_discovery_pipeline.py
- d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\tests\test_ai_discovery_e2e.py

Objectives:
1. Create `TEST_INFRA.md` at project root using the 4-tier methodology (Category-Partition, Boundary Value Analysis, Pairwise, Real-World Workloads) covering all 17 features in `PROJECT.md § Feature Inventory`.
2. Implement comprehensive, robust, independent unit and integration tests:
   - `tests/test_batch_discovery_pipeline.py`:
     - Tier 1: CSV parsing with standard headers, TSV parsing, XLSX parsing.
     - Tier 2: Semicolon delimiters, pipe delimiters, UTF-8 BOM, UTF-16 LE/BE encodings, BIFF8 .xls detection and graceful error handling, empty files, missing column headers, stream rewind. Non-destructive job retention when 0 candidates validated.
     - Tier 3: Cross-format combinations, dirty whitespace, mixed case headers, missing URLs.
   - `tests/test_ai_discovery_e2e.py`:
     - Tier 1: API JSON responses for unauthenticated requests (HTTP 401 JSON with status, error, message, login_url), non-admin role requests (HTTP 403 JSON), malformed JSON body (HTTP 400 JSON).
     - Tier 2: Valid JSON responses under all server exceptions, eliminating any HTML 500 or 302 redirects on API endpoints.
     - Tier 3: Session expiration mid-discovery simulation, verifying JSON response contract.
     - Tier 4: Synthetic corporate batch ingestion (Microsoft, Google, Amazon, Tata Motors, IBM, Adobe, Infosys, Wipro), timeout budget adherence (<=30s), ATS host matching (`turbohire.co`, `brassring.com`), and statutory CSR Schedule VII theme acceptance.
3. Verify tests can be executed with `.venv\Scripts\python -m unittest tests/test_batch_discovery_pipeline.py tests/test_ai_discovery_e2e.py` or `python manage.py test`. Note that tests testing currently-broken features will serve as our E2E acceptance gate.
4. Publish `TEST_READY.md` at project root with the test runner command and tier counts.
5. Provide a complete handoff report at `d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_test_writer_e2e\handoff.md` and notify parent via send_message.
