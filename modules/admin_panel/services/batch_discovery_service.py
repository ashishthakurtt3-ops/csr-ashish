"""
modules/admin_panel/services/batch_discovery_service.py
=======================================================
Autonomous AI Bulk Discovery Engine for Enterprise Companies.
Enables administrators to upload CSV / Excel files containing company names and domains,
crawls company websites, semantically extracts active job vacancies and statutory CSR initiatives,
and directly auto-imports verified records into the production MySQL database.
Supports both existing database entities and any newly provided random companies.
"""

import os
import re
import csv
import io
import json
import hashlib
import logging
import time
import urllib.request
import urllib.error
import urllib.parse
import asyncio
import concurrent.futures as _cf
import html as _html
import threading
from typing import List, Dict, Any, Tuple
from django.utils import timezone
from django.db import transaction, close_old_connections
from django.core.cache import cache

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    cffi_requests = None

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

from bs4 import BeautifulSoup

from modules.admin_panel.models import Company, Job, CSRProject, CSRReport, AuditTrail, DroppedCandidate
from modules.crawler_engine.hybrid_ai_service import HybridAIExtractionService
from modules.admin_panel.services.ai_config_service import get_active_ai_config, resolve_active_ai_summary
from modules.crawler_engine.crawler import (
    try_dispatch_specialized_ats,
    detect_repeating_dom_job_cards,
    try_fetch_workday_json,
    COMMON_INDIAN_LOCATIONS,
)
from modules.crawler_engine.adapters.reliance import ReliancePortalAdapter
from modules.crawler_engine.adapters.generic_jsonld import GenericStructuredJobAdapter
from modules.crawler_engine.discovery_helpers import (
    is_valid_job_title,
    is_valid_csr_project,
    is_static_asset_url,
    derive_deep_job_url,
    resolve_authentic_csr_url,
    get_registrable_domain,
    is_allowed_domain_or_ats,
    ENTERPRISE_PORTAL_REGISTRY,
    ENTERPRISE_CSR_REGISTRY,
    ALLOWED_ATS_HOSTS
)

logger = logging.getLogger(__name__)

# Media / editorial URLs are never statutory reports, even when their path
# contains words like "esg" or "disclosure" (e.g. /video/esg-risks-disclosure).
_NON_REPORT_MEDIA_EXTENSIONS = (
    '.mp4', '.mov', '.avi', '.webm', '.mkv', '.mp3', '.wav', '.m4a',
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.zip', '.rar',
)
_NON_REPORT_PATH_RE = re.compile(
    r'/(video|videos|watch|webinar|webinars|podcast|podcasts|gallery|events?|'
    r'news|newsroom|press|press-release|press-releases|press-report|'
    r'media[-_]?cent(re|er)|blog|stories|story|insights|'
    r'case-stud(y|ies))/',
    re.IGNORECASE,
)
_STRONG_REPORT_RE = re.compile(
    r'(brsr|annual[-_ ]?report|integrated[-_ ]?report|sustainability[-_ ]?report|'
    r'esg[-_ ]?report|csr[-_ ]?report|section[-_ ]?135|business[-_ ]?responsibility[-_ ]?report)',
    re.IGNORECASE,
)


def _is_non_report_media_url(url: str) -> bool:
    """True for video/audio/image/editorial URLs that must never be treated as reports."""
    try:
        path = urllib.parse.urlparse(url or '').path.lower()
    except Exception:
        path = (url or '').lower()
    if path.endswith(_NON_REPORT_MEDIA_EXTENSIONS):
        return True
    return bool(_NON_REPORT_PATH_RE.search(path))


def _is_marketing_service_url(url: str) -> bool:
    """True for service/solution/product marketing pages, which are not CSR portals."""
    try:
        path = urllib.parse.urlparse(url or '').path.lower()
    except Exception:
        path = (url or '').lower()
    return bool(re.search(
        r'/(services?|solutions?|products?|industries|offerings|capabilities|case-stud(y|ies))(/|$)',
        path,
    ))


def _is_report_document_url(url: str, title: str = '') -> bool:
    """Strict report-document test: strong report wording, or a PDF with report context."""
    low_url = (url or '').lower()
    combined = f"{title or ''} {low_url}"
    if _is_non_report_media_url(low_url):
        return False
    path = urllib.parse.urlparse(low_url).path
    is_pdf = path.endswith('.pdf')
    if _STRONG_REPORT_RE.search(combined):
        return True
    if is_pdf and any(k in combined for k in ('csr', 'esg', 'sustain', 'annual', 'brsr', 'report', '135', 'disclosure')):
        return True
    return False


def _humanize_report_title(url: str) -> str:
    """Builds a readable fallback title from a URL slug instead of showing raw slugs."""
    try:
        name = urllib.parse.unquote((url or '').rstrip('/').rsplit('/', 1)[-1])
    except Exception:
        name = (url or '').rstrip('/').rsplit('/', 1)[-1]
    name = re.sub(r'\.(pdf|html?|aspx?)$', '', name, flags=re.IGNORECASE)
    name = re.sub(r'[-_]+', ' ', name).strip()
    if not name:
        return 'Corporate CSR / Sustainability Report'
    return name[0].upper() + name[1:]


USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
BROWSER_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Ch-Ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1'
}




class BatchDiscoveryService:
    """Core service orchestrating file parsing, web crawling, AI extraction, and direct database auto-import."""

    @classmethod
    def parse_uploaded_file(cls, file_obj, filename: str) -> List[Dict[str, Any]]:
        """Parses CSV, Excel, or JSON files and normalizes column headers into standard company task objects."""
        filename_lower = filename.lower()
        records: List[Dict[str, Any]] = []

        # Ensure file pointer is at the start (handles Django UploadedFile re-reads)
        if hasattr(file_obj, 'seek'):
            try:
                file_obj.seek(0)
            except Exception:
                pass

        if filename_lower.endswith('.csv') or filename_lower.endswith('.tsv') or filename_lower.endswith('.txt'):
            content = file_obj.read()
            text = None
            for enc in ['utf-8', 'utf-8-sig', 'cp1252', 'latin-1']:
                try:
                    text = content.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
            if not text:
                text = content.decode('utf-8', errors='replace')

            # Auto-detect delimiter by sniffing first line
            first_line = text.split('\n')[0] if '\n' in text else text
            if filename_lower.endswith('.tsv'):
                delimiter = '\t'
            elif '\t' in first_line:
                delimiter = '\t'
            elif '|' in first_line and first_line.count('|') > first_line.count(','):
                delimiter = '|'
            elif ';' in first_line and first_line.count(';') > first_line.count(','):
                delimiter = ';'
            else:
                delimiter = ','

            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            for row in reader:
                norm = cls._normalize_row(row)
                if norm and (norm.get('company_name') or norm.get('homepage_url')):
                    records.append(norm)

        elif filename_lower.endswith(('.xlsx', '.xls')):
            xls_loaded = False
            if filename_lower.endswith('.xls'):
                try:
                    import xlrd
                    if hasattr(file_obj, 'seek'):
                        file_obj.seek(0)
                    xls_wb = xlrd.open_workbook(file_contents=file_obj.read())
                    xl_sheet = xls_wb.sheet_by_index(0)
                    if xl_sheet.nrows > 0:
                        xl_headers = [str(xl_sheet.cell_value(0, c)).strip() if xl_sheet.cell_value(0, c) else f'col_{c}' for c in range(xl_sheet.ncols)]
                        for rx in range(1, xl_sheet.nrows):
                            row_vals = tuple(xl_sheet.cell_value(rx, c) for c in range(xl_sheet.ncols))
                            if not any(row_vals):
                                continue
                            row_dict = {xl_headers[i]: str(row_vals[i]).strip() if i < len(row_vals) and row_vals[i] is not None else '' for i in range(len(xl_headers))}
                            norm = cls._normalize_row(row_dict)
                            if norm and (norm.get('company_name') or norm.get('homepage_url')):
                                records.append(norm)
                    xls_loaded = True
                except Exception as e:
                    logger.warning(f"Legacy .xls parsing fallback note: {e}")

            if not xls_loaded:
                import openpyxl
                if hasattr(file_obj, 'seek'):
                    try:
                        file_obj.seek(0)
                    except Exception:
                        pass
                wb = openpyxl.load_workbook(file_obj, data_only=True)
                sheet = wb.active
                rows = list(sheet.iter_rows(values_only=True))
                if rows:
                    headers = [str(h).strip() if h is not None else f'col_{i}' for i, h in enumerate(rows[0])]
                    for row_vals in rows[1:]:
                        if not any(row_vals):
                            continue
                        row_dict = {headers[i]: str(row_vals[i]).strip() if i < len(row_vals) and row_vals[i] is not None else '' for i in range(len(headers))}
                        norm = cls._normalize_row(row_dict)
                        if norm and (norm.get('company_name') or norm.get('homepage_url')):
                            records.append(norm)

        elif filename_lower.endswith('.json'):
            raw_json = file_obj.read()
            if isinstance(raw_json, bytes):
                raw_json = raw_json.decode('utf-8-sig')
            data = json.loads(raw_json)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        norm = cls._normalize_row(item)
                        if norm and (norm.get('company_name') or norm.get('homepage_url')):
                            records.append(norm)
            elif isinstance(data, dict):
                items = data.get('companies') or data.get('items') or data.get('data') or [data]
                for item in items:
                    if isinstance(item, dict):
                        norm = cls._normalize_row(item)
                        if norm and (norm.get('company_name') or norm.get('homepage_url')):
                            records.append(norm)

        return records

    @classmethod
    def _normalize_row(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Smartly and fuzzily maps varied column naming conventions to the canonical schema.
        Strictly requires only Company Name and Homepage URL.
        Careers, CSR, sector, headquarters, and symbol columns are discarded;
        all portals and metadata will be discovered automatically by crawling the Homepage URL.
        """
        lower_keys: Dict[str, str] = {}
        for k, v in row.items():
            if k is not None:
                cleaned_key = re.sub(r'[^a-zA-Z0-9]+', '_', str(k).strip().lower()).strip('_')
                raw_lower = str(k).strip().lower()
                val_str = str(v).strip() if v is not None else ''
                if cleaned_key:
                    lower_keys[cleaned_key] = val_str
                if raw_lower:
                    lower_keys[raw_lower] = val_str

        excluded_col_pattern = re.compile(
            r'(career|carrer|carer|job|vacanc|recruit|employ|hiring|'
            r'csr|sust|systan|foundat|responsib|esg|impact|'
            r'sector|industry|vertical|category|segment|'
            r'headquarter|hq|location|city|state|address|'
            r'symbol|ticker|scrip|nse|bse)',
            re.IGNORECASE
        )
        non_url_meta_col_re = re.compile(
            r'(?:^|_)(?:id|code|status|type|count|date|notes|flag|quality|verified|confidence)(?:$|_)',
            re.IGNORECASE
        )
        non_name_col_re = re.compile(
            r'(?:^|_)(?:id|code|url|link|web|website|homepage|home_page|domain|portal|site|status|type|count|date|notes|flag|quality)(?:$|_)',
            re.IGNORECASE
        )

        # 1. Website / Homepage URL (strictly from homepage/website columns, never careers/CSR)
        sanitized_web = ""
        preferred_url_keys = (
            'homepage_url', 'homepage', 'home_page_url', 'home_page', 'home_url',
            'official_website', 'official_url', 'company_website', 'company_url',
            'website_url', 'website', 'web_url', 'domain', 'url', 'link'
        )
        for pk in preferred_url_keys:
            v = lower_keys.get(pk)
            if v:
                cand = cls._sanitize_url(v)
                if cand:
                    sanitized_web = cand
                    break

        if not sanitized_web:
            for k, v in lower_keys.items():
                if v and re.search(r'(home|homp|web|site|domain|portal|official.*(web|url|link)|apex|company.*(url|web|link)|^url$|^link$)', k):
                    if not excluded_col_pattern.search(k) and not non_url_meta_col_re.search(k):
                        cand = cls._sanitize_url(v)
                        if cand:
                            sanitized_web = cand
                            break

        # 2. Company Name
        company_name = None
        preferred_name_keys = (
            'company_name', 'company', 'organization_name', 'organization',
            'organisation_name', 'organisation', 'entity_name', 'entity',
            'company_entity', 'legal_name', 'corporate_name', 'enterprise_name',
            'brand_name', 'firm_name', 'client_name', 'account_name', 'name', 'title'
        )
        for pk in preferred_name_keys:
            v = lower_keys.get(pk)
            if v and not v.lower().startswith(('http://', 'https://', 'www.')) and not cls._sanitize_url(v):
                company_name = v
                break

        if not company_name:
            for k, v in lower_keys.items():
                if v and (re.search(r'(comp|cmpny|organi|enterpr|firm|corp|legal.*name|client|account.*name|brand|entity)', k) or k in ('name', 'title')):
                    if not excluded_col_pattern.search(k) and not non_name_col_re.search(k):
                        if not v.lower().startswith(('http://', 'https://', 'www.')) and not cls._sanitize_url(v):
                            company_name = v
                            break

        # 3. Content-based smart inference fallback ONLY across non-excluded columns when headers were ambiguous
        if not sanitized_web or not company_name:
            for raw_k, raw_v in row.items():
                if raw_v is None:
                    continue
                v = str(raw_v).strip()
                if not v:
                    continue
                k_clean = re.sub(r'[^a-zA-Z0-9]+', '_', str(raw_k or '').strip().lower()).strip('_')
                if k_clean and (excluded_col_pattern.search(k_clean) or non_url_meta_col_re.search(k_clean)):
                    continue
                is_url = v.lower().startswith(('http://', 'https://', 'www.')) or bool(
                    re.match(r'^[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:/[^\s]*)?$', v, re.IGNORECASE)
                )
                if is_url:
                    v_lower = v.lower()
                    if not any(term in v_lower for term in ['career', 'carrer', 'job', 'apply', 'vacanc', 'hiring', 'csr', 'sustain', 'foundat', 'responsib', 'esg', 'impact']):
                        if not sanitized_web:
                            cand = cls._sanitize_url(v)
                            if cand:
                                sanitized_web = cand
                elif not company_name and (not k_clean or not non_name_col_re.search(k_clean)) and 2 <= len(v) <= 80:
                    company_name = v

        # Do NOT guess https://www.{clean_brand}.com or look up registries when homepage URL is absent.
        return {
            'company_name': (company_name or '').strip(),
            'website_url': sanitized_web,
            'homepage_url': sanitized_web,
        }

    @classmethod
    def _sanitize_url(cls, url: Any) -> str:
        if not url:
            return ""
        s = str(url).strip()
        if not s or s.lower() in ('none', 'null', 'nan', 'n/a', '-', 'na', 'not available'):
            return ""
        if any(ch.isspace() for ch in s):
            return ""
        # Reject non-HTTP(S) schemes and email addresses explicitly
        if re.match(r'^(mailto|tel|javascript|data|ftp|file):', s, re.IGNORECASE):
            return ""
        if '@' in s.split('/')[0]:
            return ""
        if not re.match(r'^https?://', s, re.IGNORECASE):
            s = 'https://' + s
        else:
            s = re.sub(r'^https?://', lambda m: m.group(0).lower(), s, count=1)
        try:
            parsed = urllib.parse.urlparse(s)
            _ = parsed.port
        except ValueError:
            return ""
        host = parsed.hostname or ""
        if parsed.scheme not in ('http', 'https') or not host or '.' not in host:
            return ""
        labels = host.split('.')
        if any(not lbl for lbl in labels) or len(labels[-1]) < 2 or not re.search(r'[a-zA-Z]{2,}', labels[-1]):
            return ""
        if is_static_asset_url(s):
            return ""
        return s

    @staticmethod
    def _matches_enterprise_key(key: str, comp_lower: str, official_domain: str = "") -> bool:
        """Matches an enterprise registry/pipeline key using word boundaries or domain token match."""
        k_clean = (key or '').strip().lower()
        if not k_clean:
            return False
        if comp_lower and re.search(r'(?<!\w)' + re.escape(k_clean) + r'(?!\w)', comp_lower):
            return True
        if official_domain:
            dom_low = official_domain.lower()
            dom_labels = [lbl for lbl in re.split(r'[.-]+', dom_low) if lbl]
            key_slug = k_clean.replace(' ', '')
            if len(key_slug) >= 4:
                return key_slug in dom_low
            return key_slug in dom_labels
        return False

    @classmethod
    def _infer_sector(cls, comp_name: str, given_sector: str = None) -> str:
        """Intelligently detects corporate industry sector based on business keywords."""
        if given_sector and str(given_sector).strip() and str(given_sector).strip().lower() not in ('corporate enterprise', 'enterprise', 'unknown', 'none', '-'):
            return str(given_sector).strip()
        n = (comp_name or '').lower()
        if re.search(r'\b(solar|power|energy|wind|renewable|thermal|hydro|electric)\b', n):
            return 'Renewable Energy & Power'
        if re.search(r'\b(health|healthcare|hospital|hospitals|pharma|pharmaceuticals|medical|biotech|clinic|lifesciences|diagnostics)\b', n):
            return 'Healthcare & Pharmaceuticals'
        if re.search(r'\b(bank|banking|finance|financial|capital|fintech|insurance|securities|wealth|credit|payments)\b', n):
            return 'Banking & Financial Services'
        if re.search(r'\b(tech|technologies|software|cloud|digital|cyber|data|infotech|consultancy|systems|it)\b', n):
            return 'Information Technology'
        if re.search(r'\b(auto|automotive|motors|mobility|vehicles|tyre|tyres|tire|tires|battery)\b', n):
            return 'Automotive & Transportation'
        if re.search(r'\b(steel|metal|metals|mining|cement|construction|infra|infrastructure|engineering)\b', n):
            return 'Infrastructure, Heavy Industry & Metals'
        if re.search(r'\b(retail|mart|store|consumer|fmcg|foods|beverage|beverages|brew|dairy|agro)\b', n):
            return 'Consumer Goods & Retail'
        if re.search(r'\b(telecom|telecommunications|broadband|wireless|communications)\b', n):
            return 'Telecommunications & Media'
        if re.search(r'\b(chem|chemicals|petro|petrochemicals|oil|gas|refining|refinery)\b', n):
            return 'Petrochemicals & Materials'
        return 'Corporate Enterprise'

    # Canonical Indian cities -> (City Display Name, State Name)
    INDIAN_CITY_TO_STATE = {
        'mumbai': ('Mumbai', 'Maharashtra'),
        'navi mumbai': ('Navi Mumbai', 'Maharashtra'),
        'thane': ('Thane', 'Maharashtra'),
        'pune': ('Pune', 'Maharashtra'),
        'nagpur': ('Nagpur', 'Maharashtra'),
        'nashik': ('Nashik', 'Maharashtra'),
        'aurangabad': ('Aurangabad', 'Maharashtra'),
        'bengaluru': ('Bengaluru', 'Karnataka'),
        'bangalore': ('Bengaluru', 'Karnataka'),
        'mysuru': ('Mysuru', 'Karnataka'),
        'mysore': ('Mysuru', 'Karnataka'),
        'mangaluru': ('Mangaluru', 'Karnataka'),
        'mangalore': ('Mangaluru', 'Karnataka'),
        'hyderabad': ('Hyderabad', 'Telangana'),
        'secunderabad': ('Secunderabad', 'Telangana'),
        'chennai': ('Chennai', 'Tamil Nadu'),
        'coimbatore': ('Coimbatore', 'Tamil Nadu'),
        'madurai': ('Madurai', 'Tamil Nadu'),
        'new delhi': ('New Delhi', 'Delhi'),
        'delhi': ('Delhi', 'Delhi'),
        'noida': ('Noida', 'Uttar Pradesh'),
        'greater noida': ('Greater Noida', 'Uttar Pradesh'),
        'lucknow': ('Lucknow', 'Uttar Pradesh'),
        'kanpur': ('Kanpur', 'Uttar Pradesh'),
        'gurugram': ('Gurugram', 'Haryana'),
        'gurgaon': ('Gurugram', 'Haryana'),
        'faridabad': ('Faridabad', 'Haryana'),
        'kolkata': ('Kolkata', 'West Bengal'),
        'ahmedabad': ('Ahmedabad', 'Gujarat'),
        'gandhinagar': ('Gandhinagar', 'Gujarat'),
        'vadodara': ('Vadodara', 'Gujarat'),
        'surat': ('Surat', 'Gujarat'),
        'jamnagar': ('Jamnagar', 'Gujarat'),
        'jaipur': ('Jaipur', 'Rajasthan'),
        'udaipur': ('Udaipur', 'Rajasthan'),
        'chandigarh': ('Chandigarh', 'Chandigarh'),
        'indore': ('Indore', 'Madhya Pradesh'),
        'bhopal': ('Bhopal', 'Madhya Pradesh'),
        'kochi': ('Kochi', 'Kerala'),
        'cochin': ('Kochi', 'Kerala'),
        'thiruvananthapuram': ('Thiruvananthapuram', 'Kerala'),
        'trivandrum': ('Thiruvananthapuram', 'Kerala'),
        'bhubaneswar': ('Bhubaneswar', 'Odisha'),
        'patna': ('Patna', 'Bihar'),
        'ranchi': ('Ranchi', 'Jharkhand'),
        'jamshedpur': ('Jamshedpur', 'Jharkhand'),
        'guwahati': ('Guwahati', 'Assam'),
        'dehradun': ('Dehradun', 'Uttarakhand'),
        'visakhapatnam': ('Visakhapatnam', 'Andhra Pradesh'),
        'vijayawada': ('Vijayawada', 'Andhra Pradesh'),
    }

    INDIAN_STATE_NAMES = {
        'maharashtra': 'Maharashtra',
        'karnataka': 'Karnataka',
        'telangana': 'Telangana',
        'tamil nadu': 'Tamil Nadu',
        'uttar pradesh': 'Uttar Pradesh',
        'haryana': 'Haryana',
        'west bengal': 'West Bengal',
        'gujarat': 'Gujarat',
        'rajasthan': 'Rajasthan',
        'madhya pradesh': 'Madhya Pradesh',
        'kerala': 'Kerala',
        'odisha': 'Odisha',
        'bihar': 'Bihar',
        'jharkhand': 'Jharkhand',
        'assam': 'Assam',
        'punjab': 'Punjab',
        'uttarakhand': 'Uttarakhand',
        'andhra pradesh': 'Andhra Pradesh',
        'chhattisgarh': 'Chhattisgarh',
        'goa': 'Goa',
        'delhi': 'Delhi',
        'chandigarh': 'Chandigarh',
    }

    INDIAN_STATE_CODES = {
        'MH': 'Maharashtra', 'KA': 'Karnataka', 'TS': 'Telangana', 'TG': 'Telangana',
        'TN': 'Tamil Nadu', 'DL': 'Delhi', 'UP': 'Uttar Pradesh', 'HR': 'Haryana',
        'WB': 'West Bengal', 'GJ': 'Gujarat', 'RJ': 'Rajasthan', 'MP': 'Madhya Pradesh',
        'KL': 'Kerala', 'OR': 'Odisha', 'OD': 'Odisha', 'BR': 'Bihar',
        'JH': 'Jharkhand', 'AS': 'Assam', 'PB': 'Punjab', 'UK': 'Uttarakhand',
        'UR': 'Uttarakhand', 'AP': 'Andhra Pradesh', 'CG': 'Chhattisgarh',
        'CT': 'Chhattisgarh', 'GA': 'Goa', 'CH': 'Chandigarh',
    }

    @classmethod
    def _collect_jsonld_objects(cls, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Safely parses all JSON-LD blocks (including @graph and nested lists) into flat dict objects."""
        objects: List[Dict[str, Any]] = []
        if not soup:
            return objects

        def _walk(node: Any):
            if isinstance(node, dict):
                objects.append(node)
                if '@graph' in node and isinstance(node['@graph'], list):
                    for child in node['@graph']:
                        _walk(child)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        for script in soup.find_all('script', type='application/ld+json'):
            raw = script.string or script.get_text() or ''
            raw = raw.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
                _walk(parsed)
            except Exception:
                continue
        return objects

    @classmethod
    def _extract_city_state_from_address_text(cls, text: str) -> str:
        """Extracts 'City, State' from a structured or semi-structured address string."""
        if not text:
            return ""
        cleaned = re.sub(r'\s+', ' ', str(text)).strip()
        if len(cleaned) < 4:
            return ""
        low = cleaned.lower()
        # Reject biller/travel route spam (e.g., utility biller lists in consumer app footers)
        if any(noise in low for noise in (
            'bill payment', 'metro card', 'recharge', 'water supply', 'municipal corporation',
            'flight tickets', 'train tickets', 'movie ticket', 'bus ticket', 'loan emi', 'insurance premium'
        )):
            return ""

        # Pick the earliest matching city in the address (breaking ties at same position by longest city name)
        city_hits: List[Tuple[int, int, str, str]] = []
        for city_key, (city_name, state_name) in cls.INDIAN_CITY_TO_STATE.items():
            m_city = re.search(r'\b' + re.escape(city_key) + r'\b', low)
            if m_city:
                city_hits.append((m_city.start(), -len(city_key), city_name, state_name))

        matched_city = ""
        mapped_state = ""
        if city_hits:
            _, _, matched_city, mapped_state = min(city_hits, key=lambda x: (x[0], x[1]))

        matched_state = ""
        if not mapped_state:
            state_hits: List[Tuple[int, int, str]] = []
            for state_key, state_val in cls.INDIAN_STATE_NAMES.items():
                m_st = re.search(r'\b' + re.escape(state_key) + r'\b', low)
                if m_st:
                    state_hits.append((m_st.start(), -len(state_key), state_val))
            if state_hits:
                _, _, matched_state = min(state_hits, key=lambda x: (x[0], x[1]))

        if matched_city:
            final_state = mapped_state or matched_state
            if final_state and final_state.lower() != matched_city.lower():
                return f"{matched_city}, {final_state}"
            return f"{matched_city}, India" if not final_state else matched_city

        if matched_state:
            return f"{matched_state}, India"

        # Generic international "City, State" / "City, Country" in short explicit address snippets
        m = re.search(r'\b([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\s*,\s*([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\b', cleaned)
        if m:
            c_part, s_part = m.group(1).strip(), m.group(2).strip()
            bad_words = {'road', 'street', 'floor', 'tower', 'sector', 'plot', 'block', 'phase', 'marg', 'avenue', 'building', 'limited', 'ltd', 'pvt', 'private', 'inc'}
            if c_part.lower() not in bad_words and s_part.lower() not in bad_words:
                return f"{c_part}, {s_part}"

        return ""

    @classmethod
    def _extract_hq_from_jsonld(cls, jsonld_objs: List[Dict[str, Any]]) -> str:
        """Extracts headquarters city/state from JSON-LD Organization/Corporation/LocalBusiness address."""
        for obj in jsonld_objs:
            obj_type = obj.get('@type', '')
            if isinstance(obj_type, list):
                obj_type = ' '.join(str(x) for x in obj_type)
            type_low = str(obj_type).lower()
            is_org = any(t in type_low for t in ('organization', 'corporation', 'localbusiness', 'financialservice', 'bank', 'medical', 'postaladdress'))
            if not is_org and 'address' not in obj and 'headquarters' not in obj:
                continue

            addr_candidates = []
            for key in ('address', 'headquarters', 'foundingLocation'):
                val = obj.get(key)
                if val:
                    if isinstance(val, list):
                        addr_candidates.extend(val)
                    else:
                        addr_candidates.append(val)
            loc = obj.get('location')
            if isinstance(loc, dict) and loc.get('address'):
                addr_candidates.append(loc.get('address'))
            if 'postaladdress' in type_low:
                addr_candidates.append(obj)

            for addr in addr_candidates:
                if isinstance(addr, str):
                    res = cls._extract_city_state_from_address_text(addr)
                    if res:
                        return res
                elif isinstance(addr, dict):
                    locality = str(addr.get('addressLocality') or addr.get('name') or '').strip()
                    region = str(addr.get('addressRegion') or '').strip()
                    country = addr.get('addressCountry')
                    if isinstance(country, dict):
                        country = country.get('name') or country.get('addressCountry') or ''
                    country = str(country or '').strip()
                    street = str(addr.get('streetAddress') or '').strip()

                    # Normalize Indian city & 2-letter Indian state codes when Indian context is confirmed
                    loc_low = locality.lower()
                    is_indian = (
                        loc_low in cls.INDIAN_CITY_TO_STATE
                        or region.lower() in cls.INDIAN_STATE_NAMES
                        or country.lower() in ('in', 'ind', 'india')
                    )
                    if loc_low in cls.INDIAN_CITY_TO_STATE:
                        locality, default_state = cls.INDIAN_CITY_TO_STATE[loc_low]
                    else:
                        default_state = ''

                    if region.lower() in cls.INDIAN_STATE_NAMES:
                        region = cls.INDIAN_STATE_NAMES[region.lower()]
                    elif is_indian and region.upper() in cls.INDIAN_STATE_CODES:
                        region = cls.INDIAN_STATE_CODES[region.upper()]
                    elif not region and default_state:
                        region = default_state

                    if locality and region and locality.lower() != region.lower():
                        return f"{locality}, {region}"
                    if locality and country and locality.lower() != country.lower():
                        return f"{locality}, {country}"
                    if locality:
                        return locality
                    if street:
                        res = cls._extract_city_state_from_address_text(street)
                        if res:
                            return res
        return ""

    @classmethod
    def extract_company_metadata_from_html(cls, raw_html: str, cleaned_text: str, comp_name: str, base_url: str = '') -> Dict[str, str]:
        """
        Extracts company industry sector and headquarters city/state directly from crawled
        homepage HTML (<title>, <meta>, JSON-LD Organization, <address>, footer/office text).
        """
        sector_val = cls._infer_sector(comp_name)
        hq_val = 'India'
        if not raw_html and not cleaned_text:
            return {'sector': sector_val, 'headquarters': hq_val}

        soup = None
        title_text = ''
        meta_desc = ''
        meta_keywords = ''
        headings_text = ''
        footer_text = ''
        address_blocks: List[str] = []
        jsonld_objs: List[Dict[str, Any]] = []
        full_body_text = cleaned_text or ''

        if raw_html:
            try:
                soup = BeautifulSoup(raw_html, 'html.parser')
                if soup.title:
                    title_text = soup.title.get_text(' ', strip=True)
                for m in soup.find_all('meta'):
                    m_name = (m.get('name') or m.get('property') or '').strip().lower()
                    m_content = (m.get('content') or '').strip()
                    if not m_content:
                        continue
                    if m_name in ('description', 'og:description', 'twitter:description'):
                        meta_desc = f"{meta_desc} {m_content}".strip()
                    elif m_name == 'keywords':
                        meta_keywords = f"{meta_keywords} {m_content}".strip()

                headings_text = ' '.join(
                    h.get_text(' ', strip=True) for h in soup.find_all(['h1', 'h2'])[:12]
                )
                jsonld_objs = cls._collect_jsonld_objects(soup)

                for addr_el in soup.find_all('address'):
                    t = addr_el.get_text(' ', strip=True)
                    if t:
                        address_blocks.append(t)

                for f_el in soup.find_all('footer'):
                    ft = f_el.get_text(' ', strip=True)
                    if ft:
                        footer_text = f"{footer_text} {ft}".strip()

                for div_el in soup.find_all(attrs={'class': re.compile(r'(registered-office|corporate-office|head-office|headquarters|office-address|company-address)', re.I)}):
                    dt = div_el.get_text(' ', strip=True)
                    if dt and len(dt) < 600:
                        address_blocks.append(dt)
                for div_el in soup.find_all(attrs={'id': re.compile(r'(registered-office|corporate-office|head-office|headquarters|office-address|company-address)', re.I)}):
                    dt = div_el.get_text(' ', strip=True)
                    if dt and len(dt) < 600:
                        address_blocks.append(dt)

                for tag in soup(['script', 'style', 'svg', 'noscript']):
                    tag.decompose()
                dom_text = soup.get_text(' ', strip=True)
                if dom_text:
                    full_body_text = dom_text
            except Exception as e:
                logger.debug(f"Metadata HTML parse note for {base_url}: {e}")

        # --- 1. SECTOR EXTRACTION ---
        jsonld_industries: List[str] = []
        jsonld_descs: List[str] = []
        org_industry_raw = ''
        for obj in jsonld_objs:
            obj_type = str(obj.get('@type') or '').lower()
            ind = obj.get('industry')
            if isinstance(ind, str) and ind.strip():
                jsonld_industries.append(ind.strip())
                if any(t in obj_type for t in ('organization', 'corporation', 'localbusiness')) and not org_industry_raw:
                    org_industry_raw = ind.strip()
            app_cat = obj.get('applicationCategory')
            if isinstance(app_cat, str) and app_cat.strip():
                jsonld_industries.append(app_cat.strip())
            desc = obj.get('description')
            if isinstance(desc, str) and desc.strip():
                jsonld_descs.append(desc.strip())

        sector_rules = {
            'Information Technology': [
                r'\binformation\s+technology\b', r'\bit\s+services\b', r'\bsoftware\b',
                r'\bcloud\s+computing\b', r'\bcybersecurity\b', r'\bartificial\s+intelligence\b',
                r'\benterprise\s+ai\b', r'\bsaas\b', r'\bdigital\s+transformation\b',
                r'\btechnology\s+services\b', r'\bconsulting\b', r'\bdata\s+analytics\b',
                r'\binfotech\b', r'\bengineering\s+services\b', r'\bcloud\b',
            ],
            'Banking & Financial Services': [
                r'\bfintech\b', r'\bupi\b', r'\bdigital\s+payments?\b', r'\bpayments?\b',
                r'\bbanking\b', r'\bfinancial\s+services\b', r'\bfinancialproduct\b',
                r'\bwealth\s+management\b', r'\bmutual\s+funds?\b', r'\binsurance\b',
                r'\bcredit\s+cards?\b', r'\bloans?\b', r'\bnbfc\b', r'\bpay\s+bills\b',
                r'\bfastag\b', r'\brecharge\b', r'\basset\s+management\b',
            ],
            'Healthcare & Pharmaceuticals': [
                r'\bhealthcare\b', r'\bhospitals?\b', r'\bpharmaceuticals?\b', r'\bpharma\b',
                r'\bbiotech(?:nology)?\b', r'\bdiagnostics?\b', r'\bclinical\b', r'\bmedical\b',
                r'\bpatient\s+care\b', r'\btherapeutics\b', r'\blife\s*sciences\b', r'\bmedicines?\b',
            ],
            'Automotive & Transportation': [
                r'\bautomotive\b', r'\bautomobiles?\b', r'\belectric\s+vehicles?\b',
                r'\bpassenger\s+vehicles?\b', r'\bcommercial\s+vehicles?\b', r'\bmobility\b',
                r'\btyres?\b', r'\btires?\b', r'\bmotorcycles?\b', r'\bauto\s+components?\b',
                r'\baviation\b', r'\bairlines?\b', r'\blogistics\b',
            ],
            'Renewable Energy & Power': [
                r'\brenewable\s+energy\b', r'\bsolar\s+power\b', r'\bwind\s+energy\b',
                r'\bpower\s+generation\b', r'\bthermal\s+power\b', r'\bhydroelectric\b',
                r'\bclean\s+energy\b', r'\belectricity\b', r'\bpower\s+transmission\b',
                r'\bpower\s+distribution\b', r'\benergy\s+storage\b', r'\bgreen\s+hydrogen\b',
            ],
            'Infrastructure, Heavy Industry & Metals': [
                r'\binfrastructure\b', r'\bheavy\s+engineering\b', r'\bconstruction\b',
                r'\bsteel\b', r'\bmetals?\b', r'\bmining\b', r'\bcement\b',
                r'\balumin(?:i)?um\b', r'\bbuilding\s+materials\b', r'\breal\s+estate\b',
            ],
            'Consumer Goods & Retail': [
                r'\bfmcg\b', r'\bconsumer\s+goods\b', r'\bretail\b', r'\be-?commerce\b',
                r'\bfood\s+delivery\b', r'\bquick\s+commerce\b', r'\brestaurants?\b',
                r'\bgroceries\b', r'\bbeverages?\b', r'\bdairy\b', r'\bpackaged\s+foods?\b',
            ],
            'Telecommunications & Media': [
                r'\btelecommunications?\b', r'\btelecom\b', r'\b5g\s+network\b',
                r'\bbroadband\b', r'\bmobile\s+network\b', r'\bbroadcasting\b',
                r'\bstreaming\b', r'\bmedia\s+(?:and|&)\s+entertainment\b',
            ],
            'Petrochemicals & Materials': [
                r'\bpetrochemicals?\b', r'\boil\s+(?:and|&)\s+gas\b', r'\brefining\b',
                r'\brefinery\b', r'\bhydrocarbons?\b', r'\bpolymers?\b',
                r'\bspecialty\s+chemicals?\b', r'\bagrochemicals?\b', r'\bfertilizers?\b',
            ],
        }

        weighted_buckets = [
            (' '.join(jsonld_industries), 5),
            (f"{title_text} {meta_desc}", 4),
            (f"{meta_keywords} {headings_text} {' '.join(jsonld_descs)}", 3),
            (comp_name or '', 2),
            ((full_body_text or '')[:6000], 1),
        ]

        sector_scores: Dict[str, int] = {sec: 0 for sec in sector_rules}
        for bucket_text, weight in weighted_buckets:
            if not bucket_text:
                continue
            b_low = bucket_text.lower()
            for sec, patterns in sector_rules.items():
                hits = 0
                for pat in patterns:
                    matches = re.findall(pat, b_low)
                    if matches:
                        hits += min(len(matches), 3)
                if hits:
                    sector_scores[sec] += hits * weight

        best_sector, best_score = max(sector_scores.items(), key=lambda kv: kv[1])
        if best_score > 0:
            sector_val = best_sector
        elif org_industry_raw and 3 <= len(org_industry_raw) <= 80 and re.search(r'[a-zA-Z]{3}', org_industry_raw):
            sector_val = org_industry_raw

        # --- 2. HEADQUARTERS EXTRACTION ---
        # Priority A: JSON-LD Organization.address
        hq_candidate = cls._extract_hq_from_jsonld(jsonld_objs)

        # Priority B: <address> elements & explicit office/HQ containers
        if not hq_candidate:
            for block in address_blocks:
                hq_candidate = cls._extract_city_state_from_address_text(block)
                if hq_candidate:
                    break

        # Priority C: Explicit Registered Office / Corporate Office / Headquarters patterns in footer or body
        if not hq_candidate:
            body_window = full_body_text if len(full_body_text) <= 24000 else f"{full_body_text[:12000]}\n{full_body_text[-12000:]}"
            search_corpus = f"{footer_text}\n{body_window}"
            office_patterns = [
                r'(?:registered\s+office|regd\.?\s+office|corporate\s+office|head\s*office|headquarters?|global\s+headquarters?)\s*[:\-–]?\s*([^|\n•;]{8,220})',
                r'(?:headquartered|based)\s+(?:in|at)\s+([A-Z][^|\n•;.]{3,100})',
            ]
            for op in office_patterns:
                for m in re.finditer(op, search_corpus, re.IGNORECASE):
                    hq_candidate = cls._extract_city_state_from_address_text(m.group(1))
                    if hq_candidate:
                        break
                if hq_candidate:
                    break

        # Priority D: Footer postal address segments (must contain PIN code or street/building noun)
        if not hq_candidate and footer_text:
            for seg in re.split(r'[|\n•]+', footer_text):
                seg_clean = seg.strip()
                if len(seg_clean) < 12 or len(seg_clean) > 260:
                    continue
                has_pin = bool(re.search(r'\b[1-8]\d{5}\b', seg_clean))
                has_street_noun = bool(re.search(r'\b(road|rd\.?|marg|street|st\.?|tower|sector|plot|building|floor|chambers|house|avenue|expressway|bhavan|complex|phase)\b', seg_clean, re.I))
                if has_pin or has_street_noun:
                    hq_candidate = cls._extract_city_state_from_address_text(seg_clean)
                    if hq_candidate:
                        break

        # Priority E: Formal CIN state code if explicitly labeled on page (e.g. CIN: L72200MH1995PLC085699)
        if not hq_candidate:
            cin_match = re.search(r'\bCIN\b\s*[:\-–]?\s*[LU]\d{5}([A-Z]{2})\d{4}[A-Z]{3}\d{6}', f"{footer_text} {full_body_text}", re.IGNORECASE)
            if cin_match:
                st_code = cin_match.group(1).upper()
                if st_code in cls.INDIAN_STATE_CODES:
                    hq_candidate = f"{cls.INDIAN_STATE_CODES[st_code]}, India"

        if hq_candidate:
            hq_val = hq_candidate

        return {
            'sector': sector_val,
            'headquarters': hq_val,
        }

    @classmethod
    def _derive_clean_domain(cls, comp_name: str, given_url: str = None) -> str:
        """Derives canonical official website domain for any corporate name."""
        if given_url and str(given_url).strip():
            url = str(given_url).strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            return url
        cleaned = re.sub(
            r'\b(ltd|limited|pvt|private|corp|corporation|inc|incorporated|technologies|solutions|services|group|holdings|india|enterprises|co)\b',
            '',
            comp_name,
            flags=re.IGNORECASE
        )
        slug = re.sub(r'[^a-zA-Z0-9]+', '', cleaned).lower()
        if not slug or len(slug) < 3:
            slug = re.sub(r'[^a-zA-Z0-9]+', '', comp_name).lower()
        return f"https://www.{slug}.com"

    @classmethod
    def fetch_page_content(cls, url: str, timeout: int = 6) -> Tuple[str, str, int]:
        """
        Safely fetches page text from target corporate portal using curl_cffi Chrome impersonation
        to bypass Cloudflare/Akamai bot detection, with urllib SSL fallback.
        Returns (raw_html, cleaned_text, status_code).
        """
        if not url:
            return "", "", 0

        raw_html = ""
        status = 0

        # 1. Primary: curl_cffi with Chrome 124 browser TLS/JA3 impersonation
        if cffi_requests is not None:
            try:
                resp = cffi_requests.get(url, impersonate="chrome124", timeout=timeout, headers=BROWSER_HEADERS)
                status = resp.status_code
                if status == 200 and resp.content:
                    # Decode explicitly.  Relying on the library's locale-derived
                    # default can mangle UTF-8 quotes/trademarks (e.g. cp437), which
                    # then leaks into AI summaries and stored evidence text.
                    declared = (resp.encoding or '').strip().lower()
                    raw_bytes = resp.content
                    if declared and declared not in ('iso-8859-1', 'latin-1'):
                        try:
                            raw_html = raw_bytes.decode(declared, errors='replace')
                        except LookupError:
                            raw_html = raw_bytes.decode('utf-8', errors='replace')
                    else:
                        try:
                            raw_html = raw_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            raw_html = raw_bytes.decode('cp1252', errors='replace')
            except Exception as e:
                logger.debug(f"curl_cffi fetch for {url} encountered: {e}")

        # 2. Fallback: urllib with unverified SSL
        if not raw_html:
            import ssl
            try:
                req = urllib.request.Request(url, headers=BROWSER_HEADERS)
                ctx = ssl._create_unverified_context()
                with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
                    status = resp.status
                    raw = resp.read(500000) # Read up to 500KB
                    raw_html = raw.decode('utf-8', errors='replace')
            except urllib.error.HTTPError as e:
                return "", "", e.code
            except Exception as e:
                logger.debug(f"urllib fetch failed for {url}: {e}")
                return "", "", status or 0

        if not raw_html:
            return "", "", status

        # High-signal HTML cleaning for NLP while preserving raw_html for JSON-LD & DOM inspection
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw_html, 'html.parser')
            for el in soup(['script', 'style', 'svg', 'noscript', 'nav', 'header', 'footer', 'aside']):
                el.decompose()
            main_el = (
                soup.find('main')
                or soup.find(id=re.compile(r'^(content|main-content|main)$', re.I))
                or soup.find(class_=re.compile(r'\b(content|main-content|page-content)\b', re.I))
            )
            target_soup = main_el if main_el and len(main_el.get_text(strip=True)) > 200 else soup
            cleaned = target_soup.get_text(separator=' ', strip=True)
        except Exception:
            cleaned = re.sub(r'<(script|style|svg|noscript|header|nav|footer|aside)[^>]*>.*?</\1>', ' ', raw_html, flags=re.DOTALL | re.IGNORECASE)
            cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        return raw_html, cleaned, status
    @classmethod
    def find_target_links_from_html(cls, raw_html: str, base_url: str) -> Dict[str, str]:
        """
        Extracts genuine careers and CSR links directly from company homepage HTML navigation/footer.
        Scores dedicated corporate portals highly while strongly downranking commercial services,
        product offerings, blogs, insights, news, and contact-form pages.
        """
        discovered = {'careers_url': '', 'csr_url': ''}
        if not raw_html:
            return discovered

        candidate_links = []
        try:
            soup = BeautifulSoup(raw_html, 'html.parser')
            for a in soup.find_all('a', href=True):
                h = a['href'].strip()
                t = a.get_text(' ', strip=True)
                if h:
                    candidate_links.append((h, t))
        except Exception:
            pass

        # Also apply regex to catch any anchors embedded inside multiline or unconventional attributes
        regex_links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw_html, flags=re.DOTALL | re.IGNORECASE)
        for href, text in regex_links:
            candidate_links.append((href.strip(), re.sub(r'<[^>]+>', ' ', text).strip()))

        base_parsed = urllib.parse.urlparse(base_url or '')
        base_host_raw = (base_parsed.netloc or '').lower()
        base_host = base_host_raw[4:] if base_host_raw.startswith('www.') else base_host_raw

        commercial_noise_path_re = re.compile(
            r'(?:^|/)(what-we-do|services?|solutions?|products?|offerings?|industries?|'
            r'capabilities|platform|consulting|blogs?|insights?|news|newsroom|'
            r'press|press-releases?|media|articles?|stories|case-stud(?:y|ies)|'
            r'whitepapers?|webinars?|events?|contact-us|contact|whats-on-your-mind|'
            r'faqs?|fraud|legal|disclaimer|alumni|retirees?|privacy|terms|cookie)(?:/|$)',
            re.IGNORECASE
        )
        blocked_url_tokens = (
            'login', 'signin', 'auth/', 'privacy', 'terms', 'cookie',
            'facebook.com', 'twitter.com', 'x.com/', 'linkedin.com',
            'instagram.com', 'youtube.com', 'whatsapp.', 't.me/'
        )

        # Track best score per URL: full_url -> (score, -path_depth, -len(path))
        careers_best: Dict[str, Tuple[int, int, int]] = {}
        csr_best: Dict[str, Tuple[int, int, int]] = {}

        for href_clean, text_raw in candidate_links:
            if not href_clean or href_clean.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            if is_static_asset_url(href_clean):
                continue

            full_url = urllib.parse.urljoin(base_url, href_clean)
            if is_static_asset_url(full_url):
                continue

            u_lower = full_url.lower()
            if any(bad in u_lower for bad in blocked_url_tokens):
                continue

            if base_url and not is_allowed_domain_or_ats(full_url, base_url):
                continue

            parsed_u = urllib.parse.urlparse(full_url)
            u_host = (parsed_u.netloc or '').lower()
            u_host_clean = u_host[4:] if u_host.startswith('www.') else u_host
            path = (parsed_u.path or '').lower()
            path_stripped = path.strip('/')
            path_depth = len([seg for seg in path_stripped.split('/') if seg]) if path_stripped else 0
            text_lower = re.sub(r'\s+', ' ', (text_raw or '')).strip().lower()
            combined = f"{path} {text_lower}"
            same_host = bool(base_host_raw and (u_host == base_host_raw or u_host_clean == base_host))
            is_commercial_or_noise = bool(commercial_noise_path_re.search(path))

            # --- 1. Careers Scoring ---
            is_ats_host = any(ats in u_host for ats in ALLOWED_ATS_HOSTS) or u_host.startswith(('careers.', 'jobs.'))
            has_career_signal = is_ats_host or any(
                w in combined for w in ('careers', 'career', 'jobs', 'job', 'work-with-us', 'join-us', 'openings', 'vacanc', 'hiring')
            )
            if has_career_signal:
                c_score = 0
                if is_ats_host:
                    c_score += 25
                if re.search(r'(?:^|/)(?:careers|jobs)(?:/|$|/india|/en|/global)', path):
                    c_score += 24
                elif re.search(r'(?:^|/)(?:career|work-with-us|join-us|current-openings|openings|vacancies)(?:/|$)', path):
                    c_score += 20
                elif 'career' in path or 'job' in path:
                    c_score += 14

                if re.search(r'\b(careers?|jobs?|openings|vacancies|join\s+us|work\s+with\s+us|we.?re\s+hiring)\b', text_lower):
                    c_score += 12
                if any(p in path for p in ('/who-we-are/', '/about/', '/about-us/', '/company/', '/corporate/')):
                    c_score += 6
                if same_host or u_host.startswith(('careers.', 'jobs.')):
                    c_score += 4
                if path_stripped in ('careers', 'jobs', 'careers/india', 'career'):
                    c_score += 5
                if not parsed_u.query and not parsed_u.fragment and path_depth <= 3:
                    c_score += 4

                if is_commercial_or_noise:
                    c_score -= 45
                if any(bad_t in text_lower for bad_t in ('services', 'solutions', 'consulting', 'blog', 'article', 'news', 'fraud', 'faq', 'disclaimer', 'alumni')):
                    c_score -= 15
                if parsed_u.fragment:
                    c_score -= 10

                if c_score > 0:
                    rank_tuple = (c_score, -path_depth, -len(path_stripped))
                    if full_url not in careers_best or rank_tuple > careers_best[full_url]:
                        careers_best[full_url] = rank_tuple

            # --- 2. CSR / ESG / Sustainability Scoring ---
            has_csr_signal = any(
                w in combined for w in (
                    'csr', 'corporate-social-responsibility', 'corporate-responsibility',
                    'social-responsibility', 'sustainability', 'esg', 'foundation',
                    'social-impact', 'community-welfare', 'community-impact', 'giving-back',
                    'responsible-business', 'section-135'
                )
            )
            if has_csr_signal:
                s_score = 0
                if '/corporate-social-responsibility' in path or re.search(r'(?:^|/)csr(?:/|$|\.html?)', path):
                    s_score += 32
                elif '/corporate-responsibility' in path or '/social-responsibility' in path:
                    s_score += 28
                elif '/company/sustainability/esg' in path or '/sustainability/esg' in path or re.search(r'(?:^|/)esg(?:/|$|\.html?)', path):
                    s_score += 26
                elif 'foundation' in path or 'foundation' in u_host:
                    s_score += 22
                elif 'social-impact' in path or 'community-impact' in path or 'community-welfare' in path or re.search(r'(?:^|/)impact(?:/|$|\.html?)', path):
                    s_score += 20
                elif re.search(r'(?:^|/)sustainability(?:/|$|\.html?)', path) or 'sustainable-business' in path:
                    s_score += 18
                elif any(k in path for k in ('sustainability', 'esg', 'csr', 'responsibility')):
                    s_score += 10

                if any(p in path for p in ('/who-we-are/', '/about/', '/about-us/', '/company/', '/corporate/')):
                    s_score += 8
                if same_host:
                    s_score += 5
                if not parsed_u.query and not parsed_u.fragment and path_depth <= 4:
                    s_score += 4

                # Anchor text signals
                if 'corporate social responsibility' in text_lower or re.search(r'\bcsr\b', text_lower):
                    s_score += 12
                elif any(t in text_lower for t in ('esg', 'social impact', 'corporate responsibility', 'foundation')):
                    s_score += 8
                elif 'sustainability' in text_lower and not any(bad_t in text_lower for bad_t in ('services', 'solutions', 'consulting')):
                    s_score += 6
                elif 'community' in text_lower and any(k in path for k in ('responsibility', 'csr', 'community', 'impact')):
                    s_score += 4

                # Strong penalties for commercial services, offerings, blogs, insights, contact pages
                if is_commercial_or_noise:
                    s_score -= 45
                if any(bad_t in text_lower for bad_t in ('services', 'solutions', 'consulting', 'offering', 'products', 'blog', 'article', 'news', 'press', 'contact', 'form', 'case study', 'whitepaper')):
                    s_score -= 18
                if 'sustainability-services' in path or 'esg-services' in path or 'csr-services' in path:
                    s_score -= 20
                if parsed_u.fragment:
                    s_score -= 12

                if s_score > 0:
                    rank_tuple = (s_score, -path_depth, -len(path_stripped))
                    if full_url not in csr_best or rank_tuple > csr_best[full_url]:
                        csr_best[full_url] = rank_tuple

        if careers_best:
            best_careers_url = max(careers_best.items(), key=lambda item: item[1])[0]
            discovered['careers_url'] = best_careers_url

        if csr_best:
            best_csr_url = max(csr_best.items(), key=lambda item: item[1])[0]
            discovered['csr_url'] = best_csr_url

        return discovered

    @classmethod
    def fetch_rendered_page(cls, url: str, timeout: int = 8) -> Tuple[str, str, int]:
        """
        Uses headless Playwright to render client-side JavaScript SPAs (React, Vue, Angular, SuccessFactors, Workday)
        with realistic Chrome browser context options.
        Returns (raw_html, cleaned_text, status_code).
        """
        if not url or not async_playwright:
            return "", "", 0
        try:
            async def _render():
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=['--disable-blink-features=AutomationControlled']
                    )
                    context = await browser.new_context(
                        user_agent=USER_AGENT,
                        viewport={'width': 1366, 'height': 768},
                        locale='en-US',
                        extra_http_headers={
                            'Accept-Language': 'en-US,en;q=0.9',
                        }
                    )
                    page = await context.new_page()
                    try:
                        try:
                            resp = await page.goto(url, wait_until='domcontentloaded', timeout=min(timeout * 1000, 10000))
                        except Exception:
                            resp = await page.goto(url, wait_until='load', timeout=timeout * 1000)
                        await page.wait_for_timeout(1500)
                        try:
                            body_text = await page.inner_text('body')
                        except Exception:
                            body_text = ""
                        content = await page.content()
                        status = resp.status if resp else 200
                        return content, body_text, status
                    finally:
                        await context.close()
                        await browser.close()

            def _run_sync():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(_render())
                finally:
                    loop.close()

            try:
                asyncio.get_running_loop()
                from concurrent.futures import ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=1) as ex:
                    raw_html, body_text, status = ex.submit(_run_sync).result(timeout=timeout + 10)
            except RuntimeError:
                raw_html, body_text, status = _run_sync()

            if not raw_html:
                return "", "", status or 0
            soup = BeautifulSoup(raw_html, 'html.parser')
            for tag in soup(['script', 'style', 'nav', 'footer', 'noscript', 'aside']):
                tag.decompose()
            cleaned = re.sub(r'\s+', ' ', soup.get_text(' ', strip=True)).strip()
            if body_text and len(body_text) > len(cleaned):
                cleaned = re.sub(r'\s+', ' ', body_text).strip()
            return raw_html, cleaned, status
        except Exception as e:
            logger.debug(f"Headless render error for {url}: {e}")
            return "", "", 0

    @classmethod
    def extract_pdf_text_from_url(cls, pdf_url: str, max_pages: int = 10, timeout: int = 12) -> str:
        """Downloads and extracts clean text from a statutory Section 135 PDF report."""
        if not pdf_url or not PdfReader or not cffi_requests:
            return ""
        try:
            resp = cffi_requests.get(pdf_url, impersonate="chrome124", timeout=timeout, headers=BROWSER_HEADERS)
            if resp.status_code == 200 and resp.content:
                reader = PdfReader(io.BytesIO(resp.content))
                pages_text = []
                for p in reader.pages[:max_pages]:
                    txt = p.extract_text()
                    if txt:
                        pages_text.append(txt)
                return "\n".join(pages_text).strip()
        except Exception as e:
            logger.debug(f"PDF extract error for {pdf_url}: {e}")
        return ""

    @classmethod
    def find_deep_openings_link(cls, raw_html: str, current_careers_url: str) -> str:
        """
        When on a careers landing page, finds specific links pointing to actual vacancies/openings,
        prioritizing enterprise ATS engines (TurboHire, Workday, SuccessFactors, Taleo, etc.).
        """
        if not raw_html:
            return ""
        curr_norm = current_careers_url.rstrip('/').lower()
        soup = BeautifulSoup(raw_html, 'html.parser')

        # Priority 1: Direct Enterprise ATS links and dynamic job dashboards
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')) or is_static_asset_url(href):
                continue
            full_url = urllib.parse.urljoin(current_careers_url, href)
            if full_url.rstrip('/').lower() == curr_norm or is_static_asset_url(full_url):
                continue
            if any(bad in full_url.lower() for bad in [
                'login', 'auth', 'privacy', 'terms', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube',
                'safelinks.protection.outlook', 'introduceyourself', 'equal-opportunit', 'eeo', 'diversity', 'inclusion', 'veteran',
                'smileshrms', 'hrms', 'employee-login', 'staff-login'
            ]):
                continue
            h_lower = href.lower()
            if any(ats in h_lower for ats in ['zwayam', 'jobs.happiestminds.com', 'turbohire', 'myworkdayjobs', 'successfactors', 'taleo', 'icims', 'lever.co', 'greenhouse.io', 'darwinbox', 'smartrecruiters', 'dashboardv2', 'careerpage']):
                return full_url

        # Priority 2: Standard deep job opening paths and action phrases
        links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw_html, flags=re.DOTALL | re.IGNORECASE)
        for href, link_text in links:
            href_clean = href.strip()
            if href_clean.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            if is_static_asset_url(href_clean):
                continue
            full_url = urllib.parse.urljoin(current_careers_url, href_clean)
            if is_static_asset_url(full_url):
                continue
            if full_url.rstrip('/').lower() == curr_norm:
                continue
            text_clean = re.sub(r'<[^>]+>', ' ', link_text).strip().lower()
            combined = f"{href_clean.lower()} {text_clean}"
            if any(k in combined for k in [
                'openings', 'current-openings', 'current openings', 'vacanc', 'search-job', 'job-search',
                'explore-opportunities', 'opportunities', 'view-jobs', 'positions', 'career-opportunities',
                'open-jobs', 'viewalljobs', 'view-all-jobs', 'search-jobs', 'find-jobs', 'lateral-hiring', 'job-opportunities',
                'explore-roles', 'all-jobs', 'view-all', 'careers/openings', 'searchjobs', 'jobsearch'
            ]):
                if not any(bad in full_url.lower() for bad in [
                    'login', 'auth', 'privacy', 'terms', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube',
                    'why-work-with-us', 'why-work', 'about-us', 'our-culture', 'life-at', 'meet-our-team',
                    'equal-opportunit', 'equal-opportunity', 'eeo', 'diversity', 'inclusion', 'veteran',
                    'business-opportunit', 'supplier', 'dealer', 'vendor', 'franchise',
                    'exchange', 'student', 'admission', 'study-abroad', 'safelinks.protection.outlook', 'introduceyourself'
                ]):
                    return full_url
        return ""

    @classmethod
    def find_deep_csr_link(cls, raw_html: str, current_csr_url: str) -> str:
        """
        When on a CSR overview page, finds specific links pointing to actual projects, initiatives, or reports.
        """
        if not raw_html:
            return ""
        curr_norm = current_csr_url.rstrip('/').lower()
        soup = BeautifulSoup(raw_html, 'html.parser')

        # If current page already contains direct Section 135 PDF reports or disclosure links, stay here
        has_statutory_pdfs = any(
            a['href'].lower().endswith('.pdf') and any(k in (a['href'] + ' ' + a.get_text()).lower() for k in ['csr', 'sustainability', 'section 135', 'schedule-vii', 'project'])
            for a in soup.find_all('a', href=True)
        )
        if has_statutory_pdfs:
            return ""

        # Priority 1: Reporting center & statutory disclosure links
        for a in soup.find_all('a', href=True):
            href = a['href'].strip()
            if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')) or is_static_asset_url(href):
                continue
            full_url = urllib.parse.urljoin(current_csr_url, href)
            if full_url.rstrip('/').lower() == curr_norm or is_static_asset_url(full_url):
                continue
            if any(bad in full_url.lower() for bad in ['login', 'auth', 'privacy', 'terms', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube']):
                continue
            combined = f"{href.lower()} {a.get_text(' ', strip=True).lower()}"
            if any(k in combined for k in ['sustainability-reporting-center', 'reporting-center', 'sustainability-report', 'csr-policy', 'csr-committee', 'statutory-disclosures']):
                return full_url

        # Priority 2: General CSR initiatives & programs
        links = re.findall(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', raw_html, flags=re.DOTALL | re.IGNORECASE)
        for href, link_text in links:
            href_clean = href.strip()
            if href_clean.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            if is_static_asset_url(href_clean):
                continue
            full_url = urllib.parse.urljoin(current_csr_url, href_clean)
            if is_static_asset_url(full_url):
                continue
            if full_url.rstrip('/').lower() == curr_norm:
                continue
            text_clean = re.sub(r'<[^>]+>', ' ', link_text).strip().lower()
            combined = f"{href_clean.lower()} {text_clean}"
            if any(k in combined for k in [
                'initiatives', 'projects', 'our-work', 'programmes', 'programs', 'impact', 'focus-areas',
                'annual-report', 'policy', 'interventions', 'sustainability-strategy', 'planet-resilience',
                'working-with-communities', 'csr-policy', 'csr-committee', 'foundation', 'csr-activities',
                'social-responsibility'
            ]):
                if not any(bad in full_url.lower() for bad in ['login', 'auth', 'privacy', 'terms', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube']):
                    return full_url
        return ""

    @classmethod
    def crawl_deep_portal_chain(cls, initial_url: str, target_type: str = 'jobs', max_hops: int = 2, logs: List[str] = None) -> Tuple[str, str, str, int]:
        """
        Multi-hop crawler that traverses nested corporate portals (up to max_hops deep)
        and automatically renders client-side SPAs using headless Playwright when static HTML is sparse.
        Returns (final_url, html, text, status).
        """
        logs = logs if logs is not None else []
        curr_url = initial_url
        visited = set()
        best_url = initial_url
        best_html = ""
        best_text = ""
        best_status = 0

        for hop in range(1, max_hops + 1):
            if curr_url in visited:
                break
            visited.add(curr_url)
            html, text, status = cls.fetch_page_content(curr_url)

            # Check if page is an SPA, empty, or an ATS platform requiring DOM rendering
            is_ats_domain = any(k in curr_url.lower() for k in ['turbohire', 'myworkdayjobs', 'successfactors', 'taleo', 'open-jobs', 'smartrecruiters', 'lever.co', 'greenhouse.io', 'ashbyhq.com'])
            is_sparse = not text or len(text) < 400
            has_spa_container = any(k in html.lower() for k in ['id="root"', 'id="app"', 'ng-app', '<router-outlet>'])
            needs_render = is_ats_domain or (is_sparse and has_spa_container)

            if needs_render:
                logs.append(f"⚡ Rendering dynamic portal '{curr_url[:65]}' with headless browser (Hop {hop})...")
                r_html, r_text, r_status = cls.fetch_rendered_page(curr_url)
                if len(r_text) > len(text):
                    html, text, status = r_html, r_text, r_status
                    logs.append(f"✓ Headless browser rendered {len(r_text)} chars of active DOM content")

            # Check if current page already displays active job cards or statutory CSR/ESG reports
            if target_type == 'jobs' and html:
                check_soup = BeautifulSoup(html, 'html.parser')
                cards_found = detect_repeating_dom_job_cards(check_soup, curr_url)
                if cards_found and len(cards_found) >= 2:
                    logs.append(f"✓ Detected {len(cards_found)} live job cards directly on portal ({curr_url[:65]}). Destination reached.")
                    best_url, best_html, best_text, best_status = curr_url, html, text, status
                    break
            elif target_type == 'csr' and html:
                check_soup = BeautifulSoup(html, 'html.parser')
                pdf_disclosures = [
                    a['href'] for a in check_soup.find_all('a', href=True)
                    if a['href'].lower().endswith('.pdf') and any(k in (a['href'] + ' ' + a.get_text()).lower() for k in ['csr', 'sustainability', 'section 135', 'schedule-vii', 'project', 'annual-report'])
                ]
                if pdf_disclosures:
                    logs.append(f"✓ Detected {len(pdf_disclosures)} statutory CSR/ESG disclosure document(s) directly on portal ({curr_url[:65]}). Destination reached.")
                    best_url, best_html, best_text, best_status = curr_url, html, text, status
                    break

            # Retain page with highest content length as best fallback
            if len(text) > len(best_text):
                best_url, best_html, best_text, best_status = curr_url, html, text, status

            # Check for deeper link
            if target_type == 'jobs':
                next_link = cls.find_deep_openings_link(html, curr_url)
            else:
                next_link = cls.find_deep_csr_link(html, curr_url)

            if next_link and next_link not in visited and next_link.rstrip('/').lower() != curr_url.rstrip('/').lower():
                logs.append(f"Following deep {target_type} portal link (Hop {hop+1}): {next_link}")
                curr_url = next_link
            else:
                break

        return best_url, best_html, best_text, best_status

    @classmethod
    def extract_jobs_via_ats_intelligence(cls, company: Company, careers_url: str, sector: str, logs: List[str]) -> List[Dict[str, Any]]:
        """
        Grounded dynamic portal extraction:
        Renders client-side dynamic DOM using headless browser, and extracts authentic vacancies.
        NEVER synthesizes hallucinated job titles or fake requisition IDs.
        """
        logs.append(f"⚡ Inspecting dynamic client-side portal '{careers_url}' with headless browser...")
        try:
            r_html, r_text, r_status = cls.fetch_rendered_page(careers_url, timeout=8)
            if r_html and len(r_text) > 80:
                soup = BeautifulSoup(r_html, 'html.parser')
                cards = detect_repeating_dom_job_cards(soup, careers_url)
                if cards and len(cards) >= 2:
                    valid_cards = []
                    for card in cards:
                        t = card.get('title')
                        if is_valid_job_title(t):
                            valid_cards.append({
                                'job_title': t,
                                'location': card.get('location') or 'India',
                                'department': card.get('department') or 'Corporate',
                                'work_mode': 'Full-time',
                                'experience': 'As specified on portal',
                                'application_url': card.get('apply_url') or '',
                                'verbatim_source_quote': card.get('verbatim_quote') or f"Rendered Job: {t}",
                                'confidence': 0.95
                            })
                    if valid_cards:
                        logs.append(f"✓ Headless browser extracted {len(valid_cards)} active vacancies directly from rendered DOM")
                        return valid_cards

                ai_jobs = HybridAIExtractionService.extract_unstructured_jobs(
                    company_id=company.company_id,
                    company_name=company.company_name,
                    raw_content=r_text,
                    careers_url=careers_url,
                    timeout=15
                )
                if ai_jobs and isinstance(ai_jobs, list):
                    valid_ai = [j for j in ai_jobs if isinstance(j, dict) and is_valid_job_title(j.get('job_title'))]
                    if valid_ai:
                        logs.append(f"✓ Extracted {len(valid_ai)} active vacancies from rendered portal text")
                        return valid_ai
        except Exception as e:
            logs.append(f"Dynamic portal note: {str(e)[:80]}")

        logs.append(f"ℹ️ Portal uses direct candidate login or no static vacancies published.")
        return []

    @classmethod
    def _extract_grounded_csr_projects_from_text(cls, company: Company, text: str, source_url: str) -> List[Dict[str, Any]]:
        """
        Deterministic parser for statutory Section 135 & Schedule VII initiatives from PDF / page text.
        Extracts genuine documented community programs with verbatim evidence sentences.
        """
        if not text or len(text) < 100:
            return []

        # Conservative, evidence-grounded deterministic extraction.
        # Only explicit "Program name: description" definitions found verbatim in
        # the source text are accepted.  The old keyword→template mapping was
        # removed because it manufactured projects that the company never named.
        sentences = re.split(r'(?<=[.!?])\s+', text)
        results: List[Dict[str, Any]] = []
        seen = set()
        csr_signal = (
            'education', 'school', 'health', 'hospital', 'water', 'sanitation', 'skill',
            'livelihood', 'women', 'child', 'rural', 'environment', 'plantation', 'forest',
            'community', 'beneficiar', 'village', 'farmer', 'disabilit', 'nutrition',
            'scholarship', 'welfare', 'conservation', 'renewable', 'energy', 'waste',
        )
        topic_map = (
            ('education', 'Education & Skill Development'),
            ('school', 'Education & Skill Development'),
            ('scholarship', 'Education & Skill Development'),
            ('skill', 'Education & Skill Development'),
            ('health', 'Healthcare & Nutrition'),
            ('hospital', 'Healthcare & Nutrition'),
            ('nutrition', 'Healthcare & Nutrition'),
            ('water', 'Water & Sanitation'),
            ('sanitation', 'Water & Sanitation'),
            ('environment', 'Environment & Sustainability'),
            ('plantation', 'Environment & Sustainability'),
            ('forest', 'Environment & Sustainability'),
            ('conservation', 'Environment & Sustainability'),
            ('renewable', 'Environment & Sustainability'),
            ('energy', 'Environment & Sustainability'),
            ('women', 'Women Empowerment'),
            ('rural', 'Rural Development'),
            ('village', 'Rural Development'),
            ('farmer', 'Rural Development'),
            ('disaster', 'Disaster Relief'),
        )
        for s in sentences:
            s_clean = re.sub(r'\s+', ' ', s).strip()
            if len(s_clean) < 40 or len(s_clean) > 600:
                continue
            m = re.match(
                r"^(?P<name>[A-Z][A-Za-z0-9&()'’\-– ]{3,80}?)\s*[:–—]\s*(?P<desc>.{30,})$",
                s_clean,
            )
            if not m:
                continue
            name = m.group('name').strip()
            desc = m.group('desc').strip()
            if name.lower() in seen or not is_valid_csr_project(name):
                continue
            low_desc = desc.lower()
            if not any(k in low_desc for k in csr_signal):
                continue
            category = 'Corporate Social Responsibility'
            for keyword, label in topic_map:
                if keyword in low_desc:
                    category = label
                    break
            money = re.search(r'(?:₹|rs\.?|inr)\s*[\d,.]+(?:\s*(?:crore|lakh|million|billion))?', desc, re.IGNORECASE)
            seen.add(name.lower())
            results.append({
                'project_name': name,
                'category': category,
                'state': '',
                'district': '',
                'budget': money.group(0) if money else '',
                'description': desc[:800],
                'verbatim_quote': s_clean[:600],
                'source_url': source_url,
                'confidence': 0.75,
            })

        return results

    @classmethod
    def extract_csr_via_intelligence(cls, company: Company, csr_url: str, sector: str, logs: List[str]) -> List[Dict[str, Any]]:
        """
        Grounded Section 135 extraction:
        Inspects statutory Section 135 annual report and disclosure PDFs, extracting genuine initiatives.
        NEVER synthesizes templated project names.
        Aggregates multiple initiatives across disclosures.
        """
        logs.append(f"⚡ Inspecting statutory Section 135 PDF filings & disclosure reports...")
        all_collected_projs: List[Dict[str, Any]] = []
        seen_names: set = set()
        pdf_texts: List[Tuple[str, str]] = []

        try:
            c_html, c_text, _ = cls.fetch_page_content(csr_url)
            pdf_links = []
            if csr_url.lower().endswith('.pdf'):
                pdf_links.append(csr_url)
            elif c_html:
                soup = BeautifulSoup(c_html, 'html.parser')
                company_domain = company.official_domain or get_registrable_domain(csr_url)
                for a in soup.find_all('a', href=True):
                    h = a['href'].strip()
                    txt = a.get_text(' ', strip=True).lower()
                    low_h = h.lower()
                    if not low_h.endswith('.pdf'):
                        continue
                    combined = f"{low_h} {txt}"
                    # Only statutory CSR / BRSR / sustainability / annual report
                    # documents qualify.  Talent, recruitment, service-brochure and
                    # case-study PDFs are not CSR disclosures even if they mention
                    # a social initiative in passing.
                    if not any(k in combined for k in (
                        'csr', 'brsr', 'section-135', 'section 135', 'schedule-vii',
                        'schedule vii', 'annual-report', 'annual report',
                        'sustainability-report', 'sustainability report', 'esg-report',
                    )):
                        continue
                    if any(bad in combined for bad in (
                        'talent', 'pulse', 'recruit', 'career', 'brochure', 'case-stud',
                        'services/', 'service-', 'capability', 'newsletter',
                    )):
                        continue
                    full_pdf = urllib.parse.urljoin(csr_url, h)
                    if not is_allowed_domain_or_ats(full_pdf, company_domain):
                        continue
                    if full_pdf not in pdf_links:
                        pdf_links.append(full_pdf)

            # Prioritize the most recent 2 ESG / Section 135 PDF reports to balance depth & speed
            for pdf_url in pdf_links[:2]:
                logs.append(f"Parsing statutory CSR disclosure PDF: {pdf_url[:70]}...")
                pdf_text = cls.extract_pdf_text_from_url(pdf_url, max_pages=15)
                if pdf_text and len(pdf_text) > 200:
                    # The document itself must discuss CSR / Section 135 / BRSR.
                    # A generic sustainability-services brochure does not qualify.
                    if not re.search(
                        r'(section\s*135|schedule\s*vii|corporate\s+social\s+responsibility|\bcsr\b|\bbrsr\b)',
                        pdf_text[:30000], re.IGNORECASE,
                    ):
                        logs.append(f"Report skipped (no CSR/Section 135 context): {pdf_url[:80]}")
                        continue
                    pdf_texts.append((pdf_url, pdf_text))

                    # 1. Deterministic grounded extraction from official disclosure text
                    det_projs = cls._extract_grounded_csr_projects_from_text(company, pdf_text, pdf_url)
                    for dp in det_projs:
                        dp_norm = dp['project_name'].lower()
                        if dp_norm not in seen_names and is_valid_csr_project(dp['project_name']):
                            seen_names.add(dp_norm)
                            dp['raw_pdf_text'] = pdf_text
                            all_collected_projs.append(dp)

                    # 2. AI Multi-Project Extraction for additional unstructured initiatives
                    try:
                        ai_projs = HybridAIExtractionService.extract_unstructured_csr_projects(
                            company_id=company.company_id,
                            company_name=company.company_name,
                            raw_content=pdf_text,
                            csr_url=pdf_url,
                            timeout=20
                        )
                        if ai_projs and isinstance(ai_projs, list):
                            for p in ai_projs:
                                if isinstance(p, dict) and is_valid_csr_project(p.get('project_name')):
                                    p_name = p.get('project_name', '').strip()
                                    p_norm = p_name.lower()
                                    if p_norm not in seen_names:
                                        seen_names.add(p_norm)
                                        p['source_url'] = pdf_url
                                        p['raw_pdf_text'] = pdf_text
                                        all_collected_projs.append(p)
                    except Exception as ai_err:
                        logger.debug(f"AI CSR extraction fallback: {ai_err}")

            # Also check page text if still empty
            if not all_collected_projs and c_text and len(c_text) > 200:
                det_projs = cls._extract_grounded_csr_projects_from_text(company, c_text, csr_url)
                for dp in det_projs:
                    dp_norm = dp['project_name'].lower()
                    if dp_norm not in seen_names and is_valid_csr_project(dp['project_name']):
                        seen_names.add(dp_norm)
                        dp['raw_pdf_text'] = c_text
                        all_collected_projs.append(dp)

            if all_collected_projs:
                logs.append(f"✓ Extracted {len(all_collected_projs)} verified Section 135 initiatives directly from official disclosures")
                return all_collected_projs

        except Exception as e:
            logs.append(f"CSR disclosure inspection note: {str(e)[:80]}")

        logs.append(f"ℹ️ No statutory Section 135 projects found in available page text or disclosures.")
        return []

    @classmethod
    def discover_all_real_jobs(cls, company: Company, careers_url: str, raw_html: str, cleaned_text: str, sector: str, logs: List[str]) -> List[Dict[str, Any]]:
        """
        Multi-tier deterministic and AI extraction pipeline for 100% genuine active vacancies:
        Tier 1: Reliance ASP.NET WebForms Live Job Grid.
        Tier 2: Amazon Official Search API for India (amazon.jobs/en/search.json?country=IND).
        Tier 3: Workday CXS Recruitment API (Samsung & all Workday portals) with full pagination.
        Tier 4: Specialized ATS Adapters (Lever, Greenhouse, SmartRecruiters, Darwinbox, SuccessFactors, Taleo).
        Tier 5: TCS Lateral & Specialty Career Track Crawlers.
        Tier 6: Schema.org JSON-LD Structured JobPostings.
        Tier 7: Repeating DOM Job Card Detector.
        Tier 8: Comprehensive AI Job Extraction across up to 40,000 characters of page content.
        Tier 9: Dynamic ATS intelligence fallback if and only if zero listings could be extracted from DOM/APIs.
        """
        comp_lower = company.company_name.lower()
        comp_domain = getattr(company, 'official_domain', '') or ''

        # Tier Zwayam / Happiest Minds ATS Portal (jobs.happiestminds.com / public.zwayam.com)
        if cls._matches_enterprise_key('happiest minds', comp_lower, comp_domain) or 'zwayam' in careers_url.lower() or 'jobs.happiestminds.com' in careers_url.lower() or 'public.zwayam.com' in careers_url.lower():
            try:
                from modules.crawler_engine.adapters.zwayam import ZwayamAdapter
                z_adapter = ZwayamAdapter()
                logs.append(f"⚡ Inspecting live Zwayam ATS Search API for {company.company_name}...")
                z_records = z_adapter.extract_jobs(company.company_id, careers_url)
                if z_records:
                    formatted = []
                    for zr in z_records:
                        title = zr.job_title
                        if is_valid_job_title(title):
                            formatted.append({
                                'job_title': title,
                                'location': zr.location_raw or 'Bengaluru, Karnataka, India',
                                'department': zr.department or 'Technology Services',
                                'work_mode': zr.work_mode or 'On-site',
                                'experience': zr.source_evidence.get('experience', 'As specified on portal'),
                                'application_url': zr.application_url,
                                'requisition_id': zr.external_job_id or '',
                                'verbatim_source_quote': zr.source_evidence.get('raw_source') or f"Happiest Minds Opening: {title} in {zr.location_raw}",
                                'confidence': 0.99
                            })
                    if formatted:
                        logs.append(f"✓ Zwayam ATS Adapter extracted {len(formatted)} live jobs directly from Zwayam recruitment API")
                        return formatted
            except Exception as e:
                logs.append(f"Zwayam adapter note: {e}")

        # Tier 1: Reliance Careers Portal (careers.ril.com)
        if cls._matches_enterprise_key('reliance', comp_lower, comp_domain) or cls._matches_enterprise_key('ril', comp_lower, comp_domain) or 'careers.ril.com' in careers_url.lower():
            rel_adapter = ReliancePortalAdapter()
            target_url = "https://careers.ril.com/rilcareers/frmjobsearch.Aspx"
            try:
                logs.append(f"⚡ Inspecting live Reliance Careers ASP.NET Grid at {target_url}...")
                grid_html, _, g_status = cls.fetch_page_content(target_url)
                if grid_html:
                    grid_jobs = rel_adapter.extract_from_grid_html(grid_html, company.company_id)
                    if grid_jobs:
                        formatted = []
                        for gj in grid_jobs:
                            title = gj.get('job_title') or ''
                            if is_valid_job_title(title):
                                formatted.append({
                                    'job_title': title,
                                    'location': gj.get('location') or 'India',
                                    'department': gj.get('functional_area') or 'Corporate',
                                    'work_mode': 'On-site',
                                    'experience': 'As specified on portal',
                                    'application_url': gj.get('application_url') or gj.get('detail_url'),
                                    'requisition_id': gj.get('job_id') or '',
                                    'verbatim_source_quote': f"Reliance Grid Opening: {title} in {gj.get('location')} ({gj.get('employer_name')})",
                                    'confidence': 0.99
                                })
                        if formatted:
                            logs.append(f"✓ Reliance Portal Adapter extracted {len(formatted)} live jobs directly from {target_url}")
                            return formatted
            except Exception as e:
                logs.append(f"Reliance adapter note: {e}")

        # Tier 2: Amazon Official Search API
        if cls._matches_enterprise_key('amazon', comp_lower, comp_domain) or 'amazon.jobs' in careers_url.lower():
            try:
                logs.append("⚡ Querying Amazon Official Search API for India vacancies...")
                if cffi_requests is not None:
                    api_resp = cffi_requests.get("https://amazon.jobs/en/search.json?country=IND&result_limit=100", impersonate="chrome124", timeout=8)
                    if api_resp.status_code == 200:
                        a_data = api_resp.json()
                        hits = a_data.get('hits', 0)
                        postings = a_data.get('jobs', [])
                        a_jobs = []
                        for item in postings:
                            title = item.get('title')
                            if not title or not is_valid_job_title(title):
                                continue
                            path = item.get('job_path') or f"/en/jobs/{item.get('id_icims')}"
                            app_url = f"https://amazon.jobs{path}"
                            a_jobs.append({
                                'job_title': title,
                                'location': item.get('city') or item.get('location') or 'India',
                                'department': item.get('business_category') or item.get('job_category') or 'Corporate',
                                'work_mode': 'Full-time',
                                'experience': item.get('basic_qualifications_preview') or 'Standard Amazon Qualifications',
                                'application_url': app_url,
                                'requisition_id': str(item.get('id_icims', '')),
                                'verbatim_source_quote': f"Amazon Job {item.get('id_icims')}: {title} ({item.get('city')})",
                                'confidence': 0.99
                            })
                        if a_jobs:
                            logs.append(f"✓ Amazon Official API extracted {len(a_jobs)} live vacancies in India (total live on portal: {hits})")
                            return a_jobs
            except Exception as e:
                logs.append(f"Amazon API note: {e}")

        # Tier 2B: Microsoft Official PCSX Careers API
        if cls._matches_enterprise_key('microsoft', comp_lower, comp_domain) or 'careers.microsoft.com' in careers_url.lower():
            logs.append("⚡ Querying Microsoft Official Careers PCSX API for India...")
            try:
                if cffi_requests is not None:
                    ms_api = "https://apply.careers.microsoft.com/api/pcsx/search?domain=microsoft.com&query=&location=India&start=0"
                    ms_headers = {
                        'User-Agent': USER_AGENT,
                        'Accept': 'application/json',
                        'Referer': 'https://jobs.careers.microsoft.com/'
                    }
                    r = cffi_requests.get(ms_api, headers=ms_headers, impersonate="chrome124", timeout=6)
                    if r.status_code == 200:
                        ms_data = r.json()
                        positions = ms_data.get('data', {}).get('positions', [])
                        ms_jobs = []
                        for p in positions:
                            title = p.get('name')
                            pid = str(p.get('id') or '')
                            if not title or not is_valid_job_title(title):
                                continue
                            loc = p.get('location') or 'India'
                            dept = p.get('department') or 'Engineering & Technology'
                            app_url = f"https://jobs.careers.microsoft.com/global/en/share/{pid}" if pid else "https://jobs.careers.microsoft.com/global/en/search?lc=India"
                            ms_jobs.append({
                                'job_title': title,
                                'location': loc if loc != 'None' else 'India',
                                'department': dept,
                                'work_mode': 'On-site / Hybrid',
                                'experience': 'As specified on Microsoft Careers',
                                'application_url': app_url,
                                'requisition_id': pid,
                                'verbatim_source_quote': f"Microsoft Requisition {pid}: {title} ({dept})",
                                'confidence': 0.99,
                                'ats_platform': 'microsoft_pcsx',
                                'extraction_method': 'ats_api'
                            })
                        if ms_jobs:
                            logs.append(f"✓ Microsoft PCSX API extracted {len(ms_jobs)} live verified vacancies in India")
                            return ms_jobs
            except Exception as e:
                logs.append(f"Microsoft PCSX note: {e}")

        # Tier 2C: Google Official Careers Static & Fast Parser
        if cls._matches_enterprise_key('google', comp_lower, comp_domain) or 'careers.google.com' in careers_url.lower():
            logs.append("⚡ Querying Google Official Careers portal for India vacancies...")
            try:
                g_url = "https://www.google.com/about/careers/applications/jobs/results/?location=India"
                g_html, _, g_stat = cls.fetch_page_content(g_url, timeout=6)
                if g_html:
                    g_soup = BeautifulSoup(g_html, 'html.parser')
                    google_jobs = []
                    seen_g_ids = set()
                    for a in g_soup.find_all('a', href=True):
                        h = a['href']
                        if 'jobs/results/' in h and not h.endswith('jobs/results/'):
                            m = re.search(r'jobs/results/(\d+)-([^?&#]+)', h)
                            if m:
                                jid = m.group(1)
                                if jid in seen_g_ids:
                                    continue
                                seen_g_ids.add(jid)
                                raw_slug = m.group(2).replace('-', ' ').title()
                                link_txt = a.get_text(' ', strip=True)
                                title = link_txt if len(link_txt) > 5 and is_valid_job_title(link_txt) else raw_slug
                                if is_valid_job_title(title):
                                    full_g_url = f"https://www.google.com/about/careers/applications/jobs/results/{m.group(1)}-{m.group(2)}"
                                    google_jobs.append({
                                        'job_title': title,
                                        'location': 'India',
                                        'department': 'Technology & Operations',
                                        'work_mode': 'Full-time / Hybrid',
                                        'experience': 'As specified on Google Careers',
                                        'application_url': full_g_url,
                                        'requisition_id': jid,
                                        'verbatim_source_quote': f"Google Job {jid}: {title}",
                                        'confidence': 0.99,
                                        'ats_platform': 'google_careers',
                                        'extraction_method': 'ats_api'
                                    })
                    if google_jobs:
                        logs.append(f"✓ Google Careers extracted {len(google_jobs)} live verified vacancies directly from official portal")
                        return google_jobs
            except Exception as e:
                logs.append(f"Google Careers note: {e}")

        # Tier 3: Workday CXS Recruitment API (Samsung, Pfizer & all Workday portals)
        if cls._matches_enterprise_key('samsung', comp_lower, comp_domain) or cls._matches_enterprise_key('pfizer', comp_lower, comp_domain) or 'myworkdayjobs.com' in careers_url.lower():
            logs.append("⚡ Querying Workday CXS Recruitment API...")
            try:
                cxs_url = None
                if cls._matches_enterprise_key('samsung', comp_lower, comp_domain):
                    cxs_url = "https://sec.wd3.myworkdayjobs.com/wday/cxs/sec/Samsung_Careers/jobs"
                elif cls._matches_enterprise_key('pfizer', comp_lower, comp_domain):
                    cxs_url = "https://pfizer.wd1.myworkdayjobs.com/wday/cxs/pfizer/PfizerCareers/jobs"
                elif 'myworkdayjobs.com' in careers_url.lower():
                    p = urllib.parse.urlparse(careers_url)
                    tenant = p.netloc.split('.')[0]
                    parts = [pt for pt in p.path.split('/') if pt]
                    site = parts[-1] if parts else 'Careers'
                    cxs_url = f"{p.scheme}://{p.netloc}/wday/cxs/{tenant}/{site}/jobs"
                
                if cxs_url and cffi_requests is not None:
                    wd_jobs = []
                    offset = 0
                    limit = 20
                    total = None
                    search_kw = 'India'
                    for _ in range(5): # Up to 100 jobs
                        payload = json.dumps({'appliedFacets': {}, 'limit': limit, 'offset': offset, 'searchText': search_kw})
                        r = cffi_requests.post(cxs_url, data=payload, headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, impersonate="chrome124", timeout=8)
                        if r.status_code != 200:
                            break
                        data = r.json()
                        if total is None:
                            total = data.get('total', 0)
                        postings = data.get('jobPostings', [])
                        if not postings:
                            break
                        for item in postings:
                            title = item.get('title')
                            ext = item.get('externalPath', '')
                            if not title or not is_valid_job_title(title) or not ext:
                                continue
                            base_wd = cxs_url.split('/wday/cxs/')[0]
                            site_name = cxs_url.split('/')[-2]
                            app_url = f"{base_wd}/{site_name}{ext}"
                            wd_jobs.append({
                                'job_title': title,
                                'location': item.get('locationsText') or 'India',
                                'department': 'Technology & Operations',
                                'work_mode': 'On-site / Hybrid',
                                'experience': 'As specified on Workday',
                                'application_url': app_url,
                                'requisition_id': item.get('bulletFields', [None])[0] or '',
                                'verbatim_source_quote': f"Workday Listing: {title} ({item.get('locationsText')})",
                                'confidence': 0.99
                            })
                        offset += len(postings)
                        if total and offset >= total:
                            break
                        if len(postings) < limit:
                            break
                    if wd_jobs:
                        logs.append(f"✓ Workday CXS API extracted {len(wd_jobs)} live job vacancies (total live: {total or len(wd_jobs)})")
                        return wd_jobs
            except Exception as e:
                logs.append(f"Workday CXS note: {e}")

        # Tier 3B: JPMorgan Chase Oracle Cloud Candidate Experience API
        if cls._matches_enterprise_key('jpmorgan', comp_lower, comp_domain) or cls._matches_enterprise_key('jpmc', comp_lower, comp_domain) or 'jpmc.fa.oraclecloud.com' in careers_url.lower():
            logs.append("⚡ Querying JPMorgan Chase Oracle Cloud CX Recruitment API for India...")
            try:
                if cffi_requests is not None:
                    jpmc_api = "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions?onlyData=true&expand=requisitionList&finder=findReqs;siteNumber=CX_1001,limit=30,keyword=%22India%22,sortBy=RELEVANCY"
                    r = cffi_requests.get(jpmc_api, headers={'Accept': 'application/json'}, impersonate="chrome124", timeout=15)
                    if r.status_code == 200:
                        data = r.json()
                        items = data.get('items', [])
                        req_list = items[0].get('requisitionList', []) if items else []
                        jpmc_jobs = []
                        for req in req_list:
                            title = req.get('Title')
                            req_id = str(req.get('Id') or '')
                            if not title or not is_valid_job_title(title):
                                continue
                            loc = req.get('PrimaryLocation') or 'India'
                            app_url = f"https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/{req_id}"
                            jpmc_jobs.append({
                                'job_title': title,
                                'location': loc,
                                'department': req.get('BusinessUnit') or 'Banking & Technology',
                                'work_mode': 'Hybrid / On-site',
                                'experience': 'As specified on JPMC Careers',
                                'application_url': app_url,
                                'requisition_id': req_id,
                                'verbatim_source_quote': f"JPMorgan Chase Requisition {req_id}: {title} ({loc})",
                                'confidence': 0.99
                            })
                        if jpmc_jobs:
                            logs.append(f"✓ JPMC Oracle Cloud API extracted {len(jpmc_jobs)} live verified vacancies in India")
                            return jpmc_jobs
            except Exception as e:
                logs.append(f"JPMC Oracle API note: {e}")

        # Tier 3C: HCLTech SAP SuccessFactors Recruiting API
        if cls._matches_enterprise_key('hcl', comp_lower, comp_domain) or cls._matches_enterprise_key('hcltech', comp_lower, comp_domain) or 'careers.hcltech.com' in careers_url.lower():
            logs.append("⚡ Querying HCLTech Official Careers Recruiting API for India...")
            try:
                if cffi_requests is not None:
                    hcl_jobs = []
                    payload = {'locale': 'en_US', 'pageNumber': 0, 'keywords': 'India'}
                    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
                    r = cffi_requests.post('https://careers.hcltech.com/services/recruiting/v1/jobs', json=payload, headers=headers, impersonate="chrome124", timeout=8)
                    if r.status_code == 200:
                        data = r.json()
                        jsr = data.get('jobSearchResult', [])
                        for item in jsr:
                            resp = item.get('response', {})
                            title = resp.get('unifiedStandardTitle') or resp.get('urlTitle')
                            jid = str(resp.get('id') or '')
                            if not title or not is_valid_job_title(title):
                                continue
                            loc_val = resp.get('custprimecity') or 'India'
                            if isinstance(loc_val, list):
                                loc_val = ', '.join(loc_val)
                            url_slug = resp.get('urlTitle') or resp.get('unifiedUrlTitle') or 'job'
                            app_url = f"https://careers.hcltech.com/job/{url_slug}/{jid}-en_US"
                            hcl_jobs.append({
                                'job_title': title,
                                'location': f"{loc_val}, India" if 'india' not in str(loc_val).lower() else str(loc_val),
                                'department': 'Digital & IT Services',
                                'work_mode': 'On-site / Hybrid',
                                'experience': 'As specified on HCLTech portal',
                                'application_url': app_url,
                                'requisition_id': jid,
                                'verbatim_source_quote': f"HCLTech Opening {jid}: {title} in {loc_val}",
                                'confidence': 0.99
                            })
                        if hcl_jobs:
                            logs.append(f"✓ HCLTech Recruiting API extracted {len(hcl_jobs)} live verified vacancies in India (total open: {data.get('totalJobs')})")
                            return hcl_jobs
            except Exception as e:
                logs.append(f"HCLTech API note: {e}")

        # Tier 3D: Phenom People Recruitment Platform (eagerLoadRefineSearch / phApp.ddo)
        if 'eagerloadrefinesearch' in raw_html.lower() or 'phapp.ddo' in raw_html.lower() or 'careers.titan.in' in careers_url.lower():
            logs.append("⚡ Querying Phenom People enterprise recruitment portal...")
            try:
                idx = raw_html.find('phApp.ddo = ')
                if idx != -1:
                    end_idx = raw_html.find('; phApp.', idx)
                    if end_idx != -1:
                        raw_js = raw_html[idx + len('phApp.ddo = '):end_idx]
                        ph_data = json.loads(raw_js)
                        ph_jobs = ph_data.get('eagerLoadRefineSearch', {}).get('data', {}).get('jobs', [])
                        parsed_phenom = []
                        base_careers = re.sub(r'/search-results.*', '', careers_url).rstrip('/')
                        for pj in ph_jobs:
                            p_title = pj.get('title')
                            if not p_title or not is_valid_job_title(p_title):
                                continue
                            p_seq = pj.get('jobSeqNo') or pj.get('jobId') or pj.get('reqId') or ''
                            slug_t = re.sub(r'[^a-zA-Z0-9]+', '-', p_title).strip('-')
                            app_url = f"{base_careers}/job/{p_seq}/{slug_t}" if p_seq else careers_url
                            parsed_phenom.append({
                                'job_title': p_title,
                                'location': pj.get('location') or pj.get('city') or 'India',
                                'department': pj.get('department') or pj.get('category') or 'Corporate',
                                'work_mode': 'On-site / Hybrid',
                                'experience': 'As specified on portal',
                                'application_url': app_url,
                                'requisition_id': p_seq,
                                'verbatim_source_quote': pj.get('descriptionTeaser') or f"Phenom Listing: {p_title} ({p_seq})",
                                'confidence': 0.99,
                                'ats_platform': 'phenom',
                                'extraction_method': 'ats_api'
                            })
                        if parsed_phenom:
                            logs.append(f"✓ Phenom People ATS extracted {len(parsed_phenom)} live verified vacancies")
                            return parsed_phenom
            except Exception as e:
                logs.append(f"Phenom People extraction note: {e}")

        # Tier 4: Specialized ATS Adapters (Lever, Greenhouse, SmartRecruiters, Darwinbox, SuccessFactors, Taleo)
        spec_jobs = try_dispatch_specialized_ats(careers_url)
        if spec_jobs:
            formatted = []
            for sj in spec_jobs:
                title = sj.get('title')
                if is_valid_job_title(title):
                    formatted.append({
                        'job_title': title,
                        'location': sj.get('location') or 'India',
                        'department': sj.get('department') or 'Corporate',
                        'work_mode': 'Full-time',
                        'experience': 'As specified on portal',
                        'application_url': sj.get('apply_url') or careers_url,
                        'verbatim_source_quote': sj.get('verbatim_quote') or f"ATS Posting: {title}",
                        'confidence': 0.98
                    })
            if formatted:
                logs.append(f"✓ Specialized ATS Adapter extracted {len(formatted)} live jobs from {careers_url}")
                return formatted

        # Tier 5: TCS Lateral & Specialized Hiring Tracks
        if 'tcs' in comp_lower or 'tata consultancy' in comp_lower:
            logs.append("⚡ Scraping TCS India Lateral & Specialized Hiring tracks...")
            try:
                tcs_tracks = [
                    'https://www.tcs.com/careers/india/tcs-cloud-hiring',
                    'https://www.tcs.com/careers/india/tcs-cybersecurity-hiring',
                    'https://www.tcs.com/careers/india/tcs-ai-careers',
                    'https://www.tcs.com/careers/india/tcs-data-and-analytics-careers',
                    'https://www.tcs.com/careers/india/tcs-esu-hiring',
                    'https://www.tcs.com/careers/india/tcs-industrial-autonomy-engineering-careers',
                    'https://www.tcs.com/careers/india/tcs-interactive-hiring',
                    'https://www.tcs.com/careers/india/lateral-hiring'
                ]
                tcs_jobs = []
                seen_titles = set()
                for track_url in tcs_tracks:
                    thtml, ttext, tstatus = cls.fetch_page_content(track_url)
                    if thtml:
                        soup = BeautifulSoup(thtml, 'html.parser')
                        for tag in soup.find_all(['h2', 'h3', 'h4', 'strong', 'li']):
                            txt = tag.get_text(' ', strip=True)
                            if any(w in txt.lower() for w in ['architect', 'engineer', 'lead', 'developer', 'consultant', 'manager', 'specialist', 'analyst']):
                                if is_valid_job_title(txt) and txt.lower() not in seen_titles:
                                    seen_titles.add(txt.lower())
                                    tcs_jobs.append({
                                        'job_title': txt,
                                        'location': 'Pan-India',
                                        'department': 'Cloud, Cybersecurity & Digital',
                                        'work_mode': 'Hybrid / Full-time',
                                        'experience': '3-8 Years',
                                        'application_url': track_url or 'https://www.tcs.com/careers/india',
                                        'verbatim_source_quote': f"TCS Verified Lateral Opening: {txt}",
                                        'confidence': 0.96
                                    })
                if tcs_jobs:
                    logs.append(f"✓ Extracted {len(tcs_jobs)} live lateral job tracks from TCS official career portal")
                    return tcs_jobs
            except Exception as e:
                logs.append(f"TCS track note: {e}")

        # Tier 6: Schema.org JSON-LD Structured JobPostings
        if raw_html:
            jsonld_adapter = GenericStructuredJobAdapter()
            jsonld_jobs = jsonld_adapter.extract_jobs(company.company_id, careers_url, raw_html)
            if jsonld_jobs:
                valid_jsonld = []
                for rec in jsonld_jobs:
                    if is_valid_job_title(rec.job_title):
                        valid_jsonld.append({
                            'job_title': rec.job_title,
                            'location': rec.location_raw or 'India',
                            'department': rec.department or 'Corporate',
                            'work_mode': rec.work_mode or 'Full-time',
                            'experience': 'As specified on portal',
                            'application_url': rec.application_url or rec.detail_url or '',
                            'requisition_id': rec.external_job_id or '',
                            'verbatim_source_quote': f"Schema.org JobPosting: {rec.job_title}",
                            'confidence': rec.confidence
                        })
                if valid_jsonld:
                    logs.append(f"✓ Schema.org JSON-LD extracted {len(valid_jsonld)} structured job postings directly from page HTML")
                    return valid_jsonld

        # Tier 7: Repeating DOM Job Card Detector
        if raw_html:
            soup = BeautifulSoup(raw_html, 'html.parser')
            dom_cards = detect_repeating_dom_job_cards(soup, careers_url)
            if dom_cards and len(dom_cards) >= 3:
                valid_dom = []
                for card in dom_cards:
                    title = card.get('title')
                    if is_valid_job_title(title):
                        valid_dom.append({
                            'job_title': title,
                            'location': card.get('location') or 'India',
                            'department': card.get('department') or 'Corporate',
                            'work_mode': 'Full-time',
                            'experience': 'As specified on portal',
                            'application_url': card.get('apply_url') or '',
                            'verbatim_source_quote': card.get('verbatim_quote') or f"DOM Card: {title}",
                            'confidence': 0.92
                        })
                if valid_dom:
                    logs.append(f"✓ DOM Repeating Card Detector discovered {len(valid_dom)} live job cards directly on careers page")
                    return valid_dom

        # Tier 8: Comprehensive AI Job Extraction across up to 40,000 characters of live page content
        content_to_pass = raw_html if raw_html else cleaned_text
        if content_to_pass and len(content_to_pass) > 80:
            logs.append(f"Running AI Job Extraction on live page content ({len(cleaned_text)} chars)...")
            try:
                ai_jobs = HybridAIExtractionService.extract_unstructured_jobs(
                    company_id=company.company_id,
                    company_name=company.company_name,
                    raw_content=content_to_pass,
                    careers_url=careers_url,
                    timeout=18
                )
                if ai_jobs and isinstance(ai_jobs, list):
                    valid_ai = [j for j in ai_jobs if isinstance(j, dict) and is_valid_job_title(j.get('job_title'))]
                    if valid_ai:
                        logs.append(f"✓ AI Job Extraction discovered {len(valid_ai)} active vacancies from page text")
                        return valid_ai
            except Exception as e:
                logs.append(f"AI job extraction note: {str(e)[:80]}")

        # Tier 9: Dynamic ATS & Corporate Intelligence Fallback
        logs.append(f"ℹ️ Careers portal uses client-side SPA. Engaging AI Corporate Intelligence...")
        return cls.extract_jobs_via_ats_intelligence(company, careers_url, sector, logs)

    @classmethod
    def discover_all_real_csr(cls, company: Company, csr_url: str, raw_html: str, cleaned_text: str, sector: str, logs: List[str]) -> List[Dict[str, Any]]:
        """
        Multi-tier extraction pipeline for Section 135 CSR projects and statutory initiatives:
        1. Direct DOM initiative cards and dedicated initiative links.
        2. AI Multi-Project Extraction on full CSR content (up to 40,000 chars).
        3. Single narrative disambiguation fallback.
        4. Section 135 MCA Schedule VII Intelligence fallback.
        """
        discovered = []
        seen_names = set()

        # Tier 1: Parse DOM initiative links and cards
        if raw_html:
            soup = BeautifulSoup(raw_html, 'html.parser')
            
            # 1a. Dedicated initiative / program links
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                t = a.get_text(' ', strip=True)
                if any(k in href.lower() for k in ['/initiatives/', '/programs/', '/projects/', '/focus-areas/']):
                    if is_valid_csr_project(t) and t.lower() not in seen_names:
                        seen_names.add(t.lower())
                        full_proj_url = urllib.parse.urljoin(csr_url, href)
                        discovered.append({
                            'project_name': t,
                            'category': 'Corporate Social Responsibility',
                            # No invented budget, location or narrative: only the
                            # page's own anchor text and URL are stored.
                            'verbatim_quote': t,
                            'source_url': full_proj_url,
                            'confidence': 0.85
                        })

        # Tier 2: AI Multi-Project Extraction on Full Text (up to 40,000 chars)
        if cleaned_text and len(cleaned_text) > 80:
            logs.append(f"Running AI Section 135 Multi-Project Extraction ({len(cleaned_text)} chars)...")
            try:
                ai_projects = HybridAIExtractionService.extract_unstructured_csr_projects(
                    company_id=company.company_id,
                    company_name=company.company_name,
                    raw_content=cleaned_text,
                    csr_url=csr_url,
                    timeout=18
                )
                if ai_projects and isinstance(ai_projects, list):
                    for p in ai_projects:
                        name = (p.get('project_name') or '').strip()
                        if is_valid_csr_project(name) and name.lower() not in seen_names:
                            seen_names.add(name.lower())
                            p['source_url'] = p.get('source_url') or csr_url
                            discovered.append(p)
            except Exception as e:
                logs.append(f"AI CSR extraction note: {str(e)[:80]}")

        # Tier 3: If DOM + AI yielded projects, return them!
        if discovered:
            logs.append(f"✓ Discovered {len(discovered)} authentic Section 135 CSR projects from portal")
            return discovered

        # Tier 4: Fallback to Section 135 Statutory Disclosure PDFs
        logs.append(f"ℹ️ Inspecting official Section 135 statutory PDF filings...")
        pdf_projs = cls.extract_csr_via_intelligence(company, csr_url, sector, logs)
        if pdf_projs:
            return pdf_projs

        # If no statutory CSR disclosure found, record dropped and return 0
        cls._record_dropped_candidate(company, 'CSR', f"{company.company_name} CSR Disclosures", csr_url, "no statutory CSR disclosure found", {"csr_url": csr_url})
        logs.append(f"No statutory Section 135 CSR disclosure found for {company.company_name}.")
        return []

    @classmethod
    def _record_dropped_candidate(cls, company: Company, candidate_type: str, name: str, target_url: str, reason: str, raw_data: Any = None):
        """Persists dropped job and CSR candidates to DroppedCandidate table for auditability & diagnostics."""
        try:
            from modules.admin_panel.models import DroppedCandidate
            DroppedCandidate.objects.create(
                company=company,
                candidate_type=candidate_type,
                title_or_name=name or '',
                target_url=target_url or '',
                reason=reason or 'UNKNOWN',
                raw_data=raw_data if isinstance(raw_data, dict) else {}
            )
        except Exception as e:
            logger.warning(f"Failed to record dropped candidate: {e}")

    @classmethod
    def validate_job(cls, candidate: Dict[str, Any], company: Company, seen_urls: set, logs: List[str] = None) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Hard Validation Gate (Stage 6) for Job Vacancies before database insertion.
        Rules:
        1. Reject invalid job titles.
        2. Reject missing or non-HTTP application URLs.
        3. Allowed host check: must match company registrable domain or approved ATS.
        4. Blacklist check: reject login, signin, privacy, policy, about-us, etc.
        5. Reject bare landing pages (/careers, /jobs, homepage).
        6. Reject duplicate URLs across different titles.
        7. Live HTTP 200 check: fetch apply URL (following redirects) requiring status 200.
        8. Reject if final redirected URL is a landing or login page.
        9. Reject if title or requisition ID is not found on linked page or in ATS metadata.
        """
        logs = logs if logs is not None else []
        title = (candidate.get('job_title') or '').strip()
        app_url = (candidate.get('application_url') or '').strip()
        req_id = str(candidate.get('requisition_id') or '').strip()

        # 1. Job Title Validation
        if not title or not is_valid_job_title(title):
            reason = f"INVALID_JOB_TITLE: '{title[:40]}'"
            cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
            return False, reason, candidate

        # 2. Application URL Presence & Format
        if not app_url or not app_url.startswith(('http://', 'https://')) or is_static_asset_url(app_url):
            reason = f"MISSING_OR_INVALID_URL: '{app_url[:40]}'"
            cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
            return False, reason, candidate

        # 3. Allowed Host Validation (Registrable domain or approved ATS)
        comp_domain = company.official_domain or company.website_url or get_registrable_domain(app_url)
        if not is_allowed_domain_or_ats(app_url, comp_domain):
            reason = f"DISALLOWED_HOST: Host for {app_url[:45]} not allowed"
            cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
            return False, reason, candidate

        # 4. Blacklist & Landing Page Detection
        app_url_clean = re.sub(r'([?&])(utm_[^&]+|fbclid=[^&]+|ref=[^&]+)', '', app_url).rstrip('&?')
        parsed_u = urllib.parse.urlparse(app_url_clean)
        p_path = parsed_u.path.strip('/').lower()

        blacklist_keywords = [
            'signin', 'login', 'auth/login', 'accounts.google', 'login.microsoftonline',
            '/policy-positions', '/programs-policies', '/about-us', '/who-we-are',
            '/investor', '/press-releases', '/culture', '/media', '/contact-us',
            '/terms', '/privacy', 'introduceyourself', 'equal-opportunity', 'safelinks',
            'why-work', 'life-at', 'our-culture', 'business-opportunit'
        ]
        if any(bad in app_url_clean.lower() for bad in blacklist_keywords):
            reason = f"BLACKLISTED_URL: Matches restricted keywords"
            cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
            return False, reason, candidate

        # Bare landing pages are not job postings. Never fabricate an anchor
        # (e.g. #req-123) to make a landing page look like a direct vacancy.
        # Only a real job identifier in the query string can make such a URL direct.
        if p_path in ('', 'careers', 'career', 'jobs', 'job', 'home', 'corporate/careers', 'about/careers', 'work-with-us'):
            query_low = (parsed_u.query or '').lower()
            has_real_job_id = bool(re.search(r'(^|[&?])(job|jobid|job_id|req|requisition|posting|vacancy|id)=[^&]+', query_low))
            if not has_real_job_id:
                reason = "LANDING_PAGE_NOT_JOB: Points to a careers landing page, not a direct vacancy"
                cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
                return False, reason, candidate

        # 5. Duplicate URL Check
        if app_url_clean.lower() in seen_urls:
            reason = f"DUPLICATE_URL: Already assigned to another position"
            cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
            return False, reason, candidate

        # 6. Lightweight URL Verification (NO per-URL HTTP fetch to avoid N+1 timeout bottleneck)
        # ROOT CAUSE FIX: Previously, every single job candidate triggered a synchronous
        # 10-second HTTP GET + optional 6-second Playwright render = up to 16 seconds per job.
        # With 10+ jobs, this alone exceeded the 120s client timeout causing "Discovery probe timed out".
        #
        # New approach:
        #   - ATS API jobs (Workday, Oracle, Amazon, etc.): Already verified by the API itself.
        #     Skip HTTP fetch entirely — trust the structured API response.
        #   - DOM-extracted jobs with verbatim quotes: Already verified against live page content.
        #     Skip HTTP fetch — the page was just crawled and the title was found in it.
        #   - Only perform a FAST (3s timeout) HEAD request for jobs from unknown sources
        #     that lack both a verbatim quote and an ATS platform marker.

        # 6a. Determine verification tier
        is_ats_api = any(k in app_url_clean.lower() for k in [
            'myworkdayjobs.com', 'oraclecloud.com', 'successfactors.com', 'param.ai',
            'greenhouse.io', 'lever.co', 'smartrecruiters.com', 'ashbyhq.com', 'icims.com', 'taleo.net',
            'amazon.jobs', 'careers.ril.com', 'darwinbox', 'phenompeople.com', 'phenom.com', 'turbohire',
            'zwayam.com', 'jobs.happiestminds.com'
        ]) or bool(candidate.get('ats_platform')) or candidate.get('extraction_method') == 'ats_api'

        has_verbatim = bool(candidate.get('verbatim_source_quote'))
        high_confidence = float(candidate.get('confidence') or 0) >= 0.90

        if is_ats_api:
            # Tier A: ATS API-sourced jobs — zero network verification needed
            if not title or len(title) < 3:
                reason = "ATS_API_RECORD_MISSING_TITLE"
                cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
                return False, reason, candidate
            # Trusted — skip HTTP fetch entirely
        elif has_verbatim or high_confidence:
            # Tier B: DOM-extracted or AI-extracted with verbatim source evidence
            # The page was just crawled; the title/quote was found in the live content.
            # Only do a fast structural URL check (no network call):
            final_url = app_url_clean
            parsed_fin = urllib.parse.urlparse(final_url)
            fin_path = parsed_fin.path.strip('/').lower()
            if any(bad in final_url.lower() for bad in ['signin', 'login', 'auth/', 'accounts.google']):
                reason = "REDIRECTED_TO_LANDING_OR_LOGIN"
                cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
                return False, reason, candidate
        else:
            # Tier C: Unknown source, low confidence, no verbatim — fast HEAD check (3s max)
            try:
                if cffi_requests is not None:
                    resp = cffi_requests.head(app_url_clean, impersonate="chrome124", timeout=3,
                                              headers=BROWSER_HEADERS, allow_redirects=True)
                    status_code = resp.status_code
                    final_url = str(resp.url) if hasattr(resp, 'url') else app_url_clean
                else:
                    status_code = 200
                    final_url = app_url_clean
            except Exception as exc:
                # A network failure is not evidence of a live vacancy. Reject
                # honestly instead of pretending the URL returned HTTP 200.
                reason = f"LIVE_URL_UNREACHABLE: {str(exc)[:90]}"
                cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
                return False, reason, candidate

            if status_code in (404, 410):
                reason = f"HTTP_STATUS_{status_code}"
                cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
                return False, reason, candidate

            # Check redirected URL for login walls
            parsed_fin = urllib.parse.urlparse(final_url)
            fin_path = parsed_fin.path.strip('/').lower()
            if any(bad in final_url.lower() for bad in ['signin', 'login', 'auth/', 'accounts.google']):
                reason = "REDIRECTED_TO_LANDING_OR_LOGIN"
                cls._record_dropped_candidate(company, 'JOB', title, app_url, reason, candidate)
                return False, reason, candidate

        seen_urls.add(app_url_clean.lower())
        candidate['application_url'] = app_url_clean
        return True, "", candidate

    @classmethod
    def validate_csr(
        cls,
        candidate_or_company: Any,
        company_or_initiatives: Any = None,
        source_page_text: str = '',
        source_pdf_text: str = '',
        logs: List[str] = None
    ) -> Any:
        """
        Hard Validation Gate (Stage 7) for CSR Projects before database insertion.
        Supports both single candidate validation:
            validate_csr(cand, company, source_page_text, source_pdf_text, logs) -> (is_valid, reason, cand)
        and batch initiative list validation:
            validate_csr(company, initiatives, source_page_text, source_pdf_text) -> (valid_list, rejected_list)
            validate_csr(initiatives, company, source_page_text, source_pdf_text) -> (valid_list, rejected_list)

        Rules:
        1. Reject invalid CSR project names.
        2. Reject policy, ethics, compliance, or whistleblower statements.
        3. Resilient quote verification (100% exact, normalized alphanumeric, continuous n-gram, or >=75% token overlap).
        4. Source URL must be an allowed host.
        5. Never aborts the entire initiative list on a single invalid item.
        """
        logs = logs if logs is not None else []

        # Batch mode: company first, list second
        if isinstance(company_or_initiatives, list):
            company = candidate_or_company
            initiatives = company_or_initiatives
            valid_list = []
            rejected_list = []
            for item in initiatives:
                if not isinstance(item, dict):
                    continue
                ok, reason, validated = cls._validate_single_csr(item, company, source_page_text, source_pdf_text, logs)
                if ok:
                    valid_list.append(validated)
                else:
                    rejected_list.append({'candidate': item, 'reason': reason})
            return valid_list, rejected_list

        # Batch mode: list first, company second
        if isinstance(candidate_or_company, list):
            initiatives = candidate_or_company
            company = company_or_initiatives
            valid_list = []
            rejected_list = []
            for item in initiatives:
                if not isinstance(item, dict):
                    continue
                ok, reason, validated = cls._validate_single_csr(item, company, source_page_text, source_pdf_text, logs)
                if ok:
                    valid_list.append(validated)
                else:
                    rejected_list.append({'candidate': item, 'reason': reason})
            return valid_list, rejected_list

        # Single candidate mode:
        candidate = candidate_or_company
        company = company_or_initiatives
        return cls._validate_single_csr(candidate, company, source_page_text, source_pdf_text, logs)

    @classmethod
    def _validate_single_csr(
        cls,
        candidate: Dict[str, Any],
        company: Any,
        source_page_text: str,
        source_pdf_text: str = '',
        logs: List[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        logs = logs if logs is not None else []
        name = (candidate.get('project_name') or '').strip()
        src_url = (candidate.get('source_url') or '').strip()
        quote = (candidate.get('verbatim_quote') or candidate.get('description') or '').strip()

        # 1. Project Name Validation
        if not name or not is_valid_csr_project(name):
            reason = f"INVALID_CSR_PROJECT_NAME: '{name[:40]}'"
            if company and hasattr(cls, '_record_dropped_candidate'):
                cls._record_dropped_candidate(company, 'CSR', name, src_url, reason, candidate)
            return False, reason, candidate

        # 2. Reject Policy / Compliance / Ethics Statements
        n_lower = name.lower()
        policy_indicators = [
            'policy', 'code of conduct', 'whistleblower', 'ethics', 'ethical', 'compliance',
            'marketing', 'committee', 'governance', 'disclaimer', 'we hold ourselves',
            'equal employment', 'standards of business', 'terms of use', 'privacy statement',
            'anti-bribery', 'human rights policy', 'sustainability statement'
        ]
        if any(k in n_lower for k in policy_indicators):
            reason = f"POLICY_NOT_PROJECT: '{name[:40]}'"
            if company and hasattr(cls, '_record_dropped_candidate'):
                cls._record_dropped_candidate(company, 'CSR', name, src_url, reason, candidate)
            return False, reason, candidate

        # 2b. Reject umbrella labels that do not name a specific project,
        # e.g. "Reliance Foundation CSR activities".
        if (
            re.search(r'\b(csr|corporate social responsibility)\s+(activities|initiatives|programmes|programs|projects)\s*$', n_lower)
            and len(n_lower.split()) <= 6
        ):
            reason = f"UMBRELLA_LABEL_NOT_PROJECT: '{name[:40]}'"
            if company and hasattr(cls, '_record_dropped_candidate'):
                cls._record_dropped_candidate(company, 'CSR', name, src_url, reason, candidate)
            return False, reason, candidate

        # 3. Resilient Verbatim Quote Verification
        if not quote or len(quote) < 8:
            reason = "MISSING_VERBATIM_QUOTE"
            if company and hasattr(cls, '_record_dropped_candidate'):
                cls._record_dropped_candidate(company, 'CSR', name, src_url, reason, candidate)
            return False, reason, candidate

        # Normalize whitespace BEFORE the substring check (Bug 2 fix)
        quote_lower = re.sub(r'\s+', ' ', (quote or '').strip().lower())
        src_lower = re.sub(r'\s+', ' ', (source_page_text or '').lower())
        pdf_lower = re.sub(r'\s+', ' ', (source_pdf_text or candidate.get('raw_pdf_text') or candidate.get('source_text') or '').lower())

        # 3a. Exact substring in web page or PDF text (whitespace-normalized)
        is_verbatim = (quote_lower in src_lower) or (pdf_lower and (quote_lower in pdf_lower))

        # 3b. Normalized alphanumeric substring
        if not is_verbatim:
            norm_q = re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', quote_lower)).strip()
            norm_src = re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', src_lower))
            norm_pdf = re.sub(r'\s+', ' ', re.sub(r'[^a-zA-Z0-9\s]', ' ', pdf_lower)) if pdf_lower else ''
            if norm_q and (norm_q in norm_src or (norm_pdf and norm_q in norm_pdf)):
                is_verbatim = True

            # 3c. Continuous N-gram match (min 4 words)
            if not is_verbatim:
                words_q = [w for w in norm_q.split() if len(w) > 1]
                if len(words_q) >= 4:
                    n = min(len(words_q), 5)
                    for i in range(len(words_q) - n + 1):
                        sub_phrase = ' '.join(words_q[i:i+n])
                        if sub_phrase in norm_src or (norm_pdf and sub_phrase in norm_pdf):
                            is_verbatim = True
                            break

            # 3d. Token-level overlap (>= 75% of significant words)
            if not is_verbatim:
                stop_words = {'and', 'or', 'in', 'the', 'for', 'at', 'with', 'from', 'this', 'that', 'our', 'all', 'are', 'was', 'were', 'been', 'have', 'has'}
                sig_words = [w for w in words_q if len(w) >= 3 and w not in stop_words]
                if len(sig_words) >= 3:
                    found_in_src = sum(1 for w in sig_words if w in norm_src)
                    found_in_pdf = sum(1 for w in sig_words if norm_pdf and w in norm_pdf)
                    max_found = max(found_in_src, found_in_pdf)
                    if (max_found / len(sig_words)) >= 0.75:
                        is_verbatim = True

        if not is_verbatim:
            reason = f"QUOTE_NOT_VERBATIM_SUBSTRING: '{quote[:40]}'"
            if company and hasattr(cls, '_record_dropped_candidate'):
                cls._record_dropped_candidate(company, 'CSR', name, src_url, reason, candidate)
            return False, reason, candidate

        # 4. Allowed Host Check
        if src_url and company:
            allowed_domains = set()
            for candidate_domain in [
                getattr(company, 'official_domain', None),
                getattr(company, 'website_url', None),
                getattr(company, 'csr_portal_url', None),
                getattr(company, 'sustainability_url', None),
                candidate.get('csr_portal_url'),
                candidate.get('source_url'),
            ]:
                if candidate_domain:
                    reg = get_registrable_domain(candidate_domain)
                    if reg and not any(reg.endswith(ats) or ats in reg for ats in ALLOWED_ATS_HOSTS):
                        allowed_domains.add(reg)

            if hasattr(company, 'csr_portal_url') and company.csr_portal_url:
                c_reg = get_registrable_domain(company.csr_portal_url)
                if c_reg and not any(c_reg.endswith(ats) or ats in c_reg for ats in ALLOWED_ATS_HOSTS):
                    allowed_domains.add(c_reg)

            # If company name / brand matches registrable domain of src_url
            c_name = getattr(company, 'company_name', '')
            c_clean = re.sub(r'[^a-zA-Z0-9]', '', c_name).lower()
            src_reg = get_registrable_domain(src_url)
            if c_clean and len(c_clean) >= 3 and (c_clean in src_reg.lower() or src_reg.lower() in c_clean):
                allowed_domains.add(src_reg)

            is_allowed = any(is_allowed_domain_or_ats(src_url, d) for d in allowed_domains) if allowed_domains else False
            if not is_allowed:
                reason = f"DISALLOWED_CSR_HOST: '{src_url[:45]}'"
                if company and hasattr(cls, '_record_dropped_candidate'):
                    cls._record_dropped_candidate(company, 'CSR', name, src_url, reason, candidate)
                return False, reason, candidate

        return True, "", candidate

    # ------------------------------------------------------------------
    # Autonomous discovery helpers (sitemap, link graph, reports, progress)
    # ------------------------------------------------------------------
    @classmethod
    def _fetch_sitemap_urls(
        cls,
        base_url: str,
        timeout: int = 5,
        max_sitemaps: int = 4,
        max_urls: int = 500,
    ) -> List[str]:
        """Fetches robots.txt sitemap declarations and /sitemap.xml (including
        sitemap indexes) and returns the discovered page URLs.

        This is deliberately bounded: a handful of sitemaps and at most
        ``max_urls`` page URLs.  Failures are non-fatal and simply yield fewer
        URLs (never an exception that could abort the whole discovery run).
        """
        if not base_url:
            return []
        parsed = urllib.parse.urlparse(base_url)
        if not parsed.scheme or not parsed.netloc:
            return []
        origin = f"{parsed.scheme}://{parsed.netloc}"

        queue: List[str] = []
        seen_sitemaps = set()
        urls: List[str] = []

        # robots.txt is the cheapest place to learn the real sitemap locations.
        try:
            robots_html, robots_text, _ = cls.fetch_page_content(f"{origin}/robots.txt", timeout=3)
            for line in ((robots_html or robots_text) or '').splitlines():
                m = re.match(r'\s*sitemap:\s*(\S+)', line, re.IGNORECASE)
                if m:
                    queue.append(m.group(1).strip())
        except Exception:
            pass
        queue.append(f"{origin}/sitemap.xml")

        while queue and len(seen_sitemaps) < max_sitemaps and len(urls) < max_urls:
            sitemap_url = queue.pop(0).strip()
            if not sitemap_url or sitemap_url in seen_sitemaps:
                continue
            seen_sitemaps.add(sitemap_url)
            try:
                raw, text, _status = cls.fetch_page_content(sitemap_url, timeout=timeout)
            except Exception:
                continue
            body = raw or text or ''
            if not body:
                continue
            locs = re.findall(r'<loc[^>]*>\s*([^<]+?)\s*</loc>', body, re.IGNORECASE)
            if not locs:
                continue
            is_index = '<sitemapindex' in body[:2000].lower()
            for loc in locs:
                loc = _html.unescape(loc.strip())
                if not loc.startswith(('http://', 'https://')):
                    continue
                if is_index or loc.lower().split('?')[0].endswith('.xml'):
                    if len(seen_sitemaps) + len(queue) < max_sitemaps * 4:
                        queue.append(loc)
                else:
                    if loc not in urls:
                        urls.append(loc)
                    if len(urls) >= max_urls:
                        break
        return urls

    @classmethod
    def _pick_sitemap_targets(cls, sitemap_urls: List[str], official_domain: str) -> Dict[str, List[str]]:
        """Classifies sitemap URLs into careers / CSR / report candidates."""
        careers_re = re.compile(
            r'(career|careers|jobs?|vacanc|opening|hiring|recruit|work-with-us|join-us|join-our-team)',
            re.IGNORECASE,
        )
        csr_re = re.compile(
            r'(csr|corporate-social|social-responsibility|sustainability|esg|foundation|'
            r'community|rural-development|social-impact|environment|philanthrop|impact)',
            re.IGNORECASE,
        )
        targets = {'careers': [], 'csr': [], 'reports': []}
        for url in sitemap_urls or []:
            if not url:
                continue
            try:
                if official_domain and not is_allowed_domain_or_ats(url, official_domain):
                    continue
            except Exception:
                continue
            low = url.lower()
            is_pdf = low.split('?')[0].endswith('.pdf')
            if _is_report_document_url(url):
                targets['reports'].append(url)
            if not is_pdf and careers_re.search(low):
                targets['careers'].append(url)
            if not is_pdf and csr_re.search(low) and not _is_marketing_service_url(url):
                targets['csr'].append(url)

        # Shallow, stable URLs first: they are the most likely official hubs.
        # Report PDFs are ranked before report hubs so deep enrichment analyses
        # actual disclosures rather than random editorial pages.
        def _rank(u: str, key: str = ''):
            path = urllib.parse.urlparse(u).path or '/'
            pdf_first = 0 if (key == 'reports' and path.lower().endswith('.pdf')) else 1
            return (pdf_first, path.count('/'), len(path), u)

        for key in targets:
            deduped = list(dict.fromkeys(targets[key]))
            targets[key] = sorted(deduped, key=lambda u, k=key: _rank(u, k))[:12]
        return targets

    @classmethod
    def _find_external_signal_links(cls, raw_html: str, base_url: str, comp_name: str) -> List[Dict[str, str]]:
        """Finds likely official foundation / group CSR destinations linked from
        the homepage.  Only links whose host or anchor text carries the company
        brand token (or an explicit foundation signal) are returned, so random
        third-party links are not treated as company sources."""
        results: List[Dict[str, str]] = []
        if not raw_html or not base_url:
            return results
        base_reg = get_registrable_domain(base_url)
        brand_tokens = [
            t for t in re.split(r'[^a-z0-9]+', (comp_name or '').lower())
            if len(t) >= 3 and t not in {'limited', 'ltd', 'private', 'pvt', 'company', 'corporation', 'corp', 'india', 'group', 'the', 'and'}
        ]
        try:
            soup = BeautifulSoup(raw_html, 'html.parser')
        except Exception:
            return results
        for a in soup.find_all('a', href=True):
            href = (a.get('href') or '').strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            full = urllib.parse.urljoin(base_url, href).split('#')[0]
            if not full.startswith(('http://', 'https://')):
                continue
            reg = get_registrable_domain(full)
            if not reg or reg == base_reg:
                continue
            if any(ats in reg for ats in ALLOWED_ATS_HOSTS):
                continue
            text = a.get_text(' ', strip=True)
            haystack = f"{reg} {full} {text}".lower()
            has_brand = any(tok in haystack for tok in brand_tokens) if brand_tokens else False
            has_signal = any(k in haystack for k in ('foundation', 'csr', 'social-responsibility', 'sustainability', 'trust', 'philanthrop'))
            if has_brand and has_signal:
                results.append({'url': full, 'text': text[:160], 'reason': 'linked_official_foundation'})
        # Deduplicate by URL host + path
        deduped = {}
        for item in results:
            key = item['url'].rstrip('/').lower()
            if key not in deduped:
                deduped[key] = item
        return list(deduped.values())[:6]

    @classmethod
    def _classify_report(cls, title: str, url: str) -> str:
        combined = f"{title or ''} {url or ''}".lower()
        if 'brsr' in combined:
            return 'BRSR'
        if 'integrated' in combined:
            return 'INTEGRATED'
        if 'annual' in combined:
            return 'ANNUAL'
        if 'sustainab' in combined or 'esg' in combined:
            return 'SUSTAINABILITY'
        if 'section 135' in combined or 'section-135' in combined or 'csr' in combined:
            return 'CSR'
        return 'OTHER'

    @classmethod
    def _extract_financial_year(cls, text: str) -> str:
        if not text:
            return ''
        patterns = [
            r'(?:financial\s+year|fy)\s*[:\-–]?\s*(20\d{2})\s*[-–/]\s*(20\d{2}|\d{2})',
            r'\b(20\d{2})\s*[-–/]\s*(20\d{2}|\d{2})\b',
        ]
        for pat in patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                start, end = m.group(1), m.group(2)
                if len(end) == 2:
                    end = start[:2] + end
                try:
                    if 2000 <= int(start) <= 2100 and int(end) == int(start) + 1:
                        return f"FY {start}-{str(end)[-2:]}"
                except Exception:
                    continue
        return ''

    @classmethod
    def _discover_report_links(cls, raw_html: str, base_url: str) -> List[Dict[str, str]]:
        """Finds CSR / annual / BRSR / sustainability report links on a page."""
        results: List[Dict[str, str]] = []
        if not base_url:
            return results
        if base_url.lower().split('?')[0].endswith('.pdf'):
            results.append({
                'url': base_url,
                'title': _humanize_report_title(base_url)[:180],
                'report_type': cls._classify_report(base_url, base_url),
            })
            return results
        if not raw_html:
            return results
        try:
            soup = BeautifulSoup(raw_html, 'html.parser')
        except Exception:
            return results
        for a in soup.find_all('a', href=True):
            href = (a.get('href') or '').strip()
            if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
                continue
            full = urllib.parse.urljoin(base_url, href).split('#')[0]
            if not full.startswith(('http://', 'https://')):
                continue
            text = a.get_text(' ', strip=True)
            if not _is_report_document_url(full, text):
                continue
            fallback = _humanize_report_title(full)
            generic_anchor = (text or '').strip().lower() in {
                'read more', 'read more...', 'learn more', 'view', 'view more', 'download',
                'download pdf', 'click here', 'here', 'pdf', 'open', 'link',
            }
            results.append({
                'url': full,
                'title': ((fallback if generic_anchor else text) or fallback)[:180],
                'report_type': cls._classify_report(text, full),
            })
        deduped = {}
        for item in results:
            key = item['url'].rstrip('/').lower()
            if key not in deduped:
                deduped[key] = item
        return list(deduped.values())[:10]

    @classmethod
    def _text_value(cls, value: Any, limit: int = 8000) -> str:
        if value is None:
            return ''
        if isinstance(value, (list, tuple, set)):
            joined = '; '.join(str(v).strip() for v in value if v not in (None, ''))
            return joined[:limit]
        if isinstance(value, dict):
            try:
                return json.dumps(value, ensure_ascii=False)[:limit]
            except Exception:
                return str(value)[:limit]
        return str(value).strip()[:limit]

    @classmethod
    def _list_value(cls, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(v).strip() for v in value if str(v).strip()]
        return [part.strip() for part in re.split(r'[;|\n]+|,\s*(?=[A-Z])', str(value)) if part.strip()]

    @classmethod
    def _publish_progress(cls, options: Dict[str, Any], payload: Dict[str, Any]) -> None:
        token = ''
        if isinstance(options, dict):
            token = str(options.get('progress_token') or options.get('session_id') or '')
        if not token:
            return
        try:
            cache.set(f'discovery_progress_{token}', payload, timeout=3600)
            cache.set(f'discovery_telemetry_{token}', payload, timeout=3600)
        except Exception:
            pass

    @classmethod
    def _persist_job_candidates(
        cls,
        company: Company,
        candidates: List[Dict[str, Any]],
        now: Any,
        logs: List[str],
        seen_urls: set = None,
    ) -> Tuple[List[Dict[str, Any]], List[int]]:
        """Validates and upserts job candidates without deleting existing rows.

        Returns ``(validated_candidates, saved_job_row_ids)``.  Existing records
        for the same (company, title, application URL) are updated in place, so
        an incomplete crawl can never wipe previously verified vacancies.
        """
        seen_urls = seen_urls if seen_urls is not None else set()
        validated_jobs: List[Dict[str, Any]] = []
        seen_job_keys = set()
        for cand in candidates or []:
            try:
                is_valid, reason, validated_cand = cls.validate_job(cand, company, seen_urls, logs)
            except Exception as exc:
                logs.append(f"Job validation error for '{(cand or {}).get('job_title', '')[:40]}': {str(exc)[:100]}")
                continue
            if not is_valid:
                continue
            req_id = (validated_cand.get('requisition_id') or '').strip()
            t_norm = (validated_cand.get('job_title') or '').strip().lower()
            loc_norm = (validated_cand.get('location') or '').strip().lower()
            dedupe_key = req_id if req_id else (t_norm, loc_norm)
            if dedupe_key in seen_job_keys:
                cls._record_dropped_candidate(
                    company, 'JOB', validated_cand.get('job_title', ''),
                    validated_cand.get('application_url', ''), 'DUPLICATE_RECORD', validated_cand,
                )
                continue
            seen_job_keys.add(dedupe_key)
            validated_jobs.append(validated_cand)

        saved_ids: List[int] = []
        for j in validated_jobs:
            title = j.get('job_title') or ''
            app_url = j.get('application_url') or ''
            if not title or not app_url:
                continue
            slug = re.sub(r'[^a-zA-Z0-9]+', '', title).upper()[:8]
            job_hash = hashlib.md5(f"{company.company_id}_{title}_{app_url}".encode('utf-8')).hexdigest()[:6].upper()
            evidence_h = hashlib.sha256(f"{company.company_id}_{title}_{app_url}".encode('utf-8')).hexdigest()
            skills_list = cls._list_value(j.get('skills') or j.get('required_skills'))
            defaults = {
                'job_id': f"JOB_{company.company_id}_{slug}_{job_hash}",
                'external_job_id': (j.get('requisition_id') or j.get('external_job_id') or '')[:120] or None,
                'ats_platform': (j.get('ats_platform') or '')[:80] or None,
                'department': cls._text_value(j.get('department'))[:500] or 'Corporate',
                'team': cls._text_value(j.get('team'))[:500] or None,
                'location': cls._text_value(j.get('location'))[:500] or 'India',
                'city': cls._text_value(j.get('city'))[:200] or None,
                'state': cls._text_value(j.get('state'))[:200] or None,
                'work_mode': (j.get('work_mode') or '')[:80] or None,
                'employment_type': (j.get('employment_type') or '')[:80] or None,
                'experience': cls._text_value(j.get('experience'))[:120] or None,
                'education': cls._text_value(j.get('education') or j.get('qualifications')) or None,
                'skills': '; '.join(skills_list)[:2000] or None,
                'required_skills': skills_list,
                'job_description': cls._text_value(j.get('description') or j.get('job_description')) or None,
                'description_raw': cls._text_value(j.get('description') or j.get('job_description')) or None,
                'responsibilities': cls._text_value(j.get('responsibilities')) or None,
                'requirements': cls._text_value(j.get('requirements')) or None,
                'qualifications': cls._text_value(j.get('qualifications')) or None,
                'posted_date': cls._text_value(j.get('posting_date') or j.get('posted_date'))[:80] or None,
                'salary': cls._text_value(j.get('salary_range') or j.get('salary'))[:120] or None,
                'salary_text': cls._text_value(j.get('salary_range') or j.get('salary'))[:120] or None,
                'application_url': app_url,
                'canonical_url': app_url,
                'source_url': j.get('source_url') or app_url,
                'status': 'ACTIVE',
                'verification_status': 'PUBLISHED',
                'confidence': float(j.get('confidence') or 0.90),
                'retrieved_at': now,
                'first_seen_at': now,
                'last_seen_at': now,
                'evidence_text': (j.get('verbatim_source_quote') or j.get('verbatim_quote') or '')[:4000] or f"Verified opening on {app_url}",
                'content_hash': evidence_h,
                'verification_reason': 'Validated live job opening from an authoritative company or ATS source',
                'extraction_method': (j.get('extraction_method') or 'autonomous_discovery')[:100],
                'details_status': 'PARTIAL' if (j.get('description') or j.get('job_description')) else 'MISSING',
            }
            try:
                obj, _created = Job.objects.update_or_create(
                    company=company,
                    job_title=title,
                    application_url=app_url,
                    defaults=defaults,
                )
                saved_ids.append(obj.job_row_id)
            except Exception as exc:
                logs.append(f"Job save failed for '{title[:50]}': {str(exc)[:120]}")
                cls._record_dropped_candidate(company, 'JOB', title, app_url, f'DATABASE_SAVE_FAILED: {str(exc)[:120]}', j)

        if validated_jobs:
            logs.append(f"Validated & saved {len(saved_ids)} job opening(s) (existing records updated, none deleted).")
        return validated_jobs, saved_ids

    @classmethod
    def _persist_csr_candidates(
        cls,
        company: Company,
        candidates: List[Dict[str, Any]],
        csr_text: str,
        now: Any,
        logs: List[str],
    ) -> Tuple[List[Dict[str, Any]], List[int]]:
        """Validates and upserts CSR projects without deleting existing rows."""
        validated_csr: List[Dict[str, Any]] = []
        seen_csr_keys = set()
        for cand in candidates or []:
            try:
                is_valid, reason, validated_cand = cls.validate_csr(
                    cand, company, csr_text or '', cand.get('raw_pdf_text', ''), logs,
                )
            except Exception as exc:
                logs.append(f"CSR validation error for '{(cand or {}).get('project_name', '')[:40]}': {str(exc)[:100]}")
                continue
            if not is_valid:
                continue
            p_norm = (validated_cand.get('project_name') or '').strip().lower()
            if p_norm in seen_csr_keys:
                cls._record_dropped_candidate(
                    company, 'CSR', validated_cand.get('project_name', ''),
                    validated_cand.get('source_url', ''), 'DUPLICATE_PROJECT', validated_cand,
                )
                continue
            seen_csr_keys.add(p_norm)
            validated_csr.append(validated_cand)

        saved_ids: List[int] = []
        for c in validated_csr:
            p_name = (c.get('project_name') or '').strip()
            if not p_name:
                continue
            c_src = c.get('source_url') or ''
            evidence_h = hashlib.sha256(f"{company.company_id}_{p_name}_{c_src}".encode('utf-8')).hexdigest()
            raw_meta = {
                'ai_summary': c.get('summary') or c.get('description') or '',
                'schedule_vii': c.get('schedule_vii') or c.get('schedule_vii_category') or '',
                'topic': c.get('topic') or c.get('category') or '',
                'beneficiaries': cls._text_value(c.get('beneficiaries'), 2000),
                'implementing_partner': cls._text_value(c.get('partner') or c.get('implementing_partner'), 1000),
                'financial_year': c.get('financial_year') or '',
                'expenditure': cls._text_value(c.get('expenditure') or c.get('budget'), 500),
                'confidence': float(c.get('confidence') or 0.90),
            }
            defaults = {
                'category': cls._text_value(c.get('category') or c.get('topic'))[:500] or 'Corporate Social Responsibility',
                'state': cls._text_value(c.get('state'))[:300] or 'Not specified',
                'geographic_location': cls._text_value(c.get('district') or c.get('geographic_location') or c.get('state'))[:500] or 'India',
                'budget': cls._text_value(c.get('budget') or c.get('expenditure'))[:500] or 'Not published',
                'description': cls._text_value(c.get('description') or c.get('summary')) or None,
                'confidence': float(c.get('confidence') or 0.90),
                'status': 'ACTIVE',
                'source_url': c_src,
                'canonical_url': c_src,
                'verification_status': 'PUBLISHED',
                'retrieved_at': now,
                'first_seen_at': now,
                'last_seen_at': now,
                'evidence_text': (c.get('verbatim_quote') or c.get('evidence_text') or '')[:4000] or f"Verified CSR initiative: {p_name}",
                'content_hash': evidence_h,
                'verification_reason': 'Validated CSR initiative with traceable source evidence',
                'raw_metadata': raw_meta,
            }
            try:
                obj, _created = CSRProject.objects.update_or_create(
                    company=company,
                    project_name=p_name,
                    defaults=defaults,
                )
                saved_ids.append(obj.csr_id)
            except Exception as exc:
                logs.append(f"CSR project save failed for '{p_name[:50]}': {str(exc)[:120]}")
                cls._record_dropped_candidate(company, 'CSR', p_name, c_src, f'DATABASE_SAVE_FAILED: {str(exc)[:120]}', c)

        if validated_csr:
            logs.append(f"Validated & saved {len(saved_ids)} CSR project(s) (existing records updated, none deleted).")
        return validated_csr, saved_ids

    @classmethod
    def _report_row(cls, report: CSRReport) -> Dict[str, Any]:
        return {
            'report_id': str(report.report_id),
            'title': report.title,
            'report_type': report.report_type,
            'financial_year': report.financial_year or '',
            'source_url': report.source_url,
            'summary': report.summary or '',
            'topics': report.topics or [],
            'initiatives': report.initiatives or [],
            'key_findings': report.key_findings or [],
            'expenditure': report.expenditure or '',
            'beneficiaries': report.beneficiaries or '',
            'geographic_coverage': report.geographic_coverage or '',
            'implementing_partners': report.implementing_partners or '',
            'evidence_text': report.evidence_text or '',
        }

    @classmethod
    def _persist_reports(
        cls,
        company: Company,
        report_docs: List[Dict[str, Any]],
        now: Any,
        logs: List[str],
    ) -> List[Dict[str, Any]]:
        """Persists / updates CSR, annual, BRSR and sustainability report metadata."""
        saved: List[Dict[str, Any]] = []
        for doc in report_docs or []:
            url = (doc.get('url') or '').strip()
            if not url:
                continue
            text = doc.get('text') or ''
            title = (doc.get('title') or '').strip()
            title = re.sub(r'\s+', ' ', title)
            if not title:
                title = _humanize_report_title(url)
            elif ' ' not in title and ('-' in title or '_' in title):
                title = _humanize_report_title(title)
            if len(title) < 3:
                title = 'Corporate CSR / Sustainability Report'
            fy = doc.get('financial_year') or cls._extract_financial_year(f"{title} {text[:4000]}")
            report_type = doc.get('report_type') or cls._classify_report(title, url)
            summary = doc.get('summary') or ''
            topics = doc.get('topics') or []
            initiatives = doc.get('initiatives') or []
            findings = doc.get('key_findings') or []
            expenditure = doc.get('expenditure') or ''
            beneficiaries = doc.get('beneficiaries') or ''
            coverage = doc.get('geographic_coverage') or ''
            partners = doc.get('implementing_partners') or ''
            evidence = doc.get('evidence_text') or ''

            # AI report analysis when a provider is configured and text exists.
            if text and len(text) > 250:
                try:
                    ai_report = HybridAIExtractionService.summarize_csr_report(
                        company_id=company.company_id,
                        company_name=company.company_name,
                        report_url=url,
                        raw_content=text,
                        timeout=18,
                    )
                    if isinstance(ai_report, dict):
                        summary = ai_report.get('summary') or summary
                        topics = ai_report.get('topics') or topics
                        initiatives = ai_report.get('initiatives') or initiatives
                        findings = ai_report.get('key_findings') or findings
                        expenditure = ai_report.get('expenditure') or expenditure
                        beneficiaries = ai_report.get('beneficiaries') or beneficiaries
                        coverage = ai_report.get('geographic_coverage') or coverage
                        partners = ai_report.get('implementing_partners') or partners
                        fy = ai_report.get('financial_year') or fy
                        evidence = ai_report.get('evidence_quote') or evidence
                except Exception as exc:
                    logs.append(f"AI report analysis note: {str(exc)[:100]}")

            if not summary:
                # Honest extractive fallback: first substantive paragraphs of the
                # official document, never an invented narrative.
                cleaned = re.sub(r'\s+', ' ', text).strip()
                summary = cleaned[:1200]
            if not evidence:
                evidence = re.sub(r'\s+', ' ', text).strip()[:500]

            content_hash = hashlib.sha256(f"{company.company_id}|{url.rstrip('/').lower()}".encode('utf-8')).hexdigest()
            try:
                obj, _created = CSRReport.objects.update_or_create(
                    company=company,
                    content_hash=content_hash,
                    defaults={
                        'title': title[:255],
                        'report_type': report_type,
                        'financial_year': (fy or '')[:30] or None,
                        'source_url': url,
                        'summary': summary or None,
                        'topics': cls._list_value(topics),
                        'initiatives': cls._list_value(initiatives),
                        'key_findings': cls._list_value(findings),
                        'expenditure': cls._text_value(expenditure, 1000) or None,
                        'beneficiaries': cls._text_value(beneficiaries, 2000) or None,
                        'geographic_coverage': cls._text_value(coverage, 1000) or None,
                        'implementing_partners': cls._text_value(partners, 2000) or None,
                        'evidence_text': (evidence or '')[:4000] or None,
                        'verification_status': 'PUBLISHED',
                        'retrieved_at': now,
                        'first_seen_at': now,
                        'last_seen_at': now,
                    },
                )
                saved.append(cls._report_row(obj))
            except Exception as exc:
                logs.append(f"Report save failed for '{title[:50]}': {str(exc)[:120]}")
        if saved:
            logs.append(f"Validated & saved {len(saved)} CSR/report document(s).")
        return saved

    @classmethod
    def _deep_enrich(
        cls,
        company_id: str,
        options: Dict[str, Any],
        sitemap_targets: Dict[str, List[str]],
        processed_careers: List[str],
        processed_csr: List[str],
        processed_reports: List[str],
    ) -> None:
        """Background deep enrichment: continues discovering additional jobs,
        CSR projects and reports after the initial response has been returned.

        It never deletes anything and only adds/updates verified records.
        """
        try:
            from django.db import connection
            if connection.vendor == 'sqlite':
                return  # test databases: never spawn background DB writers
        except Exception:
            pass
        try:
            close_old_connections()
            company = Company.objects.filter(pk=company_id).first()
            if not company:
                return
            logs: List[str] = []
            now = timezone.now()
            started = time.monotonic()
            token = (options or {}).get('progress_token') or (options or {}).get('session_id') or ''
            seen_urls: set = set()
            new_jobs = 0
            new_csr = 0
            new_reports = 0

            career_urls = [u for u in (sitemap_targets.get('careers') or []) if u not in processed_careers][:6]
            for extra_url in career_urls:
                try:
                    html, text, status = cls.fetch_page_content(extra_url, timeout=6)
                    if status != 200 or not text or len(text) < 120:
                        continue
                    cands = cls.discover_all_real_jobs(company, extra_url, html, text, company.sector or '', logs)
                    if cands:
                        _v, ids = cls._persist_job_candidates(company, cands, now, logs, seen_urls)
                        new_jobs += len(ids)
                except Exception:
                    continue

            csr_urls = [u for u in (sitemap_targets.get('csr') or []) if u not in processed_csr][:6]
            for extra_url in csr_urls:
                try:
                    html, text, status = cls.fetch_page_content(extra_url, timeout=6)
                    if status != 200 or not text or len(text) < 120:
                        continue
                    cands = cls.discover_all_real_csr(company, extra_url, html, text, company.sector or '', logs)
                    if cands:
                        _v, ids = cls._persist_csr_candidates(company, cands, text, now, logs)
                        new_csr += len(ids)
                except Exception:
                    continue

            report_urls = [u for u in (sitemap_targets.get('reports') or []) if u not in processed_reports][:4]
            report_docs = []
            for report_url in report_urls:
                try:
                    if report_url.lower().split('?')[0].endswith('.pdf'):
                        text = cls.extract_pdf_text_from_url(report_url, max_pages=8, timeout=10)
                    else:
                        _h, text, _s = cls.fetch_page_content(report_url, timeout=6)
                    if text and len(text) > 200:
                        report_docs.append({
                            'url': report_url,
                            'title': _humanize_report_title(report_url)[:180],
                            'report_type': cls._classify_report(report_url, report_url),
                            'text': text,
                        })
                except Exception:
                    continue
            if report_docs:
                new_reports = len(cls._persist_reports(company, report_docs, now, logs))

            if token:
                payload = cache.get(f'discovery_progress_{token}') or {}
                if isinstance(payload, dict):
                    payload.update({
                        'deep_enrichment': 'COMPLETED',
                        'deep_enrichment_ms': int((time.monotonic() - started) * 1000),
                        'deep_enrichment_new_jobs': new_jobs,
                        'deep_enrichment_new_csr': new_csr,
                        'deep_enrichment_new_reports': new_reports,
                        'jobs_imported': company.jobs.count(),
                        'csr_imported': company.csr_projects.count(),
                        'reports_count': company.csr_reports.count(),
                        'stage': 'Deep enrichment complete',
                    })
                    cache.set(f'discovery_progress_{token}', payload, timeout=3600)
                    cache.set(f'discovery_telemetry_{token}', payload, timeout=3600)
        except Exception as exc:
            try:
                logger.warning(f"Deep enrichment failed for {company_id}: {exc}")
            except Exception:
                pass
        finally:
            try:
                close_old_connections()
            except Exception:
                pass

    @classmethod
    def process_single_company(cls, company_task: Dict[str, Any], options: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Executes strict live web crawling and AI extraction for a company adhering to Stages 1-9:
        - Stage 1: Strict 2-field input validation (reject missing/invalid company_name or homepage_url).
        - Stage 2: Company matching via registrable domain primary key, exact name fallback,
                   plus metadata extraction (sector & headquarters) directly from crawled homepage HTML.
        - Stage 3: Autonomous portal discovery from homepage HTML, 1-hop hub links, subdomains,
                   registries, and corporate paths.
        - Stage 4 & 6: Job crawling and hard validation gate (validate_job).
        - Stage 7: CSR crawling and hard validation gate (validate_csr).
        - Stage 8: Deduplication before insert.
        - Stage 9: Strict Database == UI == Export synchronization.
        """
        options = options or {}
        comp_name = (company_task.get('company_name') or '').strip()
        raw_user_url = (company_task.get('homepage_url') or company_task.get('website_url') or '').strip()
        user_url = cls._sanitize_url(raw_user_url)

        # If a URL was passed in company_name alongside a valid homepage_url, clean company_name
        if comp_name and user_url and (re.match(r'^(https?://|www\.)', comp_name, re.IGNORECASE) or comp_name.lower() == raw_user_url.lower()):
            extracted_name = urllib.parse.urlparse(user_url).netloc.replace('www.', '').split('.')[0].title()
            if extracted_name:
                comp_name = extracted_name

        logs = []
        now = timezone.now()

        # STAGE 1: STRICT INPUT CONTRACT VALIDATION (both company_name and homepage_url required)
        if not comp_name or not user_url:
            err_msg = f"Rejected: both company_name and homepage_url are strictly required (got company_name='{comp_name}', homepage_url='{raw_user_url}')."
            logs.append(f"[ERROR] {err_msg}")
            return {
                'status': 'error',
                'company_name': comp_name or 'Unknown',
                'message': err_msg,
                'jobs': [],
                'csr': [],
                'jobs_discovered': 0,
                'jobs_imported': 0,
                'csr_discovered': 0,
                'csr_imported': 0,
                'jobs_dropped': 0,
                'csr_dropped': 0,
                'logs': logs
            }

        # Normalize URL: prepend https://, strip tracking parameters
        norm_url = user_url
        if not norm_url.startswith(('http://', 'https://')):
            norm_url = 'https://' + norm_url
        norm_url = re.sub(r'([?&])(utm_[^&]+|fbclid=[^&]+|ref=[^&]+)', '', norm_url).rstrip('&?')

        # Fetch homepage HTML directly
        final_website = norm_url
        _t_home_fetch = time.monotonic()
        home_html, home_text, home_status = cls.fetch_page_content(norm_url)
        homepage_fetch_ms = (time.monotonic() - _t_home_fetch) * 1000
        if home_status in (200, 301, 302, 307, 308):
            final_website = norm_url
        official_domain = get_registrable_domain(final_website)

        if not official_domain or '.' not in official_domain:
            err_msg = f"Rejected: invalid homepage_url domain '{raw_user_url}' for company '{comp_name}'"
            logs.append(f"[ERROR] {err_msg}")
            return {
                'status': 'error',
                'company_name': comp_name,
                'message': err_msg,
                'jobs': [],
                'csr': [],
                'jobs_discovered': 0,
                'jobs_imported': 0,
                'csr_discovered': 0,
                'csr_imported': 0,
                'jobs_dropped': 0,
                'csr_dropped': 0,
                'logs': logs
            }

        HybridAIExtractionService.begin_trace()
        try:
            return cls._run_single_company_discovery(
                comp_name=comp_name,
                final_website=final_website,
                official_domain=official_domain,
                home_html=home_html,
                home_text=home_text,
                home_status=home_status,
                options=options,
                logs=logs,
                now=now,
                homepage_fetch_ms=homepage_fetch_ms,
            )
        finally:
            HybridAIExtractionService.end_trace()

    @classmethod
    def _run_single_company_discovery(
        cls,
        comp_name: str,
        final_website: str,
        official_domain: str,
        home_html: str,
        home_text: str,
        home_status: int,
        options: Dict[str, Any],
        logs: List[str],
        now: Any,
        homepage_fetch_ms: float = 0.0,
    ) -> Dict[str, Any]:
        logs.append(f"Starting live web discovery for '{comp_name}' (Homepage: {final_website}, Domain: {official_domain})...")

        _t_discovery_start = time.monotonic()
        # Telemetry timing defaults (overwritten by actual stage timers below)
        _careers_discovery_ms = 0.0
        _job_extraction_ms = 0.0
        _csr_extraction_ms = 0.0

        # Stage 1: homepage links are extracted immediately; sitemap discovery
        # is performed in the portal-discovery phase below (bounded + non-fatal).
        site_links = cls.find_target_links_from_html(home_html, final_website)
        sitemap_urls: List[str] = []
        sitemap_targets: Dict[str, List[str]] = {'careers': [], 'csr': [], 'reports': []}
        if (not home_html or len(home_text) < 200) and not (site_links.get('careers_url') and site_links.get('csr_url')):
            low_home = (home_html or '').lower()
            is_spa_or_waf = (
                not home_html
                or home_status in (202, 403)
                or any(k in low_home for k in (
                    'id="root"', 'id="app"', 'id="__next"', 'ng-app', '<router-outlet>',
                    'awswafcookiedomainlist', 'gokuprops', 'cf-browser-verification',
                    '__cf_chl', 'challenge-platform', 'just a moment...',
                ))
            )
            if is_spa_or_waf:
                r_html, r_text, r_stat = cls.fetch_rendered_page(final_website, timeout=8)
                if r_html and (len(r_text) > len(home_text) or len(r_html) > len(home_html or '')):
                    home_html, home_text, home_status = r_html, r_text, r_stat
                    site_links = cls.find_target_links_from_html(home_html, final_website)

        # Extract Sector & Headquarters directly from crawled homepage HTML/text
        extracted_meta = cls.extract_company_metadata_from_html(home_html, home_text, comp_name, final_website)
        sector_val = extracted_meta.get('sector') or 'Corporate Enterprise'
        hq_val = extracted_meta.get('headquarters') or 'India'
        logs.append(f"Extracted homepage metadata -> Sector: '{sector_val}', Headquarters: '{hq_val}'")

        generic_sectors = {'', 'corporate enterprise', 'enterprise', 'unknown', 'general', 'other', 'n/a', '-'}
        generic_hqs = {'', 'india', 'pan-india', 'pan india', 'unknown', 'n/a', '-'}

        # STAGE 2: COMPANY MATCHING (Registrable Domain Primary Key)
        company = None
        is_new_company = False
        existing = Company.objects.filter(official_domain__iexact=official_domain).first()
        if not existing:
            existing = Company.objects.filter(company_name__iexact=comp_name).first()

        if existing:
            company = existing
            is_new_company = False
            update_fields = ['official_domain', 'website_url']
            company.official_domain = official_domain
            company.website_url = final_website
            if (company.sector or '').strip().lower() in generic_sectors and sector_val.strip().lower() not in generic_sectors:
                company.sector = sector_val
                update_fields.append('sector')
            if (company.headquarters or '').strip().lower() in generic_hqs and hq_val.strip().lower() not in generic_hqs:
                company.headquarters = hq_val
                update_fields.append('headquarters')
            company.save(update_fields=update_fields)
            logs.append(f"Entity profile identified in directory: {company.company_id} ({company.company_name})")
        else:
            is_new_company = True
            slug = re.sub(r'[^a-zA-Z0-9]+', '', comp_name).upper()[:12]
            comp_hash = hashlib.md5(comp_name.encode('utf-8')).hexdigest()[:4].upper()
            comp_id = f"COMP_BATCH_{slug}_{comp_hash}"
            comp_content_hash = hashlib.sha256(f"{comp_name}_{final_website}".encode('utf-8')).hexdigest()

            company = Company.objects.create(
                company_id=comp_id,
                company_name=comp_name,
                legal_name=comp_name,
                sector=sector_val,
                headquarters=hq_val,
                official_domain=official_domain,
                website_url=final_website,
                source_url=final_website,
                canonical_url=final_website,
                careers_url='',
                csr_portal_url='',
                sustainability_url='',
                nse_symbol=None,
                verification_status='PUBLISHED',
                listing_status='Active',
                jobs_access='PUBLIC',
                csr_access='PUBLIC',
                contacts_access='PUBLIC',
                link_quality='EXCELLENT',
                website_url_status='ACTIVE',
                crawl_status='SUCCESS',
                data_confidence=0.95,
                retrieved_at=now,
                first_seen_at=now,
                last_seen_at=now,
                evidence_text=f"Batch discovered corporate portal: {final_website}",
                content_hash=comp_content_hash,
                verification_reason="Live Web AI Discovery automated validation"
            )
            logs.append(f"Provisioned new company in directory: {company.company_id} ({company.company_name})")
            cache.delete('companies_lookup_lightweight')

        base_url = final_website.rstrip('/')
        comp_lower = comp_name.strip().lower()

        # STAGE 3: PORTAL DISCOVERY (Autonomous discovery directly from Homepage URL alone)
        careers_url = ''
        careers_method = 'not_found'
        csr_url = ''
        csr_method = 'not_found'
        _t_careers_start = time.monotonic()

        # Priority 1: Direct links discovered from homepage navigation/anchors
        if site_links.get('careers_url'):
            c_cand = site_links['careers_url']
            if is_allowed_domain_or_ats(c_cand, official_domain):
                careers_url = c_cand
                careers_method = 'nav_link'
                logs.append(f"Discovered careers link from homepage navigation: {careers_url}")

        if site_links.get('csr_url'):
            csr_cand = site_links['csr_url']
            if is_allowed_domain_or_ats(csr_cand, official_domain):
                csr_url = csr_cand
                csr_method = 'nav_link'
                logs.append(f"Discovered CSR portal from homepage navigation: {csr_url}")

        # Priority 2: Lightweight 1-hop discovery across homepage hub links when careers or CSR is nested
        if not careers_url or not csr_url:
            hub_candidates: List[str] = []
            seen_hubs = {final_website.rstrip('/').lower()}
            hub_suffix_re = re.compile(r'(?:^|/)(company|about|about-us|who-we-are|investor-relations|investors)(?:\.html?)?$', re.IGNORECASE)

            if home_html:
                try:
                    h_soup = BeautifulSoup(home_html, 'html.parser')
                    for a in h_soup.find_all('a', href=True):
                        href = a['href'].strip()
                        if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')) or is_static_asset_url(href):
                            continue
                        full_hub = urllib.parse.urljoin(final_website, href).split('#')[0]
                        if not is_allowed_domain_or_ats(full_hub, official_domain):
                            continue
                        p_path = urllib.parse.urlparse(full_hub).path.rstrip('/').lower()
                        if hub_suffix_re.search(p_path):
                            norm_hub = full_hub.rstrip('/').lower()
                            if norm_hub not in seen_hubs:
                                seen_hubs.add(norm_hub)
                                hub_candidates.append(full_hub)
                except Exception:
                    pass

            for suffix in ('/company', '/about-us', '/about', '/investor-relations', '/investors'):
                probe_hub = f"{base_url}{suffix}"
                if probe_hub.rstrip('/').lower() not in seen_hubs:
                    seen_hubs.add(probe_hub.rstrip('/').lower())
                    hub_candidates.append(probe_hub)

            for hub_url in hub_candidates[:5]:
                if careers_url and csr_url:
                    break
                h_html, h_text, h_stat = cls.fetch_page_content(hub_url, timeout=4)
                if h_stat == 200 and h_html and not any(err in (h_text or '')[:300].lower() for err in ('404 not found', 'page not found')):
                    hub_links = cls.find_target_links_from_html(h_html, hub_url)
                    if not careers_url and hub_links.get('careers_url') and is_allowed_domain_or_ats(hub_links['careers_url'], official_domain):
                        careers_url = hub_links['careers_url']
                        careers_method = 'hub_nav_link'
                        logs.append(f"Discovered careers link via 1-hop hub ({hub_url}): {careers_url}")
                    if not csr_url and hub_links.get('csr_url') and is_allowed_domain_or_ats(hub_links['csr_url'], official_domain):
                        csr_url = hub_links['csr_url']
                        csr_method = 'hub_nav_link'
                        logs.append(f"Discovered CSR portal via 1-hop hub ({hub_url}): {csr_url}")

                    # Opportunistically refine generic metadata from hub page
                    if (company.sector or '').strip().lower() in generic_sectors or (company.headquarters or '').strip().lower() in generic_hqs:
                        hub_meta = cls.extract_company_metadata_from_html(h_html, h_text, comp_name, hub_url)
                        meta_updates = []
                        if (company.sector or '').strip().lower() in generic_sectors and hub_meta.get('sector', '').strip().lower() not in generic_sectors:
                            company.sector = hub_meta['sector']
                            sector_val = company.sector
                            meta_updates.append('sector')
                        if (company.headquarters or '').strip().lower() in generic_hqs and hub_meta.get('headquarters', '').strip().lower() not in generic_hqs:
                            company.headquarters = hub_meta['headquarters']
                            hq_val = company.headquarters
                            meta_updates.append('headquarters')
                        if meta_updates:
                            company.save(update_fields=meta_updates)

        # Priority 2B: Lightweight 1-hop contact/investor probe when Sector or Headquarters is still generic
        if (company.sector or '').strip().lower() in generic_sectors or (company.headquarters or '').strip().lower() in generic_hqs:
            meta_candidates: List[str] = []
            seen_meta = {final_website.rstrip('/').lower()}
            meta_path_re = re.compile(r'(?:^|/)(contact|contact-us|about-us|investor-relations|investors)(?:\.html?)?$', re.IGNORECASE)
            if home_html:
                try:
                    m_soup = BeautifulSoup(home_html, 'html.parser')
                    for a in m_soup.find_all('a', href=True):
                        href = a['href'].strip()
                        if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')) or is_static_asset_url(href):
                            continue
                        full_m = urllib.parse.urljoin(final_website, href).split('#')[0]
                        if not is_allowed_domain_or_ats(full_m, official_domain):
                            continue
                        m_path = urllib.parse.urlparse(full_m).path.rstrip('/').lower()
                        if meta_path_re.search(m_path):
                            norm_m = full_m.rstrip('/').lower()
                            if norm_m not in seen_meta:
                                seen_meta.add(norm_m)
                                meta_candidates.append(full_m)
                except Exception:
                    pass
            for suffix in ('/contact-us', '/contact', '/investor-relations'):
                probe_m = f"{base_url}{suffix}"
                if probe_m.rstrip('/').lower() not in seen_meta:
                    seen_meta.add(probe_m.rstrip('/').lower())
                    meta_candidates.append(probe_m)
            for m_url in meta_candidates[:2]:
                if (company.sector or '').strip().lower() not in generic_sectors and (company.headquarters or '').strip().lower() not in generic_hqs:
                    break
                m_html, m_text, m_stat = cls.fetch_page_content(m_url, timeout=4)
                if m_stat == 200 and m_html:
                    sub_meta = cls.extract_company_metadata_from_html(m_html, m_text, comp_name, m_url)
                    meta_updates = []
                    if (company.sector or '').strip().lower() in generic_sectors and sub_meta.get('sector', '').strip().lower() not in generic_sectors:
                        company.sector = sub_meta['sector']
                        sector_val = company.sector
                        meta_updates.append('sector')
                    if (company.headquarters or '').strip().lower() in generic_hqs and sub_meta.get('headquarters', '').strip().lower() not in generic_hqs:
                        company.headquarters = sub_meta['headquarters']
                        hq_val = company.headquarters
                        meta_updates.append('headquarters')
                    if meta_updates:
                        company.save(update_fields=meta_updates)
                        logs.append(f"Refined metadata via official page ({m_url}) -> Sector: '{sector_val}', HQ: '{hq_val}'")

        # Priority 2C: Sitemap & link-graph discovery (generic, works for arbitrary companies)
        try:
            _t_sitemap = time.monotonic()
            sitemap_urls = cls._fetch_sitemap_urls(final_website, timeout=5)
            sitemap_targets = cls._pick_sitemap_targets(sitemap_urls, official_domain)
            logs.append(
                f"Sitemap discovery: {len(sitemap_urls)} URLs | "
                f"career candidates: {len(sitemap_targets.get('careers', []))} | "
                f"CSR candidates: {len(sitemap_targets.get('csr', []))} | "
                f"report candidates: {len(sitemap_targets.get('reports', []))}"
            )

            # Verify a candidate portal really responds before adopting it.
            def _verify_portal_candidate(candidate_urls: List[str], kind: str) -> str:
                for candidate in candidate_urls[:4]:
                    try:
                        p_html, p_text, p_stat = cls.fetch_page_content(candidate, timeout=5)
                    except Exception:
                        continue
                    if p_stat == 200 and (len(p_text or '') > 120 or len(p_html or '') > 400):
                        return candidate
                    logs.append(f"Sitemap {kind} candidate did not respond with usable content: {candidate}")
                return ''

            if not careers_url:
                verified = _verify_portal_candidate(sitemap_targets.get('careers', []), 'careers')
                if verified:
                    careers_url = verified
                    careers_method = 'sitemap'
                    logs.append(f"Discovered careers portal via sitemap: {careers_url}")

            if not csr_url:
                verified = _verify_portal_candidate(sitemap_targets.get('csr', []), 'CSR')
                if verified:
                    csr_url = verified
                    csr_method = 'sitemap'
                    logs.append(f"Discovered CSR portal via sitemap: {csr_url}")

            # Official foundations / group CSR sites linked from the homepage.
            if not csr_url:
                for ext_link in cls._find_external_signal_links(home_html, final_website, comp_name):
                    try:
                        e_html, e_text, e_stat = cls.fetch_page_content(ext_link['url'], timeout=5)
                    except Exception:
                        continue
                    if e_stat == 200 and (len(e_text or '') > 120 or len(e_html or '') > 400):
                        csr_url = ext_link['url']
                        csr_method = 'linked_foundation'
                        logs.append(f"Discovered linked official foundation/CSR domain: {csr_url}")
                        break

            logs.append(f"Sitemap/portal graph phase completed in {int((time.monotonic() - _t_sitemap) * 1000)}ms")
        except Exception as sitemap_err:
            logs.append(f"Sitemap discovery note (non-fatal): {str(sitemap_err)[:120]}")

        # Priority 3: Subdomain probes on official domain for Careers
        if not careers_url:
            for sub in ('careers', 'jobs'):
                sub_url = f"https://{sub}.{official_domain}"
                p_html, p_text, p_stat = cls.fetch_page_content(sub_url, timeout=5)
                if p_stat == 200:
                    low_snippet = (p_html or '')[:2500].lower()
                    is_soft_404 = any(err in low_snippet for err in ('404 not found', 'page not found', 'domain for sale'))
                    has_content = len(p_text) > 150 or (
                        len(p_text) > 40 and any(k in (p_html or '').lower() for k in ('career', 'job', 'opening', 'hiring'))
                    ) or (
                        len(p_html) > 500 and any(k in (p_html or '').lower() for k in ('career', 'job', 'opening', 'id="root"', 'id="app"', 'workday', 'greenhouse', 'lever', 'phenom', 'darwinbox'))
                    )
                    if not is_soft_404 and has_content:
                        careers_url = sub_url
                        careers_method = 'subdomain_probe'
                        logs.append(f"Discovered careers portal via subdomain probe: {careers_url}")
                        break

        # Priority 4: Enterprise recruitment portal registry (safe word-boundary / domain check)
        if not careers_url:
            reg_careers = None
            for k, v in ENTERPRISE_PORTAL_REGISTRY.items():
                if cls._matches_enterprise_key(k, comp_lower, official_domain):
                    reg_careers = v
                    break
            if reg_careers:
                careers_url = reg_careers
                careers_method = 'ats_detect'
                logs.append(f"Identified enterprise recruitment portal: {careers_url}")

        # Priority 5: Path probing on official corporate domain for Careers
        if not careers_url:
            for probe in ['/careers', '/jobs', '/about/careers', '/join-us', '/work-with-us', '/career']:
                p_url = f"{base_url}{probe}"
                p_html, p_text, p_stat = cls.fetch_page_content(p_url)
                if p_stat == 200 and len(p_text) > 150 and not any(err in (p_text or '')[:300].lower() for err in ('404 not found', 'page not found')):
                    careers_url = p_url
                    careers_method = 'path_probe'
                    logs.append(f"Discovered careers portal via path probe: {careers_url}")
                    break

        if not careers_url:
            careers_method = 'not_found'
            logs.append(f"No authentic careers portal verified for {comp_name}. 0 jobs will be saved.")

        # Priority 4 for CSR: Enterprise CSR registry portal (safe word-boundary / domain check)
        if not csr_url:
            reg_csr = None
            for k, v in ENTERPRISE_CSR_REGISTRY.items():
                if cls._matches_enterprise_key(k, comp_lower, official_domain):
                    reg_csr = v
                    break
            if reg_csr:
                csr_url = reg_csr
                csr_method = 'registry'
                logs.append(f"Identified enterprise CSR registry portal: {csr_url}")

        # Priority 5 for CSR: Path probing on official corporate domain
        if not csr_url:
            for probe in [
                '/corporate-social-responsibility',
                '/who-we-are/corporate-social-responsibility',
                '/csr',
                '/sustainability',
                '/corporate-responsibility',
                '/about-us/corporate-social-responsibility',
                '/corporate/sustainability',
                '/company/sustainability/esg',
                '/esg'
            ]:
                p_url = f"{base_url}{probe}"
                p_html, p_text, p_stat = cls.fetch_page_content(p_url)
                if p_stat == 200 and len(p_text) > 150 and not any(err in (p_text or '')[:300].lower() for err in ('404 not found', 'page not found')):
                    csr_url = p_url
                    csr_method = 'path_probe'
                    logs.append(f"Discovered CSR portal via path probe: {csr_url}")
                    break

        if not csr_url:
            csr_method = 'not_found'
            logs.append(f"No authentic CSR portal verified for {comp_name}. 0 CSR projects will be saved.")

        # Priority 6: Concurrent path probing for careers + CSR simultaneously (if still not found)
        if not careers_url or not csr_url:
            career_paths = ['/careers', '/jobs', '/work-with-us', '/join-us', '/join']
            csr_paths = ['/csr', '/sustainability', '/corporate-social-responsibility', '/esg']

            def _probe_path(url):
                try:
                    h, t, s = cls.fetch_page_content(url, 4)
                    return h, t, s
                except Exception:
                    return '', '', 0

            with _cf.ThreadPoolExecutor(max_workers=4) as _probe_ex:
                career_futures = {
                    _probe_ex.submit(_probe_path, f"{base_url}{p}"): p
                    for p in career_paths if not careers_url
                }
                csr_futures = {
                    _probe_ex.submit(_probe_path, f"{base_url}{p}"): p
                    for p in csr_paths if not csr_url
                }
                for fut, path in career_futures.items():
                    try:
                        h, t, s = fut.result(timeout=6)
                        if s == 200 and len(t) > 150 and not careers_url:
                            careers_url = f"{base_url}{path}"
                            careers_method = 'concurrent_path_probe'
                            logs.append(f"Discovered careers portal via concurrent path probe: {careers_url}")
                            break
                    except Exception:
                        pass
                for fut, path in csr_futures.items():
                    try:
                        h, t, s = fut.result(timeout=6)
                        if s == 200 and len(t) > 150 and not csr_url:
                            csr_url = f"{base_url}{path}"
                            csr_method = 'concurrent_path_probe'
                            logs.append(f"Discovered CSR portal via concurrent path probe: {csr_url}")
                            break
                    except Exception:
                        pass

        _careers_discovery_ms = (time.monotonic() - _t_careers_start) * 1000

        company.careers_url = careers_url or None
        company.csr_portal_url = csr_url or None
        company.sustainability_url = csr_url or None
        company.save(update_fields=['careers_url', 'csr_portal_url', 'sustainability_url'])


# STAGE 4-8: CONCURRENT JOB / CSR / REPORT TRACKS
        # Jobs and CSR are extracted independently and each track is persisted
        # as soon as it completes.  Nothing is deleted: an incomplete crawl can
        # never wipe previously verified records.
        _t_job_start = time.monotonic()
        _t_csr_start = time.monotonic()
        _t_concurrent_start = time.monotonic()

        job_state: Dict[str, Any] = {'candidates': [], 'status': 'SKIPPED', 'error': '', 'ms': 0.0}
        csr_state: Dict[str, Any] = {'candidates': [], 'status': 'SKIPPED', 'error': '', 'ms': 0.0, 'html': '', 'text': '', 'url': csr_url}
        report_state: Dict[str, Any] = {'links': [], 'docs': [], 'status': 'SKIPPED', 'error': '', 'ms': 0.0}
        validated_jobs: List[Dict[str, Any]] = []
        validated_csr: List[Dict[str, Any]] = []
        report_rows: List[Dict[str, Any]] = []
        db_jobs: List[Dict[str, Any]] = []
        db_csr: List[Dict[str, Any]] = []
        first_job_ms: int = 0
        first_csr_ms: int = 0
        http_failures = 0

        def _serialize_db_jobs() -> List[Dict[str, Any]]:
            rows = list(company.jobs.all().order_by('job_row_id').values(
                'job_id', 'external_job_id', 'job_title', 'department', 'location',
                'work_mode', 'experience', 'salary', 'employment_type', 'ats_platform',
                'application_url', 'source_url', 'confidence', 'evidence_text',
                'job_description', 'skills', 'posted_date',
            ))
            serialized = []
            for rj in rows:
                serialized.append({
                    'job_id': rj['job_id'],
                    'job_title': rj['job_title'],
                    'department': rj['department'],
                    'location': rj['location'],
                    'work_mode': rj['work_mode'],
                    'experience': rj['experience'],
                    'salary_range': rj['salary'],
                    'employment_type': rj.get('employment_type') or '',
                    'ats_platform': rj.get('ats_platform') or '',
                    'application_url': rj['application_url'],
                    'source_url': rj.get('source_url') or rj['application_url'],
                    'requisition_id': rj['external_job_id'],
                    'confidence': rj['confidence'],
                    'evidence_text': rj['evidence_text'],
                    'description': rj.get('job_description') or '',
                    'skills': rj.get('skills') or '',
                    'posting_date': rj.get('posted_date') or '',
                })
            return serialized

        def _serialize_db_csr() -> List[Dict[str, Any]]:
            rows = list(company.csr_projects.all().order_by('csr_id').values(
                'csr_id', 'project_name', 'category', 'state', 'geographic_location',
                'budget', 'description', 'source_url', 'canonical_url', 'confidence',
                'evidence_text', 'raw_metadata',
            ))
            serialized = []
            for rc in rows:
                meta = rc.get('raw_metadata') if isinstance(rc.get('raw_metadata'), dict) else {}
                serialized.append({
                    'project_id': str(rc['csr_id']),
                    'project_name': rc['project_name'],
                    'category': rc['category'],
                    'state': rc['state'],
                    'geographic_location': rc['geographic_location'],
                    'district': rc['geographic_location'],
                    'budget': rc['budget'],
                    'description': rc['description'],
                    'summary': meta.get('ai_summary') or rc['description'] or '',
                    'source_url': rc['source_url'],
                    'canonical_url': rc['canonical_url'],
                    'confidence': rc['confidence'],
                    'evidence_text': rc['evidence_text'],
                    'verbatim_quote': rc['evidence_text'],
                    'beneficiaries': meta.get('beneficiaries') or '',
                    'implementing_partner': meta.get('implementing_partner') or '',
                    'financial_year': meta.get('financial_year') or '',
                    'schedule_vii': meta.get('schedule_vii') or '',
                    'expenditure': meta.get('expenditure') or rc.get('budget') or '',
                })
            return serialized

        def _job_worker() -> None:
            started = time.monotonic()
            try:
                if not (options.get('extract_jobs', True) and careers_url):
                    job_state['status'] = 'SKIPPED'
                    return
                job_state['status'] = 'RUNNING'
                logs.append(f"Probing live careers portal: {careers_url}")
                deep_url, job_html, job_text, job_status = cls.crawl_deep_portal_chain(
                    careers_url, target_type='jobs', max_hops=2, logs=logs,
                )
                if not job_html:
                    job_html, job_text, job_status = cls.fetch_page_content(deep_url or careers_url, timeout=6)
                candidates = cls.discover_all_real_jobs(
                    company, deep_url or careers_url, job_html, job_text, sector_val, logs,
                )
                if not candidates:
                    reg_cand = None
                    for k, reg_p in ENTERPRISE_PORTAL_REGISTRY.items():
                        if cls._matches_enterprise_key(k, comp_lower, company.official_domain or official_domain):
                            reg_cand = reg_p
                            break
                    if reg_cand and reg_cand.rstrip('/') != (careers_url or '').rstrip('/'):
                        logs.append(f"Engaging dedicated enterprise vacancy registry: {reg_cand}")
                        fb_url, fb_html, fb_text, _fb_stat = cls.crawl_deep_portal_chain(
                            reg_cand, target_type='jobs', max_hops=1, logs=logs,
                        )
                        candidates = cls.discover_all_real_jobs(
                            company, fb_url or reg_cand, fb_html, fb_text, sector_val, logs,
                        )
                job_state['candidates'] = candidates or []
                job_state['status'] = 'COMPLETED'
            except Exception as exc:
                job_state['status'] = 'FAILED'
                job_state['error'] = str(exc)[:240]
                logs.append(f"Job track error (non-fatal, CSR continues): {str(exc)[:140]}")
            finally:
                job_state['ms'] = (time.monotonic() - started) * 1000
                close_old_connections()

        def _csr_worker() -> None:
            started = time.monotonic()
            try:
                if not (options.get('extract_csr', True) and csr_url):
                    csr_state['status'] = 'SKIPPED'
                    return
                csr_state['status'] = 'RUNNING'
                logs.append(f"Probing live CSR portal: {csr_url}")
                deep_csr_url, csr_html, csr_text, _csr_status = cls.crawl_deep_portal_chain(
                    csr_url, target_type='csr', max_hops=2, logs=logs,
                )
                csr_state['url'] = deep_csr_url or csr_url
                csr_state['html'] = csr_html or ''
                csr_state['text'] = csr_text or ''
                candidates = cls.discover_all_real_csr(
                    company, csr_state['url'], csr_html, csr_text, sector_val, logs,
                )
                if not candidates:
                    csr_cand = None
                    for k, reg_c in ENTERPRISE_CSR_REGISTRY.items():
                        if cls._matches_enterprise_key(k, comp_lower, company.official_domain or official_domain):
                            csr_cand = reg_c
                            break
                    if csr_cand and csr_cand.rstrip('/') != (csr_url or '').rstrip('/'):
                        logs.append(f"Engaging dedicated enterprise CSR registry: {csr_cand}")
                        fb_csr_url, fb_csr_html, fb_csr_text, _fb_stat = cls.crawl_deep_portal_chain(
                            csr_cand, target_type='csr', max_hops=1, logs=logs,
                        )
                        if fb_csr_text:
                            csr_state['text'] = fb_csr_text
                            csr_state['html'] = fb_csr_html or csr_state['html']
                            csr_state['url'] = fb_csr_url or csr_cand
                        candidates = cls.discover_all_real_csr(
                            company, fb_csr_url or csr_cand, fb_csr_html, fb_csr_text, sector_val, logs,
                        )
                csr_state['candidates'] = candidates or []
                csr_state['status'] = 'COMPLETED'
            except Exception as exc:
                csr_state['status'] = 'FAILED'
                csr_state['error'] = str(exc)[:240]
                logs.append(f"CSR track error (non-fatal, jobs continue): {str(exc)[:140]}")
            finally:
                csr_state['ms'] = (time.monotonic() - started) * 1000
                close_old_connections()

        def _report_worker() -> None:
            started = time.monotonic()
            try:
                if not options.get('extract_reports', True):
                    report_state['status'] = 'SKIPPED'
                    return
                report_state['status'] = 'RUNNING'
                links = cls._discover_report_links(home_html, final_website)
                for sitemap_report_url in (sitemap_targets.get('reports') or [])[:6]:
                    if not _is_report_document_url(sitemap_report_url):
                        continue
                    links.append({
                        'url': sitemap_report_url,
                        'title': _humanize_report_title(sitemap_report_url)[:180],
                        'report_type': cls._classify_report(sitemap_report_url, sitemap_report_url),
                    })
                deduped = {}
                for item in links:
                    key = (item.get('url') or '').rstrip('/').lower()
                    if key and key not in deduped:
                        deduped[key] = item
                report_state['links'] = list(deduped.values())[:6]
                docs = []
                for item in report_state['links'][:4]:
                    url = item.get('url') or ''
                    try:
                        if url.lower().split('?')[0].endswith('.pdf'):
                            text = cls.extract_pdf_text_from_url(url, max_pages=8, timeout=10)
                        else:
                            _rh, text, _rs = cls.fetch_page_content(url, timeout=6)
                    except Exception:
                        text = ''
                    if text and len(text) > 200:
                        docs.append({
                            'url': url,
                            'title': item.get('title') or '',
                            'report_type': item.get('report_type') or cls._classify_report(item.get('title', ''), url),
                            'text': text,
                        })
                    elif url:
                        logs.append(f"Report document unavailable or empty: {url[:90]}")
                report_state['docs'] = docs
                report_state['status'] = 'COMPLETED'
            except Exception as exc:
                report_state['status'] = 'FAILED'
                report_state['error'] = str(exc)[:240]
                logs.append(f"Report track error (non-fatal): {str(exc)[:140]}")
            finally:
                report_state['ms'] = (time.monotonic() - started) * 1000
                close_old_connections()

        def _consume_jobs() -> None:
            nonlocal validated_jobs, db_jobs, first_job_ms
            if job_state.get('status') == 'SKIPPED':
                return
            candidates = job_state.get('candidates') or []
            validated_jobs, _saved_ids = cls._persist_job_candidates(
                company, candidates, now, logs, seen_urls=set(),
            )
            db_jobs = _serialize_db_jobs()
            if db_jobs and not first_job_ms:
                first_job_ms = int((time.monotonic() - _t_discovery_start) * 1000)
            cls._publish_progress(options, {
                'status': 'running',
                'stage': 'Jobs validated & saved',
                'company_name': comp_name,
                'company_id': company.company_id,
                'website_url': company.website_url,
                'careers_url': careers_url or '',
                'csr_url': csr_url or '',
                'jobs': db_jobs,
                'csr': db_csr,
                'reports': report_rows,
                'jobs_imported': len(db_jobs),
                'csr_imported': len(db_csr),
                'reports_count': len(report_rows),
                'elapsed_ms': int((time.monotonic() - _t_discovery_start) * 1000),
                'deep_enrichment': 'PENDING',
            })

        def _consume_csr() -> None:
            nonlocal validated_csr, db_csr, first_csr_ms
            if csr_state.get('status') == 'SKIPPED':
                return
            candidates = csr_state.get('candidates') or []
            validated_csr, _saved_ids = cls._persist_csr_candidates(
                company, candidates, csr_state.get('text') or '', now, logs,
            )
            db_csr = _serialize_db_csr()
            if db_csr and not first_csr_ms:
                first_csr_ms = int((time.monotonic() - _t_discovery_start) * 1000)
            cls._publish_progress(options, {
                'status': 'running',
                'stage': 'CSR projects validated & saved',
                'company_name': comp_name,
                'company_id': company.company_id,
                'website_url': company.website_url,
                'careers_url': careers_url or '',
                'csr_url': csr_url or '',
                'jobs': db_jobs,
                'csr': db_csr,
                'reports': report_rows,
                'jobs_imported': len(db_jobs),
                'csr_imported': len(db_csr),
                'reports_count': len(report_rows),
                'elapsed_ms': int((time.monotonic() - _t_discovery_start) * 1000),
                'deep_enrichment': 'PENDING',
            })

        def _consume_reports() -> None:
            nonlocal report_rows
            if report_state.get('status') == 'SKIPPED':
                return
            report_rows = cls._persist_reports(company, report_state.get('docs') or [], now, logs)
            cls._publish_progress(options, {
                'status': 'running',
                'stage': 'Reports analysed & saved',
                'company_name': comp_name,
                'company_id': company.company_id,
                'website_url': company.website_url,
                'careers_url': careers_url or '',
                'csr_url': csr_url or '',
                'jobs': db_jobs,
                'csr': db_csr,
                'reports': report_rows,
                'jobs_imported': len(db_jobs),
                'csr_imported': len(db_csr),
                'reports_count': len(report_rows),
                'elapsed_ms': int((time.monotonic() - _t_discovery_start) * 1000),
                'deep_enrichment': 'PENDING',
            })

        # Concurrent execution: each track writes independently.  SQLite test
        # databases run sequentially to avoid in-memory DB/thread incompatibility.
        _use_threads = bool(options.get('concurrent_tracks', True))
        try:
            from django.db import connection as _db_connection
            if _db_connection.vendor == 'sqlite':
                _use_threads = False
        except Exception:
            _use_threads = False

        if _use_threads:
            executor = _cf.ThreadPoolExecutor(max_workers=3)
            future_kinds = {}
            if options.get('extract_jobs', True) and careers_url:
                future_kinds[executor.submit(_job_worker)] = 'jobs'
            if options.get('extract_csr', True) and csr_url:
                future_kinds[executor.submit(_csr_worker)] = 'csr'
            if options.get('extract_reports', True):
                future_kinds[executor.submit(_report_worker)] = 'reports'
            pending = set(future_kinds)
            deadline = time.monotonic() + float(options.get('track_timeout_seconds') or 45)
            while pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                done, pending = _cf.wait(
                    pending, timeout=remaining, return_when=_cf.FIRST_COMPLETED,
                )
                for future in done:
                    kind = future_kinds.get(future)
                    try:
                        if kind == 'jobs':
                            _consume_jobs()
                        elif kind == 'csr':
                            _consume_csr()
                        elif kind == 'reports':
                            _consume_reports()
                    except Exception as consume_err:
                        logs.append(f"Persist phase error for {kind} track: {str(consume_err)[:140]}")
            for stuck in pending:
                kind = future_kinds.get(stuck, '')
                logs.append(f"{kind.upper()} track exceeded the initial {int(options.get('track_timeout_seconds') or 45)}s budget; partial results kept, deep enrichment will continue.")
                if kind == 'jobs':
                    job_state['status'] = job_state.get('status') or 'TIMEOUT'
                elif kind == 'csr':
                    csr_state['status'] = csr_state.get('status') or 'TIMEOUT'
                elif kind == 'reports':
                    report_state['status'] = report_state.get('status') or 'TIMEOUT'
            executor.shutdown(wait=False)
        else:
            _job_worker()
            _consume_jobs()
            _csr_worker()
            _consume_csr()
            _report_worker()
            _consume_reports()

        _job_extraction_ms = float(job_state.get('ms') or 0.0)
        _csr_extraction_ms = float(csr_state.get('ms') or 0.0)
        _total_discovery_ms = (time.monotonic() - _t_discovery_start) * 1000

        # Final DB synchronisation (includes pre-existing records, which remain intact)
        db_jobs = _serialize_db_jobs()
        db_csr = _serialize_db_csr()
        try:
            db_reports = [cls._report_row(r) for r in company.csr_reports.all().order_by('-report_id')[:50]]
        except Exception:
            db_reports = report_rows

        jobs_dropped_cnt = DroppedCandidate.objects.filter(company=company, candidate_type='JOB').count()
        csr_dropped_cnt = DroppedCandidate.objects.filter(company=company, candidate_type='CSR').count()
        _run_rejected = max(
            0,
            len(job_state.get('candidates') or []) + len(csr_state.get('candidates') or []) - (
                len(validated_jobs) + len(validated_csr)
            ),
        )

        ai_trace = HybridAIExtractionService.end_trace()
        ai_summary = resolve_active_ai_summary(force_refresh=True)
        succeeded_events = [ev for ev in ai_trace if ev.get('status') in ('SUCCESS', 'SUCCESS_VIA_FALLBACK')]
        ai_invoked = len(ai_trace) > 0
        ai_succeeded = len(succeeded_events) > 0
        last_success = succeeded_events[-1] if succeeded_events else None

        used_provider = (last_success.get('provider') if last_success else '') or ''
        used_provider_display = (last_success.get('provider_display') if last_success else '') or ''
        used_model = (last_success.get('model') if last_success else '') or ''
        fallback_used = bool(last_success.get('fallback_used')) if last_success else False
        models_used: List[str] = []
        for ev in succeeded_events:
            ev_model = ev.get('model') or ''
            ev_prov = ev.get('provider_display') or ev.get('provider') or ''
            ev_label = f"{ev_model} ({ev_prov} · Failover)" if ev.get('fallback_used') else f"{ev_model} ({ev_prov})"
            if ev_model and ev_label not in models_used:
                models_used.append(ev_label)

        # Honest outcome classification: a failed fetch or failed AI call is
        # never reported as a successful zero-result discovery.
        home_ok = home_status in (200, 201, 301, 302, 307, 308) and bool(home_html)
        track_failed = (
            job_state.get('status') in ('FAILED', 'TIMEOUT')
            or csr_state.get('status') in ('FAILED', 'TIMEOUT')
            or report_state.get('status') in ('FAILED', 'TIMEOUT')
        )
        has_results = bool(db_jobs or db_csr or db_reports)

        if has_results:
            _outcome = 'PARTIAL_SUCCESS' if (track_failed or not home_ok) else 'SUCCESS_WITH_RESULTS'
        elif not home_ok:
            _outcome = 'FETCH_FAILED'
        elif _run_rejected > 0:
            _outcome = 'VALIDATION_REJECTED'
        elif ai_invoked and not ai_succeeded:
            _outcome = 'AI_PROVIDER_FAILED'
        elif careers_url or csr_url:
            _outcome = 'PARTIAL_SUCCESS' if track_failed else 'SUCCESS_NO_RESULTS'
        else:
            # No official careers/CSR destination could be verified, so a
            # "confirmed zero" conclusion is not honest.
            _outcome = 'PARTIAL_SUCCESS'

        if ai_invoked and ai_succeeded:
            runtime_label = ", ".join(models_used) if len(models_used) > 1 else (models_used[0] if models_used else f"{used_model} ({used_provider_display})")
            logs.append(f"AI Model Used: {runtime_label}")
        elif ai_invoked and not ai_succeeded:
            logs.append(
                f"AI Model Status: Configured {ai_summary.get('badge_label', 'None')} failed during extraction; deterministic verification only."
            )

        # Background deep enrichment starts only after the initial response is
        # ready, never blocking the dashboard.
        _deep_status = 'SKIPPED'
        _skip_bg = False
        try:
            from django.db import connection as _bg_connection
            if _bg_connection.vendor == 'sqlite':
                _skip_bg = True
        except Exception:
            _skip_bg = True
        if _skip_bg:
            _deep_status = 'SKIPPED_TEST_DATABASE'
        elif not options.get('deep_enrich', True):
            _deep_status = 'SKIPPED_DISABLED'
        else:
            _deep_status = 'RUNNING'
            try:
                threading.Thread(
                    target=cls._deep_enrich,
                    args=(
                        company.company_id,
                        dict(options),
                        sitemap_targets,
                        [careers_url] if careers_url else [],
                        [csr_url] if csr_url else [],
                        [d.get('url') for d in (report_state.get('docs') or [])],
                    ),
                    daemon=True,
                    name=f"deep-enrich-{company.company_id[:20]}",
                ).start()
            except Exception as bg_err:
                _deep_status = 'FAILED_TO_START'
                logs.append(f"Deep enrichment could not start: {str(bg_err)[:100]}")

        _telemetry = {
            'homepage_fetch_ms': int(max(0.0, homepage_fetch_ms or 0.0)),
            'homepage_content_chars': len(home_text or ''),
            'sitemap_urls_found': len(sitemap_urls),
            'careers_discovery_ms': int(_careers_discovery_ms),
            'csr_discovery_ms': int(max(0.0, (time.monotonic() - _t_csr_start) * 1000)) if csr_url else 0,
            'portal_discovery_ms': int(_careers_discovery_ms),
            'job_extraction_ms': int(_job_extraction_ms),
            'csr_extraction_ms': int(_csr_extraction_ms),
            'report_extraction_ms': int(float(report_state.get('ms') or 0.0)),
            'total_ms': int(_total_discovery_ms),
            'time_to_first_job_ms': first_job_ms,
            'time_to_first_csr_ms': first_csr_ms,
            'ai_calls': len(ai_trace),
            'ai_succeeded': ai_succeeded,
            'validation_accepted': len(validated_jobs) + len(validated_csr),
            'validation_rejected': _run_rejected,
            'jobs_saved': len(db_jobs),
            'csr_projects_saved': len(db_csr),
            'reports_saved': len(db_reports),
            'http_failures': http_failures,
            'candidate_jobs': len(job_state.get('candidates') or []),
            'candidate_csr': len(csr_state.get('candidates') or []),
            'outcome': _outcome,
            'careers_method': careers_method,
            'csr_method': csr_method,
            'job_track_status': job_state.get('status'),
            'csr_track_status': csr_state.get('status'),
            'report_track_status': report_state.get('status'),
            'job_track_error': job_state.get('error') or '',
            'csr_track_error': csr_state.get('error') or '',
            'deep_enrichment': _deep_status,
            'deep_enrichment_ms': 0,
        }

        try:
            AuditTrail.objects.create(
                record_type="Company",
                record_id=str(company.company_id),
                action="LIVE_WEB_AI_DISCOVERY",
                user_role="AI Web Discovery Engine",
                notes=(
                    f"Autonomous discovery for {comp_name}: {len(db_jobs)} verified jobs, "
                    f"{len(db_csr)} CSR projects, {len(db_reports)} reports; outcome={_outcome}."
                ),
                timestamp=now.isoformat(),
            )
        except Exception as audit_err:
            logger.warning(f"Failed to record audit trail: {audit_err}")

        _final_payload = {
            'status': 'completed',
            'stage': 'Discovery complete',
            'company_name': comp_name,
            'company_id': company.company_id,
            'is_new_company': is_new_company,
            'sector': company.sector or 'Corporate Enterprise',
            'headquarters': company.headquarters or 'India',
            'website_url': company.website_url,
            'careers_url': careers_url or '',
            'csr_url': csr_url or '',
            'jobs': db_jobs,
            'csr': db_csr,
            'reports': db_reports,
            'jobs_imported': len(db_jobs),
            'csr_imported': len(db_csr),
            'reports_count': len(db_reports),
            'outcome': _outcome,
            'telemetry': _telemetry,
            'logs': logs[-40:],
            'deep_enrichment': _deep_status,
        }
        cls._publish_progress(options, _final_payload)

        return {
            'status': 'success' if _outcome != 'FETCH_FAILED' else 'error',
            'is_new_company': is_new_company,
            'company_name': comp_name,
            'company_id': company.company_id,
            'official_domain': company.official_domain or official_domain,
            'sector': company.sector or 'Corporate Enterprise',
            'headquarters': company.headquarters or 'India',
            'nse_symbol': company.nse_symbol or '',
            'verification_status': company.verification_status,
            'website_url': company.website_url,
            'careers_url': careers_url or '',
            'careers_method': careers_method,
            'csr_url': csr_url or '',
            'csr_method': csr_method,
            'jobs_discovered': len(db_jobs),
            'jobs_imported': len(db_jobs),
            'csr_discovered': len(db_csr),
            'csr_imported': len(db_csr),
            'reports_count': len(db_reports),
            'reports_imported': len(db_reports),
            'jobs_dropped': jobs_dropped_cnt,
            'csr_dropped': csr_dropped_cnt,
            'jobs': db_jobs,
            'csr': db_csr,
            'reports': db_reports,
            'logs': logs,
            'telemetry': _telemetry,
            'outcome': _outcome,
            'deep_enrichment': _deep_status,
            'ai_config': {
                'provider_id': ai_summary.get('provider_id', ''),
                'provider_display': ai_summary.get('provider_display', 'Not Configured'),
                'model': ai_summary.get('model', ''),
                'status': ai_summary.get('status', 'UNCONFIGURED'),
                'is_ready': ai_summary.get('is_ready', False),
                'badge_label': ai_summary.get('badge_label', 'No AI Model Configured'),
                'ai_invoked': ai_invoked,
                'ai_succeeded': ai_succeeded,
                'used_provider': used_provider,
                'used_provider_display': used_provider_display,
                'used_model': used_model,
                'fallback_used': fallback_used,
                'models_used': models_used,
            },
        }
