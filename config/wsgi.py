"""
WSGI config for CSR & Job Intelligence Platform.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Startup check: logs effective DEBUG, cache backend, CONN_MAX_AGE and server type
try:
    from django.conf import settings
    server_type = "Waitress WSGI" if any("waitress" in m.lower() for m in sys.modules) else "WSGI Application"
    cache_backend = settings.CACHES.get('default', {}).get('BACKEND', 'Unknown')
    conn_max_age = settings.DATABASES.get('default', {}).get('CONN_MAX_AGE', 'None')
    print("=" * 60)
    print(" [SERVER STARTUP CHECK]")
    print(f"  Server Type:   {server_type}")
    print(f"  DEBUG:         {settings.DEBUG}")
    print(f"  Cache Backend: {cache_backend}")
    print(f"  CONN_MAX_AGE:  {conn_max_age}")
    print("=" * 60)
except Exception as e:
    print(f"Startup check warning: {e}")
