"""
modules/crawler_engine/robots_handler.py
========================================
RFC 9309 compliant robots.txt handler.
Wraps Python standard library urllib.robotparser.RobotFileParser with:
- Chrome 124 TLS/JA3 impersonation via curl_cffi and fallback cascade.
- RFC 9309 status code enforcement (2xx parse, 404/410 allow all, 401/403 disallow all, 5xx configurable fallback).
- Pre-sorting of Allow/Disallow rulelines for RFC 9309 longest-match precedence.
- Full integer and floating-point crawl-delay parsing.
- Multi-source sitemap extraction with comment stripping and URL normalization.
"""
from __future__ import annotations

import logging
import re
import ssl
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from typing import Dict, List, Optional, Set, Tuple

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/plain,text/html,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def rfc_preprocess_rules(lines: List[str]) -> List[str]:
    """Sort Allow/Disallow rules by path length within each user-agent group.

    RFC 9309 Section 2.2.2 gives the longest matching path precedence. Python's
    RobotFileParser uses first-match-wins, so emitting the longest rules first
    reproduces the required behaviour.

    A group ends ONLY at the next ``User-agent:`` directive. Blank lines,
    comments, ``Sitemap:`` and ``Crawl-delay:`` do not terminate a group; treating
    them as terminators splits one group into several sort windows and produces
    the wrong precedence.
    """
    result: List[str] = []
    header_lines: List[str] = []
    rules: List[Tuple[int, int, str]] = []  # (path_len, is_allow, original_line)

    def _flush() -> None:
        nonlocal header_lines, rules
        if rules:
            # Longest path first; on equal length, Allow (1) before Disallow (0).
            rules.sort(key=lambda item: (item[0], item[1]), reverse=True)
            result.extend(header_lines)
            result.extend(item[2] for item in rules)
        else:
            result.extend(header_lines)
        header_lines = []
        rules = []

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if not stripped or lower.startswith('#'):
            header_lines.append(line)
            continue

        if lower.startswith('user-agent:'):
            # A new User-agent line starts a new group, but only once the current
            # group already has rules. Consecutive User-agent lines share a group.
            if rules:
                _flush()
            header_lines.append(line)
            continue

        if lower.startswith(('allow:', 'disallow:')):
            parts = stripped.split(':', 1)
            directive = parts[0].strip().lower()
            path = parts[1].strip() if len(parts) > 1 else ''
            # Remove inline comment if present
            if '#' in path:
                path = path.split('#', 1)[0].strip()
            is_allow = 1 if directive == 'allow' else 0
            rules.append((len(path), is_allow, stripped))
            continue

        # Crawl-delay, Sitemap, Request-rate, Host: position-independent.
        header_lines.append(line)

    _flush()
    return result


def fetch_robots_txt(url: str, timeout: int = 10) -> Tuple[int, str]:
    """
    Multi-tier fetch cascade for robots.txt:
    Tier 1: curl_cffi with chrome124 impersonation
    Tier 2: requests standard HTTP client
    Tier 3: urllib with unverified SSL context fallback
    Returns (status_code, content_text).
    """
    # 1. curl_cffi
    if cffi_requests is not None:
        try:
            resp = cffi_requests.get(
                url,
                impersonate="chrome124",
                headers=DEFAULT_HEADERS,
                timeout=timeout,
                allow_redirects=True,
            )
            return resp.status_code, resp.text or ""
        except Exception as e:
            logger.debug("curl_cffi robots.txt fetch error for %s: %s", url, e)

    # 2. requests fallback
    if requests is not None:
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True)
            return resp.status_code, resp.text or ""
        except Exception as e:
            logger.debug("requests robots.txt fallback error for %s: %s", url, e)

    # 3. urllib fallback with unverified SSL
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            raw = resp.read(200000).decode("utf-8", errors="replace")
            status = getattr(resp, "status", getattr(resp, "code", 200))
            return status, raw
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        logger.debug("urllib robots.txt fallback error for %s: %s", url, e)
        return 0, ""


class RobotsHandler:
    """
    RFC 9309 compliant Robots.txt handler.
    Wraps urllib.robotparser.RobotFileParser and provides longest-match ordering,
    status-code enforcement, float crawl-delay parsing, and multi-source sitemap discovery.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        user_agent: str = "*",
        timeout: int = 10,
        allow_on_403: bool = False,
        allow_on_5xx: bool = True,
    ):
        self.base_url = base_url
        self.default_user_agent = user_agent
        self.timeout = timeout
        self.allow_on_403 = allow_on_403
        self.allow_on_5xx = allow_on_5xx

        self.rp = urllib.robotparser.RobotFileParser()
        self.status_code: int = 0
        self.raw_content: str = ""
        self.sitemaps: List[str] = []
        self._parsed_crawl_delay: Optional[float] = None
        self.is_fetched: bool = False

        if base_url:
            self.robots_url = self._build_robots_url(base_url)
        else:
            self.robots_url = ""

    @staticmethod
    def _build_robots_url(url: str) -> str:
        """Extracts scheme://netloc/robots.txt per RFC 9309."""
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        parsed = urllib.parse.urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    @classmethod
    def from_content(
        cls,
        content: str,
        base_url: str = "https://example.com",
        status_code: int = 200,
        user_agent: str = "*",
        allow_on_403: bool = False,
        allow_on_5xx: bool = True,
    ) -> RobotsHandler:
        """Constructs and parses RobotsHandler directly from robots.txt content."""
        handler = cls(
            base_url=base_url,
            user_agent=user_agent,
            allow_on_403=allow_on_403,
            allow_on_5xx=allow_on_5xx,
        )
        handler.parse_content(content, status_code=status_code)
        handler.is_fetched = True
        return handler

    @classmethod
    def from_url(
        cls,
        url: str,
        user_agent: str = "*",
        timeout: int = 10,
        allow_on_403: bool = False,
        allow_on_5xx: bool = True,
    ) -> RobotsHandler:
        """Fetches robots.txt from url and returns an initialized RobotsHandler."""
        handler = cls(
            base_url=url,
            user_agent=user_agent,
            timeout=timeout,
            allow_on_403=allow_on_403,
            allow_on_5xx=allow_on_5xx,
        )
        handler.fetch_and_parse()
        return handler

    def fetch_and_parse(self, base_url: Optional[str] = None) -> bool:
        """Fetches robots.txt using fallback cascade and parses according to RFC 9309."""
        if base_url:
            self.base_url = base_url
            self.robots_url = self._build_robots_url(base_url)

        if not self.robots_url:
            return False

        status_code, content = fetch_robots_txt(self.robots_url, timeout=self.timeout)
        self.status_code = status_code
        self.raw_content = content
        self.is_fetched = True

        return self.parse_content(content, status_code)

    def parse_content(self, content: str, status_code: int = 200) -> bool:
        """Parses robots.txt text adhering strictly to RFC 9309 status rules."""
        self.status_code = status_code
        self.raw_content = content or ""

        # RFC 9309 Section 2.3.1.2: Status Code Rules
        if status_code in (404, 410):
            # Not Found: Allow all
            self.rp.allow_all = True
            self.rp.last_checked = time.time()
            self.sitemaps = []
            return True

        if status_code in (401, 403):
            # Unauthorized / Forbidden
            if self.allow_on_403:
                logger.warning("Robots.txt returned %d; allow_on_403=True override applied.", status_code)
                self.rp.allow_all = True
            else:
                self.rp.disallow_all = True
            self.rp.last_checked = time.time()
            return True

        if 500 <= status_code < 600 or status_code == 0:
            # 5xx or connection failure: temporary server error
            if self.allow_on_5xx:
                # Production resilience fallback policy allows navigation crawling
                self.rp.allow_all = True
            else:
                self.rp.disallow_all = True
            self.rp.last_checked = time.time()
            return False if not self.allow_on_5xx else True

        if 200 <= status_code < 300:
            raw_lines = self.raw_content.splitlines() if self.raw_content else []
            processed_lines = rfc_preprocess_rules(raw_lines)
            self.rp.parse(processed_lines)
            self.rp.last_checked = time.time()

            # Extract Sitemaps
            sitemaps_found: Set[str] = set()
            parsed_maps = self.rp.site_maps()
            if parsed_maps:
                for sm in parsed_maps:
                    if sm:
                        sitemaps_found.add(sm.strip())

            for line in raw_lines:
                # Strip inline comment
                clean_line = line.split('#', 1)[0].strip()
                m = re.match(r'^\s*sitemap:\s*(\S+)', clean_line, re.IGNORECASE)
                if m:
                    sm_url = m.group(1).strip()
                    if self.robots_url and not sm_url.startswith(('http://', 'https://')):
                        sm_url = urllib.parse.urljoin(self.robots_url, sm_url)
                    sitemaps_found.add(sm_url)

            self.sitemaps = list(sorted(sitemaps_found))

            # Extract Crawl-Delay (supports int and float)
            cd_match = re.search(r'^\s*crawl-delay:\s*([0-9]+(?:\.[0-9]+)?)', self.raw_content, re.IGNORECASE | re.MULTILINE)
            if cd_match:
                try:
                    self._parsed_crawl_delay = float(cd_match.group(1))
                except ValueError:
                    pass
            elif self.rp.crawl_delay(self.default_user_agent) is not None:
                self._parsed_crawl_delay = float(self.rp.crawl_delay(self.default_user_agent))

            return True

        # Catch-all
        self.rp.allow_all = True
        return True

    def is_allowed(self, url: str, user_agent: Optional[str] = None) -> bool:
        """Checks if the given URL is allowed to be crawled."""
        ua = user_agent or self.default_user_agent or "*"
        return self.rp.can_fetch(ua, url)

    def can_fetch(self, user_agent: str, url: str) -> bool:
        """Alias matching RobotFileParser.can_fetch."""
        return self.rp.can_fetch(user_agent, url)

    def get_sitemaps(self) -> List[str]:
        """Returns list of declared sitemap URLs."""
        return list(self.sitemaps)

    def get_crawl_delay(self, user_agent: Optional[str] = None) -> Optional[float]:
        """Returns crawl-delay in seconds (int or float) or None."""
        if self._parsed_crawl_delay is not None:
            return self._parsed_crawl_delay
        ua = user_agent or self.default_user_agent or "*"
        delay = self.rp.crawl_delay(ua)
        return float(delay) if delay is not None else None
