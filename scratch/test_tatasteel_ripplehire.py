from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    page.goto('https://tatasteel.ripplehire.com/candidate/', wait_until='networkidle')
    html = page.content()
    soup = BeautifulSoup(html, 'html.parser')
    print("Page Title:", page.title())
    print("Cards/Links on RippleHire:")
    for a in soup.find_all('a', href=True):
        txt = a.get_text(' ', strip=True)
        href = a['href']
        if any(k in href.lower() or k in txt.lower() for k in ['job', 'detail', 'opening', 'engineer', 'manager', 'lead']):
            print(f"  * {txt} -> {href}")

    browser.close()

