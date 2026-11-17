"""
modules/crawler_engine/pdf_extractor.py
=======================================
High-accuracy PDF text and table extraction engine using pypdf.
Extracts clean textual narratives, identifies structured tables, and tags
exact page numbers and statutory evidence for CSR, BRSR, and annual filings.
"""
from __future__ import annotations

import io
import logging
import os
import re
from typing import Any, Dict, List, Optional
import pypdf

logger = logging.getLogger(__name__)


class ExtractedPDFResult(str):
    """
    Hybrid string subclass that preserves 100% backward compatibility
    with code expecting a raw string, while exposing rich structured attributes:
    - .pages: List of per-page dictionaries with text and metadata
    - .page_citations: Formatted citations with page numbers
    - .tables: List of detected tables with page numbers
    - .statutory_evidence: List of extracted statutory / expenditure findings
    - .page_count: Total pages processed
    - .get(k, default): Dictionary-like access
    """
    pages: List[Dict[str, Any]]
    page_citations: str
    tables: List[Dict[str, Any]]
    statutory_evidence: List[Dict[str, Any]]
    page_count: int

    def __new__(cls, full_text: str, **kwargs):
        obj = super().__new__(cls, full_text or "")
        obj.pages = kwargs.get("pages", [])
        obj.page_citations = kwargs.get("page_citations", "")
        obj.tables = kwargs.get("tables", [])
        obj.statutory_evidence = kwargs.get("statutory_evidence", [])
        obj.page_count = kwargs.get("page_count", len(obj.pages))
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": str(self),
            "pages": self.pages,
            "page_citations": self.page_citations,
            "tables": self.tables,
            "statutory_evidence": self.statutory_evidence,
            "page_count": self.page_count,
        }


class PDFReportExtractor:
    """
    Extracts text, tabular structures, and structured page references from
    corporate sustainability, CSR, BRSR, and annual report PDF documents.
    """
    def __init__(self, max_pages: int = 150):
        self.max_pages = max_pages

    def extract_from_bytes(self, pdf_bytes: bytes, filename: str = "report.pdf") -> List[Dict[str, Any]]:
        """
        Parses raw PDF bytes and returns page-by-page text chunks with metadata.

        Corrupt, encrypted or partially unreadable documents are logged instead
        of being swallowed, so "no data extracted" is distinguishable from
        "document contains no CSR evidence".
        """
        pages_data: List[Dict[str, Any]] = []
        failed_pages: List[int] = []

        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes), strict=False)
        except Exception:
            logger.warning("PDF could not be opened: %s", filename, exc_info=True)
            return pages_data

        try:
            total_pages = min(len(reader.pages), self.max_pages)
        except Exception:
            logger.warning("PDF page count unavailable: %s", filename, exc_info=True)
            return pages_data

        for idx in range(total_pages):
            page_num = idx + 1
            try:
                page = reader.pages[idx]
                raw_text = page.extract_text() or ""
                clean_text = self._normalize_text(raw_text)

                if len(clean_text) < 40:
                    continue

                # Check for table or project markers
                has_expenditure = bool(re.search(r'(?:inr|rs\.?|₹|lakh|crore|budget|outlay|expenditure|spent)', clean_text, re.IGNORECASE))
                has_schedule_vii = bool(re.search(r'(?:schedule\s*vii|section\s*135|csr\s*committee|implementing\s*agency|brsr)', clean_text, re.IGNORECASE))

                tables = self._detect_tables(clean_text, page_num)
                evidence = self._extract_page_evidence(clean_text, page_num)

                pages_data.append({
                    "page_number": page_num,
                    "filename": filename,
                    "text": clean_text,
                    "char_count": len(clean_text),
                    "has_expenditure_indicators": has_expenditure,
                    "has_statutory_indicators": has_schedule_vii,
                    "tables": tables,
                    "evidence": evidence,
                })
            except Exception:
                failed_pages.append(page_num)
                logger.warning(
                    "PDF page extraction failed: %s page %d", filename, page_num, exc_info=True
                )

        if failed_pages:
            logger.warning(
                "PDF %s: %d of %d pages failed extraction (pages %s)",
                filename,
                len(failed_pages),
                total_pages,
                failed_pages[:20],
            )

        return pages_data

    def extract_document(self, pdf_bytes: bytes, filename: str = "report.pdf") -> ExtractedPDFResult:
        """
        Extracts document into an ExtractedPDFResult containing aggregated text,
        page-by-page citations, detected tables, and statutory evidence.
        """
        pages = self.extract_from_bytes(pdf_bytes, filename)
        if not pages:
            return ExtractedPDFResult(
                "",
                pages=[],
                page_citations="",
                tables=[],
                statutory_evidence=[],
                page_count=0,
            )

        # Aggregate text
        text_parts = [p["text"] for p in pages]
        full_text = "\n\n".join(text_parts).strip()

        # Build page-by-page citations
        citation_parts: List[str] = []
        all_tables: List[Dict[str, Any]] = []
        all_evidence: List[Dict[str, Any]] = []

        for p in pages:
            p_num = p["page_number"]
            # Page header
            citation_parts.append(f"[Page {p_num}]")

            # Include detected tables
            if p.get("tables"):
                for t in p["tables"]:
                    all_tables.append(t)
                    citation_parts.append(f"  Table: {t.get('summary', 'Tabular Disclosure')}")
                    for row in t.get("rows", [])[:5]:
                        citation_parts.append(f"    {' | '.join(row)}")

            # Include evidence lines
            if p.get("evidence"):
                for ev in p["evidence"]:
                    all_evidence.append(ev)
                    citation_parts.append(f"  Citation: {ev.get('snippet', '')}")

            # Include representative text snippet
            sample_snippet = p["text"][:350].replace("\n", " ").strip()
            citation_parts.append(f"  Snippet: {sample_snippet}...")
            citation_parts.append("")

        page_citations = "\n".join(citation_parts).strip()

        return ExtractedPDFResult(
            full_text,
            pages=pages,
            page_citations=page_citations,
            tables=all_tables,
            statutory_evidence=all_evidence,
            page_count=len(pages),
        )

    def _detect_tables(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """Detects tabular blocks with aligned columns or numeric rows."""
        tables: List[Dict[str, Any]] = []
        lines = text.split("\n")
        current_table_rows: List[List[str]] = []

        num_col_re = re.compile(r'(?:[0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?|\b[0-9]+%|\b[0-9]+\b)')

        for line in lines:
            line_s = line.strip()
            if not line_s:
                if len(current_table_rows) >= 2:
                    tables.append({
                        "page_number": page_num,
                        "rows": current_table_rows,
                        "row_count": len(current_table_rows),
                        "summary": f"Detected table ({len(current_table_rows)} rows) on page {page_num}",
                    })
                current_table_rows = []
                continue

            # Split on multi-spaces, tabs, or pipes
            cells = [c.strip() for c in re.split(r'\s{2,}|\t+|\|', line_s) if c.strip()]
            if len(cells) >= 2 and any(num_col_re.search(c) for c in cells):
                current_table_rows.append(cells)
            else:
                if len(current_table_rows) >= 2:
                    tables.append({
                        "page_number": page_num,
                        "rows": current_table_rows,
                        "row_count": len(current_table_rows),
                        "summary": f"Detected table ({len(current_table_rows)} rows) on page {page_num}",
                    })
                current_table_rows = []

        if len(current_table_rows) >= 2:
            tables.append({
                "page_number": page_num,
                "rows": current_table_rows,
                "row_count": len(current_table_rows),
                "summary": f"Detected table ({len(current_table_rows)} rows) on page {page_num}",
            })

        return tables

    def _extract_page_evidence(self, text: str, page_num: int) -> List[Dict[str, Any]]:
        """Extracts high-value statutory and financial disclosure sentences with page citations."""
        evidence: List[Dict[str, Any]] = []
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        statutory_pattern = re.compile(
            r'(?:schedule\s*vii|section\s*135|csr\s*committee|implementing\s*agency|'
            r'inr\s*[0-9]+|rs\.?\s*[0-9]+|₹\s*[0-9]+|budget\s*of|spent\s*(?:inr|rs)|'
            r'annual\s*action\s*plan|net\s*profit\s*under\s*section)',
            re.IGNORECASE,
        )

        for s in sentences:
            s_clean = s.strip()
            if len(s_clean) > 30 and statutory_pattern.search(s_clean):
                evidence.append({
                    "page_number": page_num,
                    "snippet": s_clean[:250],
                })
                if len(evidence) >= 5:
                    break

        return evidence

    def _normalize_text(self, text: str) -> str:
        # Normalize whitespace and unicode ligatures
        text = text.replace('\xa0', ' ')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
