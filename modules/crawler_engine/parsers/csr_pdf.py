import io
import re
import requests
from typing import List, Dict, Any, Optional
from pypdf import PdfReader


THEMATIC_CATEGORIES = [
    ('Education & Literacy', ['education', 'school', 'scholarship', 'stem', 'literacy', 'learning']),
    ('Healthcare & Sanitation', ['healthcare', 'health', 'hospital', 'sanitation', 'medical', 'nutrition', 'wash']),
    ('Environmental Sustainability', ['environment', 'renewable', 'solar', 'afforestation', 'biodiversity', 'water conservation', 'carbon']),
    ('Rural Development', ['rural development', 'village', 'agriculture', 'farmer', 'watershed', 'livelihood']),
    ('Skill Development & Livelihoods', ['skill', 'vocational', 'employment', 'entrepreneurship', 'youth empowerment']),
    ('Women Empowerment', ['women', 'gender', 'shg', 'self-help group', 'maternal']),
    ('Disaster Relief & Community Care', ['disaster relief', 'rehabilitation', 'elderly care', 'orphanage', 'differently abled']),
]

BUDGET_PATTERN = re.compile(
    r'(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d+)?)\s*(?:Cr(?:ore)?|Lakh|Million|Billion)?',
    re.IGNORECASE
)

YEAR_PATTERN = re.compile(r'(?:FY\s*20\d{2}[-–]\d{2,4}|20\d{2}[-–]\d{2,4})', re.IGNORECASE)


class CSRPdfParser:
    """
    Downloads and extracts authentic field-level CSR disclosures from official corporate
    CSR policy, annual CSR reports, and BRSR disclosure PDF documents.
    """
    def __init__(self, pdf_url: str, company: Any):
        self.pdf_url = pdf_url
        self.company = company
        self.error_code: Optional[str] = None
        self.http_status: Optional[int] = None

    def fetch_and_extract(self) -> List[Dict[str, Any]]:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,*/*;q=0.8'
        }
        try:
            resp = requests.get(self.pdf_url, headers=headers, timeout=6, stream=True)
            self.http_status = resp.status_code

            if resp.status_code in (403, 429):
                self.error_code = 'BLOCKED'
                return []
            if not resp.ok:
                self.error_code = f'HTTP_{resp.status_code}'
                return []

            # Stream up to 4MB max to prevent hanging on massive 100MB annual reports
            chunks = []
            downloaded = 0
            max_bytes = 4 * 1024 * 1024
            for chunk in resp.iter_content(chunk_size=65536):
                chunks.append(chunk)
                downloaded += len(chunk)
                if downloaded >= max_bytes:
                    break

            content = b"".join(chunks)
            if not content.startswith(b'%PDF'):
                self.error_code = 'NOT_A_VALID_PDF'
                return []

            return self._parse_pdf_bytes(content)

        except requests.exceptions.Timeout:
            self.error_code = 'FETCH_TIMEOUT'
            return []
        except requests.exceptions.ConnectionError:
            self.error_code = 'CONNECTION_ERROR'
            return []
        except Exception as e:
            self.error_code = f'PARSE_ERROR: {str(e)[:50]}'
            return []

    def _parse_pdf_bytes(self, pdf_bytes: bytes) -> List[Dict[str, Any]]:
        extracted_projects = []
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            num_pages = len(reader.pages)

            # Limit to first 25 pages to avoid extreme processing delays on 300-page annual reports
            max_pages = min(num_pages, 25)

            for page_idx in range(max_pages):
                page = reader.pages[page_idx]
                text = page.extract_text() or ''
                page_num = page_idx + 1

                # Search for CSR section keywords
                lower_text = text.lower()
                if not any(k in lower_text for k in ['csr', 'social responsibility', 'sustainability', 'section 135', 'schedule vii']):
                    continue

                # Paragraph-level segmentation
                paragraphs = [p.strip() for p in text.split('\n\n') if len(p.strip()) > 40]
                if not paragraphs:
                    paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 50]

                for para in paragraphs:
                    para_lower = para.lower()

                    # Match thematic category
                    matched_category = None
                    for cat_name, keywords in THEMATIC_CATEGORIES:
                        if any(kw in para_lower for kw in keywords):
                            matched_category = cat_name
                            break

                    if not matched_category:
                        continue

                    # Project title heuristic: First sentence or phrase
                    first_line = para.split('.')[0].strip()
                    if len(first_line) < 15 or len(first_line) > 120:
                        first_line = f"{matched_category} Initiative - {self.company.company_name}"

                    # Budget detection
                    budget_val = None
                    budget_match = BUDGET_PATTERN.search(para)
                    if budget_match:
                        budget_val = budget_match.group(0).strip()

                    # State/Location detection in India
                    indian_states = [
                        'Maharashtra', 'Karnataka', 'Tamil Nadu', 'Gujarat', 'Uttar Pradesh',
                        'Rajasthan', 'Madhya Pradesh', 'Telangana', 'Andhra Pradesh', 'West Bengal',
                        'Bihar', 'Odisha', 'Kerala', 'Punjab', 'Haryana', 'Assam', 'Jharkhand'
                    ]
                    location_val = None
                    for state in indian_states:
                        if state.lower() in para_lower:
                            location_val = state
                            break

                    extracted_projects.append({
                        'project_name': first_line[:200],
                        'category': matched_category,
                        'description': para[:1500],
                        'budget': budget_val, # Only populated if pattern found, else None
                        'geographic_location': location_val, # Only populated if state found, else None
                        'source_url': self.pdf_url,
                        'evidence_text': f"[PDF Page {page_num}] {para[:1500]}",
                        'evidence_locator': f"Page {page_num}",
                        'discovered_date': None,
                        'parser_platform': 'CSR_PDF'
                    })

                    if len(extracted_projects) >= 10:
                        break

                if len(extracted_projects) >= 10:
                    break

        except Exception as e:
            self.error_code = f"PDF_EXTRACTION_ERROR: {str(e)[:50]}"

        return extracted_projects
