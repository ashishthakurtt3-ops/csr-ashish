import hashlib
import sys
import os

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Company

count = Company.objects.count()
hasher = hashlib.sha256()
for c in Company.objects.order_by('company_id'):
    line = f"{c.company_id}:{c.company_name}:{c.website_url}\n"
    hasher.update(line.encode('utf-8'))

checksum = hasher.hexdigest()
print(f"DB Row count: {count}")
print(f"DB SHA256 Checksum: {checksum}")
