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
    r'(?:INR|Rs\.?|₹)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:Cr(?:ore)?|Lakh|Million|Billion)?',
    re.IGNORECASE
)

PDF_JUNK_PATTERNS = [
    re.compile(r'initiative\s*[-—]\s*[A-Za-z]', re.IGNORECASE),
    re.compile(r'\b(award|awards|conclave|djsi|cdp\b|msci\b|sustainalytics|ftse4good|peacock|yearbook|certified|certification|great place to work|accreditation)\b', re.IGNORECASE),
    re.compile(r'\b(p\s*a\s*g\s*e|contents|preface|data book|annual report|document no|declaration|compliances|notice of|general meeting|agm)\b', re.IGNORECASE),
    re.compile(r'\b(board/cmd|directors|remuneration|key managerial|policy on|terms of reference|committee|composition)\b', re.IGNORECASE),
    re.compile(r'\b(statement number|business responsibility|audit assurance|recommendations)\b', re.IGNORECASE),
    re.compile(r'^(we\s|the year was|further,\s*the company|in terms of|pursuant to|safety first|zero harm)', re.IGNORECASE),
]

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
            head_cl = None
            try:
                head_resp = requests.head(self.pdf_url, headers=headers, timeout=3, allow_redirects=True)
                cl_header = head_resp.headers.get('content-length')
                if cl_header:
                    head_cl = int(cl_header)
                    if head_cl > 3 * 1024 * 1024:
                        self.error_code = 'PDF_TOO_LARGE'
                        return []
            except Exception:
                pass

            resp = requests.get(self.pdf_url, headers=headers, timeout=4)
            self.http_status = resp.status_code

            if resp.status_code in (403, 429):
                self.error_code = 'BLOCKED'
                return []
            if not resp.ok:
                self.error_code = f'HTTP_{resp.status_code}'
                return []

            content = resp.content
            if len(content) > 3 * 1024 * 1024:
                self.error_code = 'PDF_TOO_LARGE'
                return []
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
            import logging
            logging.getLogger("pypdf").setLevel(logging.ERROR)
            reader = PdfReader(io.BytesIO(pdf_bytes), strict=False)
            num_pages = len(reader.pages)

            # Check up to first 4 pages with a strict 2-second time budget
            max_pages = min(num_pages, 4)
            import time as _t
            t_start = _t.time()

            for page_idx in range(max_pages):
                if _t.time() - t_start > 2:
                    break
                try:
                    page = reader.pages[page_idx]
                    text = page.extract_text() or ''
                except Exception:
                    continue
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
                    first_line = ' '.join(para.split('.')[0].split()).strip()
                    if len(first_line) < 15 or len(first_line) > 120:
                        # NEVER synthesize or make up titles - must be verbatim from source text
                        continue

                    # Filter out non-project table of contents, pagination, or remuneration sentences
                    if any(pat.search(first_line) for pat in PDF_JUNK_PATTERNS):
                        continue

                    # Budget detection - strictly requiring digits and never allowing malformed strings like 'rs,'
                    budget_val = None
                    budget_match = BUDGET_PATTERN.search(para)
                    if budget_match:
                        candidate_b = budget_match.group(0).strip()
                        if any(c.isdigit() for c in candidate_b) and candidate_b.lower() not in ('rs,', 'inr,', 'nan', 'none'):
                            budget_val = candidate_b

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
