import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    for var in ['wait_timeout', 'interactive_timeout', 'net_read_timeout', 'net_write_timeout', 'max_allowed_packet', 'innodb_lock_wait_timeout', 'autocommit']:
        cursor.execute(f"SHOW VARIABLES LIKE '{var}'")
        print(cursor.fetchall())
