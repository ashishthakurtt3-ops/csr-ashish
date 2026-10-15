import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, Contact, CompanyCompletenessRegister

client = Client()

print("=" * 80)
print("RUNNING COMPREHENSIVE VIEW & INTELLIGENCE VERIFICATION")
print("=" * 80)

# 1. Test Company Registry Coverage
total_companies = Company.objects.count()
total_registers = CompanyCompletenessRegister.objects.count()
print(f"Total Companies in Registry: {total_companies}")
print(f"Total Completeness Register Entries: {total_registers}")
assert total_companies == 200, f"Expected 200 companies, found {total_companies}"
assert total_registers == 200, f"Expected 200 registers, found {total_registers}"

# 2. Test Representative Companies
test_cids = [
    "COMP_TOP200_002", # TCS
    "COMP_TOP200_009", # HUL
    "COMP_TOP200_051", # Siemens
    "COMP_TOP200_082", # Ambuja Cements
    "COMP_TOP200_169", # ACC
    "COMP_TOP200_174", # Fortis Healthcare
]

for cid in test_cids:
    comp = Company.objects.get(company_id=cid)
    resp = client.get(f"/companies/{cid}/dossier")
    assert resp.status_code == 200, f"Dossier failed for {cid}: {resp.status_code}"
    data = resp.json()

    # Section 1 & 2: Company Header & Overview
    c_info = data.get("company", {})
    assert c_info.get("company_name") == comp.company_name
    assert c_info.get("company_id") == cid
    print(f"\n[OK] Company {cid} - {comp.company_name}:")
    print(f"     Apex Domain: {c_info.get('apex_domain')}")
    print(f"     Sector: {c_info.get('sector')}")
    print(f"     Headquarters: {c_info.get('headquarters') or 'Not provided by source'}")

    # Section 3: Intelligence Summary (7 cards)
    summary = data.get("intelligence_summary", {})
    assert "eligible_published_jobs" in summary
    assert "verified_csr_projects" in summary
    assert "open_opportunities" in summary
    assert "published_contacts" in summary
    assert "available_reports" in summary
    assert "last_source_check" in summary
    assert "overall_coverage_status" in summary
    print(f"     Summary: {summary['eligible_published_jobs']} jobs ({summary['jobs_status']}), "
          f"{summary['verified_csr_projects']} CSR ({summary['csr_status']}), "
          f"{summary['open_opportunities']} opps, {summary['published_contacts']} contacts, "
          f"{summary['available_reports']} reports. Status: {summary['overall_coverage_status']}")

    # Section 9: Official Reports & Documents
    reports = data.get("official_reports", [])
    print(f"     Official Reports catalogued: {len(reports)}")
    for r in reports[:2]:
        print(f"       - {r['title']} [{r['document_type']}]: {r['source_url']}")

    # Section 10: Sources & Verification (4 pillars)
    audit = data.get("coverage_audit", {})
    assert "corporate_profile_status" in audit
    assert "careers_source_status" in audit
    assert "ats_platform" in audit
    assert "csr_status" in audit
    print(f"     ATS Platform: {audit.get('ats_platform')} (Status: {audit.get('careers_source_status')})")

    # Check zero vs published jobs logic
    jobs = data.get("jobs", [])
    if len(jobs) == 0:
        assert summary["jobs_status"] in ["VERIFIED_ZERO_JOBS", "NO_RECORDS_CONFIRMED", "PENDING", "FAILED"], \
            f"Unexpected jobs_status {summary['jobs_status']} for 0 jobs"
        print(f"     Confirmed 0 jobs with status: {summary['jobs_status']}")
    else:
        print(f"     Found {len(jobs)} active verified jobs.")

# 3. Test Universal Job Details View & Scoped Related Jobs
print("\n" + "=" * 80)
print("TESTING UNIVERSAL JOB DETAILS AND STRICT SAME-COMPANY RELATED JOBS")
print("=" * 80)

sample_jobs = Job.objects.filter(
    verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'],
    status='ACTIVE'
)[:10]

for job in sample_jobs:
    resp = client.get(f"/api/jobs/{job.job_id}/")
    assert resp.status_code == 200, f"Job detail failed for {job.job_id}: {resp.status_code}"
    res_json = resp.json()
    jdata = res_json.get("job") or res_json

    # Check Key Metadata
    assert jdata.get("job_id") == job.job_id
    assert jdata.get("company_id") == job.company_id
    assert jdata.get("company_name") == job.company.company_name
    assert jdata.get("application_url") == job.application_url

    # Check Related Jobs strictly scoped to SAME company
    related = res_json.get("related_jobs", [])
    for rjob in related:
        assert rjob.get("company_id") == job.company_id, \
            f"LEAK DETECTED: Related job {rjob.get('job_id')} has company {rjob.get('company_id')} != {job.company_id}"

    print(f"[OK] Job {job.job_id} ({job.job_title[:35]}...) at {job.company.company_name[:25]}: {len(related)} strictly-same-employer related jobs.")

print("\n" + "=" * 80)
print("ALL BACKEND INTEGRITY AND STANDARDIZATION TESTS PASSED 100%!")
print("=" * 80)
