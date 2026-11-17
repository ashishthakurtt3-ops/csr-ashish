"""
tests_pure/test_m3_four_remaining_items.py
==========================================
Targeted unit & integration tests covering all 4 completed items:
1. Multi-Category URL Classification across all 17 corporate categories
   (Leadership, Management, Business Segments, Products, Locations, Contact,
   Media/News, Policies, Compliance, Procurement, Suppliers, Tenders, etc.)
2. 5-Tier URL Verification Status Taxonomy:
   VERIFIED_OFFICIAL, VERIFIED_ASSOCIATED, POTENTIALLY_RELEVANT, UNVERIFIED, BROKEN_OR_INACCESSIBLE.
3. Page-by-page PDF Text and Table Extraction preserving page numbers and citations.
4. Standard Processing Outcome code alignment and bidirectional compatibility.
"""
import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path and Django is initialized
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

try:
    django.setup()
except Exception:
    pass

from modules.crawler_engine.url_classifier import (
    classify_url,
    determine_5tier_verification_status,
    FiveTierVerificationStatus,
    FIVE_TIER_TO_DB_STATUS,
    ClassificationResult,
)
from modules.crawler_engine.pdf_extractor import (
    PDFReportExtractor,
    ExtractedPDFResult,
)
from modules.admin_panel.services.batch_discovery_service import (
    ProcessingOutcome,
    BatchDiscoveryService,
)


class TestItem1UrlClassification(unittest.TestCase):
    """Item 1: Complete classification of all remaining important company URLs."""

    def test_01_leadership_and_management_classification(self):
        # Leadership
        res = classify_url("https://www.company.com/about/leadership", link_text="Board of Directors")
        self.assertEqual(res.primary_category, "LEADERSHIP")
        self.assertEqual(res.detailed_classification, "LEADERSHIP")
        self.assertGreaterEqual(res.confidence, 0.70)

        # Management
        res_m = classify_url("https://www.company.com/company/management-team", link_text="Executive Committee")
        self.assertEqual(res_m.primary_category, "MANAGEMENT")
        self.assertEqual(res_m.detailed_classification, "MANAGEMENT")
        self.assertGreaterEqual(res_m.confidence, 0.70)

    def test_02_business_segments_and_products_classification(self):
        # Business Segments
        res_b = classify_url("https://www.company.com/business-segments", link_text="Operating Divisions")
        self.assertEqual(res_b.primary_category, "BUSINESS_SEGMENTS")
        self.assertEqual(res_b.detailed_classification, "BUSINESS_SEGMENTS")

        # Products & Services
        res_p = classify_url("https://www.company.com/products-and-services", link_text="Our Capabilities")
        self.assertEqual(res_p.primary_category, "PRODUCTS_SERVICES")
        self.assertEqual(res_p.detailed_classification, "PRODUCTS_SERVICES")

    def test_03_locations_and_contact_classification(self):
        # Locations
        res_l = classify_url("https://www.company.com/our-locations", link_text="Global Presence & Offices")
        self.assertEqual(res_l.primary_category, "LOCATIONS")

        # Contact
        res_c = classify_url("https://www.company.com/contact-us", link_text="Customer Support")
        self.assertEqual(res_c.primary_category, "CONTACT")

    def test_04_media_policies_compliance_classification(self):
        # Media & News
        res_m = classify_url("https://www.company.com/media/press-releases", link_text="Newsroom")
        self.assertEqual(res_m.primary_category, "MEDIA_NEWS")

        # Policies
        res_pol = classify_url("https://www.company.com/corporate-policies/code-of-conduct", link_text="Ethics Policy")
        self.assertEqual(res_pol.primary_category, "POLICIES")

        # Compliance
        res_cmp = classify_url("https://www.company.com/investors/statutory-compliance", link_text="Regulatory Filings")
        self.assertEqual(res_cmp.primary_category, "COMPLIANCE")

    def test_05_procurement_suppliers_tenders_classification(self):
        # Procurement
        res_prc = classify_url("https://www.company.com/procurement", link_text="Supply Chain Partners")
        self.assertEqual(res_prc.primary_category, "PROCUREMENT")

        # Supplier Registration
        res_sup = classify_url("https://www.company.com/vendor-portal/supplier-registration", link_text="Vendor Enrolment")
        self.assertEqual(res_sup.primary_category, "SUPPLIER_REGISTRATION")

        # Tenders
        res_tnd = classify_url("https://www.company.com/active-tenders", link_text="Bids and RFP Notices")
        self.assertEqual(res_tnd.primary_category, "TENDERS")


class TestItem2FiveTierVerification(unittest.TestCase):
    """Item 2: Implement complete 5-tier URL verification status system."""

    def test_01_verified_official_tier(self):
        db_s, label, ev = determine_5tier_verification_status(
            "https://www.tcs.com/leadership", "tcs.com", http_status=200
        )
        self.assertEqual(label, FiveTierVerificationStatus.VERIFIED_OFFICIAL.value)
        self.assertEqual(db_s, "APPROVED")
        self.assertTrue(ev["is_ats"] is False)

    def test_02_verified_associated_tier(self):
        db_s, label, ev = determine_5tier_verification_status(
            "https://tcs.taleo.net/careers", "tcs.com", http_status=200, is_ats=True
        )
        self.assertEqual(label, FiveTierVerificationStatus.VERIFIED_ASSOCIATED.value)
        self.assertEqual(db_s, "APPROVED")

    def test_03_potentially_relevant_tier(self):
        db_s, label, ev = determine_5tier_verification_status(
            "https://external-directory.com/listing", "tcs.com", http_status=200
        )
        self.assertEqual(label, FiveTierVerificationStatus.POTENTIALLY_RELEVANT.value)
        self.assertEqual(db_s, "REVIEW_REQUIRED")

    def test_04_unverified_tier(self):
        db_s, label, ev = determine_5tier_verification_status(
            "https://www.tcs.com/unprobed-path", "tcs.com", http_status=None, is_unverified=True
        )
        self.assertEqual(label, FiveTierVerificationStatus.UNVERIFIED.value)
        self.assertEqual(db_s, "DISCOVERED")

    def test_05_broken_or_inaccessible_tier(self):
        db_s, label, ev = determine_5tier_verification_status(
            "https://www.tcs.com/dead-link", "tcs.com", http_status=404, is_accessible=False
        )
        self.assertEqual(label, FiveTierVerificationStatus.BROKEN_OR_INACCESSIBLE.value)
        self.assertEqual(db_s, "INACCESSIBLE")

        # Soft-404 detection
        db_s, label, ev = determine_5tier_verification_status(
            "https://www.tcs.com/page", "tcs.com", http_status=200, title="404 Not Found"
        )
        self.assertEqual(label, FiveTierVerificationStatus.BROKEN_OR_INACCESSIBLE.value)
        self.assertEqual(db_s, "INACCESSIBLE")


class TestItem3PageByPagePdfExtraction(unittest.TestCase):
    """Item 3: Integrate page-by-page PDF text and table extraction."""

    def test_01_extracted_pdf_result_hybrid_behavior(self):
        res = ExtractedPDFResult(
            "Combined full text of document.",
            pages=[{"page_number": 1, "text": "Page 1 text"}],
            page_citations="[Page 1] Page 1 text",
            tables=[{"page_number": 1, "summary": "Sample Table"}],
            page_count=1,
        )
        # Verify raw string transparency
        self.assertTrue(isinstance(res, str))
        self.assertIn("Combined full text", res)
        self.assertEqual(len(res), 31)

        # Verify structured attributes
        self.assertEqual(res.page_count, 1)
        self.assertEqual(len(res.pages), 1)
        self.assertEqual(res.pages[0]["page_number"], 1)
        self.assertEqual(res.tables[0]["summary"], "Sample Table")
        self.assertIn("[Page 1]", res.page_citations)

    def test_02_table_and_statutory_extraction(self):
        extractor = PDFReportExtractor(max_pages=5)
        text_with_table = (
            "Annual CSR Report 2024\n"
            "Pursuant to Section 135 of the Companies Act, 2013, the CSR Committee presents this report.\n"
            "The company spent INR 45.50 Crore during FY2024.\n\n"
            "CSR Project Expenditure Table:\n"
            "Project Description     State          Budget (INR Cr)    Actual Spent (INR Cr)\n"
            "Healthcare Clinics      Odisha         15.00              14.80\n"
            "Primary Education       Bihar          20.00              19.50\n"
            "Clean Water Project     Rajasthan      10.50              10.20\n\n"
            "All projects adhere to Schedule VII of the Act."
        )
        tables = extractor._detect_tables(text_with_table, page_num=7)
        evidence = extractor._extract_page_evidence(text_with_table, page_num=7)

        self.assertGreaterEqual(len(tables), 1)
        self.assertEqual(tables[0]["page_number"], 7)
        self.assertGreaterEqual(tables[0]["row_count"], 3)

        self.assertGreaterEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["page_number"], 7)
        self.assertTrue(any("135" in ev["snippet"] or "INR" in ev["snippet"] for ev in evidence))


class TestItem4ProcessingOutcomeAlignment(unittest.TestCase):
    """Item 4: Align processing outcomes with required standard status codes."""

    def test_01_bidirectional_equality(self):
        # SUCCESS_WITH_RESULTS == SUCCESS_WITH_DATA
        po_results = ProcessingOutcome("SUCCESS_WITH_RESULTS")
        self.assertEqual(po_results, "SUCCESS_WITH_RESULTS")
        self.assertEqual(po_results, "SUCCESS_WITH_DATA")

        # SUCCESS_NO_RESULTS == SUCCESS_NO_DATA
        po_no_results = ProcessingOutcome("SUCCESS_NO_RESULTS")
        self.assertEqual(po_no_results, "SUCCESS_NO_RESULTS")
        self.assertEqual(po_no_results, "SUCCESS_NO_DATA")

        # Standard codes
        self.assertEqual(ProcessingOutcome("PARTIAL_SUCCESS"), "PARTIAL_SUCCESS")
        self.assertEqual(ProcessingOutcome("FETCH_FAILED"), "FETCH_FAILED")
        self.assertEqual(ProcessingOutcome("VALIDATION_FAILED"), "VALIDATION_FAILED")
        self.assertEqual(ProcessingOutcome("DOCUMENT_PROCESSING_FAILED"), "DOCUMENT_PROCESSING_FAILED")
        self.assertEqual(ProcessingOutcome("DATABASE_SAVE_FAILED"), "DATABASE_SAVE_FAILED")

    def test_02_dictionary_lookup_and_serialization(self):
        payload = {
            "outcome": ProcessingOutcome("SUCCESS_WITH_RESULTS"),
            "standard_outcome": "SUCCESS_WITH_DATA",
            "outcome_code": "SUCCESS_WITH_DATA",
        }
        self.assertEqual(payload.get("outcome"), "SUCCESS_WITH_RESULTS")
        self.assertEqual(payload.get("outcome"), "SUCCESS_WITH_DATA")
        self.assertEqual(payload.get("standard_outcome"), "SUCCESS_WITH_DATA")


if __name__ == "__main__":
    unittest.main()
