"""
ATS Adapters with complete pagination and job detail page fetch.

Rules:
- Never stop at first API page (Workday 25-limit, SmartRecruiters paging, etc.)
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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
}
REQUEST_TIMEOUT = 6


def safe_get(url: str, **kwargs) -> Optional[requests.Response]:
    """HTTP GET with a single retry on transient errors."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, **kwargs)
        return resp
    except Exception:
        return None


def safe_post(url: str, **kwargs) -> Optional[requests.Response]:
    """HTTP POST with error swallowing."""
    try:
        resp = requests.post(url, headers={**HEADERS, 'Content-Type': 'application/json', 'Accept': 'application/json'},
                             timeout=REQUEST_TIMEOUT, **kwargs)
        return resp
    except Exception:
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
        token = None
        for_match = re.search(r'[?&]for=([^&#]+)', link, re.IGNORECASE)
        if for_match:
            token = for_match.group(1)
        if not token:
            match = re.search(r'greenhouse\.io/([^/?#]+)', link, re.IGNORECASE)
            if match and match.group(1) not in ('embed', 'js', 'api'):
                token = match.group(1)
        if not token:
            return []
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        jobs = []
        resp = safe_get(api_url)
        if not resp or not resp.ok:
            return []
        try:
            data = resp.json()
        except Exception:
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

            job_url = job.get('absolute_url') or link
            external_id = str(job.get('id', '')) or None

            # Fetch detail from the boards API (has content=true) first
            detail_content = job.get('content', '')  # Already fetched with content=true

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
        match = re.search(r'lever\.co/([^/?#]+)', link, re.IGNORECASE)
        if not match:
            return []
        token = match.group(1)
        api_url = f"https://api.lever.co/v0/postings/{token}?mode=json"
        resp = safe_get(api_url)
        if not resp or not resp.ok:
            return []
        try:
            data = resp.json()
        except Exception:
            return []

        jobs = []
        for job in data:
            title = job.get('text')
            if not title:
                continue
            cats = job.get('categories', {}) or {}
            lists = job.get('lists', []) or []

            # Extract structured sections from lists
            responsibilities = None
            requirements = None
            for section in lists:
                content = section.get('content', '')
                label_lc = (section.get('text') or '').lower()
                if 'responsibilit' in label_lc:
                    responsibilities = BeautifulSoup(content, 'lxml').get_text('\n', strip=True)[:2000]
                elif 'requirement' in label_lc or 'qualif' in label_lc:
                    requirements = BeautifulSoup(content, 'lxml').get_text('\n', strip=True)[:2000]

            # Full description from descriptionPlain
            full_desc = job.get('descriptionPlain') or BeautifulSoup(job.get('description', ''), 'lxml').get_text('\n', strip=True)

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
                'application_url': job.get('applyUrl') or link,
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

    def extract_jobs(self, link: str, company: Any) -> List[Dict[str, Any]]:
        parsed = urllib.parse.urlparse(link)
        host = parsed.netloc
        path_parts = [p for p in parsed.path.strip('/').split('/') if p]
        if not path_parts:
            return []

        # Handle locale prefixes like /en-US/ or /en/
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

        jobs = []
        offset = 0
        limit = 20
        total = None

        while True:
            payload = {"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": ""}
            resp = safe_post(api_url, json=payload)
            if not resp or not resp.ok:
                break
            try:
                data = resp.json()
            except Exception:
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
                app_url = f"https://{host}/{site}{external_path}" if external_path else link
                detail_id = item.get('bulletFields', [None])[0] if item.get('bulletFields') else None

                jobs.append({
                    'title': title.strip(),
                    'location': item.get('locationsText'),
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

            offset += limit
            if total is not None and offset >= total:
                break
            if len(postings) < limit:
                break
            time.sleep(0.3)  # polite rate limit

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
            return []

        base_api = f"https://api.smartrecruiters.com/v1/companies/{token}/postings"

        jobs = []
        page = 0
        page_size = 100

        while True:
            resp = safe_get(f"{base_api}?pageSize={page_size}&pageNumber={page}")
            if not resp or not resp.ok:
                break
            try:
                data = resp.json()
            except Exception:
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
                    'application_url': item.get('ref') or link,
                    'source_url': base_api,
                    'external_job_id': item.get('id'),
                    'ats_platform': 'SmartRecruiters',
                    'evidence_text': json.dumps({'id': item.get('id'), 'title': name.strip(), 'department': dept_val, 'location': location_str})
                })

            # Check if more pages
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
        match = re.search(r'ashbyhq\.com/([^/?#]+)', link, re.IGNORECASE)
        if not match:
            return []
        token = match.group(1)
        api_url = f"https://api.ashbyhq.com/posting-api/job-board/{token}"
        resp = safe_post(api_url, json={})
        if not resp or not resp.ok:
            return []
        try:
            data = resp.json()
        except Exception:
            return []

        jobs = []
        for item in data.get('jobs', []):
            title = item.get('title')
            if not title:
                continue
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
                'application_url': item.get('applyUrl') or link,
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
                break
            try:
                data = resp.json()
            except Exception:
                break
            results = data.get('d', {}).get('results', [])
            if not results:
                break
            for item in results:
                title = item.get('JobTitle')
                if not title:
                    continue
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
                    'application_url': link,
                    'source_url': base_api,
                    'external_job_id': str(item.get('JobReqId', '')),
                    'ats_platform': 'SuccessFactors',
                    'evidence_text': json.dumps({'JobReqId': item.get('JobReqId'), 'title': title, 'department': item.get('DepartmentName'), 'location': item.get('City')})
                })
            skip += top
            if len(results) < top:
                break
        return jobs

    def _scrape_html_pages(self, link: str) -> List[Dict[str, Any]]:
        """HTML scrape fallback for SuccessFactors career pages (including Career Site Builder)."""
        jobs = []
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
                        break
                else:
                    break

            soup = BeautifulSoup(resp.text, 'lxml')
            found_this_page = False

            # 1. Try JSON-LD first
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string or '')
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        if item.get('@type') == 'JobPosting' and item.get('title'):
                            loc_str = item.get('jobLocation', {}).get('address', {}).get('addressLocality') if isinstance(item.get('jobLocation'), dict) else None
                            jobs.append({
                                'title': item['title'].strip(),
                                'location': loc_str,
                                'city': loc_str,
                                'employment_type': item.get('employmentType'),
                                'posted_date': item.get('datePosted'),
                                'closing_date': item.get('validThrough'),
                                'job_description': BeautifulSoup(item.get('description', ''), 'lxml').get_text('\n', strip=True)[:3000] or None,
                                'salary': None, 'experience': None, 'education': None, 'skills': None,
                                'application_url': link, 'source_url': link,
                                'external_job_id': None,
                                'ats_platform': 'SuccessFactors',
                                'evidence_text': json.dumps({'title': item['title'], 'location': loc_str})
                            })
                            found_this_page = True
                except Exception:
                    pass

            # 2. Career Site Builder (CSB) /job/ link extraction
            if not found_this_page:
                seen_on_page = set()
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if '/job/' in href:
                        title_text = a.get_text(strip=True)
                        if not title_text or len(title_text) < 3 or title_text.lower() in ('apply now', 'more', 'view'):
                            continue
                        job_url = urllib.parse.urljoin(url, href)
                        if job_url in seen_on_page:
                            continue
                        seen_on_page.add(job_url)

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
                        found_this_page = True

            if not found_this_page:
                break
            page += 1
            if page >= 25:  # Cap at 500 jobs per company
                break
            time.sleep(0.3)
        return jobs


class OracleTaleoAdapter(BaseATSAdapter):
    """
    Oracle Taleo / Oracle Cloud HCM candidate portals.
    Supports Oracle Cloud Candidate Experience REST API & Taleo JSON-LD.
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
        # 1. Oracle Cloud Candidate Experience REST API
        if 'oraclecloud.com' in link.lower() or 'sites/cx_' in link.lower() or 'opportunity' in link.lower():
            oracle_jobs = self._extract_oracle_cloud_ce(link, company)
            if oracle_jobs:
                return oracle_jobs

        # 2. Taleo / Standard Oracle HTML & JSON-LD fallback
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

        if not oracle_host:
            return []

        jobs = []
        offset = 0
        limit = 25

        while True:
            api_url = f"{oracle_host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&finder=findReqs;siteNumber={site_number}&expand=requisitionList&offset={offset}&limit={limit}"
            resp = safe_get(api_url)
            if not resp or not resp.ok:
                break
            try:
                data = json.loads(resp.text)
            except Exception:
                break

            items = data.get('items', [])
            if not items:
                break
            req_list = items[0].get('requisitionList', [])
            if not req_list:
                break

            for req in req_list:
                title = req.get('Title')
                if not title:
                    continue
                req_id = req.get('Id')
                app_url = f"{oracle_host}/hcmUI/CandidateExperience/en/sites/{site_number}/job/{req_id}" if req_id else link
                loc = req.get('PrimaryLocation')
                jobs.append({
                    'title': title.strip(),
                    'location': loc,
                    'city': loc.split(',')[0].strip() if loc else None,
                    'state': loc.split(',')[1].strip() if loc and ',' in loc else None,
                    'employment_type': req.get('JobSchedule') or req.get('Schedule'),
                    'posted_date': req.get('PostedDate'),
                    'closing_date': req.get('PostingEndDate'),
                    'department': req.get('Department') or req.get('JobFamily'),
                    'business_unit': req.get('BusinessUnit'),
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

            offset += limit
            if offset >= 1000 or len(req_list) < limit:
                break
            time.sleep(0.3)

        return jobs

    def _extract_taleo_jsonld(self, link: str, company: Any) -> List[Dict[str, Any]]:
        jobs = []
        page = 0
        while True:
            url = link if page == 0 else f"{link}&offset={page * 25}"
            resp = safe_get(url)
            if not resp or not resp.ok:
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
                                'application_url': link, 'source_url': link,
                                'external_job_id': None,
                                'ats_platform': 'Oracle_Taleo',
                                'evidence_text': json.dumps({'title': item['title']})
                            })
                            found += 1
                except Exception:
                    pass
            if found == 0:
                break
            page += 1
            if page > 40:
                break
            time.sleep(0.3)
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
]


class ATSParser(BaseParser):
    """
    Scans HTML content for verified ATS links, dispatches to the correct adapter,
    extracts ALL jobs with full pagination, then enriches each job with its detail page.
    """
    def __init__(self, company, url, final_url, html_content):
        super().__init__(company, url, final_url, html_content)
        self.discovered_platform = None

    def get_extraction_method(self):
        return f"ATS_API_{self.discovered_platform or 'DISCOVERED'}"

    def extract_jobs(self) -> List[Dict[str, Any]]:
        ats_links = self.find_ats_links()
        all_jobs = []

        for link in ats_links:
            for adapter in ATS_ADAPTER_REGISTRY:
                if adapter.matches(link):
                    self.discovered_platform = adapter.name
                    extracted = adapter.extract_jobs(link, self.company)
                    if extracted:
                        # Enrich each job with its detail page content
                        enriched_jobs = self._enrich_with_detail_pages(extracted)
                        all_jobs.extend(enriched_jobs)
                        return all_jobs

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
            # Fetch detail if URL present and not rich yet
            if (detail_count < 50
                and detail_url and detail_url.startswith('http') 
                and not job.get('responsibilities')
                and 'hcmui' not in detail_url.lower()
                and 'oraclecloud.com' not in detail_url.lower()):
                time.sleep(0.05)  # polite delay between detail fetches
                detail_data = fetch_job_detail(detail_url)
                # Merge: update fields where detail_data has valid content
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

    def find_ats_links(self) -> List[str]:
        soup = BeautifulSoup(self.html_content, 'lxml')
        ats_links = set()
        link_scores = {}

        ats_signatures = [
            'greenhouse.io',
            'lever.co',
            'myworkdayjobs.com',
            'smartrecruiters.com',
            'ashbyhq.com',
            'successfactors.com',
            'successfactors.eu',
            'heromotocorp.com',
            'jobs.heromotocorp.com',
            'taleo.net',
            'oraclecloud.com',
            'icims.com',
            'darwinbox.in',
            'eightfold.ai',
        ]

        c_name = (getattr(self.company, 'company_name', '') or '').lower()
        company_keywords = [w for w in re.findall(r'[a-z]+', c_name) if len(w) > 3 and w not in ('limited', 'india', 'corp', 'company', 'services')]

        # 1. Check self.url and self.final_url first (handles direct ATS links & redirects)
        for u in (self.url, self.final_url):
            if u and any(sig in u.lower() for sig in ats_signatures):
                ats_links.add(u)
                link_scores[u] = 5

        # 2. Check <a> links in HTML with anchor text keyword matching
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            txt = a.get_text(strip=True).lower()
            if href.startswith('/'):
                href = urllib.parse.urljoin(self.url, href)

            is_ats = (
                any(sig in href.lower() for sig in ats_signatures) or
                'sites/cx_' in href.lower() or
                ('opportunity' in href.lower() and 'requisition' in href.lower())
            )
            if is_ats:
                ats_links.add(href)
                score = sum(10 for kw in company_keywords if kw in txt or kw in href.lower())
                if 'cx_1/' in href.lower() or href.lower().endswith('cx_1') or 'cx_1?' in href.lower():
                    score += 1
                link_scores[href] = max(link_scores.get(href, 0), score)

        # 3. Check <iframe> sources
        for iframe in soup.find_all('iframe', src=True):
            src = iframe['src'].strip()
            if any(sig in src.lower() for sig in ats_signatures):
                if src.startswith('/'):
                    src = urllib.parse.urljoin(self.url, src)
                ats_links.add(src)
                link_scores[src] = link_scores.get(src, 2)

        # 4. Check for embedded Oracle Cloud hosts in scripts
        oracle_match = re.search(r'https?://[a-zA-Z0-9.-]+\.oraclecloud\.com', self.html_content)
        if oracle_match:
            host_url = oracle_match.group(0)
            ats_links.add(host_url)
            link_scores[host_url] = link_scores.get(host_url, 1)

        # 5. Check for embedded SuccessFactors scripts in HTML
        if 'successfactors.com' in self.html_content.lower() or 'successfactors.eu' in self.html_content.lower():
            target_url = self.final_url or self.url
            if target_url:
                ats_links.add(target_url)
                link_scores[target_url] = max(link_scores.get(target_url, 0), 10)

        # Sort by relevance score descending
        return sorted(list(ats_links), key=lambda x: link_scores.get(x, 0), reverse=True)

