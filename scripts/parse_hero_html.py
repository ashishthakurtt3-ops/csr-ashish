from bs4 import BeautifulSoup
import re

with open('scripts/hero_job_detail.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'lxml')

print("=== JOB TITLE ===")
title_el = soup.find(['h1', 'h2'], class_=re.compile(r'title|job', re.I)) or soup.find('h1')
print(f"H1: {soup.find('h1')}")
print(f"Title Element: {title_el}")

print("\n=== HEADER / METADATA SPANS & DIVS ===")
# Look for date, location, etc.
for el in soup.find_all(['span', 'div', 'p']):
    txt = el.get_text(strip=True)
    if any(k in txt for k in ['6 Oct 2026', 'Raipur', 'CT, IN', 'India BU', 'E4 to M2']):
        # only print leaf-ish elements
        if len(txt) < 150:
            print(f"[{el.name} class={el.get('class')}] {txt}")

print("\n=== ALL HEADINGS (H1-H6, STRONG, B) ===")
for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b']):
    txt = h.get_text(strip=True)
    if txt and len(txt) < 80:
        print(f"<{h.name} class={h.get('class')}>: {txt}")

print("\n=== JOB DESCRIPTION CONTAINER ===")
for div in soup.find_all('div', class_=re.compile(r'job|desc|content|detail', re.I)):
    classes = " ".join(div.get('class', []))
    text_len = len(div.get_text(strip=True))
    if 300 < text_len < 10000:
        print(f"Div class='{classes}', text_len={text_len}")

# Let's inspect the main content area
main_content = soup.find('div', class_=re.compile(r'jobdescription|job-description|jobDisplay|content', re.I)) or soup.find('div', id=re.compile(r'content|job', re.I))
if main_content:
    print("\n--- Main Content Text Preview (First 2000 chars) ---")
    print(main_content.get_text(separator='\n', strip=True)[:2000])
