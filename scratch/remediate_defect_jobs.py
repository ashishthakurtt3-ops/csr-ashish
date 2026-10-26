import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import sys
sys.stdout.reconfigure(encoding='utf-8')
from django.db.models import Q
from modules.admin_panel.models import Job
from modules.admin_panel.verification import (
    NON_CAREER_URL_PATTERNS,
    UI_NAV_DEFECT_PATTERNS,
    EXACT_MATCH_DEFECT_TOKENS,
    apply_job_safety_filters
)

print("=== Starting Database Cleanup for Defective Job Records ===", flush=True)


active_all = Job.objects.filter(status='ACTIVE')
print(f"Total ACTIVE jobs before remediation: {active_all.count()}")

# Identify jobs that fail safety filters
defective_count = 0
for bad_url in NON_CAREER_URL_PATTERNS:
    matched = Job.objects.filter(status='ACTIVE').filter(
        django.db.models.Q(application_url__icontains=bad_url) | django.db.models.Q(source_url__icontains=bad_url)
    )
    cnt = matched.count()
    if cnt > 0:
        matched.update(status='INACTIVE', verification_status='REJECTED', verification_reason='Non-career URL')
        defective_count += cnt
        print(f"Deactivated {cnt} jobs matching bad URL pattern: '{bad_url}'")

# Specific language / phrase exclusions
for title_term in [
    'Life @', 'Life at ', 'Jobs at ', 'Results of ', 'Result of ',
    'Final Result', 'Detailed Result', 'Interview Schedule', 'Admit Card',
    '(External website', 'Montréal', 'Montreal', 'Québec', 'Quebec',
    'Latin America', 'Gerente de', 'Estágio', 'Banco de Talentos',
    'verfahrensmechaniker', 'Kautschuktechnologe', 'Откликнуться', 'एसजेवीएन',
    'Emotron', 'I have read, understood', 'Diversity and Inclusion', 'Our Products',
    'Reconnect with Us', 'Analyst relations', 'Media contacts', 'Request for Services',
    'AWS re:Invent', 'Microsoft Ignite', 'Oracle AI World', 'Gobally present, regionally supported',
    'Discover your team', 'Search for open positions by country', 'Become part of our family',
    'Building A Better Bharat, Together', 'Investor Meet & Presentation', 'Annual Reports',
    'Grievance Redressal Officer', 'List of Authorized Collection', 'Unauthorized Individuals/Entities',
    'Customer Awareness Literature', 'Regional Centralized Customer Service Centre',
    'KMP for determining materiality', 'Information and reports including compliance',
    'Contact for investor grievances', 'Vigil Mechanism/ Whistle Blower Policy',
    'Investor Education & Protection Fund', 'Disclosure under Reg', 'Disclosure on Related Party Transactions',
    'Current Openings – Global', 'Current Openings - Global', 'Customer Portal - DARPAN',
    'We are not able to verify your identity', 'Year of incorporation verification failed',
    'Year of Birth verification failed', 'Verify using another option', 'Strictly Necessary',
    'SmartRecruiters Attrax', 'Track Complaint', 'Lodge a Complaint', 'Have a Grievance?',
    'Compensation Philosophy', 'Innovation Initiatives', 'Learning and Development',
    'Public Announcement-', 'Detailed Public Statement-', 'Offer Lette r', 'Search & Apply',
    'Working at Reliance Group', 'Cookie Notice', 'Beware of fraudulent job offers',
    'Wipro Locations', 'Cookie Consent Manager', 'Our Partners', 'Our Vision & Mission',
    'AVRO INDIA Bot', "You're on our list", 'Adani Career Site', 'Adani Connex Career Site',
    'Openings at Zydus', 'View Backlog Vacancies (PDF)', 'Откликнуться сейчас', 'Apply Here',
    'Video Gallery', 'Image Gallery', 'Company Newsletters', 'Media Kit', 'Corporate Press Kit',
    'News And Updates', 'Life care with focus on innovation', 'Solid Waste Treatment',
    'AC & DC UPS', 'Waste Management', 'Software Products', 'IT Services', 'IoT & Smart Analytics',
    'Cherpoli Shahpur', 'Download', 'Notice:', 'Social Connect', 'Career Opportunities', 'Projects',
    'title', 'Home', 'About Us', 'Our Values', 'Leadership Team', 'Our Story', 'Press Kit',
    'Stories', 'Press Releases', 'Useful Information', 'Corporate Governance', 'Investors Centre',
    'Case Studies', 'Community Development', 'Environment', 'Governance', 'Media', 'Investors',
    'Trending', 'Financials', 'Sustainability', 'Overview', 'Company Overview', 'For Corporate',
    'For Infrastructure', 'For Home Builders', 'Consumer Products', 'Saved Jobs', 'Frequently Asked Questions',
    'Website feedback', 'Partnership', 'Download Forms', 'View our Ads', 'Customer Education',
    'Asset Publisher', 'Departments', 'otPcCenter', 'otCenterRounded', 'Skip to content',
    'Skip to primary navigation', 'Free Credit Score', 'Locator', 'Branch Locator'
]:
    if title_term in EXACT_MATCH_DEFECT_TOKENS:
        matched = Job.objects.filter(status='ACTIVE', job_title__iexact=title_term)
    else:
        matched = Job.objects.filter(status='ACTIVE', job_title__icontains=title_term)
    cnt = matched.count()
    if cnt > 0:
        matched.update(status='INACTIVE', verification_status='REJECTED', verification_reason='Non-job defect title')
        defective_count += cnt
        print(f"Deactivated {cnt} jobs matching title term: '{title_term}'")

active_after = Job.objects.filter(status='ACTIVE').exclude(verification_status='REJECTED').count()
print(f"\nRemediation complete! Total records deactivated: {defective_count}")
print(f"Total clean, authentic ACTIVE jobs remaining: {active_after}")
