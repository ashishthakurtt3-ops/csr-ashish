import warnings
import re
from typing import Tuple
from urllib.parse import urlparse
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

STRICT_SSO_LOGIN_URLS = re.compile(
    r'(/login/?$|/signin/?$|/sign-in/?$|/auth/|/sso/|/oauth2?/|/saml/|auth0\.com|login\.microsoftonline\.com|/user/login/?$|/account/login/?$)',
    re.IGNORECASE
)

LOGIN_TEXT_PATTERNS = re.compile(
    r'(please\s+(?:sign\s*in|log\s*in)\s+to\s+view|sign\s*in\s+to\s+view\s+(?:jobs|careers|opportunities|vacancies)|candidate\s+login\s+required|member\s+login\s+required|must\s+be\s+logged\s+in\s+to\s+view|access\s+restricted\.?\s+please\s+(?:log\s*in|authenticate)|enter\s+your\s+credentials\s+to\s+access)',
    re.IGNORECASE
)


def fetch_live_page(url: str, timeout: int = 25) -> dict:
    """
    Fetches live URL using curl_cffi Chrome 124 TLS fingerprint to bypass Cloudflare/WAF 403 blocks.
    Strictly follows 'Extract First, Login Wall Last':
    If HTTP status is 200, ALWAYS returns ok=True so the extractors inspect the content first.
    Only classifies as LOGIN_REQUIRED if:
      - HTTP status is 401 or 403, OR
      - Page redirected to strict SSO/login endpoint AND body text < 150 words (no public data rendered).
    """
    try:
        resp = cffi_requests.get(
            url,
            impersonate="chrome124",
            headers=DEFAULT_HEADERS,
            timeout=timeout,
            allow_redirects=True,
        )
        final_url = str(resp.url)
        html = resp.text or ""
        status_code = resp.status_code

        is_login_wall = False
        login_reason = ""
        p_url = urlparse(final_url)

        # Word count of visible body text
        soup = BeautifulSoup(html, "lxml") if html else None
        body_text = soup.get_text(" ", strip=True) if soup else ""
        word_count = len(body_text.split())

        if status_code in (401, 403):
            is_login_wall = True
            login_reason = f"HTTP {status_code} ({'Authentication' if status_code == 401 else 'Access'} Required)"
        elif STRICT_SSO_LOGIN_URLS.search(p_url.path or '') or STRICT_SSO_LOGIN_URLS.search(p_url.netloc or ''):
            if word_count < 150:
                is_login_wall = True
                login_reason = f"Redirected to SSO/login endpoint {p_url.netloc}{p_url.path} with no public content"
        elif html and soup:
            text_match = LOGIN_TEXT_PATTERNS.search(body_text)
            links = soup.find_all("a", href=True)
            has_data_links = any(
                any(k in (a.get('href', '') + a.get_text()).lower() for k in ('job', 'career', 'csr', 'opening', 'position', 'role', 'vacancy', 'opportunity'))
                for a in links
            )
            password_inputs = soup.find_all("input", {"type": "password"})
            if password_inputs and not has_data_links and word_count < 150 and len(links) < 5:
                is_login_wall = True
                login_reason = "Dedicated login form with no public listings or links"
            elif text_match and not has_data_links and word_count < 150 and len(links) < 8:
                is_login_wall = True
                login_reason = text_match.group(0)

        # If 200 <= status_code < 300, we ALWAYS return ok=True so extractors can run first
        # unless it is unequivocally a pure SSO wall with no content (<150 words)
        is_ok = (200 <= status_code < 300) and not (is_login_wall and word_count < 150)

        return {
            "ok": is_ok,
            "status_code": status_code,
            "final_url": final_url,
            "html": html,
            "access_status": "LOGIN_REQUIRED" if is_login_wall else ("PUBLIC_OK" if 200 <= status_code < 300 else f"HTTP_{status_code}"),
            "login_reason": login_reason if is_login_wall else None,
            "error": None if (200 <= status_code < 300 and not is_login_wall) else (login_reason or f"HTTP {status_code} at {final_url}")
        }
    except Exception as exc:
        return {
            "ok": False,
            "status_code": 0,
            "final_url": url,
            "html": "",
            "access_status": "FETCH_ERROR",
            "login_reason": None,
            "error": str(exc)
        }


def detect_login_wall(status_code: int, final_url: str, html: str) -> Tuple[bool, str]:
    """Compatibility wrapper around login detection rules."""
    if status_code == 401:
        return True, "HTTP 401 (Authentication Required)"
    p = urlparse(final_url or '')
    soup = BeautifulSoup(html, "lxml") if html else None
    body_text = soup.get_text(" ", strip=True) if soup else ""
    word_count = len(body_text.split())

    if STRICT_SSO_LOGIN_URLS.search(p.path or '') or STRICT_SSO_LOGIN_URLS.search(p.netloc or ''):
        if word_count < 150:
            return True, f"redirected to auth/login endpoint {p.netloc}{p.path}"
    if html and soup:
        password_inputs = soup.find_all("input", {"type": "password"})
        links = soup.find_all("a", href=True)
        has_data_links = any(
            any(k in (a.get('href', '') + a.get_text()).lower() for k in ('job', 'career', 'csr', 'opening', 'position', 'role', 'vacancy', 'opportunity'))
            for a in links
        )
        if password_inputs and not has_data_links and word_count < 150 and len(links) < 5:
            return True, "password form and no public data links on the page"
        text_match = LOGIN_TEXT_PATTERNS.search(body_text)
        if text_match and not has_data_links and word_count < 150 and len(links) < 8:
            return True, text_match.group(0)
    return False, ""
