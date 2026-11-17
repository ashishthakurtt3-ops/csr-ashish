"""
Unit tests for the Autonomous Company URL Discovery Engine additions:
- Discovered URLs serialization across categories
- Export endpoints: CSV and Excel (.xlsx)
- Decoupled URLs Only mode (robots.txt, sitemaps, navigation without heavy data extraction)
"""

import io
import json
from unittest import TestCase
from unittest.mock import patch, MagicMock

import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from modules.admin_panel.models import Company, CompanySource, User
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.admin_panel.views.batch_discovery_views import (
    export_discovered_urls_csv_api,
    export_discovered_urls_excel_api,
    recent_dossiers_api,
)


class AutonomousUrlDiscoveryEngineTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_user = User(username='test_admin', is_staff=True, is_superuser=True)

    def test_01_serialize_company_sources_structure(self):
        """Verifies _serialize_company_sources returns category-mapped, 5-tier verified items."""
        mock_comp = MagicMock()
        mock_source = MagicMock()
        mock_source.source_id = 999
        mock_source.final_url = "https://example.com/careers"
        mock_source.original_url = "https://example.com/careers"
        mock_source.source_type = "CAREERS_LANDING"
        mock_source.detailed_classification = "Careers Portal"
        mock_source.link_text = "Join Our Team"
        mock_source.discovery_method = "HEADER_NAV"
        mock_source.verification_status = "APPROVED"
        mock_source.confidence = 0.98
        mock_source.last_verified_at = None
        mock_source.classification_json = {
            "primary_category": "CAREERS",
            "verification_status_label": "Verified Official Company URL",
        }

        with patch("modules.admin_panel.models.CompanySource.objects.filter") as mock_filter:
            mock_filter.return_value.order_by.return_value = [mock_source]
            results = BatchDiscoveryService._serialize_company_sources(mock_comp)

        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertEqual(item["category"], "Careers & Recruitment")
        self.assertEqual(item["final_url"], "https://example.com/careers")
        self.assertEqual(item["verification_status_label"], "Verified Official Company URL")
        self.assertEqual(item["discovery_method"], "HEADER_NAV")
        self.assertEqual(item["confidence"], 0.98)

    def test_02_export_urls_csv_endpoint(self):
        """Verifies export_discovered_urls_csv_api returns 200 with CSV headers."""
        req = self.factory.get("/admin-portal/ai-discovery/export-urls/csv/")
        req.user = self.admin_user

        mock_source = {
            "source_id": 1,
            "final_url": "https://company.com/sustainability",
            "category": "ESG & Sustainability",
            "detailed_classification": "Sustainability Initiatives",
            "link_text": "Sustainability",
            "verification_status": "APPROVED",
            "verification_status_label": "Verified Official Company URL",
            "discovery_method": "FOOTER_NAV",
            "confidence": 0.95,
            "last_verified_at": "2026-11-17T10:00:00",
        }

        with patch("modules.admin_panel.services.batch_discovery_service.BatchDiscoveryService._serialize_company_sources", return_value=[mock_source]):
            resp = export_discovered_urls_csv_api(req)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("Content-Disposition", resp)
        self.assertIn("attachment; filename=", resp["Content-Disposition"])
        content = resp.content.decode("utf-8")
        self.assertIn("Company Name,Official Base URL,Discovered URL", content)
        self.assertIn("https://company.com/sustainability", content)
        self.assertIn("ESG & Sustainability", content)

    def test_03_export_urls_excel_endpoint(self):
        """Verifies export_discovered_urls_excel_api returns 200 with xlsx MIME type."""
        req = self.factory.get("/admin-portal/ai-discovery/export-urls/excel/")
        req.user = self.admin_user

        mock_source = {
            "source_id": 2,
            "final_url": "https://company.com/investor-relations",
            "category": "Investor Relations & Reports",
            "detailed_classification": "Annual Reports",
            "link_text": "Investor Reports",
            "verification_status": "APPROVED",
            "verification_status_label": "Verified Official Company URL",
            "discovery_method": "HEADER_NAV",
            "confidence": 0.99,
            "last_verified_at": "2026-11-17T10:00:00",
        }

        with patch("modules.admin_panel.services.batch_discovery_service.BatchDiscoveryService._serialize_company_sources", return_value=[mock_source]):
            resp = export_discovered_urls_excel_api(req)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("openxmlformats", resp["Content-Type"])
        self.assertIn(".xlsx", resp["Content-Disposition"])
        self.assertGreater(len(resp.content), 2000)

    def test_04_urls_only_mode_execution(self):
        """Verifies process_single_company honors urls_only: skips deep extraction and returns sources."""
        task = {
            "company_name": "Acme Corp",
            "homepage_url": "https://www.acme.com",
            "website_url": "https://www.acme.com",
        }
        options = {
            "urls_only": True,
            "extract_jobs": True,  # should be overridden to False
            "extract_csr": True,   # should be overridden to False
        }

        dummy_company = MagicMock()
        dummy_company.company_id = "COMP_TEST_ACME_001"
        dummy_company.company_name = "Acme Corp"
        dummy_company.website_url = "https://www.acme.com"
        dummy_company.careers_url = "https://www.acme.com/careers"
        dummy_company.csr_portal_url = None
        dummy_company.official_domain = "acme.com"
        dummy_company.sector = "Technology"
        dummy_company.headquarters = "India"
        dummy_company.nse_symbol = None
        dummy_company.verification_status = "PUBLISHED"
        dummy_company.source_registry.count.return_value = 1
        dummy_company.jobs.all.return_value.order_by.return_value.values.return_value = []
        dummy_company.csr_projects.all.return_value.order_by.return_value.values.return_value = []

        with patch.object(BatchDiscoveryService, "fetch_page_content", return_value=("<html><a href='/careers'>Careers</a></html>", "Text", 200)), \
             patch.object(BatchDiscoveryService, "normalize_and_validate_company", return_value=(True, "https://www.acme.com", "acme.com", None)), \
             patch("modules.admin_panel.models.Company.objects.filter") as mock_comp_filter, \
             patch.object(BatchDiscoveryService, "_fetch_sitemap_urls", return_value=[]), \
             patch.object(BatchDiscoveryService, "_classify_and_persist_navigation_sources", return_value=5), \
             patch.object(BatchDiscoveryService, "_serialize_company_sources", return_value=[{"final_url": "https://www.acme.com/careers"}]):

            mock_comp_filter.return_value.first.return_value = dummy_company

            result = BatchDiscoveryService.process_single_company(task, options)

            self.assertEqual(result["status"], "success")
            self.assertEqual(len(result["sources"]), 1)
            self.assertEqual(result["sources"][0]["final_url"], "https://www.acme.com/careers")
            self.assertEqual(result["jobs_discovered"], 0)  # Skipped as requested
            self.assertEqual(result["csr_discovered"], 0)   # Skipped as requested
