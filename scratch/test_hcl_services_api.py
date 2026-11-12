from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    def handle_response(response):
        if '/services/recruiting/v1/jobs' in response.url:
            print("FOUND JOBS API RESPONSE!")
            print("Status:", response.status)
            try:
                data = response.json()
                print("Keys:", data.keys())
                jobs = data.get('jobs', []) or data.get('jobSearchResults', []) or []
                print(f"Total jobs returned: {len(jobs)}")
                for j in jobs[:5]:
                    print("  Job:", j.get('title') or j.get('jobTitle'), "ID:", j.get('id') or j.get('jobId'), "URL:", j.get('url'))
            except Exception as e:
                print("JSON decode error:", e, response.text()[:200])

    page.on("response", handle_response)
    page.goto('https://careers.hcltech.com/search/?q=&locationsearch=India', wait_until='networkidle')
    page.wait_for_timeout(3000)
    browser.close()

