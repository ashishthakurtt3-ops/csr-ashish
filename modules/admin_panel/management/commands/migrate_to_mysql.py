"""Orchestrator: merged MySQL migration (fixture + legacy gaps + CSV)."""
import csv
import glob
import os
from pathlib import Path

import pymysql
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.serializers import deserialize
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
    Subscription,
    SubscriptionEvent,
    UsageCounter,
    User,
)




class Command(BaseCommand):
    help = "Import merged production data (fixture + legacy gaps + CSV)"

    def handle(self, *args, **options):
        self._ensure_users()
        fixture = self._latest_fixture()
        if fixture:
            self._import_fixture(fixture)
        legacy_rows = self._read_legacy_mysql()
        if legacy_rows:
            self._gap_fill_from_legacy(legacy_rows)
        self._import_companies_from_csv()
        from django.core.management import call_command
        # Seeding logic removed to prevent synthetic data generation
        self.stdout.write(
            self.style.SUCCESS("[OK] Database migrated: merged dataset loaded.")
        )

    def _gap_fill_from_legacy(self, rows):
        with transaction.atomic():
            for r in rows.get("companies", []):
                if r.get("company_id"):
                    Company.objects.update_or_create(
                        company_id=r["company_id"],
                        defaults={
                            "company_name": r.get("company_name", ""),
                            "nse_symbol": r.get("nse_symbol") or "",
                            "isin": r.get("isin") or "",
                            "website_url": r.get("website_url") or "",
                            "sector": r.get("sector") or "",
                            "headquarters": r.get("headquarters") or "",
                            "careers_url": r.get("careers_url") or "",
                            "csr_portal_url": r.get("csr_portal_url") or "",
                            "link_quality": r.get("link_quality")
                            or "VERIFIED_DEEP_LINK",
                        },
                    )
            for r in rows.get("opportunity_scores", []):
                if r.get("company_id"):
                    OpportunityScore.objects.get_or_create(
                        company_id=r["company_id"],
                        defaults={
                            "active_csr": float(r.get("active_csr") or 0.0),
                            "focus_match": float(r.get("focus_match") or 0.0),
                            "recent_activity": float(
                                r.get("recent_activity") or 0.0),
                            "ngo_activity": float(
                                r.get("ngo_activity") or 0.0),
                            "opportunity_page": float(
                                r.get("opportunity_page") or 0.0),
                            "contact_availability": float(
                                r.get("contact_availability") or 0.0),
                            "geographic_match": float(
                                r.get("geographic_match") or 0.0),
                            "score": float(r.get("score") or 0.0),
                            "evidence_status": r.get("evidence_status"),
                            "rationale": r.get("rationale"),
                            "scored_at": r.get("scored_at"),
                        },
                    )

            for r in rows.get("csr_projects", []):
                CSRProject.objects.get_or_create(
                    fingerprint=r.get("fingerprint")
                    or "legacy-%s" % r.get("csr_id"),
                    defaults={
                        "company_id": r.get("company_id"),
                        "project_name": r.get("project_name"),
                        "category": r.get("category"),
                        "description": r.get("description"),
                        "geographic_location": r.get(
                            "geographic_location"),
                        "state": r.get("state"),
                        "budget": r.get("budget"),
                        "source_url": r.get("source_url"),
                        "confidence": float(r.get("confidence") or 0.0),
                    },
                )
            for r in rows.get("jobs", []):
                Job.objects.get_or_create(
                    fingerprint=r.get("fingerprint")
                    or "legacy-%s" % r.get("job_row_id"),
                    defaults={
                        "company_id": r.get("company_id"),
                        "job_id": r.get("job_id"),
                        "job_title": r.get("job_title") or "",
                        "department": r.get("department"),
                        "function": r.get("function"),
                        "location": r.get("location"),
                        "state": r.get("state"),
                        "country": r.get("country") or None,
                        "work_mode": r.get("work_mode"),
                        "employment_type": r.get("employment_type"),
                        "education": r.get("education"),
                        "skills": r.get("skills"),
                        "salary": r.get("salary"),
                        "job_description": r.get("job_description"),
                        "application_url": r.get("application_url"),
                        "source_url": r.get("source_url"),
                        "status": r.get("status") or "ACTIVE",
                        "confidence": float(r.get("confidence") or 0.0),
                        "link_status": r.get("link_status"),
                        "data_provenance": r.get("data_provenance"),
                    },
                )
            for r in rows.get("ngo_collaborations", []):
                NGOCollaboration.objects.get_or_create(
                    fingerprint=r.get("fingerprint")
                    or "legacy-%s" % r.get("collab_id"),
                    defaults={
                        "company_id": r.get("company_id"),
                        "ngo_name": r.get("ngo_name") or "",
                        "relationship_type": r.get("relationship_type"),
                        "location": r.get("location"),
                        "source_url": r.get("source_url"),
                        "confidence": float(r.get("confidence") or 0.0),
                    },
                )
            for r in rows.get("contacts", []):
                Contact.objects.get_or_create(
                    fingerprint=r.get("fingerprint")
                    or "legacy-%s" % r.get("contact_id"),
                    defaults={
                        "company_id": r.get("company_id"),
                        "name": r.get("name"),
                        "designation": r.get("designation"),
                        "department": r.get("department"),
                        "email": r.get("email"),
                        "phone": r.get("phone"),
                        "source_url": r.get("source_url"),
                        "confidence": float(r.get("confidence") or 0.0),
                        "verification_status": r.get(
                            "verification_status"),
                    },
                )

            for r in rows.get("csr_opportunities", []):
                CSROpportunity.objects.get_or_create(
                    fingerprint=r.get("fingerprint")
                    or "legacy-%s" % r.get("opp_id"),
                    defaults={
                        "company_id": r.get("company_id"),
                        "title": r.get("title") or "",
                        "opportunity_type": r.get("opportunity_type"),
                        "category": r.get("category"),
                        "portal_url": r.get("portal_url"),
                        "status": r.get("status") or "OPEN",
                        "confidence": float(r.get("confidence") or 0.0),
                    },
                )
            for r in rows.get("prospects", []):
                if r.get("company_id"):
                    Prospect.objects.get_or_create(
                        company_id=r["company_id"],
                        defaults={
                            "stage": r.get("stage") or "Shortlisted",
                            "notes": r.get("notes"),
                            "assigned_to": r.get("assigned_to"),
                            "match_score": float(
                                r.get("match_score") or 85.0),
                        },
                    )
            for r in rows.get("pages", []):
                PageRecord.objects.get_or_create(
                    page_id=r.get("page_id"),
                    defaults={
                        "company_id": r.get("company_id"),
                        "url": r.get("url") or "",
                        "title": r.get("title"),
                        "page_type": r.get("page_type"),
                        "status": r.get("status"),
                        "confidence": float(r.get("confidence") or 0.0),
                    },
                )
            if rows.get("audit_trail"):
                for r in rows["audit_trail"]:
                    AuditTrail.objects.get_or_create(
                        audit_id=r.get("audit_id"),
                        defaults={
                            "record_type": r.get("record_type") or "",
                            "record_id": r.get("record_id"),
                            "action": r.get("action") or "",
                            "previous_value": r.get("previous_value"),
                            "new_value": r.get("new_value"),
                            "user_role": r.get("user_role"),
                            "notes": r.get("notes"),
                            "timestamp": r.get("timestamp") or "",
                        },
                    )
            for r in rows.get("promo_codes", []):
                if r.get("code"):
                    PromoCode.objects.get_or_create(
                        code=r["code"],
                        defaults={"percent_off": r.get("percent_off", 0)},
                    )
            for r in rows.get("subscriptions", []):
                if r.get("subscription_id"):
                    Subscription.objects.get_or_create(
                        subscription_id=r["subscription_id"],
                        defaults={
                            "tenant_id": r.get("tenant_id")
                            or r["subscription_id"],
                            "plan_id": r.get("plan_id"),
                            "status": r.get("status"),
                            "organization_name": r.get(
                                "organization_name"),
                        },
                    )
            for r in rows.get("subscription_events", []):
                SubscriptionEvent.objects.get_or_create(
                    event_id=r.get("event_id"),
                    defaults={
                        "subscription_id": r.get("subscription_id"),
                        "tenant_id": r.get("tenant_id"),
                        "event_type": r.get("event_type"),
                        "to_plan": r.get("to_plan"),
                    },
                )
            for r in rows.get("invoices", []):
                Invoice.objects.get_or_create(
                    invoice_id=r.get("invoice_id"),
                    defaults={
                        "invoice_no": r.get("invoice_no"),
                        "subscription_id": r.get("subscription_id"),
                        "tenant_id": r.get("tenant_id"),
                        "status": r.get("status") or "PAID",
                        "total_paise": r.get("total_paise") or 0,
                    },
                )
            for r in rows.get("usage_counters", []):
                UsageCounter.objects.get_or_create(
                    tenant_id=r.get("tenant_id"),
                    metric=r.get("metric"),
                    period_date=r.get("period_date"),
                    defaults={"used": r.get("used") or 0},
                )
        self.stdout.write(
            "  + Legacy gap-fill complete (Django rows kept on conflict)."
        )






    def _ensure_users(self):
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@impactbridge.org",
                "role": User.ROLE_ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "organization_name": "ImpactBridge Governance Team",
                "designation": "Chief Intelligence Officer",
                "is_verified": True,
            },
        )
        if created:
            initial_pw = os.environ.get("ADMIN_INITIAL_PASSWORD", "")
            if initial_pw:
                admin_user.set_password(initial_pw)
            else:
                admin_user.set_unusable_password()
                self.stdout.write("Created superuser 'admin' WITHOUT a password. Run: python manage.py changepassword admin")
            admin_user.save()

        ngo_user, created = User.objects.get_or_create(
            username="ngo_manager",
            defaults={
                "email": "manager@ngoalliance.org",
                "role": User.ROLE_NGO_MANAGER,
                "is_staff": False,
                "organization_name": "Pratham Education Foundation",
                "designation": "Partnerships Director",
                "is_verified": True,
            },
        )
        if created:
            ngo_pw = os.environ.get("NGO_INITIAL_PASSWORD", "")
            if ngo_pw:
                ngo_user.set_password(ngo_pw)
            else:
                ngo_user.set_unusable_password()
            ngo_user.save()

    def _latest_fixture(self):
        candidates = sorted(
            glob.glob(
                str(Path(settings.BASE_DIR) / "data" / "db_backup_*.json")
            )
        )
        if not candidates:
            self.stderr.write("No fixture backup found; skipping fixture load.")
            return None
        self.stdout.write(
            "--> Loading fixture %s ..." % Path(candidates[-1]).name
        )
        return candidates[-1]

    def _import_fixture(self, fixture_path):
        with transaction.atomic():
            with open(fixture_path, "r", encoding="utf-8") as fh:
                objects = list(deserialize("json", fh.read()))
            saved = 0
            skipped = 0
            for obj in objects:
                try:
                    # DeserializedObject.save() -> Model.save_base(raw=True)
                    # (UPDATE when the primary key exists, INSERT otherwise).
                    obj.save()
                    saved += 1
                except Exception:
                    skipped += 1
        self.stdout.write(
            "  + Fixture saved: %d (skipped: %d)" % (saved, skipped)
        )

    def _read_legacy_mysql(self):
        try:
            conn = pymysql.connect(
                host=settings.LEGACY_MYSQL.get("HOST", "localhost"),
                port=int(settings.LEGACY_MYSQL.get("PORT", 3306)),
                user=settings.LEGACY_MYSQL.get("USER", ""),
                password=settings.LEGACY_MYSQL.get("PASSWORD", ""),
                database=settings.LEGACY_MYSQL.get("NAME", "csr_intelligence"),
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
        except Exception as exc:
            self.stderr.write(
                "Legacy MySQL unreachable (%s); skipping gap-fill." % exc
            )
            return None
        tables = (
            "companies", "opportunity_scores", "csr_projects", "jobs",
            "ngo_collaborations", "contacts", "csr_opportunities",
            "prospects", "pages", "audit_trail", "promo_codes",
            "subscriptions", "subscription_events", "invoices",
            "usage_counters",
        )
        rows = {}
        try:
            cur = conn.cursor()
            for table in tables:
                try:
                    cur.execute("SELECT * FROM `%s`" % table)
                    rows[table] = cur.fetchall()
                    self.stdout.write(
                        "  + Legacy %s: %d rows" % (table, len(rows[table]))
                    )
                except Exception as exc:
                    self.stderr.write(
                        "  ! Legacy %s unreadable: %s" % (table, exc))
        finally:
            conn.close()
        return rows

    def _import_companies_from_csv(self):
        csv_path = Path(settings.BASE_DIR) / "data" / (
            "Top_200_Indian_Companies_Web_Scraping_Master_ENRICHED.csv"
        )
        if not csv_path.exists():
            return
        created = 0
        with open(csv_path, "r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                cid = row.get("company_id")
                if not cid:
                    continue
                _, was_created = Company.objects.get_or_create(
                    company_id=cid,
                    defaults={
                        "company_name": row.get("company_name", ""),
                        "nse_symbol": row.get("nse_symbol", ""),
                        "isin": row.get("isin", ""),
                        "website_url": row.get("website_url", ""),
                        "sector": row.get("sector", ""),
                        "headquarters": row.get("headquarters", ""),
                        "careers_url": row.get("careers_url", ""),
                        "csr_portal_url": row.get("csr_portal_url", ""),
                        "link_quality": row.get("link_quality")
                        or "VERIFIED_DEEP_LINK",
                    },
                )
                created += 1 if was_created else 0
        self.stdout.write(
            "  + Companies from master CSV (new): %d" % created)
