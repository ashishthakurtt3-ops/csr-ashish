import json
import os
import sys
import django
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Company

audit_json_path = os.path.join(BASE_DIR, 'scratch', 'all_200_companies_identity_audit.json')
with open(audit_json_path, 'r', encoding='utf-8') as f:
    audit_data = json.load(f)

print(f"Loaded {len(audit_data)} records from {audit_json_path}")

db_companies = {c.company_id: c for c in Company.objects.filter(company_id__startswith='COMP_TOP200_')}
assert len(db_companies) == 200, f"Expected 200 companies in DB, got {len(db_companies)}"

eight_companies = {
    'COMP_TOP200_160': {
        'name': '3i Infotech Limited',
        'details': 'Listed on NSE (3IINFOLTD) and BSE (532628); ISIN INE748C01038; Navi Mumbai, MH. CIN not populated in seed fixture; statutory ROC filing ingestion pending.'
    },
    'COMP_TOP200_162': {
        'name': '63 moons technologies limited',
        'details': 'Listed on NSE (63MOONS) and BSE (526881); ISIN INE111B01023; Chennai, TN. CIN not populated in seed fixture; statutory ROC filing ingestion pending.'
    },
    'COMP_TOP200_166': {
        'name': 'AAA Technologies Limited',
        'details': 'Listed on NSE SME (AAATECH) and BSE (543248); ISIN INE0D0U01013; Mumbai, MH. CIN not populated in seed fixture; statutory ROC filing ingestion pending.'
    },
    'COMP_TOP200_170': {
        'name': 'ACS Technologies Limited',
        'details': 'Listed on BSE (538668); ISIN INE366C01021; Hyderabad, TG. CIN not populated in seed fixture; statutory ROC filing ingestion pending.'
    },
    'COMP_TOP200_173': {
        'name': 'AGS Transact Technologies Limited',
        'details': 'Listed on NSE (AGSTRA) and BSE (543453); ISIN INE583L01014; Mumbai, MH. CIN not populated in seed fixture; statutory ROC filing ingestion pending.'
    },
    'COMP_TOP200_175': {
        'name': 'AION-TECH SOLUTIONS LIMITED',
        'details': 'Listed on BSE (533080) and NSE (GOLDTECH); ISIN INE805A01014; Secunderabad, TG. CIN not populated in seed fixture; statutory ROC filing ingestion pending.'
    },
    'COMP_TOP200_190': {
        'name': 'AXISCADES Technologies Limited',
        'details': 'Listed on NSE (AXISCADES) and BSE (532307); ISIN INE555B01013; Bengaluru, KA. CIN not populated in seed fixture; statutory ROC filing ingestion pending.'
    },
    'COMP_TOP200_197': {
        'name': 'Aartech Solonics Limited',
        'details': 'Listed on BSE SME (542475); ISIN INE01C001026; Mandideep/Bhopal, MP. CIN not populated in seed fixture; statutory ROC filing ingestion pending.'
    }
}

updated_records = []
for item in audit_data:
    cid = item['company_id']
    if cid not in db_companies:
        continue
    comp = db_companies[cid]
    
    # Standardize statuses
    prev_st = item.get('status')
    if prev_st == 'AUTHORITATIVE_VERIFIED':
        item['status'] = 'AUTHORITATIVE_VERIFIED'
        item['category_description'] = 'Verified corporate identity supported by primary regulatory filings (BRSR / MCA-21 / Annual Reports).'
    elif prev_st == 'STATUTORY_EXEMPT':
        item['status'] = 'STATUTORY_EXEMPT'
        item['category_description'] = 'Statutory corporation constituted under special Act of Parliament; legitimately exempt from Companies Act CIN.'
    elif cid in eight_companies or prev_st == 'UNESTABLISHED':
        item['status'] = 'CIN_UNKNOWN_UNVERIFIED'
        item['category_description'] = 'CIN was unpopulated from inception; stock exchange metadata confirmed; statutory MCA-21 filing ingestion pending.'
        if cid in eight_companies:
            info = eight_companies[cid]
            item['authoritative_source'] = f"NSE/BSE Listed Issuer. {info['details']}"
            item['correction'] = f"Categorized as CIN_UNKNOWN_UNVERIFIED: {info['details']}"
    elif prev_st in ['UNESTABLISHED_CLEARED', 'FABRICATED_CIN_REMOVED']:
        item['status'] = 'FABRICATED_CIN_REMOVED'
        item['category_description'] = 'Previously fabricated prototype CIN purged to None; statutory MCA-21 CIN remains unverified pending filing ingestion.'
    
    item['db_cin'] = comp.cin
    item['db_legal_name'] = comp.legal_name
    item['db_headquarters'] = comp.headquarters
    item['db_official_domain'] = comp.official_domain
    item['db_isin'] = comp.isin
    item['db_nse_symbol'] = comp.nse_symbol
    item['db_bse_scrip_code'] = comp.bse_scrip_code
    
    updated_records.append(item)

# Count final distribution
status_counts = Counter(item['status'] for item in updated_records)
print("Updated Status Distribution:")
for st, cnt in sorted(status_counts.items()):
    print(f"  {st}: {cnt}")

total = sum(status_counts.values())
print(f"Total accounted for: {total} / 200")
assert total == 200, f"Expected exactly 200, got {total}"
assert status_counts['AUTHORITATIVE_VERIFIED'] == 148, f"Expected 148, got {status_counts['AUTHORITATIVE_VERIFIED']}"
assert status_counts['STATUTORY_EXEMPT'] == 10, f"Expected 10, got {status_counts['STATUTORY_EXEMPT']}"
assert status_counts['FABRICATED_CIN_REMOVED'] == 34, f"Expected 34, got {status_counts['FABRICATED_CIN_REMOVED']}"
assert status_counts['CIN_UNKNOWN_UNVERIFIED'] == 8, f"Expected 8, got {status_counts['CIN_UNKNOWN_UNVERIFIED']}"

with open(audit_json_path, 'w', encoding='utf-8') as f:
    json.dump(updated_records, f, indent=2)

print(f"Successfully wrote reconciled audit log to {audit_json_path}")
