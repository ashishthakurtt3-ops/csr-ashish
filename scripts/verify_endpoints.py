import hashlib, os, sys, django, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client

client = Client()

def sha256_file(fn):
    h = hashlib.sha256()
    with open(fn, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

print("======================================================================")
print("1. DATABASE HASH INTEGRITY CHECK")
print("======================================================================")
for f in ['db.sqlite3', 'db.sqlite3.backup_20261010_134144', 'db.sqlite3.audit_checkpoint_20261010']:
    if os.path.exists(f):
        print(f"{f}:")
        print(f"  SHA-256: {sha256_file(f)}")
        print(f"  Size   : {os.path.getsize(f):,} bytes")

print("\n======================================================================")
print("2. CSR PROJECT CATEGORY API FILTERS (/csr/projects?category=...)")
print("======================================================================")
cats = [
    ('all', ''),
    ('environment', 'environment'),
    ('education', 'education'),
    ('others', 'others'),
    ('women', 'women'),
    ('healthcare', 'healthcare'),
    ('uncategorized', 'uncategorized'),
]
for label, cat_param in cats:
    url = f"/csr/projects?limit=500" if not cat_param else f"/csr/projects?category={cat_param}&limit=500"
    r = client.get(url)
    data = r.json()
    count = len(data) if isinstance(data, list) else (data.get('total') or len(data.get('results', [])))
    print(f"Category [{label:<14}]: HTTP {r.status_code} | Count: {count}")

print("\n======================================================================")
print("3. CSR OPPORTUNITIES SCOPED API (/csr/opportunities?scope=...)")
print("======================================================================")
scopes = [
    ('Default (CSR-only)', ''),
    ('scope=csr', 'csr'),
    ('scope=procurement', 'procurement'),
    ('scope=all', 'all'),
]
for label, scope_param in scopes:
    url = "/csr/opportunities?limit=500" if not scope_param else f"/csr/opportunities?scope={scope_param}&limit=500"
    r = client.get(url)
    data = r.json()
    items = data if isinstance(data, list) else data.get('results', [])
    count = len(items)
    types = [item.get('opportunity_type') for item in items]
    print(f"Scope [{label:<20}]: HTTP {r.status_code} | Count: {count} | Types: {set(types)}")

print("\n======================================================================")
print("4. OPPORTUNITIES CSV EXPORT INTEGRITY")
print("======================================================================")
for scope in ['csr', 'procurement', 'all']:
    r = client.get(f"/csr/opportunities?scope={scope}&format=csv")
    lines = r.content.decode('utf-8').strip().split('\n')
    rows = len(lines) - 1 if len(lines) > 1 else 0
    header = lines[0] if lines else ''
    cd = r.headers.get('Content-Disposition')
    print(f"CSV Export [scope={scope:<11}]: HTTP {r.status_code} | Data Rows: {rows} | Header Columns: {len(header.split(','))}")

print("\n======================================================================")
print("5. PLATFORM STATS / METRICS (/stats)")
print("======================================================================")
r = client.get('/stats')
if r.status_code == 200:
    data = r.json()
    print(f"HTTP {r.status_code}")
    print(f"  csr_projects            : {data.get('csr_projects')}")
    print(f"  total_companies         : {data.get('total_companies')}")
    print(f"  crawled_companies       : {data.get('crawled_companies')}")
    print(f"  contacts_extracted      : {data.get('contacts_extracted')}")
    print(f"  active_opportunities    : {data.get('active_opportunities')}")
    print(f"  total_csr_budget_cr     : {data.get('total_csr_budget_cr')}")
    print(f"  statutory_csr_budget_cr : {data.get('statutory_csr_budget_cr')}")
    print(f"  sustainability_outlay_cr: {data.get('sustainability_outlay_cr')}")
    print(f"  sustainability details  : {json.dumps(data.get('sustainability_outlay_details'), indent=4)}")
else:
    print(f"Failed HTTP {r.status_code}: {r.content}")
