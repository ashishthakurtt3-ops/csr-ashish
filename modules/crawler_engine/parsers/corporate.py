import re
import json
import urllib.parse
from bs4 import BeautifulSoup
from .base import BaseParser

CSR_THEMES = [
    ('Education & Skill Building', ['education', 'scholarship', 'school', 'literacy', 'learning', 'stem']),
    ('Healthcare & Community Well-being', ['healthcare', 'health', 'hospital', 'medical', 'nutrition', 'wellness']),
    ('Environmental Stewardship', ['environment', 'renewable', 'carbon', 'water', 'biodiversity', 'solar', 'green']),
    ('Rural & Community Empowerment', ['rural', 'community', 'livelihood', 'farmer', 'agriculture', 'village']),
    ('Women & Inclusive Growth', ['women', 'gender', 'empowerment', 'shg', 'inclusion', 'diversity']),
]

BUDGET_REGEX = re.compile(
    r'(?:INR|Rs\.?|₹)\s*([0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?)\s*(?:Cr(?:ore)?|Lakh|Million|Billion)?',
    re.IGNORECASE
)

# Reject headings that represent marketing slogans, awards, table of contents, or navigation
JUNK_CSR_TITLE_PATTERNS = [
    re.compile(r'initiative\s*[-—]\s*[A-Za-z]', re.IGNORECASE),
    re.compile(r'\b(award|awards|conclave|djsi|cdp\b|msci\b|sustainalytics|ftse4good|peacock|yearbook|certified|certification|great place to work|accreditation)\b', re.IGNORECASE),
    re.compile(r'\b(p\s*a\s*g\s*e|contents|preface|data book|annual report|document no|declaration|compliances|notice of|general meeting|agm|committee|composition|terms of reference)\b', re.IGNORECASE),
    re.compile(r'^(we\s|our\s(esg|efforts|initiatives|three|spirit)|about us|quick links|career|social$|sustainability$|safety first|zero harm)', re.IGNORECASE),
    re.compile(r'\b(calculator|predictor|store locator|workplace|networks|management framework)\b', re.IGNORECASE),
]

INDIAN_STATES = [
    'Maharashtra', 'Karnataka', 'Tamil Nadu', 'Gujarat', 'Uttar Pradesh',
    'Rajasthan', 'Madhya Pradesh', 'Telangana', 'Andhra Pradesh', 'West Bengal',
    'Bihar', 'Odisha', 'Kerala', 'Punjab', 'Haryana', 'Assam', 'Jharkhand'
]


class CorporateHTMLParser(BaseParser):
    def get_extraction_method(self):
        return "CORPORATE_HTML_EVIDENCE"

    def extract_company_details(self):
        soup = BeautifulSoup(self.html_content, 'lxml')
        title_tag = soup.find('title')
        title = title_tag.text.strip() if title_tag else None
        
        if title:
            clean_name = title.split('|')[0].split('-')[0].split('–')[0].strip()
            return {
                'company_name': clean_name,
                'evidence_text': str(title_tag)[:1000]
            }
        return None

    def extract_contacts(self):
        soup = BeautifulSoup(self.html_content, 'lxml')
        contacts = []
        seen = set()
        
        # Look for mailto links
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if href.lower().startswith('mailto:'):
                email = href.replace('mailto:', '').split('?')[0].strip().lower()
                # Basic email sanity check
                if email and '@' in email and '.' in email and len(email) < 120:
                    if email in seen:
                        continue
                    seen.add(email)

                    # Extract anchor context or surrounding text
                    parent_text = a.parent.get_text(strip=True) if a.parent else ''
                    dept = 'General'
                    if any(k in parent_text.lower() for k in ['csr', 'sustainability', 'foundation']):
                        dept = 'CSR & Sustainability'
                    elif any(k in parent_text.lower() for k in ['careers', 'recruitment', 'hr', 'jobs']):
                        dept = 'Human Resources / Talent'

                    contacts.append({
                        'email': email,
                        'name': None,     # Enforce NULL: personal names must not be guessed
                        'phone': None,    # Enforce NULL: phone numbers must not be guessed
                        'department': dept,
                        'evidence_text': f"Anchor: {str(a)[:500]} | Context: {parent_text[:300]}"
                    })

            elif href.lower().startswith('tel:'):
                phone = href.replace('tel:', '').strip()
                if phone and len(phone) >= 8 and len(phone) < 30:
                    if phone in seen:
                        continue
                    seen.add(phone)

                    parent_text = a.parent.get_text(strip=True) if a.parent else ''
                    contacts.append({
                        'email': None,
                        'name': None,
                        'phone': phone,
                        'department': None,
                        'evidence_text': f"Anchor: {str(a)[:500]} | Context: {parent_text[:300]}"
                    })
                    
        return contacts

    def extract_csr(self):
        soup = BeautifulSoup(self.html_content, 'lxml')
        csr_projects = []
        seen_titles = set()

        is_csr_page = any(k in self.url.lower() for k in ['csr', 'sustainability', 'foundation', 'community', 'esg', 'social-impact'])

        if not is_csr_page:
            # Check title
            title_tag = soup.find('title')
            title_str = title_tag.text.lower() if title_tag else ''
            if not any(k in title_str for k in ['csr', 'sustainability', 'foundation', 'community']):
                return []

        # 1. Search for initiative/project blocks or cards
        candidate_blocks = soup.find_all(
            ['div', 'section', 'article', 'li'], 
            class_=re.compile(r'(project|initiative|program|pillar|focus-area|card|impact)', re.IGNORECASE)
        )

        for block in candidate_blocks:
            h = block.find(['h2', 'h3', 'h4', 'h5', 'strong'])
            if not h:
                continue
            heading_text = ' '.join(h.get_text(strip=True).split())
            if len(heading_text) < 5 or len(heading_text) > 120 or heading_text in seen_titles:
                continue

            # Verify against non-project junk patterns (awards, slogans, templates, page artifacts)
            if any(pat.search(heading_text) for pat in JUNK_CSR_TITLE_PATTERNS):
                continue

            block_text = block.get_text(separator=' ', strip=True)
            if len(block_text) < 40:
                continue

            # Match theme
            matched_theme = 'Corporate Social Responsibility'
            for theme_name, kws in CSR_THEMES:
                if any(kw in block_text.lower() for kw in kws):
                    matched_theme = theme_name
                    break

            # Budget detection in block - strictly requiring digits and never allowing malformed strings like 'rs,'
            budget_val = None
            b_match = BUDGET_REGEX.search(block_text)
            if b_match:
                candidate_budget = b_match.group(0).strip()
                # Ensure candidate has actual numeric digits
                if any(c.isdigit() for c in candidate_budget) and candidate_budget.lower() not in ('rs,', 'inr,', 'nan', 'none'):
                    budget_val = candidate_budget

            # Location detection in block
            loc_val = None
            for st in INDIAN_STATES:
                if st.lower() in block_text.lower():
                    loc_val = st
                    break

            seen_titles.add(heading_text)
            csr_projects.append({
                'project_name': heading_text,
                'category': matched_theme,
                'description': block_text[:1200],
                'geographic_location': loc_val,  # Strictly NULL if not present in text
                'budget': budget_val,            # Strictly NULL if not present in text
                'evidence_text': str(block)[:2000]
            })

            if len(csr_projects) >= 15:
                break

        return csr_projects

    def extract_opportunities(self):
        soup = BeautifulSoup(self.html_content, 'lxml')
        opps = []
        seen_links = set()

        is_csr_page = any(k in self.url.lower() for k in ['csr', 'sustainability', 'foundation', 'grant', 'rfp', 'ngo'])
        if not is_csr_page:
            return []

        # Find links with grant, rfp, apply, proposal
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            text = a.get_text(separator=' ', strip=True)
            href_lower = href.lower()
            text_lower = text.lower()

            if any(k in href_lower or k in text_lower for k in ['grant', 'rfp', 'request for proposal', 'apply for funding', 'partner with us', 'eoi']):
                full_url = urllib.parse.urljoin(self.url, href)
                if full_url in seen_links:
                    continue
                seen_links.add(full_url)

                title_clean = text if len(text) > 8 and len(text) < 150 else f"CSR Partner Application / RFP - {self.company.company_name}"
                opp_type = "Grant / RFP" if any(k in text_lower or k in href_lower for k in ['grant', 'rfp']) else "NGO Partnership"

                opps.append({
                    'title': title_clean,
                    'opportunity_type': opp_type,
                    'portal_url': full_url,
                    'evidence_text': f"Link Tag: {str(a)[:500]} | Text: {text[:200]}"
                })

                if len(opps) >= 10:
                    break

        return opps
