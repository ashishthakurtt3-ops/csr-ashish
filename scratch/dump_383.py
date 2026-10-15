import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

rows = cur.execute('SELECT csr_id, company_id, project_name, category, budget, geographic_location, source_url, description FROM admin_panel_csrproject WHERE verification_status = "PUBLISHED" ORDER BY csr_id').fetchall()

with open('scratch/all_383_projects.txt', 'w', encoding='utf-8') as f:
    for r in rows:
        cid, comp, name, cat, bud, loc, url, desc = r
        clean_name = ' '.join(name.split())
        clean_desc = ' '.join((desc or '').split())[:120]
        f.write(f"ID: {cid} | Comp: {comp} | Title: {clean_name}\n")
        f.write(f"   Cat: {cat} | Bud: {bud} | Loc: {loc} | URL: {url}\n")
        f.write(f"   Desc: {clean_desc}\n\n")

print(f"Dumped {len(rows)} projects to scratch/all_383_projects.txt")
