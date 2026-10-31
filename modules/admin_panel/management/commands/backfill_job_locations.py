"""
Backfill structured location attributes (city, state, country, clean location)
for all existing Job records using the comprehensive location normalizer.

Usage:
    python manage.py backfill_job_locations           # Dry run
    python manage.py backfill_job_locations --apply   # Apply changes to DB
"""
from collections import Counter
from django.core.management.base import BaseCommand
from modules.admin_panel.models import Job
from modules.crawler_engine.location_normalizer import normalize_job_location


class Command(BaseCommand):
    help = "Backfill structured location fields (city, state, country) from raw location strings"

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Persist changes to database')
        parser.add_argument('--limit', type=int, default=0, help='Limit number of records to process')

    def handle(self, *args, **options):
        apply_changes = options['apply']
        limit = options['limit']

        qs = Job.objects.all().order_by('job_row_id')
        if limit > 0:
            qs = qs[:limit]

        total = qs.count() if limit == 0 else limit
        self.stdout.write(f"Processing {total} jobs...")

        updated_count = 0
        stats = Counter()

        for job in qs.iterator(chunk_size=500):
            raw_loc = getattr(job, 'raw_location', None) or job.location or ''
            norm = normalize_job_location(raw_loc)

            new_loc = norm['location']
            new_city = norm['city']
            new_state = norm['state']
            new_country = norm['country']
            new_work_mode = norm['work_mode']

            needs_update = False
            upd = {}

            if new_city and job.city != new_city:
                upd['city'] = new_city
                needs_update = True
                stats['updated_city'] += 1

            if new_state and job.state != new_state:
                upd['state'] = new_state
                needs_update = True
                stats['updated_state'] += 1

            if new_country and job.country != new_country:
                upd['country'] = new_country
                needs_update = True
                stats['updated_country'] += 1

            if new_loc and job.location != new_loc:
                upd['location'] = new_loc
                needs_update = True
                stats['cleaned_location'] += 1

            if new_work_mode and not job.work_mode:
                upd['work_mode'] = new_work_mode
                needs_update = True
                stats['inferred_work_mode'] += 1

            if needs_update:
                updated_count += 1
                if apply_changes:
                    Job.objects.filter(pk=job.pk).update(**upd)

        self.stdout.write(f"Done. Examined: {total}, Needs Update: {updated_count}")
        for k, v in stats.items():
            self.stdout.write(f"  {k}: {v}")

        if apply_changes:
            self.stdout.write(self.style.SUCCESS(f"Successfully applied updates to {updated_count} jobs."))
        else:
            self.stdout.write(self.style.WARNING("Dry run only. Use --apply to save changes to the database."))
