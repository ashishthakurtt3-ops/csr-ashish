"""Django-native test suite for the website (public portal) application.

These tests are the migrated equivalents of the legacy ``tests/`` pytest
suite (``test_pagination.py``, ``test_jobs_api.py``, ``test_scoring.py``),
which targeted the retired FastAPI ``app`` package and were removed during
the Django-only cleanup. They validate the same behavioural contracts —
server-side pagination envelopes, jobs-board data-quality invariants and
the scoring engine — against the Django implementation.
"""

from django.test import Client, TestCase

from modules.admin_panel.models import (
    Company,
    Contact,
    CSROpportunity,
    CSRProject,
    Job,
    NGOCollaboration,
    OpportunityScore,
    Prospect,
)
from modules.website.utils.pagination import paginate_queryset
from modules.website.utils.scoring_service import (
    calculate_ngo_match,
    score_company,
)


def make_company(company_id, name, **kwargs):
    defaults = {
        "company_name": name,
        "nse_symbol": "SYM-%s" % company_id[-3:],
        "website_url": "https://example-%s.example/" % company_id.lower(),
        "careers_url": "https://example-%s.example/careers" % company_id.lower(),
        "csr_portal_url": "https://example-%s.example/csr" % company_id.lower(),
        "sector": "IT",
        "headquarters": "Bengaluru, Karnataka",
        "crawl_status": "CRAWLED",
    }
    defaults.update(kwargs)
    return Company.objects.create(company_id=company_id, **defaults)


class PaginationEngineTests(TestCase):
    """Unit tests for modules.website.utils.pagination.paginate_queryset."""

    @classmethod
    def setUpTestData(cls):
        for i in range(1, 6):
            make_company("PAG00%d" % i, "Pagination Company %d" % i)

    def _qs(self):
        return Company.objects.filter(
            company_id__startswith="PAG").order_by("company_name")

    def test_unpaginated_call_returns_flat_list(self):
        result = paginate_queryset(
            self._qs(), lambda c: {"company_id": c.company_id})
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)

    def test_paginated_call_returns_full_envelope(self):
        result = paginate_queryset(
            self._qs(), lambda c: {"company_id": c.company_id},
            page=1, page_size=2,
        )
        self.assertIsInstance(result, dict)
        for key in ("items", "total", "page", "page_size",
                    "total_pages", "has_next", "has_prev"):
            self.assertIn(key, result)
        self.assertEqual(result["page"], 1)
        self.assertEqual(result["page_size"], 2)
        self.assertEqual(result["total"], 5)
        self.assertEqual(result["total_pages"], 3)
        self.assertTrue(result["has_next"])
        self.assertFalse(result["has_prev"])
        self.assertEqual(len(result["items"]), 2)

    def test_last_page_boundary(self):
        result = paginate_queryset(
            self._qs(), lambda c: {"company_id": c.company_id},
            page=3, page_size=2,
        )
        self.assertEqual(len(result["items"]), 1)
        self.assertFalse(result["has_next"])
        self.assertTrue(result["has_prev"])

    def test_invalid_page_falls_back_to_flat_list(self):
        result = paginate_queryset(
            self._qs(), lambda c: {"company_id": c.company_id},
            page="not-a-number",
        )
        self.assertIsInstance(result, list)

    def test_page_size_is_capped(self):
        result = paginate_queryset(
            self._qs(), lambda c: {"company_id": c.company_id},
            page=1, page_size=500,
        )
        self.assertEqual(result["page_size"], 100)


class PortalSmokeTests(TestCase):
    def test_homepage_health_stats(self):
        client = Client()
        self.assertEqual(client.get("/").status_code, 200)
        health = client.get("/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json().get("status"), "ok")
        stats = client.get("/stats")
        self.assertEqual(stats.status_code, 200)
        payload = stats.json()
        for key in (
            "total_companies",
            "csr_projects",
            "ngo_collaborations",
            "jobs_tracked",
            "contacts_extracted",
            "active_opportunities",
        ):
            self.assertIn(key, payload)

class CompaniesApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a = make_company("TST001", "Tata Test Industries", sector="ENERGY")
        cls.b = make_company("TST002", "Test Finance Bank", sector="BANKING")
        OpportunityScore.objects.create(company=cls.a, score=82.5)
        CSRProject.objects.create(
            company=cls.a, project_name="Test School Program",
            category="Education", confidence=0.9,
        )

    def test_unpaginated_list_returns_array(self):
        data = Client().get("/companies").json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)

    def test_paginated_envelope(self):
        data = Client().get(
            "/companies", {"page": 1, "page_size": 1}).json()
        self.assertIsInstance(data, dict)
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertGreaterEqual(data["total"], 2)
        self.assertEqual(len(data["items"]), 1)

    def test_search_filters(self):
        data = Client().get("/companies", {"q": "Tata Test"}).json()
        names = [c["company_name"] for c in data]
        self.assertIn("Tata Test Industries", names)

    def test_sector_filter_and_detail(self):
        data = Client().get("/companies", {"sector": "BANKING"}).json()
        self.assertTrue(all(c["sector"] == "BANKING" for c in data))
        detail = Client().get("/companies/TST001").json()
        self.assertEqual(detail["company_name"], "Tata Test Industries")

    def test_dossier_reports_who_why_how(self):
        dossier = Client().get("/companies/TST001/dossier").json()
        self.assertIn("strategic_playbook", dossier)
        playbook = dossier["strategic_playbook"]
        self.assertIn("who", playbook)
        self.assertIn("why", playbook)
        self.assertIn("how", playbook)

    def test_recommendations_envelope(self):
        data = Client().get(
            "/recommendations", {"page": 1, "page_size": 5}).json()
        self.assertIn("items", data)
        self.assertIn("total", data)


class JobsApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = make_company(
            "JOB001", "Jobs Test Corp", sector="IT",
            careers_url="https://jobs-test.example/careers",
        )
        Job.objects.create(
            company=cls.company, job_id="J-1",
            job_title="CSR Program Manager",
            department="CSR", location="Mumbai", state="Maharashtra",
            work_mode="Hybrid", status="ACTIVE", link_status="VERIFIED_HTTP_200",
            application_url="https://jobs-test.example/apply/J-1",
        )
        Job.objects.create(
            company=cls.company, job_id="J-2",
            job_title="Backend Engineer",
            department="Engineering", location="Bengaluru",
            state="Karnataka", work_mode="Remote", status="ACTIVE",
            link_status="VERIFIED_HTTP_200",
            application_url="https://jobs-test.example/apply/J-2",
        )

    def test_jobs_list_is_flat_without_page(self):
        data = Client().get("/jobs").json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2)
        row = data[0]
        self.assertIn("company_name", row)
        self.assertIn("nse_symbol", row)
        self.assertIn("application_url", row)

    def test_jobs_paginated_envelope(self):
        data = Client().get("/jobs", {"page": 1, "page_size": 1}).json()
        self.assertIn("items", data)
        self.assertIn("total", data)
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["items"]), 1)

    def test_every_application_link_is_absolute_http(self):
        data = Client().get("/jobs", {"limit": 500}).json()
        for row in data:
            url = row.get("application_url") or ""
            self.assertTrue(
                url.startswith("http"),
                "Non-absolute application URL for %r: %r"
                % (row.get("job_title"), url),
            )

    def test_impact_only_filter(self):
        data = Client().get("/jobs", {"impact_only": "true"}).json()
        titles = [r["job_title"] for r in data]
        self.assertIn("CSR Program Manager", titles)
        self.assertNotIn("Backend Engineer", titles)

    def test_work_mode_filter(self):
        data = Client().get("/jobs", {"work_mode": "Remote"}).json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["job_title"], "Backend Engineer")

    def test_jobs_summary_contract(self):
        summary = Client().get("/jobs/summary").json()
        for key in (
            "total_roles", "active_roles", "impact_roles",
            "remote_roles", "companies_hiring", "by_department",
            "by_location", "by_company",
        ):
            self.assertIn(key, summary)
        self.assertEqual(summary["total_roles"], 2)
        self.assertEqual(summary["impact_roles"], 1)

class CSRAndMatchingApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = make_company(
            "CSR001", "CSR Match Corp", sector="ENERGY",
            website_url="https://csr-match.example/",
        )
        CSRProject.objects.create(
            company=cls.company, project_name="Village Schools",
            category="Education", state="Maharashtra",
            geographic_location="Maharashtra", confidence=0.95,
        )
        CSROpportunity.objects.create(
            company=cls.company, title="Education Partner RFP",
            category="Education", status="OPEN",
        )
        NGOCollaboration.objects.create(
            company=cls.company, ngo_name="Test Foundation",
        )
        Contact.objects.create(
            company=cls.company, name="CSR Head",
            email="csr@csr-match.example", verification_status="VERIFIED",
        )
        Prospect.objects.create(company=cls.company, stage="Shortlisted")

    def test_csr_projects_and_opportunities(self):
        client = Client()
        projects = client.get("/csr/projects").json()
        self.assertIsInstance(projects, (list, dict))
        items = projects["items"] if isinstance(projects, dict) else projects
        self.assertTrue(
            any(p.get("project_name") == "Village Schools" for p in items))
        opps = client.get(
            "/csr/opportunities", {"page": 1, "page_size": 10}).json()
        self.assertIn("items", opps)
        self.assertTrue(
            any(o.get("title") == "Education Partner RFP"
                for o in opps["items"]))

    def test_ngo_match_post_scores_and_sorts(self):
        import json

        client = Client()
        payload = {
            "profile": {
                "focus_areas": ["Education"],
                "locations": ["Maharashtra"],
            },
            "limit": 10,
        }
        data = client.post(
            "/ngo/matches", data=json.dumps(payload),
            content_type="application/json",
        ).json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)
        scores = [r["match_score"] for r in data]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(all(0 <= s <= 100 for s in scores))

    def test_prospects_crud(self):
        import json

        client = Client()
        listed = client.get("/prospects").json()
        items = listed["items"] if isinstance(listed, dict) else listed
        self.assertTrue(
            any(p.get("company_id") == "CSR001" for p in items))
        created = client.post(
            "/prospects",
            data=json.dumps({"company_id": "CSR001", "notes": "Follow up"}),
            content_type="application/json",
        )
        self.assertIn(created.status_code, (200, 201))
        deleted = client.delete("/prospects/CSR001/")
        self.assertIn(deleted.status_code, (200, 204))
        self.assertFalse(
            Prospect.objects.filter(company_id="CSR001").exists())


class ScoringEngineTests(TestCase):
    def test_score_is_bounded(self):
        company = {"company_id": "COMP_001", "company_name": "Test Corp"}
        evidence = {
            "csr_pages": 2,
            "opportunity_pages": 2,
            "ngo_collaborations": 2,
            "recent_projects": 3,
            "contacts": 1,
            "categories": ["Education"],
            "states": ["Maharashtra"],
            "scrape_complete": True,
        }
        result = score_company(
            company, evidence,
            {"focus_areas": ["Education"], "locations": ["Maharashtra"]},
        )
        self.assertTrue(0 <= result["score"] <= 100)
        self.assertEqual(result["evidence_status"], "Evidence-based")

    def test_pending_when_not_scraped(self):
        result = score_company(
            {"company_id": "X"}, {"scrape_complete": False})
        self.assertEqual(result["evidence_status"], "Pending scrape")

    def test_ngo_match_dimensions_bounded(self):
        company = {
            "company_id": "COMP_001",
            "company_name": "GreenTech Energy Ltd",
            "sector": "ENERGY",
            "nse_symbol": "GREENTECH",
            "website_url": "https://greentech.example/",
            "csr_portal_url": "https://greentech.example/csr",
        }
        projects = [
            {"category": "Education;Health",
             "geographic_location": "Maharashtra"},
            {"category": "Education", "state": "Karnataka"},
        ]
        profile = {
            "focus_areas": ["Education"],
            "locations": ["Maharashtra"],
            "beneficiaries": ["Children"],
            "project_scale": "medium",
        }
        result = calculate_ngo_match(company, projects, profile)
        for dimension, value in result["match_components"].items():
            self.assertTrue(
                0 <= value <= 100,
                "dimension %r out of bounds: %r" % (dimension, value),
            )
        self.assertTrue(0 <= result["match_score"] <= 100)
        self.assertTrue(len(result["match_reasons"]) > 0)
