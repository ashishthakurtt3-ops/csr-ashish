"""Smoke-check the admin "create subscription plan" page.

Manual script, not a unit test. It is deliberately named without a ``test``
prefix so that ``manage.py test`` does not import it during discovery.

Usage (with a development server running):

    $env:SMOKE_BASE_URL = 'http://127.0.0.1:8000'
    .\.venv\Scripts\python.exe scripts\create_plan_smoke.py

Exit code 0 means the page rendered and the POST was accepted or redirected.
"""

import http.cookiejar
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = 'http://127.0.0.1:8000'
CREATE_PLAN_PATH = '/admin-portal/subscriptions/plans/create/'


def main() -> int:
    base_url = os.environ.get('SMOKE_BASE_URL', DEFAULT_BASE_URL).rstrip('/')
    create_url = base_url + CREATE_PLAN_PATH

    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    failures = 0
    csrf_token = ''

    # GET the create page and extract the CSRF token.
    try:
        response = opener.open(create_url, timeout=10)
        html = response.read().decode()
        print('GET status:', response.status)

        match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
        if match:
            csrf_token = match.group(1)
            print('CSRF token found:', csrf_token[:20] + '...')
        else:
            print('CSRF token NOT found')
            failures += 1

        if 'is_new' in html:
            print('is_new variable present in template')
        else:
            print('is_new variable NOT found in template')
    except Exception as exc:  # noqa: BLE001 - diagnostic script
        print('GET error:', exc)
        failures += 1

    # POST a throwaway plan.
    payload = urllib.parse.urlencode({
        'csrfmiddlewaretoken': csrf_token,
        'code': 'testplan',
        'name': 'Test Plan',
        'slug': 'test-plan',
        'description': 'Test plan',
        'currency': 'INR',
        'monthly_price_inr': '0',
        'yearly_price_inr': '0',
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
    }).encode()

    request = urllib.request.Request(
        create_url,
        data=payload,
        headers={
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': create_url,
            'Cookie': '; '.join(f'{c.name}={c.value}' for c in cj),
        },
    )

    try:
        response = opener.open(request, timeout=10)
        print('POST status:', response.status)
        print('Redirect URL:', response.geturl())
    except urllib.error.HTTPError as exc:
        print('HTTP ERROR:', exc.code, exc.reason)
        print('Error body (first 2000 chars):')
        print(exc.read().decode()[:2000])
        failures += 1
    except Exception as exc:  # noqa: BLE001 - diagnostic script
        print('POST error:', exc)
        failures += 1

    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
