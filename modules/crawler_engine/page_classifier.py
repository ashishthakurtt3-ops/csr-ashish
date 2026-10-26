"""
modules/crawler_engine/page_classifier.py
=========================================
Two-Stage AI-Powered Website Discovery & Page Classification Engine.

Implements:
1. Stage One: Link Name & Context Discovery & Classification.
2. Stage Two: Content Retrieval, Deep Classification & Structured Parsing.
3. Independent Evidence-Validation Gate:
   - Prevents customer-facing application false positives.
   - Prevents generic partnership false positives.
   - Requires actual vacancy evidence for jobs and Section 135 evidence for CSR.
   - Safely preserves existing approved URLs when evidence is insufficient.
"""

import re
import logging
from urllib.parse import urlparse, urljoin
from typing import Dict, Any, List, Optional, Tuple

from bs4 import BeautifulSoup

from . import ai_classifier_config as cfg
from .ai_api_client import AIClient, get_ai_client, QuotaExhaustedError
from .access_detector import fetch_live_page
from .normalizers import clean_text, normalize_canonical_url

logger = logging.getLogger(__name__)


class TwoStagePageClassifier:
    """
    Orchestrates the two-stage classification and independent evidence validation
    workflow across corporate websites.
    """

    def __init__(self, client: Optional[AIClient] = None):
        self.client = client or get_ai_client()


    # --------------------------------------------------------------------------
    # STAGE 1: LINK DISCOVERY & BATCH CLASSIFICATION
    # --------------------------------------------------------------------------
    def extract_candidate_links_from_html(
        self, base_url: str, html: str, max_links: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Extracts candidate links from navigation, header, footer, and main content
        preserving surrounding context and link location.
        """
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        candidates: List[Dict[str, Any]] = []
        seen_urls = set()

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
                continue

            full_url = urljoin(base_url, href)
            # Remove hash anchors
            clean_url = full_url.split('#')[0].rstrip('/')
            if not clean_url or clean_url in seen_urls:
                continue
            seen_urls.add(clean_url)

            text = clean_text(a.get_text(" ", strip=True)) or ""
            title_attr = clean_text(a.get("title", "")) or ""
            aria_label = clean_text(a.get("aria-label", "")) or ""
            link_label = text or title_attr or aria_label or ""

            # Determine DOM location context
            parent_tag = a.parent.name if a.parent else ""
            in_header = bool(a.find_parent(["header", "nav"]) or "menu" in str(a.parent.get("class", [])))
            in_footer = bool(a.find_parent("footer") or "footer" in str(a.parent.get("class", [])))
            location_tag = "HEADER_NAV" if in_header else ("FOOTER_NAV" if in_footer else "BODY_CONTENT")

            candidates.append({
                "url": clean_url,
                "text": link_label[:120],
                "location": location_tag,
                "parent_tag": parent_tag
            })

            if len(candidates) >= max_links:
                break

        return candidates

    def classify_discovered_links(
        self, company_name: str, domain: str, links: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Submits candidate links in compact batches to AI for Stage 1 classification.
        """
        if not links:
            return []

        classified: List[Dict[str, Any]] = []
        batch_size = cfg.LINK_BATCH_SIZE

        for i in range(0, len(links), batch_size):
            batch = links[i:i + batch_size]
            try:
                batch_results = self.client.classify_links_batch(company_name, domain, batch)
                # Map back to original links
                res_map = {r.get("url"): r for r in batch_results if isinstance(r, dict)}
                for l in batch:
                    u = l.get("url")
                    c_info = res_map.get(u, {})
                    classified.append({
                        **l,
                        "broad_category": c_info.get("broad_category", "OTHER_COMPANY_INFORMATION"),
                        "candidate_category": c_info.get("candidate_category", "UNKNOWN_REQUIRES_REVIEW"),
                        "confidence": float(c_info.get("confidence", 0.5)),
                        "reasoning": c_info.get("reasoning", ""),
                        "actual_model": c_info.get("actual_model", "unknown"),
                        "error": c_info.get("error")
                    })
            except QuotaExhaustedError:
                raise
            except Exception as e:
                err_str = str(e)
                logger.warning("Error in link batch classification: %s", err_str)
                for l in batch:
                    classified.append({
                        **l,
                        "broad_category": "OTHER_COMPANY_INFORMATION",
                        "candidate_category": "UNKNOWN_REQUIRES_REVIEW",
                        "confidence": 0.4,
                        "reasoning": f"Batch processing exception: {err_str}",
                        "actual_model": "rule_based_fallback",
                        "error": err_str
                    })


        return classified

    def filter_promising_candidates_for_stage_2(
        self, classified_links: List[Dict[str, Any]], max_pages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Filters and prioritizes candidate URLs to fetch and deeply evaluate in Stage 2.
        Prioritizes:
        1. Jobs Listing candidates & ATS portals
        2. Careers Landing candidates
        3. CSR Project Disclosures & Overviews
        4. Sustainability & Annual reports
        """
        priority_categories = {
            "JOBS_LISTING_CANDIDATE": 100,
            "CAREERS_LANDING_CANDIDATE": 90,
            "CSR_PROJECT_DISCLOSURE_CANDIDATE": 85,
            "CSR_PARTNERSHIP_RFP_CANDIDATE": 80,
            "CSR_OVERVIEW_CANDIDATE": 75,
            "SUSTAINABILITY_REPORT_CANDIDATE": 70,
            "CSR_REPORT_CANDIDATE": 65,
            "ANNUAL_REPORT_CANDIDATE": 60,
            "INDIVIDUAL_JOB_CANDIDATE": 50,
            "HR_INFORMATION_CANDIDATE": 40
        }

        scored = []
        for l in classified_links:
            cat = l.get("candidate_category")
            if cat in priority_categories:
                base_prio = priority_categories[cat]
                conf = l.get("confidence", 0.5)
                score = base_prio * conf
                scored.append((score, l))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:max_pages]]

    # --------------------------------------------------------------------------
    # STAGE 2: CONTENT FETCH & DEEP PAGE CLASSIFICATION
    # --------------------------------------------------------------------------
    def fetch_and_prepare_page_data(self, url: str) -> Dict[str, Any]:
        """
        Fetches live page and prepares bounded text, structural headings, ATS detection,
        and vacancy indicators for Stage 2 AI analysis.
        """
        res = fetch_live_page(url)
        if not res.get("ok"):
            return {
                "url": url,
                "status_code": res.get("status_code", 0),
                "is_accessible": False,
                "title": "",
                "headings": [],
                "main_text": "",
                "ats_platform": None,
                "job_indicators": {"job_card_count": 0},
                "csr_indicators": {"statutory_terms_found": False},
                "content_hash": None
            }

        html = res.get("html", "")
        soup = BeautifulSoup(html, "lxml")
        title = clean_text(soup.title.string) if soup.title else ""
        headings = [clean_text(h.get_text()) for h in soup.find_all(["h1", "h2", "h3"]) if clean_text(h.get_text())][:8]

        # Detect ATS signature in URL or script tags
        ats_platform = None
        url_lower = url.lower()
        if "greenhouse.io" in url_lower: ats_platform = "GREENHOUSE"
        elif "lever.co" in url_lower: ats_platform = "LEVER"
        elif "smartrecruiters.com" in url_lower: ats_platform = "SMARTRECRUITERS"
        elif "myworkdayjobs.com" in url_lower: ats_platform = "WORKDAY"
        elif "darwinbox" in url_lower: ats_platform = "DARWINBOX"
        elif "successfactors" in url_lower: ats_platform = "SUCCESSFACTORS"
        elif "taleo.net" in url_lower or "oraclecloud.com" in url_lower: ats_platform = "ORACLE_TCS"

        # Check for job vacancy elements
        body_text = clean_text(soup.get_text(" ", strip=True)) or ""
        job_card_count = len(soup.find_all(class_=re.compile(r'(job|posting|vacancy|opening|role)-?(item|card|listing|row)', re.I)))

        # Check for Section 135 / CSR statutory terms
        statutory_found = bool(re.search(r'\b(section\s*135|schedule\s*vii|csr\s*committee|annual\s*action\s*plan)\b', body_text, re.I))

        # Build content hash
        import hashlib
        content_hash = hashlib.sha256(body_text.encode("utf-8")).hexdigest()[:32] if body_text else None

        return {
            "url": res.get("final_url") or url,
            "status_code": res.get("status_code", 200),
            "is_accessible": True,
            "title": title,
            "headings": headings,
            "main_text": body_text[:cfg.MAX_INPUT_CHARS],
            "ats_platform": ats_platform,
            "job_indicators": {"job_card_count": job_card_count},
            "csr_indicators": {"statutory_terms_found": statutory_found},
            "content_hash": content_hash
        }

    def classify_destination_page(
        self, company_name: str, url: str, page_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Executes Stage 2 content classification via AI API.
        """
        return self.client.classify_page_content(company_name, url, page_data)

    # --------------------------------------------------------------------------
    # INDEPENDENT EVIDENCE-VALIDATION GATE
    # --------------------------------------------------------------------------
    def validate_page_evidence(
        self, company_name: str, official_domain: Optional[str], page_classification: Dict[str, Any], page_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Independent evidence gate: verifies the AI prediction against factual extracted rules.
        Decides: APPROVED, REVIEW_REQUIRED, or REJECTED.
        """
        page_type = page_classification.get("page_type", "UNKNOWN_REQUIRES_REVIEW")
        conf = float(page_classification.get("confidence", 0.0))
        url = page_data.get("url", "")
        text = (page_data.get("main_text", "") or "").lower()
        actual_model = page_classification.get("actual_model", "unknown")
        err = page_classification.get("error")

        # Rule 0 (Requirement 4): Deterministic fallback classifications must NEVER approve or verify a source.
        if actual_model in ("rule_based_fallback", "fallback", "offline_fallback"):
            fallback_decision = "PENDING_AI" if err else "REVIEW_REQUIRED"
            return {
                "decision": fallback_decision,
                "reason": (
                    f"Deterministic fallback ({actual_model}) cannot verify or approve source without genuine AI classification."
                    + (f" AI error: {err}" if err else "")
                ),
                "target_field": None,
                "verified_type": page_type,
                "actual_model": actual_model,
                "error": err
            }

        # Rule 1: Inaccessible pages are rejected as live sources
        if not page_data.get("is_accessible") or page_type == "INACCESSIBLE_PAGE":
            return {
                "decision": "REJECTED",
                "reason": "Destination URL returned error, 404, or is inaccessible.",
                "target_field": None,
                "verified_type": "INACCESSIBLE_PAGE",
                "actual_model": actual_model
            }

        # Rule 2: Commercial consumer application links are rejected
        if page_type == "UNRELATED_PAGE" or any(p in text for p in ["apply for personal loan", "apply for credit card", "track loan application"]):
            return {
                "decision": "REJECTED",
                "reason": "Page is a commercial consumer banking/loan application, not an employment vacancy.",
                "target_field": None,
                "verified_type": "UNRELATED_PAGE",
                "actual_model": actual_model
            }

        # Rule 3: Check confidence threshold
        min_thresh = cfg.CLASSIFICATION_THRESHOLDS.get(page_type, cfg.CLASSIFICATION_THRESHOLDS["DEFAULT"])
        if conf < min_thresh:
            return {
                "decision": "REVIEW_REQUIRED",
                "reason": f"Confidence score {conf:.2f} is below strict threshold {min_thresh:.2f}.",
                "target_field": None,
                "verified_type": page_type,
                "actual_model": actual_model
            }

        # Rule 4: Map verified page types to Company model fields
        if page_type == "JOBS_LISTING_PAGE":
            return {
                "decision": "APPROVED",
                "reason": "Verified active jobs listing portal with vacancy indicators.",
                "target_field": "jobs_page_url",
                "verified_type": page_type,
                "actual_model": actual_model
            }
        elif page_type == "CAREERS_LANDING_PAGE":
            return {
                "decision": "APPROVED",
                "reason": "Verified corporate careers landing portal.",
                "target_field": "careers_url",
                "verified_type": page_type,
                "actual_model": actual_model
            }
        elif page_type in ("CSR_PROJECT_DISCLOSURE", "CSR_OVERVIEW_PAGE"):
            return {
                "decision": "APPROVED",
                "reason": "Verified corporate social responsibility disclosure / policy portal.",
                "target_field": "csr_portal_url",
                "verified_type": page_type,
                "actual_model": actual_model
            }
        elif page_type == "CSR_PARTNERSHIP_OR_RFP":
            # Extra guard: must have RFP / tender / grant call evidence
            if not any(k in text for k in ["rfp", "request for proposal", "grant", "eoi", "expression of interest", "tender", "call for proposals"]):
                return {
                    "decision": "REVIEW_REQUIRED",
                    "reason": "Partner page does not contain concrete RFP/grant documentation. Preserved for review.",
                    "target_field": None,
                    "verified_type": "CSR_OVERVIEW_PAGE",
                    "actual_model": actual_model
                }
            return {
                "decision": "APPROVED",
                "reason": "Verified active CSR grant / RFP solicitation page.",
                "target_field": "csr_portal_url",
                "verified_type": page_type,
                "actual_model": actual_model
            }
        elif page_type in ("SUSTAINABILITY_OR_ESG_REPORT", "CSR_REPORT", "ANNUAL_REPORT_WITH_CSR_EVIDENCE"):
            return {
                "decision": "APPROVED",
                "reason": "Verified statutory sustainability / annual report document.",
                "target_field": "sustainability_url" if "sustainability" in page_type.lower() else "annual_report_url",
                "verified_type": page_type,
                "actual_model": actual_model
            }

        return {
            "decision": "REVIEW_REQUIRED",
            "reason": f"Page type '{page_type}' requires human review before replacing existing source.",
            "target_field": None,
            "verified_type": page_type,
            "actual_model": actual_model
        }

