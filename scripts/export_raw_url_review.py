"""
Export Raw Yahoo Finance and Wikidata Homepage URL Results for All Companies.
Generates:
1. reports/stage1a_shortcut/manual_url_review_all_companies.csv
2. reports/stage1a_shortcut/manual_url_review_all_companies.md
STRICT READ-ONLY. No database writes, no AI calls, no web requests.
"""

import os
import csv

IN_PATH = os.path.join("reports", "stage1a_shortcut", "homepage_candidates_v2.csv")
OUT_CSV = os.path.join("reports", "stage1a_shortcut", "manual_url_review_all_companies.csv")
OUT_MD = os.path.join("reports", "stage1a_shortcut", "manual_url_review_all_companies.md")

# Known collector log messages
LOG_MISMATCHES = {
    "COMP_TOP200_058": "Yahoo search/name mismatch for symbol LTIM.NS: result ignored",
    "COMP_TOP200_078": "Yahoo search/name mismatch for symbol MCDOWELL-N.NS: result ignored",
    "COMP_TOP200_113": "Yahoo search/name mismatch for symbol INDIA.NS: result ignored",
    "COMP_TOP200_115": "Yahoo name mismatch: 'UCO Bank' for symbol UCOBANK.NS vs company name 'ashish'; result ignored",
}

FIELDS = [
    "Company ID",
    "Company Name",
    "Wikidata Website URL",
    "Wikidata Domain",
    "Wikidata Entity URL",
    "Yahoo Finance Website URL",
    "Yahoo Finance Domain",
    "Yahoo Finance Symbol",
    "Yahoo Finance Source URL",
    "Collection Notes"
]

def generate():
    with open(IN_PATH, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 201, f"Expected 201 rows, got {len(rows)}"

    export_rows = []

    for r in rows:
        cid = r["company_id"].strip()
        name = r["name"].strip()
        
        wiki_url = r.get("wikidata_url", "").strip()
        wiki_domain = r.get("wikidata_domain", "").strip()
        wiki_label = r.get("wikidata_label", "").strip()
        
        yahoo_url = r.get("yahoo_url", "").strip()
        yahoo_domain = r.get("yahoo_domain", "").strip()
        yahoo_sym = r.get("yahoo_symbol_used", "").strip()
        yahoo_name = r.get("yahoo_name", "").strip()
        
        notes_parts = []
        
        existing_notes = r.get("notes", "").strip()
        if existing_notes:
            notes_parts.append(existing_notes)
            
        if cid in LOG_MISMATCHES:
            notes_parts.append(LOG_MISMATCHES[cid])
            
        if wiki_label and wiki_label.lower() != name.lower():
            notes_parts.append(f"Wikidata label: '{wiki_label}'")
            
        if yahoo_name and yahoo_name.lower() != name.lower():
            notes_parts.append(f"Yahoo name: '{yahoo_name}'")
            
        if not wiki_url and not yahoo_url:
            if not notes_parts:
                notes_parts.append("Neither Wikidata nor Yahoo Finance returned a homepage URL")
        elif not wiki_url:
            notes_parts.append("Wikidata: NOT COLLECTED (no entity with P856 matching company name)")
        elif not yahoo_url:
            if cid not in LOG_MISMATCHES:
                notes_parts.append("Yahoo Finance: NOT COLLECTED (no ticker/profile website found)")

        col_notes = "; ".join(notes_parts) if notes_parts else "Both sources collected successfully"

        row_dict = {
            "Company ID": cid,
            "Company Name": name,
            "Wikidata Website URL": wiki_url if wiki_url else "NOT COLLECTED",
            "Wikidata Domain": wiki_domain if wiki_domain else "NOT COLLECTED",
            "Wikidata Entity URL": "NOT COLLECTED",
            "Yahoo Finance Website URL": yahoo_url if yahoo_url else "NOT COLLECTED",
            "Yahoo Finance Domain": yahoo_domain if yahoo_domain else "NOT COLLECTED",
            "Yahoo Finance Symbol": yahoo_sym if yahoo_sym else "NOT COLLECTED",
            "Yahoo Finance Source URL": "NOT COLLECTED",
            "Collection Notes": col_notes
        }
        export_rows.append(row_dict)

    # 1. Write CSV with UTF-8 BOM for seamless Excel compatibility
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(export_rows)

    print(f"Successfully wrote {len(export_rows)} rows to {OUT_CSV}")

    # 2. Write Markdown table split into 4 logical batches
    sections = [
        ("Part 1: COMP_0 & COMP_TOP200_001 to COMP_TOP200_050 (Batch 1)", export_rows[:51]),
        ("Part 2: COMP_TOP200_051 to COMP_TOP200_100", export_rows[51:101]),
        ("Part 3: COMP_TOP200_101 to COMP_TOP200_150", export_rows[101:151]),
        ("Part 4: COMP_TOP200_151 to COMP_TOP200_200", export_rows[151:201]),
    ]

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("# Raw Yahoo Finance and Wikidata Homepage URL Review (All 201 Companies)\n\n")
        f.write("**Generated:** 2026-10-29\n")
        f.write("**Scope:** All 201 companies (`COMP_0` through `COMP_TOP200_200`).\n")
        f.write("**Purpose:** Pure raw URL audit comparing Wikidata (Property P856) and Yahoo Finance results with zero database influence.\n\n")
        f.write("---\n\n")

        for sec_title, sec_rows in sections:
            f.write(f"## {sec_title} ({len(sec_rows)} companies)\n\n")
            f.write("| Company ID | Company Name | Wikidata Website URL | Wikidata Domain | Yahoo Finance Website URL | Yahoo Finance Domain | Yahoo Symbol | Collection Notes |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for r in sec_rows:
                # Format URLs nicely if present
                w_url_disp = f"[`{r['Wikidata Website URL']}`]({r['Wikidata Website URL']})" if r['Wikidata Website URL'] != "NOT COLLECTED" else "*NOT COLLECTED*"
                y_url_disp = f"[`{r['Yahoo Finance Website URL']}`]({r['Yahoo Finance Website URL']})" if r['Yahoo Finance Website URL'] != "NOT COLLECTED" else "*NOT COLLECTED*"
                w_dom = f"`{r['Wikidata Domain']}`" if r['Wikidata Domain'] != "NOT COLLECTED" else "*NOT COLLECTED*"
                y_dom = f"`{r['Yahoo Finance Domain']}`" if r['Yahoo Finance Domain'] != "NOT COLLECTED" else "*NOT COLLECTED*"
                y_sym = f"`{r['Yahoo Finance Symbol']}`" if r['Yahoo Finance Symbol'] != "NOT COLLECTED" else "*NOT COLLECTED*"
                
                # Sanitize pipe characters in notes
                clean_notes = r['Collection Notes'].replace("|", "\\|")
                f.write(f"| {r['Company ID']} | {r['Company Name']} | {w_url_disp} | {w_dom} | {y_url_disp} | {y_dom} | {y_sym} | {clean_notes} |\n")
            f.write("\n\n")

    print(f"Successfully wrote {len(export_rows)} rows to {OUT_MD}")

if __name__ == "__main__":
    generate()

