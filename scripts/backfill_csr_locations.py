import os
import sys
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from modules.admin_panel.models import CSRProject, Company

INDIAN_STATES_LIST = [
    'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
    'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
    'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
    'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
    'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
    'Delhi', 'Jammu & Kashmir', 'Jammu and Kashmir', 'Ladakh', 'Puducherry', 'Chandigarh'
]

MAJOR_INDIAN_CITIES_LIST = [
    'Mumbai', 'Bengaluru', 'Bangalore', 'Delhi', 'New Delhi', 'Hyderabad',
    'Chennai', 'Kolkata', 'Pune', 'Ahmedabad', 'Gurugram', 'Gurgaon', 'Noida',
    'Jaipur', 'Lucknow', 'Kanpur', 'Nagpur', 'Indore', 'Thane', 'Bhopal',
    'Visakhapatnam', 'Patna', 'Vadodara', 'Ghaziabad', 'Ludhiana', 'Agra',
    'Nashik', 'Faridabad', 'Meerut', 'Rajkot', 'Varanasi', 'Srinagar',
    'Aurangabad', 'Dhanbad', 'Amritsar', 'Navi Mumbai', 'Prayagraj', 'Allahabad',
    'Ranchi', 'Howrah', 'Coimbatore', 'Jabalpur', 'Gwalior', 'Vijayawada',
    'Jodhpur', 'Madurai', 'Raipur', 'Kota', 'Guwahati', 'Chandigarh', 'Mysore',
    'Mysuru', 'Tiruchirappalli', 'Salem', 'Kochi', 'Cochin', 'Bhubaneswar',
    'Dehradun', 'Jamnagar', 'Udaipur', 'Mangalore', 'Mangaluru', 'Shimla'
]

def extract_locations(text):
    if not text:
        return None, None
    text_lower = text.lower()
    if any(k in text_lower for k in ['pan-india', 'pan india', 'across india', 'nationwide', 'all india']):
        return 'Pan-India', 'Pan-India'
    
    found_states = []
    for st in INDIAN_STATES_LIST:
        if re.search(r'\b' + re.escape(st) + r'\b', text, re.IGNORECASE):
            found_states.append(st)
            
    found_cities = []
    for ci in MAJOR_INDIAN_CITIES_LIST:
        if re.search(r'\b' + re.escape(ci) + r'\b', text, re.IGNORECASE):
            found_cities.append(ci)
            
    if found_cities and found_states:
        ci_str = " / ".join(found_cities[:3])
        st_str = " / ".join(found_states[:2])
        return f"{ci_str}, {st_str}", found_states[0]
    elif found_cities:
        return " / ".join(found_cities[:3]), None
    elif found_states:
        return " / ".join(found_states[:3]), found_states[0]
    return None, None

def run_backfill():
    projects = CSRProject.objects.all().select_related('company')
    updated_count = 0
    from_text = 0
    from_hq = 0
    from_pan = 0

    for p in projects:
        full_text = f"{p.project_name or ''} {p.description or ''}"
        loc, state = extract_locations(full_text)
        
        if loc:
            from_text += 1
        elif p.company and p.company.headquarters:
            loc, state = extract_locations(p.company.headquarters)
            if not loc:
                loc = p.company.headquarters.split(',')[0].strip()
            from_hq += 1
        else:
            loc = 'Pan-India'
            state = 'Pan-India'
            from_pan += 1

        p.geographic_location = loc
        p.state = state
        p.raw_location = loc
        p.save(update_fields=['geographic_location', 'state', 'raw_location'])
        updated_count += 1

    print(f"Successfully backfilled {updated_count} CSR projects!")
    print(f"  - Extracted from project text: {from_text}")
    print(f"  - Derived from company corporate HQ: {from_hq}")
    print(f"  - Classified as Pan-India: {from_pan}")

if __name__ == '__main__':
    run_backfill()
