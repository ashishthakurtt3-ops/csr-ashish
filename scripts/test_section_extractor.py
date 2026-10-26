import re
import json
from bs4 import BeautifulSoup

with open('scripts/hero_job_detail.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'lxml')

print("--- Testing Metadata Extraction ---")
# 1. Date
date_val = None
date_el = soup.find(class_=re.compile(r'jobDate', re.I))
if date_el:
    date_val = date_el.get_text(strip=True).replace('Date:', '').strip()
print(f"Extracted Date: {date_val}")

# 2. Location
loc_val = None
loc_el = soup.find(class_=re.compile(r'jobGeoLocation|jobLocation', re.I))
if loc_el:
    loc_val = loc_el.get_text(strip=True).replace('Location:', '').strip()
print(f"Extracted Location: {loc_val}")

# 3. Sections extraction
# In SuccessFactors CSB, the jobdescription contains headers (h2 or b) followed by paragraphs/lists.
# Let's inspect all headings inside the job display
job_display = soup.find(class_=re.compile(r'jobDisplay|jobdescription|job', re.I))

sections = {}
current_header = None
current_content = []

# Collect elements inside job_display
for elem in job_display.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'b', 'p', 'ul', 'ol', 'div']):
    # If element is a header
    is_header = False
    text = elem.get_text(strip=True)
    if not text:
        continue
    
    # Check if this element acts as a section header
    # in CSB: <h2 ...><b ...>Heading</b></h2> or <b>Heading</b>
    if elem.name in ['h2', 'h3', 'h4']:
        is_header = True
    elif elem.name in ['b', 'strong'] and len(text) < 60 and not elem.find_parent(['h2', 'h3', 'h4', 'li']):
        # If parent is just a p or div and text is short title-case
        parent = elem.parent
        if parent and parent.name in ['p', 'div'] and len(parent.get_text(strip=True)) == len(text):
            is_header = True

    if is_header:
        h_clean = text.strip()
        if current_header and current_content:
            sections[current_header] = "\n".join(current_content).strip()
        current_header = h_clean
        current_content = []
    else:
        # If it's a leaf content paragraph or list
        if elem.name in ['p', 'ul', 'ol'] and current_header:
            # avoid duplicating parent text if already visited
            p_text = elem.get_text(separator='\n', strip=True)
            if p_text and p_text != current_header and p_text not in "\n".join(current_content):
                current_content.append(p_text)

if current_header and current_content:
    sections[current_header] = "\n".join(current_content).strip()

print(f"\n--- Extracted {len(sections)} Sections ---")
for k, v in sections.items():
    print(f"SECTION [{k}]:\n{v[:150]}...\n")
