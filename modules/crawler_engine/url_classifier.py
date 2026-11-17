"""
modules/crawler_engine/url_classifier.py
========================================
Autonomous URL Classification & 5-Tier Verification Engine.

Provides:
1. Complete Multi-Category URL Classification:
   - Careers and Recruitment (Careers, Jobs, Openings, ATS Portals, Graduate Programs, Internships)
   - CSR and Social Impact (CSR Initiatives, Projects, Foundations, NGO Partnerships)
   - ESG and Sustainability (ESG Overview, Climate Action, Governance, Net Zero)
   - Investor Relations and Corporate Reports (Annual, Financial, Integrated, BRSR, Section 135)
   - Other Important Company URLs:
     * About Company / Overview / Heritage
     * Leadership and Board of Directors
     * Management Team / Executives
     * Business Segments / Divisions
     * Products and Services / Solutions
     * Locations / Worldwide Offices
     * Contact Us / Helpdesk
     * Media, News, Press Releases
     * Policies (Code of Conduct, Ethics, Whistleblower)
     * Compliance (Statutory, Regulatory Disclosures)
     * Procurement / Supply Chain
     * Supplier Registration / Vendor Portal
     * Tenders / Bids / RFP

2. 5-Tier URL Verification Taxonomy:
   - VERIFIED_OFFICIAL: Reachable on official corporate domain / subdomains.
   - VERIFIED_ASSOCIATED: Reachable on verified external ATS / Foundation / Group domains.
   - POTENTIALLY_RELEVANT: Reachable external domain link without confirmed direct association.
   - UNVERIFIED: Candidate discovered but not yet probed.
   - BROKEN_OR_INACCESSIBLE: HTTP error, DNS failure, timeout, or soft 404.
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class FiveTierVerificationStatus(str, Enum):
    VERIFIED_OFFICIAL = "VERIFIED_OFFICIAL"
    VERIFIED_ASSOCIATED = "VERIFIED_ASSOCIATED"
    POTENTIALLY_RELEVANT = "POTENTIALLY_RELEVANT"
    UNVERIFIED = "UNVERIFIED"
    BROKEN_OR_INACCESSIBLE = "BROKEN_OR_INACCESSIBLE"


# Mapping from 5-tier status to Django CompanySource.VERIFICATION_STATUS_CHOICES
FIVE_TIER_TO_DB_STATUS = {
    FiveTierVerificationStatus.VERIFIED_OFFICIAL.value: "APPROVED",
    FiveTierVerificationStatus.VERIFIED_ASSOCIATED.value: "APPROVED",
    FiveTierVerificationStatus.POTENTIALLY_RELEVANT.value: "REVIEW_REQUIRED",
    FiveTierVerificationStatus.UNVERIFIED.value: "DISCOVERED",
    FiveTierVerificationStatus.BROKEN_OR_INACCESSIBLE.value: "INACCESSIBLE",
}


# Category Definitions & Regex Patterns
CATEGORY_RULES: List[Dict[str, Any]] = [
    # 1. Careers & Recruitment
    {
        "category": "CAREERS",
        "detailed": "CAREERS_PORTAL",
        "source_type": "CAREERS_LANDING",
        "path_patterns": [
            r"/(?:careers?|jobs?|openings|current-openings|vacancies|recruitment|work-with-us|join-us|join-our-team|job-search|talent|opportunities)(?:/|$)",
            r"/(?:students?-graduates?|graduate-programs?|internships?|campus-hiring)(?:/|$)",
        ],
        "text_patterns": [
            r"\b(?:careers?|jobs?|current openings|join our team|work with us|join us|vacancies|job search|opportunities|campus recruitment|internships?)\b"
        ],
        "weight": 95,
    },
    # 2. CSR and Social Impact
    {
        "category": "CSR",
        "detailed": "CSR_INITIATIVE",
        "source_type": "CSR_OVERVIEW",
        "path_patterns": [
            r"/(?:csr|corporate-social-responsibility|social-impact|community-development|csr-initiatives|csr-projects|community-outreach)(?:/|$)",
            r"/(?:foundation|trust|ngo-partnerships?|education-initiatives?|healthcare-initiatives?|rural-development)(?:/|$)",
        ],
        "text_patterns": [
            r"\b(?:csr|corporate social responsibility|social impact|community development|csr initiatives|csr projects|foundation|trust|ngo partnerships?|rural development)\b"
        ],
        "weight": 90,
    },
    # 3. ESG and Sustainability
    {
        "category": "ESG_SUSTAINABILITY",
        "detailed": "SUSTAINABILITY_INITIATIVE",
        "source_type": "CSR_OVERVIEW",
        "path_patterns": [
            r"/(?:sustainability|esg|environment|climate-action|net-zero|carbon-neutrality|social-responsibility|sustainability-initiatives)(?:/|$)",
        ],
        "text_patterns": [
            r"\b(?:sustainability|esg|environment|climate action|net zero|carbon neutrality|environmental practices|sustainability initiatives)\b"
        ],
        "weight": 90,
    },
    # 4. Investor Relations and Corporate Reports
    {
        "category": "INVESTOR_RELATIONS",
        "detailed": "INVESTOR_RELATIONS",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:investors?|investor-relations?|financials?|shareholder-information|financial-results)(?:/|$)",
            r"/(?:annual-reports?|integrated-reports?|brsr(?:-core)?|csr-reports?|sustainability-reports?|section-135)(?:/|$|\.pdf)",
        ],
        "text_patterns": [
            r"\b(?:investor relations|investors?|annual reports?|financial reports?|integrated reports?|brsr|brsr core|csr reports?|sustainability reports?|section 135)\b"
        ],
        "weight": 85,
    },
    # 5. Leadership and Board of Directors
    {
        "category": "LEADERSHIP",
        "detailed": "LEADERSHIP",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:leadership|board-of-directors|board-members|directors|executive-leadership|executive-team|our-leaders|key-executives)(?:/|$)",
        ],
        "text_patterns": [
            r"\b(?:leadership|board of directors|executive leadership|board members|our leaders|directors|key executives)\b"
        ],
        "weight": 80,
    },
    # 6. Management Team
    {
        "category": "MANAGEMENT",
        "detailed": "MANAGEMENT",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:management(?:-team)?|senior-management|executive-committee|cxo-team)(?:/|$)",
        ],
        "text_patterns": [
            r"\b(?:management team|senior management|executive committee|management)\b"
        ],
        "weight": 80,
    },
    # 7. Business Segments & Divisions
    {
        "category": "BUSINESS_SEGMENTS",
        "detailed": "BUSINESS_SEGMENTS",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:business-segments?|businesses|divisions?|group-companies|subsidiaries|operating-segments|business-units|industry-segments)(?:/|$)",
        ],
        "text_patterns": [
            r"\b(?:business segments?|businesses|divisions?|group companies|subsidiaries|operating segments|business units)\b"
        ],
        "weight": 75,
    },
    # 8. Products and Services
    {
        "category": "PRODUCTS_SERVICES",
        "detailed": "PRODUCTS_SERVICES",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:products?|services?|solutions?|offerings?|capabilities|portfolio|what-we-do|technologies)(?:[-_].*|/|$)",
        ],
        "text_patterns": [
            r"\b(?:products?|services?|solutions?|offerings?|capabilities|what we do|technologies|portfolio)\b"
        ],
        "weight": 75,
    },
    # 9. Locations and Global Presence
    {
        "category": "LOCATIONS",
        "detailed": "LOCATIONS",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:.*[-_])?(?:locations?|global-presence|worldwide|offices?|branches|facilities|manufacturing-plants?|development-cent(?:ers?|res?))(?:[-_].*|/|$)",
        ],
        "text_patterns": [
            r"\b(?:locations?|our locations?|global presence|worldwide offices?|facilities|branches|manufacturing plants?|our offices)\b"
        ],
        "weight": 75,
    },
    # 10. Contact Us
    {
        "category": "CONTACT",
        "detailed": "CONTACT",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:.*[-_])?(?:contact(?:-us)?|get-in-touch|reach-us|enquiry|customer-support|helpdesk|feedback)(?:[-_].*|/|$)",
        ],
        "text_patterns": [
            r"\b(?:contact us|contact|get in touch|reach us|enquiry|customer support|helpdesk)\b"
        ],
        "weight": 75,
    },
    # 11. Media, News and Press Releases
    {
        "category": "MEDIA_NEWS",
        "detailed": "MEDIA_NEWS",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:.*[-_])?(?:media(?:-cent(?:er|re))?|news|newsroom|press-releases?|press|in-the-news|media-kit|articles|stories|insights)(?:[-_].*|/|$)",
        ],
        "text_patterns": [
            r"\b(?:media|news|newsroom|press releases?|press|in the news|media center|articles)\b"
        ],
        "weight": 70,
    },
    # 12. Policies
    {
        "category": "POLICIES",
        "detailed": "POLICIES",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:.*[-_])?(?:policies|policy|code-of-conduct|ethics(?:-policy)?|whistleblower(?:-policy)?|anti-bribery|privacy-policy|terms-of-use|terms-and-conditions)(?:[-_].*|/|$)",
        ],
        "text_patterns": [
            r"\b(?:policies|code of conduct|ethics policy|whistleblower policy|anti-bribery|privacy policy|terms of use)\b"
        ],
        "weight": 75,
    },
    # 13. Compliance & Governance
    {
        "category": "COMPLIANCE",
        "detailed": "COMPLIANCE",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:.*[-_])?(?:compliance|statutory-compliance|regulatory-disclosures?|secretarial-compliance|corporate-governance(?:/compliance)?|statutory-filings?|regulatory-filings?)(?:[-_].*|/|$)",
        ],
        "text_patterns": [
            r"\b(?:compliance|statutory compliance|regulatory disclosures?|secretarial compliance|corporate governance|statutory filings?|regulatory filings?)\b"
        ],
        "weight": 80,
    },
    # 14. Procurement & Supply Chain
    {
        "category": "PROCUREMENT",
        "detailed": "PROCUREMENT",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:.*[-_])?(?:procurement|suppliers?|supply-chain(?:-partners?)?|vendors?)(?:[-_].*|/|$)",
        ],
        "text_patterns": [
            r"\b(?:procurement|suppliers?|supply chain|vendors?)\b"
        ],
        "weight": 75,
    },
    # 15. Supplier Registration
    {
        "category": "SUPPLIER_REGISTRATION",
        "detailed": "SUPPLIER_REGISTRATION",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:.*[-_])?(?:supplier-registration|vendor-registration|vendor-portal|vendor-enrolment|partner-registration)(?:[-_].*|/|$)",
        ],
        "text_patterns": [
            r"\b(?:supplier registration|vendor registration|vendor portal|vendor enrolment|supplier portal)\b"
        ],
        "weight": 80,
    },
    # 16. Tenders & RFP
    {
        "category": "TENDERS",
        "detailed": "TENDERS",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:.*[-_])?(?:tenders?|tender-notices?|rfp|rfq|bidding|active-tenders?|e-procurement|contracts)(?:[-_].*|/|$)",
        ],
        "text_patterns": [
            r"\b(?:tenders?|tender notices?|rfp|rfq|bidding|active tenders?|e-procurement|contracts?)\b"
        ],
        "weight": 80,
    },
    # 17. About Company
    {
        "category": "ABOUT_COMPANY",
        "detailed": "ABOUT_COMPANY",
        "source_type": "OTHER",
        "path_patterns": [
            r"/(?:.*[-_])?(?:about(?:-us)?|who-we-are|our-story|company-profile|overview|history|heritage|mission-vision|values)(?:[-_].*|/|$)",
        ],
        "text_patterns": [
            r"\b(?:about us|about company|who we are|our story|company profile|overview|history|heritage|mission and vision)\b"
        ],
        "weight": 70,
    },
]


@dataclass
class ClassificationResult:
    """Strongly typed classification result."""
    primary_category: str
    detailed_classification: str
    source_type: str
    confidence: float
    matched_keywords: List[str] = field(default_factory=list)
    supporting_evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary_category": self.primary_category,
            "detailed_classification": self.detailed_classification,
            "source_type": self.source_type,
            "confidence": round(self.confidence, 2),
            "matched_keywords": self.matched_keywords,
            "supporting_evidence": self.supporting_evidence,
        }


def classify_url(
    url: str,
    link_text: str = "",
    page_title: str = "",
    meta_description: str = "",
    is_ats: bool = False,
    is_foundation: bool = False,
) -> ClassificationResult:
    """
    Classifies a discovered URL using URL path, anchor text, page title,
    meta description, and associated external markers.
    """
    url_low = (url or "").lower().strip()
    link_low = (link_text or "").lower().strip()
    title_low = (page_title or "").lower().strip()
    meta_low = (meta_description or "").lower().strip()

    parsed = urllib.parse.urlparse(url_low)
    path = parsed.path or "/"

    # 1. External ATS platform override
    if is_ats or any(ats in url_low for ats in ("workday", "taleo", "greenhouse", "lever", "smartrecruiters", "darwinbox", "turbohire", "zwayam", "phenom", "icims")):
        return ClassificationResult(
            primary_category="CAREERS",
            detailed_classification="ATS_GATEWAY",
            source_type="ATS_PORTAL",
            confidence=0.98,
            matched_keywords=["ATS_PLATFORM"],
            supporting_evidence=f"External ATS platform detected in URL: {url}",
        )

    # 2. External Foundation override
    if is_foundation or ("foundation" in url_low and any(k in url_low for k in ("trust", "csr", "social", "care", "charity"))):
        return ClassificationResult(
            primary_category="CSR",
            detailed_classification="CORPORATE_FOUNDATION",
            source_type="CSR_OVERVIEW",
            confidence=0.95,
            matched_keywords=["CORPORATE_FOUNDATION"],
            supporting_evidence=f"Corporate foundation domain detected: {url}",
        )

    # 3. Report PDF detection
    is_pdf = path.endswith(".pdf") or "application/pdf" in meta_low
    if is_pdf:
        combined_text = f"{path} {link_low} {title_low}"
        if any(k in combined_text for k in ("annual", "integrated")):
            return ClassificationResult(
                primary_category="INVESTOR_RELATIONS",
                detailed_classification="ANNUAL_REPORT",
                source_type="ANNUAL_REPORT",
                confidence=0.95,
                matched_keywords=["ANNUAL_REPORT_PDF"],
                supporting_evidence=f"Annual report PDF detected: {url}",
            )
        if any(k in combined_text for k in ("brsr", "section-135", "section 135")):
            return ClassificationResult(
                primary_category="INVESTOR_RELATIONS",
                detailed_classification="BRSR_REPORT",
                source_type="CSR_REPORT",
                confidence=0.95,
                matched_keywords=["BRSR_SECTION_135_PDF"],
                supporting_evidence=f"BRSR / Section 135 PDF detected: {url}",
            )
        if any(k in combined_text for k in ("csr", "social")):
            return ClassificationResult(
                primary_category="CSR",
                detailed_classification="CSR_REPORT",
                source_type="CSR_REPORT",
                confidence=0.95,
                matched_keywords=["CSR_REPORT_PDF"],
                supporting_evidence=f"CSR report PDF detected: {url}",
            )
        if any(k in combined_text for k in ("sustain", "esg")):
            return ClassificationResult(
                primary_category="ESG_SUSTAINABILITY",
                detailed_classification="SUSTAINABILITY_REPORT",
                source_type="SUSTAINABILITY_REPORT",
                confidence=0.95,
                matched_keywords=["SUSTAINABILITY_REPORT_PDF"],
                supporting_evidence=f"Sustainability report PDF detected: {url}",
            )

    # 4. Pattern matching across categories
    best_match: Optional[Dict[str, Any]] = None
    best_score: float = 0.0
    best_evidence: str = ""
    best_matched_keys: List[str] = []

    for rule in CATEGORY_RULES:
        score = 0.0
        matched_keys: List[str] = []

        # Check path patterns
        leaf = path.rstrip('/').rsplit('/', 1)[-1]
        for pat in rule["path_patterns"]:
            m = re.search(pat, path, re.IGNORECASE)
            if m:
                score += 0.55
                matched_keys.append(f"path:{m.group(0)}")
                # Specificity bonus if matched on the leaf segment
                if re.search(pat, f"/{leaf}", re.IGNORECASE):
                    score += 0.15
                break

        # Check link text
        for pat in rule["text_patterns"]:
            m = re.search(pat, link_low, re.IGNORECASE)
            if m:
                score += 0.35
                matched_keys.append(f"text:{m.group(0)}")
                break

        # Check page title
        if title_low:
            for pat in rule["text_patterns"]:
                m = re.search(pat, title_low, re.IGNORECASE)
                if m:
                    score += 0.20
                    matched_keys.append(f"title:{m.group(0)}")
                    break

        # Scale by rule weight
        normalized_score = min(0.99, score * (rule["weight"] / 100.0))
        if normalized_score > best_score:
            best_score = normalized_score
            best_match = rule
            best_matched_keys = matched_keys
            best_evidence = f"Matched {', '.join(matched_keys)} with base weight {rule['weight']}"

    if best_match and best_score >= 0.40:
        return ClassificationResult(
            primary_category=best_match["category"],
            detailed_classification=best_match["detailed"],
            source_type=best_match["source_type"],
            confidence=best_score,
            matched_keywords=best_matched_keys,
            supporting_evidence=best_evidence,
        )

    # 5. Default Fallback
    return ClassificationResult(
        primary_category="OTHER",
        detailed_classification="GENERAL_CORPORATE_PAGE",
        source_type="OTHER",
        confidence=0.30,
        matched_keywords=[],
        supporting_evidence="Generic corporate link without explicit category keywords",
    )


def determine_5tier_verification_status(
    url: str,
    official_domain: str,
    http_status: Optional[int] = 200,
    is_accessible: bool = True,
    is_ats: bool = False,
    is_foundation: bool = False,
    redirect_target: str = "",
    title: str = "",
    text_snippet: str = "",
    is_unverified: bool = False,
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Evaluates discovered URL against the 5-tier verification system.

    Returns:
    (db_status, five_tier_label, evidence_dict)

    Where:
    - db_status: matches Django CompanySource.VERIFICATION_STATUS_CHOICES ('APPROVED', 'REVIEW_REQUIRED', 'INACCESSIBLE', etc.)
    - five_tier_label: exact label requested in Master Prompt §6 ('VERIFIED_OFFICIAL', 'VERIFIED_ASSOCIATED', etc.)
    - evidence_dict: audit trail containing HTTP status, canonical redirects, domains, etc.
    """
    final_url = redirect_target or url
    parsed = urllib.parse.urlparse(final_url)
    host = (parsed.netloc or "").lower().split(":")[0]
    clean_official = (official_domain or "").lower().strip()
    if clean_official.startswith("www."):
        clean_official = clean_official[4:]

    evidence: Dict[str, Any] = {
        "original_url": url,
        "final_url": final_url,
        "http_status": http_status,
        "host": host,
        "official_domain": clean_official,
        "is_ats": is_ats,
        "is_foundation": is_foundation,
    }

    # Tier 4: UNVERIFIED
    # Candidate discovered but pending HTTP probe or explicitly unverified
    if is_unverified or http_status is None:
        evidence["reason"] = "Discovered URL candidate awaiting HTTP verification"
        return (
            FIVE_TIER_TO_DB_STATUS[FiveTierVerificationStatus.UNVERIFIED.value],
            FiveTierVerificationStatus.UNVERIFIED.value,
            evidence,
        )

    # Tier 5: BROKEN_OR_INACCESSIBLE
    # Check for HTTP errors, unreachable status, or soft-404 in title/text
    soft_404 = False
    low_title = (title or "").lower()
    low_text = (text_snippet or "")[:500].lower()
    if any(err in low_title or err in low_text for err in ("404 not found", "page not found", "access denied", "site unavailable", "domain for sale")):
        soft_404 = True

    if not is_accessible or (http_status is not None and http_status in (0, 404, 410, 500, 502, 503, 504)) or soft_404:
        evidence["reason"] = f"Unreachable or error HTTP {http_status}" if not soft_404 else "Soft-404 detected"
        return (
            FIVE_TIER_TO_DB_STATUS[FiveTierVerificationStatus.BROKEN_OR_INACCESSIBLE.value],
            FiveTierVerificationStatus.BROKEN_OR_INACCESSIBLE.value,
            evidence,
        )

    # Tier 1: VERIFIED_OFFICIAL
    # Host matches official domain or subdomain
    is_official_host = (
        host == clean_official or
        host.endswith("." + clean_official) or
        (clean_official in host and any(host.endswith(s) for s in (".com", ".org", ".in", ".co.in", ".net", ".io")))
    )
    if is_official_host and http_status in (200, 201, 301, 302, 307, 308):
        evidence["reason"] = f"Verified official corporate domain ({host}) with HTTP {http_status}"
        return (
            FIVE_TIER_TO_DB_STATUS[FiveTierVerificationStatus.VERIFIED_OFFICIAL.value],
            FiveTierVerificationStatus.VERIFIED_OFFICIAL.value,
            evidence,
        )

    # Tier 2: VERIFIED_ASSOCIATED
    # External ATS platform or verified corporate foundation
    if (is_ats or is_foundation) and http_status in (200, 201, 301, 302, 307, 308):
        kind = "ATS portal" if is_ats else "Corporate foundation"
        evidence["reason"] = f"Verified associated {kind} ({host}) with HTTP {http_status}"
        return (
            FIVE_TIER_TO_DB_STATUS[FiveTierVerificationStatus.VERIFIED_ASSOCIATED.value],
            FiveTierVerificationStatus.VERIFIED_ASSOCIATED.value,
            evidence,
        )

    # Tier 3: POTENTIALLY_RELEVANT
    # External domain linked from official site, responds HTTP 200, but not verified as official ATS/foundation
    if http_status in (200, 201, 301, 302, 307, 308):
        evidence["reason"] = f"External linked domain ({host}) requiring review"
        return (
            FIVE_TIER_TO_DB_STATUS[FiveTierVerificationStatus.POTENTIALLY_RELEVANT.value],
            FiveTierVerificationStatus.POTENTIALLY_RELEVANT.value,
            evidence,
        )

    # Tier 4: UNVERIFIED
    evidence["reason"] = "Discovered URL candidate awaiting HTTP verification"
    return (
        FIVE_TIER_TO_DB_STATUS[FiveTierVerificationStatus.UNVERIFIED.value],
        FiveTierVerificationStatus.UNVERIFIED.value,
        evidence,
    )
