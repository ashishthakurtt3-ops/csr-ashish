from modules.admin_panel.models import Company, Job

print("--- EXAMINING ACC, AMBUJA, AND OTHER COMPANIES ---")
acc = Company.objects.get(company_id='COMP_TOP200_169')
print(f"ACC: careers_url={acc.careers_url}, website_url={acc.website_url}, ats_platform={acc.ats_platform}")

ambuja = Company.objects.get(company_id='COMP_TOP200_082')
print(f"Ambuja: careers_url={ambuja.careers_url}, website_url={ambuja.website_url}, ats_platform={ambuja.ats_platform}")

# Check what jobs were crawled for ACC and Ambuja originally
acc_jobs = Job.objects.filter(company=acc)
print(f"ACC jobs in DB count: {acc_jobs.count()}")
for j in acc_jobs:
    print(f"  {j.job_id} | {j.job_title} | {j.verification_status} | {j.status} | {j.source_url} | {j.evidence_text[:100] if j.evidence_text else ''}")

