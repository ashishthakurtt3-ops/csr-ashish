import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job, Company
from django.db.models import Q

# 1. Exact phrases and tokens that are UI controls / navigation / menu headers
EXACT_NAV_DEFECTS = {
    'home', 'home page', 'about us', 'about', 'who we are', 'our story', 'our history', 'our values', 'values',
    'our brands', 'leadership', 'leadership team', 'management team', 'board of directors',
    'press kit', 'press releases', 'stories', 'case studies', 'newsroom', 'news', 'useful information',
    'trending', 'corporate governance', 'governance', 'investors centre', 'investors', 'investor relations',
    'shareholders', 'financials', 'community development', 'environment', 'sustainability', 'overview',
    'company overview', 'for corporate', 'for infrastructure', 'for home builders', 'consumer products',
    'products', 'view details', 'know more', 'learn more', 'click here', 'apply now', 'apply online',
    'how to apply', 'upload resume', 'submit resume', 'search jobs', 'view all', 'view all roles',
    'view all openings', 'all jobs', 'explore jobs', 'find jobs', 'explore opportunities', 'careers',
    'frequently asked questions', 'faqs', 'faqs & support', 'customer service', 'customer education',
    'download forms', 'view our ads', 'website feedback', 'partnership', 'saved jobs',
    'can’t find what you are looking for?', "can't find what you are looking for?", 'asset publisher',
    'fraud alert', 'fraud alert - global', 'equal opportunity policy', 'fraud awareness',
    'contact us', 'contact', 'sitemap', 'privacy policy', 'privacy notice', 'terms of use',
    'terms & conditions', 'cookie policy', 'cookie settings', 'cookie consent', 'disclaimer',
    'next', 'previous', 'first', 'last', 'next >>', 'previous <<', 'next >', '< previous',
    'culture', 'our culture', 'life at ultratech', 'jobs at ultratech', 'leadership team',
    'disclaimer', 'branch locator', 'calculator', 'media centre', 'media', 'loss of share certificates',
    'odr portal', 'review accommodations for disability', 'workplace equity & diversity',
    'opera mobile preview', 'education', 'healthcare', 'insurance', 'technology', 'ecommerce',
    'user experience', 'recruitingce', 'articles of association', 'saksham niveshak', '3 wheelers',
    'motorcycles', 'global business', 'destinations', 'locations'
}

# Substring patterns that indicate boilerplate or non-job content
SUBSTRING_DEFECTS = [
    'fraud alert', 'brand ambassador', 'championships', 'life at ', 'life @', 'jobs at ',
    'review accommodations', 'cookie consent', 'cookie settings', 'privacy policy',
    'terms of use', 'download app', 'video library', 'know more about', 'types of loan',
    'frequently asked questions', 'saved jobs', 'view all', 'view our ads', 'window-eyes',
    'yourdolphin.co.uk'
]

# Overseas markers
OVERSEAS_INDICATORS = [
    'montréal', 'montreal', 'québec', 'quebec', 'canada', 'rotterdam', 'netherlands',
    'usa', 'united states', 'vietnam', 'philippines', 'thailand', 'germany', 'poland',
    'singapore', 'indonesia', 'london', 'uk', 'united kingdom', 'chicago'
]

active_jobs = Job.objects.filter(status='ACTIVE')
print(f"Total current ACTIVE jobs: {active_jobs.count()}")

nav_defect_jobs = []
overseas_jobs = []

for j in active_jobs:
    t_clean = (j.job_title or '').strip().lower()
    loc_clean = (j.location or '').strip().lower()
    
    # Check overseas
    if any(m in t_clean or m in loc_clean for m in OVERSEAS_INDICATORS):
        # Exclude legitimate Indian positions that might coincidentally contain something
        if 'montr' in t_clean or 'québec' in t_clean or 'quebec' in t_clean or 'canada' in loc_clean:
            overseas_jobs.append(j)
            continue
            
    # Check exact match defects
    if t_clean in EXACT_NAV_DEFECTS:
        nav_defect_jobs.append(j)
        continue
        
    # Check substring defects
    if any(sub in t_clean for sub in SUBSTRING_DEFECTS):
        nav_defect_jobs.append(j)
        continue
        
    # Generic short one-word menu titles
    if t_clean in ['home', 'overview', 'stories', 'media', 'investors', 'environment', 'governance', 'financials']:
        nav_defect_jobs.append(j)
        continue

print(f"Identified Navigation / Boilerplate Defect Jobs: {len(nav_defect_jobs)}")
print(f"Identified Overseas / Canada Jobs: {len(overseas_jobs)}")

print("\nSample flagged navigation jobs (first 25):")
for j in nav_defect_jobs[:25]:
    print(f"  [{j.company.company_name[:25]}] '{j.job_title}' (ID: {j.job_id})")

print("\nSample flagged overseas jobs:")
for j in overseas_jobs:
    print(f"  [{j.company.company_name[:25]}] '{j.job_title}' | Loc: '{j.location}'")
