"""
Universal Job Detail Extractor.

Retrieves, extracts, validates, and preserves the full set of job detail fields
from official employer career pages across all 200 companies and all ATS platforms
(SAP SuccessFactors CSB, Workday, Taleo, Oracle Cloud, Greenhouse, Lever, SmartRecruiters, Ashby, Generic HTML).

Strict Grounding Rule:
- Real source data only.
- Never guess, infer, estimate, or fabricate.
- If the source mentions a field, extract and preserve it.
- If the source truly omits a field after fetching, leave as None (frontend displays 'Not mentioned by source').
- If not fetched or failed, set detail_fetch_status accordingly.
"""

import json
import re
import urllib.parse
from bs4 import BeautifulSoup, Tag, NavigableString
from typing import Dict, Any, Optional, Tuple, List
import requests

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
}
REQUEST_TIMEOUT = 12


def safe_fetch(url: str) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    """Fetch URL safely and return (html_text, status_code, final_url)."""
    if not url or not url.startswith('http'):
        return None, None, None
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        return resp.text, resp.status_code, resp.url
    except Exception as e:
        return None, None, None


class UniversalJobDetailExtractor:
    """
    Universal extractor capable of parsing HTML and embedded structured data
    from any company career detail page.
    """

    @classmethod
    def extract_from_url(cls, detail_url: str, preloaded_html: Optional[str] = None) -> Dict[str, Any]:
        """Fetch detail URL (if needed) and extract all factual fields."""
        result: Dict[str, Any] = {
            'detail_fetch_status': 'NOT_FETCHED',
            'detail_fetched': False,
            'job_title': None,
            'external_job_id': None,
            'posted_date': None,
            'application_deadline': None,
            'closing_date': None,
            'location': None,
            'city': None,
            'state': None,
            'country': None,
            'pincode': None,
            'function': None,
            'business_unit': None,
            'department': None,
            'team': None,
            'pay_band': None,
            'salary': None,
            'salary_min': None,
            'salary_max': None,
            'salary_currency': None,
            'employment_type': None,
            'work_mode': None,
            'role_purpose': None,
            'responsibilities': None,
            'day_in_the_life': None,
            'qualifications': None,
            'preferred_qualifications': None,
            'education': None,
            'experience': None,
            'technical_skills': None,
            'behavioural_skills': None,
            'skills': None,
            'benefits': None,
            'employer_info': None,
            'job_description': None,
            'structured_details': {},
            'evidence_text': None,
            'source_url': detail_url,
            'final_url': detail_url,
        }

        if not detail_url or not detail_url.startswith('http'):
            result['detail_fetch_status'] = 'NOT_FETCHED'
            return result

        html = preloaded_html
        status_code = 200
        final_url = detail_url

        fetch_url = detail_url
        # Normalize SmartRecruiters web URLs to API endpoint
        sr_match = re.search(r'jobs\.smartrecruiters\.com/([^/]+)/(\d+)', detail_url)
        if sr_match:
            fetch_url = f"https://api.smartrecruiters.com/v1/companies/{sr_match.group(1)}/postings/{sr_match.group(2)}"

        # Normalize Lever web URLs to API endpoint
        lever_match = re.search(r'jobs\.lever\.co/([^/]+)/([a-f0-9\-]{36})', detail_url)
        if lever_match:
            fetch_url = f"https://api.lever.co/v0/postings/{lever_match.group(1)}/{lever_match.group(2)}"

        # Pre-emptive Oracle Cloud HCM REST API extraction (avoid fetching the SPA HTML)
        oc_preempt = re.search(r'oraclecloud\.com.*?/(?:CandidateExperience|hcmUI/CandidateExperience)/.*?/job/(\d+)', detail_url, re.I)
        if oc_preempt and not html:
            req_id = oc_preempt.group(1)
            netloc = urllib.parse.urlparse(detail_url).netloc
            api_url = f"https://{netloc}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?finder=ById;Id={req_id}"
            api_text, api_status, _ = safe_fetch(api_url)
            if api_status == 200 and api_text:
                try:
                    oc_data = json.loads(api_text)
                    if oc_data.get('items'):
                        result['final_url'] = detail_url
                        cls._extract_from_oracle_hcm_json(oc_data['items'][0], result, detail_url)
                        result['detail_fetched'] = True
                        result['detail_fetch_status'] = 'FETCHED'
                        return result
                except Exception:
                    pass

        if not html:
            html, status_code, final_url = safe_fetch(fetch_url)

        if not html or status_code not in (200, 201):
            if status_code in (404, 410, 403, 500, 502, 503):
                result['detail_fetch_status'] = 'SOURCE_UNAVAILABLE'
            else:
                result['detail_fetch_status'] = 'EXTRACTION_FAILED'
            return result

        result['final_url'] = final_url

        # Fallback: Check for Oracle Cloud Candidate Experience SPA in final_url
        oc_fallback = re.search(r'oraclecloud\.com.*?/(?:CandidateExperience|hcmUI/CandidateExperience)/.*?/job/(\d+)', final_url, re.I)
        if oc_fallback:
            req_id = oc_fallback.group(1)
            netloc = urllib.parse.urlparse(final_url).netloc
            api_url = f"https://{netloc}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails?finder=ById;Id={req_id}"
            api_text, api_status, _ = safe_fetch(api_url)
            if api_status == 200 and api_text:
                try:
                    oc_data = json.loads(api_text)
                    if oc_data.get('items'):
                        cls._extract_from_oracle_hcm_json(oc_data['items'][0], result, final_url)
                        result['detail_fetched'] = True
                        result['detail_fetch_status'] = 'FETCHED'
                        return result
                except Exception:
                    pass

        # Check if the fetched content is JSON (e.g. Lever API, SmartRecruiters API or other ATS REST API)
        trimmed = (html or '').strip()
        if (trimmed.startswith('{') or trimmed.startswith('[')):
            if 'lever.co' in final_url or 'lever.co' in fetch_url:
                try:
                    lever_data = json.loads(trimmed)
                    if isinstance(lever_data, dict):
                        cls._extract_from_lever_json(lever_data, result, final_url)
                        result['detail_fetched'] = True
                        result['detail_fetch_status'] = 'FETCHED'
                        return result
                except Exception:
                    pass

            if 'smartrecruiters' in final_url or 'smartrecruiters' in fetch_url or 'jobAd' in trimmed:
                try:
                    sr_data = json.loads(trimmed)
                    if isinstance(sr_data, dict):
                        cls._extract_from_smartrecruiters_json(sr_data, result, final_url)
                        result['detail_fetched'] = True
                        result['detail_fetch_status'] = 'FETCHED'
                        return result
                except Exception:
                    pass

        soup = BeautifulSoup(html, 'lxml')

        # Extract external job ID from URL if present
        id_match = re.search(r'/(?:job|requisition|postings|detail)/[^/]+/(\d{6,})', final_url, re.I)
        if not id_match:
            id_match = re.search(r'/(?:job|requisition|postings|detail)/(\d{6,})', final_url, re.I)
        if not id_match:
            id_match = re.search(r'[?&](?:job_?id|req_?id|jobId|reqId)=(\w+)', final_url, re.I)
        if id_match:
            result['external_job_id'] = id_match.group(1)

        # 1. Structured Data / JSON-LD Extraction (if present)
        cls._extract_json_ld(soup, result)

        # 2. ATS & Meta Tags Header Extraction (Title, Date, Location, Requisition)
        cls._extract_header_metadata(soup, html, result, final_url)

        # 3. Content Sections Extraction (CSB, Workday, Standard DOM)
        cls._extract_content_sections(soup, html, result)

        # 4. Clean up, normalization & assembly
        cls._finalize_extracted_data(result, html)

        # Check if meaningful extraction occurred
        has_content = bool(
            result['job_description'] or
            result['responsibilities'] or
            result['qualifications'] or
            result['role_purpose'] or
            result['location'] or
            result['posted_date']
        )
        if has_content:
            result['detail_fetched'] = True
            result['detail_fetch_status'] = 'FETCHED'
        else:
            result['detail_fetch_status'] = 'EXTRACTION_FAILED'

        return result

    @classmethod
    def _extract_json_ld(cls, soup: BeautifulSoup, result: Dict[str, Any]):
        """Parse schema.org JobPosting if present in ld+json."""
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                raw_text = script.string or script.get_text() or ''
                if not raw_text.strip():
                    continue
                data = json.loads(raw_text)
                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    if '@graph' in data and isinstance(data['@graph'], list):
                        items = data['@graph']
                    else:
                        items = [data]

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    itype = item.get('@type', '')
                    if itype == 'JobPosting' or (isinstance(itype, list) and 'JobPosting' in itype):
                        if not result['job_title'] and item.get('title'):
                            result['job_title'] = item.get('title').strip()
                        if not result['posted_date'] and item.get('datePosted'):
                            result['posted_date'] = str(item.get('datePosted')).strip()
                        if not result['closing_date'] and item.get('validThrough'):
                            result['closing_date'] = str(item.get('validThrough')).strip()
                        if not result['employment_type'] and item.get('employmentType'):
                            result['employment_type'] = str(item.get('employmentType')).strip()
                        if not result['department'] and item.get('occupationalCategory'):
                            result['department'] = str(item.get('occupationalCategory')).strip()

                        # Location
                        job_loc = item.get('jobLocation')
                        if isinstance(job_loc, dict):
                            addr = job_loc.get('address', {})
                            if isinstance(addr, dict):
                                loc_parts = [addr.get('addressLocality'), addr.get('addressRegion'), addr.get('addressCountry')]
                                loc_str = ', '.join([p for p in loc_parts if p])
                                if loc_str and not result['location']:
                                    result['location'] = loc_str
                                if not result['city'] and addr.get('addressLocality'):
                                    result['city'] = addr.get('addressLocality')
                                if not result['state'] and addr.get('addressRegion'):
                                    result['state'] = addr.get('addressRegion')
                                if not result['country'] and addr.get('addressCountry'):
                                    result['country'] = addr.get('addressCountry')
                                if not result['pincode'] and addr.get('postalCode'):
                                    result['pincode'] = addr.get('postalCode')

                        # Description
                        desc = item.get('description')
                        if desc and not result['job_description']:
                            desc_soup = BeautifulSoup(desc, 'lxml')
                            result['job_description'] = desc_soup.get_text(separator='\n', strip=True)

                        # Salary
                        base_sal = item.get('baseSalary')
                        if isinstance(base_sal, dict):
                            cur = base_sal.get('currency')
                            val = base_sal.get('value')
                            if isinstance(val, dict):
                                result['salary_min'] = val.get('minValue')
                                result['salary_max'] = val.get('maxValue')
                                result['salary_currency'] = cur
                                if result['salary_min'] and result['salary_max']:
                                    result['salary'] = f"{cur or ''} {result['salary_min']} - {result['salary_max']}".strip()
                        break
            except Exception:
                continue

    @classmethod
    def _extract_header_metadata(cls, soup: BeautifulSoup, html: str, result: Dict[str, Any], final_url: str):
        """Extract title, date, location, function, pay band from header metadata elements."""
        # Title
        if not result['job_title']:
            h1 = soup.find('h1', id=re.compile(r'job-?title', re.I)) or soup.find('h1', class_=re.compile(r'job-?title|title', re.I)) or soup.find('h1')
            if h1:
                t = h1.get_text(strip=True)
                if t and len(t) < 150:
                    result['job_title'] = t

        # Date
        if not result['posted_date']:
            date_el = soup.find(class_=re.compile(r'jobDate|posting-date|date-posted', re.I))
            if date_el:
                d_txt = date_el.get_text(strip=True)
                d_clean = re.sub(r'^(?:Date|Posted Date|Date Posted)\s*:\s*', '', d_txt, flags=re.I).strip()
                if d_clean:
                    result['posted_date'] = d_clean
            else:
                m = re.search(r'(?:Date|Posted Date):\s*([0-9]{1,2}\s+[A-Za-z]{3,9}\s+[0-9]{4})', html, re.I)
                if not m:
                    m = re.search(r'(?:Date|Posted Date):\s*([0-9]{4}-[0-9]{2}-[0-9]{2})', html, re.I)
                if not m:
                    m = re.search(r'(?:Date|Posted Date):\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4})', html, re.I)
                if m:
                    result['posted_date'] = m.group(1).strip()

        # Location
        if not result['location']:
            geo_el = soup.find(class_=re.compile(r'jobGeoLocation', re.I))
            if geo_el:
                result['location'] = geo_el.get_text(strip=True)
            else:
                loc_el = soup.find(class_=re.compile(r'jobLocation|job-location|location', re.I))
                if loc_el:
                    l_txt = loc_el.get_text(strip=True)
                    l_clean = re.sub(r'^(?:Location)\s*:\s*', '', l_txt, flags=re.I).strip()
                    if l_clean:
                        result['location'] = l_clean
                else:
                    m = re.search(r'Location:\s*([^\n\r<]{3,80})', html, re.I)
                    if m:
                        result['location'] = m.group(1).strip()

        # Parse location components if location string exists
        if result['location']:
            loc_str = result['location']
            # Pattern: "Raipur, CT, IN, 492001" or "Bengaluru, Karnataka, India"
            parts = [p.strip() for p in loc_str.split(',') if p.strip()]
            if len(parts) >= 1:
                result['city'] = parts[0]
            if len(parts) >= 2:
                result['state'] = parts[1]
            if len(parts) >= 3:
                # Check if third part is country code or name
                if re.match(r'^\d{6}$', parts[-1]):
                    result['pincode'] = parts[-1]
                    if len(parts) >= 4:
                        result['country'] = parts[-2]
                else:
                    result['country'] = parts[-1]

        # Function
        if not result['function']:
            m = re.search(r'(?:Function|Functional Area)\s*:\s*(?:</b>|</strong>)?\s*([^\r\n<]+)', html, re.I)
            if m:
                f_val = m.group(1).strip()
                if f_val and len(f_val) < 100:
                    result['function'] = f_val

        # Pay Band / Grade
        if not result['pay_band']:
            m = re.search(r'(?:Pay Band|Pay Grade|Salary Band|Job Band)\s*:\s*(?:</b>|</strong>)?\s*([^\r\n<]+)', html, re.I)
            if m:
                pb_val = m.group(1).strip()
                if pb_val and len(pb_val) < 100:
                    result['pay_band'] = pb_val

    @classmethod
    def _extract_content_sections(cls, soup: BeautifulSoup, html: str, result: Dict[str, Any]):
        """
        Extracts content sections by scanning the job container DOM.
        Maps headings to the appropriate normalized model fields.
        """
        # Find main content container
        container = (
            soup.find(class_=re.compile(r'jobDisplay|jobdescription|job-description|job-details|contentWrapper', re.I)) or
            soup.find('div', id=re.compile(r'content|job', re.I)) or
            soup.find('article') or
            soup.body
        )
        if not container:
            return

        sections: Dict[str, List[str]] = {}
        current_header: Optional[str] = None

        # Helper to determine if an element acts as a section header
        KNOWN_HEADERS = {
            'role summary', 'job summary', 'position summary', 'summary of role', 'about the role',
            'job purpose', 'position purpose', 'role & purpose', 'role and purpose', 'position overview',
            'job overview', 'overview', 'summary', 'essential duties and responsibilities',
            'essential duties', 'key responsibilities', 'responsibilities & key deliverables',
            'responsibilities', 'duties and responsibilities', 'duties', 'core responsibilities',
            'what you will do', 'what you\'ll do', 'key accountabilities', 'job responsibilities',
            'qualification and experience', 'qualifications and experience', 'academic qualification',
            'academic qualification & experience', 'education & experience', 'education and experience',
            'educational qualifications', 'educational qualification', 'required qualifications',
            'basic qualifications', 'minimum qualifications', 'qualifications & requirements',
            'qualifications', 'qualification', 'requirements', 'eligibility', 'competencies',
            'core competencies', 'behavioural skills', 'behavioral skills', 'technical skills',
            'technical knowledge', 'hard skills', 'skills & knowledge', 'skills', 'physical requirements',
            'benefits', 'what we offer', 'perks', 'compensation & benefits', 'about the company', 'about us'
        }

        for elem in container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b', 'p', 'ul', 'ol', 'div']):
            text = elem.get_text(strip=True)
            if not text:
                continue

            is_header = False
            norm_text = re.sub(r'[:\s]+$', '', text).lower().strip()

            # Standard headings
            if elem.name in ['h2', 'h3', 'h4', 'h5']:
                if len(text) < 70 and not elem.find_parent(['ul', 'ol']):
                    is_header = True
            elif elem.name in ['strong', 'b'] and len(text) < 60:
                parent = elem.parent
                if parent and parent.name in ['p', 'div'] and not elem.find_parent(['li', 'ul', 'ol']):
                    parent_text = parent.get_text(strip=True)
                    # If strong/b is the entirety of parent or parent starts with it
                    if parent_text == text or (len(parent_text) - len(text) < 5):
                        is_header = True
                    else:
                        inline_val = parent.get_text(separator=' ', strip=True)
                        if inline_val.startswith(text):
                            val = inline_val[len(text):].strip().lstrip(':').strip()
                            if val and len(val) < 200:
                                k = text.strip().rstrip(':')
                                sections[k] = [val]
            elif elem.name in ['p', 'div'] and not elem.find_parent(['ul', 'ol', 'table']):
                if len(text) < 60 and (norm_text in KNOWN_HEADERS or any(norm_text.startswith(h) for h in KNOWN_HEADERS if len(h) > 8)):
                    is_header = True

            if is_header:
                current_header = text.strip().rstrip(':')
                if current_header not in sections:
                    sections[current_header] = []
            else:
                if current_header and elem.name in ['p', 'ul', 'ol']:
                    p_text = elem.get_text(separator='\n', strip=True)
                    if p_text and p_text != current_header:
                        # Avoid duplicates
                        existing = "\n".join(sections[current_header])
                        if p_text not in existing:
                            sections[current_header].append(p_text)

        # Merge section parts into clean text
        cleaned_sections: Dict[str, str] = {}
        for h, parts in sections.items():
            content = "\n".join(parts).strip()
            if content:
                cleaned_sections[h] = content

        result['structured_details'] = cleaned_sections

        # Map sections to specific fields based on heading semantics
        for header, content in cleaned_sections.items():
            hl = header.lower().strip()

            # 1. Function
            if hl in ('function', 'functional area', 'job function'):
                result['function'] = content
                continue

            # 2. Pay Band / Grade
            if hl in ('pay band', 'pay grade', 'salary band', 'grade', 'job band', 'band'):
                result['pay_band'] = content
                continue

            # 3. Role / Role and purpose / Position Summary
            if any(kw in hl for kw in ['role', 'summary', 'overview', 'about the role', 'about the job', 'job purpose', 'purpose of the role']):
                if not result['role_purpose']:
                    result['role_purpose'] = content
                continue

            # 4. Responsibilities / Duties
            if any(kw in hl for kw in [
                'responsibilit', 'essential dut', 'what you will do', 'what you\'ll do',
                'duties', 'core responsibilit', 'key accountabilit', 'job responsibilit', 'deliverables'
            ]):
                if not result['responsibilities']:
                    result['responsibilities'] = content
                continue

            # 5. A Day in the life
            if any(kw in hl for kw in ['a day in the life', 'day in the life', 'typical day']):
                result['day_in_the_life'] = content
                continue

            # 6. Academic Qualification & Experience / Qualifications / Requirements
            if any(kw in hl for kw in [
                'qualification', 'academic qualification', 'education & experience', 'education and experience',
                'educational qualification', 'required qualification', 'basic qualification', 'minimum qualification',
                'eligibility', 'requirements', 'who you are', 'candidate profile', 'profile'
            ]):
                if not result['qualifications']:
                    result['qualifications'] = content
                # Also extract education and experience mentions if present in this block
                cls._extract_edu_exp_from_text(content, result)
                continue

            # 7. Education specific section
            if any(kw in hl for kw in ['education', 'academic', 'degree']):
                if not result['education']:
                    result['education'] = content
                continue

            # 8. Technical Skills/Knowledge
            if any(kw in hl for kw in ['technical skill', 'technical knowledge', 'hard skill', 'domain knowledge']):
                if not result['technical_skills']:
                    result['technical_skills'] = content
                continue

            # 9. Behavioural Skills / Soft Skills / Competencies
            if any(kw in hl for kw in ['competenc', 'behavioural skill', 'behavioral skill', 'soft skill', 'personal attributes', 'leadership attributes']):
                # Clean out noisy footer buttons / application text
                c_lines = [cl.strip() for cl in content.split('\n') if cl.strip()]
                clean_c = [cl for cl in c_lines if not any(b in cl.lower() for b in ['apply now', 'start applying', 'please wait', 'share this job', 'linkedin', '#li-']) and cl.lower() not in ('start', 'apply')]
                if clean_c and not result['behavioural_skills']:
                    result['behavioural_skills'] = '\n'.join(clean_c)
                continue

            # 10. Benefits / Perks
            if any(kw in hl for kw in ['benefits', 'what we offer', 'perks', 'compensation & benefits', 'why join']):
                result['benefits'] = content
                continue

            # 11. Employer / Company Information
            if any(kw in hl for kw in ['about hero', 'about lupin', 'about the company', 'about us', 'who we are', 'what will it be like to work for']):
                existing_emp = result['employer_info'] or ''
                result['employer_info'] = (existing_emp + '\n\n' + content).strip()
                continue

    @classmethod
    def _extract_edu_exp_from_text(cls, text: str, result: Dict[str, Any]):
        """Extract education credentials and experience duration from qualification text."""
        # 1. Look for specific degree pattern
        if not result['education']:
            deg_m = re.search(r'\b(PhD|Doctorate|MBA|B\.?Tech|M\.?Tech|B\.?E|B\.?Com|B\.?Sc|M\.?Sc|Bachelor(?:\'s)?|Master(?:\'s)?|Diploma|Graduat(?:e|ion))\b[^\n.;]*', text, re.I)
            if deg_m:
                result['education'] = deg_m.group(0).strip()

        # 2. Look for experience pattern e.g. "1-3 years", "1-3 yrs", "8-10 years"
        if not result['experience']:
            exp_m = re.search(r'(\d+(?:\s*[-–to]\s*\d+)?\s*\+?\s*(?:yrs|years?)(?:\s+(?:of\s+)?experience)?[^\n.;]*)', text, re.I)
            if exp_m:
                result['experience'] = exp_m.group(1).strip()

        # Fallback to lines if not matched above
        lines = [line.strip().lstrip('-•* ') for line in text.split('\n') if line.strip()]
        for line in lines:
            ll = line.lower()
            if not result['education'] and any(k in ll for k in ['mba', 'b.tech', 'm.tech', 'b.e', 'bachelor', 'master', 'graduate', 'degree', 'diploma', 'phd', 'ca ']):
                result['education'] = line
            if not result['experience'] and any(k in ll for k in ['exp', 'experience', 'yrs', 'years']):
                result['experience'] = line

    @classmethod
    def _finalize_extracted_data(cls, result: Dict[str, Any], html: str):
        """Combine skills and build full position description preserving all job sections."""
        # Check for genuine raw container description in HTML first
        if html and not result['job_description']:
            soup = BeautifulSoup(html, 'lxml')
            disp = (
                soup.find('span', class_=re.compile(r'jobdescription', re.I)) or
                soup.find('div', class_=re.compile(r'jobdescription', re.I)) or
                soup.find(class_=re.compile(r'\bjobdescription\b|\bjob-description\b', re.I)) or
                soup.find(class_=re.compile(r'jobDisplayShell|jobDisplay', re.I))
            )
            if disp:
                raw_t = disp.get_text(separator='\n', strip=True)
                if len(raw_t) > 80:
                    result['job_description'] = raw_t

        # If role_purpose is still empty, look at the start of job_description before any header
        if not result['role_purpose'] and result['job_description']:
            first_hdr_m = re.search(r'(?:^|\n)\s*(?:Essential\s*Duties|Key\s*Responsibilities|Responsibilities|Qualification|Requirements|Competencies)[:\s\n]+', result['job_description'], re.I)
            if first_hdr_m and first_hdr_m.start() > 30:
                intro = result['job_description'][:first_hdr_m.start()].strip()
                intro = re.sub(r'^(?:Job\s*Description|Role\s*Summary)[:\s\n]*', '', intro, flags=re.I).strip()
                if intro and len(intro) > 20:
                    result['role_purpose'] = intro

        # If any primary sections are still missing, extract from the full job_description text
        if result['job_description']:
            cls._extract_missing_sections_from_prose(result['job_description'], result)

        # Combine skills
        skill_parts = []
        if result['technical_skills']:
            tech_items = [re.sub(r'^[-•*]\s*', '', s).strip() for s in result['technical_skills'].split('\n') if s.strip()]
            skill_parts.extend(tech_items)
        if result['behavioural_skills']:
            beh_items = [re.sub(r'^[-•*]\s*', '', s).strip() for s in result['behavioural_skills'].split('\n') if s.strip()]
            skill_parts.extend(beh_items)

        if skill_parts and not result['skills']:
            result['skills'] = ', '.join(skill_parts)

        # Assemble Full Position Description if still missing
        if not result['job_description']:
            desc_sections = []
            if result['role_purpose']:
                desc_sections.append(f"ROLE & PURPOSE:\n{result['role_purpose']}")
            if result['day_in_the_life']:
                desc_sections.append(f"A DAY IN THE LIFE:\n{result['day_in_the_life']}")
            if result['responsibilities']:
                desc_sections.append(f"KEY RESPONSIBILITIES:\n{result['responsibilities']}")
            if result['qualifications']:
                desc_sections.append(f"QUALIFICATIONS & REQUIREMENTS:\n{result['qualifications']}")
            if result['technical_skills']:
                desc_sections.append(f"TECHNICAL SKILLS / KNOWLEDGE:\n{result['technical_skills']}")
            if result['behavioural_skills']:
                desc_sections.append(f"BEHAVIOURAL SKILLS:\n{result['behavioural_skills']}")
            if desc_sections:
                result['job_description'] = "\n\n".join(desc_sections)

    @classmethod
    def _extract_missing_sections_from_prose(cls, text: str, result: Dict[str, Any]):
        """Parse structured sections directly from text prose when DOM tags were flat or omitted."""
        if not text:
            return
        lines = [re.sub(r'[\uFFFD\x7f-\x9f]+', ' ', l).strip() for l in text.split('\n') if l.strip()]
        sections: Dict[str, List[str]] = {}
        current_key: Optional[str] = None

        header_patterns = [
            ('role_purpose', r'^(?:role\s*summary|job\s*summary|position\s*summary|about\s*the\s*role|job\s*purpose|position\s*overview|job\s*overview|overview|role\s*&\s*purpose)$'),
            ('responsibilities', r'^(?:essential\s*duties\s*and\s*responsibilities|essential\s*duties|key\s*responsibilities|responsibilities|what\s*you\s*will\s*do|what\s*you\'ll\s*do|duties\s*and\s*responsibilities|duties|core\s*responsibilities|key\s*accountabilities|job\s*responsibilities)$'),
            ('qualifications', r'^(?:qualification\s*and\s*experience|qualifications\s*and\s*experience|qualifications\s*&\s*requirements|required\s*qualifications|basic\s*qualifications|minimum\s*qualifications|educational\s*qualifications?|academic\s*qualifications?|qualifications|qualification|requirements|eligibility|candidate\s*profile)$'),
            ('education', r'^(?:education\s*and\s*experience|educational\s*qualifications?|academic\s*qualifications?|education)$'),
            ('technical_skills', r'^(?:technical\s*skills|technical\s*knowledge|hard\s*skills|domain\s*knowledge)$'),
            ('behavioural_skills', r'^(?:competencies|core\s*competencies|behavioural\s*skills|behavioral\s*skills|soft\s*skills|personal\s*attributes)$'),
        ]

        for line in lines:
            norm = re.sub(r'[:\s]+$', '', line).lower()
            matched_key = None
            for key, pat in header_patterns:
                if re.match(pat, norm):
                    matched_key = key
                    break
            if matched_key:
                current_key = matched_key
                if current_key not in sections:
                    sections[current_key] = []
            elif current_key:
                if any(b in norm for b in ['apply now', 'start applying', 'please wait', 'share this job', 'linkedin', '#li-']):
                    continue
                sections[current_key].append(line)
            else:
                if 'intro' not in sections:
                    sections['intro'] = []
                sections['intro'].append(line)

        # Populate missing target fields
        if not result['role_purpose']:
            if sections.get('role_purpose'):
                result['role_purpose'] = '\n'.join(sections['role_purpose']).strip()
            elif sections.get('intro'):
                intro_text = '\n'.join(sections['intro']).strip()
                if len(intro_text) > 25 and not any(h in intro_text.lower() for h in ['essential duties', 'key responsibilities']):
                    result['role_purpose'] = intro_text

        if not result['responsibilities'] and sections.get('responsibilities'):
            result['responsibilities'] = '\n'.join(sections['responsibilities']).strip()
            result['structured_details']['Key Responsibilities'] = result['responsibilities']

        if not result['qualifications'] and sections.get('qualifications'):
            result['qualifications'] = '\n'.join(sections['qualifications']).strip()
            result['structured_details']['Qualifications'] = result['qualifications']
            cls._extract_edu_exp_from_text(result['qualifications'], result)

        if not result['education'] and sections.get('education'):
            result['education'] = '\n'.join(sections['education']).strip()
            result['structured_details']['Education'] = result['education']

        if not result['technical_skills'] and sections.get('technical_skills'):
            result['technical_skills'] = '\n'.join(sections['technical_skills']).strip()
            result['structured_details']['Technical Skills'] = result['technical_skills']

        if (not result['behavioural_skills'] or len(result['behavioural_skills'].strip()) < 10) and sections.get('behavioural_skills'):
            result['behavioural_skills'] = '\n'.join(sections['behavioural_skills']).strip()
            result['structured_details']['Behavioural Skills'] = result['behavioural_skills']

        # Record evidence
        evidence = {
            'title': result['job_title'],
            'location': result['location'],
            'date': result['posted_date'],
            'function': result['function'],
            'pay_band': result['pay_band'],
            'sections_extracted': list(result['structured_details'].keys()),
        }
        result['evidence_text'] = json.dumps(evidence)

    @classmethod
    def _extract_from_smartrecruiters_json(cls, data: Dict[str, Any], result: Dict[str, Any], url: str):
        """Extract structured job details from SmartRecruiters API response."""
        result['job_title'] = data.get('name')
        result['external_job_id'] = data.get('refNumber') or data.get('id')
        if data.get('releasedDate'):
            result['posted_date'] = str(data['releasedDate'])[:10]
        
        loc = data.get('location') or {}
        city = loc.get('city')
        region = loc.get('region')
        country = loc.get('country')
        parts = [p for p in [city, region, country] if p]
        result['location'] = ', '.join(parts) if parts else None
        result['city'] = city
        result['state'] = region
        result['country'] = country
        
        type_info = data.get('typeOfEmployment')
        if isinstance(type_info, dict):
            result['employment_type'] = type_info.get('label')
        elif isinstance(type_info, str):
            result['employment_type'] = type_info

        job_ad = data.get('jobAd') or {}
        sections = job_ad.get('sections') or {}

        # 1. Company Description
        comp_sec = sections.get('companyDescription') or {}
        comp_text = comp_sec.get('text') or ''
        if comp_text:
            clean_comp = BeautifulSoup(comp_text, 'html.parser').get_text(separator='\n').strip()
            if clean_comp:
                result['employer_info'] = clean_comp
                result['structured_details']['Company Description'] = clean_comp

        # 2. Job Description
        jd_sec = sections.get('jobDescription') or {}
        jd_text = jd_sec.get('text') or ''
        if jd_text:
            clean_jd = BeautifulSoup(jd_text, 'html.parser').get_text(separator='\n').strip()
            result['job_description'] = clean_jd
            resp_match = re.search(r'(?:Roles\s*&\s*Responsibilities|Key\s*Responsibilities|Responsibilities)[:\s\n]+(.*)', clean_jd, re.I | re.S)
            if resp_match:
                result['responsibilities'] = resp_match.group(1).strip()
                result['structured_details']['Key Responsibilities'] = result['responsibilities']
                role_part = clean_jd[:resp_match.start()].strip()
                if role_part:
                    role_clean = re.sub(r'^(?:Job\s*Summary|Role\s*Summary)[:\s\n]*', '', role_part, flags=re.I).strip()
                    result['role_purpose'] = role_clean
                    result['structured_details']['Role & Purpose'] = role_clean
            else:
                result['role_purpose'] = clean_jd
                result['structured_details']['Role & Purpose'] = clean_jd

        # 3. Qualifications
        qual_sec = sections.get('qualifications') or {}
        qual_text = qual_sec.get('text') or ''
        if qual_text:
            clean_qual = BeautifulSoup(qual_text, 'html.parser').get_text(separator='\n').strip()
            result['qualifications'] = clean_qual
            result['structured_details']['Qualifications'] = clean_qual

            ed_match = re.search(r'(?:Educational\s*Qualification|Education)[:\s\n]+([^\n]+)', clean_qual, re.I)
            if ed_match:
                result['education'] = ed_match.group(1).strip()

            exp_match = re.search(r'(?:Work\s*Experience|Experience)[:\s\n]+([^\n]+)', clean_qual, re.I)
            if exp_match:
                result['experience'] = exp_match.group(1).strip()

            tech_match = re.search(r'Technical\s*Skills[:\s\n]+(.*?)(?=Behavioural\s*Skills|$)', clean_qual, re.I | re.S)
            if tech_match:
                result['technical_skills'] = tech_match.group(1).strip()
                result['structured_details']['Technical Skills'] = result['technical_skills']

            beh_match = re.search(r'Behavioural\s*Skills[:\s\n]+(.*)', clean_qual, re.I | re.S)
            if beh_match:
                result['behavioural_skills'] = beh_match.group(1).strip()
                result['structured_details']['Behavioural Skills'] = result['behavioural_skills']

        # 4. Additional Information
        add_sec = sections.get('additionalInformation') or {}
        add_text = add_sec.get('text') or ''
        if add_text:
            clean_add = BeautifulSoup(add_text, 'html.parser').get_text(separator='\n').strip()
            if clean_add:
                result['structured_details']['Additional Information'] = clean_add

        # Record evidence
        evidence = {
            'title': result['job_title'],
            'location': result['location'],
            'date': result['posted_date'],
            'sections_extracted': list(result['structured_details'].keys()),
        }
        result['evidence_text'] = json.dumps(evidence)

    @classmethod
    def _extract_from_oracle_hcm_json(cls, item: Dict[str, Any], result: Dict[str, Any], url: str):
        """Extract structured job details from Oracle HCM Cloud Candidate Experience JSON item."""
        result['job_title'] = item.get('Title')
        result['external_job_id'] = str(item.get('Id') or item.get('RequisitionId') or '')
        if item.get('ExternalPostedStartDate'):
            result['posted_date'] = str(item['ExternalPostedStartDate'])[:10]
        if item.get('ExternalPostedEndDate'):
            result['application_deadline'] = str(item['ExternalPostedEndDate'])[:10]
            result['closing_date'] = result['application_deadline']
        
        result['location'] = item.get('PrimaryLocation') or item.get('PrimaryLocationCountry')
        result['department'] = item.get('Category')
        result['function'] = item.get('JobFunction')
        result['employment_type'] = item.get('RequisitionType')
        result['education'] = item.get('StudyLevel')

        desc = item.get('ExternalDescriptionStr') or item.get('ShortDescriptionStr')
        if desc:
            clean_desc = BeautifulSoup(desc, 'html.parser').get_text(separator='\n').strip()
            if clean_desc:
                result['job_description'] = clean_desc
                result['structured_details']['Job Description'] = clean_desc
                result['responsibilities'] = clean_desc

        qual = item.get('ExternalQualificationsStr')
        if qual:
            clean_qual = BeautifulSoup(qual, 'html.parser').get_text(separator='\n').strip()
            if clean_qual:
                result['qualifications'] = clean_qual
                result['structured_details']['Qualifications'] = clean_qual

        corp = item.get('CorporateDescriptionStr') or item.get('OrganizationDescriptionStr')
        if corp:
            clean_corp = BeautifulSoup(corp, 'html.parser').get_text(separator='\n').strip()
            if clean_corp:
                result['employer_info'] = clean_corp
                result['structured_details']['Company Description'] = clean_corp

        # Record evidence
        evidence = {
            'title': result['job_title'],
            'location': result['location'],
            'date': result['posted_date'],
            'function': result['function'],
            'sections_extracted': list(result['structured_details'].keys()),
        }
        result['evidence_text'] = json.dumps(evidence)

    @classmethod
    def _extract_from_lever_json(cls, data: Dict[str, Any], result: Dict[str, Any], url: str):
        """Extract structured job details from Lever API response."""
        result['job_title'] = data.get('text')
        result['external_job_id'] = data.get('id')
        cats = data.get('categories') or {}
        result['department'] = cats.get('department')
        result['team'] = cats.get('team')
        result['function'] = cats.get('team') or cats.get('department')
        result['location'] = cats.get('location')
        result['employment_type'] = cats.get('commitment')
        result['work_mode'] = data.get('workplaceType')

        desc_raw = data.get('descriptionPlain') or data.get('description') or ''
        clean_desc = BeautifulSoup(desc_raw, 'html.parser').get_text(separator='\n').strip() if '<' in desc_raw else desc_raw.strip()
        result['job_description'] = clean_desc

        # Scan for semantic sections in description text
        role_m = re.search(r'(?:About the Role|Role Summary|Role & Purpose)[:\s\n]+(.*?)(?=(?:Key Responsibilities|Responsibilities|About the Team|Qualifications|What you\'ll do|$))', clean_desc, re.I | re.S)
        if role_m:
            result['role_purpose'] = role_m.group(1).strip()
            result['structured_details']['Role & Purpose'] = result['role_purpose']

        resp_m = re.search(r'(?:Key Responsibilities|Responsibilities|What You Will Do|What You\'ll Do)[:\s\n]+(.*?)(?=(?:Qualifications|Requirements|What You Need|About the Team|$))', clean_desc, re.I | re.S)
        if resp_m:
            result['responsibilities'] = resp_m.group(1).strip()
            result['structured_details']['Responsibilities'] = result['responsibilities']

        qual_m = re.search(r'(?:Qualifications|Requirements|What We Are Looking For|Must Have)[:\s\n]+(.*?)(?=(?:Benefits|What We Offer|About|$))', clean_desc, re.I | re.S)
        if qual_m:
            result['qualifications'] = qual_m.group(1).strip()
            result['structured_details']['Qualifications'] = result['qualifications']
            cls._extract_edu_exp_from_text(result['qualifications'], result)

        team_m = re.search(r'(?:About the Team|About Us|About Paytm|About Company)[:\s\n]+(.*?)(?=(?:About the Role|Key Responsibilities|$))', clean_desc, re.I | re.S)
        if team_m:
            result['employer_info'] = team_m.group(1).strip()
            result['structured_details']['Company Description'] = result['employer_info']

        lists = data.get('lists') or []
        for lst in lists:
            lst_title = lst.get('text') or ''
            lst_content = lst.get('content') or ''
            clean_lst = BeautifulSoup(lst_content, 'html.parser').get_text(separator='\n').strip() if '<' in lst_content else lst_content.strip()
            if lst_title and clean_lst:
                result['structured_details'][lst_title] = clean_lst
                lt_lower = lst_title.lower()
                if 'responsibilit' in lt_lower and not result['responsibilities']:
                    result['responsibilities'] = clean_lst
                elif ('qualificat' in lt_lower or 'requirement' in lt_lower) and not result['qualifications']:
                    result['qualifications'] = clean_lst
                    cls._extract_edu_exp_from_text(clean_lst, result)

        evidence = {
            'title': result['job_title'],
            'location': result['location'],
            'date': result['posted_date'],
            'function': result['function'],
            'sections_extracted': list(result['structured_details'].keys()),
        }
        result['evidence_text'] = json.dumps(evidence)


