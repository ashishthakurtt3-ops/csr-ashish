import os, sys, django
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models.company import Company
from modules.admin_panel.models.job import Job
from django.db.models import Count, Q

comps = Company.objects.all()
print(f"Total companies in DB: {comps.count()}")

active_verified_q = Q(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])

comp_stats = []
for c in comps:
    total_jobs = Job.objects.filter(company=c).count()
    active_verified_jobs = Job.objects.filter(company=c).filter(active_verified_q).count()
    comp_stats.append((c.company_id, c.company_name, total_jobs, active_verified_jobs))

# Sort by active_verified_jobs desc
comp_stats.sort(key=lambda x: x[3], reverse=True)

with_active = [c for c in comp_stats if c[3] > 0]
zero_active = [c for c in comp_stats if c[3] == 0]

print(f"Companies with active verified jobs (>0): {len(with_active)}")
print(f"Companies with ZERO active verified jobs (0): {len(zero_active)}")

print("\n--- Companies with Active Verified Jobs ---")
for c in with_active:
    print(f"{c[0]}: {c[1]} -> {c[3]} active verified (total jobs: {c[2]})")

print("\n--- Sample of Companies with 0 Active Verified Jobs ---")
for c in zero_active[:20]:
    print(f"{c[0]}: {c[1]} -> total jobs: {c[2]}")
