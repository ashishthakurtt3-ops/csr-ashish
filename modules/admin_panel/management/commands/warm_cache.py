import time
from django.contrib.auth.models import AnonymousUser
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from modules.admin_panel.snapshot_service import (
    get_current_stats_snapshot,
    get_current_job_summary_snapshot,
)
from modules.website.views.home_views import index_view, stats_view
from modules.website.views.company_api_views import (
    companies_lookup_api,
    companies_list_api,
)
from modules.website.views.job_api_views import jobs_list_api
from modules.website.views.opportunity_api_views import csr_projects_api
from modules.website.views.matching_api_views import match_ngo_api


def _request(rf, path, data=None):
    """Build a request with the attributes AuthenticationMiddleware normally adds.

    Views called directly (outside the middleware stack) otherwise raise
    ``AttributeError`` on ``request.user`` and ``request.session``.
    """
    req = rf.get(path, data or {})
    req.user = AnonymousUser()
    req.session = {}
    return req


class Command(BaseCommand):
    help = "Primes and warms all core caches (snapshots, lookup, top listings, home page, NGO matches)"

    def handle(self, *args, **options):
        start_time = time.time()
        rf = RequestFactory()
        self.stdout.write("Warming platform caches...")

        # 1. Authoritative snapshots
        t0 = time.time()
        get_current_stats_snapshot()
        get_current_job_summary_snapshot()
        self.stdout.write(f" [OK] Stats & Job snapshots primed ({int((time.time() - t0)*1000)} ms)")

        # 2. Home page context & render
        t0 = time.time()
        req_home = _request(rf, '/')
        index_view(req_home)
        self.stdout.write(f" [OK] Home page view primed ({int((time.time() - t0)*1000)} ms)")

        # 3. Companies lookup
        t0 = time.time()
        req_lookup = _request(rf, '/companies/lookup')
        companies_lookup_api(req_lookup)
        self.stdout.write(f" [OK] /companies/lookup primed ({int((time.time() - t0)*1000)} ms)")

        # 4. First page of /companies
        t0 = time.time()
        req_comp = _request(rf, '/companies', {'page': 1, 'page_size': 12})
        companies_list_api(req_comp)
        self.stdout.write(f" [OK] /companies?page=1&page_size=12 primed ({int((time.time() - t0)*1000)} ms)")

        # 5. First page of /jobs
        t0 = time.time()
        req_jobs = _request(rf, '/jobs', {'page': 1, 'page_size': 12})
        jobs_list_api(req_jobs)
        self.stdout.write(f" [OK] /jobs?page=1&page_size=12 primed ({int((time.time() - t0)*1000)} ms)")

        # 6. First page of /csr/projects
        t0 = time.time()
        req_csr = _request(rf, '/csr/projects', {'page': 1, 'page_size': 12})
        csr_projects_api(req_csr)
        self.stdout.write(f" [OK] /csr/projects?page=1&page_size=12 primed ({int((time.time() - t0)*1000)} ms)")

        # 7. NGO matches base data
        t0 = time.time()
        req_ngo = _request(rf, '/ngo/matches')
        match_ngo_api(req_ngo)
        self.stdout.write(f" [OK] /ngo/matches primed ({int((time.time() - t0)*1000)} ms)")

        total_ms = int((time.time() - start_time) * 1000)
        self.stdout.write(self.style.SUCCESS(f"All core caches successfully warmed in {total_ms} ms!"))
