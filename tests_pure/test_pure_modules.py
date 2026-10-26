"""Django-free tests: run with  python -m unittest discover -s tests_pure -v"""
import sys, types, unittest, importlib
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
for name, rel in (('modules', 'modules'), ('modules.crawler_engine', 'modules/crawler_engine')):
    m = types.ModuleType(name); m.__path__ = [str(ROOT / rel)]; sys.modules[name] = m
n = importlib.import_module('modules.crawler_engine.normalizers')
o = importlib.import_module('modules.crawler_engine.ownership')
lv = importlib.import_module('modules.crawler_engine.link_verifier')
ad = importlib.import_module('modules.crawler_engine.access_detector')
NOW = datetime(2026, 10, 16, tzinfo=timezone.utc)


class Resp:
    def __init__(self, status=200, json_data=None, text='', url=None, headers=None):
        self.status_code, self._j, self.text, self.url = status, json_data, text, url
        self.headers = headers or {}
    def json(self): return self._j


class Normalizers(unittest.TestCase):
    def test_dates(self):
        self.assertEqual(n.normalize_date('1783043640931'), '2026-07-03')
        self.assertEqual(n.normalize_date('2026-07-03T10:00:00.000Z'), '2026-07-03')
        self.assertEqual(n.normalize_date('Posted 9 Days Ago', NOW), '2026-10-07')
        self.assertEqual(n.normalize_date('Posted Yesterday', NOW), '2026-10-15')
        self.assertIsNone(n.normalize_date('Posted 30+ Days Ago', NOW))
        self.assertIsNone(n.normalize_date('garbage'))

    def test_enums(self):
        self.assertEqual(n.normalize_employment_type('FULL_TIME'), 'Full-time')
        self.assertEqual(n.normalize_employment_type('Full-time Employment'), 'Full-time')
        self.assertIsNone(n.normalize_employment_type('Regular'))
        self.assertIsNone(n.normalize_employment_type('Professional'))
        self.assertEqual(n.normalize_work_mode('onsite'), 'On-site')
        self.assertEqual(n.normalize_work_mode('remote'), 'Remote')

    def test_country(self):
        self.assertEqual(n.infer_country('Ho Chi Minh City, Vietnam'), 'Vietnam')
        self.assertEqual(n.infer_country('Jefferson City, MO'), 'United States')
        self.assertEqual(n.infer_country('Gurgaon, Gurgaon, IN'), 'India')
        self.assertIsNone(n.infer_country('Hoboken US HQ'))          # unknown -> never defaults to India
        self.assertEqual(n.split_location('Madhya Pradesh, India'), (None, 'Madhya Pradesh'))

    def test_urls(self):
        self.assertEqual(n.normalize_application_url('https://api.smartrecruiters.com/v1/companies/X/postings/7'),
                         'https://jobs.smartrecruiters.com/X/7')
        self.assertIsNone(n.normalize_application_url('mailto:a@b.com'))
        self.assertIsNone(n.normalize_application_url('https://www.google.com/search?q=jobs'))
        self.assertTrue(n.is_generic_landing_url('https://x.com/careers'))
        self.assertFalse(n.is_generic_landing_url('https://jobs.lever.co/paytm/abc/apply'))

    def test_csr_page_title_filter(self):
        self.assertTrue(n.is_page_title_not_csr_project('CSR'))
        self.assertTrue(n.is_page_title_not_csr_project('Corporate Social Responsibility | Reliance Industries Limited', 'Reliance Industries Limited'))
        self.assertTrue(n.is_page_title_not_csr_project('Sustainability - Overview', 'Infosys Limited'))
        self.assertFalse(n.is_page_title_not_csr_project('Project Nanhi Kali - Girl Child Education', 'Mahindra & Mahindra Limited'))

    def test_generic_contact_email_filter(self):
        self.assertTrue(n.is_generic_or_non_csr_contact_email('info@company.com'))
        self.assertTrue(n.is_generic_or_non_csr_contact_email('webmaster@company.com'))
        self.assertTrue(n.is_generic_or_non_csr_contact_email('investors@company.com'))
        self.assertFalse(n.is_generic_or_non_csr_contact_email('csr@company.com'))
        self.assertFalse(n.is_generic_or_non_csr_contact_email('info@reliancefoundation.org'))

    def test_csr_source_format(self):
        self.assertIn('PDF', n.detect_csr_source_format('https://acme.com/reports/csr-2025.pdf'))
        self.assertEqual(n.detect_csr_source_format('https://www.reliancefoundation.org/'), 'Foundation Portal Webpage')
        self.assertEqual(n.detect_csr_source_format('https://acme.com/csr-initiatives'), 'CSR Webpage')


class Ownership(unittest.TestCase):
    CX1 = 'https://eibd.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/1'
    def test_shared_site_without_entity_is_unresolved(self):
        self.assertEqual(o.resolve_owner({'application_url': self.CX1}, 'ACC')[0], o.UNRESOLVED)
    def test_entity_field_decides(self):
        j = {'application_url': self.CX1, 'business_unit': 'ACC Limited'}
        self.assertEqual(o.resolve_owner(j, 'ACC')[0], o.OWNED)
        self.assertEqual(o.resolve_owner(j, 'ADANIENT')[0], o.WRONG_COMPANY)
    def test_exclusive_site(self):
        u = self.CX1.replace('CX_1', 'CX_3003')
        self.assertEqual(o.resolve_owner({'application_url': u}, 'ADANIPOWER')[0], o.OWNED)
        self.assertEqual(o.resolve_owner({'application_url': u}, 'ACC')[0], o.WRONG_COMPANY)
    def test_hul_india_only(self):
        u = 'https://unilever.wd3.myworkdayjobs.com/s/job/1'
        self.assertEqual(o.resolve_owner({'application_url': u, 'location': 'Rotterdam'}, 'HINDUNILVR')[0], o.NOT_IN_SCOPE)
        self.assertEqual(o.resolve_owner({'application_url': u, 'location': 'Mumbai, Maharashtra'}, 'HINDUNILVR')[0], o.OWNED)


class LinkVerifier(unittest.TestCase):
    def test_generic_url_rejected_without_network(self):
        r = lv.verify_job_link('https://www.lauruslabs.com/', 'Chemist', get=lambda u: 1 / 0)
        self.assertEqual(r.status, lv.GENERIC)
    def test_lever_ok_and_mismatch(self):
        url = 'https://jobs.lever.co/paytm/9eed4fec-73f7-4114-a5d3-b2f689c92e8c/apply'
        ok = lv.verify_job_link(url, 'Account Executive Director', get=lambda u: Resp(200, {'text': 'Account Executive / Director'}))
        self.assertTrue(ok.ok)
        bad = lv.verify_job_link(url, 'Account Executive Director', get=lambda u: Resp(200, {'text': 'Plumber'}))
        self.assertEqual(bad.status, lv.MISMATCH)
    def test_greenhouse_ok(self):
        url = 'https://boards.greenhouse.io/razorpay/jobs/4123456'
        ok = lv.verify_job_link(url, 'Senior Backend Engineer', get=lambda u: Resp(200, {'title': 'Senior Backend Engineer'}))
        self.assertTrue(ok.ok)
    def test_404_is_broken(self):
        url = 'https://jobs.smartrecruiters.com/DrReddys/744000'
        self.assertEqual(lv.verify_job_link(url, 'X Y Z', get=lambda u: Resp(404)).status, lv.BROKEN)
    def test_html_redirect_elsewhere(self):
        url = 'https://careers.acme.com/job/123-Analyst'
        r = lv.verify_job_link(url, 'Analyst', '123', get=lambda u: Resp(200, text='x', url='https://other.com/job/1'))
        self.assertEqual(r.status, lv.REDIRECTED)
    def test_html_id_found(self):
        url = 'https://careers.acme.com/job/Delhi-Analyst/1438974700/'
        r = lv.verify_job_link(url, 'Analyst', '1438974700', get=lambda u: Resp(200, text='<h1>Analyst</h1>', url=url))
        self.assertTrue(r.ok)
    def test_closed_soft404(self):
        url = 'https://careers.acme.com/job/Delhi-Analyst/1/'
        r = lv.verify_job_link(url, 'Analyst', '1', get=lambda u: Resp(200, text='This job is no longer available', url=url))
        self.assertEqual(r.status, lv.CLOSED)
    def test_network_error_is_unreachable(self):
        def boom(u): raise TimeoutError('t')
        self.assertEqual(lv.verify_job_link('https://careers.acme.com/job/Delhi-Analyst/1/', 'Analyst', get=boom).status, lv.UNREACHABLE)
    def test_oracle_ok(self):
        url = 'https://eibd.fa.em2.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/job/47814'
        r = lv.verify_job_link(url, 'Assistant Manager - Security',
                               get=lambda u: Resp(200, {'items': [{'Id': '47814', 'Title': 'Assistant Manager - Security'}]}))
        self.assertTrue(r.ok)
    def test_csr_link_webpage_and_pdf_and_login(self):
        r_web = lv.verify_csr_link('https://www.tcs.com/csr', expected_domain='tcs.com',
                                   get=lambda u: Resp(200, text='<title>TCS CSR Initiatives</title>', url='https://www.tcs.com/csr'))
        self.assertTrue(r_web.ok)
        self.assertEqual(r_web.source_format, 'CSR Webpage')

        r_pdf = lv.verify_csr_link('https://www.tcs.com/reports/csr-2025.pdf', expected_domain='tcs.com',
                                   get=lambda u: Resp(200, text='%PDF-1.7', url='https://www.tcs.com/reports/csr-2025.pdf',
                                                      headers={'Content-Type': 'application/pdf'}))
        self.assertTrue(r_pdf.ok)
        self.assertIn('PDF', r_pdf.source_format)

        r_login = lv.verify_csr_link('https://www.acme.com/csr', expected_domain='acme.com',
                                     get=lambda u: Resp(200, text='<input type="password">', url='https://login.acme.com/sso'))
        self.assertFalse(r_login.ok)
        self.assertEqual(r_login.status, lv.LOGIN_WALL)


class AccessDetector(unittest.TestCase):
    def test_signals(self):
        self.assertTrue(ad.detect_login_wall(401, 'https://x.com', '')[0])
        self.assertFalse(ad.detect_login_wall(403, 'https://x.com', '')[0])
        self.assertTrue(ad.detect_login_wall(200, 'https://login.microsoftonline.com/a', '')[0])
        self.assertTrue(ad.detect_login_wall(200, 'https://x.com/c', '<input type="password">')[0])
        self.assertFalse(ad.detect_login_wall(200, 'https://x.com/careers', '<a href="/job/1"></a>' * 5 + '<input type="password">')[0])
        self.assertFalse(ad.detect_login_wall(200, 'https://x.com/careers', '<h1>Jobs</h1>')[0])


if __name__ == '__main__':
    unittest.main()
