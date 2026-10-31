"""
modules/crawler_engine/location_normalizer.py
=============================================
Enterprise Location Parsing & Normalization Engine:
- Extracts and standardizes city, state, country, and postal code from raw text scraped from company websites & ATS portals.
- Recognizes Indian states, union territories, major tier-1/tier-2/tier-3 cities.
- Recognizes international countries (ISO codes and full names) and US/global states/regions.
- Strips internal corporate noise (plant codes, office codes, requisitions).
"""

import re
from typing import Dict, Any, Optional, Tuple

# Country name & code mappings
COUNTRY_MAP = {
    # ISO-2 / ISO-3 -> Standard Country Name
    'IN': 'India', 'IND': 'India', 'INDIA': 'India',
    'US': 'United States', 'USA': 'United States', 'UNITED STATES': 'United States',
    'UK': 'United Kingdom', 'GB': 'United Kingdom', 'GBR': 'United Kingdom', 'UNITED KINGDOM': 'United Kingdom',
    'DE': 'Germany', 'DEU': 'Germany', 'GERMANY': 'Germany',
    'SG': 'Singapore', 'SGP': 'Singapore', 'SINGAPORE': 'Singapore',
    'AE': 'United Arab Emirates', 'ARE': 'United Arab Emirates', 'UAE': 'United Arab Emirates', 'DUBAI': 'United Arab Emirates',
    'NL': 'Netherlands', 'NLD': 'Netherlands', 'NETHERLANDS': 'Netherlands',
    'AU': 'Australia', 'AUS': 'Australia', 'AUSTRALIA': 'Australia',
    'CA': 'Canada', 'CAN': 'Canada', 'CANADA': 'Canada',
    'FR': 'France', 'FRA': 'France', 'FRANCE': 'France',
    'JP': 'Japan', 'JPN': 'Japan', 'JAPAN': 'Japan',
    'CH': 'Switzerland', 'CHE': 'Switzerland', 'SWITZERLAND': 'Switzerland',
    'IE': 'Ireland', 'IRL': 'Ireland', 'IRELAND': 'Ireland',
    'SE': 'Sweden', 'SWE': 'Sweden', 'SWEDEN': 'Sweden',
    'ZA': 'South Africa', 'ZAF': 'South Africa', 'SOUTH AFRICA': 'South Africa',
    'MY': 'Malaysia', 'MYS': 'Malaysia', 'MALAYSIA': 'Malaysia',
    'PH': 'Philippines', 'PHL': 'Philippines', 'PHILIPPINES': 'Philippines',
    'BR': 'Brazil', 'BRA': 'Brazil', 'BRAZIL': 'Brazil',
    'MX': 'Mexico', 'MEX': 'Mexico', 'MEXICO': 'Mexico',
    'PL': 'Poland', 'POL': 'Poland', 'POLAND': 'Poland',
    'ES': 'Spain', 'ESP': 'Spain', 'SPAIN': 'Spain',
    'IT': 'Italy', 'ITA': 'Italy', 'ITALY': 'Italy',
}

# Indian State codes and standard names
INDIAN_STATES = {
    'ANDHRA PRADESH': 'Andhra Pradesh', 'AP': 'Andhra Pradesh',
    'ARUNACHAL PRADESH': 'Arunachal Pradesh', 'AR': 'Arunachal Pradesh',
    'ASSAM': 'Assam', 'AS': 'Assam',
    'BIHAR': 'Bihar', 'BR': 'Bihar',
    'CHHATTISGARH': 'Chhattisgarh', 'CG': 'Chhattisgarh', 'CT': 'Chhattisgarh',
    'GOA': 'Goa', 'GA': 'Goa',
    'GUJARAT': 'Gujarat', 'GJ': 'Gujarat',
    'HARYANA': 'Haryana', 'HR': 'Haryana',
    'HIMACHAL PRADESH': 'Himachal Pradesh', 'HP': 'Himachal Pradesh',
    'JHARKHAND': 'Jharkhand', 'JH': 'Jharkhand',
    'KARNATAKA': 'Karnataka', 'KA': 'Karnataka',
    'KERALA': 'Kerala', 'KL': 'Kerala',
    'MADHYA PRADESH': 'Madhya Pradesh', 'MP': 'Madhya Pradesh',
    'MAHARASHTRA': 'Maharashtra', 'MH': 'Maharashtra',
    'MANIPUR': 'Manipur', 'MN': 'Manipur',
    'MEGHALAYA': 'Meghalaya', 'ML': 'Meghalaya',
    'MIZORAM': 'Mizoram', 'MZ': 'Mizoram',
    'NAGALAND': 'Nagaland', 'NL': 'Nagaland',
    'ODISHA': 'Odisha', 'ORISSA': 'Odisha', 'OD': 'Odisha', 'OR': 'Odisha',
    'PUNJAB': 'Punjab', 'PB': 'Punjab',
    'RAJASTHAN': 'Rajasthan', 'RJ': 'Rajasthan',
    'SIKKIM': 'Sikkim', 'SK': 'Sikkim',
    'TAMIL NADU': 'Tamil Nadu', 'TN': 'Tamil Nadu',
    'TELANGANA': 'Telangana', 'TS': 'Telangana', 'TG': 'Telangana',
    'TRIPURA': 'Tripura', 'TR': 'Tripura',
    'UTTAR PRADESH': 'Uttar Pradesh', 'UP': 'Uttar Pradesh',
    'UTTARAKHAND': 'Uttarakhand', 'UK': 'Uttarakhand', 'UA': 'Uttarakhand',
    'WEST BENGAL': 'West Bengal', 'WB': 'West Bengal',
    'DELHI': 'Delhi', 'DL': 'Delhi', 'NEW DELHI': 'Delhi', 'NCR': 'Delhi NCR', 'DELHI NCR': 'Delhi NCR',
    'CHANDIGARH': 'Chandigarh', 'CH': 'Chandigarh',
    'PUDUCHERRY': 'Puducherry', 'PY': 'Puducherry',
    'JAMMU AND KASHMIR': 'Jammu & Kashmir', 'JK': 'Jammu & Kashmir',
    'LADAKH': 'Ladakh', 'LA': 'Ladakh',
    'PAN-INDIA': 'Pan-India', 'PAN INDIA': 'Pan-India',
}

# Major Indian Cities to State mapping
CITY_TO_STATE = {
    'MUMBAI': ('Mumbai', 'Maharashtra'),
    'PUNE': ('Pune', 'Maharashtra'),
    'NAGPUR': ('Nagpur', 'Maharashtra'),
    'NASHIK': ('Nashik', 'Maharashtra'),
    'CHAKAN': ('Chakan', 'Maharashtra'),
    'AIROLI': ('Airoli', 'Maharashtra'),
    'SANTACRUZ': ('Santacruz', 'Maharashtra'),
    'THANE': ('Thane', 'Maharashtra'),
    'NAVI MUMBAI': ('Navi Mumbai', 'Maharashtra'),
    'AURANGABAD': ('Aurangabad', 'Maharashtra'),
    'BENGALURU': ('Bengaluru', 'Karnataka'),
    'BANGALORE': ('Bengaluru', 'Karnataka'),
    'MYSORE': ('Mysuru', 'Karnataka'),
    'MYSURU': ('Mysuru', 'Karnataka'),
    'MANGALORE': ('Mangaluru', 'Karnataka'),
    'HUBBALLI': ('Hubballi', 'Karnataka'),
    'CHENNAI': ('Chennai', 'Tamil Nadu'),
    'COIMBATORE': ('Coimbatore', 'Tamil Nadu'),
    'MADURAI': ('Madurai', 'Tamil Nadu'),
    'TRICHY': ('Tiruchirappalli', 'Tamil Nadu'),
    'SALEM': ('Salem', 'Tamil Nadu'),
    'HYDERABAD': ('Hyderabad', 'Telangana'),
    'SECUNDERABAD': ('Secunderabad', 'Telangana'),
    'WARANGAL': ('Warangal', 'Telangana'),
    'VISAKHAPATNAM': ('Visakhapatnam', 'Andhra Pradesh'),
    'VIZAG': ('Visakhapatnam', 'Andhra Pradesh'),
    'VIJAYAWADA': ('Vijayawada', 'Andhra Pradesh'),
    'TIRUPATI': ('Tirupati', 'Andhra Pradesh'),
    'GUNTUR': ('Guntur', 'Andhra Pradesh'),
    'AHMEDABAD': ('Ahmedabad', 'Gujarat'),
    'GANDHINAGAR': ('Gandhinagar', 'Gujarat'),
    'VADODARA': ('Vadodara', 'Gujarat'),
    'BARODA': ('Vadodara', 'Gujarat'),
    'SURAT': ('Surat', 'Gujarat'),
    'RAJKOT': ('Rajkot', 'Gujarat'),
    'MUNDRA': ('Mundra', 'Gujarat'),
    'HAZIRA': ('Hazira', 'Gujarat'),
    'DAHEJ': ('Dahej', 'Gujarat'),
    'JAMNAGAR': ('Jamnagar', 'Gujarat'),
    'GURGAON': ('Gurgaon', 'Haryana'),
    'GURUGRAM': ('Gurugram', 'Haryana'),
    'FARIDABAD': ('Faridabad', 'Haryana'),
    'MANESAR': ('Manesar', 'Haryana'),
    'PANIPAT': ('Panipat', 'Haryana'),
    'NOIDA': ('Noida', 'Uttar Pradesh'),
    'GREATER NOIDA': ('Greater Noida', 'Uttar Pradesh'),
    'LUCKNOW': ('Lucknow', 'Uttar Pradesh'),
    'KANPUR': ('Kanpur', 'Uttar Pradesh'),
    'VARANASI': ('Varanasi', 'Uttar Pradesh'),
    'AGRA': ('Agra', 'Uttar Pradesh'),
    'KOLKATA': ('Kolkata', 'West Bengal'),
    'CALCUTTA': ('Kolkata', 'West Bengal'),
    'HOWRAH': ('Howrah', 'West Bengal'),
    'SILIGURI': ('Siliguri', 'West Bengal'),
    'DURGAPUR': ('Durgapur', 'West Bengal'),
    'JAIPUR': ('Jaipur', 'Rajasthan'),
    'JODHPUR': ('Jodhpur', 'Rajasthan'),
    'UDAIPUR': ('Udaipur', 'Rajasthan'),
    'KOTA': ('Kota', 'Rajasthan'),
    'INDORE': ('Indore', 'Madhya Pradesh'),
    'BHOPAL': ('Bhopal', 'Madhya Pradesh'),
    'PITHAMPUR': ('Pithampur', 'Madhya Pradesh'),
    'GWALIOR': ('Gwalior', 'Madhya Pradesh'),
    'JABALPUR': ('Jabalpur', 'Madhya Pradesh'),
    'KOCHI': ('Kochi', 'Kerala'),
    'COCHIN': ('Kochi', 'Kerala'),
    'THIRUVANANTHAPURAM': ('Thiruvananthapuram', 'Kerala'),
    'TRIVANDRUM': ('Thiruvananthapuram', 'Kerala'),
    'CALICUT': ('Kozhikode', 'Kerala'),
    'KOZHIKODE': ('Kozhikode', 'Kerala'),
    'BHUBANESWAR': ('Bhubaneswar', 'Odisha'),
    'CUTTACK': ('Cuttack', 'Odisha'),
    'ROURKELA': ('Rourkela', 'Odisha'),
    'CHANDIGARH': ('Chandigarh', 'Chandigarh'),
    'MOHALI': ('Mohali', 'Punjab'),
    'LUDHIANA': ('Ludhiana', 'Punjab'),
    'AMRITSAR': ('Amritsar', 'Punjab'),
    'PATNA': ('Patna', 'Bihar'),
    'RANCHI': ('Ranchi', 'Jharkhand'),
    'JAMSHEDPUR': ('Jamshedpur', 'Jharkhand'),
    'RAIPUR': ('Raipur', 'Chhattisgarh'),
    'BHILAI': ('Bhilai', 'Chhattisgarh'),
    'GUWAHATI': ('Guwahati', 'Assam'),
    'DEHRADUN': ('Dehradun', 'Uttarakhand'),
    'HARIDWAR': ('Haridwar', 'Uttarakhand'),
    'SHIMLA': ('Shimla', 'Himachal Pradesh'),
    'BADDI': ('Baddi', 'Himachal Pradesh'),
    'PANAJI': ('Panaji', 'Goa'),
}

# US State codes
US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California',
    'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'FL': 'Florida', 'GA': 'Georgia',
    'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa',
    'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri',
    'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey',
    'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio',
    'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont',
    'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming',
}


def clean_plant_or_office_noise(text: str) -> str:
    """Removes internal corporate plant, facility, or requisition codes."""
    if not text:
        return ""
    # Strip things like 'MUM-KND-AFS(AD)', 'Chennai-MRV-AD', '(FD)', 'Plant', 'CO', 'A.O'
    cleaned = re.sub(r'[\(\[\{][^\)\]\}]*[\)\]\}]', '', text)
    cleaned = re.sub(r'\b(?:plant|office|branch|facility|campus|centre|center|works|site|hub|a\.o|co)\b', '', cleaned, flags=re.I)
    cleaned = re.sub(r'[-_/]+(?:mrv|afs|ad|knd|fd|co)\b', '', cleaned, flags=re.I)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,-_')
    return cleaned


def normalize_job_location(raw_location: Optional[str], default_hq: Optional[str] = None) -> Dict[str, Any]:
    """
    Parses a raw location string into structured fields:
    returns: {
        'location': formatted_display_location,
        'city': city_name or None,
        'state': state_name or None,
        'country': country_name or None,
        'pincode': pincode or None,
        'is_remote': bool
    }
    """
    if not raw_location or not raw_location.strip():
        if default_hq and default_hq.strip():
            return normalize_job_location(default_hq)
        return {
            'location': 'India',
            'city': None,
            'state': None,
            'country': 'India',
            'pincode': None,
            'is_remote': False,
            'work_mode': None
        }

    raw = raw_location.strip()
    raw_lower = raw.lower()

    # Remote check
    if any(k in raw_lower for k in ['remote', 'work from home', 'wfh', 'virtual', 'anywhere']):
        return {
            'location': 'Remote',
            'city': None,
            'state': None,
            'country': None,
            'pincode': None,
            'is_remote': True,
            'work_mode': 'Remote'
        }

    # Extract pincode (e.g. 122001, 302028, 492001)
    pincode = None
    pin_match = re.search(r'\b([0-9]{6})\b', raw)
    if pin_match:
        pincode = pin_match.group(1)
        raw = raw.replace(pincode, '').strip(' ,-_')

    # Split into comma/hyphen parts
    parts = [clean_plant_or_office_noise(p) for p in re.split(r'[,/|;]+', raw)]
    parts = [p for p in parts if p and p.lower() not in ('1 location', 'location', 'multiple locations', 'n/a', 'none')]

    city = None
    state = None
    country = None

    # Check each part from right to left
    remaining_parts = []
    for p in parts:
        p_upper = p.upper().strip()
        p_clean = p.strip()

        # 1. Country check
        if p_upper in COUNTRY_MAP:
            country = COUNTRY_MAP[p_upper]
            continue

        # 2. Indian state check
        if p_upper in INDIAN_STATES:
            state = INDIAN_STATES[p_upper]
            if not country:
                country = 'India'
            continue

        # 3. US State check
        if p_upper in US_STATES:
            state = US_STATES[p_upper]
            if not country:
                country = 'United States'
            continue

        remaining_parts.append(p_clean)

    # Resolve city from remaining parts or mapped city
    for p in remaining_parts:
        p_upper = p.upper().strip()
        if p_upper in CITY_TO_STATE:
            c_name, s_name = CITY_TO_STATE[p_upper]
            city = c_name
            if not state:
                state = s_name
            if not country:
                country = 'India'
            break
        elif not city and len(p) >= 2 and not p.isdigit():
            city = p.title()

    # If country is not yet set and we have Indian city or state:
    if not country:
        if state in INDIAN_STATES.values() or (city and city.upper() in CITY_TO_STATE):
            country = 'India'

    # Build clean formatted display string
    display_parts = []
    if city:
        display_parts.append(city)
    if state and (not city or state.lower() not in city.lower()):
        display_parts.append(state)
    if country and (not display_parts or country.lower() not in [x.lower() for x in display_parts]):
        display_parts.append(country)

    if display_parts:
        formatted_loc = ', '.join(display_parts)
    else:
        formatted_loc = raw if raw else 'India'

    return {
        'location': formatted_loc,
        'city': city,
        'state': state,
        'country': country,
        'pincode': pincode,
        'is_remote': False,
        'work_mode': None
    }
