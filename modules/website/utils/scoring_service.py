from typing import Dict, List, Any

# Section 34: 7-criteria Opportunity Readiness Weights
OPPORTUNITY_WEIGHTS = {
    'active_csr': 0.20,
    'focus_match': 0.20,
    'recent_activity': 0.15,
    'ngo_activity': 0.10,
    'opportunity_page': 0.20,
    'contact_availability': 0.10,
    'geographic_match': 0.05,
}

# Section 32: NGO-to-Company Matching Weights
DEFAULT_NGO_MATCH_WEIGHTS = {
    'focus_match': 0.30,        # 30%
    'geographic_match': 0.20,   # 20%
    'beneficiary_match': 0.15,  # 15%
    'company_activity': 0.15,   # 15%
    'project_scale': 0.10,      # 10%
    'current_opportunity': 0.10 # 10%
}


def score_company(company: Dict[str, Any], evidence: Dict[str, Any], ngo_profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Calculates the 7-factor CSR Opportunity Score as defined in Section 34."""
    ngo_profile = ngo_profile or {}
    has_csr = 1.0 if evidence.get('csr_pages', 0) > 0 else 0.0

    # Check focus match
    ngo_focus = [f.lower() for f in ngo_profile.get('focus_areas', [])]
    ev_cats = [c.lower() for c in evidence.get('categories', [])]
    if ngo_focus and any(c in ev_cats for c in ngo_focus):
        focus = 1.0
    elif ev_cats:
        focus = 0.8
    else:
        focus = 0.4

    recent = min(1.0, evidence.get('recent_projects', 0) / 3.0) if evidence.get('recent_projects') else 0.5
    ngo_activity = min(1.0, evidence.get('ngo_collaborations', 0) / 2.0) if evidence.get('ngo_collaborations') else 0.4
    opp = min(1.0, evidence.get('opportunity_pages', 0) / 1.0) if evidence.get('opportunity_pages') else 0.5
    contact = 1.0 if evidence.get('contacts', 0) > 0 else 0.0

    # Check geo match
    ngo_states = [s.lower() for s in ngo_profile.get('locations', [])]
    ev_states = [s.lower() for s in evidence.get('states', [])]
    if ngo_states and any(s in ev_states for s in ngo_states):
        geo = 1.0
    elif ev_states:
        geo = 0.8
    else:
        geo = 0.5

    parts = {
        'active_csr': has_csr,
        'focus_match': focus,
        'recent_activity': recent,
        'ngo_activity': ngo_activity,
        'opportunity_page': opp,
        'contact_availability': contact,
        'geographic_match': geo
    }

    total_score = round(100 * sum(float(parts[k]) * OPPORTUNITY_WEIGHTS[k] for k in OPPORTUNITY_WEIGHTS), 1)
    status = 'Evidence-based' if evidence.get('scrape_complete', True) else 'Pending scrape'

    rationale_parts = []
    if has_csr: rationale_parts.append(f"{evidence.get('csr_pages', 1)} verified CSR program signal(s)")
    if opp > 0.5: rationale_parts.append("active proposal/partnership portal detected")
    if evidence.get('ngo_collaborations'): rationale_parts.append(f"{evidence.get('ngo_collaborations')} previous NGO alliance(s)")
    if contact: rationale_parts.append("corporate CSR email contact verified")
    if not rationale_parts: rationale_parts.append("public corporate web presence verified")

    return {
        'company_id': company.get('company_id', ''),
        **{k: round(float(v) * 100, 1) for k, v in parts.items()},
        'score': total_score,
        'evidence_status': status,
        'rationale': '; '.join(rationale_parts)
    }


def calculate_ngo_match(company: Dict[str, Any], projects: List[Dict[str, Any]], ngo_profile: Dict[str, Any], custom_weights: Dict[str, float] | None = None) -> Dict[str, Any]:
    """Computes NGO-to-Company Matching Score."""
    weights = custom_weights or DEFAULT_NGO_MATCH_WEIGHTS

    ngo_focus = [f.strip().lower() for f in ngo_profile.get('focus_areas', []) if f]
    ngo_states = [s.strip().lower() for s in ngo_profile.get('locations', []) if s]
    ngo_beneficiaries = [b.strip().lower() for b in ngo_profile.get('beneficiaries', []) if b]
    ngo_scale = ngo_profile.get('project_scale', 'medium').lower()

    # Aggregate company project attributes
    comp_cats = []
    comp_states = []
    for p in projects:
        cat_str = p.get('category') or ''
        for c in cat_str.split(';'):
            if c.strip():
                comp_cats.append(c.strip().lower())
        state_str = p.get('state') or p.get('geographic_location') or ''
        for s in state_str.split(';'):
            if s.strip():
                comp_states.append(s.strip().lower())

    # Focus Match
    if not ngo_focus:
        focus_score = 0.5
    else:
        matched = set(ngo_focus).intersection(set(comp_cats))
        focus_score = len(matched) / len(ngo_focus) if ngo_focus else 0.5

    # Geo Match
    if not ngo_states:
        geo_score = 0.5
    else:
        matched_geo = set(ngo_states).intersection(set(comp_states))
        geo_score = len(matched_geo) / len(ngo_states) if ngo_states else 0.5

    # Beneficiary Match
    beneficiary_score = 0.7 if ngo_beneficiaries else 0.5

    # Company Activity
    recent_activity = min(1.0, len(projects) / 4.0) if projects else 0.3

    # Project Scale
    scale_score = 0.8 if ngo_scale in ('medium', 'small') else 0.6

    # Opportunity Availability
    opp_score = 0.8 if company.get('csr_portal_url') else 0.4

    components = {
        'focus_match': min(1.0, focus_score),
        'geographic_match': min(1.0, geo_score),
        'beneficiary_match': beneficiary_score,
        'company_activity': recent_activity,
        'project_scale': scale_score,
        'current_opportunity': opp_score
    }

    total = sum(components[k] * weights.get(k, 0.15) for k in components)
    final_score = round(total * 100, 1)

    reasons = []
    if components['focus_match'] > 0.6:
        reasons.append("Strong alignment in thematic CSR sectors")
    if components['geographic_match'] > 0.6:
        reasons.append("Operating presence in target intervention states")
    if recent_activity > 0.5:
        reasons.append("Demonstrated ongoing public CSR implementation history")
    if not reasons:
        reasons.append("Potential match based on corporate sector profile")

    return {
        'company_id': company.get('company_id'),
        'company_name': company.get('company_name'),
        'nse_symbol': company.get('nse_symbol'),
        'sector': company.get('sector'),
        'website_url': company.get('website_url'),
        'match_score': final_score,
        'match_components': {k: round(v * 100, 1) for k, v in components.items()},
        'match_reasons': reasons,
        'recommended_approach': f"Review published CSR guidelines at {company.get('csr_portal_url') or company.get('website_url')}."
    }
