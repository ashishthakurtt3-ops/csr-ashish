"""
Scalable command to crawl all 200 companies (and any additional companies as more are added).

Usage:
    python manage.py crawl_all_companies
    python manage.py crawl_all_companies --workers 4 --verify-links
    python manage.py crawl_all_companies --only-pending
    python manage.py crawl_all_companies --company RELIANCE
    python manage.py crawl_all_companies --import-csv data/new_companies.csv --only-pending
"""
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import close_old_connections, models
from django.db.models import Q
from django.utils import timezone

from modules.admin_panel.models import Company
from modules.admin_panel.verification import public_jobs, public_records
from modules.crawler_engine.crawler import sync_single_company_live


class Command(BaseCommand):
    help = "Ensure all 200+ companies exist in MySQL, crawl their websites for real Jobs and CSR data, and mark Login-Required or Not Available accurately."

    def add_arguments(self, parser):
        parser.add_argument("--workers", type=int, default=4,
                            help="Number of concurrent company crawlers (default: 4).")
        parser.add_argument("--company", help="Crawl a single company by company_id or NSE symbol.")
        parser.add_argument("--only-pending", action="store_true",
                            help="Only crawl companies with crawl_status in PENDING / FAILED.")
        parser.add_argument("--only-failing", action="store_true",
                            help="Prioritize and only crawl companies with FAILED status or < 50%% direct link rate.")
        parser.add_argument("--strategy", type=str,
                            help="Only crawl companies matching a specific extraction_strategy.")
        parser.add_argument("--dry-run", action="store_true",
                            help="Simulate crawling without persisting records.")
        parser.add_argument("--limit", type=int, default=0,
                            help="Optional max number of companies to crawl in this batch (0 = all).")
        parser.add_argument("--import-csv", dest="import_csv",
                            help="Optional path to a CSV of additional companies to import before crawling.")
        parser.add_argument("--verify-links", action="store_true",
                            help="Also run verify_csr_links and verify_job_links after crawling.")

    def handle(self, *args, **opts):
        # 1. Ensure all 200 base companies from master CSV exist in MySQL
        master_csv = Path(settings.BASE_DIR) / "data" / "Top_200_Indian_Companies_Web_Scraping_Master_ENRICHED.csv"
        if master_csv.exists():
            self._import_csv(str(master_csv), only_missing=True)

        # 2. Optionally import additional companies CSV when scaling beyond 200
        if opts.get("import_csv"):
            self._import_csv(opts["import_csv"], only_missing=False)

        # Work queue: ordered by last_live_synced_at (nulls first) with priority for failing
        qs = Company.objects.all().order_by(models.F("last_live_synced_at").asc(nulls_first=True))

        if opts.get("company"):
            c_arg = opts["company"].strip()
            qs = qs.filter(Q(company_id__iexact=c_arg) | Q(nse_symbol__iexact=c_arg) | Q(company_name__icontains=c_arg))
        elif opts.get("only_failing"):
            qs = qs.filter(Q(crawl_status="FAILED") | Q(last_strategy_success_rate__lt=50.0) | Q(last_strategy_success_rate__isnull=True))
        elif opts.get("only_pending"):
            qs = qs.filter(crawl_status__in=["PENDING", "FAILED", ""])

        if opts.get("strategy"):
            qs = qs.filter(extraction_strategy=opts["strategy"].strip())

        if opts.get("limit") and opts["limit"] > 0:
            qs = qs[:opts["limit"]]

        companies = list(qs)
        total = len(companies)
        self.stdout.write(self.style.NOTICE(
            f"--> Starting scalable crawl for {total} companies (workers={opts['workers']})..."
        ))

        crawled = failed = login_flagged = total_jobs = total_csr = 0

        def _crawl_one(idx_comp):
            idx, comp = idx_comp
            close_old_connections()
            summary = sync_single_company_live(comp)
            comp.refresh_from_db()

            # Set explicit availability status (PUBLIC / LOGIN_REQUIRED / NOT_PUBLISHED) so Admin & Public pages
            # always show either real extracted data, "Available only after login", or "Not available on the company website".
            changed_fields = []
            v_jobs = public_jobs(comp.jobs.all()).count()
            v_csr = public_records(comp.csr_projects.all()).count()
            v_con = public_records(comp.contacts.all()).count()

            if v_jobs > 0:
                new_j_acc = "PUBLIC"
            elif comp.jobs_access == "LOGIN_REQUIRED":
                new_j_acc = "LOGIN_REQUIRED"
            else:
                new_j_acc = "NOT_PUBLISHED"

            if comp.jobs_access != new_j_acc:
                comp.jobs_access = new_j_acc
                changed_fields.append("jobs_access")

            has_csr_url = bool(comp.csr_portal_url or comp.foundation_url or comp.sustainability_url or comp.esg_url or comp.brsr_url or comp.annual_report_url)
            if v_csr > 0 or has_csr_url:
                new_c_acc = "PUBLIC"
            elif comp.csr_access == "LOGIN_REQUIRED":
                new_c_acc = "LOGIN_REQUIRED"
            else:
                new_c_acc = "NOT_PUBLISHED"

            if comp.csr_access != new_c_acc:
                comp.csr_access = new_c_acc
                changed_fields.append("csr_access")

            if comp.contacts_access != "LOGIN_REQUIRED":
                new_ct_acc = "PUBLIC"
                if comp.contacts_access != new_ct_acc:
                    comp.contacts_access = new_ct_acc
                    changed_fields.append("contacts_access")

            if comp.data_access_note and ("403" in comp.data_access_note or "Restricted" in comp.data_access_note):
                comp.data_access_note = ""
                changed_fields.append("data_access_note")

            if changed_fields:
                comp.data_access_checked_at = timezone.now()
                changed_fields.append("data_access_checked_at")
                comp.save(update_fields=changed_fields)

            is_login = any(
                getattr(comp, f) == "LOGIN_REQUIRED"
                for f in ("jobs_access", "csr_access", "contacts_access")
            )
            close_old_connections()
            return idx, comp, summary, is_login, v_jobs, v_csr

        workers = max(1, int(opts.get("workers") or 1))
        if workers == 1:
            for idx, comp in enumerate(companies, 1):
                _, c_obj, summ, is_login, vj, vc = _crawl_one((idx, comp))
                crawled += 1
                c_status = summ.get("status") if isinstance(summ, dict) else getattr(summ, "status", "SUCCESS")
                if c_status == "FAILED":
                    failed += 1
                if is_login:
                    login_flagged += 1
                total_jobs += vj
                total_csr += vc
                self.stdout.write(
                    f"[{idx}/{total}] {c_obj.company_name}: status={c_status} "
                    f"verified_jobs={vj} verified_csr={vc} "
                    f"(jobs_access={c_obj.jobs_access}, csr_access={c_obj.csr_access})"
                )
        else:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = [pool.submit(_crawl_one, (idx, comp)) for idx, comp in enumerate(companies, 1)]
                for fut in as_completed(futures):
                    try:
                        idx, c_obj, summ, is_login, vj, vc = fut.result()
                        crawled += 1
                        c_status = summ.get("status") if isinstance(summ, dict) else getattr(summ, "status", "SUCCESS")
                        if c_status == "FAILED":
                            failed += 1
                        if is_login:
                            login_flagged += 1
                        total_jobs += vj
                        total_csr += vc
                        self.stdout.write(
                            f"[{idx}/{total}] {c_obj.company_name}: status={c_status} "
                            f"verified_jobs={vj} verified_csr={vc} "
                            f"(jobs_access={c_obj.jobs_access}, csr_access={c_obj.csr_access})"
                        )
                    except Exception as exc:
                        failed += 1
                        self.stderr.write(f"Worker exception: {exc}")

        self.stdout.write(self.style.SUCCESS(
            f"[OK] Crawl finished: {crawled}/{total} companies processed | "
            f"Verified Jobs: {total_jobs} | Verified CSR Projects: {total_csr} | "
            f"Login-Required Companies: {login_flagged} | Failed: {failed}"
        ))

        if opts.get("verify_links"):
            self.stdout.write("--> Running live CSR and Job link verification...")
            call_command("verify_csr_links")
            call_command("verify_job_links")

    def _import_csv(self, csv_path_str: str, only_missing: bool = False):
        p = Path(csv_path_str)
        if not p.exists():
            self.stderr.write(f"CSV file not found: {p}")
            return
        added = updated = 0
        with open(p, "r", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                cid = (row.get("company_id") or "").strip()
                cname = (row.get("company_name") or "").strip()
                if not cname:
                    continue
                if not cid:
                    sym = (row.get("nse_symbol") or "").strip().upper()
                    cid = f"COMP_{sym}" if sym else f"COMP_{Company.objects.count() + added + 1:04d}"
                defaults = {
                    "company_name": cname,
                    "legal_name": (row.get("legal_name") or "").strip() or None,
                    "nse_symbol": (row.get("nse_symbol") or "").strip() or None,
                    "bse_scrip_code": (row.get("bse_scrip_code") or "").strip() or None,
                    "isin": (row.get("isin") or "").strip() or None,
                    "cin": (row.get("cin") or "").strip() or None,
                    "sector": (row.get("sector") or "").strip() or None,
                    "headquarters": (row.get("headquarters") or "").strip() or None,
                    "website_url": (row.get("website_url") or "").strip() or None,
                    "careers_url": (row.get("careers_url") or "").strip() or None,
                    "csr_portal_url": (row.get("csr_portal_url") or "").strip() or None,
                    "sustainability_url": (row.get("sustainability_url") or "").strip() or None,
                    "esg_url": (row.get("esg_url") or "").strip() or None,
                    "foundation_url": (row.get("foundation_url") or "").strip() or None,
                }
                if only_missing:
                    _, created = Company.objects.get_or_create(company_id=cid, defaults=defaults)
                    if created:
                        added += 1
                else:
                    _, created = Company.objects.update_or_create(company_id=cid, defaults=defaults)
                    if created:
                        added += 1
                    else:
                        updated += 1
        if added or updated:
            self.stdout.write(self.style.SUCCESS(
                f"[CSV Sync] Added {added} companies, updated {updated} companies (Total in DB: {Company.objects.count()})."
            ))
