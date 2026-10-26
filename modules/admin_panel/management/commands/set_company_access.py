"""
Record where a company publishes its data (public / only after login / not published).

    python manage.py set_company_access --symbol RELIANCE --jobs LOGIN_REQUIRED --note "Careers needs candidate login"
    python manage.py set_company_access --symbol TCS --csr PUBLIC --contacts NOT_PUBLISHED
    python manage.py set_company_access --detect          # check careers, CSR, and contact URLs for login walls

Values: PUBLIC, LOGIN_REQUIRED, NOT_PUBLISHED, UNKNOWN. The website and admin panel then show
"Available only after login on the company website" / "Not available on the company website".
--detect only flags LOGIN_REQUIRED on strong signals (HTTP 401/403, redirect to a login/SSO page,
password form with no public data links) and writes a note so an admin can confirm it in the admin panel.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from modules.admin_panel.models import Company
from modules.crawler_engine.access_detector import detect_login_wall

CHOICES = ['PUBLIC', 'LOGIN_REQUIRED', 'NOT_PUBLISHED', 'UNKNOWN']


class Command(BaseCommand):
    help = "Set or detect per-company data access mode (Jobs, CSR, Contacts)."

    def add_arguments(self, p):
        p.add_argument('--symbol')
        p.add_argument('--company-id')
        for k in ('jobs', 'csr', 'contacts'):
            p.add_argument(f'--{k}', choices=CHOICES)
        p.add_argument('--note')
        p.add_argument('--detect', action='store_true')

    def handle(self, *a, **o):
        if o['detect']:
            return self._detect()
        if not (o['symbol'] or o['company_id']):
            raise CommandError('Give --symbol or --company-id (or use --detect).')
        c = Company.objects.filter(Q(nse_symbol=o['symbol']) | Q(company_id=o['company_id'])).first()
        if not c:
            raise CommandError('Company not found.')
        for k in ('jobs', 'csr', 'contacts'):
            if o[k]:
                setattr(c, f'{k}_access', o[k])
        if o['note'] is not None:
            c.data_access_note = o['note']
        c.data_access_checked_at = timezone.now()
        c.save(update_fields=['jobs_access', 'csr_access', 'contacts_access', 'data_access_note', 'data_access_checked_at'])
        self.stdout.write(self.style.SUCCESS(f"{c.company_name}: jobs={c.jobs_access} csr={c.csr_access} contacts={c.contacts_access}"))

    def _detect(self):
        import requests
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from django.db import close_old_connections

        flagged = 0
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'}
        companies = list(Company.objects.all())
        self.stdout.write(f"Detecting data access / login walls across {len(companies)} companies with 16 workers...")

        def _check_company(c):
            close_old_connections()
            notes = []
            changed = False
            checks = [
                ('jobs_access', 'Jobs', c.careers_url or c.jobs_page_url or c.ats_url),
                ('csr_access', 'CSR', c.csr_portal_url or c.sustainability_url or c.esg_url or c.foundation_url),
                ('contacts_access', 'Contacts', c.contact_page_url),
            ]
            for field, label, target_url in checks:
                if not target_url or not str(target_url).startswith('http'):
                    continue
                try:
                    r = requests.get(target_url, timeout=7, allow_redirects=True, headers=headers)
                except Exception:
                    continue
                wall, signal = detect_login_wall(r.status_code, r.url, r.text or '')
                if wall:
                    setattr(c, field, 'LOGIN_REQUIRED')
                    notes.append(f"{label}: login required ({signal})")
                    changed = True
                elif r.status_code == 200 and getattr(c, field) == 'UNKNOWN':
                    setattr(c, field, 'PUBLIC')
                    changed = True
            if changed:
                if notes:
                    existing_note = (c.data_access_note or '').strip()
                    new_note = f"Auto-detected {timezone.localdate()}: {'; '.join(notes)}."
                    c.data_access_note = f"{existing_note} | {new_note}".strip(' |') if existing_note else new_note
                c.data_access_checked_at = timezone.now()
                c.save(update_fields=['jobs_access', 'csr_access', 'contacts_access', 'data_access_note', 'data_access_checked_at'])
                return c.company_name, notes
            return None, []

        with ThreadPoolExecutor(max_workers=16) as pool:
            futures = [pool.submit(_check_company, c) for c in companies]
            for fut in as_completed(futures):
                try:
                    cname, notes = fut.result()
                    if notes:
                        flagged += 1
                        self.stdout.write(f"{cname}: {'; '.join(notes)}")
                except Exception as exc:
                    pass

        self.stdout.write(self.style.SUCCESS(f"Flagged {flagged} companies with login-required sections."))
