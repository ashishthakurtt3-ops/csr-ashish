import sqlite3
from collections import Counter

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

# 1. Total rows by verification status
print("=== TOTAL CSR RECORDS BY STATUS ===")
statuses = cur.execute('SELECT verification_status, count(*) FROM admin_panel_csrproject GROUP BY verification_status').fetchall()
for s, c in statuses:
    print(f"  {s}: {c}")

# 2. Pattern analysis in PUBLISHED rows (383 rows)
print("\n=== ANALYSIS OF 383 PUBLISHED RECORDS ===")
pub_rows = cur.execute('SELECT csr_id, company_id, project_name, category, budget, geographic_location, state, source_url FROM admin_panel_csrproject WHERE verification_status = "PUBLISHED"').fetchall()
print(f"Total PUBLISHED: {len(pub_rows)}")

# Check template pattern "Initiative - Company"
template_rows = [r for r in pub_rows if 'Initiative - ' in r[2]]
print(f"  Template 'Initiative - Company' pattern: {len(template_rows)}")

# Check report headings / table fragments (e.g. starts with page number, table header, generic terms)
generic_titles = [
    'social', 'about us', 'sustainability', 'governance', 'stakeholder value created',
    'stakeholder\nvalue created', 'scope 1:', 'scope 2:', 'quick links', 'frequency',
    'purpose of engagement', 'our initiatives', 'area of initiatives', 'career development',
    'women development', 'early career development', 'digital capability development',
    'leadership development', 'reducing carbon emissions', 'want to create the future of medicine?',
    "dr. reddy's - good health can't wait", 'enhancing trust with our stakeholders',
    'tech enabled employee lifecycle assistance', 'ftse4good index series'
]
generic_matches = [r for r in pub_rows if r[2].strip().lower() in generic_titles]
print(f"  Known generic titles/table headers: {len(generic_matches)}")

# Check "rs," budget rows
rs_comma = [r for r in pub_rows if r[4] and 'rs,' in r[4].lower()]
print(f"  Malformed budget 'rs,': {len(rs_comma)}")

# Check budget distribution
budgets = Counter([r[4] for r in pub_rows])
print("\n=== BUDGET VALUES IN PUBLISHED ===")
for b, cnt in budgets.most_common():
    print(f"  {repr(b)}: {cnt}")

# Check location distribution
loc_present = len([r for r in pub_rows if r[5] or r[6]])
print(f"\nLocation present: {loc_present}/{len(pub_rows)} (Missing: {len(pub_rows) - loc_present})")

# Check source URLs
pdf_sources = len([r for r in pub_rows if (r[7] or '').lower().endswith('.pdf')])
html_sources = len([r for r in pub_rows if not (r[7] or '').lower().endswith('.pdf')])
print(f"\nSources: {pdf_sources} PDF sources, {html_sources} HTML sources")
