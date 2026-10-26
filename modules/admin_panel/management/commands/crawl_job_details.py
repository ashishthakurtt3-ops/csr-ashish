import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Tuple, Dict

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from modules.admin_panel.models import Job, Company
from modules.crawler_engine.parsers.detail_extractor import UniversalJobDetailExtractor


class Command(BaseCommand):
    help = "Crawl and extract full rich job details (responsibilities, education, experience, skills, benefits) from official ATS postings."

    def add_arguments(self, parser):
        parser.add_argument('--company', type=str, default=None, help="Filter by Company ID, NSE symbol, or Company Name")
        parser.add_argument('--job-id', type=int, default=None, help="Crawl a single Job by job_row_id")
        parser.add_argument('--limit', type=int, default=None, help="Maximum number of jobs to crawl")
        parser.add_argument('--only-missing', action='store_true', default=False, help="Process only jobs with MISSING or PARTIAL details")
        parser.add_argument('--backfill-descriptions', action='store_true', default=False, help="Parse structured fields from existing database descriptions")
        parser.add_argument('--force', action='store_true', default=False, help="Force re-scrape even if detail_fetched is already True")
        parser.add_argument('--dry-run', action='store_true', default=False, help="Simulate extraction without writing changes to the database")
        parser.add_argument('--concurrency', type=int, default=4, help="Number of concurrent worker threads (default 4)")

    def handle(self, *args, **options):
        company_filter = options.get('company')
        job_id_filter = options.get('job_id')
        limit = options.get('limit')
        only_missing = options.get('only_missing')
        backfill_desc = options.get('backfill_descriptions')
        force = options.get('force')
        dry_run = options.get('dry_run')
        concurrency = max(1, options.get('concurrency') or 4)

        mode_str = "DRY-RUN" if dry_run else "LIVE CRAWL"
        self.stdout.write(self.style.SUCCESS(f"=== Universal Job Detail Crawler [{mode_str}] ==="))

        qs = Job.objects.select_related('company').filter(status='ACTIVE')

        if job_id_filter:
            qs = qs.filter(job_row_id=job_id_filter)
        elif company_filter:
            c = Company.objects.filter(
                Q(company_id=company_filter) |
                Q(nse_symbol__iexact=company_filter) |
                Q(company_name__icontains=company_filter)
            ).first()
            if not c:
                self.stderr.write(f"Company matching '{company_filter}' not found.")
                return
            qs = qs.filter(company=c)

        if backfill_desc:
            qs = qs.filter(
                Q(job_description__isnull=False) & ~Q(job_description='') &
                (
                    Q(responsibilities_list__isnull=True) | Q(responsibilities_list=[]) |
                    Q(qualifications_education__isnull=True) | Q(qualifications_education=[]) |
                    Q(details_status__in=['MISSING', 'PARTIAL', 'FAILED']) |
                    Q(details_status__isnull=True)
                )
            )
        elif only_missing and not force:
            qs = qs.filter(
                Q(detail_fetched=False) |
                Q(details_status__in=['MISSING', 'PARTIAL', 'FAILED']) |
                Q(responsibilities__isnull=True) | Q(responsibilities='') |
                Q(education__isnull=True) | Q(education='')
            )
        elif not force:
            qs = qs.filter(detail_fetched=False)

        # For live crawling without backfill_desc, must have an HTTP URL to scrape
        if not backfill_desc:
            qs = qs.filter(
                Q(application_url__startswith='http') |
                Q(canonical_url__startswith='http') |
                Q(source_url__startswith='http')
            )

        total_matching = qs.count()
        self.stdout.write(f"Eligible jobs to crawl: {total_matching}")

        if limit:
            qs = qs[:limit]
            self.stdout.write(f"Applying limit of {limit} jobs.")

        jobs_list = list(qs)
        if not jobs_list:
            self.stdout.write(self.style.SUCCESS("No jobs meet the crawl criteria. Nothing to do."))
            return

        success_count = 0
        partial_count = 0
        failed_count = 0

        def process_single_job(job: Job) -> Tuple[int, str, Dict, Optional[Exception]]:
            target_url = job.application_url or job.canonical_url or job.source_url
            try:
                if backfill_desc:
                    extracted = UniversalJobDetailExtractor.extract_from_text(job.job_description, job.job_title)
                    return job.job_row_id, target_url or 'db_text', extracted, None

                # Otherwise, live fetch with fallback to existing description
                extracted = UniversalJobDetailExtractor.extract_from_url(target_url, preloaded_html=None)
                if (not extracted.get('detail_fetched') or extracted.get('details_status') in ('MISSING', 'FAILED')) and job.job_description:
                    fallback_ext = UniversalJobDetailExtractor.extract_from_text(job.job_description, job.job_title)
                    if fallback_ext.get('detail_fetched'):
                        for k, v in fallback_ext.items():
                            if v and not extracted.get(k):
                                extracted[k] = v
                        extracted['detail_fetched'] = True
                        extracted['details_status'] = fallback_ext.get('details_status', 'PARTIAL')
                        extracted['details_missing_fields'] = fallback_ext.get('details_missing_fields', [])
                return job.job_row_id, target_url, extracted, None
            except Exception as e:
                return job.job_row_id, target_url, {}, e

        self.stdout.write(f"Launching pool with {concurrency} threads...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(process_single_job, job): job for job in jobs_list}
            for future in as_completed(futures):
                orig_job = futures[future]
                job_id, url, extracted, err = future.result()

                if err or not extracted:
                    failed_count += 1
                    self.stdout.write(f"  [ERR] Job #{job_id}: {err or 'Empty extraction'}")
                    continue

                fetch_status = extracted.get('detail_fetch_status', 'EXTRACTION_FAILED')
                status = extracted.get('details_status', 'PARTIAL')

                if status == 'COMPLETE':
                    success_count += 1
                elif status == 'PARTIAL':
                    partial_count += 1
                else:
                    failed_count += 1

                safe_title = (orig_job.job_title or '')[:30].encode('ascii', 'replace').decode('ascii')
                if (success_count + partial_count + failed_count) % 25 == 0 or status == 'COMPLETE':
                    self.stdout.write(
                        f"  [{status}] Job #{job_id} ({safe_title}): "
                        f"Resp={bool(extracted.get('responsibilities'))} Edu={bool(extracted.get('education'))} "
                        f"Skills={bool(extracted.get('skills'))} Missing={extracted.get('details_missing_fields', [])}"
                    )

                if not dry_run and extracted.get('detail_fetched'):
                    with transaction.atomic():
                        j = Job.objects.select_for_update().get(job_row_id=job_id)
                        j.detail_fetched = True
                        j.detail_fetch_status = fetch_status
                        j.detail_fetched_at = timezone.now().isoformat()
                        j.details_status = status
                        j.details_missing_fields = extracted.get('details_missing_fields', [])
                        j.details_scraped_at = timezone.now()

                        # Enriched text & lists
                        if extracted.get('job_description'):
                            j.job_description = extracted['job_description']
                        if extracted.get('description_raw'):
                            j.description_raw = extracted['description_raw']
                        if extracted.get('description_html'):
                            j.description_html = extracted['description_html']
                        if extracted.get('about_role') or extracted.get('role_purpose'):
                            j.about_role = extracted.get('about_role') or extracted.get('role_purpose')
                            j.role_purpose = j.about_role

                        if extracted.get('responsibilities'):
                            j.responsibilities = extracted['responsibilities']
                        if extracted.get('responsibilities_list'):
                            j.responsibilities_list = extracted['responsibilities_list']

                        if extracted.get('education'):
                            j.education = extracted['education']
                        if extracted.get('qualifications_education'):
                            j.qualifications_education = extracted['qualifications_education']

                        if extracted.get('experience'):
                            j.experience = str(extracted['experience'])[:50].strip()
                        if extracted.get('qualifications_experience') or extracted.get('experience'):
                            j.qualifications_experience = extracted.get('qualifications_experience') or extracted.get('experience')

                        if extracted.get('skills'):
                            j.skills = extracted['skills']
                        if extracted.get('required_skills'):
                            j.required_skills = extracted['required_skills']
                        if extracted.get('preferred_skills'):
                            j.preferred_skills = extracted['preferred_skills']

                        if extracted.get('benefits'):
                            j.benefits = extracted['benefits']
                        if extracted.get('salary'):
                            j.salary = str(extracted['salary'])[:50].strip()
                            j.salary_text = str(extracted['salary'])[:120].strip()
                        if extracted.get('salary_currency'):
                            j.salary_currency = str(extracted['salary_currency'])[:10].strip()
                            j.currency = str(extracted['salary_currency'])[:10].strip()
                        if extracted.get('salary_min'):
                            j.salary_min = extracted['salary_min']
                        if extracted.get('salary_max'):
                            j.salary_max = extracted['salary_max']

                        if extracted.get('work_mode') and not j.work_mode:
                            j.work_mode = str(extracted['work_mode'])[:50].strip()
                        if extracted.get('employment_type') and not j.employment_type:
                            j.employment_type = str(extracted['employment_type'])[:50].strip()
                        if extracted.get('seniority_level'):
                            j.seniority_level = str(extracted['seniority_level'])[:50].strip()

                        if extracted.get('posted_date') and not j.posted_date:
                            j.posted_date = extracted['posted_date']
                        if extracted.get('closing_date') and not j.closing_date:
                            j.closing_date = extracted['closing_date']
                        if extracted.get('external_job_id') and not j.external_job_id:
                            j.external_job_id = extracted['external_job_id']

                        if extracted.get('structured_details'):
                            j.structured_details = extracted['structured_details']

                        j.save()

        elapsed = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(
            f"\n=== Detail Crawl Complete ({elapsed:.1f}s) ===\n"
            f"  - Total Processed: {len(jobs_list)}\n"
            f"  - Complete: {success_count}\n"
            f"  - Partial: {partial_count}\n"
            f"  - Failed / Source Unavailable: {failed_count}\n"
        ))
