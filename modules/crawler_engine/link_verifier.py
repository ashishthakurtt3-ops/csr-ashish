"""
Live verification of job apply links AND CSR / corporate portal links.

1. Job links (`verify_job_link`):
   A job may be published ONLY when `verify_job_link` returns ok=True, i.e.
   * the page / ATS API answers HTTP 200,
   * it was not redirected to a different site or a generic landing page,
   * it is not a "job closed / not found" soft-404 or a login wall, and
   * the posting's requisition id appears in it, or its title matches the job title.

2. CSR & corporate links (`verify_csr_link`):
   Verifies CSR portal webpages, Foundation pages, Sustainability/ESG pages, and PDF disclosures
   (Annual Report, BRSR, CSR PDF). Detects login walls (`LOGIN_REQUIRED`), broken links,
   invalid cross-domain redirects, and identifies whether the source is a Webpage or PDF.

Pure Python + `requests` (no Django) so it can be unit-tested with a fake `get`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Optional
from urllib.parse import quote, urlparse, urldefrag, urljoin
from curl_cffi import requests as cffi_requests

from .normalizers import is_generic_landing_url, detect_csr_source_format
from .access_detector import detect_login_wall

# Status constants
OK = 'VERIFIED_HTTP_200'
BROKEN = 'LINK_BROKEN'
MISMATCH = 'CONTENT_MISMATCH'
REDIRECTED = 'REDIRECTED_ELSEWHERE'
GENERIC = 'GENERIC_LANDING_PAGE'
CLOSED = 'JOB_CLOSED'
LOGIN_WALL = 'LOGIN_REQUIRED'
UNREACHABLE = 'UNREACHABLE'

_CLOSED_PHRASES = (
    'this job is no longer available',
    'job posting has expired',
    'position has been filled',
    'requisition is closed',
    'no longer accepting applications',
    'job is closed',
    'this position has closed',
    'job not found',
    'page not found',
)

_SOFT_404_PHRASES = (
    'page not found',
    '404 not found',
    '404 - not found',
    'error 404',
    'not found',
    'page does not exist',
)


@dataclass
class LinkResult:
    ok: bool
    status: str
    http_code: Optional[int]
    final_url: Optional[str]
    reason: str
    source_format: str = 'HTML Webpage'


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r'[a-z0-9]+', (text or '').lower()) if len(w) > 1]


def title_matches(expected: str, candidate: str) -> bool:
    if not expected or not candidate:
        return False
    ew = set(_words(expected))
    cw = set(_words(candidate))
    if not ew or not cw:
        return False
    overlap = ew & cw
    if len(ew) == 1:
        return len(overlap) >= 1
    return len(overlap) >= min(len(ew), 2)


def build_highlight_url(official_page_url: str, verbatim_text: str) -> str:
    """
    Appends Chrome/Edge Text Fragment (#:~:text=...) to the official URL so clicking the link
    opens the official webpage, scrolls directly to the exact text, and highlights it in yellow.
    """
    clean_base, _ = urldefrag(official_page_url)
    # Clean punctuation that breaks text fragments
    cleaned = re.sub(r'[\r\n\t]+', ' ', verbatim_text or '').strip()
    words = [w for w in cleaned.split(' ') if w and not w.startswith('http')]
    if len(words) < 4:
        return clean_base
    snippet = " ".join(words[:7])
    return f"{clean_base}#:~:text={quote(snippet)}"


def verify_url_live(url: str, timeout: int = 15) -> dict:
    """
    Probes a job or CSR URL live using Chrome TLS impersonation to confirm HTTP 200 status.
    """
    clean_url, _ = urldefrag(url)
    try:
        resp = cffi_requests.get(
            clean_url,
            impersonate="chrome124",
            timeout=timeout,
            allow_redirects=True,
            headers={"Cache-Control": "no-cache"}
        )
        is_valid = 200 <= resp.status_code < 300
        return {
            "is_valid": is_valid,
            "status_code": resp.status_code,
            "final_url": str(resp.url),
            "verification_state": "LINK_OK" if is_valid else f"HTTP_{resp.status_code}"
        }
    except Exception as exc:
        return {
            "is_valid": False,
            "status_code": 0,
            "final_url": clean_url,
            "verification_state": "BROKEN",
            "error": str(exc)
        }


def _registrable(host: str) -> str:
    p = (host or '').lower().removeprefix('www.').split('.')
    return '.'.join(p[-3:]) if len(p) >= 3 and p[-2] in ('co', 'com', 'org', 'net', 'gov', 'ac', 'res') else '.'.join(p[-2:])


def _default_get(url, **kw):
    clean_url, _ = urldefrag(url)
    hdrs = {
        'Accept': 'application/json,text/html,application/pdf;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
    }
    if '.pdf' in str(clean_url).lower():
        hdrs['Range'] = 'bytes=0-4095'
    try:
        r = cffi_requests.get(
            clean_url,
            impersonate="chrome124",
            timeout=kw.pop('timeout', 20),
            allow_redirects=True,
            headers=hdrs,
            **kw
        )
        if r.status_code == 206:
            r.status_code = 200
        return r
    except Exception:
        import requests
        r = requests.get(clean_url, timeout=20, allow_redirects=True, headers=hdrs)
        if r.status_code == 206:
            r.status_code = 200
        return r


# ----------------------------- ATS specific API checks ---------------------- #
def _check_oracle(url, ext_id, title, get):
    p = urlparse(url)
    m = re.search(r'/sites/(CX_\w+)/job/(\d+)', url, re.I)
    if not m:
        return None
    site, req = m.group(1), m.group(2)
    api = (f"{p.scheme}://{p.netloc}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
           f"?expand=all&onlyData=true&finder=" + quote(f'ById;Id="{req}",siteNumber={site}', safe=''))
    r = get(api)
    if r.status_code != 200:
        return LinkResult(False, BROKEN, r.status_code, url, f'Oracle API HTTP {r.status_code}')
    items = (r.json() or {}).get('items') or []
    if not items:
        return LinkResult(False, CLOSED, 200, url, 'Oracle requisition not returned (closed/removed)')
    api_title = items[0].get('Title') or ''
    if str(items[0].get('Id')) != req or not title_matches(title, api_title):
        return LinkResult(False, MISMATCH, 200, url, f"Oracle title '{api_title}' != '{title}'")
    return LinkResult(True, OK, 200, url, 'Oracle API confirms requisition and title')


def _check_lever(url, ext_id, title, get):
    m = re.match(r'https?://jobs\.lever\.co/([^/]+)/([0-9a-f-]{36})', url, re.I)
    if not m:
        return None
    r = get(f'https://api.lever.co/v0/postings/{m.group(1)}/{m.group(2)}')
    if r.status_code != 200:
        return LinkResult(False, BROKEN, r.status_code, url, f'Lever API HTTP {r.status_code}')
    if not title_matches(title, (r.json() or {}).get('text', '')):
        return LinkResult(False, MISMATCH, 200, url, 'Lever posting title differs')
    return LinkResult(True, OK, 200, url, 'Lever API confirms posting and title')


def _check_smartrecruiters(url, ext_id, title, get):
    m = re.match(r'https?://jobs\.smartrecruiters\.com/([^/]+)/(\d+)', url, re.I)
    if not m:
        return None
    r = get(f'https://api.smartrecruiters.com/v1/companies/{m.group(1)}/postings/{m.group(2)}')
    if r.status_code != 200:
        return LinkResult(False, BROKEN, r.status_code, url, f'SmartRecruiters API HTTP {r.status_code}')
    if not title_matches(title, (r.json() or {}).get('name', '')):
        return LinkResult(False, MISMATCH, 200, url, 'SmartRecruiters title differs')
    return LinkResult(True, OK, 200, url, 'SmartRecruiters API confirms posting and title')


def _check_workday(url, ext_id, title, get):
    p = urlparse(url)
    if 'myworkdayjobs.com' not in p.netloc:
        return None
    parts = [x for x in p.path.split('/') if x]
    if len(parts) > 1 and re.match(r'^[a-z]{2}(-[A-Za-z]{2})?$', parts[0]):
        parts = parts[1:]
    if len(parts) < 3:
        return None
    site, rest = parts[0], '/' + '/'.join(parts[1:])
    tenant = p.netloc.split('.')[0]
    r = get(f"https://{p.netloc}/wday/cxs/{tenant}/{site}{rest}")
    if r.status_code != 200:
        return LinkResult(False, BROKEN, r.status_code, url, f'Workday API HTTP {r.status_code}')
    info = (r.json() or {}).get('jobPostingInfo') or {}
    if not title_matches(title, info.get('title', '')):
        return LinkResult(False, MISMATCH, 200, url, 'Workday title differs')
    return LinkResult(True, OK, 200, url, 'Workday API confirms posting and title')


def _check_greenhouse(url, ext_id, title, get):
    m = re.match(r'https?://(?:boards|job-boards)\.greenhouse\.io/([^/]+)/jobs/(\d+)', url, re.I)
    if not m:
        return None
    r = get(f'https://boards-api.greenhouse.io/v1/boards/{m.group(1)}/jobs/{m.group(2)}')
    if r.status_code != 200:
        return LinkResult(False, BROKEN, r.status_code, url, f'Greenhouse API HTTP {r.status_code}')
    if not title_matches(title, (r.json() or {}).get('title', '')):
        return LinkResult(False, MISMATCH, 200, url, 'Greenhouse posting title differs')
    return LinkResult(True, OK, 200, url, 'Greenhouse API confirms posting and title')


_API_CHECKS = (_check_oracle, _check_lever, _check_smartrecruiters, _check_workday, _check_greenhouse)


# ----------------------------- generic HTML check --------------------------- #
def _check_html(url, ext_id, title, get):
    r = get(url)
    final = getattr(r, 'url', url) or url
    text = getattr(r, 'text', '') or ''
    is_login, signal = detect_login_wall(r.status_code, final, text)
    if is_login:
        return LinkResult(False, LOGIN_WALL, r.status_code, final, f'Login required ({signal})')
    if r.status_code != 200:
        return LinkResult(False, BROKEN, r.status_code, final, f'HTTP {r.status_code}')
    if _registrable(urlparse(final).netloc) != _registrable(urlparse(url).netloc):
        return LinkResult(False, REDIRECTED, 200, final, f'redirected to {urlparse(final).netloc}')
    if is_generic_landing_url(final) and not is_generic_landing_url(url):
        return LinkResult(False, GENERIC, 200, final, 'redirected to a generic landing page')
    low = text.lower()
    if any(ph in low for ph in _CLOSED_PHRASES):
        return LinkResult(False, CLOSED, 200, final, 'page says the job is closed / not found')
    if ext_id and (str(ext_id) in final or str(ext_id) in text):
        return LinkResult(True, OK, 200, final, 'requisition id found on page')
    head = ' '.join(re.findall(r'<(?:title|h1|h2)[^>]*>(.*?)</(?:title|h1|h2)>', text, re.I | re.S))
    if title_matches(title, head):
        return LinkResult(True, OK, 200, final, 'page title/heading matches job title')
    return LinkResult(False, MISMATCH, 200, final, 'neither requisition id nor job title found on page')


def verify_job_link(application_url: Optional[str], job_title: str, external_job_id: Optional[str] = None,
                    get: Callable = _default_get) -> LinkResult:
    if not application_url or not re.match(r'^https?://', application_url, re.I):
        return LinkResult(False, BROKEN, None, application_url, 'no http(s) application url')
    if 'google.com/search' in application_url.lower() or 'bing.com/search' in application_url.lower():
        return LinkResult(False, BROKEN, None, application_url, 'search engine URL is not a job link')
    if is_generic_landing_url(application_url):
        return LinkResult(False, GENERIC, None, application_url, 'URL is a generic careers/landing page, not one job')
    try:
        for check in _API_CHECKS:
            res = check(application_url, external_job_id, job_title, get)
            if res is not None:
                return res
        return _check_html(application_url, external_job_id, job_title, get)
    except Exception as exc:                      # timeout, DNS, bad JSON ...
        return LinkResult(False, UNREACHABLE, None, application_url, f'{type(exc).__name__}: {exc}'[:200])


# ----------------------------- CSR & Portal Link Check ---------------------- #
def verify_csr_link(url: Optional[str], expected_domain: Optional[str] = None,
                    expected_title: Optional[str] = None, get: Callable = _default_get) -> LinkResult:
    """
    Verifies a CSR webpage, Foundation portal, Sustainability/ESG page, or PDF disclosure URL.
    Ensures HTTP 200, valid redirect chain, no login wall, and identifies whether the
    resource is a PDF document or HTML webpage.
    """
    if not url or not re.match(r'^https?://', url, re.I):
        return LinkResult(False, BROKEN, None, url, 'no http(s) url')
    if 'google.com/search' in url.lower() or 'bing.com/search' in url.lower():
        return LinkResult(False, BROKEN, None, url, 'search engine URL is not an official CSR link')

    try:
        r = get(url)
        final = getattr(r, 'url', url) or url
        text = getattr(r, 'text', '') or ''
        headers = getattr(r, 'headers', {}) or {}
        content_type = str(headers.get('Content-Type') or headers.get('content-type') or '').lower()

        is_login, signal = detect_login_wall(r.status_code, final, text)
        if is_login:
            return LinkResult(False, LOGIN_WALL, r.status_code, final,
                              f'CSR data available only after login ({signal})',
                              source_format='Login Required')

        if r.status_code != 200:
            return LinkResult(False, BROKEN, r.status_code, final, f'HTTP {r.status_code}')

        orig_reg = _registrable(urlparse(url).netloc)
        final_reg = _registrable(urlparse(final).netloc)
        exp_reg = _registrable(expected_domain) if expected_domain else orig_reg

        # Allow redirect to same registrable domain, expected domain, or official foundation/trust domain
        is_foundation_redirect = any(k in final_reg for k in ('foundation', 'trust', 'philanthrop'))
        is_pdf_cdn = '.pdf' in final.lower() or 'application/pdf' in content_type
        if final_reg != orig_reg and final_reg != exp_reg and not is_foundation_redirect and not is_pdf_cdn:
            return LinkResult(False, REDIRECTED, 200, final, f'redirected to unrelated domain {final_reg}')

        # Detect PDF disclosure vs HTML webpage
        fmt = detect_csr_source_format(final)
        if 'application/pdf' in content_type or text.startswith('%PDF') or '.pdf' in final.lower():
            if 'PDF' not in fmt:
                fmt = 'PDF Document (CSR Disclosure)'
            return LinkResult(True, OK, 200, final, 'Verified CSR PDF disclosure', source_format=fmt)

        low = text.lower()
        head = ' '.join(re.findall(r'<(?:title|h1)[^>]*>(.*?)</(?:title|h1)>', text, re.I | re.S)).lower()
        if any(ph in head for ph in _SOFT_404_PHRASES):
            return LinkResult(False, BROKEN, 200, final, 'Soft-404 page not found')

        if expected_title:
            # Verify that at least one distinctive word from the project title or CSR context appears
            tw = [w for w in _words(expected_title) if len(w) > 3]
            if tw and not any(w in low for w in tw):
                return LinkResult(False, MISMATCH, 200, final,
                                  f"CSR project '{expected_title[:40]}' not found on source page",
                                  source_format=fmt)

        return LinkResult(True, OK, 200, final, f'Verified {fmt}', source_format=fmt)
    except Exception as exc:
        return LinkResult(False, UNREACHABLE, None, url, f'{type(exc).__name__}: {exc}'[:200])
