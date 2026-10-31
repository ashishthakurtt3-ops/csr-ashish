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
        
        # Test hiding header-inner
        res = await page.evaluate("""() => {
            const el = document.querySelector('.header-inner');
            const style = window.getComputedStyle(el);
            return {
                display: style.display,
                width: el.offsetWidth,
                scrollWidth: document.documentElement.scrollWidth,
                offsetWidth: document.documentElement.offsetWidth
            };
        }""")
        print("Before fix:", res)
        
        # Inject fix
        await page.add_style_tag(content="""
            html, body {
                overflow-x: hidden !important;
                max-width: 100vw !important;
            }
            @media (max-width: 1023px) {
                .header-inner {
                    display: none !important;
                }
                .app-bg-glows {
                    display: none !important;
                }
            }
        """)
        
        res_after = await page.evaluate("""() => {
            return {
                scrollWidth: document.documentElement.scrollWidth,
                offsetWidth: document.documentElement.offsetWidth,
                bodyScrollWidth: document.body.scrollWidth,
                hasOverflow: document.documentElement.scrollWidth > document.documentElement.offsetWidth
            };
        }""")
        print("After fix:", res_after)
        await browser.close()

asyncio.run(main())

