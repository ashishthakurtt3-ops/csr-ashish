from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    network_calls = []
    page.on("response", lambda r: network_calls.append((r.status, r.url)) if 'job' in r.url.lower() or 'search' in r.url.lower() else None)

    page.goto('https://careers.jpmorgan.com/global/en/home', wait_until='networkidle')
    print("Page Title:", page.title())
    print("Job-related Network responses:", len(network_calls))
    for status, url in network_calls[:10]:
        print(f"  {status} {url[:100]}")

    browser.close()

