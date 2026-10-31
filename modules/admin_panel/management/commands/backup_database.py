import os
import sys
import subprocess
import time
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Creates an automated MySQL database backup with verification and retention pruning'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default=os.path.join(settings.BASE_DIR, 'exports', 'backups'),
            help='Directory to store the database backup file',
        )
        parser.add_argument(
            '--retention',
            type=int,
            default=10,
            help='Maximum number of backups to retain (older ones are pruned)',
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        retention = options['retention']
        os.makedirs(output_dir, exist_ok=True)

        db = settings.DATABASES['default']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"csr_intelligence_backup_{timestamp}.sql"
        backup_path = os.path.join(output_dir, backup_filename)

        mysqldump_candidates = [
            r'C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe',
            r'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqldump.exe',
            'mysqldump',
        ]
        mysqldump_bin = 'mysqldump'
        for cand in mysqldump_candidates:
            if os.path.exists(cand):
                mysqldump_bin = cand
                break

        cmd = [
            mysqldump_bin,
            '-u', str(db.get('USER', 'root')),
            '-h', str(db.get('HOST', 'localhost')),
            '-P', str(db.get('PORT', '3306')),
            '--single-transaction',
            '--routines',
            '--triggers',
            str(db['NAME'])
        ]

        env = os.environ.copy()
        env['MYSQL_PWD'] = str(db.get('PASSWORD', ''))

        self.stdout.write(f"Initiating automated database backup: {backup_filename}...")
        try:
            with open(backup_path, 'wb') as f:
                res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)

            if res.returncode != 0:
                err_msg = res.stderr.decode('utf-8', errors='replace')
                self.stderr.write(self.style.ERROR(f"Backup failed: {err_msg}"))
                return

            size_mb = os.path.getsize(backup_path) / (1024 * 1024)
            self.stdout.write(f"Backup written ({size_mb:.2f} MB). Verifying integrity...")

            # Integrity verification check
            with open(backup_path, 'r', encoding='utf-8', errors='replace') as f:
                content_head = [f.readline() for _ in range(50)]
                f.seek(0, os.SEEK_END)
                end_pos = max(0, f.tell() - 2048)
                f.seek(end_pos)
                tail = f.read()

            if 'MySQL dump' not in ''.join(content_head):
                self.stderr.write(self.style.ERROR("Verification warning: 'MySQL dump' header missing."))
            elif 'Dump completed' not in tail:
                self.stderr.write(self.style.ERROR("Verification warning: 'Dump completed' footer missing."))
            else:
                self.stdout.write(self.style.SUCCESS(f"[OK] Backup integrity verified: {backup_filename}"))

            # Retention pruning
            self._prune_old_backups(output_dir, retention)

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error executing backup: {e}"))

    def _prune_old_backups(self, output_dir: str, retention: int):
        try:
            backups = [
                os.path.join(output_dir, f) for f in os.listdir(output_dir)
                if f.startswith('csr_intelligence_backup_') and f.endswith('.sql')
            ]
            backups.sort(key=os.path.getmtime, reverse=True)

            if len(backups) > retention:
                to_delete = backups[retention:]
                self.stdout.write(f"Pruning {len(to_delete)} backup(s) exceeding retention limit of {retention}...")
                for old_f in to_delete:
                    try:
                        os.remove(old_f)
                        self.stdout.write(f"  Removed: {os.path.basename(old_f)}")
                    except Exception as e:
                        self.stderr.write(f"  Failed to delete {old_f}: {e}")
        except Exception as e:
            self.stderr.write(f"Error during backup pruning: {e}")
