"""
tests/test_stage1_discovery_helpers.py
======================================
Unit tests for Stage 1 discovery helpers without live network requests.
"""
import unittest
from modules.crawler_engine.discovery_helpers import (
    is_real_deep_url,
    get_registrable_domain,
    is_same_registrable_domain_or_ats,
    verify_careers_url_content,
)

class Stage1DiscoveryHelpersTestCase(unittest.TestCase):

    def test_is_real_deep_url_rejects_empty_or_none(self):
        self.assertFalse(is_real_deep_url(None, "https://company.com"))
        self.assertFalse(is_real_deep_url("", "https://company.com"))
        self.assertFalse(is_real_deep_url("   ", "https://company.com"))

    def test_is_real_deep_url_rejects_root_homepage(self):
        # Exact match
        self.assertFalse(is_real_deep_url("https://company.com", "https://company.com"))
        # Trailing slash differences
        self.assertFalse(is_real_deep_url("https://company.com/", "https://company.com"))
        self.assertFalse(is_real_deep_url("http://company.com", "https://company.com/"))
        # www prefix differences
        self.assertFalse(is_real_deep_url("https://www.company.com/", "https://company.com"))
        self.assertFalse(is_real_deep_url("https://company.com", "https://www.company.com/"))
        # Case insensitivity
        self.assertFalse(is_real_deep_url("https://WWW.Company.Com/", "https://company.com"))

    def test_is_real_deep_url_accepts_subdomains_and_paths(self):
        # Deep path
        self.assertTrue(is_real_deep_url("https://company.com/careers", "https://company.com"))
        self.assertTrue(is_real_deep_url("https://company.com/jobs/openings", "https://company.com"))
        self.assertTrue(is_real_deep_url("https://www.company.com/sustainability", "https://company.com"))
        # Deep subdomain
        self.assertTrue(is_real_deep_url("https://careers.company.com", "https://company.com"))
        self.assertTrue(is_real_deep_url("https://careers.company.com/", "https://www.company.com"))
        self.assertTrue(is_real_deep_url("https://jobs.company.com", "https://company.com"))
        # External ATS domain
        self.assertTrue(is_real_deep_url("https://jobs.lever.co/company", "https://company.com"))
        self.assertTrue(is_real_deep_url("https://company.myworkdayjobs.com/careers", "https://company.com"))

    def test_get_registrable_domain(self):
        self.assertEqual(get_registrable_domain("https://careers.tatamotors.com/openings"), "tatamotors.com")
        self.assertEqual(get_registrable_domain("https://www.sbi.co.in/careers"), "sbi.co.in")
        self.assertEqual(get_registrable_domain("new.abb.com"), "abb.com")
        self.assertEqual(get_registrable_domain("https://iocl.com"), "iocl.com")

    def test_is_same_registrable_domain_or_ats(self):
        # Same domain / subdomain
        self.assertTrue(is_same_registrable_domain_or_ats("https://careers.tatapower.com", "https://www.tatapower.com"))
        self.assertTrue(is_same_registrable_domain_or_ats("https://tatapower.com/csr", "https://tatapower.com"))
        # Unrelated domain
        self.assertFalse(is_same_registrable_domain_or_ats("https://randomdomain.com/jobs", "https://tatapower.com"))
        # Known ATS domains
        self.assertTrue(is_same_registrable_domain_or_ats("https://tatapower.myworkdayjobs.com/en-US/careers", "https://tatapower.com"))
        self.assertTrue(is_same_registrable_domain_or_ats("https://jobs.lever.co/tatapower", "https://tatapower.com"))
        self.assertTrue(is_same_registrable_domain_or_ats("https://boards.greenhouse.io/tatapower", "https://tatapower.com"))

    def test_verify_careers_url_content_jsonld(self):
        html = """
        <html>
            <head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org/",
                    "@type": "JobPosting",
                    "title": "Software Engineer",
                    "description": "Develop high-scale cloud platforms"
                }
                </script>
            </head>
            <body><h1>Welcome to Careers</h1></body>
        </html>
        """
        has_signals, conf, signals = verify_careers_url_content(html, "https://company.com/careers")
        self.assertTrue(has_signals)
        self.assertGreaterEqual(conf, 0.70)
        self.assertIn("jsonld_job_posting", signals)

    def test_verify_careers_url_content_ats_iframe(self):
        html = """
        <html>
            <body>
                <h1>Current Openings</h1>
                <iframe src="https://company.myworkdayjobs.com/en-US/careers" width="100%" height="600"></iframe>
            </body>
        </html>
        """
        has_signals, conf, signals = verify_careers_url_content(html, "https://company.com/careers")
        self.assertTrue(has_signals)
        self.assertTrue(any("ats_reference" in s for s in signals))

    def test_verify_careers_url_content_apply_links(self):
        html = """
        <html>
            <body>
                <div class="openings">
                    <div>
                        <h2>Data Engineer</h2>
                        <a href="/job/49210">Apply Now</a>
                    </div>
                    <div>
                        <h2>DevOps Lead</h2>
                        <a href="/job/49211">Apply Now</a>
                    </div>
                </div>
            </body>
        </html>
        """
        has_signals, conf, signals = verify_careers_url_content(html, "https://company.com/careers")
        self.assertTrue(has_signals)
        self.assertTrue(any("job_action_links" in s for s in signals))

    def test_verify_careers_url_content_empty_or_no_signals(self):
        html = "<html><body><h1>About Our Leadership Team</h1><p>We are dedicated to excellence.</p></body></html>"
        has_signals, conf, signals = verify_careers_url_content(html, "https://company.com/about")
        self.assertFalse(has_signals)
        self.assertEqual(conf, 0.25)
        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
