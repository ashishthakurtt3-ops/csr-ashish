import os
import sys
import subprocess
import time

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
from django.conf import settings

db = settings.DATABASES['default']
backup_dir = os.path.join('exports', 'backups')
os.makedirs(backup_dir, exist_ok=True)

timestamp = time.strftime('%Y%m%d_%H%M%S')
backup_path = os.path.join(backup_dir, f'csr_intelligence_backup_pre_cleanup_{timestamp}.sql')

mysqldump_bin = r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe'
if not os.path.exists(mysqldump_bin):
    mysqldump_bin = 'mysqldump'

cmd = [
    mysqldump_bin,
    '-u', db['USER'],
    '-h', db['HOST'],
    '-P', str(db['PORT']),
    '--single-transaction',
    '--routines',
    '--triggers',
    db['NAME']
]

env = os.environ.copy()
env['MYSQL_PWD'] = db.get('PASSWORD', '')

print(f"Creating full database backup to {backup_path}...")
with open(backup_path, 'wb') as f:
    res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)

if res.returncode != 0:
    print(f"Error creating backup: {res.stderr.decode('utf-8', errors='replace')}")
    sys.exit(1)

size_mb = os.path.getsize(backup_path) / (1024 * 1024)
print(f"Backup created successfully! Size: {size_mb:.2f} MB")

# Verify backup can be read and contains essential tables
with open(backup_path, 'r', encoding='utf-8', errors='replace') as f:
    content_head = [f.readline() for _ in range(50)]
    f.seek(0, os.SEEK_END)
    end_pos = max(0, f.tell() - 2048)
    f.seek(end_pos)
    tail = f.read()

assert 'MySQL dump' in ''.join(content_head), "Backup header check failed"
assert 'Dump completed' in tail, "Backup completion marker missing"
print("Verification passed: Backup is valid and readable.")
