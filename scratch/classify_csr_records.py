import sqlite3, re
from collections import Counter

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

rows = cur.execute('SELECT csr_id, company_id, project_name, category, budget, geographic_location, source_url, description FROM admin_panel_csrproject WHERE verification_status = "PUBLISHED"').fetchall()

print(f"Total currently published: {len(rows)}")

template_count = 0
unparsed_pdf_header = 0
single_word_or_header = 0
general_corporate = 0
genuine_looking = 0

samples_genuine = []
samples_junk = []

generic_list = [
    'social', 'about us', 'sustainability', 'governance', 'stakeholder value created',
    'scope 1:', 'scope 2:', 'quick links', 'frequency', 'purpose of engagement',
    'our initiatives', 'area of initiatives', 'career development', 'women development',
    'early career development', 'digital capability development', 'leadership development',
    'reducing carbon emissions', 'want to create the future of medicine?',
    "dr. reddy's - good health can't wait", 'enhancing trust with our stakeholders',
    'tech enabled employee lifecycle assistance', 'ftse4good index series',
    'esg commitments', 'sustainable financing framework', 'overview', 'material issues',
    'products/services', 'operations', 'markets served by the entity', 'investors'
]

for r in rows:
    cid, comp, name, cat, bud, loc, url, desc = r
    clean_name = ' '.join(name.split())
    name_l = clean_name.lower()
    
    # Check 1: Template 'Category Initiative - Company'
    if re.search(r'Initiative\s*-\s*', clean_name):
        template_count += 1
        samples_junk.append(('TEMPLATE', cid, comp, clean_name))
        continue
        
    # Check 2: Starts with page number / report title / markdown table
    if re.match(r'^\d+\s*\|\s*', clean_name) or 'annual report' in name_l or 'sustainability report' in name_l or 'esg data book' in name_l or 'printed version is uncontroll' in name_l or 'csr policy' in name_l or 'kurla road' in name_l:
        unparsed_pdf_header += 1
        samples_junk.append(('PDF_HEADER', cid, comp, clean_name))
        continue

    # Check 3: Short generic headers
    if clean_name.lower() in generic_list or len(clean_name.split()) <= 1:
        single_word_or_header += 1
        samples_junk.append(('GENERIC_HEADER', cid, comp, clean_name))
        continue
        
    # Check 4: General claims or sentence fragments
    if any(name_l.startswith(prefix) for prefix in ['we ', 'our ', 'to ', 'the ', 'with ']):
        general_corporate += 1
        samples_junk.append(('GENERAL_CLAIM', cid, comp, clean_name))
        continue
        
    genuine_looking += 1
    samples_genuine.append((cid, comp, clean_name, bud, loc, url))

print(f'Templates (e.g. "Healthcare Initiative - ITC Limited"): {template_count}')
print(f'PDF Headers / Disclosures / S.No tables: {unparsed_pdf_header}')
print(f'Generic words / navigation links: {single_word_or_header}')
print(f'Corporate statement sentences ("We work for..."): {general_corporate}')
print(f'Genuine-looking project names: {genuine_looking}')

print('\n--- SAMPLES OF GENUINE-LOOKING (first 30) ---')
for s in samples_genuine[:30]:
    b_disp = s[3] if s[3] else "None"
    l_disp = s[4] if s[4] else "None"
    print(f'[{s[0]}] ({s[1]}): {s[2][:70]} | Budget: {b_disp} | Loc: {l_disp}')

print('\n--- SAMPLES OF JUNK IDENTIFIED ---')
for s in samples_junk[:20]:
    print(f'{s[0]} [{s[1]}] ({s[2]}): {s[3][:70]}')
