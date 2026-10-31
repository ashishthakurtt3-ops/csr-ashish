import csv

def generate_reconciliation_csv():
    output_rows = []
    
    # 1. JOBS (3)
    with open('reports/accuracy_pilot_batch_001_050/job_candidates.csv', 'r', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            cid = r['candidate_id']
            title = r['title']
            comp = r['company_name']
            comp_id = r['company_id']
            apply_url = r['apply_url']
            src_url = r['source_url']
            evidence = r['evidence_excerpts']
            
            if "Schlosser" in title or "Spritzguss" in title:
                verdict = "INCORRECT"
                findings = "German-language role ('Schlosser-Meister' / 'Teamleitung Spritzguss') from European entity; location was falsely defaulted to 'India' due to Indian parent company HQ."
                defect = "GEOLOCATION_MISATTRIBUTION"
                action = "REJECT"
            elif title == "Executive":
                verdict = "NEEDS_MANUAL_REVIEW"
                findings = "Generic non-descriptive title ('Executive') without department or office location in anchor text. Requires verification of requisition active status."
                defect = "INSUFFICIENT_SPECIFICITY"
                action = "FLAG_FOR_OPERATOR_REVIEW"
            else:
                verdict = "CONFIRMED"
                findings = "Valid job opening."
                defect = "NONE"
                action = "APPROVE"
                
            output_rows.append({
                "candidate_id": cid,
                "candidate_type": "JOB",
                "company_id": comp_id,
                "company_name": comp,
                "title_or_project": title,
                "source_url": src_url,
                "apply_or_target_url": apply_url,
                "claimed_evidence": evidence,
                "audit_verdict": verdict,
                "audit_findings": findings,
                "root_cause_defect": defect,
                "recommended_action": action
            })

    # 2. OPPORTUNITIES (4)
    seen_opp_urls = set()
    with open('reports/accuracy_pilot_batch_001_050/opportunity_candidates.csv', 'r', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            cid = r['candidate_id']
            title = r['opportunity_title']
            comp = r['company_name']
            comp_id = r['company_id']
            src_url = r['source_url']
            evidence = r['supporting_evidence']
            
            if src_url in seen_opp_urls:
                verdict = "DUPLICATE"
                findings = "Exact duplicate of candidate CAND_OPP_COMP_TOP200_012_0001 with identical URL."
                defect = "DUPLICATE_OPPORTUNITY_HASH"
                action = "PURGE_DUPLICATE"
            elif "ariba.com" in src_url and "selfRegistration" in src_url:
                verdict = "INCORRECT"
                findings = "Permanent SAP Ariba supplier onboarding / registration portal, not an active open tender, RFP, or grant opportunity."
                defect = "GENERAL_VENDOR_PORTAL_CONFUSION"
                action = "REJECT"
            elif "rfps-for-impact-assessments" in src_url:
                verdict = "CONFIRMED"
                findings = "Genuine CSR procurement opportunity: Official RFP published by ITC for third-party CSR impact evaluation studies."
                defect = "NONE"
                action = "APPROVE"
            elif "RFP-NML" in src_url or "term loan" in title.lower():
                verdict = "INCORRECT"
                findings = "Corporate finance syndication tender for NTPC Mining Ltd borrowing term loans from banks; unrelated to CSR, grants, or social impact."
                defect = "COMMERCIAL_FINANCE_TENDER"
                action = "REJECT"
            else:
                verdict = "NEEDS_MANUAL_REVIEW"
                findings = "Ambiguous procurement link."
                defect = "UNKNOWN"
                action = "FLAG_FOR_OPERATOR_REVIEW"
                
            seen_opp_urls.add(src_url)
            output_rows.append({
                "candidate_id": cid,
                "candidate_type": "OPPORTUNITY",
                "company_id": comp_id,
                "company_name": comp,
                "title_or_project": title,
                "source_url": src_url,
                "apply_or_target_url": src_url,
                "claimed_evidence": evidence,
                "audit_verdict": verdict,
                "audit_findings": findings,
                "root_cause_defect": defect,
                "recommended_action": action
            })

    # 3. CSR (63)
    confirmed_csr_names = {
        'Vidya Vahini',
        'Sports Lab',
        'Kamalnayan Bajaj Hospital',
        'Shiksha Mandal, Wardha'
    }
    
    with open('reports/accuracy_pilot_batch_001_050/csr_candidates.csv', 'r', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            cid = r['candidate_id']
            pname = r['project_name'].strip()
            comp = r['company_name']
            comp_id = r['company_id']
            url = r['source_url']
            evidence = r['supporting_evidence']
            
            # Check Confirmed first
            if pname in confirmed_csr_names:
                verdict = "CONFIRMED"
                findings = f"Verified genuine, discrete CSR field project/institution supported by {comp} under Section 135."
                defect = "NONE"
                action = "APPROVE"
            # A. Synthesized placeholder
            elif "Community Development Program" in pname:
                verdict = "INCORRECT"
                findings = "Synthesized placeholder generated by crawler from statutory keyword match; not a genuine discrete named project."
                defect = "SYNTHESIZED_PLACEHOLDER_TITLE"
                action = "REJECT"
            # B. Banking commercial products
            elif "current-account" in url or "sbi-green" in url or any(k in pname.lower() for k in ["loans for", "agriculture banking", "interest rate"]):
                verdict = "INCORRECT"
                findings = "Commercial banking product (SME/Current Account/Loan), misclassified as CSR due to matching words like 'Healthcare' and 'Agriculture'."
                defect = "COMMERCIAL_BANKING_MISCLASSIFICATION"
                action = "REJECT"
            # C. Marketing / Promotional Video Headings / Commercial Consulting
            elif any(k in pname.lower() for k in ["watch how", "tools and products to support your", "learn more", "econiq-consulting", "leed"]):
                verdict = "INCORRECT"
                findings = "Website navigation call-to-action, green building rating credential, or commercial consulting pitch, not a CSR project."
                defect = "PROMOTIONAL_MARKETING_OR_CREDENTIAL"
                action = "REJECT"
            # D. Generic Schedule VII Headings / Governance Themes
            elif pname.lower() in [
                "health", "education", "sports", "environment", "women empowerment",
                "arts, culture & heritage", "healthcare", "skill development",
                "rural development", "water", "sanitation", "renewable energy",
                "water conservation", "afforestation", "biodiversity", "cultural heritage",
                "carbon management", "carbon-management", "waste management"
            ]:
                verdict = "INCORRECT"
                findings = "Broad thematic Schedule VII governance category or navigation menu pillar, not a specific discrete project."
                defect = "GENERIC_THEMATIC_PILLAR"
                action = "REJECT"
            # E. Internal corporate ESG operations / pledges
            elif any(k in pname.lower() for k in [
                "own operations", "internal operations", "decarbonisation of india",
                "occupational health", "environmental stewardship", "towards carbon-neutral",
                "commitment towards biodiversity", "our environmental priorities",
                "through environment protection", "land use and biodiversity",
                "social health, environment and safety management", "environmental sustainability"
            ]):
                verdict = "INCORRECT"
                findings = "Corporate environmental sustainability pledge, internal workplace policy, or ESG disclosure heading, not a community CSR project."
                defect = "INTERNAL_ESG_POLICY_OR_PLEDGE"
                action = "REJECT"
            # F. Plausible large thematic programs (e.g. ITC Sustainable Livelihoods, Carbon Positive)
            else:
                verdict = "NEEDS_MANUAL_REVIEW"
                findings = "Ambiguous initiative title / sustainability pillar requiring verification against corporate annual report / BRSR."
                defect = "AMBIGUOUS_INITIATIVE_TITLE"
                action = "FLAG_FOR_OPERATOR_REVIEW"

            output_rows.append({
                "candidate_id": cid,
                "candidate_type": "CSR",
                "company_id": comp_id,
                "company_name": comp,
                "title_or_project": pname,
                "source_url": url,
                "apply_or_target_url": url,
                "claimed_evidence": evidence,
                "audit_verdict": verdict,
                "audit_findings": findings,
                "root_cause_defect": defect,
                "recommended_action": action
            })

    # Save to CSV
    fieldnames = [
        "candidate_id", "candidate_type", "company_id", "company_name",
        "title_or_project", "source_url", "apply_or_target_url", "claimed_evidence",
        "audit_verdict", "audit_findings", "root_cause_defect", "recommended_action"
    ]
    out_path = 'reports/accuracy_pilot_batch_001_050/audited_candidates_reconciliation.csv'
    with open(out_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)
        
    print(f"Generated {out_path} with {len(output_rows)} rows.")
    
    # Print summary metrics
    from collections import Counter
    by_type = Counter((r['candidate_type'], r['audit_verdict']) for r in output_rows)
    print("\nSummary Counts:")
    for (t, v), count in sorted(by_type.items()):
        print(f"  {t} - {v}: {count}")

if __name__ == '__main__':
    generate_reconciliation_csv()
