from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    network_urls = []
    page.on("request", lambda req: network_urls.append((req.method, req.url)))

    page.goto('https://careers.hcltech.com/search/?q=&locationsearch=India', wait_until='networkidle')
    print("Page Title:", page.title())
    print("Total network requests:", len(network_urls))
    
    # Filter for candidate/job/search requests
    for method, u in network_urls:
        if any(k in u.lower() for k in ['search', 'job', 'hcm55', 'api', 'query', 'requisition']):
            print(f"  {method} {u}")

    browser.close()

