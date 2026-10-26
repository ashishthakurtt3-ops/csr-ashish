"""
Live-verify CSR portal URLs, CSR project source links, and CSR opportunity links.

    python manage.py verify_csr_links
    python manage.py verify_csr_links --company RELIANCE --workers 8

1. Checks Company CSR URLs (`csr_portal_url`, `sustainability_url`, `esg_url`, `foundation_url`,
   `annual_report_url`, `brsr_url`, `website_url`, `careers_url`):
   - Updates redirected URLs when they redirect cleanly within the company's official or foundation domain.
   - Clears broken/invalid links (404 / redirected to unrelated domain) so the UI never sends users to dead links.
   - Flags `csr_access = 'LOGIN_REQUIRED'` or `jobs_access = 'LOGIN_REQUIRED'` when a portal is behind login.
2. Checks `CSRProject.source_url` and `CSROpportunity.portal_url` / `source_url`:
   - Marks `link_status = 'VERIFIED_HTTP_200'` when verified live (HTML webpage or PDF document).
   - Demotes projects/opportunities whose source links are broken (HTTP 404/410) or redirected to unrelated domains.
"""
from concurrent.futures import ThreadPoolExecutor
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from modules.admin_panel.models import Company, CSRProject, CSROpportunity, AuditTrail
from modules.admin_panel.verification import LINK_OK
from modules.crawler_engine.link_verifier import (
    verify_csr_link, UNREACHABLE, BROKEN, REDIRECTED, LOGIN_WALL
)


class Command(BaseCommand):
    help = "Verify company CSR portal URLs, CSR project links, and CSR opportunity links over HTTP."

    def add_arguments(self, parser):
        parser.add_argument('--company', help='NSE symbol or company_id')
        parser.add_argument('--workers', type=int, default=8)

    def handle(self, *args, **opts):
        now = timezone.now()
        now_iso = now.isoformat()

        comp_qs = Company.objects.all().order_by('company_id')
        if opts['company']:
            comp_qs = comp_qs.filter(Q(nse_symbol=opts['company']) | Q(company_id=opts['company']))

        companies = list(comp_qs)
        self.stdout.write(f"Checking official CSR & corporate links for {len(companies)} companies ...")

        url_fields = (
            'website_url', 'careers_url', 'csr_portal_url', 'sustainability_url',
            'esg_url', 'foundation_url', 'annual_report_url', 'brsr_url', 'investor_url', 'contact_page_url'
        )

        comp_ok = comp_cleared = comp_login = 0
        for c in companies:
            changed = []
            exp_domain = c.official_domain or c.website_url
            for field in url_fields:
                val = (getattr(c, field) or '').strip()
                if not val:
                    continue
                res = verify_csr_link(val, expected_domain=exp_domain if field != 'website_url' else None)
                if res.ok:
                    comp_ok += 1
                    if res.final_url and res.final_url != val:
                        setattr(c, field, res.final_url)
                        changed.append(field)
                elif res.status == LOGIN_WALL:
                    comp_login += 1
                    if field in ('careers_url',):
                        c.jobs_access = 'LOGIN_REQUIRED'
                        changed.append('jobs_access')
                    elif field in ('csr_portal_url', 'sustainability_url', 'esg_url', 'foundation_url'):
                        c.csr_access = 'LOGIN_REQUIRED'
                        changed.append('csr_access')
                    elif field == 'contact_page_url':
                        c.contacts_access = 'LOGIN_REQUIRED'
                        changed.append('contacts_access')
                elif res.status in (BROKEN, REDIRECTED):
                    comp_cleared += 1
                    setattr(c, field, None)
                    changed.append(field)
            if changed:
                c.link_verified_at = now_iso
                changed.append('link_verified_at')
                c.save(update_fields=list(set(changed)))

        self.stdout.write(self.style.SUCCESS(
            f"Company URLs: {comp_ok} verified, {comp_login} login-walled, {comp_cleared} broken/invalid cleared."
        ))

        # Verify CSRProject links
        proj_qs = CSRProject.objects.select_related('company').filter(
            verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
        )
        if opts['company']:
            proj_qs = proj_qs.filter(Q(company__nse_symbol=opts['company']) | Q(company_id=opts['company']))

        projects = list(proj_qs)
        self.stdout.write(f"Checking {len(projects)} CSR project source links ...")

        def check_proj(p):
            exp = (p.company.official_domain or p.company.website_url) if p.company else None
            return p, verify_csr_link(p.source_url, expected_domain=exp)

        proj_ok = proj_bad = 0
        with ThreadPoolExecutor(max_workers=max(1, opts['workers'])) as pool:
            for p, res in pool.map(check_proj, projects):
                upd = {'link_status': LINK_OK if res.ok else res.status, 'link_verified_at': now_iso}
                if res.ok:
                    proj_ok += 1
                    if res.final_url and res.final_url != p.source_url:
                        upd['source_url'] = res.final_url
                elif res.status != UNREACHABLE:
                    proj_bad += 1
                    upd['verification_status'] = 'REJECTED'
                    upd['verification_reason'] = f"Source link failed verification: {res.status} ({res.reason})"[:500]
                CSRProject.objects.filter(pk=p.pk).update(**upd)

        self.stdout.write(self.style.SUCCESS(f"CSR Projects: {proj_ok} verified, {proj_bad} demoted (broken link)."))

        # Verify CSROpportunity links
        opp_qs = CSROpportunity.objects.select_related('company').filter(
            verification_status__in=['PUBLISHED', 'SOURCE_CONFIRMED']
        )
        if opts['company']:
            opp_qs = opp_qs.filter(Q(company__nse_symbol=opts['company']) | Q(company_id=opts['company']))

        opps = list(opp_qs)
        self.stdout.write(f"Checking {len(opps)} CSR opportunity links ...")

        def check_opp(o):
            exp = (o.company.official_domain or o.company.website_url) if o.company else None
            return o, verify_csr_link(o.portal_url or o.source_url, expected_domain=exp)

        opp_ok = opp_bad = 0
        with ThreadPoolExecutor(max_workers=max(1, opts['workers'])) as pool:
            for o, res in pool.map(check_opp, opps):
                upd = {'link_status': LINK_OK if res.ok else res.status, 'link_verified_at': now_iso}
                if res.ok:
                    opp_ok += 1
                    if res.final_url and o.portal_url and res.final_url != o.portal_url:
                        upd['portal_url'] = res.final_url
                elif res.status != UNREACHABLE:
                    opp_bad += 1
                    upd['verification_status'] = 'REJECTED'
                    upd['status'] = 'CLOSED'
                CSROpportunity.objects.filter(pk=o.pk).update(**upd)

        AuditTrail.objects.create(
            record_type='CSR',
            record_id='*',
            action='CSR_LINK_VERIFICATION_RUN',
            new_value=f'comp_ok={comp_ok} proj_ok={proj_ok} proj_bad={proj_bad} opp_ok={opp_ok} opp_bad={opp_bad}',
            user_role='verify_csr_links',
            notes='Bulk live CSR & portal link verification',
            timestamp=now_iso,
        )
        self.stdout.write(self.style.SUCCESS(f"CSR Opportunities: {opp_ok} verified, {opp_bad} demoted."))
