"""
tests/test_ai_bulk_upload_m1.py
===============================
Regression test suite for Milestone 1:
Restrict Bulk Upload Inputs & Automated Homepage Crawling.

Covers:
1. Sample template download (CSV and Excel) has strictly 2 columns: Company Name, Homepage URL.
2. File row normalization (_normalize_row) strictly normalizes company_name and homepage_url/website_url,
   discarding careers/CSR/sector/headquarters/symbol columns and never guessing missing homepage URLs.
3. parse_file_api validates company_name and homepage_url, rejecting missing homepage_url rows cleanly
   and returning clean records without careers_url, csr_url, sector, headquarters, or nse_symbol.
4. process_company_api rejects missing/invalid company_name or homepage_url and strips optional overrides.
5. Automated homepage crawling (find_target_links_from_html) prioritizes corporate CSR portals over
   B2B service/blog/contact paths (TCS-style) and extracts sector/headquarters metadata from homepage HTML.
6. Stage 3 1-hop hub discovery, subdomain probes, generic metadata refresh, and UI template constraints.
"""
import io
import json
import os
import unittest
from unittest.mock import patch
import openpyxl

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from modules.admin_panel.models import AuditTrail, Company
from modules.admin_panel.views.batch_discovery_views import (
    download_sample_template_view,
    parse_file_api,
    process_company_api,
)
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

User = get_user_model()


class TestMilestone1BulkUploadRestrictions(unittest.TestCase):

    def setUp(self):
        self.rf = RequestFactory()
        self.admin_user = User.objects.filter(is_superuser=True).first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('m1_test_admin', 'm1@example.com', 'adminpass123')

    def test_sample_template_csv_headers_strictly_two_columns(self):
        """Verify sample CSV template download strictly outputs ['Company Name', 'Homepage URL']."""
        req = self.rf.get('/admin-portal/ai-discovery/sample-template/?format=csv')
        req.user = self.admin_user
        resp = download_sample_template_view(req)
        self.assertEqual(resp.status_code, 200)

        lines = resp.content.decode('utf-8').splitlines()
        header = lines[0].strip()
        self.assertEqual(header, "Company Name,Homepage URL")
        for row_line in lines[1:]:
            if row_line.strip():
                parts = row_line.split(',')
                self.assertEqual(len(parts), 2)
                self.assertTrue(parts[1].strip().startswith("https://"))

    def test_sample_template_excel_headers_strictly_two_columns(self):
        """Verify sample Excel template download strictly outputs ['Company Name', 'Homepage URL']."""
        req = self.rf.get('/admin-portal/ai-discovery/sample-template/?format=xlsx')
        req.user = self.admin_user
        resp = download_sample_template_view(req)
        self.assertEqual(resp.status_code, 200)

        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        ws = wb.active
        headers = [cell.value for cell in ws[1]]
        self.assertEqual(headers, ["Company Name", "Homepage URL"])

    def test_normalize_row_discards_careers_csr_and_optional_metadata(self):
        """Verify _normalize_row ignores careers, CSR, sector, HQ, symbol columns and returns strict 2-field schema."""
        raw_row = {
            "Company Name": "Paytm",
            "Homepage URL": "https://paytm.com",
            "Careers URL": "https://fakecareers.com/jobs",
            "CSR URL": "https://fakecsr.com/sustainability",
            "Sector": "FinTech",
            "Headquarters": "Noida, India",
            "NSE Symbol": "PAYTM",
        }
        normalized = BatchDiscoveryService._normalize_row(raw_row)
        self.assertEqual(set(normalized.keys()), {'company_name', 'website_url', 'homepage_url'})
        self.assertEqual(normalized['company_name'], "Paytm")
        self.assertEqual(normalized['website_url'], "https://paytm.com")
        self.assertEqual(normalized['homepage_url'], "https://paytm.com")

    def test_normalize_row_does_not_guess_missing_homepage_url(self):
        """Verify _normalize_row never guesses www.<brand>.com or leaks CSR/Careers URLs when Homepage URL is missing."""
        row_startup = {
            "Company Name": "Unlisted Startup Pvt Ltd",
            "Careers URL": "https://jobs.lever.co/unlistedstartup",
            "CSR URL": "https://unlistedstartupfoundation.org",
        }
        norm1 = BatchDiscoveryService._normalize_row(row_startup)
        self.assertEqual(norm1['company_name'], "Unlisted Startup Pvt Ltd")
        self.assertEqual(norm1['homepage_url'], "")
        self.assertEqual(norm1['website_url'], "")

        row_known = {"Company Name": "Tata Consultancy Services"}
        norm2 = BatchDiscoveryService._normalize_row(row_known)
        self.assertEqual(norm2['homepage_url'], "")
        self.assertEqual(norm2['website_url'], "")

    def test_parse_file_api_returns_clean_records_without_extraneous_fields(self):
        """Verify parse_file_api strips careers/CSR/sector/HQ/symbol fields from uploaded files."""
        csv_data = (
            "Company Name,Homepage URL,Careers URL,CSR Portal Link,Sector,Headquarters,NSE Symbol\n"
            "Infosys,https://www.infosys.com,https://careers.infosys.com,https://csr.infosys.com,IT,Bengaluru,INFY\n"
        )
        up_file = SimpleUploadedFile("companies.csv", csv_data.encode('utf-8'), content_type="text/csv")
        req = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_file})
        req.user = self.admin_user
        resp = parse_file_api(req)
        self.assertEqual(resp.status_code, 200)

        data = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['companies']), 1)
        record = data['companies'][0]
        self.assertEqual(set(record.keys()), {'company_name', 'homepage_url', 'website_url'})
        self.assertEqual(record['company_name'], "Infosys")
        self.assertEqual(record['homepage_url'], "https://www.infosys.com")

    def test_parse_file_api_rejects_missing_homepage_url(self):
        """Verify parse_file_api rejects files/rows missing Homepage URL cleanly."""
        csv_all_missing = "Company Name,Careers URL,CSR URL\nPaytm,https://paytm.com/careers/,https://paytm.com/csr\n"
        up_missing = SimpleUploadedFile("missing_home.csv", csv_all_missing.encode('utf-8'), content_type="text/csv")
        req1 = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_missing})
        req1.user = self.admin_user
        resp1 = parse_file_api(req1)
        self.assertEqual(resp1.status_code, 400)
        data1 = json.loads(resp1.content.decode('utf-8'))
        self.assertEqual(data1['status'], 'error')

        csv_mixed = (
            "Company Name,Homepage URL\n"
            "Paytm,https://paytm.com\n"
            "MissingSiteCorp,\n"
        )
        up_mixed = SimpleUploadedFile("mixed.csv", csv_mixed.encode('utf-8'), content_type="text/csv")
        req2 = self.rf.post('/admin-portal/ai-discovery/parse-file/', {'file': up_mixed})
        req2.user = self.admin_user
        resp2 = parse_file_api(req2)
        self.assertEqual(resp2.status_code, 200)
        data2 = json.loads(resp2.content.decode('utf-8'))
        self.assertEqual(data2['count'], 1)
        self.assertEqual(data2['skipped_count'], 1)
        self.assertEqual(data2['companies'][0]['company_name'], "Paytm")

    def test_process_company_api_rejects_missing_homepage_url_and_strips_overrides(self):
        """Verify process_company_api requires both company_name and homepage_url, and strips all extra fields."""
        for bad_payload in [
            {"company": {"company_name": "Paytm", "homepage_url": ""}},
            {"company": {"company_name": "", "homepage_url": "https://paytm.com"}},
            {"company": {"company_name": "Paytm", "homepage_url": "not_a_valid_domain"}},
        ]:
            req = self.rf.post(
                '/admin-portal/ai-discovery/process-company/',
                data=json.dumps(bad_payload),
                content_type='application/json',
            )
            req.user = self.admin_user
            resp = process_company_api(req)
            self.assertEqual(resp.status_code, 400)
            self.assertEqual(json.loads(resp.content.decode('utf-8'))['status'], 'error')

        override_payload = {
            "company": {
                "company_name": "Paytm",
                "homepage_url": "https://paytm.com",
                "sector": "Manual Override Sector",
                "headquarters": "Manual Override HQ",
                "nse_symbol": "PAYTM",
                "careers_url": "https://evil.example.com/careers",
                "csr_url": "https://evil.example.com/csr",
            },
            "options": {"extract_jobs": True, "extract_csr": True},
        }
        with patch.object(BatchDiscoveryService, 'process_single_company', return_value={"status": "success"}) as mock_proc:
            req_ok = self.rf.post(
                '/admin-portal/ai-discovery/process-company/',
                data=json.dumps(override_payload),
                content_type='application/json',
            )
            req_ok.user = self.admin_user
            resp_ok = process_company_api(req_ok)
            self.assertEqual(resp_ok.status_code, 200)
            mock_proc.assert_called_once()
            forwarded_task = mock_proc.call_args[0][0]
            self.assertEqual(forwarded_task, {
                'company_name': 'Paytm',
                'homepage_url': 'https://paytm.com',
                'website_url': 'https://paytm.com',
            })

    def test_process_single_company_rejects_missing_homepage_url(self):
        """Verify BatchDiscoveryService.process_single_company rejects payloads missing homepage_url."""
        result = BatchDiscoveryService.process_single_company({'company_name': 'Paytm'})
        self.assertEqual(result['status'], 'error')
        self.assertIn('homepage_url', result['message'].lower())

    def test_find_target_links_from_html_discovers_careers_and_csr(self):
        """Verify find_target_links_from_html extracts careers and CSR URLs from homepage anchor tags."""
        sample_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Test Enterprise</title></head>
        <body>
            <nav>
                <a href="/about-us">About Us</a>
                <a href="/company/sustainability/esg">Sustainability &amp; ESG</a>
                <a href="/careers/">Work With Us / Careers</a>
            </nav>
            <footer>
                <a href="https://twitter.com/company">Twitter</a>
            </footer>
        </body>
        </html>
        """
        links = BatchDiscoveryService.find_target_links_from_html(sample_html, "https://samplecompany.com")
        self.assertEqual(links['careers_url'], "https://samplecompany.com/careers/")
        self.assertEqual(links['csr_url'], "https://samplecompany.com/company/sustainability/esg")

    def test_find_target_links_from_html_prioritizes_csr_over_b2b_services_and_contact(self):
        """Verify TCS-style HTML ranks corporate CSR portal ahead of B2B sustainability services, blogs, and contact forms."""
        tcs_style_html = """
        <!DOCTYPE html>
        <html>
        <body>
            <header>
                <a href="/what-we-do/services/sustainability-services">Sustainability Services</a>
                <a href="/what-we-do/solutions/talent-hiring">Hiring Solutions</a>
                <a href="/who-we-are/corporate-social-responsibility">Community</a>
                <a href="/who-we-are/tcs-sustainable-business-carbon-neutrality">Sustainability</a>
                <a href="/careers">Join us</a>
                <a href="/careers/argentina">Argentina</a>
            </header>
            <footer>
                <a href="/insights/blog/sustainability">Sustainability Insights</a>
                <a href="/contact-us/whats-on-your-mind/csr">CSR</a>
            </footer>
        </body>
        </html>
        """
        links = BatchDiscoveryService.find_target_links_from_html(tcs_style_html, "https://www.tcs.com")
        self.assertEqual(links['csr_url'], "https://www.tcs.com/who-we-are/corporate-social-responsibility")
        self.assertEqual(links['careers_url'], "https://www.tcs.com/careers")

        only_commercial_html = """
        <html><body>
            <a href="/what-we-do/services/sustainability-services">Sustainability Services</a>
            <a href="/blog/sustainability">Sustainability Blog</a>
            <a href="/contact-us/whats-on-your-mind/csr">CSR Contact</a>
        </body></html>
        """
        links_commercial = BatchDiscoveryService.find_target_links_from_html(only_commercial_html, "https://www.tcs.com")
        self.assertEqual(links_commercial['csr_url'], "")

    def test_extract_company_metadata_from_html_extracts_sector_and_hq(self):
        """Verify sector and headquarters city/state are accurately extracted from JSON-LD, meta tags, and footer address."""
        jsonld_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Acme Cloud Systems: Enterprise Software &amp; IT Services</title>
            <meta name="description" content="Global leader in cloud computing, cybersecurity, and digital transformation.">
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Acme Cloud Systems",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "Raveline Street, Fort",
                    "addressLocality": "Mumbai",
                    "addressRegion": "MH",
                    "addressCountry": "IN"
                }
            }
            </script>
        </head>
        <body><main><p>Cloud engineering and AI consulting services.</p></main></body>
        </html>
        """
        meta_a = BatchDiscoveryService.extract_company_metadata_from_html(jsonld_html, "", "Acme", "https://acme.example.com")
        self.assertEqual(meta_a['sector'], "Information Technology")
        self.assertEqual(meta_a['headquarters'], "Mumbai, Maharashtra")

        footer_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>PayFast: Secure UPI Payments &amp; Digital Financial Services</title>
            <meta name="description" content="Send money with UPI, pay bills, mutual funds, and merchant payments.">
        </head>
        <body>
            <footer>
                <p>Corporate Office: B-121, Sector 5, Noida - 201301, Uttar Pradesh, India</p>
            </footer>
        </body>
        </html>
        """
        meta_b = BatchDiscoveryService.extract_company_metadata_from_html(footer_html, "", "PayFast", "https://payfast.example.com")
        self.assertEqual(meta_b['sector'], "Banking & Financial Services")
        self.assertEqual(meta_b['headquarters'], "Noida, Uttar Pradesh")

        noisy_html = """
        <!DOCTYPE html>
        <html>
        <head><title>Consumer Utility Portal</title></head>
        <body>
            <main><p>Paytm and IEM Kolkata partner for an event.</p></main>
            <footer>
                <a href="/pay-mtnl">MTNL Mumbai Bill Payment</a>
                <a href="/metro">Bengaluru Metro Card Recharge</a>
            </footer>
        </body>
        </html>
        """
        meta_c = BatchDiscoveryService.extract_company_metadata_from_html(noisy_html, "IEM Kolkata partner", "ConsumerPortal", "https://consumer.example.com")
        self.assertEqual(meta_c['headquarters'], "India")

    def test_process_single_company_hub_subdomain_discovery_and_generic_refresh(self):
        """Verify 1-hop hub discovery, careers subdomain probe, and refreshing generic sector/HQ defaults."""
        test_domain = "m1verifycorp.in"
        Company.objects.filter(company_id="COMP_M1_TEST_001").delete()
        Company.objects.filter(official_domain__iexact=test_domain).delete()

        home_html = """
        <html>
        <head>
            <title>M1 Verify Solar: Clean Energy &amp; Solar Power Generation</title>
            <meta name="description" content="Utility-scale solar power generation and renewable energy.">
        </head>
        <body>
            <nav><a href="/company">Company</a></nav>
            <footer>Registered Office: Tower A, Cyber Hub, Gurugram, Haryana 122002</footer>
        </body>
        </html>
        """
        hub_html = """
        <html><body>
            <a href="/company/corporate-social-responsibility">Corporate Social Responsibility</a>
        </body></html>
        """
        careers_sub_html = (
            "<html><body><h1>Current Job Openings</h1>"
            "<p>Explore engineering, solar project management, and corporate roles across India and apply directly on our official careers portal.</p>"
            "</body></html>"
        )
        csr_page_html = "<html><body><h1>Rural Solar Literacy Mission</h1></body></html>"

        def fake_fetch(url, timeout=6):
            u = url.rstrip('/')
            if u == f"https://www.{test_domain}":
                return home_html, "Utility-scale solar power generation and renewable energy.", 200
            if u == f"https://www.{test_domain}/company":
                return hub_html, "Company overview and CSR portal", 200
            if u == f"https://careers.{test_domain}":
                return careers_sub_html, "Current Job Openings Explore engineering, solar project management, and corporate roles across India and apply directly on our official careers portal.", 200
            if u == f"https://www.{test_domain}/company/corporate-social-responsibility":
                return csr_page_html, "Rural Solar Literacy Mission", 200
            return "", "", 404

        try:
            # Pre-seed an existing company with generic defaults to verify refresh
            Company.objects.create(
                company_id="COMP_M1_TEST_001",
                company_name="M1 Verify Corp",
                sector="Corporate Enterprise",
                headquarters="India",
                official_domain=test_domain,
                website_url=f"https://www.{test_domain}",
            )

            with patch.object(BatchDiscoveryService, 'fetch_page_content', side_effect=fake_fetch), \
                 patch.object(BatchDiscoveryService, 'discover_all_real_jobs', return_value=[]), \
                 patch.object(BatchDiscoveryService, 'discover_all_real_csr', return_value=[]):
                res = BatchDiscoveryService.process_single_company({
                    'company_name': 'M1 Verify Corp',
                    'homepage_url': f"https://www.{test_domain}",
                    'website_url': f"https://www.{test_domain}",
                })

            self.assertEqual(res['status'], 'success')
            self.assertEqual(res['sector'], 'Renewable Energy & Power')
            self.assertEqual(res['headquarters'], 'Gurugram, Haryana')
            self.assertEqual(res['careers_url'], f"https://careers.{test_domain}")
            self.assertEqual(res['careers_method'], 'subdomain_probe')
            self.assertEqual(res['csr_url'], f"https://www.{test_domain}/company/corporate-social-responsibility")
            self.assertEqual(res['csr_method'], 'hub_nav_link')

            refreshed = Company.objects.get(company_id="COMP_M1_TEST_001")
            self.assertEqual(refreshed.sector, 'Renewable Energy & Power')
            self.assertEqual(refreshed.headquarters, 'Gurugram, Haryana')
        finally:
            AuditTrail.objects.filter(record_id="COMP_M1_TEST_001").delete()
            Company.objects.filter(company_id="COMP_M1_TEST_001").delete()
            Company.objects.filter(official_domain__iexact=test_domain).delete()

    def test_fetch_rendered_page_uses_realistic_chrome_context(self):
        """Verify fetch_rendered_page configures Playwright context with realistic Chrome USER_AGENT."""
        from unittest.mock import AsyncMock, MagicMock
        import modules.admin_panel.services.batch_discovery_service as bds

        mock_page = MagicMock()
        mock_page.goto = AsyncMock(return_value=MagicMock(status=200))
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.inner_text = AsyncMock(return_value="Rendered Career Page Text")
        mock_page.content = AsyncMock(return_value="<html><body><p>Rendered Career Page Text</p></body></html>")

        mock_context = MagicMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_context.close = AsyncMock()

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright_inst = MagicMock()
        mock_playwright_inst.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_pw_cm = MagicMock()
        mock_pw_cm.__aenter__ = AsyncMock(return_value=mock_playwright_inst)
        mock_pw_cm.__aexit__ = AsyncMock(return_value=None)

        with patch.object(bds, 'async_playwright', return_value=mock_pw_cm):
            html, text, status = BatchDiscoveryService.fetch_rendered_page("https://example.com")

        self.assertEqual(status, 200)
        self.assertIn("Rendered Career Page Text", text)
        mock_browser.new_context.assert_called_once()
        ctx_kwargs = mock_browser.new_context.call_args.kwargs
        self.assertEqual(ctx_kwargs.get('user_agent'), bds.USER_AGENT)
        self.assertIn('Chrome/', ctx_kwargs.get('user_agent', ''))
        self.assertIn('viewport', ctx_kwargs)

    def test_ai_discovery_template_has_no_optional_or_link_inputs(self):
        """Verify AI discovery HTML template contains strictly Company Name and Homepage URL inputs."""
        tpl_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'templates', 'admin', 'ai_discovery', 'index.html'
        )
        with open(tpl_path, 'r', encoding='utf-8') as f:
            html = f.read()

        self.assertIn('id="quick-company-input"', html)
        self.assertIn('id="quick-website-input"', html)
        for forbidden in (
            'quick-sector-input',
            'quick-hq-input',
            'quick-optional-fields',
            'toggleOptionalQuickFields',
            'quick-careers-input',
            'quick-csr-input',
        ):
            self.assertNotIn(forbidden, html)

    def test_hq_address_ordering_full_dom_footer_and_enterprise_boundary(self):
        """Verify earliest city precedence without cross-office state leak, full DOM footer scan, and word-boundary enterprise matching."""
        addr_text = (
            "Corporate Headquarters: Skymark One, Sector-98, Noida-201304. "
            "Registered Office: Devika Tower, Nehru Place, New Delhi-110019"
        )
        self.assertEqual(BatchDiscoveryService._extract_city_state_from_address_text(addr_text), "Noida, Uttar Pradesh")

        html_div_footer = """
        <html>
        <head><title>FinEdge Digital Payments</title></head>
        <body>
            <main><p>Digital payments, UPI transfers, and financial services platform.</p></main>
            <div class="footer">Corporate Office: Plot 12, Cyberabad, Hyderabad 500081</div>
        </body>
        </html>
        """
        meta = BatchDiscoveryService.extract_company_metadata_from_html(
            html_div_footer,
            "Digital payments, UPI transfers, and financial services platform.",
            "FinEdge Digital",
            "https://finedge.example.in",
        )
        self.assertEqual(meta['headquarters'], "Hyderabad, Telangana")
        self.assertEqual(meta['sector'], "Banking & Financial Services")

        self.assertFalse(BatchDiscoveryService._matches_enterprise_key('itc', 'fintech solutions ltd', 'fintechsol.com'))
        self.assertTrue(BatchDiscoveryService._matches_enterprise_key('itc', 'itc limited', 'itcportal.com'))
        self.assertFalse(BatchDiscoveryService._matches_enterprise_key('ril', 'april consumer ltd', 'april.com'))
        self.assertFalse(BatchDiscoveryService._matches_enterprise_key('hcl', 'techcloud india', 'techcloud.in'))

    def test_process_single_company_waf_202_triggers_playwright_fallback(self):
        """Verify HTTP 202 AWS WAF challenge shell triggers headless Playwright render to discover portals."""
        test_domain = "wafportaltest.in"
        Company.objects.filter(official_domain__iexact=test_domain).delete()

        waf_shell = "<html><head><script>window.awsWafCookieDomainList=['.wafportaltest.in'];</script></head><body></body></html>"
        rendered_html = """
        <html>
        <head><title>QuickCart Commerce: Food Delivery &amp; Quick Commerce</title></head>
        <body>
            <nav>
                <a href="https://www.wafportaltest.in/careers">Careers</a>
                <a href="https://www.wafportaltest.in/csr">CSR &amp; Impact</a>
            </nav>
            <footer>Corporate Office: Bengaluru, Karnataka</footer>
        </body>
        </html>
        """

        def fake_fetch(url, timeout=6):
            u = url.rstrip('/')
            if u == f"https://www.{test_domain}":
                return waf_shell, "", 202
            if u == f"https://www.{test_domain}/careers":
                return "<html><body><h1>Careers at QuickCart</h1></body></html>", "Careers at QuickCart", 200
            if u == f"https://www.{test_domain}/csr":
                return "<html><body><h1>QuickCart CSR Initiatives</h1></body></html>", "QuickCart CSR Initiatives", 200
            return "", "", 404

        try:
            with patch.object(BatchDiscoveryService, 'fetch_page_content', side_effect=fake_fetch), \
                 patch.object(
                     BatchDiscoveryService,
                     'fetch_rendered_page',
                     return_value=(rendered_html, "Careers CSR Bengaluru Food Delivery", 200),
                 ) as mock_render, \
                 patch.object(BatchDiscoveryService, 'discover_all_real_jobs', return_value=[]), \
                 patch.object(BatchDiscoveryService, 'discover_all_real_csr', return_value=[]):
                res = BatchDiscoveryService.process_single_company({
                    'company_name': 'QuickCart',
                    'homepage_url': f"https://www.{test_domain}",
                })

            mock_render.assert_called_once()
            self.assertEqual(res['status'], 'success')
            self.assertEqual(res['careers_url'], f"https://www.{test_domain}/careers")
            self.assertEqual(res['csr_url'], f"https://www.{test_domain}/csr")
            self.assertEqual(res['headquarters'], "Bengaluru, Karnataka")
        finally:
            AuditTrail.objects.filter(record_id__startswith="COMP_BATCH_QUICKCART").delete()
            Company.objects.filter(official_domain__iexact=test_domain).delete()


