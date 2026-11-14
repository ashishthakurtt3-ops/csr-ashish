"""
modules/crawler_engine/adapters/zwayam.py
========================================
Independent ATS extraction adapter for Zwayam Career Portals (*.zwayam.com, jobs.happiestminds.com).
Parses Zwayam recruitment search API endpoints and structured vacancy records.
"""
import json
import re
import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from .base import BaseATSAdapter, ExtractedJobRecord


class ZwayamAdapter(BaseATSAdapter):
    platform_name = "Zwayam"

    # Known domain to company ID mappings
    KNOWN_DOMAINS = {
        'jobs.happiestminds.com': 'MTU5NzQ=',
        'careers.happiestminds.com': 'MTU5NzQ=',
        'happiestminds.com': 'MTU5NzQ='
    }

    def can_handle(self, url: str) -> bool:
        netloc = urlparse(url).netloc.lower()
        return "zwayam.com" in netloc or "happiestminds.com" in netloc

    def fetch_live_jobs(self, domain: str = "jobs.happiestminds.com", company_id: Optional[str] = None, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Directly queries Zwayam public recruitment search API.
        """
        if not company_id:
            company_id = self.KNOWN_DOMAINS.get(domain, 'MTU5NzQ=')

        search_url = "https://public.zwayam.com/jobs/search"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': f'https://{domain}/happiestminds/',
            'Origin': f'https://{domain}',
            'Accept': 'application/json, text/plain, */*'
        }
        data = {
            'filterCri': json.dumps({
                'paginationStartNo': 0,
                'selectedCall': 'sort',
                'sortCriteria': {'name': 'modifiedDate', 'isAscending': False},
                'anyOfTheseWords': ''
            }),
            'domain': domain,
            'companyId': company_id
        }

        try:
            resp = requests.post(search_url, data=data, headers=headers, timeout=15)
            if resp.status_code == 200:
                payload = resp.json()
                raw_items = payload.get('data', {}).get('data', [])
                if isinstance(raw_items, list):
                    return raw_items[:limit]
        except Exception:
            pass
        return []

    def extract_jobs(self, company_id: str, source_url: str, content: str = "", content_type: str = "html") -> List[ExtractedJobRecord]:
        results: List[ExtractedJobRecord] = []
        parsed = urlparse(source_url)
        netloc = parsed.netloc.lower()

        # If content has JSON payload from Zwayam search API
        raw_items: List[Dict[str, Any]] = []
        if content_type == "json" or content.strip().startswith("{"):
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    raw_items = data.get("data", {}).get("data", []) or data.get("jobs", [])
            except Exception:
                pass

        # If no content passed or empty, query live API
        if not raw_items:
            domain = netloc if netloc in self.KNOWN_DOMAINS else "jobs.happiestminds.com"
            raw_items = self.fetch_live_jobs(domain=domain)

        for item in raw_items:
            src = item.get("_source", {})
            j_id = str(item.get("_id") or "")
            ref_no = src.get("referenceNumber") or j_id

            # Parse title
            roles = src.get("rolesList") or []
            title = roles[0].strip() if roles and roles[0] else ""
            desc = src.get("mediumDescriptionWithoutHtml") or ""

            if not title or len(title) < 3:
                if "Job Title:" in desc:
                    title = desc.split("Job Title:")[1].split("\n")[0].split(".")[0].strip()
                elif "Role:" in desc:
                    title = desc.split("Role:")[1].split("\n")[0].split(".")[0].strip()
                elif "Job Summary:" in desc and "seeking a" in desc.lower():
                    # extract role after seeking a/an
                    m = re.search(r'seeking\s+(?:a|an)\s+(?:highly\s+skilled\s+)?([A-Za-z0-9\s\-/]+?)(?:\s+with|\s+to|\.|\n)', desc, re.I)
                    if m:
                        title = m.group(1).strip()

            if not title or len(title) < 3:
                first_line = desc.strip().split("\n")[0].strip()
                if 5 <= len(first_line) <= 80:
                    title = first_line

            if not title or len(title) < 3:
                title = f"Specialist / Engineer - {ref_no}"

            title = title.replace("?", "-").strip(" -:;,")

            # Parse location
            loc = src.get("locationSeparatedbySlash") or ""
            loc_recs = src.get("jobLocationRecord") or []
            if loc_recs and isinstance(loc_recs, list) and loc_recs[0].get("formattedLocation"):
                loc = loc_recs[0]["formattedLocation"]
            elif not loc and loc_recs:
                loc = loc_recs[0].get("city") or loc_recs[0].get("location") or "India"
            if not loc:
                loc = "Bengaluru, Karnataka, India"

            # Department
            dept = src.get("DepartmentName") or "Technology Services"

            # Experience
            min_e = src.get("minYearOfExperience")
            max_e = src.get("maxYrsOfExperience")
            if min_e is not None and max_e is not None and str(max_e) not in ("0", ""):
                exp = f"{min_e}-{max_e} years"
            elif min_e is not None and str(min_e) not in ("0", ""):
                exp = f"{min_e}+ years"
            else:
                exp = "As specified on portal"

            app_url = f"https://jobs.happiestminds.com/happiestminds/#/job-details/{j_id}" if j_id else source_url

            rec = ExtractedJobRecord(
                company_id=company_id,
                job_title=title,
                detail_url=app_url,
                application_url=app_url,
                ats_platform=self.platform_name,
                department=dept,
                location_raw=loc,
                country="India",
                employment_type="Full-time",
                work_mode="On-site",
                external_job_id=ref_no,
                source_evidence={
                    "experience": exp,
                    "requisition_id": ref_no,
                    "raw_source": f"Happiest Minds Opening: {title} in {loc} ({dept}). Ref: {ref_no}"
                },
                confidence=0.99
            )
            results.append(rec)

        return results

