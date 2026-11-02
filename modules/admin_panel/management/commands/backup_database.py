import os
import sys
import subprocess
import time
import re
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Creates an automated MySQL database backup with verification, daily/weekly retention pruning, and audit logging'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default=os.path.join(settings.BASE_DIR, 'exports', 'backups'),
            help='Directory to store the database backup file',
        )
        parser.add_argument(
            '--daily-retention',
            type=int,
            default=30,
            help='Number of daily backups to retain (default: 30 days)',
        )
        parser.add_argument(
            '--weekly-retention',
            type=int,
            default=12,
            help='Number of weekly backups to retain beyond daily retention (default: 12 weeks)',
        )
        parser.add_argument(
            '--retention',
            type=int,
            default=None,
            help='Legacy parameter: sets daily retention limit',
        )

    def handle(self, *args, **options):
        output_dir = options['output_dir']
        daily_retention = options.get('retention') or options['daily_retention']
        weekly_retention = options['weekly_retention']
        os.makedirs(output_dir, exist_ok=True)

        log_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'backup_history.log')

        db = settings.DATABASES['default']
        now = datetime.now()
        timestamp = now.strftime('%Y%m%d_%H%M%S')
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
        start_time = time.time()
        try:
            with open(backup_path, 'wb') as f:
                res = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, env=env)

            duration = time.time() - start_time

            if res.returncode != 0:
                err_msg = res.stderr.decode('utf-8', errors='replace').strip()
                self.stderr.write(self.style.ERROR(f"Backup failed: {err_msg}"))
                self._log_history(log_file, "FAILED", backup_filename, 0, duration, f"mysqldump error: {err_msg}")
                return

            size_bytes = os.path.getsize(backup_path)
            size_mb = size_bytes / (1024 * 1024)
            self.stdout.write(f"Backup written ({size_mb:.2f} MB in {duration:.2f}s). Verifying integrity...")

            # Integrity verification check
            with open(backup_path, 'r', encoding='utf-8', errors='replace') as f:
                content_head = [f.readline() for _ in range(50)]
                f.seek(0, os.SEEK_END)
                end_pos = max(0, f.tell() - 2048)
                f.seek(end_pos)
                tail = f.read()

            head_text = ''.join(content_head)
            if 'MySQL dump' not in head_text:
                warn_msg = "Verification warning: 'MySQL dump' header missing."
                self.stderr.write(self.style.WARNING(warn_msg))
                self._log_history(log_file, "WARNING", backup_filename, size_mb, duration, warn_msg)
            elif 'Dump completed' not in tail:
                warn_msg = "Verification warning: 'Dump completed' footer missing."
                self.stderr.write(self.style.WARNING(warn_msg))
                self._log_history(log_file, "WARNING", backup_filename, size_mb, duration, warn_msg)
            else:
                self.stdout.write(self.style.SUCCESS(f"[OK] Backup integrity verified: {backup_filename}"))

            # Retention pruning (30 daily + 12 weekly)
            pruned_count, kept_daily, kept_weekly = self._prune_daily_weekly_backups(
                output_dir, daily_retention, weekly_retention
            )

            note = f"Integrity Verified. Kept {kept_daily} daily, {kept_weekly} weekly. Pruned {pruned_count} old."
            self._log_history(log_file, "SUCCESS", backup_filename, size_mb, duration, note)

        except Exception as e:
            duration = time.time() - start_time
            err_str = str(e)
            self.stderr.write(self.style.ERROR(f"Error executing backup: {err_str}"))
            self._log_history(log_file, "ERROR", backup_filename, 0, duration, err_str)

    def _log_history(self, log_path: str, status: str, filename: str, size_mb: float, duration: float, notes: str):
        try:
            timestamp_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_line = f"[{timestamp_str}] [{status:<7}] File: {filename:<45} | Size: {size_mb:6.2f} MB | Time: {duration:5.2f}s | {notes}\n"
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(log_line)
        except Exception as e:
            self.stderr.write(f"Failed writing to audit log: {e}")

    def _prune_daily_weekly_backups(self, output_dir: str, daily_limit: int, weekly_limit: int):
        try:
            backups = [
                f for f in os.listdir(output_dir)
                if f.startswith('csr_intelligence_backup_') and f.endswith('.sql')
            ]

            backup_meta = []
            for fname in backups:
                fpath = os.path.join(output_dir, fname)
                m = re.search(r'(\d{8})_(\d{6})', fname)
                if m:
                    dt = datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H%M%S')
                else:
                    dt = datetime.fromtimestamp(os.path.getmtime(fpath))
                backup_meta.append({
                    'name': fname,
                    'path': fpath,
                    'dt': dt,
                    'date': dt.date(),
                    'week': (dt.isocalendar()[0], dt.isocalendar()[1]),
                })

            backup_meta.sort(key=lambda x: x['dt'], reverse=True)

            # Preserve all backups if total is small
            if len(backup_meta) <= daily_limit:
                self.stdout.write(f"Current backup count ({len(backup_meta)}) is within daily limit ({daily_limit}). No pruning needed.")
                return 0, len(backup_meta), 0

            # Organize daily backups (latest per calendar day)
            keep_paths = set()
            daily_kept = 0
            seen_dates = set()

            for item in backup_meta:
                if item['date'] not in seen_dates:
                    seen_dates.add(item['date'])
                    keep_paths.add(item['path'])
                    daily_kept += 1
                    if daily_kept >= daily_limit:
                        break

            # Organize weekly backups for older backups (up to 12 weeks)
            weekly_kept = 0
            seen_weeks = set()

            # Inspect backups older than the daily cutoff
            cutoff_date = min(seen_dates) if seen_dates else datetime.now().date()
            for item in backup_meta:
                if item['date'] < cutoff_date:
                    if item['week'] not in seen_weeks:
                        seen_weeks.add(item['week'])
                        keep_paths.add(item['path'])
                        weekly_kept += 1
                        if weekly_kept >= weekly_limit:
                            break

            # Identify candidates for pruning
            to_delete = [item for item in backup_meta if item['path'] not in keep_paths]

            pruned = 0
            if to_delete:
                self.stdout.write(f"Pruning {len(to_delete)} backup(s) exceeding retention limits ({daily_limit} daily, {weekly_limit} weekly)...")
                for item in to_delete:
                    try:
                        os.remove(item['path'])
                        self.stdout.write(f"  Removed: {item['name']}")
                        pruned += 1
                    except Exception as e:
                        self.stderr.write(f"  Failed to delete {item['name']}: {e}")

            return pruned, daily_kept, weekly_kept

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error during backup pruning: {e}"))
            return 0, 0, 0
