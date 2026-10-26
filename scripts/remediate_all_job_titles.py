import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import transaction
from django.utils import timezone
from modules.admin_panel.models import Job, Company

def run_remediation():
    print("=" * 80)
    print("STARTING FULL RECONCILIATION OF JOB TITLES & BOILERPLATE ARTIFACTS")
    print("=" * 80)

    # 1. Exact match defect titles (case-insensitive)
    EXACT_DEFECTS = {
        'home', 'home page', 'about us', 'about', 'who we are', 'our story', 'our history', 'our values', 'values',
        'our brands', 'leadership', 'leadership team', 'management team', 'board of directors',
        'press kit', 'press releases', 'stories', 'case studies', 'newsroom', 'news', 'useful information',
        'trending', 'corporate governance', 'governance', 'investors centre', 'investors', 'investor relations',
        'investor information', 'shareholders', 'financials', 'community development', 'environment', 'sustainability',
        'sustainability services', 'overview', 'company overview', 'for corporate', 'for infrastructure',
        'for home builders', 'consumer products', 'products', 'view details', 'know more', 'learn more',
        'click here', 'apply now', 'apply online', 'how to apply', 'upload resume', 'submit resume', 'search jobs',
        'view all', 'view all roles', 'view all openings', 'all jobs', 'explore jobs', 'find jobs',
        'explore opportunities', 'careers', 'frequently asked questions', 'faqs', 'faqs & support', 'customer service',
        'customer education', 'download forms', 'view our ads', 'website feedback', 'partnership', 'saved jobs',
        'can’t find what you are looking for?', "can't find what you are looking for?", 'asset publisher',
        'fraud alert', 'fraud alert - global', 'equal opportunity policy', 'fraud awareness',
        'contact us', 'contact', 'sitemap', 'privacy policy', 'privacy notice', 'terms of use',
        'terms & conditions', 'cookie policy', 'cookie settings', 'cookie consent', 'disclaimer',
        'next', 'previous', 'first', 'last', 'next >>', 'previous <<', 'next >', '< previous',
        'culture', 'our culture', 'branch locator', 'calculator', 'media centre', 'media',
        'loss of share certificates', 'odr portal', 'review accommodations for disability',
        'workplace equity & diversity', 'opera mobile preview', 'education', 'healthcare',
        'insurance', 'technology', 'ecommerce', 'user experience', 'recruitingce',
        'articles of association', 'saksham niveshak', '3 wheelers', 'motorcycles',
        'global business', 'destinations', 'locations', 'csr', 'foundation'
    }

    # 2. Substrings that mark boilerplate/defects
    SUBSTRING_DEFECTS = [
        'fraud alert', 'brand ambassador', 'championships', 'life at ', 'life @', 'jobs at ',
        'review accommodations', 'cookie consent', 'cookie settings', 'privacy policy',
        'terms of use', 'download app', 'video library', 'know more about', 'types of loan',
        'frequently asked questions', 'saved jobs', 'view all', 'view our ads', 'window-eyes',
        'yourdolphin.co.uk', 'freedomscientific.com', 'webanywhere.cs.washington.edu',
        'screenreader.net', 'satogo.com', 'nvda-project.org', 'external website that opens in a new window',
        'download interview call letter', 'results of written examination'
    ]

    # 3. Overseas markers (strictly non-Indian territories)
    OVERSEAS_MARKERS = [
        'montréal', 'montreal', 'québec', 'quebec', 'canada', 'toronto',
        'rotterdam', 'netherlands', 'usa', 'united states', 'vietnam',
        'philippines', 'thailand', 'germany', 'poland', 'singapore',
        'indonesia', 'london', 'united kingdom'
    ]

    legit_roles = [
        'manager', 'officer', 'lead', 'head', 'analyst', 'engineer', 'specialist',
        'executive', 'director', 'intern', 'trainee', 'associate', 'consultant',
        'vp', 'president', 'developer', 'operator', 'supervisor', 'technician',
        'rider', 'agent', 'advisor', 'clerk', 'assistant', 'expert', 'architect'
    ]

    active_qs = Job.objects.filter(status='ACTIVE')
    total_active_before = active_qs.count()
    print(f"Total Active Jobs Before Remediation: {total_active_before}")

    rejected_nav = 0
    quarantined_overseas = 0

    with transaction.atomic():
        for j in active_qs:
            t = (j.job_title or '').strip()
            tl = t.lower()
            loc_l = (j.location or '').strip().lower()

            # Check overseas
            is_overseas = False
            if any(m in tl for m in ['montréal', 'montreal', 'québec', 'quebec', 'canada', 'toronto']) or \
               ('toronto' in loc_l) or ('canada' in loc_l and 'india' not in loc_l):
                is_overseas = True

            if is_overseas:
                j.status = 'INACTIVE'
                j.verification_status = 'QUARANTINED'
                j.verification_reason = f"OVERSEAS_TERRITORY_QUARANTINE: Vacancy '{t}' at location '{j.location}' is outside Indian jurisdiction."
                j.save(update_fields=['status', 'verification_status', 'verification_reason'])
                quarantined_overseas += 1
                continue

            # Check exact boilerplate
            is_defect = False
            defect_reason = ""

            if tl in EXACT_DEFECTS:
                is_defect = True
                defect_reason = f"EXACT_NAV_DEFECT: '{t}' is a website navigation control or header link."
            elif any(sub in tl for sub in SUBSTRING_DEFECTS):
                is_defect = True
                defect_reason = f"SUBSTRING_DEFECT: '{t}' contains non-job boilerplate."
            elif tl.startswith('http://') or tl.startswith('https://'):
                is_defect = True
                defect_reason = f"URL_TITLE_DEFECT: '{t}' is a raw hyperlink, not a job vacancy."
            elif tl.startswith('jobs at ') or tl.startswith('life at ') or tl.startswith('life @'):
                is_defect = True
                defect_reason = f"HEADER_DEFECT: '{t}' is an informational banner title."
            
            # UltraTech specifics check
            if j.company_id == 'COMP_TOP200_016' and tl in [
                'home', 'jobs at ultratech', 'life at ultratech', 'our values', 'leadership team',
                'our story', 'press kit', 'stories', 'press releases', 'useful information',
                'corporate governance', 'investors centre', 'case studies', 'community development',
                'environment', 'governance', 'about us', 'media', 'investors', 'trending',
                'financials', 'sustainability', 'overview', 'for corporate', 'for infrastructure',
                'for home builders'
            ]:
                is_defect = True
                defect_reason = f"ULTRATECH_NAV_DEFECT: '{t}' is an UltraTech website section header."

            # Verify that we don't accidentally reject genuine titles like "Chief Sustainability Officer"
            if is_defect:
                if any(role in tl for role in legit_roles) and tl not in ['leadership team', 'management team', 'saved jobs']:
                    # Recheck: if it contains an actual job title word, don't reject unless it's an exact match in EXACT_DEFECTS
                    if tl not in EXACT_DEFECTS:
                        is_defect = False

            if is_defect:
                j.status = 'INACTIVE'
                j.verification_status = 'REJECTED'
                j.verification_reason = defect_reason
                j.save(update_fields=['status', 'verification_status', 'verification_reason'])
                rejected_nav += 1

    print(f"Remediation Complete:")
    print(f"  - Quarantined Overseas / Canada Jobs: {quarantined_overseas}")
    print(f"  - Rejected Navigation / Boilerplate Jobs: {rejected_nav}")
    print(f"  - Genuine Active Jobs Remaining: {Job.objects.filter(status='ACTIVE').count()}")

if __name__ == '__main__':
    run_remediation()
