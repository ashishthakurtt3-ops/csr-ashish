"""
Retro-fit the existing jobs with the same rules the crawler now applies at ingest.

    python manage.py normalize_job_data            # dry run
    python manage.py normalize_job_data --apply

For every real (non REQ-*) job it
  * converts the apply URL to the human job page (SmartRecruiters API urls) and rejects generic landing pages,
  * converts posted/closing dates to ISO (YYYY-MM-DD) and employment type / work mode to the fixed vocabulary,
  * derives country/city/state from the source location (NULL when unknown, never "India" by default),
  * re-resolves ownership for shared ATS tenants (config/shared_tenants.json),
  * RESETS the link verification: link_status becomes NULL and the job is hidden until
    `python manage.py verify_job_links` confirms the link live.
"""
from collections import Counter

from django.core.management.base import BaseCommand

from modules.admin_panel.models import Job
from modules.crawler_engine.normalizers import (
    normalize_application_url, normalize_date, normalize_employment_type, normalize_work_mode,
    infer_country, split_location, is_generic_landing_url,
)
from modules.crawler_engine.ownership import resolve_owner, tenant_key, OWNED, load_config


class Command(BaseCommand):
    help = "Normalise stored jobs, re-resolve ownership and reset link verification."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **opts):
        cfg = load_config()
        stats = Counter()
        claimed = set()          # (ats_platform, tenant, external_id) already given to one job
        qs = (Job.objects.exclude(job_id__startswith='REQ').exclude(verification_status='LEGACY_UNVERIFIED')
              .select_related('company').order_by('job_row_id'))
        for j in qs.iterator(chunk_size=500):
            upd = {}
            url = normalize_application_url(j.application_url)
            if not url or is_generic_landing_url(url):
                stats['generic_or_invalid_url'] += 1
                upd.update(status='INACTIVE', verification_status='REJECTED',
                           verification_reason='Apply URL is empty or a generic landing page, not one job posting.')
                url = url if url else j.application_url
            upd['application_url'] = url

            location = j.location
            country = infer_country(location, None)          # stored 'India' default is not evidence
            city, state = split_location(location)
            upd.update(
                country=country, city=city or j.city, state=state or j.state,
                posted_date=normalize_date(j.posted_date), closing_date=normalize_date(j.closing_date),
                application_deadline=normalize_date(j.application_deadline),
                employment_type=normalize_employment_type(j.employment_type),
                work_mode=normalize_work_mode(j.work_mode),
            )

            decision, reason = resolve_owner(
                {'application_url': url, 'location': location, 'country': country,
                 'business_unit': j.business_unit, 'legal_entity': None},
                j.company.nse_symbol, cfg)
            upd['owner_status'] = decision
            tenant = tenant_key(url) if decision == OWNED and j.external_job_id else None
            key = (j.ats_platform, tenant, j.external_job_id)
            if tenant and key in claimed:
                tenant = None
                upd['owner_status'] = 'OWNER_UNRESOLVED'
                decision = 'OWNER_UNRESOLVED'
                reason = 'same requisition already assigned to another company'
            if tenant:
                claimed.add(key)
            upd['ats_tenant'] = tenant
            stats[decision] += 1
            if decision != OWNED:
                upd.update(status='INACTIVE',
                           verification_reason=f'Ownership not confirmed: {decision} ({reason})')

            # link verification must be redone live
            upd.update(link_status=None, link_http_status=None, link_check_reason=None, link_verified_at=None)
            if j.status == 'ACTIVE' and decision == OWNED and 'status' not in upd:
                upd['status'] = 'INACTIVE'          # hidden until verify_job_links confirms it
                stats['awaiting_link_verification'] += 1
            if opts['apply']:
                Job.objects.filter(pk=j.pk).update(**upd)
        for k, v in sorted(stats.items()):
            self.stdout.write(f"{k}: {v}")
        self.stdout.write(self.style.SUCCESS("Applied." if opts['apply'] else
                                             "Dry run only - re-run with --apply, then run verify_job_links."))
