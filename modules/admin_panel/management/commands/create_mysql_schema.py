"""Create the Django MySQL database schema from scratch (no data).

Drops and recreates the configured MySQL database, runs `migrate`, and
prints the resulting table inventory. Idempotent and safe to rerun —
the legacy business database is never touched by this command.
"""
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Create a fresh Django MySQL database schema (no data)"

    def handle(self, *args, **options):
        engine = connection.settings_dict["ENGINE"]
        if "mysql" not in engine:
            raise RuntimeError(
                "Refusing to run: default database ENGINE is %r, not MySQL. "
                "Set MYSQL_DB in .env first." % engine
            )
        db_name = connection.settings_dict["NAME"]
        self.stdout.write("--> Creating fresh MySQL database '%s'..." % db_name)
        # Create the schema with a server-level connection (the default
        # connection cannot open until the target database exists).
        import pymysql

        conn = pymysql.connect(
            host=connection.settings_dict["HOST"],
            port=int(connection.settings_dict["PORT"]),
            user=connection.settings_dict["USER"],
            password=connection.settings_dict["PASSWORD"],
            charset="utf8mb4",
        )
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DROP DATABASE IF EXISTS `%s`"
                    % db_name.replace("`", "``")
                )
                cur.execute(
                    "CREATE DATABASE `%s` CHARACTER SET utf8mb4 "
                    "COLLATE utf8mb4_unicode_ci" % db_name.replace("`", "``")
                )
            conn.commit()
        finally:
            conn.close()
        connection.close()
        self.stdout.write("--> Running migrate...")
        call_command("migrate", interactive=False, verbosity=1)
        with connection.cursor() as cur:
            cur.execute("SHOW TABLES")
            tables = sorted(r[0] for r in cur.fetchall())
        self.stdout.write(
            self.style.SUCCESS(
                "[OK] Database '%s' ready with %d tables." % (db_name, len(tables))
            )
        )
        for t in tables:
            self.stdout.write("    - %s" % t)
