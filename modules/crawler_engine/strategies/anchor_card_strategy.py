"""
Anchor-Card Extraction Strategy for ImpactBridge™ Job Discovery Engine.

Detects repeated job cards/rows across custom corporate careers portals.
Extracts title, location, and the direct detail link from:
- <a> tag wrapping or adjacent to the title
- data-href, data-url, data-link attributes
- onclick="window.open('...')" or onclick="location.href='...'"
Rejects invalid anchors (#, javascript:void(0), listing URL, mailto, tel).
"""
from __future__ import annotations

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup

from .base import BaseStrategy, ExtractionContext
from ..normalizers import clean_text, normalize_canonical_url

logger = logging.getLogger(__name__)

_REJECT_HREF_SUBSTRINGS = {
    "#", "javascript:void", "javascript:;", "mailto:", "tel:",
    "login", "signin", "register", "apply-now", "share"
}


def extract_card_destination_url(card: Any, base_url: str) -> Optional[str]:
    """Finds the most specific direct job opening URL inside a job card element."""
    # 1. <a> in header / title element
    heading = card.find(["h1", "h2", "h3", "h4", "h5", "strong"])
    if heading:
        h_a = heading.find("a", href=True)
        if h_a:
            raw = h_a["href"].strip()
            if not any(bad in raw.lower() for bad in _REJECT_HREF_SUBSTRINGS):
                return urljoin(base_url, raw)

    # 2. Any <a> in card
    for a in card.find_all("a", href=True):
        raw = a["href"].strip()
        if any(bad in raw.lower() for bad in _REJECT_HREF_SUBSTRINGS):
            continue
        if any(k in raw.lower() for k in ("/job/", "/jobs/", "/position/", "/career/", "/opening/", "jobid", "job_id", "reqid")):
            return urljoin(base_url, raw)

    # 3. data-href / data-url / data-link
    for attr in ("data-href", "data-url", "data-link"):
        val = card.get(attr)
        if val and not any(bad in val.lower() for bad in _REJECT_HREF_SUBSTRINGS):
            return urljoin(base_url, val.strip())

    # 4. onclick
    onclick = card.get("onclick") or ""
    if onclick:
        m = re.search(r"(?:location\.href|window\.open)\s*\(\s*['\"]([^'\"]+)['\"]", onclick)
        if m:
            val = m.group(1).strip()
            if not any(bad in val.lower() for bad in _REJECT_HREF_SUBSTRINGS):
                return urljoin(base_url, val)

    # 5. Fallback to first non-rejected <a>
    first_a = card.find("a", href=True)
    if first_a:
        raw = first_a["href"].strip()
        if not any(bad in raw.lower() for bad in _REJECT_HREF_SUBSTRINGS):
            return urljoin(base_url, raw)

    return None


class AnchorCardStrategy(BaseStrategy):
    name = "anchor_cards"

    def detect(self, context: ExtractionContext) -> bool:
        if not context.html_content:
            return False
        soup = BeautifulSoup(context.html_content, "lxml")
        links = soup.find_all("a", href=True)
        job_links = [
            a for a in links
            if any(k in a["href"].lower() for k in ("/job/", "/jobs/", "/career/", "/careers/", "/opening/", "/openings/", "/position/", "/positions/", "jobid="))
        ]
        return len(job_links) >= 2

    def extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        if not context.html_content:
            return []

        soup = BeautifulSoup(context.html_content, "lxml")
        canon_careers = normalize_canonical_url(context.careers_url) or context.careers_url
        jobs = []
        seen = set()

        # Group repeating cards under container parents
        candidate_parents = []
        for tag in soup.find_all(["ul", "ol", "tbody", "section", "div"]):
            parent_tags = [p.name for p in tag.parents]
            if any(bad in parent_tags for bad in ["header", "nav", "footer"]):
                continue
            tag_cls = " ".join(tag.get("class", [])).lower()
            if any(bad in tag_cls for bad in ["nav", "menu", "footer", "header", "dropdown"]):
                continue
            candidate_parents.append(tag)

        for parent in candidate_parents:
            children = [c for c in parent.find_all(recursive=False) if getattr(c, "name", None)]
            if len(children) < 2:
                continue

            sig_groups: Dict[Tuple[str, str], list] = {}
            for child in children:
                classes = " ".join(sorted(child.get("class", [])))
                sig = (child.name, classes)
                sig_groups.setdefault(sig, []).append(child)

            for sig, group in sig_groups.items():
                if len(group) < 2:
                    continue

                for card in group:
                    heading = card.find(["h2", "h3", "h4", "h5", "strong"])
                    title = ""
                    if heading:
                        title = clean_text(heading.get_text(" ", strip=True)) or ""
                    if not title:
                        link_a = card.find("a", href=True)
                        if link_a:
                            title = clean_text(link_a.get_text(" ", strip=True)) or ""

                    if not title or len(title) < 3 or len(title) > 120:
                        continue
                    if any(bad in title.lower() for bad in ("apply", "apply now", "view more", "read more", "search", "filter")):
                        continue

                    dest_url = extract_card_destination_url(card, context.final_url)
                    if not dest_url:
                        continue

                    canon_dest = normalize_canonical_url(dest_url) or dest_url
                    if not canon_dest:
                        continue

                    # Reject if equals listing URL
                    if canon_dest == canon_careers or canon_dest == normalize_canonical_url(context.final_url):
                        continue

                    key = f"{title}_{canon_dest}"
                    if key in seen:
                        continue
                    seen.add(key)

                    # Extract location if card has location-like tag
                    loc = "India"
                    loc_elem = card.find(class_=re.compile(r"location|city|country|state", re.I))
                    if loc_elem:
                        loc = clean_text(loc_elem.get_text(" ", strip=True)) or "India"

                    # Extract job id if in URL
                    id_m = re.search(r"/(?:job|jobs|position|opening|career)/([a-zA-Z0-9_\-]+)", canon_dest, re.I)
                    ext_id = id_m.group(1) if id_m else None

                    jobs.append({
                        "title": title,
                        "location": loc,
                        "department": "Corporate",
                        "application_url": canon_dest,
                        "external_job_id": ext_id,
                        "raw_metadata": {"card_html": str(card)[:500]},
                        "link_quality": "DIRECT",
                        "link_check_note": "anchor_card_direct_link",
                    })

        return jobs
