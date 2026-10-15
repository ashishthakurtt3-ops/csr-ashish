import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SHOW VARIABLES LIKE '%semi%'")
    print("Semi sync:", cursor.fetchall())
    cursor.execute("SHOW VARIABLES LIKE 'sync_binlog'")
    print("sync_binlog:", cursor.fetchall())
    cursor.execute("SHOW VARIABLES LIKE 'innodb_flush_log_at_trx_commit'")
    print("innodb_flush_log:", cursor.fetchall())
