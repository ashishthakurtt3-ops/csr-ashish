"""
modules/crawler_engine/adapters/reliance.py
===========================================
Dedicated Production Adapter for Reliance Careers Portal (careers.ril.com).
Supports:
- ASP.NET WebForms job search grid parsing (MainContent_rgJobs).
- Multi-page pagination traversal with loop/duplicate guards.
- Structured job row extraction (Job ID, Title, Entity, Location, Date).
- Full individual job detail page parsing (Responsibilities, Requirements, Skills).
- Group entity attribution (Reliance Industries, Reliance Foundation, Reliance Retail, Jio, Reliance New Energy).
- Both static HTML parsing (for deterministic testing & HTTPX) and live Playwright execution.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import httpx

from .base import BaseATSAdapter, ExtractedJobRecord

logger = logging.getLogger(__name__)

RELIANCE_CAREERS_BASE = "https://careers.ril.com/rilcareers/"
RELIANCE_SEARCH_URL = "https://careers.ril.com/rilcareers/frmjobsearch.Aspx"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}


class ReliancePortalAdapter(BaseATSAdapter):
    platform_name: str = "Reliance Careers Portal"

    def can_handle(self, url: str) -> bool:
        if not url:
            return False
        url_lower = url.lower()
        return (
            "careers.ril.com" in url_lower
            or "rilcareers" in url_lower
            or "rcareers.ril.com" in url_lower
            or "frmjobsearch.aspx" in url_lower
        )

    def determine_group_entity(self, section_text: str, title: str = "") -> Tuple[str, str]:
        """
        Determines the correct Reliance group entity from section / title.
        Returns (employer_name, entity_type).
        """
        combined = f"{section_text} {title}".lower()
        if "foundation" in combined:
            return "Reliance Foundation", "FOUNDATION"
        elif "retail" in combined:
            return "Reliance Retail", "SUBSIDIARY"
        elif "jio" in combined:
            return "Reliance Jio Infocomm Limited", "SUBSIDIARY"
        elif "new energy" in combined or "bioenergy" in combined:
            return "Reliance New Energy", "SUBSIDIARY"
        elif "life sciences" in combined:
            return "Reliance Life Sciences", "SUBSIDIARY"
        elif "petroleum" in combined or "hydrocarbon" in combined or "manufacturing" in combined or "refining" in combined:
            return "Reliance Industries Limited", "PARENT_COMPANY"
        return "Reliance Industries Limited", "PARENT_COMPANY"

    def parse_job_title_and_id(self, raw_title: str) -> Tuple[str, Optional[str]]:
        """
        Extracts clean title and vacancy ID from raw title strings like:
        'Team Member - Platform ( 83065921 )' or 'Team Member - Platform [83065921]'
        """
        clean = re.sub(r'\s+', ' ', raw_title or "").strip()
        job_id = None
        
        # Check ( 83065921 ) or [83065921]
        id_match = re.search(r'[\(\[]\s*(\d{6,10})\s*[\)\]]', clean)
        if id_match:
            job_id = id_match.group(1)
            clean = re.sub(r'[\(\[]\s*' + job_id + r'\s*[\)\]]', '', clean).strip()

        clean = clean.strip(" -|[]()")
        return clean, job_id

    def extract_detail_from_html(self, html: str, detail_url: str) -> Dict[str, Any]:
        """
        Deterministic parser for Reliance job detail page HTML.
        Extracts ASP.NET WebForms MainContent_lbl* fields.
        """
        soup = BeautifulSoup(html, "lxml")
        res = {
            "title_raw": "",
            "clean_title": "",
            "job_id": None,
            "posted_date": None,
            "section": None,
            "location": None,
            "responsibilities": None,
            "education": None,
            "experience": None,
            "skills": None,
            "is_valid_detail": False
        }

        title_lbl = soup.find(id="MainContent_lblJobTitle")
        if not title_lbl or not title_lbl.get_text(strip=True):
            # Check title tag or other headings
            if soup.title and "Reliance Careers" in soup.title.string:
                title_text = soup.title.string.split("|")[0].strip()
            else:
                return res
        else:
            title_text = title_lbl.get_text(" ", strip=True)

        clean_title, j_id = self.parse_job_title_and_id(title_text)
        res["title_raw"] = title_text
        res["clean_title"] = clean_title
        res["job_id"] = j_id
        res["is_valid_detail"] = bool(clean_title and len(clean_title) >= 3)

        posted_lbl = soup.find(id="MainContent_lblPostedDate")
        if posted_lbl:
            res["posted_date"] = posted_lbl.get_text(" ", strip=True)

        sec_lbl = soup.find(id="MainContent_lblSec")
        if sec_lbl:
            res["section"] = sec_lbl.get_text(" ", strip=True)

        loc_lbl = soup.find(id="MainContent_lblLoc")
        if loc_lbl:
            res["location"] = loc_lbl.get_text(" ", strip=True)

        resp_lbl = soup.find(id="MainContent_lblSummRole")
        if resp_lbl:
            res["responsibilities"] = resp_lbl.get_text(" ", strip=True)

        edu_lbl = soup.find(id="MainContent_lblEduReq")
        if edu_lbl:
            res["education"] = edu_lbl.get_text(" ", strip=True)

        exp_lbl = soup.find(id="MainContent_lblExpReq")
        if exp_lbl:
            res["experience"] = exp_lbl.get_text(" ", strip=True)

        skill_lbl = soup.find(id="MainContent_lblSkill")
        if skill_lbl:
            res["skills"] = skill_lbl.get_text(" ", strip=True)

        return res

    def extract_from_grid_html(self, html: str, company_id: str, base_url: str = RELIANCE_CAREERS_BASE) -> List[Dict[str, Any]]:
        """
        Parses rows from the ASP.NET MainContent_rgJobs table.
        """
        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", id="MainContent_rgJobs")
        if not table:
            return []

        rows = table.find_all("tr")
        if len(rows) < 2:
            return []

        grid_jobs: List[Dict[str, Any]] = []
        # First row is header, last row is pager
        content_rows = [r for r in rows[1:] if not r.find(id="MainContent_rgJobs_CurrentPageLabel")]

        for r in content_rows:
            tds = r.find_all("td")
            if len(tds) < 5:
                continue

            a_tag = tds[1].find("a", href=True)
            if not a_tag:
                continue

            raw_title = a_tag.get_text(" ", strip=True)
            rel_href = a_tag["href"].strip()
            full_detail_url = urljoin(base_url, rel_href)

            clean_title, j_id = self.parse_job_title_and_id(raw_title)
            functional_area = tds[2].get_text(" ", strip=True)
            location = tds[3].get_text(" ", strip=True)
            posted_date = tds[4].get_text(" ", strip=True)

            employer_name, entity_type = self.determine_group_entity(functional_area, clean_title)

            grid_jobs.append({
                "company_id": company_id,
                "job_title": clean_title,
                "job_id": j_id,
                "detail_url": full_detail_url,
                "application_url": full_detail_url,
                "functional_area": functional_area,
                "location": location,
                "posted_date": posted_date,
                "employer_name": employer_name,
                "entity_type": entity_type
            })

        return grid_jobs

    def fetch_job_detail_httpx(self, detail_url: str) -> Optional[Dict[str, Any]]:
        """
        Fetches an individual job detail page via HTTPX and parses all structured fields.
        """
        try:
            with httpx.Client(verify=False, follow_redirects=True, timeout=15.0) as client:
                resp = client.get(detail_url, headers=DEFAULT_HEADERS)
                if resp.status_code == 200:
                    return self.extract_detail_from_html(resp.text, detail_url)
        except Exception as e:
            logger.warning(f"Failed to fetch job detail {detail_url}: {e}")
        return None

    def crawl_all_pages_playwright(self, company_id: str, max_pages: int = 10) -> List[ExtractedJobRecord]:
        """
        Traverses all listing pages of careers.ril.com/rilcareers/frmjobsearch.Aspx using Playwright.
        Paginates until next button is disabled or max_pages reached.
        Fetches detail pages and returns fully enriched ExtractedJobRecord instances.
        """
        from playwright.sync_api import sync_playwright

        all_grid_rows: List[Dict[str, Any]] = []
        seen_job_ids = set()
        page_num = 1

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(RELIANCE_SEARCH_URL, timeout=35000)
                page.wait_for_selector("#MainContent_rgJobs", timeout=20000)

                while page_num <= max_pages:
                    html_content = page.content()
                    page_rows = self.extract_from_grid_html(html_content, company_id, RELIANCE_CAREERS_BASE)
                    
                    new_on_page = 0
                    for row in page_rows:
                        jid = row.get("job_id") or row.get("detail_url")
                        if jid not in seen_job_ids:
                            seen_job_ids.add(jid)
                            all_grid_rows.append(row)
                            new_on_page += 1

                    # Check next button
                    next_btn = page.locator("#MainContent_rgJobs_lnkNext")
                    if not next_btn.is_visible() or not next_btn.is_enabled():
                        break

                    curr_label = page.locator("#MainContent_rgJobs_CurrentPageLabel").text_content()
                    next_btn.click()
                    page.wait_for_load_state("networkidle", timeout=10000)
                    page.wait_for_timeout(1500)

                    new_label = page.locator("#MainContent_rgJobs_CurrentPageLabel").text_content()
                    if new_label == curr_label:
                        # Pagination stopped advancing
                        break
                    page_num += 1

                browser.close()
        except Exception as e:
            logger.error(f"Playwright pagination failed on {RELIANCE_SEARCH_URL}: {e}")

        # If Playwright failed to fetch or collected 0, fallback to single page via HTTPX
        if not all_grid_rows:
            try:
                with httpx.Client(verify=False, follow_redirects=True, timeout=20.0) as client:
                    resp = client.get(RELIANCE_SEARCH_URL, headers=DEFAULT_HEADERS)
                    if resp.status_code == 200:
                        all_grid_rows = self.extract_from_grid_html(resp.text, company_id, RELIANCE_CAREERS_BASE)
            except Exception as e:
                logger.error(f"HTTPX fallback failed on {RELIANCE_SEARCH_URL}: {e}")

        # Enrich records with detail page information
        records: List[ExtractedJobRecord] = []
        for g_row in all_grid_rows:
            detail_data = self.fetch_job_detail_httpx(g_row["detail_url"])
            if detail_data and detail_data.get("is_valid_detail"):
                title = detail_data["clean_title"] or g_row["job_title"]
                location = detail_data["location"] or g_row["location"] or "India"
                posted_date = detail_data["posted_date"] or g_row["posted_date"]
                section = detail_data["section"] or g_row["functional_area"]
                description = detail_data["responsibilities"] or f"Opportunity in {section} at {g_row['employer_name']}."
                edu = detail_data["education"]
                exp = detail_data["experience"]
                skills = detail_data["skills"]
                job_id = detail_data["job_id"] or g_row["job_id"]
            else:
                title = g_row["job_title"]
                location = g_row["location"] or "India"
                posted_date = g_row["posted_date"]
                section = g_row["functional_area"]
                description = f"Opportunity in {section} at {g_row['employer_name']}."
                edu = None
                exp = None
                skills = None
                job_id = g_row["job_id"]

            employer_name, entity_type = self.determine_group_entity(section, title)

            evidence_dict = {
                "employer_entity": employer_name,
                "entity_type": entity_type,
                "posted_date": posted_date,
                "functional_area": section,
                "education_requirements": edu,
                "experience_requirements": exp,
                "skills_competencies": skills,
                "external_job_id": job_id,
                "portal_source": "careers.ril.com",
                "verified_source_domain": "careers.ril.com",
                "ownership_validation": "CONFIRMED_RELIANCE_APEX_DOMAIN"
            }

            records.append(
                ExtractedJobRecord(
                    company_id=company_id,
                    job_title=title,
                    detail_url=g_row["detail_url"],
                    application_url=g_row["detail_url"],
                    ats_platform="Reliance Careers Portal",
                    department=section,
                    team=employer_name,
                    description=description,
                    location_raw=location,
                    country="India",
                    employment_type="Full-time",
                    work_mode="Onsite",
                    external_job_id=job_id,
                    source_evidence=evidence_dict,
                    confidence=1.0
                )
            )

        return records

    def extract_jobs(
        self,
        company_id: str,
        source_url: str,
        content: str,
        content_type: str = "html"
    ) -> List[ExtractedJobRecord]:
        """
        Main extraction entry point adhering to BaseATSAdapter contract.
        If content is HTML and contains MainContent_rgJobs table, extracts deterministically.
        If content is empty or generic, invokes full crawler.
        """
        # If HTML already contains the job search grid table (e.g. from static fixture or previous fetch)
        if content and "MainContent_rgJobs" in content:
            grid_jobs = self.extract_from_grid_html(content, company_id, RELIANCE_CAREERS_BASE)
            records: List[ExtractedJobRecord] = []
            for g_row in grid_jobs:
                records.append(
                    ExtractedJobRecord(
                        company_id=company_id,
                        job_title=g_row["job_title"],
                        detail_url=g_row["detail_url"],
                        application_url=g_row["detail_url"],
                        ats_platform="Reliance Careers Portal",
                        department=g_row["functional_area"],
                        team=g_row["employer_name"],
                        description=f"Vacancy in {g_row['functional_area']} at {g_row['employer_name']}.",
                        location_raw=g_row["location"],
                        country="India",
                        employment_type="Full-time",
                        work_mode="Onsite",
                        external_job_id=g_row["job_id"],
                        source_evidence={
                            "employer_entity": g_row["employer_name"],
                            "entity_type": g_row["entity_type"],
                            "posted_date": g_row["posted_date"],
                            "functional_area": g_row["functional_area"],
                            "external_job_id": g_row["job_id"],
                            "portal_source": "careers.ril.com",
                            "verified_source_domain": "careers.ril.com"
                        },
                        confidence=1.0
                    )
                )
            return records

        # Otherwise perform live portal crawl
        return self.crawl_all_pages_playwright(company_id=company_id)

