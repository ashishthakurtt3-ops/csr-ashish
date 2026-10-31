"""
modules/admin_panel/management/commands/crawl_company_batch.py
==============================================================
Configurable batch crawl command for bounded, evidence-based crawling
with strict read-only execution against production MySQL.

Usage:
    python manage.py crawl_company_batch --batch batch_001_050 --dry-run
    python manage.py crawl_company_batch --company-ids COMP_TOP200_001,COMP_TOP200_002 --dry-run
"""
from django.core.management.base import BaseCommand, CommandError
from modules.crawler_engine.pilot_crawler import PilotCrawler, load_batch_company_ids


class Command(BaseCommand):
    help = "Run high-accuracy evidence-based crawler on a configured batch of companies in read-only mode."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch",
            type=str,
            default="batch_001_050",
            help="Name of batch defined in config/company_batches.json (default: batch_001_050)."
        )
        parser.add_argument(
            "--company-ids",
            type=str,
            help="Optional comma-separated list of explicit company IDs to crawl."
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default="reports/accuracy_pilot_batch_001_050",
            help="Destination directory for pilot artifacts."
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=6,
            help="Maximum pages to inspect per company (default: 6)."
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=12,
            help="HTTP socket timeout in seconds (default: 12)."
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Mandatory delay between requests to the same host in seconds (default: 1.0)."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="Execute strictly in read-only mode without database writes (default: True)."
        )

    def handle(self, *args, **options):
        batch_name = options["batch"]
        company_ids_raw = options.get("company_ids")
        explicit_ids = [c.strip() for c in company_ids_raw.split(",")] if company_ids_raw else None
        output_dir = options["output_dir"]
        max_pages = options["max_pages"]
        timeout = options["timeout"]
        delay = options["delay"]
        dry_run = options["dry_run"]

        self.stdout.write(self.style.SUCCESS(
            f"=== INITIALIZING PILOT CRAWLER BATCH: {batch_name} ==="
        ))

        try:
            target_ids = load_batch_company_ids(batch_name, explicit_ids)
        except Exception as e:
            raise CommandError(f"Error loading company batch: {e}")

        self.stdout.write(f"Target Companies ({len(target_ids)}): {target_ids[0]} ... {target_ids[-1]}")
        self.stdout.write(f"Execution Mode: {'STRICT READ-ONLY (DRY RUN)' if dry_run else 'PERSISTENT'}")
        self.stdout.write(f"Output Artifacts: {output_dir}\n")

        crawler = PilotCrawler(
            batch_name=batch_name,
            explicit_company_ids=explicit_ids,
            output_dir=output_dir,
            max_pages_per_company=max_pages,
            timeout=timeout,
            delay_between_requests=delay,
            dry_run=dry_run
        )

        results = crawler.run_pilot()

        self.stdout.write(self.style.SUCCESS(
            f"\n=== PILOT BATCH {batch_name.upper()} COMPLETE ==="
        ))
        self.stdout.write(f"Companies Processed: {results['total_companies']}")
        self.stdout.write(f"Job Candidates:      {results['jobs_extracted']}")
        self.stdout.write(f"CSR Candidates:      {results['csr_extracted']}")
        self.stdout.write(f"Opportunity Records: {results['opportunities_extracted']}")
        self.stdout.write(f"Rejected / Review:   {results['rejected_or_review']}")
        self.stdout.write(f"Database Modified:   {results['db_modified']} (Expected: False)\n")
