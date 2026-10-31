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
        
        # Inject fix for header-inner
        await page.add_style_tag(content="""
            @media (max-width: 1023px) {
                .header-inner { display: none !important; }
            }
        """)
        
        wide_elements = await page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('body *').forEach(el => {
                if (el.scrollWidth > 375) {
                    results.push({
                        tag: el.tagName,
                        id: el.id,
                        className: el.className,
                        scrollWidth: el.scrollWidth,
                        offsetWidth: el.offsetWidth,
                        clientWidth: el.clientWidth
                    });
                }
            });
            return results.slice(0, 20);
        }""")
        print("Elements with scrollWidth > 375:")
        for el in wide_elements:
            print(el)
        await browser.close()

asyncio.run(main())

