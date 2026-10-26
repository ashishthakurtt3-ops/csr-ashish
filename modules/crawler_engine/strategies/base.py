"""
Base Extraction Strategy interface for ImpactBridge™ Job Discovery Engine.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class ExtractionContext:
    """Holds page context, fetched HTML, discovered URLs, and headers for a company run."""
    def __init__(self, company: Any, careers_url: str, html_content: Optional[str] = None):
        self.company = company
        self.careers_url = careers_url
        self.final_url: str = careers_url
        self.html_content: Optional[str] = html_content
        self.status_code: Optional[int] = None
        self.discovered_ats_platform: Optional[str] = None
        self.discovered_ats_token: Optional[str] = None
        self.extra_metadata: Dict[str, Any] = {}


class BaseStrategy(ABC):
    """Abstract base class for all pluggable job extraction strategies."""
    name: str = "base"

    @abstractmethod
    def detect(self, context: ExtractionContext) -> bool:
        """Returns True if this strategy is applicable to the target company / page."""
        pass

    @abstractmethod
    def extract(self, context: ExtractionContext) -> List[Dict[str, Any]]:
        """
        Extracts jobs from the source.
        Returns a list of JobDict items with keys:
          - title (str)
          - location (str)
          - application_url (str, direct job link)
          - external_job_id (str, optional)
          - department (str, optional)
          - employment_type (str, optional)
          - posted_date (str, optional)
          - job_description (str, optional)
          - raw_metadata (dict, optional)
          - link_quality (str: 'DIRECT' or 'LISTING_FALLBACK')
          - link_check_note (str, optional)
        """
        pass
