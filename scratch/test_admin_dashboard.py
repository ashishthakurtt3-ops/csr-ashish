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

from modules.admin_panel.views.dashboard import admin_dashboard_view
from modules.admin_panel.models import User

user = User.objects.filter(role='ADMIN').first()
factory = RequestFactory()
req = factory.get('/admin-portal/')
req.user = user

# warm up
admin_dashboard_view(req)

reset_queries()
t0 = time.perf_counter()
resp = admin_dashboard_view(req)
t1 = time.perf_counter()
duration_ms = (t1 - t0) * 1000

print(f"Admin Dashboard Warm: {duration_ms:.2f} ms | Query count: {len(connection.queries)}")
for i, q in enumerate(connection.queries):
    print(f"{i+1}. {q['sql'][:120]}... ({q['time']}s)")
