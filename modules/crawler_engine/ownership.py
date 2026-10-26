"""
Decides which listed company (if any) a job posting really belongs to.

Pure Python (dict in -> decision out) so it is unit-testable without Django.
Never guesses: when the posting does not identify exactly one company the
result is OWNER_UNRESOLVED and the job must not be published.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from .normalizers import is_india_location

CONFIG_PATH = Path(__file__).resolve().parents[2] / 'config' / 'shared_tenants.json'

OWNED = 'OWNED'
UNRESOLVED = 'OWNER_UNRESOLVED'
WRONG_COMPANY = 'OWNER_OTHER_COMPANY'
NOT_IN_SCOPE = 'OUT_OF_SCOPE_LOCATION'


def load_config(path: Path = CONFIG_PATH) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'tenants': []}


def _tenant_for(host: str, cfg: dict) -> Optional[dict]:
    host = (host or '').lower()
    for t in cfg.get('tenants', []):
        if t['host'].lower() == host:
            return t
    return None


def _site_number(url: str) -> Optional[str]:
    m = re.search(r'/sites/(CX_\w+)/', url or '', re.I)
    return m.group(1).upper() if m else None


def tenant_key(url: Optional[str]) -> Optional[str]:
    """Stable tenant identifier stored in Job.ats_tenant (host, + site for Oracle)."""
    if not url:
        return None
    p = urlparse(url)
    host = (p.netloc or '').lower()
    if not host:
        return None
    site = _site_number(url)
    return f"{host}/{site}" if site else host


def resolve_owner(job: Dict, crawl_symbol: Optional[str], cfg: Optional[dict] = None) -> Tuple[str, str]:
    """
    job: {'application_url', 'location', 'country', 'business_unit', 'legal_entity', 'title'}
    crawl_symbol: NSE symbol of the company whose portal is being crawled.
    Returns (decision, reason).
    """
    cfg = cfg or load_config()
    url = job.get('application_url') or ''
    host = (urlparse(url).netloc or '').lower()
    tenant = _tenant_for(host, cfg)
    if not tenant:                      # dedicated company portal - the crawler's company owns it
        return OWNED, 'dedicated portal'

    # 1. India-only scope (e.g. HUL on the global Unilever tenant)
    if crawl_symbol in tenant.get('india_only_for', []):
        if not is_india_location(job.get('location'), job.get('country')):
            return NOT_IN_SCOPE, f"location '{job.get('location')}' is not confirmed to be in India"

    # 2. Site that belongs to exactly one company
    site = _site_number(url)
    owners = tenant.get('site_owner', {})
    if site and site in owners:
        return (OWNED, f'exclusive site {site}') if owners[site] == crawl_symbol else \
               (WRONG_COMPANY, f'site {site} belongs to {owners[site]}')

    # 3. Shared site: the posting must name the legal entity / business unit
    if site and site in tenant.get('shared_sites', []):
        text = ' '.join(str(job.get(k) or '') for k in ('legal_entity', 'business_unit')).lower()
        if not text.strip():
            return UNRESOLVED, f'shared site {site} and posting has no legal-entity / business-unit field'
        hits = [sym for sym, aliases in tenant.get('entity_aliases', {}).items()
                if any(a in text for a in aliases)]
        if len(hits) == 1:
            return (OWNED, f'entity field names {hits[0]}') if hits[0] == crawl_symbol else \
                   (WRONG_COMPANY, f'entity field names {hits[0]}')
        return UNRESOLVED, 'entity field ambiguous or unknown'

    return OWNED, 'tenant without ownership rules'
