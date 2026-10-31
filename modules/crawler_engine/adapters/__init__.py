"""
modules/crawler_engine/adapters/__init__.py
===========================================
Registry and dispatcher for Source-Specific ATS Adapters.
"""
from typing import List, Optional
from .base import BaseATSAdapter, ExtractedJobRecord
from .workday import WorkdayAdapter
from .reliance import ReliancePortalAdapter
from .darwinbox import DarwinboxAdapter
from .taleo import TaleoAdapter
from .successfactors import SuccessFactorsAdapter
from .generic_jsonld import GenericStructuredJobAdapter

REGISTERED_ADAPTERS: List[BaseATSAdapter] = [
    ReliancePortalAdapter(),
    WorkdayAdapter(),
    DarwinboxAdapter(),
    TaleoAdapter(),
    SuccessFactorsAdapter(),
    GenericStructuredJobAdapter(),
]


def resolve_adapter_for_url(url: str) -> Optional[BaseATSAdapter]:
    """Finds the best matching ATS adapter for the given URL."""
    for adapter in REGISTERED_ADAPTERS:
        # Check platform-specific adapters first (GenericStructuredJobAdapter returns True for everything)
        if adapter.platform_name != "Structured JSON-LD" and adapter.can_handle(url):
            return adapter
    return GenericStructuredJobAdapter()

