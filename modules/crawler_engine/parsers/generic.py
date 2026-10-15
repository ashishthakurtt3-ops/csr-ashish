import json
import re
import urllib.parse
from bs4 import BeautifulSoup
from .base import BaseParser

NON_JOB_TITLES = {
    'home', 'about', 'about us', 'contact', 'contact us', 'privacy policy', 'terms',
    'careers', 'career', 'jobs', 'all jobs', 'search', 'search jobs', 'apply', 'apply now',
    'read more', 'view more', 'learn more', 'click here', 'login', 'sign in', 'register',
    'back', 'next', 'previous', 'cookie policy', 'sitemap', 'accessibility', 'overview',
    'life at', 'our culture', 'our values', 'our teams', 'work with us', 'join us',
    'students', 'graduates', 'experienced', 'faq', 'faqs', 'help', 'disclaimer',
    'fraud alert', 'recruitment fraud', 'caution notice', 'advisory', 'alert', 'fraudulent recruitment',
    'fake job offer', 'validate offer', 'warning', 'notice',
    'learning', 'development', 'leadership development', 'leadership development academy',
    'training', 'campus', 'benefits', 'perks', 'rewards', 'culture', 'diversity', 'inclusion'
}


JOB_URL_PATTERNS = [
    re.compile(r'/job[s]?/[\w\-]+', re.I),
    re.compile(r'/requisition[s]?/[\w\-]+', re.I),
    re.compile(r'/opening[s]?/[\w\-]+', re.I),
    re.compile(r'/position[s]?/[\w\-]+', re.I),
    re.compile(r'/vacancy[s]?/[\w\-]+', re.I),
    re.compile(r'/career[s]?/job[s]?/[\w\-]+', re.I),
    re.compile(r'/career[s]?/detail[s]?/[\w\-]+', re.I),
    re.compile(r'/career[s]?/apply/[\w\-]+', re.I),
    re.compile(r'[?&](?:job_?id|req_?id|jobId|reqId)=[\w\-]+', re.I),
]



class GenericHTMLParser(BaseParser):
    def get_extraction_method(self):
        return "GENERIC_HTML"

    def extract_jobs(self):
        jobs = []
        soup = BeautifulSoup(self.html_content, 'lxml')
        seen_titles = set()

        # 1. JSON-LD JobPosting Extraction (including nested @graph)
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                raw_text = script.string or ''
                if not raw_text.strip():
                    continue
                data = json.loads(raw_text)
                items_to_check = []
                if isinstance(data, dict):
                    if '@graph' in data and isinstance(data['@graph'], list):
                        items_to_check.extend(data['@graph'])
                    else:
                        items_to_check.append(data)
                elif isinstance(data, list):
                    items_to_check.extend(data)

                for item in items_to_check:
                    if not isinstance(item, dict):
                        continue
                    item_type = item.get('@type', '')
                    if item_type == 'JobPosting' or (isinstance(item_type, list) and 'JobPosting' in item_type):
                        title = item.get('title')
                        if not title or len(title.strip()) < 3:
                            continue
                        clean_title = title.strip()
                        if clean_title.lower() in NON_JOB_TITLES:
                            continue

                        desc = item.get('description', '')[:3000] if item.get('description') else None
                        loc_val = None
                        city_val = None
                        state_val = None
                        job_loc = item.get('jobLocation', {})
                        if isinstance(job_loc, dict):
                            addr = job_loc.get('address', {})
                            if isinstance(addr, dict):
                                city_val = addr.get('addressLocality')
                                state_val = addr.get('addressRegion')
                                loc_val = ', '.join(filter(None, [city_val, state_val, addr.get('addressCountry')]))
                        elif isinstance(job_loc, list) and job_loc:
                            addr = job_loc[0].get('address', {}) if isinstance(job_loc[0], dict) else {}
                            if isinstance(addr, dict):
                                city_val = addr.get('addressLocality')
                                state_val = addr.get('addressRegion')
                                loc_val = ', '.join(filter(None, [city_val, state_val, addr.get('addressCountry')]))

                        app_url = item.get('url') or self.final_url
                        if not app_url.startswith('http'):
                            app_url = urllib.parse.urljoin(self.final_url, app_url)

                        job_key = f"{clean_title}_{loc_val}"
                        if job_key in seen_titles:
                            continue
                        seen_titles.add(job_key)

                        jobs.append({
                            'title': clean_title,
                            'location': loc_val,
                            'city': city_val,
                            'state': state_val,
                            'employment_type': item.get('employmentType'),
                            'job_description': desc,
                            'posted_date': item.get('datePosted'),
                            'closing_date': item.get('validThrough'),
                            'department': item.get('occupationalCategory') or item.get('department'),
                            'work_mode': item.get('jobLocationType'),
                            'experience': None,
                            'skills': item.get('skills') if isinstance(item.get('skills'), str) else None,
                            'salary': None,
                            'application_url': app_url,
                            'source_url': self.final_url,
                            'evidence_text': json.dumps(item)[:2000]
                        })
            except Exception:
                pass

        if jobs:
            return jobs

        # 2. Schema.org Microdata Extraction (itemtype="http://schema.org/JobPosting")
        for container in soup.find_all(attrs={"itemtype": re.compile(r'schema\.org/JobPosting', re.I)}):
            title_el = container.find(attrs={"itemprop": "title"}) or container.find(['h1', 'h2', 'h3', 'h4'])
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or title.lower() in NON_JOB_TITLES or len(title) < 3:
                continue

            desc_el = container.find(attrs={"itemprop": "description"})
            desc = desc_el.get_text(separator='\n', strip=True)[:3000] if desc_el else None
            loc_el = container.find(attrs={"itemprop": "jobLocation"})
            loc = loc_el.get_text(strip=True) if loc_el else None
            link_el = container.find('a', href=True)
            app_url = urllib.parse.urljoin(self.final_url, link_el['href']) if link_el else self.final_url

            job_key = f"{title}_{loc}"
            if job_key in seen_titles:
                continue
            seen_titles.add(job_key)

            jobs.append({
                'title': title,
                'location': loc,
                'city': None,
                'state': None,
                'employment_type': None,
                'job_description': desc,
                'posted_date': None,
                'closing_date': None,
                'department': None,
                'work_mode': None,
                'experience': None,
                'skills': None,
                'salary': None,
                'application_url': app_url,
                'source_url': self.final_url,
                'evidence_text': str(container)[:2000]
            })

        if jobs:
            return jobs

        # 3. HTML Job Requisition Link Pattern Extraction
        # Finds direct links to job postings on corporate career portals
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if not href or href.startswith('#') or href.startswith('javascript'):
                continue
            full_url = urllib.parse.urljoin(self.final_url, href)

            # Check if href matches job URL patterns
            is_job_link = any(pat.search(href) for pat in JOB_URL_PATTERNS)
            if not is_job_link:
                continue

            text = a.get_text(strip=True)
            # Sometimes the link text is just "Apply" or an arrow, look inside parent
            if not text or len(text) < 4 or text.lower() in NON_JOB_TITLES:
                parent = a.find_parent(['li', 'tr', 'div', 'article'])
                if parent:
                    heading = parent.find(['h2', 'h3', 'h4', 'h5', 'strong', 'b'])
                    if heading:
                        text = heading.get_text(strip=True)

            if not text or len(text) < 4 or len(text) > 120 or text.lower() in NON_JOB_TITLES:
                continue

            # Skip numeric strings or dates
            if re.match(r'^\d+$', text) or re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', text):
                continue

            job_key = f"{text}_{full_url}"
            if job_key in seen_titles:
                continue
            seen_titles.add(job_key)

            # Extract nearby metadata (location / department) if present in parent container
            loc = None
            parent = a.find_parent(['li', 'tr', 'div', 'article'])
            if parent:
                parent_text = parent.get_text(separator=' | ', strip=True)
                # Check for standard Indian cities
                cities = ['Bengaluru', 'Bangalore', 'Mumbai', 'Pune', 'Hyderabad', 'Chennai', 'Delhi', 'Gurugram', 'Gurgaon', 'Noida', 'Kolkata', 'Ahmedabad', 'Remote']
                for c in cities:
                    if re.search(r'\b' + c + r'\b', parent_text, re.I):
                        loc = c
                        break

            jobs.append({
                'title': text,
                'location': loc,
                'city': loc,
                'state': None,
                'employment_type': None,
                'job_description': None,
                'posted_date': None,
                'closing_date': None,
                'department': None,
                'work_mode': None,
                'experience': None,
                'skills': None,
                'salary': None,
                'application_url': full_url,
                'source_url': self.final_url,
                'evidence_text': f"Job link extracted from: {href} | Text: {text}"
            })

            if len(jobs) >= 150:  # Safety cap per single page
                break

        if jobs:
            from .detail_extractor import UniversalJobDetailExtractor
            enriched_count = 0
            for job in jobs:
                app_url = job.get('application_url')
                if enriched_count < 30 and app_url and app_url.startswith('http') and not job.get('job_description'):
                    det = UniversalJobDetailExtractor.extract_from_url(app_url)
                    for k, v in det.items():
                        if v is not None and not job.get(k):
                            job[k] = v
                    job['detail_fetched'] = det.get('detail_fetched', True)
                    job['detail_fetch_status'] = det.get('detail_fetch_status', 'FETCHED')
                    enriched_count += 1
                else:
                    if not job.get('detail_fetched'):
                        job['detail_fetched'] = False
                        job['detail_fetch_status'] = job.get('detail_fetch_status') or 'NOT_FETCHED'

        return jobs

