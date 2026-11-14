import urllib.request, urllib.parse, http.cookiejar, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Step 1: GET login page to get CSRF token
print('=== Step 1: Login ===')
r = opener.open('http://127.0.0.1:8000/admin-portal/login/', timeout=10)
html = r.read().decode()
csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
csrf_token = csrf_match.group(1) if csrf_match else ''
print('Login CSRF:', csrf_token[:20] if csrf_token else 'NOT FOUND')

# Step 2: POST login
login_data = urllib.parse.urlencode({
    'csrfmiddlewaretoken': csrf_token,
    'username': 'admin',
    'password': 'admin123',
    'next': '/admin-portal/subscriptions/plans/create/',
}).encode()

req = urllib.request.Request(
    'http://127.0.0.1:8000/admin-portal/login/',
    data=login_data,
    headers={
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'http://127.0.0.1:8000/admin-portal/login/',
        'Cookie': '; '.join([c.name + '=' + c.value for c in cj])
    }
)
try:
    r = opener.open(req, timeout=10)
    print('Login status:', r.status, 'URL:', r.geturl())
except urllib.error.HTTPError as e:
    print('Login HTTP error:', e.code, e.reason)

# Step 3: GET create plan page
print()
print('=== Step 2: GET Create Plan Page ===')
r = opener.open('http://127.0.0.1:8000/admin-portal/subscriptions/plans/create/', timeout=10)
html = r.read().decode()
print('Create page status:', r.status)

# Check if is_new works (look for the enabled input field)
if 'id="field-code"' in html and 'readonly' not in html.split('id="field-code"')[0].split('>')[-1]:
    print('Plan Code field is ENABLED (is_new=True working)')
else:
    print('Plan Code field might be readonly')

# Extract CSRF from create page
csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
csrf_token = csrf_match.group(1) if csrf_match else ''
print('Create page CSRF:', csrf_token[:20] if csrf_token else 'NOT FOUND')

# Step 4: POST create plan
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

req = urllib.request.Request(
    'http://127.0.0.1:8000/admin-portal/subscriptions/plans/create/',
    data=create_data,
    headers={
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'http://127.0.0.1:8000/admin-portal/subscriptions/plans/create/',
        'Cookie': '; '.join([c.name + '=' + c.value for c in cj])
    }
)
try:
    r = opener.open(req, timeout=10)
    print('Create POST status:', r.status, 'URL:', r.geturl())
except urllib.error.HTTPError as e:
    print('Create POST HTTP ERROR:', e.code, e.reason)
    body = e.read().decode()
    print('Error body (first 3000 chars):')
    print(body[:3000])
except Exception as e:
    print('Create POST error:', e)