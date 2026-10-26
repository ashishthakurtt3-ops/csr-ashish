import re
import hashlib
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from modules.admin_panel.models import Job, Company, AuditTrail


def canonicalize_job_url(raw_url: str) -> str:
    """Canonicalize a job URL: force https, lowercase host, strip tracking parameters and fragments."""
    if not raw_url or not str(raw_url).strip():
        return ""
    url = str(raw_url).strip()
    if url.startswith("http://"):
        url = "https://" + url[7:]
    elif not url.startswith("https://"):
        url = "https://" + url
    
    parsed = urllib.parse.urlsplit(url)
    netloc = parsed.netloc.lower()
    if netloc.endswith(':443'):
        netloc = netloc[:-4]
    
    STRIP_PARAMS = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'gclid', 'fbclid', 'ref', 'source', 'src', 'mode', 'iis', 'iisn',
        'tracking', 'trackingcode', 'gh_src', 'lever-source', 'lever-origin',
        'ss', 'start', 'sort_by'
    }
    
    query_dict = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
    filtered_query = []
    for k, v in query_dict:
        k_lower = k.lower()
        if k_lower.startswith('utm_') or k_lower in STRIP_PARAMS:
            continue
        filtered_query.append((k, v))
    filtered_query.sort()
    new_query = urllib.parse.urlencode(filtered_query)
    
    path = parsed.path
    if len(path) > 1 and path.endswith('/'):
        path = path.rstrip('/')
        
    return urllib.parse.urlunsplit(('https', netloc, path, new_query, ''))


def compute_job_fingerprint(company_id: Any, title: str, location: str, external_job_id: Optional[str] = None) -> str:
    norm_c = str(company_id or '').strip()
    norm_t = re.sub(r'[^a-z0-9]', '', str(title or '').lower())
    norm_l = re.sub(r'[^a-z0-9]', '', str(location or '').lower())
    norm_ext = str(external_job_id or '').strip()
    raw = f"{norm_c}|{norm_t}|{norm_l}|{norm_ext}"
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def compute_job_completeness_score(j: Job) -> int:
    score = 0
    if j.job_description and len(j.job_description) > 50:
        score += 20
    if j.responsibilities or j.responsibilities_list:
        score += 15
    if j.qualifications or j.qualifications_education:
        score += 10
    if j.education:
        score += 10
    if j.skills or j.required_skills:
        score += 10
    if j.external_job_id:
        score += 10
    if j.benefits:
        score += 5
    if j.salary:
        score += 5
    if j.experience or j.qualifications_experience:
        score += 5
    if j.work_mode:
        score += 3
    if j.employment_type:
        score += 3
    if j.detail_fetched:
        score += 10
    if j.verification_status in ('VERIFIED', 'PUBLISHED', 'SOURCE_CONFIRMED'):
        score += 10
    return score


class Command(BaseCommand):
    help = "Deduplicate jobs by canonical URL, external requisition ID, and content fingerprint."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', default=False, help="Inspect duplicates without applying changes")
        parser.add_argument('--apply', action='store_true', default=False, help="Apply deduplication and merge records")

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        apply_changes = options.get('apply')
        
        if not dry_run and not apply_changes:
            self.stdout.write(self.style.WARNING("Neither --dry-run nor --apply was specified. Defaulting to --dry-run mode."))
            dry_run = True

        mode_str = "DRY-RUN" if dry_run else "LIVE APPLY"
        self.stdout.write(self.style.SUCCESS(f"Starting Job Deduplication [{mode_str}]..."))

        all_jobs = list(Job.objects.select_related('company').all().order_by('job_row_id'))
        total_initial = len(all_jobs)
        self.stdout.write(f"Total jobs loaded: {total_initial}")

        # Build disjoint-set / union-find over all jobs
        # Every job row is indexed by its job_row_id
        parent: Dict[int, int] = {j.job_row_id: j.job_row_id for j in all_jobs}
        job_by_id: Dict[int, Job] = {j.job_row_id: j for j in all_jobs}

        def find(i: int) -> int:
            path = []
            while parent[i] != i:
                path.append(i)
                i = parent[i]
            for node in path:
                parent[node] = i
            return i

        def union(i: int, j: int):
            root_i = find(i)
            root_j = find(j)
            if root_i != root_j:
                parent[root_i] = root_j

        for j in all_jobs:
            raw_target = j.application_url or j.canonical_url or j.source_url or ""
            canon = canonicalize_job_url(raw_target)
            j._computed_canonical = canon
            canon_hash = hashlib.sha256(canon.encode('utf-8')).hexdigest() if canon else ""
            j._computed_canon_hash = canon_hash
            fp = compute_job_fingerprint(j.company_id, j.job_title, j.location, j.external_job_id)
            j._computed_fingerprint = fp

        # Map keys to job IDs
        canon_to_ids: Dict[str, List[int]] = {}
        ext_to_ids: Dict[Tuple[int, str], List[int]] = {}
        fp_to_ids: Dict[str, List[int]] = {}

        for j in all_jobs:
            jid = j.job_row_id
            if j._computed_canon_hash:
                canon_key = f"{j.company_id}:{j._computed_canon_hash}"
                canon_to_ids.setdefault(canon_key, []).append(jid)
            if j.external_job_id and str(j.external_job_id).strip():
                ext_key = (j.company_id, str(j.external_job_id).strip())
                ext_to_ids.setdefault(ext_key, []).append(jid)
            if j._computed_fingerprint:
                fp_to_ids.setdefault(j._computed_fingerprint, []).append(jid)

        # Union all matching job IDs
        for key, jids in canon_to_ids.items():
            first = jids[0]
            for other in jids[1:]:
                union(first, other)

        for key, jids in ext_to_ids.items():
            first = jids[0]
            for other in jids[1:]:
                union(first, other)

        for key, jids in fp_to_ids.items():
            first = jids[0]
            for other in jids[1:]:
                union(first, other)

        # Group jobs by their root parent
        groups_by_root: Dict[int, List[Job]] = {}
        for j in all_jobs:
            root = find(j.job_row_id)
            groups_by_root.setdefault(root, []).append(j)

        duplicate_groups: List[List[Job]] = [g for g in groups_by_root.values() if len(g) > 1]
        singletons: List[Job] = [g[0] for g in groups_by_root.values() if len(g) == 1]

        self.stdout.write(f"Connected duplicate groups: {len(duplicate_groups)}")
        total_duplicates_to_remove = sum(len(g) - 1 for g in duplicate_groups)
        self.stdout.write(f"Total duplicate rows to consolidate: {total_duplicates_to_remove}")

        # Review report of merges
        fields_to_merge = [
            'external_job_id', 'department', 'team', 'function', 'business_unit',
            'location', 'city', 'state', 'country', 'work_mode', 'employment_type',
            'experience', 'education', 'skills', 'salary', 'salary_min', 'salary_max',
            'salary_currency', 'pay_band', 'job_description', 'role_purpose',
            'responsibilities', 'day_in_the_life', 'requirements', 'qualifications',
            'preferred_qualifications', 'technical_skills', 'behavioural_skills',
            'benefits', 'employer_info', 'structured_details', 'posted_date',
            'application_deadline', 'closing_date', 'description_raw', 'description_html',
            'about_role', 'responsibilities_list', 'qualifications_education',
            'qualifications_experience', 'required_skills', 'preferred_skills',
            'salary_text', 'currency', 'seniority_level'
        ]

        jobs_to_delete = []
        jobs_to_update = []

        for grp in duplicate_groups:
            # Sort group by completeness score descending, then job_row_id ascending
            grp_sorted = sorted(grp, key=lambda j: (compute_job_completeness_score(j), -j.job_row_id), reverse=True)
            primary = grp_sorted[0]
            duplicates = grp_sorted[1:]

            merged_fields_for_group = []
            for dup in duplicates:
                for field in fields_to_merge:
                    primary_val = getattr(primary, field, None)
                    dup_val = getattr(dup, field, None)
                    if (not primary_val) and dup_val:
                        setattr(primary, field, dup_val)
                        merged_fields_for_group.append(field)
                
                # Copy detail_fetched status if duplicate had it
                if not primary.detail_fetched and dup.detail_fetched:
                    primary.detail_fetched = True
                    primary.detail_fetch_status = dup.detail_fetch_status
                    primary.detail_fetched_at = dup.detail_fetched_at

                jobs_to_delete.append(dup)

            primary.canonical_url = primary._computed_canonical
            primary.canonical_url_hash = primary._computed_canon_hash
            primary.fingerprint = primary._computed_fingerprint
            jobs_to_update.append(primary)

            if len(jobs_to_update) <= 10:
                self.stdout.write(
                    f"  Group: Kept Job #{primary.job_row_id} ({primary.job_title} @ {primary.company.company_name}), "
                    f"Consolidating {len(duplicates)} dupes. Merged fields: {set(merged_fields_for_group) or 'None'}"
                )

        # For all jobs not in duplicate groups, also ensure canonical_url and hash are set
        singleton_updates = []
        for s in singletons:
            if s.canonical_url != s._computed_canonical or s.canonical_url_hash != s._computed_canon_hash or s.fingerprint != s._computed_fingerprint:
                s.canonical_url = s._computed_canonical
                s.canonical_url_hash = s._computed_canon_hash
                s.fingerprint = s._computed_fingerprint
                singleton_updates.append(s)

        self.stdout.write(f"Singletons needing canonical URL / hash update: {len(singleton_updates)}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"[DRY RUN COMPLETE] Found {len(duplicate_groups)} duplicate groups. "
                f"Would remove {len(jobs_to_delete)} duplicate jobs and update {len(jobs_to_update) + len(singleton_updates)} primary jobs. "
                f"No database rows were modified."
            ))
            return

        # Execute Live Apply inside atomic transaction
        with transaction.atomic():
            # 1. Soft-delete or remove duplicate jobs FIRST to free unique key constraints
            delete_ids = [d.job_row_id for d in jobs_to_delete]
            # Record audit trail
            AuditTrail.objects.create(
                record_type='JOB_DEDUPLICATION',
                record_id='BULK',
                action='DEDUPE_JOBS',
                previous_value=f"Total jobs: {total_initial}",
                new_value=f"Consolidated and removed {len(delete_ids)} duplicate records across {len(duplicate_groups)} groups.",
                user_role='SYSTEM',
                notes=f"Merged fields into surviving primary records. Deleted duplicate IDs sample: {delete_ids[:50]}",
                timestamp=timezone.now().isoformat()
            )
            Job.objects.filter(job_row_id__in=delete_ids).delete()

            # 2. Update primaries with merged fields
            for j in jobs_to_update:
                j.save()

            # 3. Update singletons with canonical URLs and hashes
            for j in singleton_updates:
                j.save(update_fields=['canonical_url', 'canonical_url_hash', 'fingerprint'])

        remaining_count = Job.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"[DEDUPLICATION APPLIED SUCCESSFULLY]\n"
            f"  - Initial Jobs: {total_initial}\n"
            f"  - Duplicate Records Merged & Removed: {len(jobs_to_delete)}\n"
            f"  - Remaining Unique Jobs: {remaining_count}\n"
            f"  - Consistency Check: {total_initial} - {len(jobs_to_delete)} = {remaining_count} ({total_initial - len(jobs_to_delete) == remaining_count})"
        ))
