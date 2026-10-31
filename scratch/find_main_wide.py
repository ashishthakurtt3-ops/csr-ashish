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
        
        # Check what inside main-wrapper has scrollWidth > 375
        res = await page.evaluate("""() => {
            const els = [];
            document.querySelectorAll('.main-wrapper *').forEach(el => {
                if (el.scrollWidth > 375) {
                    els.push({
                        tag: el.tagName,
                        id: el.id,
                        className: el.className,
                        scrollWidth: el.scrollWidth,
                        offsetWidth: el.offsetWidth,
                        right: el.getBoundingClientRect().right
                    });
                }
            });
            return els;
        }""")
        print("Wide elements in main-wrapper:")
        for el in res[:10]:
            print(el)
        await browser.close()

asyncio.run(main())

