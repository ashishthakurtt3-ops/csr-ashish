"""
ImpactBridge™ Deterministic Live Data Engine Proxy
Re-exports the core deterministic sync functions from modules.crawler_engine.crawler.
"""
from .crawler import (
    sync_company_live,
    sync_single_company_live,
    extract_genuine_jobs_live,
    extract_genuine_csr_live,
    discover_company_official_links,
)

__all__ = [
    "sync_company_live",
    "sync_single_company_live",
    "extract_genuine_jobs_live",
    "extract_genuine_csr_live",
    "discover_company_official_links",
]
