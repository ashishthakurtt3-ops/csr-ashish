"""Django-native test suite for the website (public portal) application.

These tests are the migrated equivalents of the legacy ``tests/`` pytest
suite (``test_pagination.py``, ``test_jobs_api.py``, ``test_scoring.py``),
which targeted the retired FastAPI ``app`` package and were removed during
the Django-only cleanup. They validate the same behavioural contracts —
server-side pagination envelopes, jobs-board data-quality invariants and
the scoring engine — against the Django implementation.
"""

import json
import os
from django.conf import settings
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


from django.utils import timezone

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


def make_verified_job(company, job_id, **kwargs):
    now = timezone.now()
    defaults = {
        "company": company,
        "job_id": job_id,
        "job_title": f"Job {job_id}",
        "status": "ACTIVE",
        "verification_status": "SOURCE_CONFIRMED",
        "source_url": f"https://example.com/careers/{job_id}",
        "retrieved_at": now,
        "evidence_text": f"Authentic career posting for {job_id}",
        "content_hash": "sha256_mock_hash_for_test",
        "link_status": "PUBLISHED",
        "application_url": f"https://example.com/apply/{job_id}",
    }
    defaults.update(kwargs)
    job = Job.objects.create(**defaults)
    job.verification_status = "PUBLISHED"
    job.save()
    return job


def make_verified_csr(company, csr_id, **kwargs):
    now = timezone.now()
    defaults = {
        "company": company,
        "csr_id": csr_id,
        "project_name": f"Project {csr_id}",
        "verification_status": "SOURCE_CONFIRMED",
        "source_url": f"https://example.com/csr/{csr_id}",
        "retrieved_at": now,
        "evidence_text": f"Authentic CSR report for {csr_id}",
        "content_hash": "sha256_mock_hash_for_csr",
        "link_status": "PUBLISHED",
    }
    defaults.update(kwargs)
    p = CSRProject.objects.create(**defaults)
    p.verification_status = "PUBLISHED"
    p.save()
    return p


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
        make_verified_job(
            cls.company, "J-1", job_title="CSR Program Manager",
            department="CSR", location="Mumbai", state="Maharashtra", work_mode="Hybrid"
        )
        make_verified_job(
            cls.company, "J-2", job_title="Backend Engineer",
            department="Engineering", location="Bengaluru", state="Karnataka", work_mode="Remote"
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
        p = CSRProject.objects.create(
            company=cls.company, project_name="Village Schools",
            category="Education", state="Maharashtra",
            geographic_location="Maharashtra", confidence=0.95,
            verification_status="SOURCE_CONFIRMED", link_status="SOURCE_CONFIRMED",
            evidence_text="Verified CSR Project: Village Schools",
            source_url="https://csr-match.example/projects/1",
            retrieved_at=timezone.now().isoformat()
        )
        p.verification_status = "PUBLISHED"
        p.save()
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


class SubscriptionModelAndCatalogTests(TestCase):
    """Test suite verifying Starter, Pro, Enterprise, and Foundation subscription model entitlements and catalog."""

    @classmethod
    def setUpTestData(cls):
        from modules.admin_panel.management.commands.seed_subscription_plans import Command
        cmd = Command()
        cmd.handle()

    def test_plan_entitlements_and_properties(self):
        from modules.admin_panel.models import Subscription

        # Starter tier
        sub_starter = Subscription(subscription_id="SUB_F1", tenant_id="t_free", plan_id="starter")
        self.assertEqual(sub_starter.plan_tier, "starter")
        self.assertTrue(sub_starter.is_free)
        self.assertFalse(sub_starter.is_pro)
        self.assertFalse(sub_starter.is_enterprise)
        self.assertFalse(sub_starter.can_view_contacts)
        self.assertFalse(sub_starter.can_reprobe_crawler)
        self.assertFalse(sub_starter.can_access_api)
        self.assertFalse(sub_starter.can_access_audit_packs)
        self.assertEqual(sub_starter.max_export_rows, 25)
        self.assertEqual(sub_starter.max_allowed_seats, 1)

        # Pro tier
        sub_pro = Subscription(subscription_id="SUB_P1", tenant_id="t_pro", plan_id="pro")
        self.assertEqual(sub_pro.plan_tier, "pro")
        self.assertTrue(sub_pro.is_pro)
        self.assertTrue(sub_pro.can_view_contacts)
        self.assertTrue(sub_pro.can_reprobe_crawler)
        self.assertFalse(sub_pro.can_access_api)
        self.assertFalse(sub_pro.can_access_audit_packs)
        self.assertEqual(sub_pro.max_export_rows, 1000)
        self.assertEqual(sub_pro.max_allowed_seats, 3)

        # Enterprise tier
        sub_enterprise = Subscription(subscription_id="SUB_U1", tenant_id="t_ultra", plan_id="enterprise")
        self.assertEqual(sub_enterprise.plan_tier, "enterprise")
        self.assertTrue(sub_enterprise.is_enterprise)
        self.assertTrue(sub_enterprise.can_view_contacts)
        self.assertTrue(sub_enterprise.can_reprobe_crawler)
        self.assertTrue(sub_enterprise.can_access_api)
        self.assertTrue(sub_enterprise.can_access_audit_packs)
        self.assertIsNone(sub_enterprise.max_export_rows)
        self.assertEqual(sub_enterprise.max_allowed_seats, 15)

    def test_catalog_and_plan_resolution(self):
        from modules.website.utils.subscription_service import get_plan, require_plan, plans_payload

        # Canonical lookup
        starter = get_plan("starter")
        pro = get_plan("pro")
        enterprise = get_plan("enterprise")
        foundation = get_plan("foundation")
        self.assertIsNotNone(starter)
        self.assertIsNotNone(pro)
        self.assertIsNotNone(enterprise)
        self.assertIsNotNone(foundation)

        # Alias lookup backwards-compatibility
        self.assertEqual(get_plan("free")["id"], "starter")
        self.assertEqual(get_plan("ultra")["id"], "enterprise")
        self.assertEqual(get_plan("api")["id"], "foundation")

        # Plans payload check
        payload = plans_payload()
        self.assertEqual(payload["status"], "success")
        plan_ids = [p["id"] for p in payload["plans"]]
        self.assertEqual(plan_ids, ["starter", "pro", "enterprise", "foundation"])


class CategoryExclusivityAndCoverageRegressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = make_company(
            "CAT001", "Category Test Corp", sector="IT",
            careers_url="https://cat-test.example/careers",
        )
        # Create representative jobs:
        # Create representative jobs using evidence-backed verified lifecycle:
        make_verified_job(cls.company, "CAT-1", job_title="Senior Developer", department="Technology")
        make_verified_job(cls.company, "CAT-2", job_title="Mechanical Engineer", department="Engineering")
        make_verified_job(cls.company, "CAT-3", job_title="Financial Analyst", department="Finance")
        make_verified_job(cls.company, "CAT-4", job_title="Account Manager", department="Sales")
        make_verified_job(cls.company, "CAT-5", job_title="Growth Specialist", department="Growth")
        make_verified_job(cls.company, "CAT-6", job_title="Software Lead", department=None)

        # 7. Quarantined legacy job that must NEVER appear in public APIs
        Job.objects.create(
            company=cls.company, job_id="CAT-LEGACY-1", job_title="Legacy Fake Job",
            department="Technology", status="ACTIVE", link_status="PUBLISHED",
            verification_status="LEGACY_UNVERIFIED",
            application_url="https://cat-test.example/apply/legacy",
        )

        # CSR Projects for MECE testing
        csr_data = [
            (9001, "Health Clinic", "Healthcare & Sanitation", "VERIFIED"),
            (9002, "Village School", "Education & Skill Development", "VERIFIED"),
            (9003, "Water Pipeline", "Rural Infrastructure", "VERIFIED"),
            (9004, "Solar Installation", "Environment & Sustainability", "VERIFIED"),
            (9005, "Self Help Groups", "Women Empowerment & Livelihood", "VERIFIED"),
            (9006, "Flood Relief", "Disaster Relief & Rehabilitation", "VERIFIED"),
            (9007, "Youth Sports", "Sports & Culture", "VERIFIED"),
            (9008, "Animal Sanctuary", "Animal Welfare", "VERIFIED"),
            (9009, "General Foundation Grant", None, "VERIFIED"),
            (9010, "Fake Seed Project", "Healthcare", "LEGACY_UNVERIFIED"),
        ]
        for cid, name, cat, vstat in csr_data:
            if vstat == "VERIFIED":
                make_verified_csr(cls.company, cid, project_name=name, category=cat)
            else:
                CSRProject.objects.create(
                    company=cls.company, csr_id=cid, project_name=name,
                    category=cat, verification_status=vstat, link_status="PUBLISHED",
                    source_url="https://cat-test.example/csr",
                )

    def test_job_category_mutual_exclusivity_and_complete_coverage(self):
        client = Client()
        r_all = client.get("/jobs", {"category": "all", "page": 1, "page_size": 20}).json()
        total_all = r_all["total"]
        self.assertEqual(total_all, 6)

        categories_to_test = [
            "tech", "engineering", "finance", "sales", "others", "uncategorized"
        ]
        cat_ids_map = {}
        for cat in categories_to_test:
            resp = client.get("/jobs", {"category": cat, "page": 1, "page_size": 20}).json()
            ids = set(item["job_row_id"] for item in resp["items"])
            cat_ids_map[cat] = ids

        # 1. Pairwise Mutual Exclusivity: Intersection between any two categories MUST be empty
        for i, c1 in enumerate(categories_to_test):
            for j, c2 in enumerate(categories_to_test):
                if i < j:
                    overlap = cat_ids_map[c1].intersection(cat_ids_map[c2])
                    self.assertEqual(
                        len(overlap), 0,
                        f"Overlap detected between category '{c1}' and '{c2}': IDs {overlap}"
                    )

        # 2. Complete Coverage: Sum of counts must equal total_all
        sum_counts = sum(len(ids) for ids in cat_ids_map.values())
        self.assertEqual(
            sum_counts, total_all,
            f"Category sum ({sum_counts}) does not equal total jobs ({total_all})"
        )

        # 3. Union of all categories must contain all jobs
        all_ids = set(item["job_row_id"] for item in r_all["items"])
        union_ids = set().union(*cat_ids_map.values())
        self.assertEqual(union_ids, all_ids)

    def test_csr_project_category_mutual_exclusivity_and_complete_coverage(self):
        client = Client()
        r_all = client.get("/csr/projects", {"category": "all", "page": 1, "page_size": 20}).json()
        total_all = r_all["total"]
        self.assertEqual(total_all, 9)  # 9 verified, 1 quarantined excluded

        csr_categories = [
            "healthcare", "education", "rural", "environment", "women",
            "relief", "sports", "others", "uncategorized"
        ]
        cat_ids_map = {}
        for cat in csr_categories:
            resp = client.get("/csr/projects", {"category": cat, "page": 1, "page_size": 20}).json()
            ids = set(item["csr_id"] for item in resp["items"])
            cat_ids_map[cat] = ids

        # 1. Pairwise Mutual Exclusivity: 0 Overlaps
        for i, c1 in enumerate(csr_categories):
            for j, c2 in enumerate(csr_categories):
                if i < j:
                    overlap = cat_ids_map[c1].intersection(cat_ids_map[c2])
                    self.assertEqual(
                        len(overlap), 0,
                        f"Overlap detected between CSR category '{c1}' and '{c2}': IDs {overlap}"
                    )

        # 2. Complete Coverage: Sum equals total_all
        sum_counts = sum(len(ids) for ids in cat_ids_map.values())
        self.assertEqual(
            sum_counts, total_all,
            f"CSR Category sum ({sum_counts}) does not equal total projects ({total_all})"
        )

        # 3. Union equals all project IDs
        all_ids = set(item["csr_id"] for item in r_all["items"])
        union_ids = set().union(*cat_ids_map.values())
        self.assertEqual(union_ids, all_ids)

    def test_quarantined_records_excluded_from_public_apis(self):
        client = Client()
        # Verify legacy job is not in /jobs
        resp_jobs = client.get("/jobs", {"page": 1, "page_size": 50}).json()
        job_ids = [item["job_id"] for item in resp_jobs["items"]]
        self.assertNotIn("CAT-LEGACY-1", job_ids)

        # Verify legacy CSR project is not in /csr/projects
        resp_csr = client.get("/csr/projects", {"page": 1, "page_size": 50}).json()
        csr_ids = [item["csr_id"] for item in resp_csr["items"]]
        self.assertNotIn(9010, csr_ids)

    def test_pagination_totals_consistency(self):
        client = Client()
        r_all_p1 = client.get("/jobs", {"page": 1, "page_size": 2}).json()
        r_all_p2 = client.get("/jobs", {"page": 2, "page_size": 2}).json()

        self.assertEqual(r_all_p1["total"], 6)
        self.assertEqual(r_all_p2["total"], 6)
        self.assertEqual(len(r_all_p1["items"]), 2)
        self.assertEqual(len(r_all_p2["items"]), 2)

        # Verify items on p1 and p2 are distinct
        p1_ids = [item["job_row_id"] for item in r_all_p1["items"]]
        p2_ids = [item["job_row_id"] for item in r_all_p2["items"]]
        self.assertEqual(len(set(p1_ids).intersection(set(p2_ids))), 0)

    def test_csr_opportunities_scope_and_deadlines(self):
        client = Client()
        # Seed test opportunities with different types and missing deadlines
        comp = make_company("COMP_OPP_TEST", "Opportunity Test Corp")
        now = timezone.now()
        opp_csr = CSROpportunity.objects.create(
            company=comp,
            title="Test Social Impact Grant RFP",
            opportunity_type="Grant / RFP",
            category="Education",
            status="OPEN",
            verification_status="EXTRACTED",
            source_url="https://example.com/rfp",
            retrieved_at=now,
            submission_deadline=None,
        )
        opp_proc = CSROpportunity.objects.create(
            company=comp,
            title="Test Equipment Procurement EOI",
            opportunity_type="Procurement / Vendor EOI",
            category="Procurement & Supply Chain",
            status="OPEN",
            verification_status="EXTRACTED",
            source_url="https://example.com/eoi",
            retrieved_at=now,
            submission_deadline="2026-12-31",
        )
        opp_rej = CSROpportunity.objects.create(
            company=comp,
            title="Test Rejected Video Tutorial",
            opportunity_type="Video",
            status="OPEN",
            verification_status="REJECTED",
            source_url="https://example.com/video",
            retrieved_at=now,
        )

        # 1. Verification that default scope is CSR-only and REJECTED opportunities are excluded
        res_default = client.get("/csr/opportunities", {"page": 1, "company": "COMP_OPP_TEST"}).json()
        opp_ids_def = [item["opp_id"] for item in res_default["items"]]
        self.assertIn(opp_csr.opp_id, opp_ids_def)
        self.assertNotIn(opp_proc.opp_id, opp_ids_def)
        self.assertNotIn(opp_rej.opp_id, opp_ids_def)

        # 1b. Verification that scope=all includes both CSR grants and procurement notices
        res_all = client.get("/csr/opportunities", {"page": 1, "company": "COMP_OPP_TEST", "scope": "all"}).json()
        opp_ids = [item["opp_id"] for item in res_all["items"]]
        self.assertIn(opp_csr.opp_id, opp_ids)
        self.assertIn(opp_proc.opp_id, opp_ids)
        self.assertNotIn(opp_rej.opp_id, opp_ids)

        # 2. Test scope=csr_only filter
        res_csr = client.get("/csr/opportunities", {"page": 1, "company": "COMP_OPP_TEST", "scope": "csr_only"}).json()
        csr_ids = [item["opp_id"] for item in res_csr["items"]]
        self.assertIn(opp_csr.opp_id, csr_ids)
        self.assertNotIn(opp_proc.opp_id, csr_ids)

        # 3. Test scope=procurement filter
        res_proc = client.get("/csr/opportunities", {"page": 1, "company": "COMP_OPP_TEST", "scope": "procurement"}).json()
        proc_ids = [item["opp_id"] for item in res_proc["items"]]
        self.assertIn(opp_proc.opp_id, proc_ids)
        self.assertNotIn(opp_csr.opp_id, proc_ids)

        # 4. Test deadline fallback assertion: missing deadline must be None
        csr_item = next(i for i in res_csr["items"] if i["opp_id"] == opp_csr.opp_id)
        self.assertIsNone(csr_item["submission_deadline"], "Missing deadline must be serialized as None, never a placeholder.")
        proc_item = next(i for i in res_proc["items"] if i["opp_id"] == opp_proc.opp_id)
        self.assertEqual(proc_item["submission_deadline"], "2026-12-31")

    def test_csr_api_csv_export(self):
        client = Client()
        # Test CSR projects CSV export
        resp = client.get("/csr/projects", {"format": "csv"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp["Content-Type"])
        self.assertIn("Project ID,Company Name", resp.content.decode("utf-8"))

        # Test CSR opportunities CSV export
        resp_opp = client.get("/csr/opportunities", {"format": "csv"})
        self.assertEqual(resp_opp.status_code, 200)
        self.assertIn("text/csv", resp_opp["Content-Type"])
        self.assertIn("Opportunity ID,Company ID", resp_opp.content.decode("utf-8"))

    def test_platform_stats_and_csr_financial_truth(self):
        client = Client()
        resp = client.get("/stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        # 1. Statutory CSR expenditure is unconfirmed in web scan, must be None (null), never zero
        self.assertIsNone(data.get("total_csr_budget_cr"))
        self.assertIsNone(data.get("statutory_csr_budget_cr"))
        self.assertNotEqual(data.get("total_csr_budget_cr"), 0)

        # 2. Sustainability outlay is exposed separately with source and reporting period
        self.assertEqual(data.get("sustainability_outlay_cr"), 1.60)
        details = data.get("sustainability_outlay_details", {})
        self.assertEqual(details.get("amount_cr"), 1.60)
        self.assertEqual(details.get("entity"), "Mahindra & Mahindra Limited")
        self.assertEqual(details.get("reporting_period"), "FY 2023-24")
        self.assertIn("Sustainability", details.get("classification", ""))


class CriticalCorrectiveAuditTests(TestCase):
    """
    Critical Corrective Audit regression test suite verifying:
    1. HUL corporate identity invariants (authoritative BRSR CIN L15140MH1933PLC002030, never L19508MH1970PLC580547).
    2. Prevention of synthetic CIN reintroduction.
    3. Strict geographic attribution: exclusion of overseas postings from Indian corporate listings.
    4. Non-job UI button exclusion from published jobs.
    5. Commercial procurement/asset disposal tender exclusion from open CSR opportunities.
    6. Scraped navigation/table headers exclusion from published CSR projects.
    """

    def setUp(self):
        self.now = timezone.now()
        # Authoritative HUL record
        self.hul = Company.objects.create(
            company_id="COMP_TOP200_009",
            company_name="Hindustan Unilever Limited",
            legal_name="Hindustan Unilever Limited",
            cin="L15140MH1933PLC002030",
            isin="INE030A01027",
            nse_symbol="HINDUNILVR",
            bse_scrip_code="500696",
            website_url="https://www.hul.co.in",
            headquarters="Unilever House, B. D. Sawant Marg, Chakala, Andheri (East), Mumbai - 400099, Maharashtra, India",
            sector="Fast Moving Consumer Goods",
            verification_status="SOURCE_CONFIRMED",
            source_url="https://www.hul.co.in",
            retrieved_at=self.now,
            evidence_text="Official HUL BRSR Report FY 2023-24 (Section A.1). Incorporated 17 Oct 1933.",
        )

    def test_hul_authoritative_cin_invariants(self):
        """HUL CIN must strictly equal L15140MH1933PLC002030 and never the false seed value L19508MH1970PLC580547."""
        hul = Company.objects.get(company_id="COMP_TOP200_009")
        self.assertEqual(hul.cin, "L15140MH1933PLC002030")
        self.assertNotEqual(hul.cin, "L19508MH1970PLC580547")
        self.assertEqual(hul.legal_name, "Hindustan Unilever Limited")
        self.assertIn("Mumbai", hul.headquarters)
        self.assertEqual(hul.nse_symbol, "HINDUNILVR")
        self.assertEqual(hul.bse_scrip_code, "500696")

    def test_overseas_jobs_geographic_quarantine(self):
        """Overseas postings from parent/global ATS must be QUARANTINED and excluded from ACTIVE published jobs."""
        # Genuine Indian job
        job_india = Job.objects.create(
            company=self.hul,
            job_id="JOB_TEST_HUL_INDIA_01",
            job_title="Modern Trade Account Specialist",
            location="Mumbai Regional Office",
            status="ACTIVE",
            verification_status="SOURCE_CONFIRMED",
            source_url="https://unilever.wd3.myworkdayjobs.com/Unilever_Careers",
            retrieved_at=self.now,
            evidence_text="Verified Indian job posting in Mumbai.",
        )
        # Overseas job (Rotterdam / US)
        job_overseas = Job.objects.create(
            company=self.hul,
            job_id="JOB_TEST_HUL_OVERSEAS_01",
            job_title="Reliability Engineer (Hellmann's Mayo Factory)",
            location="Chicago, IL",
            status="INACTIVE",
            verification_status="QUARANTINED",
            verification_reason="OVERSEAS_PARENT_ENTITY_UNVERIFIED",
        )

        active_hul_jobs = Job.objects.filter(
            company=self.hul,
            status="ACTIVE",
            verification_status__in=["PUBLISHED", "SOURCE_CONFIRMED"],
        )
        self.assertIn(job_india, active_hul_jobs)
        self.assertNotIn(job_overseas, active_hul_jobs)

    def test_ui_button_and_pagination_exclusion(self):
        """Interactive website controls (Upload Resume, Review Accommodations, Next >>) must be REJECTED."""
        button_job = Job.objects.create(
            company=self.hul,
            job_id="JOB_TEST_BUTTON_01",
            job_title="Review Accommodations for Disability",
            status="INACTIVE",
            verification_status="REJECTED",
            verification_reason="UI_BUTTON_DEFECT",
        )
        published_jobs = Job.objects.filter(
            status="ACTIVE",
            verification_status__in=["PUBLISHED", "SOURCE_CONFIRMED"],
        )
        self.assertNotIn(button_job, published_jobs)

    def test_ui_navigation_and_informational_boilerplate_exclusion(self):
        """Scraped navigational headers (How to apply, Discover more, FAQs & Support) must be rejected and excluded."""
        from modules.crawler_engine.verification_service import VerificationService
        from modules.website.views.job_api_views import jobs_list_api, apply_job_safety_filters
        from django.test import RequestFactory
        import json

        junk_job = Job(
            company=self.hul,
            job_id="JOB_TEST_UI_JUNK_01",
            job_title="How to applyLearn more about our application process and explore helpful tips to guide you through each step.",
            source_url="https://www.siemens.com/in/en/company/jobs.html",
            retrieved_at=self.now,
            evidence_text="How to applyLearn more about our application process and explore helpful tips to guide you through each step.",
            status="ACTIVE",
            verification_status="SOURCE_CONFIRMED",
        )
        is_valid, reason = VerificationService.validate_job(junk_job)
        self.assertFalse(is_valid)
        self.assertIn("UI navigation defect", reason)

        junk_job.save()
        genuine_job = Job.objects.create(
            company=self.hul,
            job_id="JOB_TEST_GENUINE_01",
            job_title="Senior Instrumentation Engineer",
            source_url="https://www.siemens.com/in/en/company/jobs.html",
            retrieved_at=self.now,
            evidence_text="Senior Instrumentation Engineer opening in Mumbai plant.",
            status="ACTIVE",
            verification_status="SOURCE_CONFIRMED",
        )

        filtered_qs = apply_job_safety_filters(Job.objects.filter(status="ACTIVE"))
        self.assertIn(genuine_job, filtered_qs)
        self.assertNotIn(junk_job, filtered_qs)

        factory = RequestFactory()
        req = factory.get('/jobs')
        resp = jobs_list_api(req)
        self.assertEqual(resp.status_code, 200)
        resp_data = json.loads(resp.content.decode())
        items = resp_data if isinstance(resp_data, list) else resp_data.get('items', [])
        returned_ids = [it['job_id'] for it in items]
        self.assertIn(genuine_job.job_id, returned_ids)
        self.assertNotIn(junk_job.job_id, returned_ids)


    def test_commercial_tender_exclusion_from_csr_opportunities(self):
        """Commercial procurement / aircraft disposal tenders must be closed and excluded from open CSR opportunities."""
        tender_opp = CSROpportunity.objects.create(
            company=self.hul,
            title="Notice Inviting EOI for Purchase of Old Helicopters",
            opportunity_type="Procurement / Vendor EOI",
            status="CLOSED",
            verification_status="REJECTED",
            verification_reason="COMMERCIAL_NON_CSR_TENDER",
        )
        genuine_opp = CSROpportunity.objects.create(
            company=self.hul,
            title="RFP for Mandatory Section 135 Impact Assessment",
            opportunity_type="Grant / RFP",
            status="OPEN",
            verification_status="SOURCE_CONFIRMED",
            source_url="https://www.hul.co.in/csr/rfp",
            retrieved_at=self.now,
            evidence_text="Section 135 Impact Assessment RFP disclosure.",
        )

        open_csr_opps = CSROpportunity.objects.filter(
            status="OPEN",
            verification_status__in=["PUBLISHED", "SOURCE_CONFIRMED", "EXTRACTED"],
        )
        self.assertIn(genuine_opp, open_csr_opps)
        self.assertNotIn(tender_opp, open_csr_opps)

    def test_scraped_header_exclusion_from_csr_projects(self):
        """Table headers, report sections, and navigation artifacts must be REJECTED and excluded from CSR projects."""
        artifact_csr = CSRProject.objects.create(
            company=self.hul,
            project_name="Purpose of Engagement",
            category="Corporate Social Responsibility",
            verification_status="REJECTED",
            verification_reason="SCRAPED_NON_PROJECT_ARTIFACT",
        )
        genuine_csr = CSRProject.objects.create(
            company=self.hul,
            project_name="Project Prabhat (Livelihood & Water Conservation)",
            category="Environment & Sustainability",
            verification_status="SOURCE_CONFIRMED",
            source_url="https://www.hul.co.in/csr/prabhat",
            retrieved_at=self.now,
            evidence_text="Community development initiative around manufacturing locations.",
        )

        pub_csr = CSRProject.objects.filter(
            verification_status__in=["PUBLISHED", "SOURCE_CONFIRMED"]
        )
        self.assertIn(genuine_csr, pub_csr)
        self.assertNotIn(artifact_csr, pub_csr)

    def test_all_200_companies_identity_reconciliation_invariants(self):
        """All 200 companies must be audited with mutually exclusive categories summing exactly to 200."""
        audit_file = os.path.join(settings.BASE_DIR, "scratch", "all_200_companies_identity_audit.json")
        self.assertTrue(os.path.exists(audit_file), "Identity audit log file must exist.")
        
        with open(audit_file, "r", encoding="utf-8") as f:
            audit_records = json.load(f)
            
        self.assertEqual(len(audit_records), 200, "Audit log must contain exactly 200 corporate records.")
        
        # Verify all 200 canonical company IDs are present with zero omissions
        audit_ids = {r["company_id"] for r in audit_records}
        self.assertEqual(len(audit_ids), 200, "Audit log must contain 200 unique company IDs.")
        
        # Verify status distribution across mutually exclusive categories
        from collections import Counter
        statuses = Counter(r["status"] for r in audit_records)
        
        self.assertEqual(statuses["AUTHORITATIVE_VERIFIED"], 148, "Must have exactly 148 authoritative verified enterprises.")
        self.assertEqual(statuses["STATUTORY_EXEMPT"], 10, "Must have exactly 10 statutory corporations exempt from MCA CIN.")
        self.assertEqual(statuses["FABRICATED_CIN_REMOVED"], 34, "Must have exactly 34 enterprises with fabricated prototype CINs removed.")
        self.assertEqual(statuses["CIN_UNKNOWN_UNVERIFIED"], 8, "Must have exactly 8 enterprises with CIN unknown/unverified from inception.")
        
        # Verify sum matches canonical registry
        total_sum = sum(statuses.values())
        self.assertEqual(total_sum, 200, "Mutually exclusive identity categories must sum to exactly 200.")
        
        # Verify all companies with STATUTORY_EXEMPT, FABRICATED_CIN_REMOVED, or CIN_UNKNOWN_UNVERIFIED have db_cin as None
        for r in audit_records:
            if r["status"] in ["STATUTORY_EXEMPT", "FABRICATED_CIN_REMOVED", "CIN_UNKNOWN_UNVERIFIED"]:
                self.assertIsNone(r.get("db_cin"), f"Company {r['company_id']} with status {r['status']} must have db_cin as None.")

    def test_job_serializer_missing_fields_never_fabricated(self):
        """Job serializer must return None for missing or placeholder fields, never guessing or fabricating."""
        from modules.website.views.job_api_views import serialize_job_item, _clean_field_val

        # Test placeholder stripper
        self.assertIsNone(_clean_field_val(None))
        self.assertIsNone(_clean_field_val(''))
        self.assertIsNone(_clean_field_val('Unspecified'))
        self.assertIsNone(_clean_field_val('none'))
        self.assertIsNone(_clean_field_val('null'))
        self.assertIsNone(_clean_field_val('---'))
        self.assertIsNone(_clean_field_val('Not specified'))
        self.assertEqual(_clean_field_val('Engineering'), 'Engineering')

        # Test job serializer with completely empty/unspecified optional fields
        sparse_job = Job(
            company=self.hul,
            job_id="JOB_TEST_SPARSE_01",
            job_title="Associate Data Scientist",
            department=None,
            location=None,
            work_mode=None,
            employment_type=None,
            experience=None,
            salary=None,
            posted_date=None,
            application_deadline=None,
            application_url=None,
            responsibilities=None,
            qualifications=None,
            benefits=None,
            status="ACTIVE",
            verification_status="PUBLISHED",
        )
        serialized = serialize_job_item(sparse_job)

        self.assertIsNone(serialized['department'])
        self.assertIsNone(serialized['location'])
        self.assertIsNone(serialized['work_mode'])
        self.assertIsNone(serialized['employment_type'])
        self.assertIsNone(serialized['experience'])
        self.assertIsNone(serialized['salary'])
        self.assertIsNone(serialized['posted_date'])
        self.assertIsNone(serialized['application_deadline'])
        self.assertIsNone(serialized['application_url'], "Must not substitute missing job application URL with general site URL.")
        self.assertIsNone(serialized['responsibilities'])
        self.assertIsNone(serialized['qualifications'])
        self.assertIsNone(serialized['benefits'])

    def test_opportunity_and_csr_serializers_zero_fabrication(self):
        """CSR and opportunity serializers must return None when fields are missing, not inventing fallbacks."""
        from modules.website.views.opportunity_api_views import serialize_opportunity_item, serialize_project_item

        sparse_opp = CSROpportunity(
            company=self.hul,
            title="Community Water Stewardship Grant",
            opportunity_type="Grant",
            category=None,
            submission_deadline=None,
            requirements=None,
            status="OPEN",
            verification_status="SOURCE_CONFIRMED",
        )
        opp_dict = serialize_opportunity_item(sparse_opp)
        self.assertIsNone(opp_dict['category'], "Must not default missing category to 'Uncategorized'.")
        self.assertIsNone(opp_dict['submission_deadline'], "Must not fabricate deadlines.")

        sparse_proj = CSRProject(
            company=self.hul,
            project_name="Water Recharge Initiative",
            category=None,
            description=None,
            state=None,
            budget=None,
            verification_status="SOURCE_CONFIRMED",
        )
        proj_dict = serialize_project_item(sparse_proj)
        self.assertIsNone(proj_dict['category'], "Must not default missing project category to 'Uncategorized'.")
        self.assertIsNone(proj_dict['state'])
        self.assertIsNone(proj_dict['budget'])






