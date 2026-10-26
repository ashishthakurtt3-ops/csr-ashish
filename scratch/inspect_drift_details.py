import os, sys, json, csv
from collections import Counter
sys.path.insert(0, os.getcwd())
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models.job import Job
from modules.admin_panel.models.company import Company

# 1. Load 17:40 backup
with open('data/db_backup_20261019_174028.json', 'r', encoding='utf-8') as f:
    backup_data = json.load(f)

backup_jobs = {}
backup_by_row_id = {}
for it in backup_data:
    if it['model'] == 'admin_panel.job':
        flds = it['fields']
        backup_jobs[flds.get('job_id')] = (it['pk'], flds)
        backup_by_row_id[it['pk']] = flds

print(f"Total jobs in 17:40 backup: {len(backup_jobs)}")

# 2. Load current DB
db_jobs = {j.job_id: j for j in Job.objects.all().select_related('company')}
db_by_row_id = {j.job_row_id: j for j in db_jobs.values()}
print(f"Total jobs in current DB: {len(db_jobs)}")

# 3. Check what happened to backup ACTIVE jobs
active_to_removed = []
active_to_expired = []
active_to_active = []
missing_jobs = []

for j_id, (pk, b_fields) in backup_jobs.items():
    if b_fields.get('status') == 'ACTIVE':
        if j_id in db_jobs:
            curr = db_jobs[j_id]
            if curr.status == 'REMOVED':
                active_to_removed.append(curr)
            elif curr.status == 'EXPIRED':
                active_to_expired.append(curr)
            elif curr.status == 'ACTIVE':
                active_to_active.append(curr)
        elif pk in db_by_row_id:
            curr = db_by_row_id[pk]
            print(f"Job found by pk {pk} but job_id changed! Old: {j_id}, New: {curr.job_id}")
        else:
            missing_jobs.append((j_id, pk, b_fields))

print(f"ACTIVE in backup: {len(backup_jobs)}")
print(f"  -> Stayed ACTIVE: {len(active_to_active)}")
print(f"  -> Changed to REMOVED: {len(active_to_removed)}")
print(f"  -> Changed to EXPIRED: {len(active_to_expired)}")
print(f"  -> Truly Missing / Hard-Deleted: {len(missing_jobs)}")

if missing_jobs:
    print(f"\nMissing jobs breakdown by company:")
    missing_by_comp = Counter(m[2].get('company') for m in missing_jobs)
    for cid, cnt in missing_by_comp.items():
        comp = Company.objects.filter(company_id=cid).first()
        cname = comp.company_name if comp else f"ID {cid}"
        print(f"  Company {cname}: {cnt} jobs")
        sample = [m for m in missing_jobs if m[2].get('company') == cid][0]
        print(f"    Sample: ID={sample[0]}, Title='{sample[2].get('job_title')}', URL='{sample[2].get('application_url')}'")

# 4. Check Apollo Hospitals
print("\n" + "="*50)
print("APOLLO HOSPITALS INVESTIGATION")
apollo = Company.objects.filter(company_name__icontains='Apollo').first()
if apollo:
    print(f"Apollo company_id: {apollo.company_id}, name: {apollo.company_name}")
    apollo_backup = [b[1] for b in backup_jobs.values() if b[1].get('company') == apollo.company_id]
    apollo_curr = Job.objects.filter(company=apollo)
    print(f"Apollo in backup: {len(apollo_backup)} jobs (ACTIVE: {sum(1 for b in apollo_backup if b.get('status')=='ACTIVE')}, REMOVED: {sum(1 for b in apollo_backup if b.get('status')=='REMOVED')})")
    print(f"Apollo in current DB: {apollo_curr.count()} jobs (ACTIVE: {apollo_curr.filter(status='ACTIVE').count()}, REMOVED: {apollo_curr.filter(status='REMOVED').count()})")
    
    # Are the 8 removed Apollo jobs old jobs from backup or what?
    apollo_rem = apollo_curr.filter(status='REMOVED')
    print(f"\nApollo 8 REMOVED jobs:")
    for j in apollo_rem:
        in_b = j.job_id in backup_jobs
        print(f"  Title: {j.job_title} | ID: {j.job_id} | In Backup: {in_b} | URL: {j.application_url}")

    # Why +502 new?
    apollo_new = [j for j in apollo_curr if j.job_id not in backup_jobs]
    print(f"Apollo newly added jobs count: {len(apollo_new)}")
    print(f"Sample new Apollo jobs:")
    for j in apollo_new[:5]:
        print(f"  Title: {j.job_title} | ID: {j.job_id} | URL: {j.application_url}")

# 5. Check 10 examples each for Mahindra, Razorpay, Adani Enterprises among 334 EXPIRED
print("\n" + "="*50)
print("EXPIRED JOBS SAMPLES (10 each for Mahindra, Razorpay, Adani)")
for target_name in ['Mahindra', 'Razorpay', 'Adani']:
    comp = Company.objects.filter(company_name__icontains=target_name).first()
    if comp:
        exp_jobs = Job.objects.filter(company=comp, status='EXPIRED')
        print(f"\n{comp.company_name} (Total Expired: {exp_jobs.count()}):")
        for j in exp_jobs[:10]:
            print(f"  Title: {j.job_title[:35]:<35} | FirstSeen: {str(j.first_seen_at)[:10]} | LastSeen: {str(j.last_seen_at)[:10]} | URL: {j.application_url}")

# 6. Reconcile 85 vs 87 and 64 vs 63
print("\n" + "="*50)
print("RECONCILIATION: 85 vs 87 and 64 vs 63")
# Total removed now = 150.
# In backup: how many REMOVED?
backup_rem_count = sum(1 for b in backup_jobs.values() if b[1].get('status') == 'REMOVED')
print(f"Backup REMOVED count: {backup_rem_count}")
# Let's check status transitions
all_current_rem = Job.objects.filter(status='REMOVED')
print(f"Current DB REMOVED count: {all_current_rem.count()}")
# Of the 150 current removed:
rem_was_in_backup_active = [j for j in all_current_rem if j.job_id in backup_jobs and backup_jobs[j.job_id][1].get('status') == 'ACTIVE']
rem_was_in_backup_rem = [j for j in all_current_rem if j.job_id in backup_jobs and backup_jobs[j.job_id][1].get('status') == 'REMOVED']
rem_was_not_in_backup = [j for j in all_current_rem if j.job_id not in backup_jobs]
print(f"Of the {all_current_rem.count()} currently REMOVED:")
print(f"  Was ACTIVE in backup: {len(rem_was_in_backup_active)}")
print(f"  Was already REMOVED in backup: {len(rem_was_in_backup_rem)}")
print(f"  Not in backup (added & removed during crawl?): {len(rem_was_not_in_backup)}")

