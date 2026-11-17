"""End-to-end smoke-check for the admin plan-creation flow.

Logs in with credentials supplied through the environment, then verifies that
the create-plan page renders with an enabled plan-code field and that the form
submits successfully.

Manual script, not a unit test. It is deliberately named without a ``test``
prefix so that ``manage.py test`` does not import it during discovery.

Usage (with a development server running):

    $env:SMOKE_BASE_URL    = 'http://127.0.0.1:8000'
    $env:SMOKE_ADMIN_USER  = '<admin username>'
    $env:SMOKE_ADMIN_PASS  = '<admin password>'
    .\.venv\Scripts\python.exe scripts\create_plan_full_smoke.py

The script refuses to run without credentials; none are hardcoded.
"""

import http.cookiejar
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = 'http://127.0.0.1:8000'
LOGIN_PATH = '/admin-portal/login/'
CREATE_PLAN_PATH = '/admin-portal/subscriptions/plans/create/'


def _extract_csrf(html: str) -> str:
    match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    return match.group(1) if match else ''


def main() -> int:
    username = os.environ.get('SMOKE_ADMIN_USER', '')
    password = os.environ.get('SMOKE_ADMIN_PASS', '')
    if not username or not password:
        print('SMOKE_ADMIN_USER and SMOKE_ADMIN_PASS must be set. Aborting.')
        return 2

    base_url = os.environ.get('SMOKE_BASE_URL', DEFAULT_BASE_URL).rstrip('/')
    login_url = base_url + LOGIN_PATH
    create_url = base_url + CREATE_PLAN_PATH

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    failures = 0

    def cookies() -> str:
        return '; '.join(f'{c.name}={c.value}' for c in cj)

    # Step 1: GET login page to obtain a CSRF token.
    print('=== Step 1: Login ===')
    response = opener.open(login_url, timeout=10)
    html = response.read().decode()
    csrf_token = _extract_csrf(html)
    print('Login CSRF:', csrf_token[:20] if csrf_token else 'NOT FOUND')

    # Step 2: POST login.
    login_data = urllib.parse.urlencode({
        'csrfmiddlewaretoken': csrf_token,
        'username': username,
        'password': password,
        'next': CREATE_PLAN_PATH,
    }).encode()

    request = urllib.request.Request(
        login_url,
        data=login_data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': login_url,
            'Cookie': cookies(),
        },
    )
    try:
        response = opener.open(request, timeout=10)
        print('Login status:', response.status, 'URL:', response.geturl())
    except urllib.error.HTTPError as exc:
        print('Login HTTP error:', exc.code, exc.reason)
        failures += 1

    # Step 3: GET the create-plan page.
    print()
    print('=== Step 2: GET Create Plan Page ===')
    response = opener.open(create_url, timeout=10)
    html = response.read().decode()
    print('Create page status:', response.status)

    if 'id="field-code"' in html and 'readonly' not in html.split('id="field-code"')[0].split('>')[-1]:
        print('Plan Code field is ENABLED (is_new=True working)')
    else:
        print('Plan Code field might be readonly')
        failures += 1

    csrf_token = _extract_csrf(html)
    print('Create page CSRF:', csrf_token[:20] if csrf_token else 'NOT FOUND')

    # Step 4: POST the new plan.
    print()
    print('=== Step 3: POST Create Plan ===')
    create_data = urllib.parse.urlencode({
        'csrfmiddlewaretoken': csrf_token,
        'code': 'testplan123',
        'name': 'Test Plan 123',
        'slug': 'test-plan-123',
        'description': 'A test plan',
        'currency': 'INR',
        'monthly_price_inr': '499',
        'yearly_price_inr': '4990',
        'trial_days': '0',
        'is_active': 'on',
        'is_visible': 'on',
        'button_visible': 'on',
        'button_order': '1',
        'limit_browse_companies': '20',
        'limit_saved_records': '20',
        'limit_saved_searches': '1',
        'limit_export_rows': '20',
        'limit_compare_companies': '0',
        'limit_seats': '1',
        'limit_alert_frequency': 'weekly',
        'button_text': 'Select Plan',
        'cta_text': 'Select Plan',
        'features': 'Feature 1\nFeature 2\nFeature 3',
    }).encode()

    request = urllib.request.Request(
        create_url,
        data=create_data,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': create_url,
            'Cookie': cookies(),
        },
    )
    try:
        response = opener.open(request, timeout=10)
        print('Create POST status:', response.status, 'URL:', response.geturl())
    except urllib.error.HTTPError as exc:
        print('Create POST HTTP ERROR:', exc.code, exc.reason)
        print('Error body (first 3000 chars):')
        print(exc.read().decode()[:3000])
        failures += 1
    except Exception as exc:  # noqa: BLE001 - diagnostic script
        print('Create POST error:', exc)
        failures += 1

    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
