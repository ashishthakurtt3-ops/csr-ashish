from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto('https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/requisitions?keyword=India', wait_until='networkidle')
    page.wait_for_timeout(4000)
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    print("Page Title:", page.title())
    print("HTML Length:", len(html))
    
    # Check for job links or titles
    links = []
    for a in soup.find_all(['a', 'div', 'span']):
        txt = a.get_text(' ', strip=True)
        href = a.get('href', '')
        if 'job' in href.lower() or '/requisitions' in href.lower():
            links.append((txt, href))

    print(f"Total matching elements: {len(links)}")
    for txt, href in links[:10]:
        print(f"  * {txt[:40]} -> {href}")

    # Check text content
    print("\nBody text excerpt (first 600 chars):")
    print(page.inner_text('body')[:600])

    browser.close()

