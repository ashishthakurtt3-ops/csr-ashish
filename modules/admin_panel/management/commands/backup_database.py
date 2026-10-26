"""Export the full dataset to a versioned JSON fixture (data/db_backup_*.json).

Run this before schema changes or data migrations:

    python manage.py backup_database

The newest fixture in ``data/db_backup_*.json`` is what
``migrate_to_mysql`` loads first, so keep the file it produced next to
the project data assets.
"""
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand

from modules.admin_panel.models import (
    AuditTrail,
    Company,
    Contact,
    CSROpportunity,
    CSRProject,
    Document,
    Invoice,
    Job,
    NGOCollaboration,
    OpportunityScore,
    PageRecord,
    PromoCode,
    Prospect,
    ServiceCatalog,
    Subscription,
    SubscriptionEvent,
    UsageCounter,
    User,
    CompanyCrawlSummary,
)

MODELS = (
    User,
    Company,
    OpportunityScore,
    CSRProject,
    CSROpportunity,
    Job,
    NGOCollaboration,
    Contact,
    PageRecord,
    AuditTrail,
    CompanyCrawlSummary,
    Prospect,
    PromoCode,
    Subscription,
    SubscriptionEvent,
    Invoice,
    UsageCounter,
    Document,
    ServiceCatalog,
)


class Command(BaseCommand):
    help = "Export every record to data/db_backup_<timestamp>.json"

    def handle(self, *args, **options):
        out_dir = Path(settings.BASE_DIR) / "data"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / ("db_backup_%s.json" % stamp)

        rows = []
        for model in MODELS:
            rows.extend(list(model.objects.all()))

        with open(out_path, "w", encoding="utf-8") as fh:
            serializers.serialize("json", rows, stream=fh, indent=1)

        self.stdout.write(
            self.style.SUCCESS(
                "[OK] Wrote %s (%d objects)" % (out_path.name, len(rows))
            )
        )
