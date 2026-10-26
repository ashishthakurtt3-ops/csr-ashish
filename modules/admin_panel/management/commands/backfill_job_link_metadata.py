import re
import hashlib
from django.core.management.base import BaseCommand
from django.db import transaction
from modules.admin_panel.models.job import Job
from modules.admin_panel.models.company import Company
from modules.crawler_engine.normalizers import normalize_canonical_url, build_job_fingerprint, clean_text


class Command(BaseCommand):
    help = "Safely backfills canonical_url, external_job_id, link_quality, and fingerprint for existing Job rows."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Inspect changes without saving to database")

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        self.stdout.write("Starting Job link metadata backfill...")

        # Pre-cache company careers URLs
        companies = {c.company_id: c for c in Company.objects.all()}
        careers_map = {}
        for c_id, comp in companies.items():
            if comp.careers_url:
                norm_c = normalize_canonical_url(comp.careers_url)
                if norm_c:
                    careers_map[c_id] = norm_c

        jobs = Job.objects.select_related("company").all()
        total_jobs = jobs.count()
        self.stdout.write(f"Total jobs to inspect: {total_jobs}")

        updated_count = 0
        direct_count = 0
        fallback_count = 0
        unverified_count = 0

        # Pass 1: Count frequency of canonical URLs per company to detect shared listing URLs
        url_counts_per_company = {}
        for j in jobs:
            c_id = j.company.company_id if j.company else "UNKNOWN"
            app_url = j.application_url or j.source_url or ""
            canon = normalize_canonical_url(app_url)
            if canon:
                key = (c_id, canon)
                url_counts_per_company[key] = url_counts_per_company.get(key, 0) + 1

        batch_to_update = []
        seen_fingerprints = set()

        for j in jobs:
            c_id = j.company.company_id if j.company else "UNKNOWN"
            app_url = j.application_url or j.source_url or ""
            canon = normalize_canonical_url(app_url)
            j.canonical_url = canon

            # 1. Extract external_job_id if missing
            ext_id = j.external_job_id
            if not ext_id and isinstance(j.raw_metadata, dict):
                raw_id = (
                    j.raw_metadata.get("id")
                    or j.raw_metadata.get("jobId")
                    or j.raw_metadata.get("req_id")
                    or j.raw_metadata.get("external_job_id")
                    or j.raw_metadata.get("postingId")
                )
                if raw_id:
                    ext_id = str(raw_id).strip()

            if not ext_id and app_url:
                # Regex heuristic for ATS URLs
                # Lever: jobs.lever.co/company/<uuid>
                m_lever = re.search(r"jobs\.lever\.co/[^/]+/([a-f0-9\-]{20,})", app_url, re.I)
                if m_lever:
                    ext_id = m_lever.group(1)
                # Greenhouse: boards.greenhouse.io/company/jobs/<id>
                m_gh = re.search(r"greenhouse\.io/[^/]+/jobs/(\d+)", app_url, re.I)
                if m_gh:
                    ext_id = m_gh.group(1)
                # SmartRecruiters: jobs.smartrecruiters.com/company/<id>
                m_sr = re.search(r"jobs\.smartrecruiters\.com/[^/]+/(\w{10,})", app_url, re.I)
                if m_sr:
                    ext_id = m_sr.group(1)
                # Workday: /job/<slug>/<req_id> or /job/<req_id>
                m_wd = re.search(r"/job/(?:[^/]+/)?([A-Z0-9_\-]+)$", canon or app_url, re.I)
                if m_wd:
                    ext_id = m_wd.group(1)

            if ext_id:
                j.external_job_id = ext_id[:120]

            # 2. Determine link_quality
            shared_count = url_counts_per_company.get((c_id, canon), 0) if canon else 0
            is_company_careers = (canon and careers_map.get(c_id) and canon == careers_map.get(c_id))
            has_text_fragment = "#:~:text=" in app_url
            ats_plat = (j.ats_platform or getattr(j.company, "ats_platform", None) or "").upper()

            if is_company_careers:
                j.link_quality = "LISTING_FALLBACK"
                j.link_check_note = "matches_company_careers_url"
                fallback_count += 1
            elif shared_count > 1 and not (ats_plat in ("LEVER", "GREENHOUSE", "WORKDAY", "SMARTRECRUITERS", "DARWINBOX", "SUCCESSFACTORS") and ext_id):
                j.link_quality = "LISTING_FALLBACK"
                j.link_check_note = f"shared_by_{shared_count}_jobs_fallback"
                fallback_count += 1
            elif (ats_plat in ("LEVER", "GREENHOUSE", "WORKDAY", "SMARTRECRUITERS", "DARWINBOX", "SUCCESSFACTORS") or "lever.co" in (canon or "") or "greenhouse.io" in (canon or "")) and ext_id:
                j.link_quality = "DIRECT"
                j.link_check_note = f"ats_direct_{ats_plat.lower()}" if ats_plat else "ats_direct_url"
                j.application_url = canon
                direct_count += 1
            elif canon and any(k in canon.lower() for k in ("/job/", "/career/", "/careers/", "/openings/", "/position/")) and (ext_id or shared_count == 1):
                j.link_quality = "DIRECT"
                j.link_check_note = "direct_detail_slug"
                j.application_url = canon
                direct_count += 1
            elif has_text_fragment:
                j.link_quality = "LISTING_FALLBACK"
                j.link_check_note = "highlight_text_fragment_fallback"
                fallback_count += 1
            else:
                j.link_quality = "UNVERIFIED"
                j.link_check_note = "initial_backfill_pending_verification"
                unverified_count += 1

            # 3. Update fingerprint if missing
            if not j.fingerprint:
                new_fp = build_job_fingerprint(
                    company_id=c_id,
                    external_job_id=j.external_job_id,
                    canonical_url=j.canonical_url if j.link_quality == "DIRECT" else None,
                    title=j.job_title,
                    location=j.location,
                )
                fp_candidate = new_fp[:64]
                while fp_candidate in seen_fingerprints:
                    fp_candidate = hashlib.sha256(f"{fp_candidate}_{j.job_row_id}".encode('utf-8')).hexdigest()[:64]
                j.fingerprint = fp_candidate
                seen_fingerprints.add(j.fingerprint)

            batch_to_update.append(j)
            updated_count += 1

        if not dry_run:
            with transaction.atomic():
                Job.objects.bulk_update(
                    batch_to_update,
                    ["canonical_url", "external_job_id", "link_quality", "link_check_note", "application_url"],
                    batch_size=500
                )
            self.stdout.write(self.style.SUCCESS(f"Successfully backfilled {updated_count} jobs in MySQL."))
        else:
            self.stdout.write(self.style.WARNING(f"[DRY RUN] Would update {updated_count} jobs."))

        self.stdout.write(f"Summary: Direct: {direct_count}, Fallback: {fallback_count}, Unverified: {unverified_count}")
