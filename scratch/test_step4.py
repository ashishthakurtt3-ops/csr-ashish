import os
import sys
import time
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
django.setup()

from django.test import RequestFactory
from django.db import connection, reset_queries
from config import settings
settings.DEBUG = False

from modules.website.views.job_api_views import jobs_list_api, job_detail_api
from modules.website.views.opportunity_api_views import csr_projects_api

factory = RequestFactory()

def test_endpoint(name, view_func, path, **kwargs):
    req = factory.get(path)
    # Warm up
    view_func(req, **kwargs)
    
    # Measure warm
    reset_queries()
    t0 = time.perf_counter()
    resp = view_func(req, **kwargs)
    t1 = time.perf_counter()
    duration_ms = (t1 - t0) * 1000
    q_count = len(connection.queries)
    content_kb = len(resp.content) / 1024
    print(f"[{name}] Warm: {duration_ms:.2f} ms | Queries: {q_count} | Size: {content_kb:.2f} KB")

print("--- Testing Step 4 Endpoints ---")
test_endpoint("/jobs?page=1&page_size=12", jobs_list_api, "/jobs?page=1&page_size=12")
test_endpoint("/jobs (capped fallback)", jobs_list_api, "/jobs")
test_endpoint("/csr/projects?page=1&page_size=12", csr_projects_api, "/csr/projects?page=1&page_size=12")
test_endpoint("/csr/projects (capped fallback)", csr_projects_api, "/csr/projects")
test_endpoint("/jobs/6524 (detail)", job_detail_api, "/jobs/6524", job_id=6524)
