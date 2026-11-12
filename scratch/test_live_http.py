import urllib.request, json

req = urllib.request.urlopen('http://127.0.0.1:8000/login/')
html = req.read().decode('utf-8')
assert req.status == 200
assert '<div class="alert alert-error"' not in html
print('HTTP Live Test 1: GET http://127.0.0.1:8000/login/ returned 200 with clean form!')

req2 = urllib.request.urlopen('http://127.0.0.1:8000/companies/DUMMY_COMP_INFY/dossier')
data = json.loads(req2.read().decode('utf-8'))
assert req2.status == 200
print('HTTP Live Test 2: Anonymous Dummy dossier returned company:', data['company']['company_name'])
print('ALL LIVE HTTP TESTS PASSED!')

