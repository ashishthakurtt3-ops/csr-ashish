import sys, os
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django; django.setup()
from modules.admin_panel.services.batch_discovery_service import BatchDiscoveryService
from bs4 import BeautifulSoup
import urllib.parse
from modules.crawler_engine.discovery_helpers import is_static_asset_url

ATS_DOMAINS_AND_KEYWORDS = [
    'turbohire', 'careerpage', 'myworkdayjobs', 'successfactors', 'taleo', 'icims',
    'lever.co', 'greenhouse.io', 'darwinbox', 'smartrecruiters', 'workable', 'oraclecloud',
    'openings', 'current-openings', 'current openings', 'vacanc', 'search-job', 'job-search',
    'explore-opportunities', 'opportunities', 'view-jobs', 'positions', 'career-opportunities',
    'open-jobs', 'viewalljobs', 'search-jobs', 'find-jobs', 'lateral-hiring', 'job-opportunities',
    'explore-roles', 'all-jobs', 'view all jobs', 'view-all', 'work-with-us', 'careers/openings',
    'dashboardv2', 'searchjobs', 'jobsearch'
]

def find_deep_openings_link_v3(raw_html: str, current_careers_url: str) -> str:
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

def crawl_deep_portal_chain(initial_url: str, target_type='jobs', max_hops=3):
    curr_url = initial_url
    visited = set()
    best_html = ""
    best_text = ""
    best_status = 0
    logs = []

    for hop in range(1, max_hops + 1):
        if curr_url in visited:
            break
        visited.add(curr_url)
        logs.append(f"Hop {hop}: Fetching {curr_url}")
        html, text, status = BatchDiscoveryService.fetch_page_content(curr_url)
        
        # If static text is sparse or indicates SPA, render with Playwright
        if not text or len(text) < 250 or any(k in html.lower() for k in ['id="root"', 'id="app"', 'ng-app', '<router-outlet>', 'turbohire', 'workday']):
            logs.append(f"  Rendering SPA with headless browser...")
            r_html, r_text, r_status = BatchDiscoveryService.fetch_rendered_page(curr_url)
            if len(r_text) > len(text):
                html, text, status = r_html, r_text, r_status
                logs.append(f"  Headless rendered: {len(r_text)} chars")

        best_html, best_text, best_status = html, text, status

        # Look for next deeper link
        if target_type == 'jobs':
            next_link = find_deep_openings_link_v3(html, curr_url)
        else:
            next_link = BatchDiscoveryService.find_deep_csr_link(html, curr_url)

        if next_link and next_link not in visited and next_link.rstrip('/').lower() != curr_url.rstrip('/').lower():
            logs.append(f"  Found deeper link -> {next_link}")
            curr_url = next_link
        else:
            logs.append(f"  Reached final deep destination: {curr_url}")
            break

    return curr_url, best_html, best_text, best_status, logs

print("=== Testing Hitachi Energy ===")
url, html, text, status, logs = crawl_deep_portal_chain("https://www.hitachienergy.com/in/en/careers")
for l in logs:
    print(l)
print(f"Final URL: {url}, text len: {len(text)}")

