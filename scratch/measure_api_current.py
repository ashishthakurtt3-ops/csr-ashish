import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.test import RequestFactory
from modules.website.views.job_api_views import jobs_list_api, jobs_summary_api
from modules.website.views.opportunity_api_views import csr_projects_api, csr_opportunities_api
import json

rf = RequestFactory()

# 1. Jobs List API
req = rf.get('/api/jobs/?page=1&page_size=24&format=json')
res = jobs_list_api(req)
data = json.loads(res.content)
print("=== JOBS LIST API ===")
print("Status Code:", res.status_code)
print("Total jobs reported in JSON:", data.get('total'))
print("Returned in this page:", len(data.get('results', [])))

# 2. Jobs Summary API
req_sum = rf.get('/api/jobs/summary/')
res_sum = jobs_summary_api(req_sum)
data_sum = json.loads(res_sum.content)
print("\n=== JOBS SUMMARY API ===")
print("Status Code:", res_sum.status_code)
print("Summary data:", data_sum.get('summary', data_sum))

# 3. CSR Projects API
req_proj = rf.get('/api/csr-projects/?page=1&page_size=24&format=json')
res_proj = csr_projects_api(req_proj)
data_proj = json.loads(res_proj.content)
print("\n=== CSR PROJECTS API ===")
print("Status Code:", res_proj.status_code)
print("Total projects reported in JSON:", data_proj.get('total'))
print("Returned in this page:", len(data_proj.get('results', [])))

# 4. CSR Opportunities API
req_opp = rf.get('/api/opportunities/?page=1&page_size=24&format=json')
res_opp = csr_opportunities_api(req_opp)
data_opp = json.loads(res_opp.content)
print("\n=== CSR OPPORTUNITIES API ===")
print("Status Code:", res_opp.status_code)
print("Total opportunities reported in JSON:", data_opp.get('total'))
print("Returned in this page:", len(data_opp.get('results', [])))
