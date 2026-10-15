import os
import sys
import django

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.crawler_engine.completeness_service import CompletenessService
from modules.admin_panel.models import (
    Company, Job, CSRProject, CSROpportunity, CompanyCompletenessRegister
)

def sync_and_export():
    print("=" * 80)
    print("SYNCHRONIZING 200-COMPANY COMPLETENESS REGISTER & EXPORTING CSV")
    print("=" * 80)

    # 1. Sync all 200 companies
    registers = CompletenessService.sync_all_200_companies()
    print(f"Synchronized completeness registers for {len(registers)} companies.")

    # 2. Export coverage CSV
    csv_path = os.path.join(BASE_DIR, 'impactbridge_200_company_data_coverage.csv')
    csv_count = CompletenessService.export_csv(csv_path)
    print(f"Exported {csv_count} rows to {csv_path}")

    # 3. Compute authoritative figures
    total_companies = Company.objects.count()
    active_jobs = Job.objects.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
    pub_csr = CSRProject.objects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()
    open_opps = CSROpportunity.objects.filter(status='OPEN', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED', 'EXTRACTED']).count()

    # Company-level coverage counts
    fully_covered = CompanyCompletenessRegister.objects.filter(overall_coverage_status='FULLY_COVERED').count()
    partial = CompanyCompletenessRegister.objects.filter(overall_coverage_status='PARTIAL_COVERAGE').count()
    statutory_only = CompanyCompletenessRegister.objects.filter(overall_coverage_status='STATUTORY_DISCLOSURE_ONLY').count()
    blocked = CompanyCompletenessRegister.objects.filter(overall_coverage_status='ACCESS_RESTRICTED').count()
    pending = CompanyCompletenessRegister.objects.filter(overall_coverage_status='PENDING_DISCOVERY').count()

    # HUL specifics
    hul = Company.objects.get(company_id='COMP_TOP200_009')
    hul_reg = CompanyCompletenessRegister.objects.filter(company=hul).first()

    print("\n" + "=" * 80)
    print("AUTHORITATIVE AUDIT SUMMARY")
    print("=" * 80)
    print(f"Total Canonical Companies: {total_companies}")
    print(f"Active Published Jobs:     {active_jobs}")
    print(f"Published CSR Projects:    {pub_csr}")
    print(f"Open CSR Opportunities:    {open_opps}")
    print(f"\nCoverage Breakdown:")
    print(f"  - FULLY_COVERED:              {fully_covered}")
    print(f"  - PARTIAL_COVERAGE:           {partial}")
    print(f"  - STATUTORY_DISCLOSURE_ONLY:  {statutory_only}")
    print(f"  - ACCESS_RESTRICTED:          {blocked}")
    print(f"  - PENDING_DISCOVERY:          {pending}")
    print(f"\nHindustan Unilever Limited (COMP_TOP200_009):")
    print(f"  - Authoritative CIN:          {hul.cin}")
    print(f"  - Legal Name:                 {hul.legal_name}")
    print(f"  - Registered HQ:              {hul.headquarters}")
    print(f"  - Active Published Jobs:      {hul.jobs.filter(status='ACTIVE', verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()}")
    print(f"  - Quarantined Overseas Jobs:  {hul.jobs.filter(verification_status='QUARANTINED').count()}")
    print(f"  - Published CSR Projects:     {hul.csr_projects.filter(verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']).count()}")

if __name__ == '__main__':
    sync_and_export()
