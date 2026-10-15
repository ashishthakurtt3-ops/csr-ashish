import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

rows = cur.execute('''
    SELECT csr_id, company_id, project_name, category, budget, geographic_location, state, source_url, description, evidence_text
    FROM admin_panel_csrproject 
    WHERE verification_status = "PUBLISHED"
    ORDER BY csr_id
''').fetchall()

templates = []
pdf_artifacts = []
awards_or_rankings = []
slogans_or_sentences = []
nav_or_generic = []
genuine_projects = []

for r in rows:
    cid, comp, name, cat, bud, loc, state, url, desc, evid = r
    clean_name = ' '.join(name.split())
    name_l = clean_name.lower()
    
    # 1. Template generated names: 'Category Initiative - Company Name'
    if 'initiative -' in name_l or 'initiative —' in name_l:
        templates.append((cid, comp, clean_name, bud, 'TEMPLATE_SYNTHETIC_INITIATIVE'))
    # 2. PDF headers / table of contents / pagination fragments
    elif any(x in name_l for x in ['p a g e', '| page', 'board/cmd', 'esg data book', 'annual report 20', 'contents about the', '| apollo hospitals']):
        pdf_artifacts.append((cid, comp, clean_name, bud, 'PDF_PAGE_TABLE_ARTIFACT'))
    # 3. Awards, rankings, ESG ratings (not CSR projects)
    elif any(x in name_l for x in ['award', 'pepsico’s best', "pepsico's best", 'djsi', 'yearbook', 'msci esg', 'sustainalytics', 'cdp 20', 'dun & bradstreet', 'best corporate governance', 'golden peacock', 'cfi.co']):
        awards_or_rankings.append((cid, comp, clean_name, bud, 'CORPORATE_AWARD_OR_ESG_RATING'))
    # 4. Slogans, vision statements, fragmented sentences
    elif any(x in name_l for x in [
        'we work for', 'concrete is the most consumed', 'management framework which has', 
        'to encourage and reward', 'want to create the future', "good health can't wait",
        'technical leaders explaining', 'key features of the sfl', 'net zero initiative',
        'water positive promise', 'zero waste to landfill', 'renewable energy transition'
    ]):
        slogans_or_sentences.append((cid, comp, clean_name, bud, 'CORPORATE_SLOGAN_OR_INTERNAL_TARGET'))
    # 5. Generic nav links, internal HR/career modules, or generic corporate phrases
    elif clean_name.strip() in [
        'Social', 'About Us', 'Sustainability', 'Stakeholder Value Created', 'Quick Links', 
        'Career Development', 'Women Development', 'Early Career Development', 
        'Digital Capability Development', 'Leadership Development', 
        'Tech Enabled Employee Lifecycle Assistance', 'Equity, Diversity and Inclusion', 
        'Reducing carbon emissions', 'Enhancing trust with our stakeholders',
        'Torrent Pharmaceuticals Ltd.'
    ] or clean_name.startswith('Community SupportSAS'):
        nav_or_generic.append((cid, comp, clean_name, bud, 'GENERIC_NAV_OR_HR_POLICY'))
    else:
        genuine_projects.append((cid, comp, clean_name, cat, bud, loc, state, url, desc))

print(f"Total Published: {len(rows)}")
print(f"Templates: {len(templates)}")
print(f"PDF Artifacts: {len(pdf_artifacts)}")
print(f"Awards / ESG Ratings: {len(awards_or_rankings)}")
print(f"Slogans / Sentences: {len(slogans_or_sentences)}")
print(f"Nav / Generic HR: {len(nav_or_generic)}")
print(f"Genuine Candidate Projects: {len(genuine_projects)}")

total_junk = len(templates) + len(pdf_artifacts) + len(awards_or_rankings) + len(slogans_or_sentences) + len(nav_or_generic)
print(f"\nTotal Non-Project Artifacts: {total_junk}")
print(f"Remaining Valid CSR Initiatives: {len(genuine_projects)}")
print(f"Sum check: {total_junk + len(genuine_projects)} == {len(rows)}")

# Check budgets among genuine projects:
malformed_budgets = [p for p in genuine_projects if p[4] and any(c in str(p[4]).lower() for c in ['rs,', 'nan', 'none'])]
print(f"Genuine candidates with malformed budget ('rs,'): {len(malformed_budgets)}")

with open('scratch/classified_genuine_projects.txt', 'w', encoding='utf-8') as f:
    for p in genuine_projects:
        cid, comp, name, cat, bud, loc, state, url, desc = p
        f.write(f"[{cid}] ({comp}) Title: {name}\n")
        f.write(f"     Cat: {cat} | Bud: {bud} | Loc: {loc} | State: {state}\n")
        f.write(f"     URL: {url}\n\n")

with open('scratch/classified_junk_to_quarantine.txt', 'w', encoding='utf-8') as f:
    for j_list in [templates, pdf_artifacts, awards_or_rankings, slogans_or_sentences, nav_or_generic]:
        for item in j_list:
            f.write(f"[{item[0]}] ({item[1]}) Reason: {item[4]} | Title: {item[2]} | Bud: {item[3]}\n")
