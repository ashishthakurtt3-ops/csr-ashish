import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Force SQLite for this script
os.environ['FORCE_SQLITE'] = '1'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# We can dynamically configure settings or run migrate
import django
from django.conf import settings

# If settings not configured with sqlite, let's configure
if not settings.configured:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'

django.setup()

from django.core.management import call_command
from modules.admin_panel.models import Company, Job, CSRProject, CSROpportunity, Contact, OpportunityScore

print("Checking SQLite migration...")
call_command('migrate', verbosity=1)

print("Loading seed_data.json into SQLite...")
call_command('loaddata', 'seed_data.json', verbosity=1)

print("\n--- Verification on SQLite ---")
print("Companies:", Company.objects.count())
print("Jobs:", Job.objects.count())
print("CSR Projects:", CSRProject.objects.count())
print("CSR Opportunities:", CSROpportunity.objects.count())
print("Contacts:", Contact.objects.count())
print("Scores:", OpportunityScore.objects.count())
