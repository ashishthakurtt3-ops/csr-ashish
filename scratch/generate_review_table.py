import csv
import os

# Load reconciled data from homepage_candidates_v2.csv
in_path = os.path.join("reports", "stage1a_shortcut", "homepage_candidates_v2.csv")
with open(in_path, "r", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

print(f"Total input rows: {len(rows)}")

# Known collector log messages
log_mismatches = {
    "COMP_TOP200_058": "Yahoo search/name mismatch for symbol LTIM.NS: result ignored",
    "COMP_TOP200_078": "Yahoo search/name mismatch for symbol MCDOWELL-N.NS: result ignored",
    "COMP_TOP200_113": "Yahoo search/name mismatch for symbol INDIA.NS: result ignored",
    "COMP_TOP200_115": "Yahoo name mismatch: 'UCO Bank' for symbol UCOBANK.NS vs company name 'ashish'; result ignored",
}

output_rows = []

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
    
    # Check notes from collector / reconciliation
    existing_notes = r.get("notes", "").strip()
    if existing_notes:
        notes_parts.append(existing_notes)
        
    if cid in log_mismatches:
        notes_parts.append(log_mismatches[cid])
        
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
        if cid not in log_mismatches:
            notes_parts.append("Yahoo Finance: NOT COLLECTED (no ticker/profile website found)")

    col_notes = "; ".join(notes_parts) if notes_parts else "Both sources collected successfully"

    out_row = {
        "Company ID": cid,
        "Company Name": name,
        "Wikidata Website URL": wiki_url if wiki_url else "NOT COLLECTED",
        "Wikidata Domain": wiki_domain if wiki_domain else "NOT COLLECTED",
        "Wikidata Entity URL": "NOT COLLECTED",  # Entity ID/URL was not stored during collection
        "Yahoo Finance Website URL": yahoo_url if yahoo_url else "NOT COLLECTED",
        "Yahoo Finance Domain": yahoo_domain if yahoo_domain else "NOT COLLECTED",
        "Yahoo Finance Symbol": yahoo_sym if yahoo_sym else "NOT COLLECTED",
        "Yahoo Finance Source URL": "NOT COLLECTED",  # Profile source URL was not stored during collection
        "Collection Notes": col_notes
    }
    output_rows.append(out_row)

print(f"Prepared {len(output_rows)} output rows.")

