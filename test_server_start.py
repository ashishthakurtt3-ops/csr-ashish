import subprocess
import sys
import time
import urllib.request
import urllib.error

# Start the Django runserver in a subprocess
proc = subprocess.Popen(
    [sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000', '--insecure'],
    cwd=r'D:\D DOWNLOADS\CSR_Job_Intelligence_Production_Ready (1)',
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

# Wait for server to start (poll output)
started = False
for i in range(60):  # up to 30 seconds
    line = proc.stdout.readline(timeout=1)
    if not line:
        break
    print('SERVER OUTPUT:', line.strip())
    if 'http' in line.lower() and '8000' in line:
        started = True
    if 'Error' in line or 'ERROR' in line:
        print('!!! Server error detected !!!')

# Give it extra time
time.sleep(3)

# Check if process is still running
if proc.poll() is None:
    print('\n--- Server is running (PID:', proc.pid, ') ---')
    
    # Test 1: GET the create plan page
    print('\n=== TEST 1: GET Create Plan Page ===')
    try:
        r = urllib.request.urlopen('http://127.0.0.1:8000/admin-portal/subscriptions/plans/create/', timeout=10)
        html = r.read().decode()
        print('Status:', r.status)
        
        # Check for is_new context variable - it should be in the template context
        # but may not appear as text in the rendered HTML
        # Look for the code input field behavior
        if 'id="field-code"' in html:
            print('Plan code INPUT FIELD found in HTML')
            # Check if it has 'readonly' attribute
            if 'readonly' in html.split('id="field-code"')[1][:100]:
                print('Plan code field HAS readonly attribute')
            else:
                print('Plan code field does NOT have readonly attribute (good - is_new should be True)')
        else:
            print('Plan code INPUT FIELD NOT found in HTML')
            
        # Check for form elements
        if 'name="code"' in html:
            print('Plan code NAME found in form')
        else:
            print('Plan code NAME NOT found in form')
            
        if 'id="field-name"' in html:
            print('Plan name INPUT FIELD found')
        else:
            print('Plan name INPUT FIELD NOT found')
            
    except urllib.error.HTTPError as e:
        print('HTTP ERROR:', e.code, e.reason)
        body = e.read().decode()
        print('Error body (first 1000 chars):')
        print(body[:1000])
    except Exception as e:
        print('Error:', e)
    
    # Test 2: Try to POST create a plan (as admin)
    print('\n=== TEST 2: POST Create Plan (with admin auth) ===')
    # First login
    try:
        # Get login page
        r = urllib.request.urlopen('http://127.0.0.1:8000/admin-portal/login/', timeout=10)
        login_html = r.read().decode()
        
        import re
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_html)
        csrf_token = csrf_match.group(1) if csrf_match else ''
        
        # Login
        login_data = urllib.parse.urlencode({
            'csrfmiddlewaretoken': csrf_token,
            'username': 'admin',
            'password': 'admin123',
        }).encode()
        
        req = urllib.request.Request(
            'http://127.0.0.1:8000/admin-portal/login/',
            data=login_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        r = urllib.request.urlopen(req, timeout=10)
        print('Login redirected to:', r.geturl())
        
        # Now create a plan
        create_data = urllib.parse.urlencode({
            'csrfmiddlewaretoken': csrf_token,
            'code': 'newtestplan',
            'name': 'New Test Plan',
            'slug': 'new-test-plan',
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
            'features': 'Test feature',
        }).encode()
        
        req = urllib.request.Request(
            'http://127.0.0.1:8000/admin-portal/subscriptions/plans/create/',
            data=create_data,
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Referer': 'http://127.0.0.1:8000/admin-portal/subscriptions/plans/create/',
                'Cookie': 'sessionid=' + urllib.request.urlopen('http://127.0.0.1:8000/').cookies.get('sessionid', '') if hasattr(urllib.request.urlopen('http://127.0.0.1:8000/'), 'cookies') else ''
            }
        )
        try:
            r = urllib.request.urlopen(req, timeout=15)
            print('CREATE POST status:', r.status, 'URL:', r.geturl())
        except urllib.error.HTTPError as e:
            print('CREATE POST HTTP ERROR:', e.code, e.reason)
            body = e.read().decode()
            print('Error body (first 2000 chars):')
            print(body[:2000])
    except Exception as e:
        print('Login/create test error:', e)
else:
    print('Server process exited unexpectedly')
    output, _ = proc.communicate(timeout=5)
    print('Output:', output[:2000])