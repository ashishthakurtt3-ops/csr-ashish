import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SHOW COLUMNS FROM admin_panel_company LIKE 'website_url'")
    col = cursor.fetchone()
    print("Column definition for website_url:", col)

    cursor.execute("SHOW TRIGGERS WHERE `Table` = 'admin_panel_company'")
    triggers = cursor.fetchall()
    print("Triggers on admin_panel_company:", triggers)

