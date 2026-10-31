import os
import sys
import time
import django

sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from modules.admin_panel.models import Job
from modules.admin_panel.signals import pause_snapshot_signals

def run_benchmark():
    print("Benchmarking 500-row bulk save...")
    jobs = list(Job.objects.all()[:500])
    if len(jobs) < 500:
        print(f"Warning: Only {len(jobs)} jobs available.")
        
    print(f"Testing on {len(jobs)} jobs.")

    # 1. Measure BEFORE (signals active on each save)
    # We will test in a transaction and rollback so DB isn't permanently altered
    t0 = time.perf_counter()
    with transaction.atomic():
        for j in jobs:
            j.job_title = (j.job_title or '') + ' [TEST]'
            j.save()
        transaction.set_rollback(True)
    t_before = time.perf_counter() - t0
    print(f"BEFORE (signals active): 500 saves took {t_before:.4f}s ({len(jobs)/t_before:.1f} saves/sec)")

    # 2. Measure AFTER (pause_snapshot_signals context manager)
    t0 = time.perf_counter()
    with transaction.atomic():
        with pause_snapshot_signals():
            for j in jobs:
                j.job_title = (j.job_title or '') + ' [TEST]'
                j.save()
        transaction.set_rollback(True)
    t_after = time.perf_counter() - t0
    print(f"AFTER (signals paused):  500 saves took {t_after:.4f}s ({len(jobs)/t_after:.1f} saves/sec)")
    speedup = t_before / t_after if t_after > 0 else 0
    print(f"Speedup: {speedup:.2f}x faster with signals paused!")

if __name__ == '__main__':
    run_benchmark()
