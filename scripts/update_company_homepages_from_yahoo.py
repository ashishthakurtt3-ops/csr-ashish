"""
Update ONLY Company Homepage URLs in MySQL Using Yahoo Finance Data.
Strict scope: Updates ONLY the `website_url` column in `admin_panel_company`.
No other columns, tables, or records are touched.
"""
import os
import sys
import csv
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('modules'))
import django
django.setup()

from django.db import transaction, connection
from modules.admin_panel.models import Company


def run_homepage_update(dry_run=True):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_source_path = 'reports/stage1a_shortcut/manual_url_review_all_companies.csv'
    
    if not os.path.exists(csv_source_path):
        print(f"ERROR: Source file {csv_source_path} not found! Stopping.", flush=True)
        return

    print("=== STEP 1: INSPECT SOURCE FILE & DATABASE RECORDS ===", flush=True)
    with open(csv_source_path, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)

    print(f"Total rows in CSV: {len(csv_rows)}", flush=True)
    total_db_companies = Company.objects.count()
    print(f"Total companies in database: {total_db_companies}", flush=True)

    # Verify 1-to-1 mapping
    csv_cids = [r['Company ID'].strip() for r in csv_rows]
    if len(csv_cids) != len(set(csv_cids)):
        print("ERROR: Duplicate Company IDs found in CSV! Stopping.", flush=True)
        return

    db_companies_dict = {c.company_id: c for c in Company.objects.all()}
    missing_in_db = [cid for cid in csv_cids if cid not in db_companies_dict]
    if missing_in_db:
        print(f"ERROR: Company IDs in CSV not found in DB: {missing_in_db}! Stopping.", flush=True)
        return

    missing_in_csv = [cid for cid in db_companies_dict if cid not in csv_cids]
    if missing_in_csv:
        print(f"ERROR: Company IDs in DB not found in CSV: {missing_in_csv}! Stopping.", flush=True)
        return

    print("Verified: Perfect 1-to-1 match between CSV and MySQL database records (201 companies).", flush=True)

    print("\n=== STEP 2: CREATE TIMESTAMPED BACKUP OF CURRENT HOMEPAGE URLS ===", flush=True)
    os.makedirs('exports/backups', exist_ok=True)
    backup_json_path = f"exports/backups/company_homepage_urls_backup_{timestamp}.json"
    backup_csv_path = f"exports/backups/company_homepage_urls_backup_{timestamp}.csv"

    backup_data = []
    for c in Company.objects.order_by('company_id'):
        backup_data.append({
            'company_id': c.company_id,
            'company_name': c.company_name,
            'website_url': c.website_url,
            'website_url_status': c.website_url_status,
            'official_domain': c.official_domain
        })

    with open(backup_json_path, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'total_companies': len(backup_data),
            'companies': backup_data
        }, f, indent=2)

    with open(backup_csv_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Company ID', 'Company Name', 'Current Homepage URL', 'Website URL Status', 'Official Domain'])
        for r in backup_data:
            writer.writerow([r['company_id'], r['company_name'], r['website_url'], r['website_url_status'], r['official_domain']])

    print(f"Backup created: {backup_json_path} and {backup_csv_path}", flush=True)

    print("\n=== STEP 3: PREPARE UPDATE AND SKIP LISTS ===", flush=True)
    to_update = []
    to_skip = []

    for r in csv_rows:
        cid = r['Company ID'].strip()
        cname = r['Company Name'].strip()
        raw_yahoo = r['Yahoo Finance Website URL'].strip()
        db_comp = db_companies_dict[cid]
        current_url = db_comp.website_url

        if not raw_yahoo or raw_yahoo == 'NOT COLLECTED':
            to_skip.append({
                'company_id': cid,
                'company_name': cname,
                'current_url': current_url,
                'proposed_url': None,
                'action': 'SKIP',
                'reason': 'Yahoo Finance URL is NOT COLLECTED'
            })
        else:
            # Clean export serialization escapes if any
            clean_url = raw_yahoo.replace(r'\/', '/').replace(r'\:', ':').replace(r'\.', '.')
            to_update.append({
                'company_id': cid,
                'company_name': cname,
                'current_url': current_url,
                'proposed_url': clean_url,
                'action': 'UPDATE',
                'reason': 'Valid Yahoo Finance Website URL'
            })

    print(f"Companies to UPDATE: {len(to_update)}", flush=True)
    print(f"Companies to SKIP: {len(to_skip)}", flush=True)

    # Dry-run report
    os.makedirs('reports/stage1a_shortcut', exist_ok=True)
    dry_run_csv = f"reports/stage1a_shortcut/company_homepage_update_plan_{timestamp}.csv"
    with open(dry_run_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Company ID', 'Company Name', 'Action', 'Current Homepage URL', 'Proposed Yahoo Finance URL', 'Reason'])
        for item in to_update:
            writer.writerow([item['company_id'], item['company_name'], item['action'], item['current_url'], item['proposed_url'], item['reason']])
        for item in to_skip:
            writer.writerow([item['company_id'], item['company_name'], item['action'], item['current_url'], item['proposed_url'], item['reason']])

    print(f"Dry-run plan saved to: {dry_run_csv}", flush=True)

    print("\nThe 8 Companies to be SKIPPED (untouched):", flush=True)
    for s in to_skip:
        print(f"  - {s['company_id']}: {s['company_name']} (Current: {s['current_url']})", flush=True)

    if dry_run:
        print("\n[DRY RUN COMPLETE] No database records modified. Run with --execute to apply changes.", flush=True)
        return

    print("\n=== STEP 4: EXECUTE TARGETED SQL UPDATE IN TRANSACTION ===", flush=True)
    # Record full row snapshots before update to verify NO other column changes
    pre_update_snapshots = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM admin_panel_company")
        col_names = [desc[0] for desc in cursor.description]
        url_idx = col_names.index('website_url')
        cid_idx = col_names.index('company_id')
        for row in cursor.fetchall():
            pre_update_snapshots[row[cid_idx]] = row

    update_success_count = 0
    with transaction.atomic():
        for item in to_update:
            # Direct SQL targeted update of ONLY website_url
            rows_affected = Company.objects.filter(company_id=item['company_id']).update(website_url=item['proposed_url'])
            if rows_affected == 1:
                update_success_count += 1
            else:
                raise RuntimeError(f"Unexpected row update count ({rows_affected}) for {item['company_id']}")

    print(f"Transaction committed successfully! {update_success_count} companies updated.", flush=True)

    print("\n=== STEP 5: POST-UPDATE VERIFICATION ===", flush=True)
    post_update_snapshots = {}
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM admin_panel_company")
        col_names = [desc[0] for desc in cursor.description]
        url_idx = col_names.index('website_url')
        cid_idx = col_names.index('company_id')
        for row in cursor.fetchall():
            post_update_snapshots[row[cid_idx]] = row

    # 1. Verify updated records match expected Yahoo URLs
    mismatches = []
    for item in to_update:
        cid = item['company_id']
        expected_url = item['proposed_url']
        actual_url = post_update_snapshots[cid][url_idx]
        if actual_url != expected_url:
            mismatches.append((cid, item['company_name'], expected_url, actual_url))

    if mismatches:
        print(f"ERROR: {len(mismatches)} mismatches detected!", flush=True)
        for m in mismatches:
            print("  Mismatch:", m, flush=True)
    else:
        print(f"Verification PASS: All {update_success_count} updated records exactly match Yahoo Finance URLs.", flush=True)

    # 2. Verify skipped records remained completely untouched
    skip_failures = []
    for s in to_skip:
        cid = s['company_id']
        pre_row = pre_update_snapshots[cid]
        post_row = post_update_snapshots[cid]
        if pre_row != post_row:
            skip_failures.append((cid, s['company_name']))

    if skip_failures:
        print(f"ERROR: Skipped records were modified: {skip_failures}", flush=True)
    else:
        print(f"Verification PASS: All {len(to_skip)} skipped records remained completely untouched.", flush=True)

    # 3. Verify NO other columns were modified across all 201 records
    other_col_modifications = []
    for cid, pre_row in pre_update_snapshots.items():
        post_row = post_update_snapshots[cid]
        for col_i, col_name in enumerate(col_names):
            if col_name == 'website_url':
                continue
            if pre_row[col_i] != post_row[col_i]:
                other_col_modifications.append((cid, col_name, pre_row[col_i], post_row[col_i]))

    if other_col_modifications:
        print(f"ERROR: Unrelated columns were modified: {other_col_modifications[:5]}", flush=True)
    else:
        print("Verification PASS: Exactly 0 unrelated columns modified across all 201 company records.", flush=True)

    print("\n=== SUMMARY ===", flush=True)
    print(f"Total Companies: 201", flush=True)
    print(f"Successfully Updated: {update_success_count}", flush=True)
    print(f"Untouched / Skipped: {len(to_skip)}", flush=True)
    print(f"Failures / Mismatches: {len(mismatches)}", flush=True)


if __name__ == '__main__':
    dry_run = '--execute' not in sys.argv
    run_homepage_update(dry_run=dry_run)

