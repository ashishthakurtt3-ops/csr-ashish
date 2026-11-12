import django, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.test import Client
from modules.admin_panel.models import User

client = Client(SERVER_NAME='127.0.0.1')

# Test 1: GET /login/ (anonymous) -> pristine form, no alert-error
resp = client.get('/login/')
assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
assert '<div class="alert alert-error"' not in resp.content.decode('utf-8'), 'Found alert-error on clean GET /login/!'
print('Test 1 Passed: GET /login/ has zero alert-error banners.')

# Test 2: POST /login/ with invalid credentials -> returns 200 with inline error, no session message leakage
resp = client.post('/login/', {'username': 'wronguser', 'password': 'wrongpassword'})
assert resp.status_code == 200
assert 'Invalid username or password' in resp.content.decode('utf-8')
# Refreshing GET /login/ immediately after should NOT have any error!
resp_after = client.get('/login/')
assert '<div class="alert alert-error"' not in resp_after.content.decode('utf-8'), 'Found leaked error on subsequent GET!'
print('Test 2 Passed: POST /login/ invalid credentials handled cleanly without session leakage.')

# Test 3: Log in as admin123454 and access /admin-portal/
u = User.objects.get(username='admin123454')
client.force_login(u)
resp = client.get('/admin-portal/', follow=True)
print('Test 3: admin123454 /admin-portal/ status:', resp.status_code, 'Final URL:', resp.redirect_chain)
assert resp.status_code == 200
print('Test 3 Passed: admin123454 has full administrative access to /admin-portal/.')

# Test 4: Anonymous dossier lookup for DUMMY_COMP_INFY
anon_client = Client(SERVER_NAME='127.0.0.1')
resp = anon_client.get('/companies/DUMMY_COMP_INFY/dossier')
assert resp.status_code == 200
data = resp.json()
assert data['company']['company_name'] == 'Infosys Limited'
assert len(data.get('jobs', [])) > 0
assert len(data.get('projects', [])) > 0
print(f"Test 4 Passed: Anonymous dummy dossier returned 200 with {len(data['jobs'])} jobs and {len(data['projects'])} CSR projects.")

# Test 5: Subscription comparison API
resp = anon_client.get('/api/subscription/comparison')
assert resp.status_code == 200
comp_data = resp.json()
assert len(comp_data['plans']) >= 3
print(f"Test 5 Passed: Subscription comparison API returned {len(comp_data['plans'])} plans.")
print('ALL TESTS PASSED SUCCESSFULLY!')
