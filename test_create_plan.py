import urllib.request, urllib.parse, http.cookiejar, re

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# GET the create page
try:
    r = opener.open('http://127.0.0.1:8000/admin-portal/subscriptions/plans/create/', timeout=10)
    html = r.read().decode()
    print('GET status:', r.status)
    
    # Extract CSRF token
    csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', html)
    if csrf_match:
        csrf_token = csrf_match.group(1)
        print('CSRF token found:', csrf_token[:20] + '...')
    else:
        print('CSRF token NOT found')
        csrf_token = ''
        
    if 'is_new' in html:
        print('is_new variable present in template')
    else:
        print('is_new variable NOT found in template')
        
except Exception as e:
    print('GET error:', e)

# Now try POST to create a plan
data = urllib.parse.urlencode({
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

req = urllib.request.Request(
    'http://127.0.0.1:8000/admin-portal/subscriptions/plans/create/',
    data=data,
    headers={
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'http://127.0.0.1:8000/admin-portal/subscriptions/plans/create/',
        'Cookie': '; '.join([c.name + '=' + c.value for c in cj])
    }
)

try:
    r = opener.open(req, timeout=10)
    print('POST status:', r.status)
    print('Redirect URL:', r.geturl())
except urllib.error.HTTPError as e:
    print('HTTP ERROR:', e.code, e.reason)
    body = e.read().decode()
    print('Error body (first 2000 chars):')
    print(body[:2000])
except Exception as e:
    print('POST error:', e)