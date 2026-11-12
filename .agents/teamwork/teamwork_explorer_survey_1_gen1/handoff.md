# Technical Survey Report: R1 Non-JSON and Session Expiry Error Handling

## 1. Observation

Direct code observations from the project codebase:

### Observation 1.1: Middleware 302 Login Redirect on Unauthenticated API Calls
- **File**: `modules/admin_panel/middleware.py`
- **Lines 18–27**:
  ```python
  def __call__(self, request):
      path = request.path

      if path.startswith('/admin-portal/') and not (
          path == '/admin-portal/login/' or 
          path == '/admin-portal/logout/' or
          path.startswith('/admin-portal/auth/')
      ):
          if not request.user.is_authenticated:
              return redirect(f"/admin-portal/login/?next={path}")
  ```
- **Finding**: Any request targeting `/admin-portal/ai-discovery/parse-file/` or `/admin-portal/ai-discovery/process-company/` with an expired session or unauthenticated user is intercepted by `AdminRoleMiddleware`. The middleware executes `return redirect(f"/admin-portal/login/?next={path}")`, sending an `HTTP 302 Found` response.
- **Client Impact**: Standard browser `fetch()` automatically follows HTTP 302 redirects by default. The redirected request fetches `GET /admin-portal/login/?next=...`, which returns `HTTP 200 OK` with `Content-Type: text/html; charset=utf-8` containing full HTML (`<!DOCTYPE html>`).

### Observation 1.2: UnboundLocalError Crash in `process_company_api`
- **File**: `modules/admin_panel/views/batch_discovery_views.py`
- **Lines 84–112**:
  ```python
  @require_http_methods(['POST'])
  def process_company_api(request):
      """Processes a single company task from the client queue: crawls website, invokes AI, auto-imports to DB."""
      if not request.user.is_authenticated or not _is_admin(request.user):
          return JsonResponse({'status': 'error', 'message': 'Authentication required. Please sign in as admin.'}, status=401)

      try:
          data = json.loads(request.body.decode('utf-8'))
          company_task = data.get('company')
          options = data.get('options', {})

          if not company_task or not company_task.get('company_name'):
              return JsonResponse({'status': 'error', 'message': 'Invalid company payload.'}, status=400)

          result = BatchDiscoveryService.process_single_company(company_task, options)
          return JsonResponse(result)
      except Exception as e:
          logger.exception("Company processing failed")
          return JsonResponse({
              'status': 'error',
              'company_name': (company_task.get('company_name') if company_task else 'Unknown'),
              'message': str(e),
              'jobs_discovered': 0,
              'jobs_imported': 0,
              'csr_discovered': 0,
              'csr_imported': 0,
              'logs': [f"[ERROR] Discovery halted: {str(e)}"]
          }, status=200) # Return 200 so the client queue doesn't halt!
  ```
- **Finding**: Inside `process_company_api`, `company_task` is assigned on line 92 (`company_task = data.get('company')`). If `request.body.decode('utf-8')` or `json.loads` throws an exception (e.g., malformed body, invalid unicode, empty body), execution jumps immediately to `except Exception as e:`. On line 104, `company_task.get('company_name') if company_task else 'Unknown'` evaluates `company_task`. Because `company_task` is a local variable that was never bound prior to the exception, Python raises:
  `UnboundLocalError: local variable 'company_task' referenced before assignment`
- **Finding**: Because `UnboundLocalError` is not caught within the function, it propagates out to Django's exception handler. Django returns an HTML 500 Server Error page (`<!DOCTYPE html>...`).

### Observation 1.3: Insufficient Role Denial for Multipart Uploads in `AdminRoleMiddleware`
- **File**: `modules/admin_panel/middleware.py`
- **Lines 30–41**:
  ```python
  # Check user role if accessing sensitive areas
  if hasattr(request.user, 'is_admin_or_staff') and not request.user.is_admin_or_staff():
      if (
          request.content_type == 'application/json' or
          request.headers.get('x-requested-with') == 'XMLHttpRequest' or
          '/save/' in path or
          '/test/' in path or
          path.endswith('/audit-logs/')
      ):
          from django.http import JsonResponse
          return JsonResponse({'success': False, 'error': 'Access denied: Administrative privileges required.'}, status=403)
      return redirect('/')
  ```
- **Finding**: When an authenticated user lacking admin privileges uploads a manifest via `parse_file_api`, `request.content_type` is `multipart/form-data`, not `application/json`. Because browser `fetch()` does not automatically attach `X-Requested-With`, the condition evaluates to False and the middleware executes `return redirect('/')` (`HTTP 302` redirecting to homepage HTML). Furthermore, if the condition did match, the response payload schema is `{'success': False, 'error': ...}`, which conflicts with the expected API contract `{'status': 'error', 'message': ...}`.

### Observation 1.4: Lack of JSON-Aware Custom Exception Handlers in Django Configuration
- **File**: `config/urls.py` and `config/settings.py`
- **Lines**: `config/urls.py:9-39`, `config/settings.py:65-77`
- **Finding**: No custom `handler500`, `handler403`, or `handler400` are registered in `config/urls.py`. When an unhandled server error occurs (such as database disconnect, memory exhaustion, or view bug), Django renders `500.html` with `Content-Type: text/html`.
- **Finding**: `django.middleware.csrf.CsrfViewMiddleware` is active in `config/settings.py` line 71. If a CSRF token is expired, missing, or mismatched, Django's default `csrf_failure` view returns an HTML 403 page (`<!DOCTYPE html><h1>403 Forbidden</h1>...`).

### Observation 1.5: Frontend JSON Parsing and Session Failure Cascade in `index.html`
- **File**: `templates/admin/ai_discovery/index.html`
- **Lines 1648–1673 (`safeParseJsonResponse`)**:
  ```javascript
  async function safeParseJsonResponse(resp) {
      if (!resp) throw new Error("Empty response object received");
      if (resp.status === 403 || resp.status === 401) {
          throw new Error("Admin session expired or access denied (HTTP 403). Please log into Admin Console.");
      }
      const text = await resp.text();
      if (!text || !text.trim()) {
          throw new Error(`Server returned empty response (HTTP ${resp.status})`);
      }
      const trimmed = text.trim();
      if (trimmed.startsWith('<') || trimmed.toLowerCase().startsWith('<!doctype')) {
          let titleMatch = trimmed.match(/<title[^>]*>([^<]+)<\/title>/i);
          let extractedMsg = titleMatch ? titleMatch[1].trim() : `Server returned HTML error page (HTTP ${resp.status})`;
          throw new Error(extractedMsg);
      }
      try {
          const parsed = JSON.parse(text);
          if (!resp.ok && parsed.message) {
              throw new Error(parsed.message);
          }
          return parsed;
      } catch (e) {
          if (e.message && !e.message.includes('JSON')) throw e;
          throw new Error(`Invalid JSON received from server (HTTP ${resp.status}): ${e.message}`);
      }
  }
  ```
- **Finding**:
  1. `safeParseJsonResponse` does not inspect `resp.redirected`. When `AdminRoleMiddleware` redirects to login, `fetch` follows the redirect and `resp.status` is `200 OK` (not 401 or 403).
  2. The parser detects `trimmed.startsWith('<')`, extracts `<title>Log in | ImpactBridge Admin</title>`, and throws `new Error("Log in | ImpactBridge Admin")`.
  3. If unhandled HTML arrives without `<title>`, or in older code paths calling `resp.json()`, the browser triggers: `SyntaxError: Unexpected token '<', "<!DOCTYPE "... is not valid JSON`.
- **Lines 1927–1935 (`handleFileSelected`)**:
  ```javascript
  } catch (err) {
      if (loadingState) loadingState.style.display = 'none';
      if (dropZone) dropZone.style.display = 'block';
      logTerminal(`[NETWORK_ERROR] Failed to parse manifest: ${err.message}`, '#EF4444');
      showInAppNotification({ title: 'Network Error', message: 'Unable to communicate with server to parse manifest.', type: 'error' });
  ```
  Masks all server/session errors with a misleading "Network Error: Unable to communicate with server" toast.
- **Lines 2869–2980 (`processNextCompany`)**:
  When `safeParseJsonResponse` throws `"Log in | ImpactBridge Admin"`, `catch (err)` records it in `failedCompaniesList`. Crucially, it does **not** abort the queue: it increments `currentQueueIndex` and invokes `processNextCompany` 2.5 seconds later. If a user runs a 50-company batch, all 50 companies sequentially fail with `"Log in | ImpactBridge Admin"` instead of immediately pausing and alerting the administrator to re-authenticate.

---

## 2. Logic Chain

1. **Premise 1 (Middleware Interception)**: Based on `modules/admin_panel/middleware.py:26`, any request to `/admin-portal/ai-discovery/*` without an authenticated session receives an HTTP 302 redirect to `/admin-portal/login/?next=...`.
2. **Premise 2 (Fetch Auto-Follow)**: Standard browser `fetch()` automatically follows HTTP 302 redirects unless configured otherwise. The redirected GET request resolves to `/admin-portal/login/`, yielding HTTP 200 with HTML content (`<!DOCTYPE html>`).
3. **Premise 3 (Direct Parsing Syntax Failure)**: Calling `response.json()` on an HTML response string causes the V8 JavaScript engine to throw `SyntaxError: Unexpected token '<', "<!DOCTYPE "... is not valid JSON`.
4. **Premise 4 (Heuristic Parser Masking)**: While `safeParseJsonResponse` in `index.html:1658` extracts the `<title>` tag from the HTML string, it does not detect `resp.redirected` or HTTP 302 login redirects. It throws a generic Error with the page title (`"Log in | ImpactBridge Admin"`).
5. **Premise 5 (Queue Failure Cascading)**: Because `processNextCompany` (`index.html:2869`) does not recognize auth/session errors, it treats session expiry as an individual company crawl error. It advances the pointer and repeats the failing request for every company in the queue.
6. **Premise 6 (Server 500 HTML Leakage)**: Because no JSON exception middleware or custom JSON 500 handler exists (`config/urls.py`, `settings.py`), any unhandled exception (such as `UnboundLocalError` on `batch_discovery_views.py:104` or database disconnect) causes Django to render its HTML 500 page.
7. **Conclusion**: Resolving R1 requires a coordinated two-tier fix:
   - **Backend**: Update `AdminRoleMiddleware` and API views to strictly return structured JSON (`application/json`) with appropriate HTTP status codes (401, 403, 400, 500) for all `/admin-portal/ai-discovery/` requests, eliminating HTML redirects and HTML error pages.
   - **Frontend**: Upgrade `safeParseJsonResponse` to check `resp.redirected` and status codes, and upgrade `processNextCompany` to immediately pause the batch queue and present an actionable re-authentication prompt.

---

## 3. Caveats

1. **Session Expiry vs CSRF Expiry**: In Django with `SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'`, session expiration also invalidates the CSRF token. Handling must account for both 401 unauthenticated and 403 CSRF failure scenarios.
2. **Reverse Proxy / Nginx / Gateway Timeouts**: In production deployment behind Nginx or Cloudflare, a 502/504 gateway timeout might generate an HTML error page external to Django. Frontend handling must therefore retain robust HTML detection as a defensive safeguard.
3. **Download Sample Template Route**: The endpoint `/admin-portal/ai-discovery/sample-template/` intentionally returns file attachments (`text/csv` or `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`). It is accessed via direct `<a>` link navigation rather than AJAX JSON fetch, so it should retain standard redirect behavior for unauthenticated browser sessions.

---

## 4. Conclusion

The root cause of `Unexpected token '<', "<!DOCTYPE "... is not valid JSON` and associated frontend crashes during AI Bulk Discovery is a mismatch between Django's default browser-oriented redirect/error flow and the Single-Page Application (SPA) fetch architecture in `index.html`.

### Concrete Fix Strategy & Proposed Changes:

#### Target A: `modules/admin_panel/middleware.py`
Add explicit API detection in `AdminRoleMiddleware`:
```python
# Check if this is an API or AJAX request
is_api_request = (
    path.startswith('/admin-portal/ai-discovery/') and path != '/admin-portal/ai-discovery/'
    or request.content_type == 'application/json'
    or request.headers.get('Accept') == 'application/json'
    or request.headers.get('x-requested-with') == 'XMLHttpRequest'
)

if not request.user.is_authenticated:
    if is_api_request:
        return JsonResponse({
            'status': 'error',
            'error': 'SESSION_EXPIRED',
            'message': 'Your administrator session has expired. Please sign in again.',
            'login_url': f"/admin-portal/login/?next={path}"
        }, status=401)
    return redirect(f"/admin-portal/login/?next={path}")

# Role check for non-admin/staff:
if hasattr(request.user, 'is_admin_or_staff') and not request.user.is_admin_or_staff():
    if is_api_request:
        return JsonResponse({
            'status': 'error',
            'error': 'FORBIDDEN',
            'message': 'Access denied: Administrative privileges required.'
        }, status=403)
    return redirect('/')
```

#### Target B: `modules/admin_panel/views/batch_discovery_views.py`
1. Fix `process_company_api` to prevent `UnboundLocalError`:
```python
@require_http_methods(['POST'])
def process_company_api(request):
    """Processes a single company task from the client queue: crawls website, invokes AI, auto-imports to DB."""
    if not request.user.is_authenticated or not _is_admin(request.user):
        return JsonResponse({
            'status': 'error',
            'error': 'SESSION_EXPIRED',
            'message': 'Authentication required. Please sign in as admin.'
        }, status=401)

    company_task = None
    options = {}
    try:
        try:
            data = json.loads(request.body.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError) as parse_err:
            return JsonResponse({'status': 'error', 'message': f'Malformed JSON request body: {str(parse_err)}'}, status=400)

        company_task = data.get('company')
        options = data.get('options', {})

        if not company_task or not company_task.get('company_name'):
            return JsonResponse({'status': 'error', 'message': 'Invalid company payload.'}, status=400)

        result = BatchDiscoveryService.process_single_company(company_task, options)
        return JsonResponse(result)
    except Exception as e:
        logger.exception("Company processing failed")
        return JsonResponse({
            'status': 'error',
            'company_name': (company_task.get('company_name') if company_task else 'Unknown'),
            'message': str(e),
            'jobs_discovered': 0,
            'jobs_imported': 0,
            'csr_discovered': 0,
            'csr_imported': 0,
            'logs': [f"[ERROR] Discovery halted: {str(e)}"]
        }, status=200)
```

2. Add JSON-aware CSRF failure handler and 500 handler in `batch_discovery_views.py`:
```python
def api_csrf_failure_view(request, reason=""):
    return JsonResponse({
        'status': 'error',
        'error': 'CSRF_FAILURE',
        'message': f'CSRF security check failed ({reason}). Please refresh the page.'
    }, status=403)
```

#### Target C: `templates/admin/ai_discovery/index.html`
1. Upgrade `safeParseJsonResponse(resp)`:
```javascript
async function safeParseJsonResponse(resp) {
    if (!resp) throw new Error("Empty response object received from server.");
    
    // Detect redirect to login page
    if (resp.redirected && (resp.url.includes('/login') || resp.url.includes('/admin-portal/login'))) {
        const authErr = new Error("Your administrator session has expired. Please sign in again.");
        authErr.isSessionExpired = true;
        authErr.loginUrl = resp.url;
        throw authErr;
    }

    const contentType = resp.headers.get('content-type') || '';
    const text = await resp.text();

    if (resp.status === 401 || resp.status === 403) {
        let errorMsg = null;
        try {
            const parsed = JSON.parse(text);
            errorMsg = parsed.message || parsed.error;
        } catch(e) {}
        const authErr = new Error(errorMsg || `Session expired or permission denied (HTTP ${resp.status}).`);
        authErr.isSessionExpired = (resp.status === 401 || (errorMsg && errorMsg.includes('session')));
        authErr.status = resp.status;
        throw authErr;
    }

    if (!text || !text.trim()) {
        throw new Error(`Server returned empty response (HTTP ${resp.status})`);
    }

    const trimmed = text.trim();
    if (trimmed.startsWith('<') || trimmed.toLowerCase().startsWith('<!doctype') || (!contentType.includes('application/json') && !trimmed.startsWith('{') && !trimmed.startsWith('['))) {
        let titleMatch = trimmed.match(/<title[^>]*>([^<]+)<\/title>/i);
        let extractedMsg = titleMatch ? titleMatch[1].trim() : `Server returned HTML response (HTTP ${resp.status})`;
        if (extractedMsg.toLowerCase().includes('log in') || extractedMsg.toLowerCase().includes('login')) {
            const authErr = new Error("Administrator session expired. Please sign in again.");
            authErr.isSessionExpired = true;
            throw authErr;
        }
        throw new Error(`Server returned HTML error: ${extractedMsg}`);
    }

    try {
        const parsed = JSON.parse(text);
        if (!resp.ok && parsed.message) {
            throw new Error(parsed.message);
        }
        return parsed;
    } catch (e) {
        if (e.isSessionExpired) throw e;
        throw new Error(`Invalid JSON format (HTTP ${resp.status}): ${e.message}`);
    }
}
```

2. Upgrade `processNextCompany` error handling:
```javascript
} catch (err) {
    if (err.isSessionExpired) {
        isQueuePaused = true;
        isQueueRunning = false;
        logTerminal(`[AUTH_ERROR] Administrator session expired. Queue automatically paused to prevent data loss.`, '#EF4444');
        showInAppNotification({
            title: 'Session Expired',
            message: 'Your administrator session has timed out. Please open the login page to re-authenticate, then click Resume.',
            type: 'error',
            duration: 12000
        });
        const alertBox = document.getElementById('queue-emergency-alert');
        if (alertBox) {
            alertBox.style.display = 'flex';
            const alertText = document.getElementById('emergency-alert-text');
            if (alertText) alertText.innerHTML = `<strong>Session Expired:</strong> Your admin session has timed out. <a href="/admin-portal/login/?next=/admin-portal/ai-discovery/" target="_blank" style="color:#0A6CFF; text-decoration:underline; font-weight:700;">Click here to sign in in a new tab</a>, then click Resume below.`;
        }
        const pauseBtn = document.getElementById('btn-pause-resume');
        if (pauseBtn) {
            pauseBtn.innerText = 'Resume';
            pauseBtn.style.display = 'inline-block';
        }
        return; // Halt queue progression immediately
    }
    // Continue normal retry logic for transient network failures...
```

---

## 5. Verification Method

To verify these findings and confirm resolution:

1. **Verify Unauthenticated Middleware Behavior**:
   ```bash
   .venv\Scripts\python -c "
   import os, django
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
   django.setup()
   from django.test import Client
   c = Client()
   r = c.post('/admin-portal/ai-discovery/process-company/', data='{}', content_type='application/json')
   print('Status:', r.status_code, 'Content-Type:', r.headers.get('Content-Type'))
   "
   ```
   - **Current Output**: `Status: 302 Content-Type: text/html; charset=utf-8 Location: /admin-portal/login/?next=...`
   - **Expected Output after fix**: `Status: 401 Content-Type: application/json`

2. **Verify `UnboundLocalError` Fix**:
   ```bash
   .venv\Scripts\python -c "
   import os, django
   os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
   django.setup()
   from django.test import Client
   from modules.admin_panel.models import User
   u = User.objects.filter(is_superuser=True).first()
   c = Client()
   if u:
       c.force_login(u)
       r = c.post('/admin-portal/ai-discovery/process-company/', data='invalid json', content_type='application/json')
       print('Status:', r.status_code, 'Body:', r.json())
   "
   ```
   - **Current Output**: `Status: 500` with HTML trace page.
   - **Expected Output after fix**: `Status: 400 Body: {'status': 'error', 'message': 'Malformed JSON request body...'}`

3. **Verify Automated Unit Tests**:
   Execute the suite via:
   ```bash
   .venv\Scripts\python -m unittest tests.test_pilot_batch_crawler
   ```
