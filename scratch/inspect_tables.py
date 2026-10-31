import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.apps import apps
from django.db import connection

print("--- REGISTERED MODELS & TABLE NAMES ---")
for model in apps.get_models():
    if 'admin_panel' in model._meta.app_label or 'website' in model._meta.app_label:
        count = model.objects.count() if not model._meta.abstract else 'abstract'
        print(f"{model.__name__} (app: {model._meta.app_label}, table: {model._meta.db_table}) -> {count} rows")

with connection.cursor() as c:
    c.execute("SHOW TABLES")
    all_tables = [row[0] for row in c.fetchall()]
print(f"\nTotal MySQL tables in DB: {len(all_tables)}")
for t in all_tables:
    if 'job' in t or 'opp' in t or 'csr' in t or 'proj' in t:
        with connection.cursor() as c:
            c.execute(f"SELECT COUNT(*) FROM `{t}`")
            cnt = c.fetchone()[0]
        print(f"Table `{t}`: {cnt} rows")
