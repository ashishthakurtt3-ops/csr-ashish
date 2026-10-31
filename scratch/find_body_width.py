import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 375, "height": 812},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15"
        )
        page = await context.new_page()
        await page.goto("http://127.0.0.1:8000/", wait_until="networkidle")
        
        # Check what makes body scrollWidth > 375
        res = await page.evaluate("""() => {
            const els = [];
            document.querySelectorAll('body > *').forEach(el => {
                els.push({
                    tag: el.tagName,
                    id: el.id,
                    className: el.className,
                    scrollWidth: el.scrollWidth,
                    offsetWidth: el.offsetWidth,
                    getBoundingRight: el.getBoundingClientRect().right
                });
            });
            return {
                bodyScrollWidth: document.body.scrollWidth,
                docScrollWidth: document.documentElement.scrollWidth,
                children: els
            };
        }""")
        print("Body direct children:", res)
        await browser.close()

asyncio.run(main())

