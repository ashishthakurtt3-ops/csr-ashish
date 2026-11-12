## 2026-11-09T17:10:22Z
You are a Worker subagent implementing Milestone 3 (M3): Batch Discovery Ingestion & Pipeline Stabilization.
Working directory: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)
State folder: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_worker_m3
Original request path: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\ORIGINAL_REQUEST.md
Scope document: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\PROJECT.md
Explorer handoff report: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_explorer_survey_3\handoff.md
Survey 2 report: d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_explorer_survey_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

MANDATORY: Read the original user request at d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\ORIGINAL_REQUEST.md, PROJECT.md, and the explorer handoff reports before starting work.

Write ownership:
You own EXCLUSIVELY:
- d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\modules\admin_panel\services\batch_discovery_service.py

Detailed Scope & Tasks:
1. File Parsing Stabilization in `parse_uploaded_file`:
   - Call `file_obj.seek(0)` before reading.
   - For `.xlsx`/`.xls`: Check for `.xls` extension or BIFF8 magic bytes (`\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1`). If `xlrd` is installed, use `xlrd.open_workbook`. Otherwise, raise a clean `ValueError("Legacy .xls format detected. Please save your spreadsheet as .xlsx or .csv.")` instead of letting `openpyxl` throw unhandled `InvalidFileException`.
   - For CSV: Prepend `'utf-16'`, `'utf-16-le'`, `'utf-16-be'` to candidate encodings before `'latin-1'`.
   - Delimiter detection: Use `csv.Sniffer().sniff(text[:4096])` to determine delimiter (`,`, `;`, `\t`, `|`), falling back safely if sniffer fails.
2. Global Timeout Budget & Bounded Execution in `process_single_company`:
   - Enforce a strict 28.0-second wall-clock deadline: `deadline = time.time() + 28.0`.
   - Before deep crawls and candidate validation, check `remaining = deadline - time.time()`. If `remaining < 4.0`, gracefully truncate remaining deep crawls and proceed to persist already-extracted assets, guaranteeing the API response finishes well under 30s.
3. Eliminate N+1 Bottleneck & Fast ATS Verification in `validate_job`:
   - Add `'amazon.jobs'`, `'careers.ril.com'`, `'careers.hcltech.com'`, `'careers.adobe.com'` to `is_ats_api`.
   - In `discover_all_real_jobs` Tiers (Reliance, Amazon, JPMC, HCLTech, Phenom), set `candidate['ats_platform']` and `candidate['extraction_method'] = 'ats_api'`.
   - When `is_ats_api=True`, bypass sequential live HTTP GET requests entirely. Validate title, requisition ID, and URL format in-memory.
   - For scraped jobs, cap live HTTP verification to a maximum of 5 sampled URLs per company with a 3.0s timeout.
4. Parallel Path Probing:
   - In lines 1682-1690 and 1728-1736, probe `/careers` and `/sustainability` paths concurrently with a `ThreadPoolExecutor` and 2.5s timeout.
5. Bounded Browser Execution in `fetch_rendered_page`:
   - Set navigation timeout to 6000ms and total timeout to 8000ms. Disallow infinite waits. Ensure `await browser.close()` in `finally:`.
6. Non-Destructive DB Updates:
   - In lines 1766 & 1844, do NOT call `company.jobs.all().delete()` or `company.csr_projects.all().delete()` before validation. Collect `validated_jobs` and `validated_csr`. Only delete and replace existing records if `len(validated_jobs) > 0` (or `len(validated_csr) > 0`), preserving existing records if zero candidates pass validation.
7. Verification & Tests:
   - Run python syntax check and unittests on your changes.
   - Verify parsing with semicolon CSV, UTF-16 CSV, and `.xls` error handling.
   - Verify `process_single_company` returns within budget.
8. Write your handoff report to `d:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)\.agents\teamwork\teamwork_worker_m3\handoff.md` and notify parent via send_message.
