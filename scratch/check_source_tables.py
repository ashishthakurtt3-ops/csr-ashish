import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    for t in ['company_source_registry', 'company_crawl_summary', 'company_completeness_register', 'admin_panel_auditrun']:
        print(f"\n=== SCHEMA FOR {t} ===")
        cursor.execute(f"DESCRIBE `{t}`")
        for col in cursor.fetchall():
            print(f"  {col[0]:25} | {col[1]:20} | Null:{col[2]:3} | Key:{col[3]:3} | Default:{str(col[4]):10}")
        cursor.execute(f"SELECT count(*) FROM `{t}`")
        print(f"  TOTAL RECORDS: {cursor.fetchone()[0]}")

