from playwright.sync_api import sync_playwright
import time

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        
        print("Navigating to http://127.0.0.1:8000 ...")
        page.goto('http://127.0.0.1:8000', wait_until='networkidle')
        time.sleep(2)
        page.screenshot(path='scratch/current_home.png')
        print("Captured scratch/current_home.png")

        # Click pricing tab
        pricing_btn = page.query_selector('button[data-tab="pricing"], a[href="#pricing"], button:has-text("Pricing"), [data-target="tab-pricing"]')
        if pricing_btn:
            pricing_btn.click()
            time.sleep(1)
            page.screenshot(path='scratch/current_pricing.png')
            print("Captured scratch/current_pricing.png")
        
        # Click jobs tab
        jobs_btn = page.query_selector('button[data-tab="jobs"], [data-target="tab-jobs"]')
        if jobs_btn:
            jobs_btn.click()
            time.sleep(1)
            page.screenshot(path='scratch/current_jobs.png')
            print("Captured scratch/current_jobs.png")

        browser.close()

if __name__ == '__main__':
    capture()

