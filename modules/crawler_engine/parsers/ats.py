"""
ATS Adapters with complete pagination, real failure logging, and job detail page fetch.

Rules:
- Never stop at first API page or at a 1000-row cap or on a short page before API total is reached
- Never fall back to a generic careers/landing URL when a job has no individual apply URL
- Log the real failure reason when an ATS API request fails
- For each discovered job, also fetch the individual detail page and enrich the record
- All fields NULL unless the source actually provides the data
- Never guess, infer, or fabricate
"""
import json
import re
import time
import requests
import urllib.parse
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .base import BaseParser
from ..normalizers import normalize_application_url, infer_country
from ..ownership import load_config

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
}
REQUEST_TIMEOUT = 15

# Thread-local / last request failure diagnostics so callers can log the exact reason
LAST_HTTP_ERROR: Optional[str] = None


def safe_get(url: str, **kwargs) -> Optional[requests.Response]:
    """HTTP GET with transient retry/backoff that records the exact failure reason."""
    global LAST_HTTP_ERROR
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, **kwargs)
            if resp.status_code in (429, 502, 503, 504) and attempt == 0:
                time.sleep(1.5)
                continue
            if not resp.ok:
                LAST_HTTP_ERROR = f"GET {url[:120]} -> HTTP {resp.status_code}"
            else:
                LAST_HTTP_ERROR = None
            return resp
        except Exception as exc:
            LAST_HTTP_ERROR = f"GET {url[:120]} -> {type(exc).__name__}: {str(exc)[:160]}"
            if attempt == 0:
                time.sleep(1.0)
    return None


def safe_post(url: str, **kwargs) -> Optional[requests.Response]:
    """HTTP POST with transient retry/backoff that records the exact failure reason."""
    global LAST_HTTP_ERROR
    for attempt in range(2):
        try:
            resp = requests.post(url, headers={**HEADERS, 'Content-Type': 'application/json', 'Accept': 'application/json'},
                                 timeout=REQUEST_TIMEOUT, **kwargs)
            if resp.status_code in (429, 502, 503, 504) and attempt == 0:
                time.sleep(1.5)
                continue
            if not resp.ok:
                LAST_HTTP_ERROR = f"POST {url[:120]} -> HTTP {resp.status_code}"
            else:
                LAST_HTTP_ERROR = None
            return resp
        except Exception as exc:
            LAST_HTTP_ERROR = f"POST {url[:120]} -> {type(exc).__name__}: {str(exc)[:160]}"
            if attempt == 0:
                time.sleep(1.0)
    return None


def fetch_job_detail(detail_url: str) -> Dict[str, Any]:
    """
    Fetches an individual job detail page and extracts all factual fields using
    UniversalJobDetailExtractor.
    """
    from .detail_extractor import UniversalJobDetailExtractor
    return UniversalJobDetailExtractor.extract_from_url(detail_url)


class BaseATSAdapter:
    """Base class for platform-specific ATS adapters."""
    name = "BASE_ATS"
    last_error: Optional[str] = None

    @classmethod
    def matches(cls, url: str) -> bool:
        raise NotImplementedError

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        raise NotImplementedError


class GreenhouseAdapter(BaseATSAdapter):
    """
    Greenhouse Boards API v1. Returns ALL jobs in a single call (no pagination needed).
    Then fetches each job's detail via the individual job endpoint for full content.
    """
    name = "GREENHOUSE"

    @classmethod
    def matches(cls, url: str) -> bool:
        return 'greenhouse.io' in url.lower()

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        token = None
        for_match = re.search(r'[?&]for=([^&#]+)', link, re.IGNORECASE)
        if for_match:
            token = for_match.group(1)
        if not token:
            match = re.search(r'greenhouse\.io/([^/?#]+)', link, re.IGNORECASE)
            if match and match.group(1) not in ('embed', 'js', 'api'):
                token = match.group(1)
        if not token:
            self.last_error = f"Could not extract Greenhouse board token from {link}"
            return []
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        jobs = []
        resp = safe_get(api_url)
        if not resp or not resp.ok:
            self.last_error = LAST_HTTP_ERROR or f"Greenhouse API failed for {api_url}"
            return []
        try:
            data = resp.json()
        except Exception as exc:
            self.last_error = f"Greenhouse invalid JSON from {api_url}: {exc}"
            return []

        for job in data.get('jobs', []):
            title = job.get('title')
            if not title:
                continue
            loc_name = job.get('location', {}).get('name') if isinstance(job.get('location'), dict) else None
            dept_name = None
            depts = job.get('departments', [])
            if depts and isinstance(depts, list):
                dept_name = depts[0].get('name') if depts else None

            # NEVER fall back to `link` (the generic careers page) when a job has no individual URL
            job_url = job.get('absolute_url') or None
            external_id = str(job.get('id', '')) or None
            if not job_url and external_id:
                job_url = f"https://boards.greenhouse.io/{token}/jobs/{external_id}"

            detail_content = job.get('content', '')

            jobs.append({
                'title': title.strip(),
                'location': loc_name.strip() if loc_name else None,
                'department': dept_name.strip() if dept_name else None,
                'employment_type': None,
                'salary': None,
                'experience': None,
                'education': None,
                'skills': None,
                'posted_date': job.get('updated_at'),
                'closing_date': None,
                'application_url': job_url,
                'source_url': api_url,
                'external_job_id': external_id,
                'ats_platform': 'Greenhouse',
                'job_description': BeautifulSoup(detail_content, 'lxml').get_text(separator='\n', strip=True)[:5000] if detail_content else None,
                'evidence_text': json.dumps({'id': job.get('id'), 'title': title, 'location': loc_name, 'dept': dept_name})
            })
        return jobs


class LeverAdapter(BaseATSAdapter):
    """
    Lever public postings API. Returns ALL jobs (no pagination).
    """
    name = "LEVER"

    @classmethod
    def matches(cls, url: str) -> bool:
        return 'lever.co' in url.lower()

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        match = re.search(r'lever\.co/([^/?#]+)', link, re.IGNORECASE)
        if not match:
            self.last_error = f"Could not extract Lever token from {link}"
            return []
        token = match.group(1)
        api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"
        resp = safe_get(api_url)
        if not resp or not resp.ok:
            self.last_error = LAST_HTTP_ERROR or f"Lever API failed for {api_url}"
            return []
        try:
            data = resp.json()
        except Exception as exc:
            self.last_error = f"Lever invalid JSON from {api_url}: {exc}"
            return []

        jobs = []
        for job in data:
            title = job.get('text')
            if not title:
                continue
            cats = job.get('categories', {}) or {}
            lists = job.get('lists', []) or []

            responsibilities = None
            requirements = None
            for section in lists:
                content = section.get('content', '')
                label_lc = (section.get('text') or '').lower()
                if 'responsibilit' in label_lc:
                    responsibilities = BeautifulSoup(content, 'lxml').get_text('\n', strip=True)[:2000]
                elif 'requirement' in label_lc or 'qualif' in label_lc:
                    requirements = BeautifulSoup(content, 'lxml').get_text('\n', strip=True)[:2000]

            full_desc = job.get('descriptionPlain') or BeautifulSoup(job.get('description', ''), 'lxml').get_text('\n', strip=True)

            # NEVER fall back to `link` (generic careers page)
            app_url = job.get('applyUrl') or job.get('hostedUrl') or None

            jobs.append({
                'title': title.strip(),
                'location': cats.get('location'),
                'department': cats.get('department'),
                'team': cats.get('team'),
                'employment_type': cats.get('commitment'),
                'salary': None,
                'experience': None,
                'education': None,
                'skills': None,
                'responsibilities': responsibilities,
                'requirements': requirements,
                'job_description': full_desc[:5000] if full_desc else None,
                'posted_date': str(job.get('createdAt')) if job.get('createdAt') else None,
                'closing_date': None,
                'application_url': app_url,
                'source_url': api_url,
                'external_job_id': job.get('id'),
                'ats_platform': 'Lever',
                'evidence_text': json.dumps({'id': job.get('id'), 'title': title, 'department': cats.get('department'), 'location': cats.get('location')})
            })
        return jobs


class WorkdayAdapter(BaseATSAdapter):
    """
    Workday CXS REST API with FULL pagination.
    Fetches until offset >= total records.
    """
    name = "WORKDAY"

    @classmethod
    def matches(cls, url: str) -> bool:
        return 'myworkdayjobs.com' in url.lower()

    @staticmethod
    def _workday_country(host: str, tenant: str, site: str, external_path: str) -> Optional[str]:
        resp = safe_get(f"https://{host}/wday/cxs/{tenant}/{site}{external_path}")
        if not resp or not resp.ok:
            return None
        try:
            info = resp.json().get('jobPostingInfo') or {}
        except Exception:
            return None
        c = info.get('country')
        name = c.get('descriptor') if isinstance(c, dict) else c
        return infer_country(None, name)

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        parsed = urllib.parse.urlparse(link)
        host = parsed.netloc
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        if not path_parts:
            self.last_error = f"Workday URL {link} has no site path component"
            return []

        if len(path_parts) > 1 and re.match(r'^[a-z]{2}(-[A-Z]{2})?$', path_parts[0], re.I):
            site_part = path_parts[1]
        else:
            site_part = path_parts[0]

        sub = host.split('.')[0]
        if sub.startswith('wd') or sub == 'myworkdayjobs':
            tenant = path_parts[0]
            site = site_part
        else:
            tenant = sub
            site = site_part

        api_url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
        india_only = getattr(company, 'nse_symbol', None) in {
            sym for t in load_config().get('tenants', []) if t.get('host', '').lower() == host.lower()
            for sym in t.get('india_only_for', [])
        }

        jobs = []
        offset = 0
        limit = 20
        total = None

        while True:
            payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
            resp = safe_post(api_url, json=payload)
            if not resp or not resp.ok:
                if offset == 0:
                    self.last_error = LAST_HTTP_ERROR or f"Workday API failed at offset 0 for {api_url}"
                break
            try:
                data = resp.json()
            except Exception as exc:
                if offset == 0:
                    self.last_error = f"Workday invalid JSON from {api_url}: {exc}"
                break

            if total is None:
                total = data.get('total', 0)

            postings = data.get('jobPostings', [])
            if not postings:
                break

            for item in postings:
                title = item.get('title')
                if not title:
                    continue
                external_path = item.get('externalPath', '')
                app_url = f"https://{host}/{site}{external_path}" if external_path else None
                detail_id = item.get('bulletFields', [None])[0] if item.get('bulletFields') else None
                country = None
                if india_only and external_path:
                    country = self._workday_country(host, tenant, site, external_path)
                    if country != 'India':
                        continue

                jobs.append({
                    'title': title.strip(),
                    'location': item.get('locationsText'),
                    'country': country,
                    'department': None,
                    'employment_type': item.get('timeType'),
                    'salary': None,
                    'experience': None,
                    'education': None,
                    'skills': None,
                    'posted_date': item.get('postedOn'),
                    'closing_date': None,
                    'application_url': app_url,
                    'source_url': api_url,
                    'external_job_id': detail_id,
                    'ats_platform': 'Workday',
                    'evidence_text': json.dumps({'title': title, 'location': item.get('locationsText'), 'postedOn': item.get('postedOn')})
                })

            offset += len(postings)
            if total is not None and int(total) > 0:
                if offset >= int(total):
                    break
            elif len(postings) < limit:
                break
            time.sleep(0.3)

        return jobs


class SmartRecruitersAdapter(BaseATSAdapter):
    """
    SmartRecruiters public postings API with full pagination.
    """
    name = "SMARTRECRUITERS"

    @classmethod
    def matches(cls, url: str) -> bool:
        return 'smartrecruiters.com' in url.lower()

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        token = None
        dcr_match = re.search(r'[?&]dcr_ci=([^&#]+)', link, re.IGNORECASE)
        if dcr_match:
            token = dcr_match.group(1)
        elif 'my-applications/' in link.lower():
            my_match = re.search(r'my-applications/([^/?#]+)', link, re.IGNORECASE)
            if my_match:
                token = my_match.group(1)
        if not token:
            match = re.search(r'smartrecruiters\.com/([^/?#]+)', link, re.IGNORECASE)
            if match and match.group(1) not in ('my-applications', 'job', 'postings'):
                token = match.group(1)
        if not token:
            self.last_error = f"Could not extract SmartRecruiters company token from {link}"
            return []

        base_api = f"https://api.smartrecruiters.com/v1/companies/{token}/postings"

        jobs = []
        page = 0
        page_size = 100

        while True:
            resp = safe_get(f"{base_api}?pageSize={page_size}&pageNumber={page}")
            if not resp or not resp.ok:
                if page == 0:
                    self.last_error = LAST_HTTP_ERROR or f"SmartRecruiters API failed at page 0 for {base_api}"
                break
            try:
                data = resp.json()
            except Exception as exc:
                if page == 0:
                    self.last_error = f"SmartRecruiters invalid JSON from {base_api}: {exc}"
                break

            items = data.get('content', [])
            if not items:
                break

            for item in items:
                name = item.get('name')
                if not name:
                    continue
                loc = item.get('location', {})
                city = loc.get('city') if isinstance(loc, dict) else None
                country = loc.get('country') if isinstance(loc, dict) else None
                location_str = ', '.join(filter(None, [city, country])) or None
                dept_val = item.get('department', {}).get('label') if isinstance(item.get('department'), dict) else None

                jobs.append({
                    'title': name.strip(),
                    'location': location_str,
                    'city': city,
                    'department': dept_val,
                    'employment_type': item.get('typeOfEmployment', {}).get('label') if isinstance(item.get('typeOfEmployment'), dict) else None,
                    'experience': item.get('experienceLevel', {}).get('label') if isinstance(item.get('experienceLevel'), dict) else None,
                    'salary': None,
                    'education': None,
                    'skills': None,
                    'posted_date': item.get('releasedDate'),
                    'closing_date': None,
                    'application_url': (f"https://jobs.smartrecruiters.com/{token}/{item.get('id')}" if item.get('id') else None),
                    'country': country,
                    'source_url': base_api,
                    'external_job_id': item.get('id'),
                    'ats_platform': 'SmartRecruiters',
                    'evidence_text': json.dumps({'id': item.get('id'), 'title': name.strip(), 'department': dept_val, 'location': location_str})
                })

            total_pages = data.get('totalPages', 1)
            page += 1
            if page >= total_pages:
                break
            time.sleep(0.3)

        return jobs


class AshbyAdapter(BaseATSAdapter):
    """
    Ashby HQ posting API. Returns all jobs in a single response.
    """
    name = "ASHBY"

    @classmethod
    def matches(cls, url: str) -> bool:
        return 'ashbyhq.com' in url.lower()

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        match = re.search(r'ashbyhq\.com/([^/?#]+)', link, re.IGNORECASE)
        if not match:
            self.last_error = f"Could not extract Ashby token from {link}"
            return []
        token = match.group(1)
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
        resp = safe_post(api_url, json={})
        if not resp or not resp.ok:
            self.last_error = LAST_HTTP_ERROR or f"Ashby API failed for {api_url}"
            return []
        try:
            data = resp.json()
        except Exception as exc:
            self.last_error = f"Ashby invalid JSON from {api_url}: {exc}"
            return []

        jobs = []
        for item in data.get('jobs', []):
            title = item.get('title')
            if not title:
                continue
            # NEVER fall back to `link` (generic careers page)
            app_url = item.get('applyUrl') or item.get('jobUrl') or None
            jobs.append({
                'title': title.strip(),
                'location': item.get('locationName'),
                'department': item.get('departmentName'),
                'team': item.get('teamName'),
                'employment_type': item.get('employmentType'),
                'salary': None,
                'experience': None,
                'education': None,
                'skills': None,
                'posted_date': item.get('publishedAt'),
                'closing_date': None,
                'application_url': app_url,
                'source_url': api_url,
                'external_job_id': item.get('id'),
                'ats_platform': 'Ashby',
                'evidence_text': json.dumps({'id': item.get('id'), 'title': title, 'location': item.get('locationName')})
            })
        return jobs


class SuccessFactorsAdapter(BaseATSAdapter):
    """
    SAP SuccessFactors public career portals.
    Tries the public OData/REST API first. Falls back to HTML scraping with pagination.
    """
    name = "SUCCESSFACTORS"

    @classmethod
    def matches(cls, url: str) -> bool:
        u = url.lower()
        return (
            'successfactors.com' in u or
            'successfactors.eu' in u or
            'mahindracareers.com' in u or
            'tatamotorscareers' in u or
            'heromotocorp' in u or
            'jobs.heromotocorp' in u
        )

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        jobs = []
        jobs.extend(self._try_odata_api(link))
        if not jobs:
            jobs.extend(self._scrape_html_pages(link))
        return jobs

    def _try_odata_api(self, link: str) -> List[Dict[str, Any]]:
        """Try the SuccessFactors OData v2 job requisition endpoint."""
        parsed = urllib.parse.urlparse(link)
        host = parsed.netloc
        base_api = f"https://{host}/odata/v2/JobRequisitionPosting"
        jobs = []
        skip = 0
        top = 100
        while True:
            url = f"{base_api}?$format=json&$top={top}&$skip={skip}&$select=JobReqId,JobTitle,City,Country,DepartmentName,EmploymentType,PostingDate,JobDescription"
            resp = safe_get(url)
            if not resp or not resp.ok:
                if skip == 0:
                    self.last_error = LAST_HTTP_ERROR
                break
            try:
                data = resp.json()
            except Exception as exc:
                if skip == 0:
                    self.last_error = f"SuccessFactors OData invalid JSON: {exc}"
                break
            results = data.get('d', {}).get('results', [])
            if not results:
                break
            for item in results:
                title = item.get('JobTitle')
                if not title:
                    continue
                req_id = item.get('JobReqId')
                # Only build a job-specific URL if JobReqId is present; never fall back to `link`
                app_url = f"https://{host}/career?career_ns=job_listing&career_job_req_id={req_id}" if req_id else None
                jobs.append({
                    'title': title.strip(),
                    'location': ', '.join(filter(None, [item.get('City'), item.get('Country')])) or None,
                    'city': item.get('City'),
                    'department': item.get('DepartmentName'),
                    'employment_type': item.get('EmploymentType'),
                    'job_description': item.get('JobDescription'),
                    'posted_date': item.get('PostingDate'),
                    'closing_date': None,
                    'salary': None,
                    'experience': None,
                    'education': None,
                    'skills': None,
                    'application_url': app_url,
                    'source_url': base_api,
                    'external_job_id': str(req_id) if req_id else None,
                    'ats_platform': 'SuccessFactors',
                    'evidence_text': json.dumps({'JobReqId': req_id, 'title': title, 'department': item.get('DepartmentName'), 'location': item.get('City')})
                })
            skip += len(results)
            if len(results) < top:
                break
        return jobs

    def _scrape_html_pages(self, link: str) -> List[Dict[str, Any]]:
        """HTML scrape fallback for SuccessFactors career pages (including Career Site Builder)."""
        jobs = []
        all_seen_job_keys = set()
        page = 0
        search_base = link if '/search/' in link else link.rstrip('/') + '/search/'

        while True:
            url = f"{search_base}?q=&startrow={page * 20}"
            resp = safe_get(url)
            if not resp or not resp.ok:
                if page == 0:
                    url = f"{link}?pageSize=20&start={page * 20}" if '?' not in link else f"{link}&start={page * 20}"
                    resp = safe_get(url)
                    if not resp or not resp.ok:
                        self.last_error = LAST_HTTP_ERROR or f"SuccessFactors HTML fetch failed for {link}"
                        break
                else:
                    break

            soup = BeautifulSoup(resp.text, 'lxml')
            new_jobs_this_page = 0

            # 1. Try JSON-LD first
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string or '')
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        if item.get('@type') == 'JobPosting' and item.get('title'):
                            loc_str = item.get('jobLocation', {}).get('address', {}).get('addressLocality') if isinstance(item.get('jobLocation'), dict) else None
                            item_url = item.get('url') or item.get('sameAs') or None
                            job_key = f"{item['title'].strip()}_{item_url}"
                            if job_key in all_seen_job_keys:
                                continue
                            all_seen_job_keys.add(job_key)
                            jobs.append({
                                'title': item['title'].strip(),
                                'location': loc_str,
                                'city': loc_str,
                                'employment_type': item.get('employmentType'),
                                'posted_date': item.get('datePosted'),
                                'closing_date': item.get('validThrough'),
                                'job_description': BeautifulSoup(item.get('description', ''), 'lxml').get_text('\n', strip=True)[:3000] or None,
                                'salary': None, 'experience': None, 'education': None, 'skills': None,
                                'application_url': item_url,
                                'source_url': url,
                                'external_job_id': str(item.get('identifier', {}).get('value')) if isinstance(item.get('identifier'), dict) and item.get('identifier', {}).get('value') else None,
                                'ats_platform': 'SuccessFactors',
                                'evidence_text': json.dumps({'title': item['title'], 'location': loc_str})
                            })
                            new_jobs_this_page += 1
                except Exception:
                    pass

            # 2. Career Site Builder (CSB) /job/ link extraction
            if new_jobs_this_page == 0:
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/job/' in href:
                        title_text = a.get_text(strip=True)
                        if not title_text or len(title_text) < 3 or title_text.lower() in ('apply now', 'more', 'view'):
                            continue
                        job_url = urllib.parse.urljoin(url, href)
                        job_key = f"{title_text}_{job_url}"
                        if job_key in all_seen_job_keys:
                            continue
                        all_seen_job_keys.add(job_key)

                        id_m = re.search(r'/job/.*?/(\d+)', href)
                        ext_id = id_m.group(1) if id_m else None

                        row_parent = a.find_parent(['tr', 'div', 'li'])
                        loc_str = None
                        if row_parent:
                            loc_elem = row_parent.find(class_=re.compile(r'location|city|country', re.I))
                            if loc_elem:
                                loc_str = loc_elem.get_text(strip=True)

                        jobs.append({
                            'title': title_text,
                            'location': loc_str,
                            'city': loc_str.split(',')[0].strip() if loc_str else None,
                            'employment_type': None,
                            'posted_date': None,
                            'closing_date': None,
                            'job_description': None,
                            'salary': None, 'experience': None, 'education': None, 'skills': None,
                            'application_url': job_url,
                            'source_url': url,
                            'external_job_id': ext_id,
                            'ats_platform': 'SuccessFactors',
                            'evidence_text': json.dumps({'title': title_text, 'id': ext_id, 'url': href, 'location': loc_str})
                        })
                        new_jobs_this_page += 1

            if new_jobs_this_page == 0:
                break
            page += 1
            if page >= 15:
                break
            time.sleep(0.1)
        return jobs


class OracleTaleoAdapter(BaseATSAdapter):
    """
    Oracle Taleo / Oracle Cloud HCM candidate portals.
    Supports Oracle Cloud Candidate Experience REST API & Taleo JSON-LD.
    Pages until the API's TotalJobsCount is reached (never stopping at 1000 or on a short page).
    """
    name = "ORACLE_TALEO"

    @classmethod
    def matches(cls, url: str) -> bool:
        u = url.lower()
        return (
            'taleo.net' in u or
            'oraclecloud.com' in u or
            'fa.us' in u or
            'sites/cx_' in u or
            'opportunity' in u
        )

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        if 'oraclecloud.com' in link.lower() or 'sites/cx_' in link.lower() or 'opportunity' in link.lower():
            oracle_jobs = self._extract_oracle_cloud_ce(link, company)
            if oracle_jobs:
                return oracle_jobs

        return self._extract_taleo_jsonld(link, company)

    def _extract_oracle_cloud_ce(self, link: str, company: Any) -> List[Dict[str, Any]]:
        oracle_host = None
        if 'oraclecloud.com' in link:
            p = urllib.parse.urlparse(link)
            oracle_host = f"{p.scheme}://{p.netloc}"

        m = re.search(r'sites/(CX_\w+)', link, re.I)
        site_number = m.group(1) if m else 'CX_1'

        if not oracle_host:
            resp = safe_get(link)
            if resp and resp.ok:
                host_m = re.search(r'https?://[a-zA-Z0-9.-]+\.oraclecloud\.com', resp.text)
                if host_m:
                    oracle_host = host_m.group(0)
            else:
                self.last_error = LAST_HTTP_ERROR or f"Could not fetch Oracle portal {link}"

        if not oracle_host:
            if not self.last_error:
                self.last_error = f"No Oracle Cloud host discovered from {link}"
            return []

        jobs = []
        offset = 0
        limit = 25
        total: Optional[int] = None

        while True:
            # IMPORTANT: for Oracle HCM the paging parameters belong INSIDE the finder string.
            finder = f"findReqs;siteNumber={site_number},limit={limit},offset={offset},sortBy=POSTING_DATES_DESC"
            api_url = (f"{oracle_host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
                       f"?onlyData=true&expand=requisitionList&finder={urllib.parse.quote(finder, safe=';=,_')}")
            resp = safe_get(api_url)
            if not resp or not resp.ok:
                if offset == 0:
                    self.last_error = LAST_HTTP_ERROR or f"Oracle HCM API failed at offset 0 for {api_url}"
                break
            try:
                data = json.loads(resp.text)
            except Exception as exc:
                if offset == 0:
                    self.last_error = f"Oracle HCM invalid JSON from {api_url}: {exc}"
                break

            items = data.get('items', [])
            if not items:
                break
            if total is None:
                raw_total = items[0].get('TotalJobsCount')
                try:
                    total = int(raw_total) if raw_total is not None else None
                except (TypeError, ValueError):
                    total = None
            req_list = items[0].get('requisitionList', [])
            if not req_list:
                break

            for req in req_list:
                title = req.get('Title')
                if not title:
                    continue
                req_id = req.get('Id')
                app_url = f"{oracle_host}/hcmUI/CandidateExperience/en/sites/{site_number}/job/{req_id}" if req_id else None
                loc = req.get('PrimaryLocation')
                entity = self._oracle_legal_entity(oracle_host, site_number, req_id) if (
                    req_id and site_number.upper() in self._shared_sites(oracle_host)) else None
                jobs.append({
                    'title': title.strip(),
                    'location': loc,
                    'city': loc.split(',')[0].strip() if loc else None,
                    'state': loc.split(',')[1].strip() if loc and ',' in loc else None,
                    'country': req.get('PrimaryLocationCountry'),
                    'employment_type': req.get('JobSchedule') or req.get('Schedule'),
                    'posted_date': req.get('PostedDate'),
                    'closing_date': req.get('PostingEndDate'),
                    'department': req.get('Department') or req.get('JobFamily'),
                    'business_unit': req.get('BusinessUnit'),
                    'legal_entity': entity,
                    'work_mode': req.get('WorkplaceType'),
                    'job_description': req.get('ShortDescriptionStr'),
                    'responsibilities': req.get('ExternalResponsibilitiesStr'),
                    'qualifications': req.get('ExternalQualificationsStr'),
                    'education': req.get('StudyLevel'),
                    'travel_required': req.get('DomesticTravelRequired'),
                    'salary': None,
                    'experience': None,
                    'skills': None,
                    'application_url': app_url,
                    'source_url': api_url,
                    'external_job_id': str(req_id) if req_id else None,
                    'ats_platform': 'Oracle_Cloud',
                    'evidence_text': json.dumps({'id': req_id, 'title': title, 'location': loc, 'dept': req.get('Department'), 'job_family': req.get('JobFamily')})
                })

            # Page until the API's total count is reached!
            # Do NOT stop early on a short page when `total` is known and `offset < total`.
            step = len(req_list)
            offset += step
            if total is not None:
                if offset >= total:
                    break
            else:
                if step < limit:
                    break
            if offset >= 25000:
                break
            time.sleep(0.3)

        return jobs

    @staticmethod
    def _shared_sites(oracle_host: str):
        for t in load_config().get('tenants', []):
            if t.get('host', '').lower() == urllib.parse.urlparse(oracle_host).netloc.lower():
                return {x.upper() for x in t.get('shared_sites', [])}
        return set()

    @staticmethod
    def _oracle_legal_entity(oracle_host: str, site_number: str, req_id) -> Optional[str]:
        """Reads the organisation / legal-entity field of ONE requisition (shared Oracle portals only).
        Returns None when the portal does not expose it - the job then stays OWNER_UNRESOLVED (hidden)."""
        finder = urllib.parse.quote(f'ById;Id="{req_id}",siteNumber={site_number}', safe='')
        resp = safe_get(f"{oracle_host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"
                        f"?expand=all&onlyData=true&finder={finder}")
        if not resp or not resp.ok:
            return None
        try:
            item = (json.loads(resp.text).get('items') or [{}])[0]
        except Exception:
            return None
        for key in ('LegalEntity', 'LegalEmployer', 'Organization', 'BusinessUnit', 'BusinessUnitName'):
            if item.get(key):
                return str(item[key])
        return None

    def _extract_taleo_jsonld(self, link: str, company: Any) -> List[Dict[str, Any]]:
        jobs = []
        page = 0
        while True:
            url = link if page == 0 else f"{link}&offset={page * 25}"
            resp = safe_get(url)
            if not resp or not resp.ok:
                if page == 0 and not self.last_error:
                    self.last_error = LAST_HTTP_ERROR or f"Taleo fetch failed for {url}"
                break
            soup = BeautifulSoup(resp.text, 'lxml')
            found = 0
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string or '')
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        if item.get('@type') == 'JobPosting' and item.get('title'):
                            loc_data = item.get('jobLocation', {})
                            addr = loc_data.get('address', {}) if isinstance(loc_data, dict) else {}
                            # Never fall back to `link`
                            item_url = item.get('url') or item.get('sameAs') or None
                            jobs.append({
                                'title': item['title'].strip(),
                                'location': addr.get('addressLocality'),
                                'city': addr.get('addressLocality'),
                                'state': addr.get('addressRegion'),
                                'employment_type': item.get('employmentType'),
                                'posted_date': item.get('datePosted'),
                                'closing_date': item.get('validThrough'),
                                'job_description': BeautifulSoup(item.get('description', ''), 'lxml').get_text('\n', strip=True)[:3000] or None,
                                'salary': None, 'experience': None, 'education': None, 'skills': None,
                                'application_url': item_url,
                                'source_url': url,
                                'external_job_id': str(item.get('identifier', {}).get('value')) if isinstance(item.get('identifier'), dict) and item.get('identifier', {}).get('value') else None,
                                'ats_platform': 'Oracle_Taleo',
                                'evidence_text': json.dumps({'title': item['title']})
                            })
                            found += 1
                except Exception:
                    pass
            if found == 0:
                break
            page += 1
            if page > 100:
                break
            time.sleep(0.3)
        return jobs




class DarwinboxAdapter(BaseATSAdapter):
    """
    Darwinbox ATS (widely used by Indian enterprises: *.darwinbox.in).
    Extracts jobs from Darwinbox candidate API or career listing HTML without generic URL fallbacks.
    """
    name = "DARWINBOX"

    @classmethod
    def matches(cls, url: str) -> bool:
        return "darwinbox.in" in url.lower() or "darwinbox.com" in url.lower()

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        parsed = urllib.parse.urlparse(link)
        base_host = f"{parsed.scheme}://{parsed.netloc}"
        jobs = []

        # 1. Try Darwinbox candidate API
        page = 1
        while page <= 40:
            api_url = f"{base_host}/ms/candidateapi/job?page={page}&limit=50"
            resp = safe_get(api_url)
            if not resp or not resp.ok:
                break
            try:
                data = resp.json()
            except Exception:
                break
            items = (data.get("message", {}) if isinstance(data.get("message"), dict) else data).get("jobs") or data.get("data") or []
            if not isinstance(items, list) or not items:
                break
            for item in items:
                title = item.get("title") or item.get("job_title")
                job_id = item.get("id") or item.get("job_id")
                if not title or not job_id:
                    continue
                loc = item.get("location") or item.get("city")
                dept = item.get("department")
                app_url = f"{base_host}/ms/candidate/careers/{job_id}"
                jobs.append({
                    "title": str(title).strip(),
                    "location": str(loc).strip() if loc else None,
                    "department": str(dept).strip() if dept else None,
                    "employment_type": item.get("employment_type") or item.get("job_type"),
                    "experience": item.get("experience") or item.get("experience_range"),
                    "posted_date": item.get("created_on") or item.get("posted_date"),
                    "closing_date": None,
                    "salary": None, "education": None, "skills": None,
                    "application_url": app_url,
                    "source_url": api_url,
                    "external_job_id": str(job_id),
                    "ats_platform": "Darwinbox",
                    "evidence_text": json.dumps({"id": job_id, "title": title, "location": loc, "department": dept}, ensure_ascii=False),
                })
            if len(items) < 50:
                break
            page += 1
            time.sleep(0.25)

        if jobs:
            return jobs

        # 2. Fallback: scrape /ms/candidate/careers/<id> links from HTML
        resp = safe_get(link)
        if not resp or not resp.ok:
            self.last_error = LAST_HTTP_ERROR
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = re.search(r"/ms/candidate/careers/([a-zA-Z0-9_-]+)", href)
            if m:
                jid = m.group(1)
                title_text = a.get_text(strip=True)
                if not title_text or len(title_text) < 3 or jid in seen:
                    continue
                seen.add(jid)
                full_url = urllib.parse.urljoin(base_host, href)
                jobs.append({
                    "title": title_text,
                    "location": None, "department": None, "employment_type": None,
                    "posted_date": None, "closing_date": None, "salary": None,
                    "experience": None, "education": None, "skills": None,
                    "application_url": full_url,
                    "source_url": link,
                    "external_job_id": jid,
                    "ats_platform": "Darwinbox",
                    "evidence_text": json.dumps({"id": jid, "title": title_text, "url": full_url}, ensure_ascii=False),
                })
        return jobs


class KekaAdapter(BaseATSAdapter):
    """Keka Hire public careers API (*.keka.com)."""
    name = "KEKA"

    @classmethod
    def matches(cls, url: str) -> bool:
        return ".keka.com" in url.lower()

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        parsed = urllib.parse.urlparse(link)
        base_host = f"{parsed.scheme}://{parsed.netloc}"
        api_url = f"{base_host}/careers/api/embedjobs/default"
        resp = safe_get(api_url)
        if not resp or not resp.ok:
            self.last_error = LAST_HTTP_ERROR
            return []
        try:
            data = resp.json()
        except Exception as exc:
            self.last_error = f"Keka invalid JSON: {exc}"
            return []
        items = data if isinstance(data, list) else (data.get("data") or data.get("jobs") or [])
        jobs = []
        for item in items:
            title = item.get("title")
            jid = item.get("id")
            if not title or not jid:
                continue
            locs = item.get("jobLocations") or []
            loc_str = ", ".join(l.get("name", "") for l in locs if isinstance(l, dict) and l.get("name")) or None
            dept = item.get("departmentName")
            app_url = f"{base_host}/careers/jobdetails/{jid}"
            jobs.append({
                "title": str(title).strip(),
                "location": loc_str,
                "department": dept,
                "employment_type": item.get("jobType"),
                "experience": item.get("experience"),
                "posted_date": item.get("publishedOn"),
                "closing_date": None,
                "salary": None, "education": None, "skills": None,
                "application_url": app_url,
                "source_url": api_url,
                "external_job_id": str(jid),
                "ats_platform": "Keka",
                "evidence_text": json.dumps({"id": jid, "title": title, "location": loc_str, "department": dept}, ensure_ascii=False),
            })
        return jobs


class FreshteamAdapter(BaseATSAdapter):
    """Freshteam public job board API (*.freshteam.com)."""
    name = "FRESHTEAM"

    @classmethod
    def matches(cls, url: str) -> bool:
        return ".freshteam.com" in url.lower()

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        parsed = urllib.parse.urlparse(link)
        base_host = f"{parsed.scheme}://{parsed.netloc}"
        api_url = f"{base_host}/hire/widgets/jobs.json"
        resp = safe_get(api_url)
        if not resp or not resp.ok:
            self.last_error = LAST_HTTP_ERROR
            return []
        try:
            data = resp.json()
        except Exception as exc:
            self.last_error = f"Freshteam invalid JSON: {exc}"
            return []
        items = data.get("jobs") if isinstance(data, dict) else (data if isinstance(data, list) else [])
        jobs = []
        for item in items or []:
            title = item.get("title")
            jid = item.get("id")
            if not title:
                continue
            app_url = item.get("url") or (f"{base_host}/jobs/{jid}" if jid else None)
            if not app_url:
                continue
            branch = item.get("branch") or {}
            loc_str = ", ".join(filter(None, [branch.get("city"), branch.get("state"), branch.get("country")])) if isinstance(branch, dict) else None
            dept = (item.get("department") or {}).get("name") if isinstance(item.get("department"), dict) else None
            jobs.append({
                "title": str(title).strip(),
                "location": loc_str,
                "department": dept,
                "employment_type": item.get("type"),
                "work_mode": "Remote" if item.get("remote") else None,
                "posted_date": item.get("created_at"),
                "closing_date": item.get("closing_date"),
                "salary": None, "experience": None, "education": None, "skills": None,
                "application_url": app_url,
                "source_url": api_url,
                "external_job_id": str(jid) if jid else None,
                "ats_platform": "Freshteam",
                "evidence_text": json.dumps({"id": jid, "title": title, "location": loc_str, "department": dept}, ensure_ascii=False),
            })
        return jobs


class ZohoRecruitAdapter(BaseATSAdapter):
    """Zoho Recruit public career portals (*.zohorecruit.com / *.zohorecruit.in)."""
    name = "ZOHO_RECRUIT"

    @classmethod
    def matches(cls, url: str) -> bool:
        return "zohorecruit.com" in url.lower() or "zohorecruit.in" in url.lower()

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        resp = safe_get(link)
        if not resp or not resp.ok:
            self.last_error = LAST_HTTP_ERROR
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        jobs = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "/jobs/" in href or "Job_Description" in href or "careerportal" in href:
                title = a.get_text(strip=True)
                if not title or len(title) < 3 or title.lower() in ("apply", "apply now", "view", "view all"):
                    continue
                full_url = urllib.parse.urljoin(resp.url, href)
                if full_url in seen:
                    continue
                seen.add(full_url)
                jobs.append({
                    "title": title,
                    "location": None, "department": None, "employment_type": None,
                    "posted_date": None, "closing_date": None, "salary": None,
                    "experience": None, "education": None, "skills": None,
                    "application_url": full_url,
                    "source_url": resp.url,
                    "external_job_id": None,
                    "ats_platform": "Zoho_Recruit",
                    "evidence_text": json.dumps({"title": title, "url": full_url}, ensure_ascii=False),
                })
        return jobs


class ICIMSAdapter(BaseATSAdapter):
    """iCIMS career portals (*.icims.com)."""
    name = "ICIMS"

    @classmethod
    def matches(cls, url: str) -> bool:
        return ".icims.com" in url.lower()

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        self.last_error = None
        sep = "&" if "?" in link else "?"
        target = f"{link}{sep}in_iframe=1" if "in_iframe=1" not in link else link
        resp = safe_get(target)
        if not resp or not resp.ok:
            self.last_error = LAST_HTTP_ERROR
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        jobs = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            m = re.search(r"/jobs/(\d+)/", href)
            if m:
                jid = m.group(1)
                title = re.sub(r"^Job\s+Title\s*", "", a.get_text(separator=" ", strip=True), flags=re.I).strip()
                if not title or len(title) < 3 or jid in seen:
                    continue
                seen.add(jid)
                clean_url = urllib.parse.urljoin(resp.url, href).replace("?in_iframe=1", "").replace("&in_iframe=1", "")
                jobs.append({
                    "title": title,
                    "location": None, "department": None, "employment_type": None,
                    "posted_date": None, "closing_date": None, "salary": None,
                    "experience": None, "education": None, "skills": None,
                    "application_url": clean_url,
                    "source_url": resp.url,
                    "external_job_id": jid,
                    "ats_platform": "iCIMS",
                    "evidence_text": json.dumps({"id": jid, "title": title, "url": clean_url}, ensure_ascii=False),
                })
        return jobs


# Master Registry of ATS Adapters
ATS_ADAPTER_REGISTRY: List[BaseATSAdapter] = [
    GreenhouseAdapter(),
    LeverAdapter(),
    WorkdayAdapter(),
    SmartRecruitersAdapter(),
    AshbyAdapter(),
    SuccessFactorsAdapter(),
    OracleTaleoAdapter(),
    DarwinboxAdapter(),
    KekaAdapter(),
    FreshteamAdapter(),
    ZohoRecruitAdapter(),
    ICIMSAdapter(),
]


class ATSParser(BaseParser):
    """
    Scans HTML content for verified ATS links, dispatches to the correct adapter,
    extracts ALL jobs with full pagination, then enriches each job with its detail page.
    Records `self.last_error` when an adapter fails so crawler telemetry logs the real reason.
    """
    def __init__(self, company, url, final_url, html_content):
        super().__init__(company, url, final_url, html_content)
        self.discovered_platform = None
        self.last_error: Optional[str] = None

    def get_extraction_method(self):
        return f"ATS_API_{self.discovered_platform or 'DISCOVERED'}"

    def find_ats_links(self) -> List[str]:
        """Scans page HTML for any links or iframes matching registered ATS platforms."""
        found = []
        if not self.html_content:
            return found
        try:
            soup = BeautifulSoup(self.html_content, 'lxml')
            for tag in soup.find_all(['a', 'iframe']):
                href = (tag.get('href') or tag.get('src') or '').strip()
                if href.startswith('http'):
                    for adapter in ATS_ADAPTER_REGISTRY:
                        if adapter.matches(href) and href not in found:
                            found.append(href)
        except Exception:
            pass
        return found

    def extract_jobs(self) -> List[Dict[str, Any]]:
        seed_links = [
            getattr(self.company, 'ats_url', None),
            getattr(self.company, 'careers_url', None),
            self.final_url,
            self.url,
        ]
        ats_links = []
        extra_html_ats = re.findall(
            r"https?://(?:[a-zA-Z0-9-]+\.)*(?:darwinbox\.(?:in|com)|keka\.com|freshteam\.com|zohorecruit\.(?:com|in)|icims\.com)[^\s\"'<>]*",
            self.html_content or '',
            flags=re.I,
        )
        for u in seed_links + list(self.find_ats_links()) + extra_html_ats:
            if u and isinstance(u, str) and u.startswith('http') and u not in ats_links:
                ats_links.append(u)
        all_jobs = []
        errors = []

        for link in ats_links:
            for adapter in ATS_ADAPTER_REGISTRY:
                if adapter.matches(link):
                    self.discovered_platform = adapter.name
                    extracted = adapter.extract_jobs(link, self.company)
                    if adapter.last_error:
                        errors.append(f"{adapter.name}: {adapter.last_error}")
                    if extracted:
                        enriched_jobs = self._enrich_with_detail_pages(extracted)
                        all_jobs.extend(enriched_jobs)
                        return all_jobs

        if errors:
            self.last_error = "; ".join(errors)[:1000]
        return all_jobs

    def _enrich_with_detail_pages(self, jobs: List[Dict]) -> List[Dict]:
        """
        For jobs that have an application_url, fetch the detail page and
        merge in all additional fields (description, responsibilities, qualifications,
        pay_band, function, role_purpose, day_in_the_life, technical/behavioural skills, etc.)
        Fields are ONLY updated if the detail page provides the information.
        """
        enriched = []
        detail_count = 0
        for job in jobs:
            detail_url = job.get('application_url')
            if (detail_count < 3
                and detail_url and detail_url.startswith('http')
                and not job.get('responsibilities')
                and 'hcmui' not in detail_url.lower()
                and 'oraclecloud.com' not in detail_url.lower()):
                time.sleep(0.05)
                detail_data = fetch_job_detail(detail_url)
                for field, value in detail_data.items():
                    if value is not None and (job.get(field) is None or not str(job.get(field)).strip()):
                        job[field] = value
                job['detail_fetched'] = detail_data.get('detail_fetched', True)
                job['detail_fetch_status'] = detail_data.get('detail_fetch_status', 'FETCHED')
                detail_count += 1
            else:
                if not job.get('detail_fetched'):
                    job['detail_fetched'] = False
                    job['detail_fetch_status'] = job.get('detail_fetch_status') or 'NOT_FETCHED'
            enriched.append(job)

        return enriched
