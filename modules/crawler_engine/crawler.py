"""
Complete Company Job + CSR Intelligence Crawler
================================================
Rules:
- CORRECT DATA > MORE DATA
- Never fabricate, infer, estimate, or fill missing values
- NULL is the correct value when source data is absent
- A crawl failure must NOT incorrectly expire existing jobs
- Respect robots.txt etiquette via rate limiting
"""
import threading
import time
import hashlib
import urllib.parse
import re
import requests
from bs4 import BeautifulSoup
from django.utils import timezone
from modules.admin_panel.models import (
    Company, Job, AuditTrail, Contact, CSRProject, CSROpportunity,
    PageRecord, CompanyCrawlSummary
)
from .state import CRAWL_TASK_STATE, log_event
from .parsers.generic import GenericHTMLParser
from .parsers.ats import ATSParser, fetch_job_detail
from .parsers.corporate import CorporateHTMLParser
from .parsers.csr_pdf import CSRPdfParser
from .validators.redirect_validator import validate_redirect_chain
from .verification_service import VerificationService

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
}
REQUEST_TIMEOUT = 15


def generate_fingerprint(text):
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def safe_get(url, **kwargs):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True, **kwargs)
        if resp is not None and resp.ok and len(resp.text) < 2500:
            meta_refresh = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\'][^;]+;\s*url=([^"\']+)["\']', resp.text, re.I)
            if not meta_refresh:
                meta_refresh = re.search(r'<meta[^>]+content=["\'][^;]+;\s*url=([^"\']+)["\'][^>]+http-equiv=["\']refresh["\']', resp.text, re.I)
            if meta_refresh:
                redirect_url = meta_refresh.group(1).strip()
                target = urllib.parse.urljoin(resp.url, redirect_url)
                resp = requests.get(target, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True, **kwargs)
        return resp
    except Exception:
        return None



def fetch_with_playwright(url):
    """Playwright fallback for JavaScript-rendered SPAs."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until='networkidle', timeout=15000)
            content = page.content()
            final_url = page.url
            browser.close()
            return content, final_url, 200
    except Exception as e:
        return str(e), url, 500


def log_page_record(company, url, final_url, title, page_type, status_code, content_hash, snippet=""):
    """Creates an authentic PageRecord for telemetry."""
    try:
        now_ts = timezone.now().isoformat()
        PageRecord.objects.create(
            company=company,
            url=url,
            title=title[:255] if title else f"{company.company_name} {page_type}",
            page_type=page_type,
            content_hash=content_hash,
            last_crawled=now_ts,
            last_modified=now_ts,
            status=str(status_code),
            relevant_snippet=snippet[:500] if snippet else "",
            confidence=0.95
        )
    except Exception as e:
        print(f"[PageRecord Error] {e}")


# ============================================================
# COMPANY PAGE DISCOVERY
# ============================================================

# URL keyword patterns to match page types from anchor text / hrefs
PAGE_DISCOVERY_PATTERNS = {
    'careers_url': ['career', 'jobs', 'work with us', 'join us', 'opportunities', 'vacancies'],
    'csr_portal_url': ['csr', 'corporate social responsibility', 'social responsibility'],
    'sustainability_url': ['sustainability', 'sustainable'],
    'esg_url': ['esg', 'environmental social governance'],
    'foundation_url': ['foundation', 'philanthropy', 'trust', 'giving'],
    'investor_url': ['investor relations', 'investors', 'annual report', 'shareholders'],
    'annual_report_url': ['annual report'],
    'brsr_url': ['brsr', 'business responsibility'],
    'contact_page_url': ['contact us', 'contact', 'reach us'],
}


def discover_company_pages(company, html, base_url):
    """
    Scans the company homepage HTML for official sub-page links.
    Stores discovered URLs in the Company object.
    Never guesses — only stores links actually found in the page.
    """
    soup = BeautifulSoup(html, 'lxml')
    updates = {}
    seen = set()

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        text = a.get_text(separator=' ', strip=True).lower()

        if not href or href.startswith('#') or href.startswith('javascript'):
            continue

        full_url = urllib.parse.urljoin(base_url, href)
        if full_url in seen:
            continue
        seen.add(full_url)

        for field, keywords in PAGE_DISCOVERY_PATTERNS.items():
            if field in updates:
                continue  # already found one
            if any(kw in text or kw in href.lower() for kw in keywords):
                updates[field] = full_url

    if updates:
        for field, url in updates.items():
            setattr(company, field, url)
        company.save(update_fields=list(updates.keys()))

    return updates


# ============================================================
# JOB SAVING
# ============================================================

def save_job(company, job_data, content_hash, html_content, parser_used, now_iso, seen_fingerprints, summary):
    """
    Saves a job to the database. Handles both new and updated records.
    Strictly maps source data — no fabrication of missing fields.
    """
    title = job_data.get('title')
    if not title:
        summary.jobs_rejected += 1
        return

    app_url = job_data.get('application_url') or ''
    fingerprint = generate_fingerprint(title + app_url)
    seen_fingerprints.add(fingerprint)

    # Base fields — only from job_data, never invented
    defaults = {
        'job_title': title[:255],
        'department': job_data.get('department'),
        'team': job_data.get('team'),
        'business_unit': job_data.get('business_unit'),
        'job_family': job_data.get('job_family'),
        'location': job_data.get('location'),
        'city': job_data.get('city'),
        'state': job_data.get('state'),
        'work_mode': job_data.get('work_mode'),
        'employment_type': job_data.get('employment_type'),
        'experience': job_data.get('experience'),
        'education': job_data.get('education'),
        'skills': job_data.get('skills'),
        'salary': job_data.get('salary'),
        'salary_min': job_data.get('salary_min'),
        'salary_max': job_data.get('salary_max'),
        'salary_currency': job_data.get('salary_currency'),
        'job_description': job_data.get('job_description') or job_data.get('description'),
        'responsibilities': job_data.get('responsibilities'),
        'requirements': job_data.get('requirements'),
        'qualifications': job_data.get('qualifications'),
        'preferred_qualifications': job_data.get('preferred_qualifications'),
        'benefits': job_data.get('benefits'),
        'travel_required': job_data.get('travel_required'),
        'shift': job_data.get('shift'),
        'work_authorization': job_data.get('work_authorization'),
        'posted_date': job_data.get('posted_date'),
        'application_deadline': job_data.get('application_deadline'),
        'closing_date': job_data.get('closing_date'),
        'application_url': app_url or None,
        'ats_platform': job_data.get('ats_platform'),
        'external_job_id': job_data.get('external_job_id'),
        'last_checked_date': now_iso,
        'status': 'ACTIVE',
        'verification_status': 'EXTRACTED',
        'retrieved_at': timezone.now(),
        'last_seen_at': timezone.now(),
        'data_provenance': f'Crawler ({parser_used.get_extraction_method()})',
        'evidence_text': job_data.get('evidence_text', ''),
        'content_hash': content_hash,
        'extraction_method': parser_used.get_extraction_method(),
        'source_snapshot': html_content[:5000],
        'detail_fetched': job_data.get('detail_fetched', False),
    }

    resolved_source_url = (
        job_data.get('source_url') or
        app_url or
        getattr(parser_used, 'final_url', None) or
        company.careers_url or
        company.website_url
    )
    defaults['source_url'] = resolved_source_url

    existing = Job.objects.filter(fingerprint=fingerprint, company=company).first()
    if existing:
        for field, value in defaults.items():
            setattr(existing, field, value)
        existing.save()
        if VerificationService.publish_record(existing, actor="CrawlerLifecycle"):
            CRAWL_TASK_STATE["stats"]["updated_jobs"] += 1
            summary.jobs_updated += 1
            summary.jobs_validated += 1
        else:
            summary.jobs_rejected += 1
    else:
        new_job = Job(
            job_id=f"JOB_{fingerprint[:8]}",
            company=company,
            fingerprint=fingerprint,
            first_seen_at=timezone.now(),
            **defaults
        )
        new_job.save()
        if VerificationService.publish_record(new_job, actor="CrawlerLifecycle"):
            CRAWL_TASK_STATE["stats"]["new_jobs"] += 1
            summary.jobs_published += 1
            summary.jobs_validated += 1
        else:
            summary.jobs_rejected += 1



# ============================================================
# MAIN COMPANY PROCESSOR
# ============================================================

def process_company(company):
    """Full pipeline for one company: careers discovery → job extraction → CSR crawl."""
    now_iso = timezone.now().isoformat()
    seen_job_fingerprints = set()

    # Create a crawl summary record
    summary = CompanyCrawlSummary.objects.create(
        company=company,
        crawl_status='PENDING'
    )

    try:
        _process_careers(company, summary, seen_job_fingerprints, now_iso)
        _process_csr(company, summary, now_iso)
    except Exception as e:
        summary.error_log = str(e)[:1000]
        summary.crawl_status = 'FAILED'
        CRAWL_TASK_STATE["stats"]["fetch_failures"] += 1
        log_event('Failure', 'FAILED', f'Unhandled error: {str(e)[:50]}', company.company_id, company.company_name, 'ERROR')

    summary.crawl_finished_at = timezone.now()
    if summary.crawl_status == 'PENDING':
        summary.crawl_status = 'CRAWLED'
    summary.save()
    CRAWL_TASK_STATE["stats"]["companies_crawled"] += 1

    # Update company record
    company.last_crawled = now_iso
    company.crawl_status = summary.crawl_status
    if summary.ats_platform:
        company.ats_platform = summary.ats_platform
    if summary.ats_url:
        company.ats_url = summary.ats_url
    if summary.career_url_found:
        company.careers_url = summary.career_url_found
    company.save()


def _process_careers(company, summary, seen_job_fingerprints, now_iso):
    """Handles careers page fetch, ATS discovery, job extraction and stale marking."""
    careers_target = company.careers_url or company.website_url
    if not careers_target:
        summary.crawl_status = 'NO_CAREER_URL'
        return

    resp = safe_get(careers_target)
    if resp is None:
        summary.crawl_status = 'FAILED'
        CRAWL_TASK_STATE["stats"]["fetch_failures"] += 1
        log_event('Failure', 'FAILED', 'Connection error', company.company_id, company.company_name, 'FAILED')
        return

    status_code = resp.status_code
    final_url = resp.url

    if status_code in (403, 429):
        # Attempt Playwright headless browser fallback before marking blocked
        log_event('Info', 'INFO', f'HTTP {status_code} received, attempting Playwright fallback...', company.company_id, company.company_name, 'PLAYWRIGHT')
        pw_html, pw_url, pw_status = fetch_with_playwright(careers_target)
        if pw_status == 200 and len(pw_html) > 500:
            html_content = pw_html
            final_url = pw_url
            status_code = 200
        else:
            summary.crawl_status = 'BLOCKED'
            CRAWL_TASK_STATE["stats"]["blocked"] += 1
            log_event('Failure', 'BLOCKED', f'HTTP {status_code}', company.company_id, company.company_name, 'BLOCKED')
            log_page_record(company, careers_target, final_url, "Access Blocked", "CAREERS", status_code, "")
            return
    else:
        if not resp.ok:
            summary.crawl_status = 'FAILED'
            CRAWL_TASK_STATE["stats"]["fetch_failures"] += 1
            log_event('Failure', 'FAILED', f'HTTP {status_code}', company.company_id, company.company_name, 'FAILED')
            return
        html_content = resp.text

    # Validate redirect domain
    is_valid_domain, val_reason, source_type = validate_redirect_chain(
        company, careers_target, final_url, discovered_on_official_site=True
    )
    if not is_valid_domain:
        summary.crawl_status = 'REDIRECT_BLOCKED'
        CRAWL_TASK_STATE["stats"]["fetch_failures"] += 1
        log_event('Security', 'REJECTED', f'Unapproved Redirect: {val_reason}', company.company_id, company.company_name, 'REDIRECT_BLOCKED')
        AuditTrail.objects.create(
            record_type='Company', record_id=company.company_id,
            action='UNAPPROVED_REDIRECT_BLOCKED',
            previous_value=careers_target, new_value=final_url,
            user_role='SecurityValidator',
            notes=f"Blocked: {val_reason}", timestamp=now_iso
        )
        return

    content_hash = hashlib.md5(html_content.encode('utf-8')).hexdigest()

    # SPA fallback if content is mostly script shell
    if len(html_content) < 5000 and '<script' in html_content.lower():
        log_event('Info', 'INFO', 'Using JS Headless Renderer', company.company_id, company.company_name, 'PLAYWRIGHT')
        pw_html, pw_url, p_status = fetch_with_playwright(careers_target)
        if p_status == 200 and len(pw_html) > 500:
            html_content = pw_html
            final_url = pw_url
            content_hash = hashlib.md5(html_content.encode('utf-8')).hexdigest()

    soup_meta = BeautifulSoup(html_content, 'lxml')
    page_title_text = soup_meta.title.text.strip() if soup_meta.title else f"{company.company_name} Careers"
    log_page_record(company, careers_target, final_url, page_title_text, "CAREERS", status_code, content_hash, html_content[:200])

    # Discover other company pages from this page
    disc_updates = discover_company_pages(company, html_content, final_url)
    discovered_careers = disc_updates.get('careers_url')

    # If this was homepage and we discovered an authentic dedicated careers URL, navigate to it!
    if discovered_careers and discovered_careers != careers_target and discovered_careers != final_url:
        is_sub_valid, _, _ = validate_redirect_chain(company, careers_target, discovered_careers, discovered_on_official_site=True)
        if is_sub_valid:
            log_event('Discovery', 'FOLLOWING_CAREERS', f"Navigating to official careers URL: {discovered_careers}", company.company_id, company.company_name, 'DISCOVERY')
            sub_resp = safe_get(discovered_careers)
            if sub_resp and sub_resp.ok:
                sub_valid, _, _ = validate_redirect_chain(company, discovered_careers, sub_resp.url, discovered_on_official_site=True)
                if sub_valid:
                    final_url = sub_resp.url
                    html_content = sub_resp.text
                    content_hash = hashlib.md5(html_content.encode('utf-8')).hexdigest()
                    log_page_record(company, discovered_careers, final_url, f"{company.company_name} Dedicated Careers", "CAREERS", sub_resp.status_code, content_hash)

    summary.career_url_found = final_url

    # ATS extraction (with full pagination + detail fetch)
    ats_parser = ATSParser(company, careers_target, final_url, html_content)
    jobs_data = ats_parser.extract_jobs()
    parser_used = ats_parser

    if jobs_data:
        summary.ats_platform = ats_parser.discovered_platform
        summary.ats_url = final_url
        company.ats_platform = ats_parser.discovered_platform
        company.ats_url = final_url

    # Fallback: generic HTML parser
    if not jobs_data:
        generic_parser = GenericHTMLParser(company, careers_target, final_url, html_content)
        jobs_data = generic_parser.extract_jobs()
        parser_used = generic_parser

    summary.jobs_discovered = len(jobs_data)
    CRAWL_TASK_STATE["stats"]["jobs_discovered"] = CRAWL_TASK_STATE["stats"].get("jobs_discovered", 0) + len(jobs_data)


    for job_data in jobs_data:
        save_job(company, job_data, content_hash, html_content, parser_used, now_iso, seen_job_fingerprints, summary)

    summary.jobs_extracted = len(jobs_data)
    log_event('Extraction', 'EXTRACTED', f'Extracted {len(jobs_data)} jobs ({parser_used.get_extraction_method()})',
              company.company_id, company.company_name, 'EXTRACTED')

    # Stale job detection — only mark expired if crawl actually produced results
    if len(jobs_data) > 0:
        active_jobs = Job.objects.filter(company=company, status='ACTIVE')
        for aj in active_jobs:
            if aj.fingerprint not in seen_job_fingerprints:
                aj.status = 'EXPIRED'
                aj.verification_status = 'STALE'
                aj.save()
                summary.jobs_expired += 1
                CRAWL_TASK_STATE["stats"]["expired_jobs"] += 1
                AuditTrail.objects.create(
                    record_type='Job', record_id=str(aj.pk),
                    action='STALE_JOB_EXPIRED',
                    previous_value='ACTIVE / PUBLISHED', new_value='EXPIRED / STALE',
                    user_role='StaleDataDetector',
                    notes=f"Job absent during live crawl of {final_url}.",
                    timestamp=now_iso
                )

    # Contact extraction
    corp_parser = CorporateHTMLParser(company, careers_target, final_url, html_content)
    contacts_data = corp_parser.extract_contacts()
    for c in contacts_data:
        email = c.get('email')
        phone = c.get('phone')
        if not email and not phone:
            continue
        fp = generate_fingerprint((email or '') + (phone or '') + str(company.company_id))
        if not Contact.objects.filter(fingerprint=fp).exists():
            cont = Contact.objects.create(
                company=company,
                email=email,
                phone=phone,
                department=c.get('department'),
                evidence_text=c.get('evidence_text'),
                fingerprint=fp,
                source_url=final_url,
                retrieved_at=timezone.now(),
                verification_status='EXTRACTED'
            )
            VerificationService.publish_record(cont, actor="CrawlerLifecycle")
            summary.contacts_discovered += 1
            CRAWL_TASK_STATE["stats"]["contacts_found"] = CRAWL_TASK_STATE["stats"].get("contacts_found", 0) + 1


def _process_csr(company, summary, now_iso):
    """Deep CSR crawl: landing page + all linked sub-pages + PDF discovery."""
    # Start from CSR/Sustainability/ESG URL (whichever is known)
    csr_start_urls = list(filter(None, [
        company.csr_portal_url,
        company.sustainability_url,
        company.esg_url,
        company.foundation_url,
    ]))

    if not csr_start_urls:
        return

    all_csr_pages = set()
    pdf_links = set()
    csr_projects_saved = 0
    csr_opps_saved = 0

    def crawl_csr_page(csr_url, depth=0):
        nonlocal csr_projects_saved, csr_opps_saved
        if csr_url in all_csr_pages or depth > 1 or len(all_csr_pages) >= 5:
            return
        all_csr_pages.add(csr_url)

        csr_resp = safe_get(csr_url)
        if not csr_resp or not csr_resp.ok:
            return

        csr_final_url = csr_resp.url
        is_valid, _, _ = validate_redirect_chain(company, csr_url, csr_final_url)
        if not is_valid:
            return

        csr_html = csr_resp.text
        csr_hash = hashlib.md5(csr_html.encode('utf-8')).hexdigest()
        csr_soup = BeautifulSoup(csr_html, 'lxml')
        csr_title = csr_soup.title.text.strip() if csr_soup.title else f"{company.company_name} CSR"

        log_page_record(company, csr_url, csr_final_url, csr_title, "CSR", csr_resp.status_code, csr_hash)
        summary.csr_pages_found += 1
        CRAWL_TASK_STATE["stats"]["csr_pages_found"] = CRAWL_TASK_STATE["stats"].get("csr_pages_found", 0) + 1

        # Extract CSR projects from this page
        csr_parser = CorporateHTMLParser(company, csr_url, csr_final_url, csr_html)
        html_csr = csr_parser.extract_csr()
        for p in html_csr:
            fp = generate_fingerprint(p['project_name'] + str(company.company_id))
            if not CSRProject.objects.filter(fingerprint=fp).exists():
                csr_proj = CSRProject.objects.create(
                    company=company,
                    project_name=p['project_name'],
                    description=p.get('description'),
                    category=p.get('category'),
                    budget=p.get('budget'),
                    geographic_location=p.get('geographic_location'),
                    evidence_text=p.get('evidence_text'),
                    fingerprint=fp,
                    source_url=csr_final_url,
                    retrieved_at=timezone.now(),
                    verification_status='EXTRACTED'
                )
                VerificationService.publish_record(csr_proj, actor="CrawlerLifecycle")
                csr_projects_saved += 1
                CRAWL_TASK_STATE["stats"]["csr_projects"] = CRAWL_TASK_STATE["stats"].get("csr_projects", 0) + 1

        # Extract genuine grant/RFP opportunities
        html_opps = csr_parser.extract_opportunities()
        for opp in html_opps:
            fp = generate_fingerprint(opp['title'] + opp['portal_url'] + str(company.company_id))
            if not CSROpportunity.objects.filter(fingerprint=fp).exists():
                new_opp = CSROpportunity.objects.create(
                    company=company,
                    title=opp['title'],
                    opportunity_type=opp.get('opportunity_type'),
                    portal_url=opp.get('portal_url'),
                    evidence_text=opp.get('evidence_text'),
                    fingerprint=fp,
                    source_url=csr_final_url,
                    retrieved_at=timezone.now(),
                    verification_status='EXTRACTED'
                )
                VerificationService.publish_record(new_opp, actor="CrawlerLifecycle")
                csr_opps_saved += 1
                CRAWL_TASK_STATE["stats"]["csr_opportunities"] = CRAWL_TASK_STATE["stats"].get("csr_opportunities", 0) + 1

        # Discover CSR PDF links
        for a in csr_soup.find_all('a', href=True):
            href = a['href'].strip()
            full_link = urllib.parse.urljoin(csr_final_url, href)
            if href.lower().endswith('.pdf') and any(k in href.lower() for k in ['csr', 'sustainability', 'annual', 'brsr', 'esg', 'policy', 'report']):
                pdf_links.add(full_link)
            # Collect internal sub-links for deeper crawl (depth + 1)
            elif depth < 1 and full_link.startswith('http') and csr_final_url.split('/')[2] in full_link:
                link_text = a.get_text(strip=True).lower()
                if any(k in link_text or k in href.lower() for k in ['csr', 'sustainability', 'project', 'initiative', 'report', 'esg', 'impact']):
                    if full_link not in all_csr_pages:
                        time.sleep(0.3)
                        crawl_csr_page(full_link, depth + 1)

    for start_url in csr_start_urls:
        time.sleep(0.5)
        crawl_csr_page(start_url)

    summary.csr_projects_discovered = csr_projects_saved

    # Process PDFs (1 per company to maintain high performance across 205 companies)
    for pdf_url in list(pdf_links)[:1]:
        pdf_parser = CSRPdfParser(pdf_url, company)

        pdf_projects = pdf_parser.fetch_and_extract()
        log_page_record(
            company, pdf_url, pdf_url,
            f"CSR PDF ({pdf_parser.http_status or 'N/A'})",
            "CSR_PDF", pdf_parser.http_status or 500, "",
            f"Extracted {len(pdf_projects)} projects"
        )
        if pdf_projects:
            summary.csr_pdfs_found += 1
            CRAWL_TASK_STATE["stats"]["csr_pdfs"] = CRAWL_TASK_STATE["stats"].get("csr_pdfs", 0) + 1

        for proj in pdf_projects:
            fp = generate_fingerprint(proj['project_name'] + str(company.company_id))
            if not CSRProject.objects.filter(fingerprint=fp).exists():
                pdf_rec = CSRProject.objects.create(
                    company=company,
                    project_name=proj['project_name'],
                    category=proj.get('category'),
                    description=proj.get('description'),
                    budget=proj.get('budget'),
                    geographic_location=proj.get('geographic_location'),
                    evidence_text=proj.get('evidence_text'),
                    evidence_locator=proj.get('evidence_locator'),
                    fingerprint=fp,
                    source_url=pdf_url,
                    retrieved_at=timezone.now(),
                    verification_status='EXTRACTED'
                )
                VerificationService.publish_record(pdf_rec, actor="CrawlerLifecycle")
                summary.csr_projects_discovered += 1

    summary.csr_opportunities_discovered = csr_opps_saved


# ============================================================
# PIPELINE ORCHESTRATION
# ============================================================

def run_crawler_pipeline():
    if CRAWL_TASK_STATE["is_running"]:
        return

    CRAWL_TASK_STATE["is_running"] = True
    CRAWL_TASK_STATE["start_time"] = time.time()

    # Reset all stats
    CRAWL_TASK_STATE["stats"] = {
        "companies_requested": 0,
        "companies_crawled": 0,
        "blocked": 0,
        "fetch_failures": 0,
        "jobs_discovered": 0,
        "new_jobs": 0,
        "updated_jobs": 0,
        "expired_jobs": 0,
        "csr_pages_found": 0,
        "csr_pdfs": 0,
        "csr_projects": 0,
        "csr_opportunities": 0,
        "contacts_found": 0,
    }
    CRAWL_TASK_STATE["events"] = []

    companies = Company.objects.all().order_by('company_name')
    total_count = companies.count()
    CRAWL_TASK_STATE["stats"]["companies_requested"] = total_count

    log_event('SYSTEM', 'RUNNING', f'Starting Intelligence Pipeline ({total_count} Companies)')

    for idx, company in enumerate(companies, 1):
        if not CRAWL_TASK_STATE["is_running"]:
            break
        CRAWL_TASK_STATE["current_company"] = company.company_name
        log_event('Discovery', 'PROBING', f"[{idx}/{total_count}] Probing {company.company_name}",
                  company.company_id, company.company_name, 'START')
        process_company(company)
        time.sleep(0.5)

    log_event('SYSTEM', 'COMPLETED', f'Finished Intelligence Pipeline for {total_count} Companies')
    CRAWL_TASK_STATE["is_running"] = False
    CRAWL_TASK_STATE["current_company"] = None



def start_background_crawl():
    if CRAWL_TASK_STATE["is_running"]:
        return False
    thread = threading.Thread(target=run_crawler_pipeline)
    thread.daemon = True
    thread.start()
    return True
