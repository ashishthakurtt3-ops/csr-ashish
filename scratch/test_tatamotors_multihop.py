import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
import re
import urllib.parse
from bs4 import BeautifulSoup
from modules.crawler_engine.discovery_helpers import is_static_asset_url, is_valid_job_title
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService

ATS_DOMAINS_AND_KEYWORDS = [
    'turbohire', 'careerpage', 'myworkdayjobs', 'successfactors', 'taleo', 'icims',
    'lever.co', 'greenhouse.io', 'darwinbox', 'smartrecruiters', 'workable', 'oraclecloud',
    'openings', 'current-openings', 'current openings', 'vacanc', 'search-job', 'job-search',
    'explore-opportunities', 'opportunities', 'view-jobs', 'positions', 'career-opportunities',
    'open-jobs', 'viewalljobs', 'search-jobs', 'find-jobs', 'lateral-hiring', 'job-opportunities',
    'explore-roles', 'all-jobs', 'view all jobs', 'view-all', 'work-with-us', 'careers/openings',
    'dashboardv2', 'searchjobs', 'jobsearch'
]

def find_deep_openings_link_v2(raw_html: str, current_careers_url: str) -> str:
    if not raw_html:
        return ""
    curr_norm = current_careers_url.rstrip('/').lower()
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Priority 1: Direct ATS links or dashboard links
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')) or is_static_asset_url(href):
            continue
        full = urllib.parse.urljoin(current_careers_url, href)
        if full.rstrip('/').lower() == curr_norm or is_static_asset_url(full):
            continue
        if any(bad in full.lower() for bad in ['login', 'privacy', 'terms', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube']):
            continue
        h_lower = href.lower()
        if any(ats in h_lower for ats in ['turbohire', 'myworkdayjobs', 'successfactors', 'taleo', 'icims', 'lever.co', 'greenhouse.io', 'darwinbox', 'smartrecruiters', 'dashboardv2']):
            return full

    # Priority 2: General career openings keywords in href or text
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith(('#', 'javascript:', 'mailto:', 'tel:')) or is_static_asset_url(href):
            continue
        full = urllib.parse.urljoin(current_careers_url, href)
        if full.rstrip('/').lower() == curr_norm or is_static_asset_url(full):
            continue
        if any(bad in full.lower() for bad in ['login', 'privacy', 'terms', 'facebook', 'twitter', 'linkedin', 'instagram', 'youtube', 'student', 'admission']):
            continue
        combined = f"{href.lower()} {a.get_text(' ', strip=True).lower()}"
        if any(k in combined for k in ATS_DOMAINS_AND_KEYWORDS):
            return full

    return ""

# Test multi-hop from tatamotors homepage / careers
print("--- Hop 1 from https://www.tatamotors.com/careers ---")
html1, _, _ = BatchDiscoveryService.fetch_page_content("https://www.tatamotors.com/careers")
hop1 = find_deep_openings_link_v2(html1, "https://www.tatamotors.com/careers")
print("Hop 1 result:", hop1)

if hop1:
    print(f"--- Hop 2 from {hop1} ---")
    html2, _, _ = BatchDiscoveryService.fetch_page_content(hop1)
    hop2 = find_deep_openings_link_v2(html2, hop1)
    print("Hop 2 result:", hop2)

    if hop2:
        print(f"--- Hop 3 from {hop2} ---")
        html3, text3, _ = BatchDiscoveryService.fetch_rendered_page(hop2)
        hop3 = find_deep_openings_link_v2(html3, hop2)
        print("Hop 3 result (or final job page):", hop3 or hop2)
        print("Rendered text sample:", text3[:300])

