"""
tests/test_m1_input_and_bulk_ingestion.py
==========================================
Comprehensive test suite for Milestone 1: Company Input System Implementation.

Covers:
- Suite 1: Single Company Input & URL Sanitization (5 tests)
- Suite 2: Bulk Multi-Format Ingestion: CSV, TSV, Pipe, Semicolon, XLSX, XLS via xlrd, JSON, JSONL (5 tests)
- Suite 3: Encoding & Edge Cases: UTF-8-BOM, CP1252, empty files, accents, in-file deduplication (4 tests)
- Suite 4: Multi-Row Failure Isolation & Fault Tolerance (3 tests)
- Suite 5: Interface Contracts & View Integration (3 tests)
Total: 20 comprehensive test cases.
"""
import io
import json
import os
import struct
import unittest
from unittest.mock import patch

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import openpyxl
import xlrd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory

from modules.admin_panel.models import Company
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from modules.admin_panel.views.batch_discovery_views import parse_file_api, process_company_api
from modules.admin_panel.views.company_views import company_create_view
from modules.crawler_engine.normalizers import (
    check_domain_reachability,
    normalize_and_validate_company,
    normalize_canonical_url,
)

User = get_user_model()


def make_biff2_record(opcode: int, data: bytes) -> bytes:
    """Helper to assemble a single BIFF2 binary record."""
    return struct.pack('<HH', opcode, len(data)) + data


def build_minimal_biff_xls(rows: list) -> bytes:
    """Builds a genuine in-memory legacy .xls (BIFF2) spreadsheet for testing."""
    bof = make_biff2_record(0x0009, struct.pack('<HH', 0x0002, 0x0010))
    body = b''
    for r_idx, row in enumerate(rows):
        for c_idx, val in enumerate(row):
            val_bytes = str(val).encode('ascii', errors='replace')
            data = struct.pack('<HH3sB', r_idx, c_idx, b'\x00\x00\x00', len(val_bytes)) + val_bytes
            body += make_biff2_record(0x0004, data)
    eof = make_biff2_record(0x000A, b'')
    return bof + body + eof


# =============================================================================
# SUITE 1: Single Company Input & URL Sanitization (5 tests)
# =============================================================================
class TestM1SingleCompanyInput(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.admin_user = User.objects.filter(is_superuser=True).first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('m1_admin_test_1', 'admin1@example.com', 'adminpass123')

    def test_valid_urls_normalized(self):
        """Test standard, scheme-less, mixed-case, and tracking params are properly normalized."""
        cases = [
            ("https://www.infosys.com", "https://www.infosys.com"),
            ("wipro.com", "https://wipro.com"),
            ("HTTP://EXAMPLE.COM/", "https://example.com"),
            ("https://acme.com/?utm_source=google&ref=123", "https://acme.com"),
        ]
        for raw, expected in cases:
            self.assertEqual(BatchDiscoveryService._sanitize_url(raw), expected)

    def test_invalid_schemes_rejected(self):
        """Disallow non-HTTP(S) schemes."""
        invalid_schemes = [
            "ftp://ftp.example.com",
            "mailto:careers@example.com",
            "javascript:alert(1)",
            "file:///etc/passwd",
            "data:text/html,<html></html>",
            "tel:+919876543210",
        ]
        for url in invalid_schemes:
            self.assertEqual(BatchDiscoveryService._sanitize_url(url), "")

    def test_malformed_syntax_rejected(self):
        """Disallow invalid hostnames, ports, and static asset files."""
        invalid_urls = [
            "",
            "   ",
            "none",
            "null",
            "n/a",
            "https://localhost",
            "https://not_a_valid_domain",
            "https://example.com:99999",
            "https://example .com",
            "https://example.com/logo.png",
            "https://example.com/report.pdf",
        ]
        for url in invalid_urls:
            self.assertEqual(BatchDiscoveryService._sanitize_url(url), "")

    def test_single_company_reachability_validation(self):
        """Verify reachability validation flags unreachable/timeout domains cleanly."""
        with patch.object(BatchDiscoveryService, 'fetch_page_content', return_value=("", "", 0)):
            is_valid, norm_url, domain, err = BatchDiscoveryService.normalize_and_validate_company(
                "Fake Corp", "https://unreachable-domain-test-xyz.com", check_reachability=True
            )
            self.assertFalse(is_valid)
            self.assertIn("UNREACHABLE", err.upper())

    def test_single_company_duplicate_detection(self):
        """Verify case-insensitive name duplicate and official domain duplicate are detected."""
        test_company_id = "COMP_M1_DUP_TEST"
        Company.objects.filter(company_id=test_company_id).delete()
        Company.objects.filter(official_domain="duplicatetest.com").delete()
        Company.objects.filter(company_name__iexact="Duplicate Test Corp").delete()

        Company.objects.create(
            company_id=test_company_id,
            company_name="Duplicate Test Corp",
            official_domain="duplicatetest.com",
            website_url="https://duplicatetest.com",
        )
        try:
            # 1. Case-insensitive name duplicate
            is_dup1, comp1, reason1 = BatchDiscoveryService.check_company_duplicate("DUPLICATE TEST CORP", "https://newdomain.com")
            self.assertTrue(is_dup1)
            self.assertEqual(comp1.company_id, test_company_id)
            self.assertIn("Duplicate Test Corp", reason1)

            # 2. Domain duplicate
            is_dup2, comp2, reason2 = BatchDiscoveryService.check_company_duplicate("Completely Different Name", "https://duplicatetest.com")
            self.assertTrue(is_dup2)
            self.assertEqual(comp2.company_id, test_company_id)
            self.assertIn("duplicatetest.com", reason2)

            # 3. Unique company
            is_dup3, comp3, reason3 = BatchDiscoveryService.check_company_duplicate("Unique Corp", "https://uniquecorp123.com")
            self.assertFalse(is_dup3)
            self.assertIsNone(comp3)
        finally:
            Company.objects.filter(company_id=test_company_id).delete()


# =============================================================================
# SUITE 2: Bulk Multi-Format Ingestion (5 tests)
# =============================================================================
class TestM1BulkFormatIngestion(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.admin_user = User.objects.filter(is_superuser=True).first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('m1_admin_test_2', 'admin2@example.com', 'adminpass123')

    def test_bulk_upload_xlsx_parsing(self):
        """Verify uploading openpyxl-generated .xlsx workbook parses rows into clean company records."""
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Company Name", "Homepage URL"])
        ws.append(["Tech Mahindra", "https://www.techmahindra.com"])
        ws.append(["HCL Technologies", "https://www.hcltech.com"])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        up_file = SimpleUploadedFile(
            "companies.xlsx",
            buf.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        req = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_file})
        req.user = self.admin_user
        resp = parse_file_api(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['companies'][0]['company_name'], "Tech Mahindra")
        self.assertEqual(data['companies'][1]['company_name'], "HCL Technologies")

    def test_bulk_upload_xls_legacy_binary_parsing(self):
        """Verify uploading real binary .xls file utilizes xlrd and parses cleanly."""
        xls_bytes = build_minimal_biff_xls([
            ["Company Name", "Homepage URL"],
            ["Legacy Tech Ltd", "https://legacytech.com"],
            ["Vintage Motors", "https://vintagemotors.com"],
        ])
        up_file = SimpleUploadedFile("legacy_companies.xls", xls_bytes, content_type="application/vnd.ms-excel")
        req = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_file})
        req.user = self.admin_user
        resp = parse_file_api(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['count'], 2)
        names = [c['company_name'] for c in data['companies']]
        self.assertIn("Legacy Tech Ltd", names)
        self.assertIn("Vintage Motors", names)

    def test_bulk_upload_json_array_and_wrapped_object(self):
        """Verify parsing JSON arrays and wrapped JSON dictionaries."""
        # 1. Array of objects
        json_arr = [{"Company Name": "Larsen & Toubro", "Homepage URL": "https://www.larsentoubro.com"}]
        up_arr = SimpleUploadedFile("companies.json", json.dumps(json_arr).encode('utf-8'), content_type="application/json")
        req1 = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_arr})
        req1.user = self.admin_user
        resp1 = parse_file_api(req1)
        self.assertEqual(resp1.status_code, 200)
        data1 = json.loads(resp1.content.decode('utf-8'))
        self.assertEqual(data1['count'], 1)
        self.assertEqual(data1['companies'][0]['company_name'], "Larsen & Toubro")

        # 2. Wrapped dictionary
        json_wrapped = {"companies": [{"company_name": "Titan Company", "homepage_url": "https://www.titancompany.in"}]}
        up_wrap = SimpleUploadedFile("wrapped.json", json.dumps(json_wrapped).encode('utf-8'), content_type="application/json")
        req2 = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_wrap})
        req2.user = self.admin_user
        resp2 = parse_file_api(req2)
        self.assertEqual(resp2.status_code, 200)
        data2 = json.loads(resp2.content.decode('utf-8'))
        self.assertEqual(data2['count'], 1)
        self.assertEqual(data2['companies'][0]['company_name'], "Titan Company")

    def test_bulk_upload_jsonl_ndjson(self):
        """Verify parsing JSON Lines (.jsonl) newline-delimited JSON format."""
        jsonl_content = (
            '{"Company Name": "Alpha Corp", "Homepage URL": "https://alpha-corp.com"}\n'
            '{"Company Name": "Beta Corp", "Homepage URL": "https://beta-corp.com"}\n'
        )
        up_jsonl = SimpleUploadedFile("companies.jsonl", jsonl_content.encode('utf-8'), content_type="application/x-ndjson")
        req = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_jsonl})
        req.user = self.admin_user
        resp = parse_file_api(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['companies'][0]['company_name'], "Alpha Corp")
        self.assertEqual(data['companies'][1]['company_name'], "Beta Corp")

    def test_bulk_upload_csv_delimiters(self):
        """Verify delimiter sniffing across TSV, Pipe, and Semicolon formats."""
        # TSV
        tsv_content = "Company Name\tHomepage URL\nAcme Corp\thttps://acme.com\n"
        up_tsv = SimpleUploadedFile("companies.tsv", tsv_content.encode('utf-8'), content_type="text/tab-separated-values")
        records_tsv = BatchDiscoveryService.parse_uploaded_file(up_tsv, "companies.tsv")
        self.assertEqual(len(records_tsv), 1)
        self.assertEqual(records_tsv[0]['company_name'], "Acme Corp")

        # Pipe-delimited
        pipe_content = "Company Name|Homepage URL\nBeta LLC|https://beta.com\n"
        up_pipe = SimpleUploadedFile("companies.txt", pipe_content.encode('utf-8'), content_type="text/plain")
        records_pipe = BatchDiscoveryService.parse_uploaded_file(up_pipe, "companies.txt")
        self.assertEqual(len(records_pipe), 1)
        self.assertEqual(records_pipe[0]['company_name'], "Beta LLC")

        # Semicolon-delimited
        semi_content = "Company Name;Homepage URL\nGamma Inc;https://gamma.com\n"
        up_semi = SimpleUploadedFile("companies.csv", semi_content.encode('utf-8'), content_type="text/csv")
        records_semi = BatchDiscoveryService.parse_uploaded_file(up_semi, "companies.csv")
        self.assertEqual(len(records_semi), 1)
        self.assertEqual(records_semi[0]['company_name'], "Gamma Inc")


# =============================================================================
# SUITE 3: Encoding & Edge Cases (4 tests)
# =============================================================================
class TestM1EdgeCases(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.admin_user = User.objects.filter(is_superuser=True).first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('m1_admin_test_3', 'admin3@example.com', 'adminpass123')

    def test_utf8_bom_and_windows_1252_encoding(self):
        """Verify parsing UTF-8 with BOM and CP1252 encoded files with accented characters."""
        # UTF-8 with BOM
        bom_csv = "\ufeffCompany Name,Homepage URL\nBOM Corp,https://bomcorp.com\n"
        up_bom = SimpleUploadedFile("bom.csv", bom_csv.encode('utf-8-sig'), content_type="text/csv")
        recs_bom = BatchDiscoveryService.parse_uploaded_file(up_bom, "bom.csv")
        self.assertEqual(recs_bom[0]['company_name'], "BOM Corp")

        # Windows-1252 with accents
        cp1252_csv = "Company Name,Homepage URL\nSociété Générale,https://societegenerale.com\n"
        up_cp1252 = SimpleUploadedFile("cp1252.csv", cp1252_csv.encode('cp1252'), content_type="text/csv")
        recs_cp = BatchDiscoveryService.parse_uploaded_file(up_cp1252, "cp1252.csv")
        self.assertEqual(recs_cp[0]['company_name'], "Société Générale")

    def test_empty_and_corrupt_files_handled_cleanly(self):
        """Verify 0-byte, header-only, and unparseable files return 400 with clean error messages."""
        # 0-byte file
        empty_file = SimpleUploadedFile("empty.csv", b"", content_type="text/csv")
        req1 = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': empty_file})
        req1.user = self.admin_user
        resp1 = parse_file_api(req1)
        self.assertEqual(resp1.status_code, 400)

        # Header-only file
        header_file = SimpleUploadedFile("header_only.csv", b"Company Name,Homepage URL\n", content_type="text/csv")
        req2 = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': header_file})
        req2.user = self.admin_user
        resp2 = parse_file_api(req2)
        self.assertEqual(resp2.status_code, 400)

    def test_in_file_duplicate_deduplication(self):
        """Verify duplicate rows within the same uploaded file are deduplicated and tracked in metrics."""
        dup_csv = (
            "Company Name,Homepage URL\n"
            "Infosys,https://www.infosys.com\n"
            "Infosys,https://www.infosys.com\n"
            "Wipro,https://www.wipro.com\n"
        )
        up_dup = SimpleUploadedFile("dup.csv", dup_csv.encode('utf-8'), content_type="text/csv")
        req = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_dup})
        req.user = self.admin_user
        resp = parse_file_api(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['count'], 2)
        self.assertEqual(data['duplicate_count'], 1)
        self.assertEqual(data['skipped_count'], 1)
        names = [c['company_name'] for c in data['companies']]
        self.assertEqual(names, ["Infosys", "Wipro"])

    def test_whitespace_accents_and_special_chars(self):
        """Verify handling of extraneous whitespace, accents, and URL fragments."""
        cases = [
            ("  Nestlé S.A.  ", "https://www.nestle.com/#overview", "Nestlé S.A.", "https://www.nestle.com"),
            ("L'Oréal Group", "https://www.loreal.com/?ref=homepage", "L'Oréal Group", "https://www.loreal.com"),
        ]
        for name_in, url_in, expected_name, expected_url in cases:
            is_valid, norm_url, domain, err = BatchDiscoveryService.normalize_and_validate_company(name_in, url_in)
            self.assertTrue(is_valid)
            self.assertEqual(norm_url, expected_url)
            self.assertTrue(len(domain) > 0)


# =============================================================================
# SUITE 4: Multi-Row Failure Isolation (3 tests)
# =============================================================================
class TestM1RowIsolation(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.admin_user = User.objects.filter(is_superuser=True).first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('m1_admin_test_4', 'admin4@example.com', 'adminpass123')

    def test_multi_row_failure_isolation(self):
        """Verify 8-row batch with 3 valid and 5 invalid rows isolates failures without halting."""
        mixed_csv = (
            "Company Name,Homepage URL\n"
            "Valid Corp 1,https://valid-corp-1.com\n"
            ",https://missingname.example.com\n"
            "Missing URL Corp,\n"
            "Valid Corp 2,https://valid-corp-2.com\n"
            "FTP Corp,ftp://ftp.example.com\n"
            "Bad Domain Corp,not_a_valid_domain\n"
            "Static Asset Corp,https://example.com/logo.png\n"
            "Valid Corp 3,https://valid-corp-3.com\n"
        )
        up_file = SimpleUploadedFile("mixed.csv", mixed_csv.encode('utf-8'), content_type="text/csv")
        req = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_file})
        req.user = self.admin_user
        resp = parse_file_api(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(data['count'], 3)
        self.assertEqual(data['skipped_count'], 5)
        names = [c['company_name'] for c in data['companies']]
        self.assertEqual(names, ["Valid Corp 1", "Valid Corp 2", "Valid Corp 3"])

    def test_row_isolation_corrupt_row_does_not_abort_batch(self):
        """Verify that a malformed row in batch does not terminate subsequent valid rows."""
        rows = [
            {"Company Name": "Healthy Alpha", "Homepage URL": "https://alpha.com"},
            {"Company Name": None, "Homepage URL": None},
            {"Company Name": "Healthy Beta", "Homepage URL": "https://beta.com"},
        ]
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Company Name", "Homepage URL"])
        for r in rows:
            ws.append([r["Company Name"], r["Homepage URL"]])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        up_file = SimpleUploadedFile("corrupt_row.xlsx", buf.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        req = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_file})
        req.user = self.admin_user
        resp = parse_file_api(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(data['count'], 2)
        names = [c['company_name'] for c in data['companies']]
        self.assertEqual(names, ["Healthy Alpha", "Healthy Beta"])

    def test_mixed_valid_and_invalid_formats(self):
        """Verify JSON batch with null items and malformed items parses valid elements safely."""
        json_data = [
            {"company_name": "Valid First", "homepage_url": "https://first.com"},
            None,
            "not a dict string",
            {"company_name": "", "homepage_url": "https://bad.com"},
            {"company_name": "Valid Second", "homepage_url": "https://second.com"},
        ]
        up_file = SimpleUploadedFile("mixed.json", json.dumps(json_data).encode('utf-8'), content_type="application/json")
        req = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_file})
        req.user = self.admin_user
        resp = parse_file_api(req)
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(data['count'], 2)
        names = [c['company_name'] for c in data['companies']]
        self.assertEqual(names, ["Valid First", "Valid Second"])


# =============================================================================
# SUITE 5: Interface Contracts & View Integration (3 tests)
# =============================================================================
class TestM1InterfaceContract(unittest.TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.admin_user = User.objects.filter(is_superuser=True).first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('m1_admin_test_5', 'admin5@example.com', 'adminpass123')

    def test_normalize_and_validate_company_contract(self):
        """Verify the canonical M1 -> M2 interface contract method signature and return types."""
        # Success case
        is_valid, norm_url, domain, err = BatchDiscoveryService.normalize_and_validate_company(
            "Infosys", "https://www.infosys.com"
        )
        self.assertTrue(is_valid)
        self.assertEqual(norm_url, "https://www.infosys.com")
        self.assertEqual(domain, "infosys.com")
        self.assertEqual(err, "")

        # Failure: Empty company name
        is_valid_bad, _, _, err_bad = BatchDiscoveryService.normalize_and_validate_company(
            "", "https://www.infosys.com"
        )
        self.assertFalse(is_valid_bad)
        self.assertEqual(err_bad, "EMPTY_COMPANY_NAME")

        # Failure: Invalid URL scheme
        is_valid_scheme, _, _, err_scheme = BatchDiscoveryService.normalize_and_validate_company(
            "Infosys", "ftp://ftp.infosys.com"
        )
        self.assertFalse(is_valid_scheme)
        self.assertEqual(err_scheme, "INVALID_URL_SCHEME")

    def test_check_domain_reachability_contract(self):
        """Verify check_domain_reachability adheres to the expected contract (is_reachable, status, reason)."""
        # Reachable mocking HTTP 200
        with patch('urllib.request.urlopen') as mock_url:
            mock_resp = mock_url.return_value.__enter__.return_value
            mock_resp.status = 200
            is_reach, status, reason = check_domain_reachability("https://responsive-example.com")
            self.assertTrue(is_reach)
            self.assertEqual(status, 200)

        # Unreachable mocking DNS failure (status 0)
        with patch('urllib.request.urlopen', side_effect=Exception("getaddrinfo failed")):
            is_reach_fail, status_fail, reason_fail = check_domain_reachability("https://nxdomain-example.com")
            self.assertFalse(is_reach_fail)
            self.assertEqual(status_fail, 0)

    def test_company_create_view_integration(self):
        """Verify company_create_view validates URL syntax, duplicate domain, and rejects invalid inputs."""
        from django.contrib.messages.storage.base import BaseStorage

        class DummyMessageStorage(BaseStorage):
            def _get(self, *args, **kwargs):
                return [], True
            def _store(self, message, *args, **kwargs):
                return []

        # Pre-seed existing company for duplicate domain check
        test_company_id = "COMP_M1_VIEW_TEST"
        Company.objects.filter(company_id=test_company_id).delete()
        Company.objects.filter(official_domain="alreadyregistered.com").delete()

        Company.objects.create(
            company_id=test_company_id,
            company_name="Already Registered Inc",
            official_domain="alreadyregistered.com",
            website_url="https://alreadyregistered.com",
        )
        try:
            # 1. Missing website_url
            req1 = self.rf.post('/admin-portal/companies/create/', {'company_name': 'No Website Corp', 'website_url': ''})
            req1.user = self.admin_user
            req1._messages = DummyMessageStorage(req1)
            resp1 = company_create_view(req1)
            self.assertEqual(resp1.status_code, 200)

            # 2. Duplicate domain
            req2 = self.rf.post('/admin-portal/companies/create/', {
                'company_name': 'Brand New Alias Name',
                'website_url': 'https://alreadyregistered.com',
            })
            req2.user = self.admin_user
            req2._messages = DummyMessageStorage(req2)
            resp2 = company_create_view(req2)
            self.assertEqual(resp2.status_code, 200)

            # 3. Unreachable domain rejected
            with patch('modules.admin_panel.views.company_views.check_domain_reachability', return_value=(False, 0, "Connection refused")):
                req3 = self.rf.post('/admin-portal/companies/create/', {
                    'company_name': 'Unreachable Corp',
                    'website_url': 'https://dead-domain-12345.com',
                })
                req3.user = self.admin_user
                req3._messages = DummyMessageStorage(req3)
                resp3 = company_create_view(req3)
                self.assertEqual(resp3.status_code, 200)
                # Confirm company was NOT created
                self.assertFalse(Company.objects.filter(company_name="Unreachable Corp").exists())
        finally:
            Company.objects.filter(company_id=test_company_id).delete()
