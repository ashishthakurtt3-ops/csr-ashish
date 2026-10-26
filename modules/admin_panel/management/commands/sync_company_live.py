import sys
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections
from modules.crawler_engine.live_syncer import sync_company_live


class Command(BaseCommand):
    help = "Strict 1:1 Live Sync & On-Demand Delta Synchronization for a Single Company"

    def add_arguments(self, parser):
        parser.add_argument(
            '--company-id',
            type=str,
            dest='company_id',
            help='Company ID (e.g. COMP_TOP200_011 or COMP_0)',
        )
        parser.add_argument(
            '--domain',
            type=str,
            dest='domain',
            help='Company domain (e.g. mahindra.com or paytm.com)',
        )

    def handle(self, *args, **options):
        company_id = options.get('company_id')
        domain = options.get('domain')

        if not company_id and not domain:
            raise CommandError("You must specify either --company-id <id> or --domain <domain>.")

        close_old_connections()
        self.stdout.write(self.style.NOTICE(f"=== Initiating 1:1 Live Sync (ID: {company_id}, Domain: {domain}) ==="))

        try:
            diff = sync_company_live(company_id=company_id, domain=domain)
        finally:
            close_old_connections()

        if diff.get('status') == 'FAILED':
            self.stdout.write(self.style.ERROR(f"\n[LIVE SYNC FAILED] {diff.get('error')}"))
            sys.exit(1)

        self.stdout.write(self.style.SUCCESS(f"\n[COMPANY] {diff['company_name']} ({diff['company_id']})"))
        self.stdout.write(self.style.NOTICE(f"[TIMESTAMP] Live Sync Started: {diff.get('sync_start_time')}"))

        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Live URL Probing ---"))
        for probe in diff.get('urls_probed', []):
            url = probe.get('url')
            final_url = probe.get('final_url')
            status = probe.get('status')
            method = probe.get('method', 'HTTP')
            self.stdout.write(f"[LIVE FETCH] {method} {url} -> HTTP {status} (Final: {final_url})")

        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Live Delta Results (MySQL 1:1 Match) ---"))
        j_add = diff.get('jobs_added', 0)
        j_upd = diff.get('jobs_updated', 0)
        j_rem = diff.get('jobs_removed', 0)
        c_add = diff.get('csr_added', 0)
        c_upd = diff.get('csr_updated', 0)
        c_rem = diff.get('csr_removed', 0)

        self.stdout.write(
            self.style.SUCCESS(
                f"[JOBS DIFF] +{j_add} New Added | ~{j_upd} Updated | -{j_rem} Removed (No longer on website)"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"[CSR DIFF]  +{c_add} New Added | ~{c_upd} Updated | -{c_rem} Removed (No longer on website)"
            )
        )
        self.stdout.write(
            f"[TOTAL ACTIVE IN DB] Jobs: {diff.get('active_jobs_count', 0)} | CSR Projects: {diff.get('active_csr_count', 0)}"
        )

        from modules.admin_panel.models import Job, CSRProject, Company
        comp_obj = Company.objects.filter(company_id=diff['company_id']).first()
        if comp_obj:
            active_jobs = Job.objects.filter(company=comp_obj, status='ACTIVE')[:3]
            if active_jobs.exists():
                self.stdout.write(self.style.MIGRATE_HEADING("\n--- Sample Live Extracted Jobs (Chrome Yellow Highlight URLs) ---"))
                for aj in active_jobs:
                    self.stdout.write(f"  * Job: {aj.job_title} ({aj.location or 'India'})")
                    self.stdout.write(f"    URL: {aj.application_url}")

            active_csr = CSRProject.objects.filter(company=comp_obj)[:3]
            if active_csr.exists():
                self.stdout.write(self.style.MIGRATE_HEADING("\n--- Sample Live Extracted CSR Projects (Chrome Yellow Highlight URLs) ---"))
                for ac in active_csr:
                    self.stdout.write(f"  * CSR: {ac.project_name} [{ac.category or 'General'}] (Budget: {ac.budget or 'N/A'})")
                    self.stdout.write(f"    URL: {ac.source_url}")

        old_h = diff.get('old_hash') or 'None (initial sync)'
        new_h = diff.get('new_hash') or 'N/A'
        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Cryptographic Content Hash ---"))
        self.stdout.write(f"[HASH] Old Hash: {old_h}")
        self.stdout.write(f"[HASH] New Hash: {new_h}")
        if old_h != new_h:
            self.stdout.write(self.style.WARNING("       Payload changed on live website -> Hash updated in MySQL."))
        else:
            self.stdout.write(self.style.SUCCESS("       Payload identical to previous verification."))

        self.stdout.write(self.style.SUCCESS("\n[SYNC COMPLETE] 1:1 Live Data verified and persisted to MySQL.\n"))
