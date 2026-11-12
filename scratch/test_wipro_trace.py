import asyncio
from playwright.async_api import async_playwright

async def trace_wipro():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        apis = []
        page.on('response', lambda resp: apis.append((resp.status, resp.url)) if any(k in resp.url for k in ['api', 'job', 'search', 'graphql', 'json']) else None)
        
        await page.goto("https://careers.wipro.com/search", wait_until='networkidle', timeout=20000)
        print(f"Captured {len(apis)} matching responses:")
        for status, url in apis:
            if not url.endswith(('.js', '.png', '.jpg', '.css', '.svg', '.woff2')):
                print(f"  [{status}] {url}")
        await browser.close()

asyncio.run(trace_wipro())

