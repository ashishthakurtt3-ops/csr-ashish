"""
Seed the Django/MySQL database from the project's versioned JSON snapshot.

Usage:
    python manage.py seed_database

Optional:
    python manage.py seed_database --fresh
    python manage.py seed_database --fixture data/db_backup_20261001_134324.json
    python manage.py seed_database --admin-password "YourNewPassword"

The command uses the newest data/db_backup_*.json file by default.  It is
safe to re-run against an existing database because Django's fixture loader
upserts objects by primary key.  The --fresh option is deliberately explicit
and performs a full Django flush before loading the fixture.
"""

from __future__ import annotations

import os
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from modules.admin_panel.models import (
    AuditTrail,
    Company,
    Contact,
    CSROpportunity,
    CSRProject,
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
)


MODEL_TYPES = (
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
    Prospect,
    PromoCode,
    Subscription,
    SubscriptionEvent,
    Invoice,
    UsageCounter,
    ServiceCatalog,
)


class Command(BaseCommand):
    help = "Seed the Django database from the newest bundled JSON database snapshot."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Flush all database data before loading the seed fixture.",
        )
        parser.add_argument(
            "--fixture",
            type=str,
            default=None,
            help="Path to a specific JSON fixture. Defaults to the newest data/db_backup_*.json.",
        )
        parser.add_argument(
            "--admin-password",
            type=str,
            default=None,
            help="Reset the admin user's password after seeding.",
        )

    def handle(self, *args, **options):
        base_dir = Path(self._base_dir())
        fixture_path = self._resolve_fixture(base_dir, options.get("fixture"))

        self.stdout.write("--> CSR & Job Intelligence database seeder")
        self.stdout.write(f"Using fixture: {fixture_path}")

        if options.get("fresh"):
            self.stdout.write(self.style.WARNING(
                "--fresh specified: flushing all Django database data first."
            ))
            call_command("flush", interactive=False, verbosity=0)

        before = self._counts()

        try:
            with transaction.atomic():
                # Django's fixture loader restores FK and M2M relationships and
                # preserves primary keys from the snapshot.
                call_command(
                    "loaddata",
                    str(fixture_path),
                    verbosity=0,
                    ignorenonexistent=False,
                )

                admin_password = options.get("admin_password") or os.environ.get(
                    "SEED_ADMIN_PASSWORD"
                )
                if admin_password:
                    self._reset_admin_password(admin_password)
        except Exception as exc:
            raise CommandError(f"Seed failed: {exc}") from exc

        after = self._counts()
        self._print_counts(before, after)
        self.stdout.write(self.style.SUCCESS("[OK] Database seed completed successfully."))

    @staticmethod
    def _base_dir() -> str:
        # config.settings.BASE_DIR is the canonical Django project root.
        from django.conf import settings

        return str(settings.BASE_DIR)

    def _resolve_fixture(self, base_dir: Path, requested: str | None) -> Path:
        if requested:
            fixture = Path(requested)
            if not fixture.is_absolute():
                fixture = base_dir / fixture
            fixture = fixture.resolve()
            if not fixture.is_file():
                raise CommandError(f"Fixture not found: {fixture}")
            if fixture.stat().st_size == 0:
                raise CommandError(f"Fixture is empty: {fixture}")
            return fixture

        candidates = [
            p for p in (base_dir / "data").glob("db_backup_*.json")
            if p.is_file() and p.stat().st_size > 0
        ]
        if not candidates:
            raise CommandError(
                "No data/db_backup_*.json fixture found. "
                "Provide --fixture with a valid Django JSON fixture."
            )

        # Newest filesystem timestamp wins. This also works when fixture names
        # were copied between machines and their timestamps changed.
        return max(candidates, key=lambda p: p.stat().st_mtime).resolve()

    def _reset_admin_password(self, password: str) -> None:
        if len(password) < 6:
            raise CommandError("Admin password must be at least 6 characters long.")

        try:
            admin = User.objects.get(username="admin")
        except User.DoesNotExist as exc:
            raise CommandError(
                "Cannot reset admin password because the seeded 'admin' user does not exist."
            ) from exc

        admin.set_password(password)
        admin.save(update_fields=["password"])
        self.stdout.write("Admin password reset for user 'admin'.")

    def _counts(self) -> dict[str, int]:
        return {model.__name__: model.objects.count() for model in MODEL_TYPES}

    def _print_counts(self, before: dict[str, int], after: dict[str, int]) -> None:
        self.stdout.write("\nSeeded record counts:")
        for model in MODEL_TYPES:
            name = model.__name__
            delta = after[name] - before[name]
            self.stdout.write(f"  {name:20} {after[name]:>6}  (delta {delta:+})")
