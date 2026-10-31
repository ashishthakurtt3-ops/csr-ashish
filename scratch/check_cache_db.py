import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import sqlite3

cache_path = os.path.join(os.getcwd(), ".cache", "ai_classifier", "ai_cache.sqlite3")
if os.path.exists(cache_path):
    conn = sqlite3.connect(cache_path)
    cur = conn.cursor()
    tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"Cache Tables: {tables}")
    for t in tables:
        count = cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  Table {t}: {count} records")
        if count > 0:
            cols = [c[1] for c in cur.execute(f"PRAGMA table_info({t})").fetchall()]
            print(f"    Columns for {t}: {cols}")
            sample = cur.execute(f"SELECT * FROM {t} LIMIT 5").fetchall()
            for s in sample:
                print(f"    Row: {str(s)[:150]}")
    conn.close()
else:
    print(f"AI Cache DB not found at: {cache_path}")

