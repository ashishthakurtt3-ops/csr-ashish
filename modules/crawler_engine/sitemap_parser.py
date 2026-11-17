"""
modules/crawler_engine/sitemap_parser.py
========================================
Robust, recursive multi-format sitemap parser.
Supports:
- Standard XML <urlset> parsing with loc, lastmod, changefreq, priority.
- Nested <sitemapindex> recursive traversal with depth cap (max_depth=3).
- Compressed .xml.gz sitemap decompression (magic bytes b'\x1f\x8b', header, and URL checks).
- Unescaped entity pre-sanitization and ElementTree namespace tolerance.
- Resilient fallback to regex extraction upon malformed XML.
- Hard total URL limit (max_urls=1000) and cycle prevention.
- Seamless conversion to M2->M3 DiscoveredUrlCandidate contract.
"""
from __future__ import annotations

import gzip
import logging
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

try:
    import requests
except ImportError:
    requests = None

from .robots_handler import RobotsHandler

logger = logging.getLogger(__name__)

COMMON_SITEMAP_FALLBACKS = [
    "/sitemap.xml",
    "/sitemap_index.xml",
    "/sitemap-index.xml",
    "/sitemap.xml.gz",
    "/sitemap-jobs.xml",
    "/jobs-sitemap.xml",
    "/careers-sitemap.xml",
    "/sitemap_careers.xml",
]

MAX_DECOMPRESSED_BYTES = 10_000_000  # 10MB zip-bomb defense limit


@dataclass
class SitemapEntry:
    url: str
    lastmod: Optional[str] = None
    changefreq: Optional[str] = None
    priority: Optional[float] = None
    sitemap_source: str = ""
    depth: int = 0
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        if hasattr(self, key):
            return getattr(self, key)
        return self.raw_metadata.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        if hasattr(self, key):
            val = getattr(self, key)
            return val if val is not None else default
        return self.raw_metadata.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """Converts to dictionary representation."""
        return {
            "url": self.url,
            "lastmod": self.lastmod,
            "changefreq": self.changefreq,
            "priority": self.priority,
            "sitemap_source": self.sitemap_source,
            "depth": self.depth,
            **self.raw_metadata,
        }

    def to_candidate_dict(self) -> Dict[str, Any]:
        """Converts to M2->M3 DiscoveredUrlCandidate format."""
        return {
            "url": self.url,
            "discovery_source": "SITEMAP",
            "referring_url": self.sitemap_source,
            "anchor_text": "",
            "metadata": {
                "lastmod": self.lastmod,
                "changefreq": self.changefreq,
                "priority": self.priority,
                "depth": self.depth,
                **self.raw_metadata,
            },
        }


class SitemapParser:
    def __init__(
        self,
        max_depth: int = 3,
        max_urls: int = 1000,
        max_sitemaps: int = 50,
        timeout: int = 10,
        user_agent: Optional[str] = None,
    ):
        self.max_depth = max_depth
        self.max_urls = max_urls
        self.max_sitemaps = max_sitemaps
        self.timeout = timeout
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"

        self.visited_sitemaps: Set[str] = set()
        self.discovered_entries: List[SitemapEntry] = []
        self.discovered_urls_set: Set[str] = set()

    def fetch_sitemap_raw(self, url: str) -> Tuple[Union[bytes, str], int, str]:
        """
        Fetches sitemap content returning (content, status_code, content_type).
        Implements 3-tier cascade: curl_cffi (chrome124) -> requests -> urllib.
        """
        headers = {"User-Agent": self.user_agent, "Accept": "application/xml,text/xml,*/*;q=0.8"}

        # 1. curl_cffi
        if cffi_requests is not None:
            try:
                resp = cffi_requests.get(
                    url,
                    impersonate="chrome124",
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                ctype = resp.headers.get("content-type", "")
                return resp.content or b"", resp.status_code, ctype
            except Exception as e:
                logger.debug("curl_cffi sitemap fetch error for %s: %s", url, e)

        # 2. requests fallback
        if requests is not None:
            try:
                resp = requests.get(url, headers=headers, timeout=self.timeout, allow_redirects=True)
                ctype = resp.headers.get("content-type", "")
                return resp.content or b"", resp.status_code, ctype
            except Exception as e:
                logger.debug("requests sitemap fetch error for %s: %s", url, e)

        # 3. urllib fallback
        try:
            ctx = ssl._create_unverified_context()
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=self.timeout) as resp:
                content = resp.read(MAX_DECOMPRESSED_BYTES)
                ctype = resp.headers.get("Content-Type", "")
                status = getattr(resp, "status", getattr(resp, "code", 200))
                return content, status, ctype
        except urllib.error.HTTPError as e:
            return b"", e.code, ""
        except Exception as e:
            logger.debug("urllib sitemap fetch error for %s: %s", url, e)
            return b"", 0, ""

    def decompress_if_gzipped(
        self,
        content: Union[bytes, str],
        url: str = "",
        headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Detects and decompresses gzip-compressed content with safety limits against zip bombs.
        Returns decompressed XML string.
        """
        if isinstance(content, str):
            return content

        if not content:
            return ""

        is_gz = False
        if len(content) >= 2 and content[:2] == b'\x1f\x8b':
            is_gz = True
        elif url and url.lower().split('?')[0].endswith('.gz'):
            is_gz = True
        elif headers:
            enc = headers.get('content-encoding', '').lower()
            ct = headers.get('content-type', '').lower()
            if 'gzip' in enc or 'gzip' in ct:
                is_gz = True

        if is_gz:
            try:
                decompressed = gzip.decompress(content)
                if len(decompressed) > MAX_DECOMPRESSED_BYTES:
                    logger.warning("Decompressed sitemap exceeds max allowed size for %s; truncating.", url)
                    decompressed = decompressed[:MAX_DECOMPRESSED_BYTES]
                return decompressed.decode("utf-8", errors="replace")
            except Exception as e:
                logger.debug("gzip.decompress error for %s: %s. Attempting raw text decode.", url, e)

        try:
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1", errors="replace")

    @staticmethod
    def _sanitize_xml_entities(xml_str: str) -> str:
        """Escapes raw '&' that are not valid XML entities."""
        return re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', xml_str)

    def parse_content(self, xml_data: Union[str, bytes], sitemap_url: str = "") -> List[Dict[str, Any]]:
        """
        Parses XML text or bytes and extracts URL entries.
        Returns list of entry dicts. If malformed or HTML 404, returns empty list.
        """
        if isinstance(xml_data, bytes):
            xml_str = self.decompress_if_gzipped(xml_data, url=sitemap_url)
        else:
            xml_str = xml_data or ""

        # Strip BOM
        xml_str = xml_str.lstrip("\ufeff")

        if not xml_str or not xml_str.strip():
            return []

        # Check for HTML non-sitemap responses (e.g. 404 page returning HTML)
        lower_head = xml_str[:1000].lower()
        if "<html" in lower_head and "<loc" not in xml_str.lower() and "<sitemap" not in xml_str.lower():
            return []

        clean_xml = self._sanitize_xml_entities(xml_str)
        results: List[Dict[str, Any]] = []

        try:
            root = ET.fromstring(clean_xml.encode("utf-8"))
            tag_name = root.tag.split("}")[-1].lower()

            if tag_name == "sitemapindex":
                for child in root:
                    if child.tag.split("}")[-1].lower() == "sitemap":
                        info: Dict[str, Any] = {}
                        for el in child:
                            k = el.tag.split("}")[-1].lower()
                            info[k] = el.text.strip() if el.text else ""
                        if info.get("loc"):
                            info["url"] = info["loc"]
                            results.append(info)
            else:
                for child in root:
                    if child.tag.split("}")[-1].lower() == "url":
                        info = {}
                        for el in child:
                            k = el.tag.split("}")[-1].lower()
                            txt = el.text.strip() if el.text else ""
                            if k == "priority":
                                try:
                                    info[k] = float(txt)
                                except ValueError:
                                    info[k] = None
                            else:
                                info[k] = txt
                        if info.get("loc"):
                            info["url"] = info["loc"]
                            results.append(info)

        except ET.ParseError as err:
            logger.debug("ET.ParseError for %s: %s. Falling back to regex.", sitemap_url, err)
            # Regex extraction fallback
            loc_matches = re.finditer(r'<loc[^>]*>\s*([^<]+?)\s*</loc>', xml_str, re.IGNORECASE)
            for m in loc_matches:
                loc = m.group(1).strip()
                if loc and loc.startswith(("http://", "https://")):
                    results.append({"url": loc, "loc": loc})

        # Cap entries at max_urls
        if len(results) > self.max_urls:
            results = results[:self.max_urls]

        return results

    def parse_recursive(
        self,
        sitemap_url: str,
        max_depth: Optional[int] = None,
        depth: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Recursively traverses sitemaps up to max_depth and max_urls.
        Avoids circular references using visited_sitemaps.
        """
        effective_max_depth = self.max_depth if max_depth is None else max_depth

        if depth > effective_max_depth:
            return [e.to_dict() for e in self.discovered_entries]
        if len(self.discovered_entries) >= self.max_urls:
            return [e.to_dict() for e in self.discovered_entries]
        if len(self.visited_sitemaps) >= self.max_sitemaps:
            return [e.to_dict() for e in self.discovered_entries]

        norm_url = sitemap_url.strip()
        if not norm_url or norm_url in self.visited_sitemaps:
            return [e.to_dict() for e in self.discovered_entries]
        self.visited_sitemaps.add(norm_url)

        content, status, ctype = self.fetch_sitemap_raw(norm_url)
        if status != 200 or not content:
            return [e.to_dict() for e in self.discovered_entries]

        decompressed_text = self.decompress_if_gzipped(content, url=norm_url)
        parsed_items = self.parse_content(decompressed_text, sitemap_url=norm_url)

        is_index = "<sitemapindex" in decompressed_text[:2000].lower() or any("sitemap" in item for item in parsed_items)

        if is_index:
            for item in parsed_items:
                child_loc = item.get("loc") or item.get("url")
                if child_loc and child_loc not in self.visited_sitemaps:
                    self.parse_recursive(child_loc, max_depth=effective_max_depth, depth=depth + 1)
                    if len(self.discovered_entries) >= self.max_urls:
                        break
        else:
            for item in parsed_items:
                loc = item.get("loc") or item.get("url")
                if not loc or not loc.startswith(("http://", "https://")):
                    continue
                if loc not in self.discovered_urls_set:
                    self.discovered_urls_set.add(loc)
                    priority_val = item.get("priority")
                    if priority_val is not None and not isinstance(priority_val, (int, float)):
                        try:
                            priority_val = float(priority_val)
                        except ValueError:
                            priority_val = None

                    entry = SitemapEntry(
                        url=loc,
                        lastmod=item.get("lastmod"),
                        changefreq=item.get("changefreq"),
                        priority=priority_val,
                        sitemap_source=norm_url,
                        depth=depth,
                    )
                    self.discovered_entries.append(entry)
                    if len(self.discovered_entries) >= self.max_urls:
                        break

        return [e.to_dict() for e in self.discovered_entries]

    def discover_and_parse(
        self,
        base_url: str,
        robots_handler: Optional[RobotsHandler] = None,
    ) -> List[SitemapEntry]:
        """
        Discovers sitemaps from robots.txt + common fallbacks and parses up to limits.
        Returns List[SitemapEntry].
        """
        self.visited_sitemaps.clear()
        self.discovered_entries.clear()
        self.discovered_urls_set.clear()

        candidate_sitemaps: List[str] = []

        # 1. Probe Robots.txt
        if robots_handler:
            candidate_sitemaps.extend(robots_handler.get_sitemaps())
        else:
            rh = RobotsHandler(base_url=base_url, timeout=self.timeout)
            if rh.fetch_and_parse():
                candidate_sitemaps.extend(rh.get_sitemaps())

        # 2. Add common fallback sitemap locations if none found or to supplement
        parsed = urllib.parse.urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        if not candidate_sitemaps:
            for path in COMMON_SITEMAP_FALLBACKS:
                candidate_sitemaps.append(f"{origin}{path}")

        # 3. Parse discovered sitemaps
        for sm_url in candidate_sitemaps:
            if sm_url not in self.visited_sitemaps:
                self.parse_recursive(sm_url, depth=0)
                if len(self.discovered_entries) >= self.max_urls:
                    break

        return list(self.discovered_entries)

    def get_urls(self, base_url: str) -> List[str]:
        """Returns plain list of discovered URLs."""
        entries = self.discover_and_parse(base_url)
        return [e.url for e in entries]

    def get_candidates(self, base_url: str) -> List[Dict[str, Any]]:
        """Returns entries formatted for M2->M3 DiscoveredUrlCandidate interface."""
        entries = self.discover_and_parse(base_url)
        return [e.to_candidate_dict() for e in entries]
