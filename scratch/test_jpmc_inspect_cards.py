from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto('https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=India', wait_until='networkidle')
    page.wait_for_timeout(4000)
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')

    # Find where 'Commercial & Investment Bank' or job titles appear
    for tag in soup.find_all(text=re.compile(r'Commercial & Investment Bank|Asset Management', re.I)):
        parent = tag.parent
        print("Found text in tag:", parent.name, parent.get('class'), parent.attrs)
        # Climb up 3 levels
        p1 = parent.parent
        print("  P1:", p1.name if p1 else None, p1.get('class') if p1 else None, p1.attrs if p1 else None)
        p2 = p1.parent if p1 else None
        print("  P2:", p2.name if p2 else None, p2.get('class') if p2 else None, p2.attrs if p2 else None)
        # Check if any ancestor has href or id
        anc = parent
        while anc and anc.name != 'body':
            if anc.get('href') or anc.get('data-req-id') or anc.get('data-job-id') or 'requisition' in str(anc.attrs).lower():
                print("  --> Ancestor attributes:", anc.attrs)
                break
            anc = anc.parent

    browser.close()

