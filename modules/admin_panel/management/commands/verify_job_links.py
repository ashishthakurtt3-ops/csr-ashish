"""
Live-verify apply links and publish only what is proven.

    python manage.py verify_job_links                       # all candidates
    python manage.py verify_job_links --company ACC --limit 50
    python manage.py verify_job_links --stale-hours 24      # re-check links older than 24h

A job becomes visible (status ACTIVE, link_status VERIFIED_HTTP_200) only if its page / ATS API
answers HTTP 200 *and* shows the same requisition id or job title (see crawler_engine/link_verifier.py).
If a job link hits a login wall, the company's `jobs_access` is marked `LOGIN_REQUIRED`.
Network errors never expire or publish anything (the job simply stays hidden until the next run).
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from modules.admin_panel.models import Job, Company, AuditTrail
from modules.admin_panel.verification import LINK_OK
from modules.crawler_engine.link_verifier import verify_job_link, UNREACHABLE, BROKEN, CLOSED, LOGIN_WALL


class Command(BaseCommand):
    help = "Verify job apply links over HTTP and publish only verified jobs."

    def add_arguments(self, parser):
        parser.add_argument('--company', help='NSE symbol or company_id')
        parser.add_argument('--limit', type=int, default=0)
        parser.add_argument('--workers', type=int, default=8)
        parser.add_argument('--stale-hours', type=int, default=0,
                            help='Only jobs never verified or verified more than N hours ago.')

    def handle(self, *args, **o):
        qs = (Job.objects.filter(owner_status='OWNED',
                                 verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED'],
                                 status__in=['ACTIVE', 'INACTIVE'])
              .exclude(job_id__startswith='REQ').order_by('job_row_id'))
        if o['company']:
            qs = qs.filter(Q(company__nse_symbol=o['company']) | Q(company_id=o['company']))
        if o['stale_hours']:
            cutoff = (timezone.now() - timedelta(hours=o['stale_hours'])).isoformat()
            qs = qs.filter(Q(link_verified_at__isnull=True) | Q(link_verified_at__lt=cutoff) | ~Q(link_status=LINK_OK))
        if o['limit']:
            qs = qs[:o['limit']]
        jobs = list(qs.values('pk', 'company_id', 'application_url', 'job_title', 'external_job_id'))
        self.stdout.write(f"Checking {len(jobs)} job links ...")

        def check(row):
            return row['pk'], row['company_id'], verify_job_link(row['application_url'], row['job_title'], row['external_job_id'])

        ok = bad = unreachable = login_walled = 0
        login_company_ids = set()
        now = timezone.now()
        now_iso = now.isoformat()
        with ThreadPoolExecutor(max_workers=max(1, o['workers'])) as pool:
            for pk, cid, res in pool.map(check, jobs):
                upd = dict(link_status=res.status, link_http_status=res.http_status,
                           link_check_reason=res.reason[:1000], link_verified_at=now_iso, last_checked_date=now_iso)
                if res.ok:
                    upd.update(status='ACTIVE', verification_status='PUBLISHED')
                    if res.final_url:
                        upd['application_url'] = res.final_url
                    ok += 1
                else:
                    upd['status'] = 'INACTIVE'
                    if res.status == LOGIN_WALL:
                        login_walled += 1
                        if cid:
                            login_company_ids.add(cid)
                    if res.status in (BROKEN, CLOSED):
                        upd['verification_status'] = 'NOT_FOUND'
                    elif res.status != UNREACHABLE:
                        upd['verification_status'] = 'REJECTED'
                    upd['verification_reason'] = f"Apply link not verified: {res.status} - {res.reason}"[:1000]
                    unreachable += res.status == UNREACHABLE
                    bad += res.status != UNREACHABLE
                Job.objects.filter(pk=pk).update(**upd)

        if login_company_ids:
            Company.objects.filter(company_id__in=login_company_ids).update(
                jobs_access='LOGIN_REQUIRED',
                data_access_checked_at=now,
            )

        AuditTrail.objects.create(record_type='Job', record_id='*', action='LINK_VERIFICATION_RUN',
                                  new_value=f'ok={ok} failed={bad} login_walled={login_walled} unreachable={unreachable}',
                                  user_role='verify_job_links', notes='Bulk live link verification', timestamp=now_iso)
        self.stdout.write(self.style.SUCCESS(f"verified & published: {ok}"))
        self.stdout.write(f"failed (hidden): {bad} (login-required: {login_walled})   unreachable (hidden, retry later): {unreachable}")
