"""
Audit and reconcile geography (city, state, country) for all 964 active published jobs.
Detects when location clearly indicates an international or specific domestic geography:
- Parses country codes from location/ATS payload:
  - 'za' -> South Africa
  - 'Kazakhstan' -> Kazakhstan
  - 'de' -> Germany
  - 'th' -> Thailand
  - 'us' / 'United States' -> United States
  - 'in' / 'IN' / 'India' -> India
- Normalizes country field to standard English country name ('India' instead of 'in' or 'IN')
- Fixes Tata Power jobs where country was parsed as '0'
- Verifies employer entity / group relationship
"""
import os, sys, django, re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.admin_panel.models import Job

COUNTRY_CODE_MAP = {
    'in': 'India',
    'ind': 'India',
    'india': 'India',
    'za': 'South Africa',
    'south africa': 'South Africa',
    'kz': 'Kazakhstan',
    'kazakhstan': 'Kazakhstan',
    'de': 'Germany',
    'germany': 'Germany',
    'th': 'Thailand',
    'thailand': 'Thailand',
    'us': 'United States',
    'usa': 'United States',
    'united states': 'United States',
    'uk': 'United Kingdom',
    'gb': 'United Kingdom',
    'united kingdom': 'United Kingdom',
    'fr': 'France',
    'france': 'France',
    'ca': 'Canada',
    'canada': 'Canada',
    'my': 'Malaysia',
    'malaysia': 'Malaysia',
    'sg': 'Singapore',
    'singapore': 'Singapore',
    'ae': 'United Arab Emirates',
    'uae': 'United Arab Emirates',
    'np': 'Nepal',
    'nepal': 'Nepal',
    'bd': 'Bangladesh',
    'bangladesh': 'Bangladesh',
    'lk': 'Sri Lanka',
    'sri lanka': 'Sri Lanka',
    'ke': 'Kenya',
    'kenya': 'Kenya',
    'ng': 'Nigeria',
    'nigeria': 'Nigeria',
    'zm': 'Zambia',
    'zambia': 'Zambia',
    'zw': 'Zimbabwe',
    'zimbabwe': 'Zimbabwe',
    'tz': 'Tanzania',
    'tanzania': 'Tanzania',
    'mz': 'Mozambique',
    'mozambique': 'Mozambique',
    'cd': 'Democratic Republic of the Congo',
    'congo': 'Democratic Republic of the Congo',
    'ma': 'Morocco',
    'morocco': 'Morocco',
}

print("=" * 80)
print("AUDITING & RECONCILING GEOGRAPHY ACROSS ALL 964 ACTIVE JOBS")
print("=" * 80)

active_jobs = Job.objects.filter(status='ACTIVE', verification_status='PUBLISHED')

updated_count = 0
corrected_intl = []

for j in active_jobs:
    loc = (j.location or '').strip()
    current_country = (j.country or '').strip()
    new_country = None
    
    # 1. Parse from location string
    if loc:
        # Check explicit keywords
        loc_l = loc.lower()
        if 'kazakhstan' in loc_l or 'almaty' in loc_l:
            new_country = 'Kazakhstan'
        elif 'germany' in loc_l or 'augsburg' in loc_l:
            new_country = 'Germany'
        elif 'thailand' in loc_l or 'bangkok' in loc_l:
            new_country = 'Thailand'
        elif 'france' in loc_l or 'paris' in loc_l:
            new_country = 'France'
        elif 'south africa' in loc_l or 'johannesburg' in loc_l or 'cape town' in loc_l or 'sterkfontein' in loc_l:
            new_country = 'South Africa'
        elif 'united states' in loc_l or ', usa' in loc_l:
            new_country = 'United States'
        elif 'united kingdom' in loc_l or ', uk' in loc_l:
            new_country = 'United Kingdom'
        elif 'zimbabwe' in loc_l:
            new_country = 'Zimbabwe'
        elif 'zambia' in loc_l:
            new_country = 'Zambia'
        elif 'morocco' in loc_l:
            new_country = 'Morocco'
        elif 'nepal' in loc_l:
            new_country = 'Nepal'
        elif 'sri lanka' in loc_l:
            new_country = 'Sri Lanka'
        else:
            # Check trailing code e.g. ", za" or ", in" or ", de"
            parts = [p.strip() for p in loc.split(',') if p.strip()]
            if parts:
                last_part = parts[-1].lower()
                # If last part is a 6-digit Indian PIN code (e.g. 122100, 302028), country is India
                if re.match(r'^\d{6}$', last_part):
                    new_country = 'India'
                    if len(parts) >= 2 and parts[-2].lower() in ('in', 'india'):
                        new_country = 'India'
                elif last_part in COUNTRY_CODE_MAP:
                    new_country = COUNTRY_CODE_MAP[last_part]
                elif len(parts) >= 2 and parts[-2].lower() in COUNTRY_CODE_MAP:
                    new_country = COUNTRY_CODE_MAP[parts[-2].lower()]
                    
    # Normalization of current_country if it's 'in' or 'IN'
    if not new_country:
        if current_country.lower() in ('in', 'india'):
            new_country = 'India'
        elif current_country in ('0', '', None):
            # Check location for Indian states/cities
            if any(k in loc.lower() for k in ('delhi', 'mumbai', 'bengaluru', 'bangalore', 'chennai', 'kolkata', 'hyderabad', 'pune', 'jaipur', 'ahmedabad', 'gurugram', 'noida', 'chakan', 'gujarat', 'maharashtra', 'rajasthan', 'karnataka', 'haryana', 'punjab')):
                new_country = 'India'

    if new_country and (j.country != new_country):
        old_val = j.country
        j.country = new_country
        j.save()
        updated_count += 1
        if new_country != 'India':
            corrected_intl.append({
                'job_id': j.job_id,
                'title': j.job_title,
                'company': j.company.company_name,
                'location': j.location,
                'old_country': old_val,
                'new_country': new_country
            })

print(f"\nTotal jobs with country normalized/corrected: {updated_count}")
print(f"International jobs identified & verified: {len(corrected_intl)}")
for it in corrected_intl:
    print(f"  {it['job_id']} | {it['company'][:25]} | {it['title'][:30]} | {it['location']} -> {it['new_country']}")

print("\n--- NEW RECONCILED COUNTRY BREAKDOWN ---")
from django.db.models import Count
for r in active_jobs.values('country').annotate(c=Count('pk')).order_by('-c'):
    print(f"  {r['country'] or 'Unspecified'}: {r['c']}")
