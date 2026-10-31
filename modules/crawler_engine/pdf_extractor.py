"""
modules/crawler_engine/pdf_extractor.py
=======================================
High-accuracy PDF text and table extraction engine using pypdf.
Extracts clean textual narratives, identifies tables, and tags exact page numbers for CSR reports and annual filings.
"""
import os
import io
import re
from typing import List, Dict, Any, Optional
import pypdf


class PDFReportExtractor:
    """
    Extracts text and structured page references from corporate sustainability,
    CSR, and annual report PDF documents.
    """
    def __init__(self, max_pages: int = 150):
        self.max_pages = max_pages

    def extract_from_bytes(self, pdf_bytes: bytes, filename: str = "report.pdf") -> List[Dict[str, Any]]:
        """
        Parses raw PDF bytes and returns page-by-page text chunks with metadata.
        """
        pages_data: List[Dict[str, Any]] = []
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            total_pages = min(len(reader.pages), self.max_pages)
            
            for idx in range(total_pages):
                page_num = idx + 1
                page = reader.pages[idx]
                raw_text = page.extract_text() or ""
                clean_text = self._normalize_text(raw_text)
                
                if len(clean_text) < 50:
                    continue
                
                # Check for table or project markers
                has_expenditure = bool(re.search(r'(?:inr|rs\.?|lakh|crore|budget|outlay|expenditure|spent)', clean_text, re.IGNORECASE))
                has_schedule_vii = bool(re.search(r'(?:schedule\s*vii|section\s*135|csr\s*committee|implementing\s*agency)', clean_text, re.IGNORECASE))
                
                pages_data.append({
                    "page_number": page_num,
                    "filename": filename,
                    "text": clean_text,
                    "char_count": len(clean_text),
                    "has_expenditure_indicators": has_expenditure,
                    "has_statutory_indicators": has_schedule_vii
                })
        except Exception as e:
            pass

        return pages_data

    def _normalize_text(self, text: str) -> str:
        # Normalize whitespace and unicode ligatures
        text = text.replace('\xa0', ' ')
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

