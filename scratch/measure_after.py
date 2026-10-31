import os
import sys
import time
import json
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.db import connection, reset_queries
from django.conf import settings
from modules.admin_panel.models import Job

# DEBUG=False for application logic and benchmark
settings.DEBUG = False

first_job = Job.objects.filter(is_defective=False, status='ACTIVE').first()
jid = first_job.job_row_id if first_job else 6524

client = Client()
admin_pwd = os.environ.get('TEST_ADMIN_PASSWORD', 'Admin@12345')
client.login(username='admin', password=admin_pwd)

endpoints = [
    ('/stats', '/stats'),
    ('/companies?page=1&page_size=12', '/companies?page=1&page_size=12'),
    ('/companies?limit=5000', '/companies?limit=5000'),
    ('/jobs?page=1&page_size=12', '/jobs?page=1&page_size=12'),
    ('/jobs', '/jobs'),
    (f'/jobs/{jid}', f'/jobs/{jid}'),
    ('/csr/projects', '/csr/projects'),
    ('/csr/projects?page=1&page_size=12', '/csr/projects?page=1&page_size=12'),
    ('/ngo/matches', '/ngo/matches'),
    ('/', '/'),
    ('/admin-portal/', '/admin-portal/'),
    ('/admin-portal/jobs/', '/admin-portal/jobs/'),
]

print('=' * 95)
print('AFTER OPTIMIZATION MEASUREMENTS (DEBUG=False)')
print('=' * 95)
print(f'{"Endpoint":<38} | {"Cold (ms)":<10} | {"Warm (ms)":<10} | {"Queries":<8} | {"Size (KB)":<10}')
print('-' * 95)

results = []
for name, url in endpoints:
    # Cold request
    with connection.cursor():
        pass
    connection.force_debug_cursor = True
    reset_queries()
    t0 = time.perf_counter()
    r1 = client.get(url)
    cold_ms = (time.perf_counter() - t0) * 1000.0
    cold_queries = len(connection.queries)

    # Warm request
    reset_queries()
    t0 = time.perf_counter()
    r2 = client.get(url)
    warm_ms = (time.perf_counter() - t0) * 1000.0
    warm_queries = len(connection.queries)
    connection.force_debug_cursor = False

    size_kb = len(r2.content) / 1024.0

    print(f'{name:<38} | {cold_ms:<10.2f} | {warm_ms:<10.2f} | {warm_queries:<8} | {size_kb:<10.2f}')
    results.append({
        'endpoint': name,
        'cold_ms': round(cold_ms, 2),
        'warm_ms': round(warm_ms, 2),
        'queries': warm_queries,
        'size_kb': round(size_kb, 2),
        'status_code': r2.status_code,
    })

# Optimized SPA First Load Requests:
# In static/js/app.js: initApp() now fires only 3 requests for the visible tab
spa_requests = [
    '/stats',
    '/companies/lookup',
    '/jobs?page=1&page_size=12',
]
t_spa_0 = time.perf_counter()
for ep in spa_requests:
    client.get(ep)
total_spa_time_ms = (time.perf_counter() - t_spa_0) * 1000.0

print('-' * 95)
print(f'SPA First Load Requests: {len(spa_requests)} requests | Total Execution Time: {total_spa_time_ms:.2f} ms')
print('=' * 95)

with open('scratch/after_measurements.json', 'w') as f:
    json.dump({'endpoints': results, 'spa_requests_count': len(spa_requests), 'spa_time_ms': round(total_spa_time_ms, 2)}, f, indent=2)
