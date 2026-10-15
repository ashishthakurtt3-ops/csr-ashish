import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ['FORCE_SQLITE'] = '1'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, Contact, OpportunityScore, PageRecord, CompanyCrawlSummary, AuditTrail

print("Company fields:", [f.name for f in Company._meta.fields])
print("Job fields:", [f.name for f in Job._meta.fields])
print("CSRProject fields:", [f.name for f in CSRProject._meta.fields])
print("CSROpportunity fields:", [f.name for f in CSROpportunity._meta.fields])
print("Contact fields:", [f.name for f in Contact._meta.fields])
print("OpportunityScore fields:", [f.name for f in OpportunityScore._meta.fields])
print("PageRecord fields:", [f.name for f in PageRecord._meta.fields])
print("CompanyCrawlSummary fields:", [f.name for f in CompanyCrawlSummary._meta.fields])
