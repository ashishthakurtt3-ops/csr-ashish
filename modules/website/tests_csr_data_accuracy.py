"""
Regression & Data Integrity Test Suite for CSR Projects Pipeline and View Section.

Tests:
1. Universal 10-column CSR listing API response and serialization.
2. Single CSR project detail API (/csr/projects/<int:csr_id>) returning full Sections A-I data.
3. Elimination of malformed budgets ('rs,', 'NaN', 'None', invalid commas) and proper formatting.
4. Publication status filtering (only PUBLISHED projects visible, REJECTED and LEGACY_UNVERIFIED quarantined).
5. Schedule VII classification priority and accuracy (e.g. STEM/education vs healthcare).
6. Implementing partner and reporting period extraction.
7. Related projects strictly scoped to the same company.
8. Search and filter query parameter handling.
"""

import json
from django.test import TestCase, Client
from django.utils import timezone

from modules.admin_panel.models import Company, CSRProject
from modules.website.views.opportunity_api_views import (
    serialize_project_item,
    get_schedule_vii_classification,
    extract_implementing_partner,
    extract_reporting_period,
)
from modules.crawler_engine.parsers.corporate import BUDGET_REGEX, JUNK_CSR_TITLE_PATTERNS
from modules.crawler_engine.parsers.csr_pdf import BUDGET_PATTERN, PDF_JUNK_PATTERNS


class CsrDataAccuracyTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.company_au = Company.objects.create(
            company_id="AUBANK",
            company_name="AU Small Finance Bank Limited",
            nse_symbol="AUBANK",
            website_url="https://www.aubank.in",
            careers_url="https://www.aubank.in/careers",
            sector="Banking / Financial Services",
            headquarters="Jaipur, Rajasthan",
            crawl_status="CRAWLED",
        )
        self.company_titan = Company.objects.create(
            company_id="TITAN",
            company_name="Titan Company Limited",
            nse_symbol="TITAN",
            website_url="https://www.titancompany.in",
            careers_url="https://www.titancompany.in/careers",
            sector="Consumer Goods / Jewellery",
            headquarters="Bengaluru, Karnataka",
            crawl_status="CRAWLED",
        )

        now = timezone.now()

        # 1. Authentic AU Bank Project (Education / Dakshana)
        self.au_dakshana = CSRProject.objects.create(
            company=self.company_au,
            project_name="AU Ignite - Dakshana",
            category="Education",
            description="Preparation of underprivileged rural students for engineering and medical entrance examinations (IIT-JEE & NEET) with Dakshana Foundation in residential campuses across FY 2023-24.",
            geographic_location="Pune, Maharashtra & Jodhpur, Rajasthan",
            state="Maharashtra",
            budget="₹ 1,25,00,000",
            discovered_date="FY 2023-24",
            source_url="https://www.aubank.in/csr-annual-report-2023-24.pdf",
            evidence_locator="AU Foundation Annual Report 2023-24, Page 28",
            evidence_text="AU Ignite - Dakshana Foundation partnership for rural youth IIT-JEE/NEET education support.",
            retrieved_at=now,
            verification_status="SOURCE_CONFIRMED",
            confidence=0.95,
        )
        self.au_dakshana.verification_status = "PUBLISHED"
        self.au_dakshana.save()

        # 2. Second AU Bank Project for related projects test
        self.au_bano_champion = CSRProject.objects.create(
            company=self.company_au,
            project_name="Bano Champion - Rural Sports Initiative",
            category="Sports Promotion",
            description="Grassroots sports coaching and tournaments for youth in rural Rajasthan.",
            geographic_location="Dausa, Rajasthan",
            state="Rajasthan",
            budget="8500000",
            discovered_date="2023-24",
            source_url="https://www.aubank.in/csr/bano-champion",
            evidence_locator="AU Foundation Sports Report",
            evidence_text="AU Bano Champion rural sports initiative across Rajasthan districts.",
            retrieved_at=now,
            verification_status="SOURCE_CONFIRMED",
            confidence=0.92,
        )
        self.au_bano_champion.verification_status = "PUBLISHED"
        self.au_bano_champion.save()

        # 3. Authentic Titan Project
        self.titan_kanya = CSRProject.objects.create(
            company=self.company_titan,
            project_name="Titan Kanya - Educating the Girl Child",
            category="Women Empowerment",
            description="Remedial education and life skills support for girl students across government schools in partnership with Akshaya Patra Foundation.",
            geographic_location="Krishnagiri, Tamil Nadu",
            state="Tamil Nadu",
            budget="35000000",
            discovered_date="2022-23",
            source_url="https://www.titancompany.in/csr/kanya",
            evidence_locator="Titan Sustainability Report 2022-23",
            evidence_text="Titan Kanya initiative empowering girl child education in Tamil Nadu schools.",
            retrieved_at=now,
            verification_status="SOURCE_CONFIRMED",
            confidence=0.98,
        )
        self.titan_kanya.verification_status = "PUBLISHED"
        self.titan_kanya.save()

        # 4. Quarantined / Rejected Synthetic Record (should NOT appear in public APIs)
        self.rejected_project = CSRProject.objects.create(
            company=self.company_au,
            project_name="Community Welfare Initiative - AU Bank",
            category="Community Development",
            description="Synthetic placeholder template created in previous test fixtures.",
            geographic_location="Jaipur",
            budget="500000",
            evidence_text="Quarantined synthetic entry",
            retrieved_at=now,
            verification_status="REJECTED",
        )

        # 5. Legacy Unverified Record (should NOT appear in public APIs)
        self.legacy_project = CSRProject.objects.create(
            company=self.company_titan,
            project_name="Titan Legacy Untracked Program",
            category="Others",
            description="Legacy record without confirmed primary source.",
            geographic_location="Bengaluru",
            budget="None",
            retrieved_at=now,
            verification_status="LEGACY_UNVERIFIED",
        )

    def test_parsers_reject_malformed_budget_and_junk_titles(self):
        """Test parser regex rejects 'rs,', isolated commas, and template junk titles."""
        # 1. Malformed budget strings must not produce valid digits
        malformed_strings = ["rs,", "Rs,", "Rs. ,", "NaN", "None", "(Rs, in Lakhs)"]
        for s in malformed_strings:
            m = BUDGET_REGEX.search(s)
            has_valid_digit_budget = False
            if m:
                cand = m.group(0).strip()
                has_valid_digit_budget = any(c.isdigit() for c in cand) and cand.lower() not in ('rs,', 'inr,', 'nan', 'none')
            self.assertFalse(has_valid_digit_budget, f"Malformed budget '{s}' should not yield valid budget")

        # 2. Valid budget strings must match with digits
        valid_samples = ["₹ 1,50,00,000", "Rs. 45.5 Lakhs", "₹ 12.50 Cr", "INR 50,00,000"]
        for s in valid_samples:
            m = BUDGET_REGEX.search(s)
            self.assertIsNotNone(m, f"Valid budget '{s}' should match BUDGET_REGEX")
            cand = m.group(0).strip()
            self.assertTrue(any(c.isdigit() for c in cand))

        # 3. Junk titles must match JUNK_CSR_TITLE_PATTERNS or PDF_JUNK_PATTERNS
        junk_titles = [
            "Community Development Initiative - Adani Enterprises",
            "Healthcare Support Initiative - ABC Ltd",
            "Table of Contents",
            "Notice of 30th Annual General Meeting",
            "CSR Committee Composition and Terms",
            "Great Place to Work Certified 2024",
            "Safety First - Towards Zero Harm",
        ]
        for title in junk_titles:
            is_junk = any(pat.search(title) for pat in JUNK_CSR_TITLE_PATTERNS) or any(pat.search(title) for pat in PDF_JUNK_PATTERNS)
            self.assertTrue(is_junk, f"'{title}' should be identified as junk title")

        # 4. Legitimate project titles must NOT match junk patterns
        valid_titles = [
            "AU Ignite - Dakshana",
            "Titan Kanya - Educating the Girl Child",
            "Mobile Medical Unit - Health on Wheels",
            "Water Conservation Project",
        ]
        for title in valid_titles:
            is_junk = any(pat.search(title) for pat in JUNK_CSR_TITLE_PATTERNS)
            self.assertFalse(is_junk, f"'{title}' should NOT be identified as junk title")

    def test_schedule_vii_classification_priority(self):
        """Test Schedule VII mapping respects category priority over incidental keywords."""
        # Project category 'Education' with medical entrance in description
        # must map to Item (ii) Education, NOT Item (i) Healthcare
        sched_vii = get_schedule_vii_classification(self.au_dakshana.category, self.au_dakshana.description)
        self.assertIn("Item (ii)", sched_vii)
        self.assertIn("education", sched_vii.lower())

        # Women empowerment project
        sched_vii_kanya = get_schedule_vii_classification(self.titan_kanya.category, self.titan_kanya.description)
        self.assertIn("Item (iii)", sched_vii_kanya)
        self.assertIn("women", sched_vii_kanya.lower())

        # Sports promotion project
        sched_vii_sports = get_schedule_vii_classification(self.au_bano_champion.category, self.au_bano_champion.description)
        self.assertIn("Item (vii)", sched_vii_sports)
        self.assertIn("sports", sched_vii_sports.lower())

    def test_implementing_partner_extraction(self):
        """Test regex extraction of implementing NGO / Foundation partners from text."""
        partner_dakshana = extract_implementing_partner(self.au_dakshana.project_name, self.au_dakshana.description)
        self.assertIsNotNone(partner_dakshana)
        self.assertIn("Dakshana", partner_dakshana)

        partner_kanya = extract_implementing_partner(self.titan_kanya.project_name, self.titan_kanya.description)
        self.assertIsNotNone(partner_kanya)
        self.assertEqual(partner_kanya, "Akshaya Patra Foundation")

    def test_reporting_period_extraction(self):
        """Test reporting period extraction from discovered_date and text."""
        period = extract_reporting_period(self.au_dakshana.discovered_date, self.au_dakshana.description)
        self.assertEqual(period, "FY 2023-24")

    def test_serialization_enforces_universal_columns_and_clean_data(self):
        """Test serialize_project_item delivers all 10 universal columns and sanitized values."""
        item = serialize_project_item(self.au_dakshana)
        
        # Verify core identity & universal column fields
        self.assertEqual(item["company_name"], "AU Small Finance Bank Limited")
        self.assertEqual(item["project_name"], "AU Ignite - Dakshana")
        self.assertEqual(item["category"], "Education")
        self.assertEqual(item["normalized_category"], "Education & Skill Development")
        self.assertIn("Item (ii)", item["schedule_vii_classification"])
        self.assertEqual(item["geographic_location"], "Pune, Maharashtra & Jodhpur, Rajasthan")
        self.assertEqual(item["budget"], "₹ 1,25,00,000")
        self.assertEqual(item["reporting_period"], "FY 2023-24")

        # Verify budget is never 'rs,' or 'None'
        self.assertNotIn("rs,", str(item["budget"]).lower())

        # Test project with malformed budget value gets sanitized to None
        self.au_dakshana.budget = "rs,"
        item_malformed = serialize_project_item(self.au_dakshana)
        self.assertIsNone(item_malformed["budget"])

    def test_csr_projects_api_listing_strict_published_filter(self):
        """Test /csr/projects returns only PUBLISHED items and excludes REJECTED/LEGACY."""
        response = self.client.get("/csr/projects?page=1")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("items", data)
        self.assertEqual(data["total"], 3)  # Only the 3 published projects
        
        project_names = [p["project_name"] for p in data["items"]]
        self.assertIn("AU Ignite - Dakshana", project_names)
        self.assertIn("Bano Champion - Rural Sports Initiative", project_names)
        self.assertIn("Titan Kanya - Educating the Girl Child", project_names)
        
        # Quarantined & legacy items must NOT be present
        self.assertNotIn("Community Welfare Initiative - AU Bank", project_names)
        self.assertNotIn("Titan Legacy Untracked Program", project_names)

    def test_csr_projects_api_search_and_category_filter(self):
        """Test /csr/projects search and category filtering."""
        # Search by company name
        response = self.client.get("/csr/projects?page=1&q=Titan")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["project_name"], "Titan Kanya - Educating the Girl Child")

        # Search by project title
        response = self.client.get("/csr/projects?page=1&q=Dakshana")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["project_name"], "AU Ignite - Dakshana")

        # Filter by category
        response = self.client.get("/csr/projects?page=1&category=Education")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["items"][0]["project_name"], "AU Ignite - Dakshana")

    def test_csr_project_detail_api_endpoint(self):
        """Test /csr/projects/<int:csr_id> returns complete Sections A-I data and scoped related projects."""
        url = f"/csr/projects/{self.au_dakshana.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        project = data
        self.assertIn("project_name", project)
        
        # Section A: Project Header
        self.assertEqual(project["project_name"], "AU Ignite - Dakshana")
        self.assertEqual(project["company_name"], "AU Small Finance Bank Limited")
        self.assertEqual(project["sector"], "Banking / Financial Services")
        self.assertEqual(project["headquarters"], "Jaipur, Rajasthan")
        
        # Section B: Overview
        self.assertIn("underprivileged rural students", project["description"])
        
        # Section C: CSR Classification
        self.assertEqual(project["category"], "Education")
        self.assertIn("Item (ii)", project["schedule_vii_classification"])
        
        # Section D: Geographic Coverage
        self.assertEqual(project["geographic_location"], "Pune, Maharashtra & Jodhpur, Rajasthan")
        
        # Section E: Financial Details
        self.assertEqual(project["budget"], "₹ 1,25,00,000")
        
        # Section H: Audit & Evidence
        self.assertEqual(project["evidence_locator"], "AU Foundation Annual Report 2023-24, Page 28")
        self.assertEqual(project["source_url"], "https://www.aubank.in/csr-annual-report-2023-24.pdf")
        self.assertEqual(project["verification_status"], "PUBLISHED")

        # Section I: Related Projects strictly from AU Bank (should include Bano Champion, NOT Titan Kanya)
        related = data["related_projects"]
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0]["project_name"], "Bano Champion - Rural Sports Initiative")
        self.assertEqual(related[0]["company_name"], "AU Small Finance Bank Limited")

    def test_csr_project_detail_api_404_on_invalid_or_rejected(self):
        """Test /csr/projects/<int:csr_id> returns 404 for rejected or non-existent IDs."""
        # Non-existent ID
        resp_404 = self.client.get("/csr/projects/999999")
        self.assertEqual(resp_404.status_code, 404)

        # Quarantined / Rejected ID
        resp_rejected = self.client.get(f"/csr/projects/{self.rejected_project.pk}")
        self.assertEqual(resp_rejected.status_code, 404)
