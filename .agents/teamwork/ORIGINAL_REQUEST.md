# Original User Request

## Initial Request — 2026-11-09T16:40:43Z

Resolve errors and stabilize the AI Bulk Discovery engine in Django Admin (`/admin-portal/ai-discovery/`) so corporate file uploads, background tasks, and crawls extract active jobs and statutory CSR initiatives reliably without unhandled errors or timeouts.

Integrity mode: development

## Requirements

### R1. Non-JSON and Session Expiry Error Handling
Prevent frontend crashes caused by non-JSON or HTML responses (such as `Unexpected token '<', "<!DOCTYPE "... is not valid JSON` resulting from session expiry, auth redirects, or unhandled 500 errors). Ensure API endpoints return structured JSON responses under error conditions and the frontend UI gracefully handles and displays failures.

### R2. Corporate Crawler Reliability and Timeout Mitigation
Eliminate crawler timeouts (e.g., 45-second limits) and extraction failures when discovering jobs and statutory CSR initiatives from corporate domains (e.g., Microsoft, Google, Amazon, IBM, Adobe, Infosys, Wipro). Ensure crawls extract active jobs and statutory CSR initiatives reliably without hanging or stalling background workers.

### R3. Batch Discovery Pipeline and Background Task Stabilization
Investigate and resolve root causes across `modules/admin_panel/services/batch_discovery_service.py`, `modules/crawler_engine/`, `templates/admin/ai_discovery/index.html`, and background task execution to ensure end-to-end bulk discovery processes execute reliably.

## Acceptance Criteria

### Error Resilience & Response Parsing
- [ ] All API endpoints serving `/admin-portal/ai-discovery/` return valid JSON with appropriate status codes for all failure modes (including unauthenticated sessions and server exceptions), eliminating `<!DOCTYPE` JSON parse syntax errors in the client.
- [ ] The bulk discovery UI displays clear, actionable error notifications when network requests, session timeouts, or background jobs fail.

### Crawl Execution & Extraction
- [ ] Crawls on corporate domains finish within configured timeout limits without blocking background workers.
- [ ] Extraction logic successfully extracts active jobs and CSR data where available without silent crashes or hallucinations.

### Verification
- [ ] Synthetic bulk CSV/Excel files and automated test cases run successfully, demonstrating error-free batch ingestion, API response handling, and crawl completion.
