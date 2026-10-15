import sqlite3

def check_db(path):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    table = "admin_panel_csrproject"
    
    # Query published records with non-null budget
    cur.execute(f"SELECT csr_id, project_name, budget, verification_status FROM {table} WHERE verification_status = 'PUBLISHED' AND budget IS NOT NULL")
    pub_budgets = cur.fetchall()
    
    # Query project 970
    cur.execute(f"SELECT csr_id, project_name, budget, verification_status FROM {table} WHERE csr_id = 970")
    p970 = cur.fetchone()
    
    # Query all records with csr_id >= 951 with non-null budget
    cur.execute(f"SELECT csr_id, project_name, budget, verification_status FROM {table} WHERE csr_id >= 951 AND budget IS NOT NULL")
    crawled_budgets = cur.fetchall()
    
    # Query all records with csr_id >= 951 in general
    cur.execute(f"SELECT count(*) FROM {table} WHERE csr_id >= 951")
    crawled_count = cur.fetchone()[0]

    # Query all published count
    cur.execute(f"SELECT count(*) FROM {table} WHERE verification_status = 'PUBLISHED'")
    pub_count = cur.fetchone()[0]

    conn.close()
    return pub_budgets, p970, crawled_budgets, crawled_count, pub_count

for name, path in [('ACTIVE (db.sqlite3)', 'db.sqlite3'), 
                   ('BACKUP (db.sqlite3.backup_20261010_134144)', 'db.sqlite3.backup_20261010_134144'),
                   ('CHECKPOINT (db.sqlite3.audit_checkpoint_20261010)', 'db.sqlite3.audit_checkpoint_20261010')]:
    print(f"=== {name} ===")
    pub_b, p970, all_crawled_b, crawled_cnt, pub_cnt = check_db(path)
    print(f"Total crawled (>=951): {crawled_cnt}, Published: {pub_cnt}")
    print(f"Published non-null budgets ({len(pub_b)}):")
    for b in pub_b:
        b_val = b[2].encode('ascii', 'backslashreplace').decode('ascii') if b[2] else 'None'
        print("  ", b[0], b[1][:40], "-->", b_val, b[3])
    print(f"Project 970: {p970}")
    print(f"All crawled non-null budgets ({len(all_crawled_b)}):")
    for b in all_crawled_b:
        b_val = b[2].encode('ascii', 'backslashreplace').decode('ascii') if b[2] else 'None'
        print("  ", b[0], b[1][:40], "-->", b_val, b[3])
    print()
