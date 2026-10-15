from modules.admin_panel.models import Job

print("--- INSPECTING ORACLE ATS JOBS ACROSS ADANI / ACC / AMBUJA ---")
cids = ['COMP_TOP200_082', 'COMP_TOP200_012', 'COMP_TOP200_013', 'COMP_TOP200_033', 'COMP_TOP200_017', 'COMP_TOP200_039', 'COMP_TOP200_169']

for cid in cids:
    jobs = Job.objects.filter(company_id=cid, status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'])
    print(f"\n=== {cid} ({jobs.first().company.company_name if jobs.exists() else 'N/A'}): {jobs.count()} jobs ===")
    for j in jobs[:5]:
        print(f"  [ID {j.job_row_id}] Title: {j.job_title} | Dept: {j.department} | Loc: {j.location} | ExtID: {j.external_job_id} | AppURL: {j.application_url[:80]}...")
