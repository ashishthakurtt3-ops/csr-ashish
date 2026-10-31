import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

import sqlite3
from modules.admin_panel.models import AIProviderConfig, AISystemSettings, AIConfigurationAuditLog

print("=== AI PROVIDER CONFIG INVENTORY ===")
providers = AIProviderConfig.objects.all().order_by('provider')
print(f"Total Providers: {providers.count()}")
for p in providers:
    has_encrypted = bool(p.encrypted_api_key)
    print(f"Provider: {p.provider:12} | Display: {p.display_name:24} | Enabled: {str(p.is_enabled):5} | Status: {p.status:14} | SelectedModel: {p.selected_model:28} | BaseURL: {p.base_url or '(default)':32} | KeyMasked: {p.api_key_masked or '(none)':18} | HasEncrypted: {has_encrypted} | PaidAllowed: {p.allow_paid_calls} | LastTested: {p.last_tested_at} | LastResult: {p.last_test_result}")

print("\n=== AI SYSTEM SETTINGS ===")
settings = AISystemSettings.get_solo()
print(f"Primary Provider: {settings.primary_provider}")
print(f"Primary Model: {settings.primary_model}")
print(f"Fallback Provider: {settings.fallback_provider}")
print(f"Fallback Model: {settings.fallback_model}")
print(f"Fallback Enabled: {settings.fallback_enabled}")
print(f"Free Tier Only: {settings.free_tier_only}")
print(f"Request Timeout: {settings.request_timeout}s")
print(f"Max Retries: {settings.max_retries}")
print(f"Max Calls Per Run: {settings.max_api_calls_per_run}")

print("\n=== AUDIT LOG (Last 10 entries) ===")
logs = AIConfigurationAuditLog.objects.all().order_by('-timestamp')[:10]
print(f"Total Audit Logs: {AIConfigurationAuditLog.objects.count()}")
for l in logs:
    print(f"{l.timestamp} | Action: {l.action:18} | Provider: {l.provider:12} | Status: {l.status:12} | Details: {str(l.details)[:80]}")

print("\n=== TELEMETRY SQLITE DB ===")
db_path = os.path.join(os.getcwd(), ".cache", "ai_classifier", "ai_telemetry.sqlite3")
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    tables = [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"Telemetry Tables: {tables}")
    for t in tables:
        count = cur.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
        print(f"  Table {t}: {count} records")
        if count > 0:
            sample = cur.execute(f"SELECT * FROM {t} ORDER BY id DESC LIMIT 5").fetchall()
            for s in sample:
                print(f"    {s}")
    conn.close()
else:
    print(f"Telemetry DB not found at: {db_path}")

print("\n=== AI CACHE SQLITE DB ===")
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
            sample = cur.execute(f"SELECT * FROM {t} ORDER BY rowid DESC LIMIT 5").fetchall()
            for s in sample:
                print(f"    Row: {str(s)[:150]}")
    conn.close()
else:
    print(f"AI Cache DB not found at: {cache_path}")
