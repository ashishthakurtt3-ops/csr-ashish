"""
tests/test_reliance_adapter.py
==============================
Unit tests for the dedicated Reliance Careers Portal Adapter (careers.ril.com).
Uses real captured page fixtures for job listings and job detail pages.
"""
import unittest
from modules.crawler_engine.adapters.reliance import ReliancePortalAdapter
from modules.crawler_engine.evidence_verifier import IndependentEvidenceVerifier


SAMPLE_GRID_HTML_PAGE_1 = """
<html>
<body>
<table class="mytable table table-bordered" id="MainContent_rgJobs">
    <tr>
        <th>Sr.No.</th><th>Job Title</th><th>Functional Area</th><th>Location</th><th>Posting Date</th>
    </tr>
    <tr>
        <td>1</td>
        <td><a href="frmJobSearch.aspx?JBTITLE=FaN3xPzXCHzbhUw0mJydyw==&jbID=yftrzlv68JQAoHWmMKkdYw==">Team Member - Platform ( 83065921 )</a></td>
        <td>Reliance Foundation</td>
        <td>Kutch</td>
        <td>28 Oct 2026</td>
    </tr>
    <tr>
        <td>2</td>
        <td><a href="frmJobSearch.aspx?JBTITLE=oZ8x2qgnLWZ0h9lInK7Z3Q==&jbID=Bgr5ERI2ABrhklGPDpoVRA==">Field Executive ( 83062640 )</a></td>
        <td>Manufacturing</td>
        <td>Jamnagar</td>
        <td>26 Oct 2026</td>
    </tr>
    <tr>
        <td>3</td>
        <td><a href="frmJobSearch.aspx?JBTITLE=JXWc7smk0h1gM9r+1YHuQQ==&jbID=gZDsRQZiHhCofsGtz0SQTg==">Const Engr - CHO Projects MEP ( 83055935 )</a></td>
        <td>Project Management</td>
        <td>Jamnagar</td>
        <td>22 Oct 2026</td>
    </tr>
    <tr>
        <td colspan="5">
            <span id="MainContent_rgJobs_CurrentPageLabel">Showing 1 of 5 Pages</span>
            <input type="submit" id="MainContent_rgJobs_lnkNext" value="Next" />
        </td>
    </tr>
</table>
</body>
</html>
"""

SAMPLE_DETAIL_HTML = """
<html>
<head><title>Team Member - Platform [83065921] | Reliance Careers</title></head>
<body>
<div id="MainContent_divJobDetails">
    <span id="MainContent_lblJobTitle">Team Member - Platform [83065921]</span>
    <span id="MainContent_lblPostedDate">28 Oct 2026</span>
    <span id="MainContent_lblSec">Reliance Foundation</span>
    <span id="MainContent_lblLoc">Kutch</span>
    <span id="MainContent_lblSummRole">Evaluate and collect all user requirements for digital rural platforms and collaborate with Reliance Foundation programme teams.</span>
    <span id="MainContent_lblEduReq">Necessary: A Master / Bachelor degree in design, computer science, or a related field - B.E, BCA, MCA.</span>
    <span id="MainContent_lblExpReq">Necessary: Minimum of two years of work experience as a UI / UX designer or related role.</span>
    <span id="MainContent_lblSkill">Hands on data analytics, Entrepreneurial Mindset, Interpersonal Skills, Development sector knowledge.</span>
    <input type="submit" id="MainContent_btnapply1" value="Apply now" />
</div>
</body>
</html>
"""


class TestRelianceAdapter(unittest.TestCase):

    def setUp(self):
        self.adapter = ReliancePortalAdapter()

    def test_can_handle_target_urls(self):
        self.assertTrue(self.adapter.can_handle("https://careers.ril.com/rilcareers/frmjobsearch.Aspx"))
        self.assertTrue(self.adapter.can_handle("https://careers.ril.com/rilcareers/index.aspx"))
        self.assertTrue(self.adapter.can_handle("https://rcareers.ril.com/sap/bc/bsp/sap/zerec_home_page/home_page.do"))
        self.assertFalse(self.adapter.can_handle("https://www.tcs.com/careers"))

    def test_title_and_job_id_parsing(self):
        title, jid = self.adapter.parse_job_title_and_id("Team Member - Platform ( 83065921 )")
        self.assertEqual(title, "Team Member - Platform")
        self.assertEqual(jid, "83065921")

        title2, jid2 = self.adapter.parse_job_title_and_id("Field Executive [83062640]")
        self.assertEqual(title2, "Field Executive")
        self.assertEqual(jid2, "83062640")

    def test_group_entity_attribution(self):
        emp1, t1 = self.adapter.determine_group_entity("Reliance Foundation", "Team Member")
        self.assertEqual(emp1, "Reliance Foundation")
        self.assertEqual(t1, "FOUNDATION")

        emp2, t2 = self.adapter.determine_group_entity("Manufacturing", "Field Executive")
        self.assertEqual(emp2, "Reliance Industries Limited")
        self.assertEqual(t2, "PARENT_COMPANY")

        emp3, t3 = self.adapter.determine_group_entity("Reliance Retail Stores", "Store Manager")
        self.assertEqual(emp3, "Reliance Retail")
        self.assertEqual(t3, "SUBSIDIARY")

        emp4, t4 = self.adapter.determine_group_entity("Digital Services", "Jio Network Engineer")
        self.assertEqual(emp4, "Reliance Jio Infocomm Limited")
        self.assertEqual(t4, "SUBSIDIARY")

        emp5, t5 = self.adapter.determine_group_entity("Solar Photovoltaics", "Reliance New Energy Engineer")
        self.assertEqual(emp5, "Reliance New Energy")
        self.assertEqual(t5, "SUBSIDIARY")

    def test_grid_parsing_fixture(self):
        rows = self.adapter.extract_from_grid_html(SAMPLE_GRID_HTML_PAGE_1, "COMP_TOP200_001")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["job_title"], "Team Member - Platform")
        self.assertEqual(rows[0]["job_id"], "83065921")
        self.assertEqual(rows[0]["employer_name"], "Reliance Foundation")
        self.assertEqual(rows[0]["location"], "Kutch")
        self.assertEqual(rows[0]["posted_date"], "28 Oct 2026")

        self.assertEqual(rows[1]["job_title"], "Field Executive")
        self.assertEqual(rows[1]["job_id"], "83062640")
        self.assertEqual(rows[1]["employer_name"], "Reliance Industries Limited")
        self.assertEqual(rows[1]["location"], "Jamnagar")

    def test_detail_parsing_fixture(self):
        detail = self.adapter.extract_detail_from_html(SAMPLE_DETAIL_HTML, "https://careers.ril.com/rilcareers/frmJobSearch.aspx?id=1")
        self.assertTrue(detail["is_valid_detail"])
        self.assertEqual(detail["clean_title"], "Team Member - Platform")
        self.assertEqual(detail["job_id"], "83065921")
        self.assertEqual(detail["posted_date"], "28 Oct 2026")
        self.assertEqual(detail["section"], "Reliance Foundation")
        self.assertEqual(detail["location"], "Kutch")
        self.assertIn("digital rural platforms", detail["responsibilities"])
        self.assertIn("BCA, MCA", detail["education"])
        self.assertIn("two years", detail["experience"])
        self.assertIn("data analytics", detail["skills"])

    def test_extract_jobs_generates_valid_extracted_records(self):
        records = self.adapter.extract_jobs("COMP_TOP200_001", "https://careers.ril.com/rilcareers/frmjobsearch.Aspx", SAMPLE_GRID_HTML_PAGE_1)
        self.assertEqual(len(records), 3)
        rec = records[0]
        self.assertEqual(rec.job_title, "Team Member - Platform")
        self.assertEqual(rec.external_job_id, "83065921")
        self.assertEqual(rec.ats_platform, "Reliance Careers Portal")
        self.assertEqual(rec.team, "Reliance Foundation")
        self.assertEqual(rec.location_raw, "Kutch")

        # Verify through IndependentEvidenceVerifier
        candidate_dict = {
            "job_title": rec.job_title,
            "application_url": rec.application_url
        }
        is_valid, decision, _ = IndependentEvidenceVerifier.verify_job_candidate(candidate_dict, f"ATS Adapter (Reliance Careers Portal): {rec.job_title}")
        self.assertTrue(is_valid)
        self.assertEqual(decision, "VERIFIED")


if __name__ == '__main__':
    unittest.main()

