from django.core.management.base import BaseCommand
from scripts.apply_project_fixes import (
    delete_legacy_files,
    patch_data_exchange,
    patch_job_views,
    patch_extracted_status_in_views,
)


class Command(BaseCommand):
    help = "Remove legacy seed/backup files and enforce export-only data_exchange, close-only job edit, and unified verified status filters."

    def handle(self, *args, **options):
        delete_legacy_files()
        patch_data_exchange()
        patch_job_views()
        patch_extracted_status_in_views()
        self.stdout.write(self.style.SUCCESS("[OK] Project-wide strict data integrity rules enforced."))
