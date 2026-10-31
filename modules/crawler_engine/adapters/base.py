"""
modules/crawler_engine/adapters/base.py
=======================================
Abstract Base Class and data models for Source-Specific ATS Adapters.
Ensures uniform extraction schemas, deterministic parsing, and strict evidence tracing.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class ExtractedJobRecord:
    company_id: str
    job_title: str
    detail_url: str
    application_url: str
    ats_platform: str
    department: Optional[str] = None
    team: Optional[str] = None
    description: Optional[str] = None
    location_raw: Optional[str] = None
    country: Optional[str] = "India"
    employment_type: Optional[str] = None
    work_mode: Optional[str] = None  # Remote / Hybrid / Onsite
    external_job_id: Optional[str] = None
    source_evidence: Dict[str, Any] = field(default_factory=dict)
    first_seen_at: datetime = field(default_factory=datetime.utcnow)
    confidence: float = 1.0


class BaseATSAdapter(ABC):
    """
    Abstract Base Class for ATS extraction adapters.
    Adapters parse official API responses or HTML DOMs from specific career platforms.
    """
    platform_name: str = "generic"

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Determines if this adapter is capable of handling the target URL."""
        pass

    @abstractmethod
    def extract_jobs(self, company_id: str, source_url: str, content: str, content_type: str = "html") -> List[ExtractedJobRecord]:
        """
        Parses source content (HTML or JSON API payload) and extracts structured job records.
        Returns a list of ExtractedJobRecord instances.
        """
        pass

