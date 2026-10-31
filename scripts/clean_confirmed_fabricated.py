"""
Safe, transaction-wrapped cleanup of confirmed fabricated records.
Exports complete audit trail before deletion.
Supports --dry-run flag.
"""
import os
import sys
import json
import csv
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
import django
django.setup()

from django.db import transaction
from modules.admin_panel.models import Job, CSRProject, CSROpportunity, Company
from modules.admin_panel.verification import is_defective_job_record
from modules.admin_panel.signals import pause_snapshot_signals


def classify_job_for_cleanup(j):
    title = (j.job_title or '').strip()
    url = (j.application_url or '').strip()
    src = (j.source_url or '').strip()
    comp = j.company.company_name if j.company else ''

    # 1. Confirmed Fabricated / Scraped Non-Job patterns:
    # A. Apollo Hospitals - 100% of records are patient surgical procedures, hospital branch directories, or doctor appointment booking pages
    if 'Apollo Hospitals' in comp:
        return 'CONFIRMED_FABRICATED', 'Apollo Hospitals patient medical procedure, branch hospital directory, or doctor appointment booking page', True

    # B. Yes Bank Oracle IDCS CMS article nodes
    if 'Yes Bank' in comp and ('/sites/web/ui/idcs' in url or 'yes.bank.in' in url):
        return 'CONFIRMED_FABRICATED', 'Yes Bank Oracle CMS content node scraped due to ?job_id query parameter', True

    # C. CG Power industrial variable frequency drives product catalog
    if 'CG Power' in comp and ('api/products' in url or 'cgglobal_backend' in url or title.startswith('Emotron') or title == 'Consumer Products'):
        return 'CONFIRMED_FABRICATED', 'CG Power industrial variable speed drives product catalog item', True

    # D. ONGC accessibility screen-reader software links and recruitment exam results notices
    if 'Oil & Natural Gas' in comp and any(k in (url + src) for k in ['vispero', 'yourdolphin', 'freedomscientific', 'webanywhere', 'screenreader', 'satogo', 'nvda-project', 'documents/', 'web/eng/detail']):
        return 'CONFIRMED_FABRICATED', 'ONGC accessibility screen-reader link or recruitment exam result notice', True

    # E. HDFC AMC mutual fund investment planning calculators
    if 'HDFC Asset' in comp and 'calculators/' in url:
        return 'CONFIRMED_FABRICATED', 'HDFC AMC mutual fund financial planning calculator', True

    # F. Executive leadership biography pages
    if any(k in url for k in ['leadership-team/mr-', 'leadership-team/ms-']):
        return 'CONFIRMED_FABRICATED', 'Executive director leadership biography page', True

    # G. Indian Hotels brand domains, supplier portals, and financial transparency PDFs
    if 'Indian Hotels' in comp and any(k in (url + src) for k in [
        'utsav.gov.in', 'nidhi.tourism.gov.in', 'saathi.qcin.org', 'IHCL-Tax-Transparency',
        'suppliers', 'accessibility', 'policies', 'esg-profile', 'taj-public-service',
        'ihcltata-subscription', 'gingerhotels.com', 'vivantahotels.com', 'gateway-hotels.com',
        'hotelclarks.com', 'seleqtionshotels.com', 'brijhotels.com', 'atmantan.com',
        'claridges.com', 'tajsats.com', 'soulinaire.com', 'qmin.co.in', 'amastaysandtrails.com',
        'treeofliferesorts.com'
    ]):
        return 'CONFIRMED_FABRICATED', 'Indian Hotels brand domain, supplier portal, or tax transparency PDF', True

    # H. Defective UI navigation tokens & boilerplate
    if is_defective_job_record(title, url, src):
        return 'CONFIRMED_FABRICATED', f'Defective website navigation token or UI boilerplate: {title[:40]}', True

    # I. Corporate marketing, vendor widgets, non-career URLs
    if any(k in (url + src) for k in [
        '/what-we-do/', '/services/', '/industries/', 'case-study', 'case-studies',
        'diageoindia.com/en/careers/life-at-diageo', 'opportunities-at-diageo', 'edgeverve.com', 'pminternship.mca.gov.in',
        'consent/cookie_banner', 'hcmRestApi/resources/latest/recruitingCEUser',
        'lloyds.in/about-us/committees', 'cms.aadharhousing.com', 'avglogistics.com/leadership',
        'remember.techmahindra.com', 'salesiq.zohopublic.in'
    ]):
        return 'CONFIRMED_FABRICATED', 'Corporate marketing, vendor widget, or non-career landing page', True

    # 2. Genuine exceptions in inactive/quarantined:
    if j.job_row_id in (6719, 6713) or ('jobs.lever.co/paytm' in url):
        if j.status == 'ACTIVE':
            return 'GENUINE_ACTIVE', 'Active verified Paytm vacancy on Lever ATS', False
        return 'GENUINE_UNVERIFIED', 'Genuine Paytm technical engineering vacancy on Lever ATS', False

    if j.job_row_id in (10501, 10493, 10485) or ('jobs.whirlpool.com' in url and any(k in title for k in ['Gestionnaire', 'Gerente', 'Senior Finance Manager'])):
        if j.status == 'ACTIVE':
            return 'GENUINE_ACTIVE', 'Active verified Whirlpool opening', False
        return 'GENUINE_UNVERIFIED', 'Genuine Whirlpool career opening on official career portal', False

    if 'Samvardhana Motherson' in comp and 'careers.motherson.com/en/job/' in url:
        if j.status == 'ACTIVE':
            return 'GENUINE_ACTIVE', 'Active verified Samvardhana Motherson vacancy', False
        return 'GENUINE_UNVERIFIED', 'Genuine Samvardhana Motherson international manufacturing opening', False

    # J. Non-job corporate pages in INACTIVE or REJECTED
    if j.status == 'INACTIVE' or j.verification_status == 'REJECTED':
        return 'CONFIRMED_FABRICATED', f'Non-job corporate page or administrative link: {title[:40]}', True

    # 3. Genuine Job Postings:
    if j.status == 'ACTIVE':
        return 'GENUINE_ACTIVE', 'Active verified job posting on official careers portal', False
    elif j.status in ('EXPIRED', 'STALE') or j.status == 'REMOVED':
        return 'GENUINE_EXPIRED', 'Genuine job posting that has expired or rotated off', False
    else:
        return 'GENUINE_UNVERIFIED', f'Genuine job posting currently marked {j.status}/{j.verification_status}', False


def classify_opp_for_cleanup(o):
    title = (o.title or '').strip()
    url = (o.portal_url or o.source_url or '').strip()
    
    # 1. Cloned with Google text fragments
    if '#:~:text=' in url:
        return 'CONFIRMED_FABRICATED', 'Cloned from CSR project using Google text fragment of privacy/terms page', True
        
    # 2. Cloned from PDF statutory report
    if o.opportunity_type == 'CSR Grant / Program' and any(url.lower().endswith(ext) for ext in ['.pdf', '.pdf/']):
        return 'CONFIRMED_FABRICATED', 'Cloned from statutory annual report PDF with no open RFP or application mechanism', True
        
    # 3. Marked INVALID_SYNTHETIC in migration 0013 with synthetic prefix
    if o.status == 'INVALID_SYNTHETIC' and any(title.startswith(p) for p in ['CSR Initiative:', 'CSR Statutory Partnership:']):
        return 'CONFIRMED_FABRICATED', 'Synthetic opportunity cloned from CSR project with no submission deadline', True

    return 'GENUINE_OPPORTUNITY', 'Genuine CSR opportunity', False


def run_audit_and_cleanup(dry_run=True):
    print(f"=== RUNNING AUDIT AND CLEANUP (dry_run={dry_run}) ===", flush=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs('reports/audit', exist_ok=True)

    # 1. Baseline counts
    total_jobs_before = Job.objects.count()
    total_projects_before = CSRProject.objects.count()
    total_opps_before = CSROpportunity.objects.count()
    print(f"Baseline: Jobs={total_jobs_before}, CSRProjects={total_projects_before}, CSROpportunities={total_opps_before}", flush=True)

    # 2. Audit Jobs
    jobs_to_delete = []
    jobs_to_preserve = []
    for j in Job.objects.select_related('company').all():
        cls_name, reason, is_fab = classify_job_for_cleanup(j)
        item = {
            'id': j.job_row_id,
            'company': j.company.company_name if j.company else '',
            'title': j.job_title,
            'url': j.application_url,
            'status': j.status,
            'verification_status': j.verification_status,
            'classification': cls_name,
            'reason': reason
        }
        if is_fab:
            jobs_to_delete.append(item)
        else:
            jobs_to_preserve.append(item)

    # 3. Audit CSROpportunities
    opps_to_delete = []
    opps_to_preserve = []
    for o in CSROpportunity.objects.select_related('company').all():
        cls_name, reason, is_fab = classify_opp_for_cleanup(o)
        item = {
            'id': o.opp_id,
            'company': o.company.company_name if o.company else '',
            'title': o.title,
            'url': o.portal_url or o.source_url,
            'status': o.status,
            'verification_status': o.verification_status,
            'classification': cls_name,
            'reason': reason
        }
        if is_fab:
            opps_to_delete.append(item)
        else:
            opps_to_preserve.append(item)

    # 4. Audit CSRProjects (All 1,591 genuine)
    projects_to_delete = []
    projects_to_preserve = [
        {
            'id': p.csr_id,
            'company': p.company.company_name if p.company else '',
            'project_name': p.project_name,
            'budget': p.budget,
            'source_url': p.source_url
        }
        for p in CSRProject.objects.select_related('company').all()
    ]

    print(f"\nAudit Results:", flush=True)
    print(f"Jobs: Confirmed Fabricated={len(jobs_to_delete)}, Preserved={len(jobs_to_preserve)}", flush=True)
    print(f"CSROpportunities: Confirmed Fabricated={len(opps_to_delete)}, Preserved={len(opps_to_preserve)}", flush=True)
    print(f"CSRProjects: Confirmed Fabricated={len(projects_to_delete)}, Preserved={len(projects_to_preserve)}", flush=True)

    # Breakdown of preserved jobs
    pres_counts = {}
    for r in jobs_to_preserve:
        c = r['classification']
        pres_counts[c] = pres_counts.get(c, 0) + 1
    print(f"Preserved Jobs Breakdown: {pres_counts}", flush=True)

    # Export audit files
    audit_json_path = f"reports/audit/confirmed_fabricated_records_{timestamp}.json"
    audit_csv_path = f"reports/audit/confirmed_fabricated_records_{timestamp}.csv"

    all_deleted_records = [
        {**r, 'entity': 'Job'} for r in jobs_to_delete
    ] + [
        {**r, 'entity': 'CSROpportunity'} for r in opps_to_delete
    ]

    with open(audit_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'dry_run': dry_run,
            'summary': {
                'jobs_before': total_jobs_before,
                'jobs_deleted': len(jobs_to_delete),
                'jobs_preserved': len(jobs_to_preserve),
                'opps_before': total_opps_before,
                'opps_deleted': len(opps_to_delete),
                'opps_preserved': len(opps_to_preserve),
                'projects_before': total_projects_before,
                'projects_deleted': 0,
                'projects_preserved': len(projects_to_preserve)
            },
            'deleted_records': all_deleted_records
        }, f, indent=2)

    with open(audit_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Entity', 'ID', 'Company', 'Title', 'URL', 'Status', 'Reason'])
        for r in all_deleted_records:
            writer.writerow([r['entity'], r['id'], r['company'], r['title'], r['url'], r['status'], r['reason']])

    print(f"Audit log saved to {audit_json_path} and {audit_csv_path}", flush=True)

    if dry_run:
        print("\n[DRY RUN] No database records modified. Use --execute to commit cleanup.", flush=True)
        return

    # 5. Execute Cleanup inside atomic transaction with paused signals
    print("\nExecuting database cleanup in atomic transaction with paused signals...", flush=True)
    with pause_snapshot_signals():
        with transaction.atomic():
            job_del_ids = [r['id'] for r in jobs_to_delete]
            opp_del_ids = [r['id'] for r in opps_to_delete]

            # Fast chunked deletion using raw sql or in_bulk to avoid signal overhead
            from django.db import connection
            with connection.cursor() as cursor:
                # Delete jobs in chunks of 500 to keep queries responsive
                chunk_size = 500
                total_job_del = 0
                for i in range(0, len(job_del_ids), chunk_size):
                    chunk = job_del_ids[i:i + chunk_size]
                    placeholders = ','.join(['%s'] * len(chunk))
                    cursor.execute(f"DELETE FROM admin_panel_job WHERE job_row_id IN ({placeholders})", chunk)
                    total_job_del += cursor.rowcount

                # Delete opportunities
                total_opp_del = 0
                for i in range(0, len(opp_del_ids), chunk_size):
                    chunk = opp_del_ids[i:i + chunk_size]
                    placeholders = ','.join(['%s'] * len(chunk))
                    cursor.execute(f"DELETE FROM admin_panel_csropportunity WHERE opp_id IN ({placeholders})", chunk)
                    total_opp_del += cursor.rowcount

            # Update genuine unverified and expired jobs to consistent statuses
            Job.objects.filter(status='REMOVED', is_defective=False).update(status='EXPIRED', verification_status='STALE')
            preserved_unverified_ids = [r['id'] for r in jobs_to_preserve if r['classification'] == 'GENUINE_UNVERIFIED']
            Job.objects.filter(job_row_id__in=preserved_unverified_ids).update(status='UNVERIFIED', verification_status='UNVERIFIED', is_defective=False)

    print(f"Successfully deleted {total_job_del} job rows and {total_opp_del} opportunity rows.", flush=True)
    print(f"Database row counts after cleanup:", flush=True)
    print(f"  Jobs: {Job.objects.count()}", flush=True)
    print(f"  CSRProjects: {CSRProject.objects.count()}", flush=True)
    print(f"  CSROpportunities: {CSROpportunity.objects.count()}", flush=True)


if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv
    run_audit_and_cleanup(dry_run=dry_run)
